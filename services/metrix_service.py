import time


class MetricsService:
    """UIでの操作タイミングをservices側で管理するトラッカー。
    UIは各イベントでこのクラスのメソッドを呼び出すだけにする。
    単一描画モード用に簡素化。
    """

    def __init__(self) -> None:
        self._task_start_ts: float | None = None
        self._timing_record: dict[str, int | None] = {
            "start_latency_ms": None,
            "stroke_duration_ms": None,
        }
        self._current_stroke_start_ts: float | None = None

    def start_task(self) -> None:
        """ "次へ行く"押下相当。計測をリセットし、起点時刻を記録。"""
        self._timing_record = {
            "start_latency_ms": None,
            "stroke_duration_ms": None,
        }
        self._current_stroke_start_ts = None
        self._task_start_ts = time.perf_counter()

    def on_canvas_down(self) -> None:
        """キャンバス押下イベントで呼ぶ。開始点までの時間とストローク開始を記録。"""
        if self._task_start_ts is not None:
            if self._timing_record["start_latency_ms"] is None:
                now = time.perf_counter()
                self._timing_record["start_latency_ms"] = int(
                    (now - self._task_start_ts) * 1000
                )
        # ストローク開始
        self._current_stroke_start_ts = time.perf_counter()

    def on_canvas_up(self) -> None:
        """キャンバス解放イベントで呼ぶ。ストローク継続時間を記録。"""
        if self._current_stroke_start_ts is not None:
            if self._timing_record["stroke_duration_ms"] is None:
                dur_ms = int(
                    (time.perf_counter() - self._current_stroke_start_ts) * 1000
                )
                self._timing_record["stroke_duration_ms"] = dur_ms
        self._current_stroke_start_ts = None

    def build_rows(self, rotation_deg: float | None = None) -> list[dict]:
        """CSV追記用の辞書配列を構築する。"""
        return [
            {
                "start_latency_ms": self._timing_record.get("start_latency_ms"),
                "stroke_duration_ms": self._timing_record.get("stroke_duration_ms"),
                "rotation_deg": rotation_deg,
            }
        ]
