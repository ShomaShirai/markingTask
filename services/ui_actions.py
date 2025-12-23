import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from PIL import Image

from process.blend import blend_three
from process.draw import compose_strokes_on_image
from domain.type import BlendParams, SaveRule, Stroke
from services.user_service import get_current_user


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
) -> Image.Image:
    if not (
        os.path.isfile(bg_path) and os.path.isfile(mid_path) and os.path.isfile(fg_path)
    ):
        raise ValueError("3枚の画像パスを正しく指定してください。")
    params = BlendParams(alpha_mid=float(alpha_mid), alpha_fg=float(alpha_fg))
    out_bgr = blend_three(bg_path, mid_path, fg_path, params)
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


def save_with_canvas(base_img: Image.Image, strokes: list[Stroke]) -> str | None:
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
    os.makedirs(out_dir, exist_ok=True)

    filename = rule.file_format.format(time=time_str)
    out_path = os.path.join(out_dir, filename)

    composed.save(out_path)
    return out_path
