from typing import Iterable
from PIL import Image, ImageDraw
from domain.type import Stroke


def compose_strokes_on_image(
    base_img: Image.Image, strokes: Iterable[Stroke]
) -> Image.Image:
    """描画ストロークを画像へ焼き込む。
    base_img: リサイズ済みなど保存対象のPIL画像
    strokes: 画像座標系の点列・色・太さ
    return: 合成後の新しい画像
    """
    img = base_img.copy()
    draw = ImageDraw.Draw(img)
    for s in strokes:
        if not s.points or len(s.points) < 2:
            continue
        draw.line(s.points, fill=s.color, width=int(s.width))
    return img
