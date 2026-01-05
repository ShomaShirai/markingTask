from dataclasses import dataclass, field
import cv2 as cv


@dataclass
class BlendParams:
    alpha_mid: float = 0.3
    alpha_fg: float = 0.3


@dataclass
class User:
    name: str


@dataclass
class ProcessingConfig:
    """画像処理用の定数セット（肌色変換・血管ティント・MIPカラーマップ）"""

    hue_for_bg: int = 15
    sat_for_bg: int = 140
    vein_h: int = 30
    vein_s: int = 255
    mip_colormap: int = cv.COLORMAP_OCEAN


@dataclass
class DrawingConfig:
    """UI描画設定（Tkinter Canvas用カラー等）"""

    mip_line_color: str = "#00C8FF"  # MIP用ライン色（シアン系）
    vein_line_color: str = "#FF5050"  # 血管抽出用ライン色（赤系）
    line_width: int = 3


# キャンバス描画（UIからServicesへ渡すデータ構造）
@dataclass
class Stroke:
    # 画像座標系上の点列（Canvas座標から画像左上原点へ変換後）
    points: list[tuple[float, float]]
    color: str
    width: int
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


# Assets構成（Domainで規定し、Servicesで参照・実体パス解決）
@dataclass
class AssetsConfig:
    # ルートディレクトリ名（プロジェクト直下）
    root_dir_name: str = "assets"
    # 役割ごとの期待ファイル名候補
    expected_names: dict[str, list[str]] = field(
        default_factory=lambda: {
            "bg": ["woman.png", "bg.png"],
            "mid": ["compositionMip.png", "mip.png"],
            "fg": ["vein_white.png", "vein.png", "vein_mask.png"],
        }
    )
