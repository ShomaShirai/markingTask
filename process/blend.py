import cv2 as cv
import numpy as np

from process.HSV_trans import HSVTransformer
from domain.type import (
    BlendParams,
    ProcessingConfig,
)


def read_color(path: str) -> np.ndarray:
    img = cv.imread(path, cv.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"画像を読み込めませんでした: {path}")
    return img


def ensure_size(ref: np.ndarray, other: np.ndarray) -> np.ndarray:
    if ref.shape[:2] == other.shape[:2]:
        return other
    return cv.resize(other, (ref.shape[1], ref.shape[0]))


def rotate_image(
    img: np.ndarray, angle_deg: float, keep_size: bool = False
) -> np.ndarray:
    """中心回りに回転。

    Args:
        img: 入力画像
        angle_deg: 回転角度（度）
        keep_size: Trueの場合は元のサイズを維持、Falseの場合は全体が収まるようにサイズ拡張
    """
    if not angle_deg:
        return img

    h, w = img.shape[:2]
    center = (w / 2.0, h / 2.0)
    mat = cv.getRotationMatrix2D(center, angle_deg, 1.0)

    if keep_size:
        # 元のサイズを維持して回転（円形マスク用）
        rotated = cv.warpAffine(
            img, mat, (w, h), flags=cv.INTER_LINEAR, borderMode=cv.BORDER_CONSTANT
        )
    else:
        # サイズを拡張して全体を表示
        c, s = abs(mat[0, 0]), abs(mat[0, 1])
        new_w = int(h * s + w * c)
        new_h = int(h * c + w * s)
        mat[0, 2] += (new_w / 2.0) - center[0]
        mat[1, 2] += (new_h / 2.0) - center[1]
        rotated = cv.warpAffine(
            img,
            mat,
            (new_w, new_h),
            flags=cv.INTER_LINEAR,
            borderMode=cv.BORDER_CONSTANT,
        )
    return rotated


def colorize_mip(mip_img: np.ndarray, colormap: int) -> np.ndarray:
    # 1ch化
    if mip_img.ndim == 3:
        mip_gray = cv.cvtColor(mip_img, cv.COLOR_BGR2GRAY)
    else:
        mip_gray = mip_img
    # CLAHE
    if mip_gray.dtype == np.uint8:
        mip_u8 = mip_gray
    else:
        mip_u8 = cv.normalize(mip_gray, None, 0, 255, cv.NORM_MINMAX).astype(np.uint8)
    clahe = cv.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    mip_clahe = clahe.apply(mip_u8)
    # カラーマップ
    mip_color = cv.applyColorMap(mip_clahe, colormap)
    return mip_color


def blend_two(back: np.ndarray, front: np.ndarray, alpha: float) -> np.ndarray:
    alpha = float(np.clip(alpha, 0.0, 1.0))
    back_f = back.astype(np.float32)
    front_f = front.astype(np.float32)
    out = (alpha * front_f + (1.0 - alpha) * back_f).astype(np.uint8)
    return out


def blend_with_mask(
    back: np.ndarray, front: np.ndarray, alpha: float, mask: np.ndarray
) -> np.ndarray:
    alpha = float(np.clip(alpha, 0.0, 1.0))
    out = back.astype(np.float32)
    idx = mask > 0
    out[idx] = alpha * front[idx].astype(np.float32) + (1.0 - alpha) * back[idx].astype(
        np.float32
    )
    return out.astype(np.uint8)


# --- Helper functions ---
def apply_transforms(
    img: np.ndarray, flip_code: int | None, angle_deg: float, keep_size: bool = False
) -> np.ndarray:
    """Apply optional flip then rotation to an image.

    Args:
        img: 入力画像
        flip_code: 反転コード (None, 0, 1, -1)
        angle_deg: 回転角度
        keep_size: Trueの場合は元のサイズを維持
    """
    if flip_code is not None and flip_code in (0, 1, -1):
        img = cv.flip(img, flip_code)
    img = rotate_image(img, angle_deg, keep_size=keep_size)
    return img


