from __future__ import annotations

from datetime import datetime

from trading_agent.scheduler.window import (
    is_close_snapshot_capture_window,
    is_previous_close_research_window,
)


def test_previous_close_windows_are_separate_from_intraday_research() -> None:
    assert is_close_snapshot_capture_window(datetime(2026, 7, 13, 15, 5))
    assert not is_close_snapshot_capture_window(datetime(2026, 7, 13, 14, 55))
    assert is_previous_close_research_window(datetime(2026, 7, 14, 9, 0))
    assert not is_previous_close_research_window(datetime(2026, 7, 14, 9, 20))
