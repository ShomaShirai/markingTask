import cv2 as cv
import numpy as np

from process.HSV_trans import HSVTransformer
from domain.type import (
    BlendParams,
    HUE_FOR_BG,
    SAT_FOR_BG,
    VEIN_H,
    VEIN_S,
    MIP_COLORMAP,
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


def rotate_image(img: np.ndarray, angle_deg: float) -> np.ndarray:
    """中心回りに同サイズで回転。"""
    if not angle_deg:
        return img

    # 画像サイズを拡張することで全体の画像を表示できるように修正
    h, w = img.shape[:2]
    center = (w / 2.0, h / 2.0)
    mat = cv.getRotationMatrix2D(center, angle_deg, 1.0)
    c, s = abs(mat[0, 0]), abs(mat[0, 1])
    new_w = int(h * s + w * c)
    new_h = int(h * c + w * s)
    mat[0, 2] += (new_w / 2.0) - center[0]
    mat[1, 2] += (new_h / 2.0) - center[1]
    rotated = cv.warpAffine(
        img, mat, (new_w, new_h), flags=cv.INTER_LINEAR, borderMode=cv.BORDER_CONSTANT
    )
    return rotated


def colorize_mip(mip_img: np.ndarray, colormap: int = MIP_COLORMAP) -> np.ndarray:
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
    clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
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


def blend_three(
    bg_path: str,
    mid_path: str,
    fg_path: str,
    params: BlendParams,
    rotation_deg: float = 0.0,
    flip_code: int | None = None,
) -> np.ndarray:
    # 読み込み
    bg = read_color(bg_path)
    mid = read_color(mid_path)
    fg = read_color(fg_path)

    # 背景IRを肌色化
    hsv_tf = HSVTransformer(hue=HUE_FOR_BG, saturation=SAT_FOR_BG)
    bg_skin = hsv_tf.convert_ir_to_skin_color(bg)

    # サイズ合わせ
    mid = ensure_size(bg_skin, mid)
    fg = ensure_size(bg_skin, fg)

    # 3画像とも反転（必要なら）
    if flip_code is not None:
        if flip_code in (0, 1, -1):
            bg_skin = cv.flip(bg_skin, flip_code)
            mid = cv.flip(mid, flip_code)
            fg = cv.flip(fg, flip_code)

    # 3画像とも回転（同中心）
    bg_skin = rotate_image(bg_skin, rotation_deg)
    mid = rotate_image(mid, rotation_deg)
    fg = rotate_image(fg, rotation_deg)

    # MIPカラー化
    mid_color = colorize_mip(mid, MIP_COLORMAP)

    # MIPの非ゼロ画素のみマスク
    mid_gray_for_mask = cv.cvtColor(mid, cv.COLOR_BGR2GRAY) if mid.ndim == 3 else mid
    _, mask_mip = cv.threshold(mid_gray_for_mask, 0, 255, cv.THRESH_BINARY)

    # 背景 + MIP（マスク付き）
    blend1 = blend_with_mask(bg_skin, mid_color, params.alpha_mid, mask_mip)

    # 血管ティント（背景の明度Vを使用）
    bg_hsv = cv.cvtColor(bg_skin, cv.COLOR_BGR2HSV)
    vein_hsv = np.zeros_like(bg_hsv)
    vein_hsv[:, :, 0] = np.uint8(np.clip(VEIN_H, 0, 179))
    vein_hsv[:, :, 1] = np.uint8(np.clip(VEIN_S, 0, 255))
    vein_hsv[:, :, 2] = bg_hsv[:, :, 2]
    vein_tint = cv.cvtColor(vein_hsv, cv.COLOR_HSV2BGR)

    # 血管白領域のみブレンド
    fg_gray = cv.cvtColor(fg, cv.COLOR_BGR2GRAY)
    _, mask_bin = cv.threshold(fg_gray, 0, 255, cv.THRESH_BINARY)
    out = blend_with_mask(blend1, vein_tint, params.alpha_fg, mask_bin)

    return out