def build_masks(
    mid_img: np.ndarray, fg_img: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Build binary masks for MIP and vein from their grayscale representations."""
    mid_gray = cv.cvtColor(mid_img, cv.COLOR_BGR2GRAY) if mid_img.ndim == 3 else mid_img
    _, mask_mip = cv.threshold(mid_gray, 0, 255, cv.THRESH_BINARY)
    fg_gray = cv.cvtColor(fg_img, cv.COLOR_BGR2GRAY)
    _, mask_vein = cv.threshold(fg_gray, 0, 255, cv.THRESH_BINARY)
    return mask_mip, mask_vein


def make_base_bg(
    bg_img: np.ndarray, processing: ProcessingConfig, mode_key: str | None
) -> np.ndarray:
    if mode_key == "task1":
        return bg_img
    hsv_tf = HSVTransformer(hue=processing.hue_for_bg, saturation=processing.sat_for_bg)
    bg_skin = hsv_tf.convert_ir_to_skin_color(bg_img)
    return bg_skin


def make_mip_layer(
    mid_img: np.ndarray,
    processing: ProcessingConfig,
    mode_key: str | None,
    mip_colormap_override: int | None = None,
) -> np.ndarray:
    """Front layer for MIP: default colorized; task1 uses image as-is (no processing)."""
    if mode_key == "task1" or mode_key == "task2" or mode_key == "task3":
        return mid_img
    colormap = (
        mip_colormap_override
        if mip_colormap_override is not None
        else processing.mip_colormap
    )
    return colorize_mip(mid_img, colormap)


def make_vein_layer(
    bg_base: np.ndarray,
    processing: ProcessingConfig,
    mode_key: str | None,
    fg_img: np.ndarray | None = None,
) -> np.ndarray:
    """Front layer for veins: default HSV tint; task1 uses vein image as-is (no processing)."""
    if (mode_key == "task1" or mode_key == "task2") and fg_img is not None:
        return fg_img
    bg_hsv = cv.cvtColor(bg_base, cv.COLOR_BGR2HSV)
    vein_hsv = np.zeros_like(bg_hsv)
    vein_hsv[:, :, 0] = np.uint8(np.clip(processing.vein_h, 0, 179))
    vein_hsv[:, :, 1] = np.uint8(np.clip(processing.vein_s, 0, 255))
    vein_hsv[:, :, 2] = bg_hsv[:, :, 2]
    return cv.cvtColor(vein_hsv, cv.COLOR_HSV2BGR)


def apply_circular_mask(
    img: np.ndarray, background_color: tuple = (0, 0, 0)
) -> np.ndarray:
    """
    画像に円形マスクを適用し、円の外側を背景色で塗りつぶす

    Args:
        img: 入力画像 (BGR)
        background_color: 円の外側の色 (B, G, R)

    Returns:
        円形マスクを適用した画像
    """
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    # 画像サイズが固定されるので、円の半径も固定される
    radius = min(w, h) // 2

    # 円形マスクを作成
    mask = np.zeros((h, w), dtype=np.uint8)
    cv.circle(mask, center, radius, 255, -1)

    # マスク適用
    result = img.copy()
    if len(img.shape) == 3:
        for i in range(3):
            result[:, :, i][mask == 0] = background_color[i]
    else:
        result[mask == 0] = background_color[0]

    return result


def blend_three(
    bg_path: str,
    mid_path: str,
    fg_path: str,
    params: BlendParams,
    rotation_deg: float = 0.0,
    flip_code: int | None = None,
    processing: ProcessingConfig | None = None,
    mode_key: str | None = None,
    mip_colormap_override: int | None = None,
) -> np.ndarray:
    # 読み込み
    bg = read_color(bg_path)
    mid = read_color(mid_path)
    fg = read_color(fg_path)

    # 設定
    if processing is None:
        processing = ProcessingConfig()

    # サイズ合わせ（まだ変換前）
    mid = ensure_size(bg, mid)
    fg = ensure_size(bg, fg)

    # 円形表示の場合は元サイズを保持
    keep_size = processing.circular_display

    # 3画像へ変換適用（flip→rotate）
    bg_pre = apply_transforms(bg, flip_code, rotation_deg, keep_size=keep_size)
    mid = apply_transforms(mid, flip_code, rotation_deg, keep_size=keep_size)
    fg = apply_transforms(fg, flip_code, rotation_deg, keep_size=keep_size)

    # マスク生成
    mask_mip, mask_vein = build_masks(mid, fg)

    # レイヤー生成
    base_bg = make_base_bg(bg_pre, processing, mode_key)
    mip_layer = make_mip_layer(
        mid, processing, mode_key, mip_colormap_override=mip_colormap_override
    )
    vein_layer = make_vein_layer(base_bg, processing, mode_key, fg_img=fg)

    # ブレンド（順序固定）
    blend1 = blend_with_mask(base_bg, mip_layer, params.alpha_mid, mask_mip)
    out = blend_with_mask(blend1, vein_layer, params.alpha_fg, mask_vein)

    # 円形マスク適用（設定が有効な場合）
    if processing.circular_display:
        out = apply_circular_mask(out, background_color=processing.circular_bg_color)

    return out
