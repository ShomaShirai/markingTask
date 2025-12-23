import time


class MetricsService:
    """UIでの操作タイミングをservices側で管理するトラッカー。
    UIは各イベントでこのクラスのメソッドを呼び出すだけにする。
    """

    def __init__(self) -> None:
        self._task_start_ts: float | None = None
        self._active_mode: str | None = None  # 'mip' | 'vein'
        self._timing_record: dict[str, dict[str, int | None]] = {
            "mip": {"start_latency_ms": None, "stroke_duration_ms": None},
            "vein": {"start_latency_ms": None, "stroke_duration_ms": None},
        }
        self._current_stroke_start_ts: float | None = None

    def start_task(self) -> None:
        """ "次へ行く"押下相当。計測をリセットし、起点時刻を記録。"""
        self._timing_record = {
            "mip": {"start_latency_ms": None, "stroke_duration_ms": None},
            "vein": {"start_latency_ms": None, "stroke_duration_ms": None},
        }
        self._current_stroke_start_ts = None
        self._task_start_ts = time.perf_counter()

    def set_mode(self, mode: str | None) -> None:
        if mode not in ("mip", "vein", None):
            return
        self._active_mode = mode

    def on_canvas_down(self) -> None:
        """キャンバス押下イベントで呼ぶ。開始点までの時間とストローク開始を記録。"""
        if self._active_mode in ("mip", "vein") and self._task_start_ts is not None:
            rec = self._timing_record[self._active_mode]
            if rec["start_latency_ms"] is None:
                now = time.perf_counter()
                rec["start_latency_ms"] = int((now - self._task_start_ts) * 1000)
        # ストローク開始
        self._current_stroke_start_ts = time.perf_counter()

    def on_canvas_up(self) -> None:
        """キャンバス解放イベントで呼ぶ。ストローク継続時間を記録。"""
        if self._current_stroke_start_ts is not None and self._active_mode in (
            "mip",
            "vein",
        ):
            rec = self._timing_record[self._active_mode]
            if rec["stroke_duration_ms"] is None:
                dur_ms = int(
                    (time.perf_counter() - self._current_stroke_start_ts) * 1000
                )
                rec["stroke_duration_ms"] = dur_ms
        self._current_stroke_start_ts = None

    def build_rows(self, rotation_deg: float | None = None) -> list[dict]:
        """CSV追記用の辞書配列を構築する。"""
        rows: list[dict] = []
        for mode_key in ("mip", "vein"):
            rec = self._timing_record.get(mode_key, {})
            rows.append(
                {
                    "mode": mode_key,
                    "start_latency_ms": rec.get("start_latency_ms"),
                    "stroke_duration_ms": rec.get("stroke_duration_ms"),
                    "rotation_deg": rotation_deg,
                }
            )
        return rows
