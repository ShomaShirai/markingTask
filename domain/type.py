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
    """
    画像処理用の定数セット（肌色変換・血管ティント・MIPカラーマップ）
    カラーマップの部分は,OCEAN or HOTを使用する
    """

    hue_for_bg: int = 15
    sat_for_bg: int = 140
    vein_h: int = 30
    vein_s: int = 255
    mip_colormap: int = cv.COLORMAP_OCEAN
    # 円形表示設定
    circular_display: bool = True  # 円形表示を有効化
    circular_bg_color: tuple = (34, 34, 34)  # 円の外側の背景色 (B, G, R)


@dataclass
class DrawingConfig:
    """UI描画設定（Tkinter Canvas用カラー等）"""

    mip_line_color: str = "#00C8FF"  # MIP用ライン色（シアン系）
    vein_line_color: str = "#FF5050"  # 血管抽出用ライン色（赤系）
    line_width: int = 3


# 課題モード定義（Domainは型のみ提供。既定値はServicesで保持）
@dataclass
class ModeSpec:
    key: str  # 例: 'practice', 'task1', 'task2' ...
    label: str  # UI表示用ラベル（例: '練習', '1' など）
    max_trials: int | None  # Noneは無制限、数値はその回数で終了
    # 画像処理のモード別上書き設定（例: task5で MIP のカラーマップを HOT にする）
    mip_colormap_override: int | None = None


@dataclass
class ModesConfig:
    modes: list[ModeSpec]


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
