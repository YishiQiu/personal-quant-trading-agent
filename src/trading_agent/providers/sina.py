"""Low-frequency Sina public-source fallback for completed A-share daily bars.

The quote-list endpoint is useful before the next session opens: its 15:30 quote
snapshot contains the preceding completed daily candle.  It is a fallback, not a
guaranteed or licensed production feed, and never touches Kimi or 同花顺 data.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, time as clock_time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from trading_agent.domain.models import DailyBar, QuoteSnapshot, ResearchContext
from trading_agent.providers.base import CandidateResearchProvider, MarketDataProvider
from trading_agent.providers.eastmoney import FreeDataProviderError, SnapshotIncompleteError

TextFetcher = Callable[[str], str]
Sleep = Callable[[float], None]
Clock = Callable[[], datetime]
JsonObject = Mapping[str, Any]


class SinaFreeProvider(MarketDataProvider, CandidateResearchProvider):
    """Fetch a validated latest completed daily snapshot from Sina public endpoints.

    Use this provider for a pre-open replay of the preceding trading day's close.
    It should not be used as a claim of a realtime, licensed market-data service.
    """

    name = "sina_free"

    _QUOTE_ENDPOINT = (
        "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        "Market_Center.getHQNodeData"
    )
    _HISTORY_ENDPOINT_PREFIX = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_KLC_KL_"

    def __init__(
        self,
        *,
        page_size: int = 100,
        min_expected_symbols: int = 5_000,
        max_pages: int = 100,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0,
        page_interval_seconds: float = 0.4,
        raw_snapshot_directory: str | Path | None = Path("data/raw_snapshots"),
        snapshot_path: str | Path | None = None,
        fetch_text: TextFetcher | None = None,
        sleep: Sleep = time.sleep,
        now: Clock | None = None,
    ) -> None:
        if min(page_size, min_expected_symbols, max_pages, max_retries) <= 0:
            raise ValueError("page size, expected symbols, pages and retries must be positive")
        if retry_delay_seconds < 0 or page_interval_seconds < 0:
            raise ValueError("retry and page intervals cannot be negative")
        self._page_size = page_size
        self._min_expected_symbols = min_expected_symbols
        self._max_pages = max_pages
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds
        self._page_interval_seconds = page_interval_seconds
        self._raw_snapshot_directory = (
            Path(raw_snapshot_directory) if raw_snapshot_directory is not None else None
        )
        self._snapshot_path = Path(snapshot_path) if snapshot_path is not None else None
        self._fetch_text = fetch_text or _urlopen_text
        self._sleep = sleep
        self._now = now or (lambda: datetime.now().astimezone())

    def fetch_realtime_quotes(self) -> tuple[QuoteSnapshot, ...]:
        """Return the newest available quote snapshot after a complete pagination pass."""

        if self._snapshot_path is not None:
            return self._load_cached_snapshot()

        raw_pages: list[list[JsonObject]] = []
        rows: list[JsonObject] = []
        for page in range(1, self._max_pages + 1):
            if page > 1:
                self._sleep(self._page_interval_seconds)
            page_rows = self._fetch_quote_page(page)
            if len(page_rows) > self._page_size:
                raise SnapshotIncompleteError(f"Sina page {page} exceeded its requested size")
            if len(page_rows) < self._page_size:
                # The endpoint lacks a total field. Re-fetching the final short
                # page prevents a transient empty response from masquerading as
                # the end of the universe.
                confirmation = self._fetch_quote_page(page)
                if _codes(page_rows) != _codes(confirmation):
                    raise SnapshotIncompleteError("Sina final quote page was not stable")
                raw_pages.append(page_rows)
                rows.extend(page_rows)
                break
            raw_pages.append(page_rows)
            rows.extend(page_rows)
        else:
            raise SnapshotIncompleteError("Sina quote pagination exceeded the configured page limit")

        observed_at = self._now()
        is_final_bar = _latest_bar_is_final(observed_at)
        quotes = tuple(_quote_from_row(row, observed_at, is_final_bar) for row in rows)
        self._validate_snapshot(quotes)
        # An intraday response is useful only for an explicitly chosen future
        # realtime provider. It must never replace yesterday's completed bar.
        if is_final_bar:
            self._persist_raw_snapshot(observed_at, raw_pages)
        return quotes

    def _load_cached_snapshot(self) -> tuple[QuoteSnapshot, ...]:
        assert self._snapshot_path is not None
        try:
            document = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
            observed_at = datetime.fromisoformat(str(document["observed_at"]))
            pages = document["pages"]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise FreeDataProviderError(f"Cannot read Sina snapshot: {self._snapshot_path}") from exc
        if not isinstance(document, Mapping) or document.get("provider") != self.name:
            raise FreeDataProviderError(f"Snapshot is not from provider '{self.name}'")
        if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
            raise FreeDataProviderError("Sina snapshot has no page list")
        rows = [row for page in pages for row in page]
        if not all(isinstance(row, Mapping) for row in rows):
            raise FreeDataProviderError("Sina snapshot has invalid quote rows")
        # A persisted snapshot is immutable evidence of a completed capture;
        # replay must not inherit the current wall-clock session flag.
        quotes = tuple(_quote_from_row(row, observed_at, True) for row in rows)
        self._validate_snapshot(quotes)
        return quotes

    def fetch_research_contexts(
        self, codes: Sequence[str], as_of: datetime
    ) -> dict[str, ResearchContext]:
        """Fetch up to 300 completed daily bars for the already-shortlisted stocks."""

        contexts: dict[str, ResearchContext] = {}
        for code in codes:
            payload = self._fetch_with_retry(self._history_url(code))
            contexts[code] = ResearchContext(
                code=code,
                daily_bars=tuple(_daily_bar(row, code) for row in _history_rows(payload, code)),
            )
        return contexts

    def _fetch_quote_page(self, page: int) -> list[JsonObject]:
        payload = self._fetch_with_retry(self._quote_url(page))
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise FreeDataProviderError("Sina quote endpoint returned invalid JSON") from exc
        if not isinstance(parsed, list) or not all(isinstance(row, Mapping) for row in parsed):
            raise FreeDataProviderError("Sina quote endpoint returned no quote list")
        return list(parsed)

    def _quote_url(self, page: int) -> str:
        query = urlencode(
            {
                "page": page,
                "num": self._page_size,
                "sort": "symbol",
                "asc": 1,
                "node": "hs_a",
                "symbol": "",
                "_s_r_a": "page",
            }
        )
        return f"{self._QUOTE_ENDPOINT}?{query}"

    def _history_url(self, code: str) -> str:
        symbol = _sina_symbol(code)
        query = urlencode({"symbol": symbol, "scale": 240, "ma": "no", "datalen": 300})
        return f"{self._HISTORY_ENDPOINT_PREFIX}{symbol}=/CN_MarketDataService.getKLineData?{query}"

    def _fetch_with_retry(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                payload = self._fetch_text(url)
                if not payload.strip():
                    raise FreeDataProviderError("Sina public endpoint returned an empty response")
                return payload
            except (FreeDataProviderError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < self._max_retries:
                    self._sleep(self._retry_delay_seconds * (2**attempt))
        raise FreeDataProviderError("Sina public endpoint was unavailable after bounded retries") from last_error

    def _validate_snapshot(self, quotes: Sequence[QuoteSnapshot]) -> None:
        if len(quotes) < self._min_expected_symbols:
            raise SnapshotIncompleteError(
                f"Fetched {len(quotes)} Sina quotes; expected at least {self._min_expected_symbols}"
            )
        codes = [quote.code for quote in quotes]
        if len(set(codes)) != len(codes):
            raise SnapshotIncompleteError("Duplicate security codes in Sina quote snapshot")
        valid_quotes = sum(quote.last_price > 0 and quote.turnover_amount >= 0 for quote in quotes)
        if valid_quotes / len(quotes) < 0.95:
            raise SnapshotIncompleteError("More than 5% of Sina quotes have unusable price fields")

    def _persist_raw_snapshot(self, observed_at: datetime, pages: Sequence[Sequence[JsonObject]]) -> None:
        if self._raw_snapshot_directory is None:
            return
        self._raw_snapshot_directory.mkdir(parents=True, exist_ok=True)
        target = self._raw_snapshot_directory / observed_at.strftime("sina-%Y%m%dT%H%M%S%z.json")
        document = {
            "provider": self.name,
            "observed_at": observed_at.isoformat(),
            "page_count": len(pages),
            "pages": pages,
        }
        target.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")


def _urlopen_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "application/json, application/javascript, text/plain, */*",
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": "PersonalQuantTradingAgent/0.1 (+local-research)",
        },
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310 - module-constant public source
        raw = response.read()
    return raw.decode("gbk")


def _quote_from_row(row: JsonObject, observed_at: datetime, is_final_bar: bool) -> QuoteSnapshot:
    code = str(row.get("code", "")).zfill(6)
    if len(code) != 6 or not code.isdigit():
        raise SnapshotIncompleteError(f"Invalid code in Sina quote row: {code!r}")
    name = str(row.get("name", "")).strip()
    if not name:
        raise SnapshotIncompleteError(f"Missing name for {code}")
    return QuoteSnapshot(
        code=code,
        name=name,
        last_price=_number(row.get("trade")) or 0.0,
        pct_change=_number(row.get("changepercent")) or 0.0,
        turnover_amount=_number(row.get("amount")) or 0.0,
        volume=_number(row.get("volume")) or 0.0,
        observed_at=observed_at,
        open_price=_number(row.get("open")),
        high_price=_number(row.get("high")),
        low_price=_number(row.get("low")),
        previous_close=_number(row.get("settlement")),
        is_st="ST" in name.upper(),
        is_delisting="退" in name,
        is_final_bar=is_final_bar,
    )


def _history_rows(payload: str, code: str) -> list[JsonObject]:
    start, end = payload.find("["), payload.rfind("]")
    if start < 0 or end <= start:
        raise FreeDataProviderError(f"Sina history response for {code} has no K-line list")
    try:
        parsed = json.loads(payload[start : end + 1])
    except json.JSONDecodeError as exc:
        raise FreeDataProviderError(f"Sina history response for {code} is invalid") from exc
    if not isinstance(parsed, list) or not all(isinstance(row, Mapping) for row in parsed):
        raise FreeDataProviderError(f"Sina history response for {code} has invalid K-line rows")
    return list(parsed)


def _daily_bar(row: JsonObject, code: str) -> DailyBar:
    try:
        return DailyBar(
            trade_date=datetime.fromisoformat(str(row["day"])),
            open_price=float(row["open"]),
            high_price=float(row["high"]),
            low_price=float(row["low"]),
            close_price=float(row["close"]),
            volume=float(row["volume"]),
            # This public K-line response has no amount field. It is kept at
            # zero rather than fabricated; turnover-dependent agents need a
            # richer provider before they can use historical turnover.
            turnover_amount=0.0,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FreeDataProviderError(f"Invalid Sina daily-bar fields for {code}") from exc


def _sina_symbol(code: str) -> str:
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"Invalid A-share code: {code}")
    if code.startswith(("5", "6", "9")):
        return f"sh{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return f"sz{code}"


def _codes(rows: Sequence[JsonObject]) -> tuple[str, ...]:
    return tuple(str(row.get("code", "")) for row in rows)


def _number(value: object) -> float | None:
    try:
        if value is None or str(value).lower() in {"nan", "-"}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_bar_is_final(observed_at: datetime) -> bool:
    """A quote read before auction or after close represents the prior completed bar."""

    if observed_at.weekday() >= 5:
        return True
    local_time = observed_at.timetz().replace(tzinfo=None)
    return local_time < clock_time(9, 15) or local_time >= clock_time(15, 0)
