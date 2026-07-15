"""Time-window guard only; holidays need a dedicated exchange-calendar provider."""

from __future__ import annotations

from datetime import datetime, time


def is_tail_research_window(moment: datetime) -> bool:
    """Return true from 14:30 through 14:55 on a weekday in the caller's timezone."""

    return moment.weekday() < 5 and time(14, 30) <= moment.timetz().replace(tzinfo=None) <= time(14, 55)


def is_close_snapshot_capture_window(moment: datetime) -> bool:
    """Return true shortly after close, when a completed daily bar can be cached."""

    local_time = moment.timetz().replace(tzinfo=None)
    return moment.weekday() < 5 and time(15, 1) <= local_time <= time(15, 15)


def is_previous_close_research_window(moment: datetime) -> bool:
    """Return true during the pre-open window for prior-close candidate research."""

    local_time = moment.timetz().replace(tzinfo=None)
    return moment.weekday() < 5 and time(8, 45) <= local_time <= time(9, 15)
