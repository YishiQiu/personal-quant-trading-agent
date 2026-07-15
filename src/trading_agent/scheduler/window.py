"""只判断时间窗口；节假日需要单独接入交易日历数据源。"""

from __future__ import annotations

from datetime import datetime, time


def is_tail_research_window(moment: datetime) -> bool:
    """按调用方时区判断工作日 14:30 至 14:55 的尾盘研究窗口。"""

    return moment.weekday() < 5 and time(14, 30) <= moment.timetz().replace(tzinfo=None) <= time(14, 55)


def is_close_snapshot_capture_window(moment: datetime) -> bool:
    """判断收盘后可以缓存完整日 K 的短时间窗口。"""

    local_time = moment.timetz().replace(tzinfo=None)
    return moment.weekday() < 5 and time(15, 1) <= local_time <= time(15, 15)


def is_previous_close_research_window(moment: datetime) -> bool:
    """判断使用前收盘候选股进行盘前研究的时间窗口。"""

    local_time = moment.timetz().replace(tzinfo=None)
    return moment.weekday() < 5 and time(8, 45) <= local_time <= time(9, 15)
