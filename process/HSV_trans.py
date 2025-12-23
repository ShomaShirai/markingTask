import cv2 as cv
import numpy as np


class HSVTransformer:
    def __init__(self, hue: int = 15, saturation: int = 100):
        """
        HSV空間での変換を行うクラス（IR→肌色用の既定H/Sを保持）。

        Args:
            hue: 既定の色相 (0-179、15前後が肌色の目安)
            saturation: 既定の彩度 (0-255、100前後が自然な目安)
        """
        # 値を安全域にクリップして保持
        self.hue = int(np.clip(hue, 0, 179))
        self.saturation = int(np.clip(saturation, 0, 255))

    def set_params(self, hue: int | None = None, saturation: int | None = None):
        """既定のH/Sを更新"""
        if hue is not None:
            self.hue = int(np.clip(hue, 0, 179))
        if saturation is not None:
            self.saturation = int(np.clip(saturation, 0, 255))

    def convert_ir_to_skin_color(
        self, ir_frame, hue: int | None = None, saturation: int | None = None
    ):
        """
        赤外フレーム（グレースケール）を肌色のカラー画像に変換
        HSV色空間を使用してH(色相)とS(彩度)を肌色に設定し、V(明度)に赤外画像を適用

        Args:
            ir_frame: 赤外フレーム（グレースケール画像）
            hue: 色相 (0-179)。未指定(None)ならインスタンス既定値 self.hue を使用
            saturation: 彩度 (0-255)。未指定(None)なら self.saturation を使用

        Returns:
            skin_colored_frame: 肌色に変換されたBGR画像
        """
        # 入力を1ch uint8に整形
        if ir_frame is None:
            raise ValueError("ir_frame is None")
        if ir_frame.ndim == 3:
            ir_frame = cv.cvtColor(ir_frame, cv.COLOR_BGR2GRAY)
        if ir_frame.dtype != np.uint8:
            ir_frame = cv.normalize(ir_frame, None, 0, 255, cv.NORM_MINMAX).astype(
                np.uint8
            )

        # 使用するH/Sを決定
        use_h = int(np.clip(self.hue if hue is None else hue, 0, 179))
        use_s = int(
            np.clip(self.saturation if saturation is None else saturation, 0, 255)
        )

        # 画像サイズを取得
        height, width = ir_frame.shape

        # HSV画像を作成
        hsv_image = np.zeros((height, width, 3), dtype=np.uint8)

        # H(色相)チャンネル: 肌色 (15前後がベージュ/肌色)
        hsv_image[:, :, 0] = use_h

        # S(彩度)チャンネル: 適度な彩度
        hsv_image[:, :, 1] = use_s

        # V(明度)チャンネル: 赤外画像の明度をそのまま使用
        hsv_image[:, :, 2] = ir_frame

        # HSVからBGRに変換
        skin_colored_frame = cv.cvtColor(hsv_image, cv.COLOR_HSV2BGR)

        return skin_colored_frame
