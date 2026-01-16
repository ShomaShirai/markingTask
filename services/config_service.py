import cv2 as cv
import random
from domain.type import ProcessingConfig, DrawingConfig, ModesConfig, ModeSpec

# Services層で既定値の実体を提供
DEFAULT_PROCESSING_CONFIG = ProcessingConfig()
DEFAULT_DRAWING_CONFIG = DrawingConfig()
DEFAULT_MODES_CONFIG = ModesConfig(
    modes=[
        ModeSpec(key="practice", label="練習", max_trials=None),
        ModeSpec(key="task1", label="1", max_trials=6),
        ModeSpec(key="task2", label="2", max_trials=6),
        ModeSpec(key="task3", label="3", max_trials=6),
        ModeSpec(key="task4", label="4", max_trials=6),
        # task5: MIPのカラーマップをHOTに上書き
        ModeSpec(
            key="task5", label="5", max_trials=6, mip_colormap_override=cv.COLORMAP_HOT
        ),
    ]
)

# UIモードと内部タスクのマッピング（固定）
_ui_to_internal_task_mapping: dict[str, str] = {}


def _initialize_task_mapping():
    """UIモード（task1〜5）と内部タスク（task1〜5）のマッピングをランダムに初期化"""
    global _ui_to_internal_task_mapping
    ui_modes = ["task1", "task2", "task3", "task4", "task5"]
    internal_tasks = ["task1", "task2", "task3", "task4", "task5"]
    random.shuffle(internal_tasks)
    _ui_to_internal_task_mapping = dict(zip(ui_modes, internal_tasks))


def get_internal_task_mode(ui_mode_key: str | None) -> str:
    """
    UIで選択された課題モードに対応する内部タスクを返す

    Args:
        ui_mode_key: UIで選択されている課題モード（practice, task1〜5など）

    Returns:
        実際に使用するタスクモード
        - practiceの場合はそのまま"practice"
        - task1〜5の場合は、初回に割り当てられた内部タスク（固定）
    """
    global _ui_to_internal_task_mapping

    # 練習モードの場合はそのまま返す
    if ui_mode_key == "practice":
        return "practice"

    # マッピングが未初期化なら初期化
    if not _ui_to_internal_task_mapping:
        _initialize_task_mapping()

    # UIモードに対応する内部タスクを返す（存在しない場合はそのまま）
    return _ui_to_internal_task_mapping.get(ui_mode_key, ui_mode_key)
