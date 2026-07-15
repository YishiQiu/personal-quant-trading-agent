from __future__ import annotations

import argparse
import json
from datetime import datetime

from trading_agent import cli
from trading_agent.providers import selection
from trading_agent.providers.sina import SinaFreeProvider


def test_sina_research_defaults_to_the_latest_cached_snapshot(tmp_path, monkeypatch) -> None:
    older = tmp_path / "sina-20260713T150500+0800.json"
    latest = tmp_path / "sina-20260714T150500+0800.json"
    older.touch()
    latest.touch()
    monkeypatch.setattr(selection, "DEFAULT_RAW_SNAPSHOT_DIRECTORY", tmp_path)

    provider = cli._provider_from_args(
        argparse.Namespace(provider="sina_free", snapshot=None),
        prefer_cached_sina_snapshot=True,
    )

    assert isinstance(provider, SinaFreeProvider)
    assert provider._snapshot_path == latest


def test_latest_completed_snapshot_refreshes_a_premarket_cache_after_today_close(tmp_path) -> None:
    premarket = tmp_path / "sina-20260714T085000+0800.json"
    after_close = tmp_path / "sina-20260714T150500+0800.json"
    premarket.write_text(json.dumps({"observed_at": "2026-07-14T08:50:00+08:00"}), encoding="utf-8")

    assert selection.latest_completed_sina_snapshot(
        datetime.fromisoformat("2026-07-14T14:30:00+08:00"), tmp_path
    ) == premarket
    assert selection.latest_completed_sina_snapshot(
        datetime.fromisoformat("2026-07-14T15:05:00+08:00"), tmp_path
    ) is None

    after_close.write_text(json.dumps({"observed_at": "2026-07-14T15:05:00+08:00"}), encoding="utf-8")
    assert selection.latest_completed_sina_snapshot(
        datetime.fromisoformat("2026-07-14T15:06:00+08:00"), tmp_path
    ) == after_close
    assert selection.snapshot_close_date(premarket).isoformat() == "2026-07-13"
