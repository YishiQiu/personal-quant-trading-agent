from __future__ import annotations

from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pytest

from trading_agent.providers.eastmoney import EastmoneyFreeProvider, SnapshotIncompleteError


def _quote_row(code: str, name: str, price: float) -> dict[str, object]:
    return {
        "f2": price,
        "f3": 1.2,
        "f5": 12_000_000,
        "f6": 180_000_000,
        "f12": code,
        "f14": name,
        "f15": price + 0.3,
        "f16": price - 0.3,
        "f17": price - 0.1,
        "f18": price - 0.12,
    }


def test_free_provider_fetches_all_quote_pages_before_returning_snapshot(tmp_path) -> None:
    def fetch_json(url: str) -> dict[str, object]:
        page = parse_qs(urlparse(url).query)["pn"][0]
        if page == "1":
            return {
                "data": {
                    "total": 3,
                    "diff": [_quote_row("000001", "平安银行", 11.2), _quote_row("000002", "万科A", 7.8)],
                }
            }
        return {"data": {"total": 3, "diff": [_quote_row("600000", "浦发银行", 10.1)]}}

    provider = EastmoneyFreeProvider(
        page_size=2,
        min_expected_symbols=3,
        raw_snapshot_directory=tmp_path,
        fetch_json=fetch_json,
        sleep=lambda _: None,
    )

    quotes = provider.fetch_realtime_quotes()

    assert [quote.code for quote in quotes] == ["000001", "000002", "600000"]
    assert all(quote.last_price > 0 for quote in quotes)
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_free_provider_rejects_a_partial_quote_snapshot() -> None:
    def fetch_json(url: str) -> dict[str, object]:
        page = parse_qs(urlparse(url).query)["pn"][0]
        if page == "1":
            return {
                "data": {
                    "total": 3,
                    "diff": [_quote_row("000001", "平安银行", 11.2), _quote_row("000002", "万科A", 7.8)],
                }
            }
        return {"data": {"total": 3, "diff": []}}

    provider = EastmoneyFreeProvider(
        page_size=2,
        min_expected_symbols=3,
        raw_snapshot_directory=None,
        fetch_json=fetch_json,
        sleep=lambda _: None,
    )

    with pytest.raises(SnapshotIncompleteError, match="Fetched 2 quotes"):
        provider.fetch_realtime_quotes()


def test_free_provider_loads_daily_history_only_for_shortlisted_codes() -> None:
    seen_urls: list[str] = []

    def fetch_json(url: str) -> dict[str, object]:
        seen_urls.append(url)
        bars = [
            f"2026-06-{day:02d},10.0,10.1,10.3,9.9,1000000,10000000,1.0,1.0,0.1,0.0"
            for day in range(1, 26)
        ]
        return {"data": {"klines": bars}}

    provider = EastmoneyFreeProvider(
        raw_snapshot_directory=None,
        fetch_json=fetch_json,
        sleep=lambda _: None,
    )

    contexts = provider.fetch_research_contexts(("000001",), datetime(2026, 7, 14))

    assert len(contexts["000001"].daily_bars) == 25
    assert "secid=0.000001" in seen_urls[0]
