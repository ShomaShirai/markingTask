import os
import csv
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from PIL import Image

from process.blend import blend_three
from process.draw import compose_strokes_on_image
from domain.type import BlendParams, SaveRule, Stroke, ProcessingConfig
from services.user_service import get_current_user
from services.config_service import get_internal_task_mode


DEFAULT_PROCESSING_CONFIG = ProcessingConfig()


def browse_path(var: tk.StringVar) -> None:
    path = filedialog.askopenfilename(
        filetypes=[("画像ファイル", "*.png;*.jpg;*.jpeg;*.bmp"), ("すべて", "*.*")]
    )
    if path:
        var.set(path)


def blend_and_get_image(
    bg_path: str,
    mid_path: str,
    fg_path: str,
    alpha_mid: float,
    alpha_fg: float,
    rotation_deg: float = 0.0,
    flip_code: int | None = None,
    mode_key: str | None = None,
    mip_colormap_override: int | None = None,
) -> Image.Image:
    if not (
        os.path.isfile(bg_path) and os.path.isfile(mid_path) and os.path.isfile(fg_path)
    ):
        raise ValueError("3枚の画像パスを正しく指定してください。")
    params = BlendParams(alpha_mid=float(alpha_mid), alpha_fg=float(alpha_fg))
    out_bgr = blend_three(
        bg_path,
        mid_path,
        fg_path,
        params,
        rotation_deg=rotation_deg,
        flip_code=flip_code,
        processing=DEFAULT_PROCESSING_CONFIG,
        mode_key=mode_key,
        mip_colormap_override=mip_colormap_override,
    )
    out_rgb = out_bgr[:, :, ::-1]
    return Image.fromarray(out_rgb)


def resize_for_canvas(
    pil_img: Image.Image, canvas_w: int, canvas_h: int
) -> Image.Image:
    img_w, img_h = pil_img.size
    scale = min(canvas_w / img_w, canvas_h / img_h)
    if scale < 1.0:
        pil_img = pil_img.resize(
            (int(img_w * scale), int(img_h * scale)), Image.LANCZOS
        )
    return pil_img


def save_with_canvas(
    base_img: Image.Image, strokes: list[Stroke], mode_key: str | None = None
) -> str | None:
    """キャンバス描画を合成して、Domain規則に従って保存する。"""
    if base_img is None:
        return None

    composed = compose_strokes_on_image(base_img, strokes)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    user = get_current_user()
    username = (
        user.name if user and getattr(user, "name", None) else "unknown"
    ).strip() or "unknown"

    rule = SaveRule()
    date_str = datetime.now().strftime("%Y%m%d")
    time_str = datetime.now().strftime("%H%M%S%f")
    dir_name = rule.dir_format.format(username=username, date=date_str)
    out_dir = os.path.join(base_dir, dir_name)

    # UIモードを内部タスクに変換
    internal_task = get_internal_task_mode(mode_key)

    # モード1..5の場合はサブディレクトリ（例: "1"）を作成
    if internal_task and internal_task.startswith("task"):
        try:
            idx = int(internal_task.replace("task", ""))
            out_dir = os.path.join(out_dir, str(idx))
        except Exception:
            pass
    # 練習モードは "practice" サブディレクトリ配下に保存
    elif mode_key == "practice":
        out_dir = os.path.join(out_dir, "practice")
    os.makedirs(out_dir, exist_ok=True)

    filename = rule.file_format.format(time=time_str)
    out_path = os.path.join(out_dir, filename)

    composed.save(out_path)
    return out_path


def append_metrics_for_image(image_path: str, rows: list[dict]) -> str:
    """同じ保存ディレクトリに metrics.csv を作成/追記する。
    rows: {mode, start_latency_ms, stroke_duration_ms, rotation_deg}
    return: CSVファイルのパス
    """
    out_dir = os.path.dirname(image_path)
    csv_path = os.path.join(out_dir, "metrics.csv")

    # 画像ID抽出（image_{id}.png）
    base = os.path.basename(image_path)
    image_id = os.path.splitext(base)[0]
    if image_id.startswith("image_"):
        image_id = image_id[len("image_") :]

    fieldnames = [
        "image_id",
        "mode",
        "start_latency_ms",
        "stroke_duration_ms",
        "rotation_deg",
    ]
    write_header = not os.path.exists(csv_path)

    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "image_id": image_id,
                    "mode": r.get("mode"),
                    "start_latency_ms": r.get("start_latency_ms"),
                    "stroke_duration_ms": r.get("stroke_duration_ms"),
                    "rotation_deg": r.get("rotation_deg"),
                }
            )
    return csv_path
