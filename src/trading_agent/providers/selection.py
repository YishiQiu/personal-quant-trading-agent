"""命令行与 HTTP 接口共用的数据源选择规则。"""

from __future__ import annotations

import json
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path
from typing import Any, Mapping

from trading_agent.providers.base import MarketDataProvider
from trading_agent.providers.eastmoney import FreeDataProviderError
from trading_agent.providers.registry import ProviderRegistry
from trading_agent.providers.sina import SinaFreeProvider

DEFAULT_RAW_SNAPSHOT_DIRECTORY = Path("data/raw_snapshots")


def latest_sina_snapshot(
    raw_snapshot_directory: str | Path | None = None,
) -> Path:
    """返回最近一份完整新浪日线快照；找不到时明确报错。"""

    directory = Path(raw_snapshot_directory) if raw_snapshot_directory is not None else DEFAULT_RAW_SNAPSHOT_DIRECTORY
    snapshots = sorted(directory.glob("sina-*.json"))
    if not snapshots:
        raise FreeDataProviderError(
            "No completed Sina snapshot is available. Capture one after close before research."
        )
    return snapshots[-1]


def latest_completed_sina_snapshot(
    moment: datetime,
    raw_snapshot_directory: str | Path | None = None,
) -> Path | None:
    """返回最近完整收盘快照；当天收盘后需要重新抓取时返回 None。

    A 股交易日 15:00 以后，开盘前抓取的文件仍代表昨天收盘。
    此时返回 None，要求 API 刷新全市场快照，避免继续回放旧数据。
    """

    try:
        latest = latest_sina_snapshot(raw_snapshot_directory)
    except FreeDataProviderError:
        if _needs_today_close_refresh(moment):
            return None
        raise
    if not _needs_today_close_refresh(moment):
        return latest
    return latest if _snapshot_is_current_day_close(latest, moment.date()) else None


def completed_close_date(observed_at: datetime) -> date:
    """把抓取时间转换为对应完整日 K 的交易日期。"""

    result = observed_at.date()
    local_time = observed_at.timetz().replace(tzinfo=None)
    if observed_at.weekday() >= 5 or local_time < clock_time(9, 15):
        result -= timedelta(days=1)
    while result.weekday() >= 5:
        result -= timedelta(days=1)
    return result


def snapshot_close_date(snapshot_path: str | Path) -> date:
    """读取持久化快照的完整日 K 日期，供 API 和界面显示。"""

    try:
        document = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
        if not isinstance(document, Mapping):
            raise ValueError("snapshot is not an object")
        observed_at = datetime.fromisoformat(str(document["observed_at"]))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FreeDataProviderError(f"Cannot read Sina snapshot time: {snapshot_path}") from exc
    return completed_close_date(observed_at)


def _needs_today_close_refresh(moment: datetime) -> bool:
    if moment.weekday() >= 5:
        return False
    return moment.timetz().replace(tzinfo=None) >= clock_time(15, 0)


def _snapshot_is_current_day_close(snapshot_path: Path, current_day: date) -> bool:
    try:
        document: Any = json.loads(snapshot_path.read_text(encoding="utf-8"))
        observed_at = datetime.fromisoformat(str(document["observed_at"]))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    local_time = observed_at.timetz().replace(tzinfo=None)
    return observed_at.date() == current_day and local_time >= clock_time(15, 0)


def resolve_provider(
    registry: ProviderRegistry,
    provider_name: str,
    *,
    snapshot_path: str | Path | None = None,
    prefer_cached_sina_snapshot: bool = False,
    raw_snapshot_directory: str | Path | None = None,
) -> MarketDataProvider:
    """按统一的前收盘缓存规则解析数据源。"""

    if provider_name.casefold() == SinaFreeProvider.name:
        if snapshot_path is None and prefer_cached_sina_snapshot:
            snapshot_path = latest_sina_snapshot(raw_snapshot_directory)
        if snapshot_path is not None:
            return SinaFreeProvider(snapshot_path=snapshot_path)
    elif snapshot_path is not None:
        raise ValueError("--snapshot currently supports only provider 'sina_free'")
    return registry.create(provider_name)
