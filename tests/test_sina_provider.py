from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from trading_agent.providers.sina import SinaFreeProvider, _latest_bar_is_final


def _quote_row(code: str, name: str, price: float) -> dict[str, object]:
    return {
        "code": code,
        "name": name,
        "trade": str(price),
        "changepercent": 1.2,
        "amount": 180_000_000,
        "volume": 12_000_000,
        "open": str(price - 0.1),
        "high": str(price + 0.3),
        "low": str(price - 0.3),
        "settlement": str(price - 0.12),
    }


def test_sina_provider_returns_a_complete_final_bar_snapshot(tmp_path) -> None:
    def fetch_text(url: str) -> str:
        page = parse_qs(urlparse(url).query).get("page", ["1"])[0]
        if page == "1":
            return json.dumps([_quote_row("000001", "平安银行", 11.2), _quote_row("000002", "万科A", 7.8)])
        return json.dumps([_quote_row("600000", "浦发银行", 10.1)])

    provider = SinaFreeProvider(
        page_size=2,
        min_expected_symbols=3,
        raw_snapshot_directory=tmp_path,
        fetch_text=fetch_text,
        sleep=lambda _: None,
        now=lambda: datetime(2026, 7, 14, 8, 50),
    )

    quotes = provider.fetch_realtime_quotes()

    assert [quote.code for quote in quotes] == ["000001", "000002", "600000"]
    assert all(quote.is_final_bar is _latest_bar_is_final(quotes[0].observed_at) for quote in quotes)
    snapshot = next(tmp_path.glob("sina-*.json"))
    replay = SinaFreeProvider(
        min_expected_symbols=3,
        raw_snapshot_directory=None,
        snapshot_path=snapshot,
        fetch_text=fetch_text,
        sleep=lambda _: None,
    )

    assert len(replay.fetch_realtime_quotes()) == 3
    assert all(quote.is_final_bar for quote in replay.fetch_realtime_quotes())


def test_sina_provider_does_not_cache_an_intraday_snapshot(tmp_path) -> None:
    def fetch_text(url: str) -> str:
        return json.dumps([_quote_row("000001", "平安银行", 11.2)])

    provider = SinaFreeProvider(
        page_size=2,
        min_expected_symbols=1,
        raw_snapshot_directory=tmp_path,
        fetch_text=fetch_text,
        sleep=lambda _: None,
        now=lambda: datetime(2026, 7, 14, 10, 0),
    )

    quotes = provider.fetch_realtime_quotes()

    assert not quotes[0].is_final_bar
    assert not list(tmp_path.glob("sina-*.json"))


def test_sina_provider_parses_completed_daily_history() -> None:
    def fetch_text(url: str) -> str:
        rows = [
            {"day": f"2026-06-{day:02d}", "open": "10", "high": "10.3", "low": "9.9", "close": "10.1", "volume": "1000000"}
            for day in range(1, 26)
        ]
        return f"var kline=({json.dumps(rows)});"

    provider = SinaFreeProvider(raw_snapshot_directory=None, fetch_text=fetch_text, sleep=lambda _: None)

    contexts = provider.fetch_research_contexts(("600000",), datetime(2026, 7, 14))

    assert len(contexts["600000"].daily_bars) == 25
    assert contexts["600000"].daily_bars[-1].turnover_amount == 0.0
    assert "sh600000" in provider._history_url("600000")
