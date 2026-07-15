"""Shared provider selection policy for commands and HTTP entry points."""

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
    """Return the most recent completed Sina daily snapshot or fail clearly."""

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
    """Return the latest completed close or ``None`` when today's close needs a fresh capture.

    At or after 15:00 on an A-share weekday, a file captured before the
    opening auction still represents yesterday's close. Returning ``None``
    makes the API refresh the full snapshot rather than replaying stale data.
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
    """Translate a capture timestamp into the trading date of its completed bar."""

    result = observed_at.date()
    local_time = observed_at.timetz().replace(tzinfo=None)
    if observed_at.weekday() >= 5 or local_time < clock_time(9, 15):
        result -= timedelta(days=1)
    while result.weekday() >= 5:
        result -= timedelta(days=1)
    return result


def snapshot_close_date(snapshot_path: str | Path) -> date:
    """Read a persisted snapshot's completed-bar date for API/UI labels."""

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
    """Resolve a provider while keeping previous-close cache policy consistent."""

    if provider_name.casefold() == SinaFreeProvider.name:
        if snapshot_path is None and prefer_cached_sina_snapshot:
            snapshot_path = latest_sina_snapshot(raw_snapshot_directory)
        if snapshot_path is not None:
            return SinaFreeProvider(snapshot_path=snapshot_path)
    elif snapshot_path is not None:
        raise ValueError("--snapshot currently supports only provider 'sina_free'")
    return registry.create(provider_name)
