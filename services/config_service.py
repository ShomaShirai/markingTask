import cv2 as cv
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
        ModeSpec(key="task5", label="5", max_trials=6, mip_colormap_override=cv.COLORMAP_HOT),
    ]
)
