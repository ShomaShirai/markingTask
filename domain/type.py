from dataclasses import dataclass
import cv2 as cv


@dataclass
class BlendParams:
    alpha_mid: float = 0.3
    alpha_fg: float = 0.3


@dataclass
class User:
    name: str


# 既定の色設定（肌色バック + クール系MIP + 肌色系血管ティント）
HUE_FOR_BG: int = 15
SAT_FOR_BG: int = 140
VEIN_H: int = 30
VEIN_S: int = 255
MIP_COLORMAP: int = cv.COLORMAP_OCEAN

# 描画設定（Tkinter Canvas用カラー）
# 16進カラー文字列で指定（例: "#RRGGBB"）
MIP_LINE_COLOR: str = "#00C8FF"  # MIP用ライン色（シアン系）
VEIN_LINE_COLOR: str = "#FF5050"  # 血管抽出用ライン色（赤系）
LINE_WIDTH: int = 3


# キャンバス描画（UIからServicesへ渡すデータ構造）
@dataclass
class Stroke:
    # 画像座標系上の点列（Canvas座標から画像左上原点へ変換後）
    points: list[tuple[float, float]]
    color: str
    width: int
    rotation: float = 0.0


@dataclass
class TransformParams:
    # 画像全体に適用する回転角度（度数法）
    rotation: float = 0.0


# 計測レコード
@dataclass
class TimingRecord:
    mode: str  # 'mip' | 'vein'
    start_latency_ms: int | None = None
    stroke_duration_ms: int | None = None


@dataclass
class SessionMetrics:
    mip: TimingRecord
    vein: TimingRecord


# 保存規則（Domain層で定義し、Services層で利用）
@dataclass
class SaveRule:
    # ディレクトリ名の書式: {username}, {date} (YYYYMMDD)
    dir_format: str = "{username}_{date}"
    # ファイル名の書式: {time} (HHMMSSfff), 拡張子はServices側で決定
    file_format: str = "image_{time}.png"
