"""Dependency-free Eastmoney public-data provider with strict completeness checks.

This adapter is deliberately conservative: it returns a full, auditable snapshot or
raises an error. A partial public response must never enter the recommendation flow.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from trading_agent.domain.models import DailyBar, QuoteSnapshot, ResearchContext
from trading_agent.providers.base import CandidateResearchProvider, MarketDataProvider

JsonObject = Mapping[str, Any]
JsonFetcher = Callable[[str], JsonObject]
Sleep = Callable[[float], None]


class FreeDataProviderError(RuntimeError):
    """Base error for a public-data fetch that cannot safely be used."""


class SnapshotIncompleteError(FreeDataProviderError):
    """The public endpoint did not provide a complete, internally valid universe."""


class EastmoneyFreeProvider(MarketDataProvider, CandidateResearchProvider):
    """Free public-source provider for one 14:30 snapshot and shortlisted daily bars.

    It does not consume Kimi, 同花顺, or any `*_ths` source. It uses the Eastmoney
    public quote and daily-K endpoints only. Upstream terms and availability still
    need periodic review before unattended long-term use.
    """

    name = "eastmoney_free"

    _QUOTE_ENDPOINT = "https://push2.eastmoney.com/api/qt/clist/get"
    _HISTORY_ENDPOINT = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    _QUOTE_FIELDS = "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f22,f23"
    _QUOTE_MARKETS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"

    def __init__(
        self,
        *,
        page_size: int = 100,
        min_expected_symbols: int = 5_000,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0,
        page_interval_seconds: float = 0.4,
        raw_snapshot_directory: str | Path | None = Path("data/raw_snapshots"),
        fetch_json: JsonFetcher | None = None,
        sleep: Sleep = time.sleep,
    ) -> None:
        if page_size <= 0 or min_expected_symbols <= 0 or max_retries <= 0:
            raise ValueError("page size, expected symbols and retries must be positive")
        if retry_delay_seconds < 0 or page_interval_seconds < 0:
            raise ValueError("retry and page intervals cannot be negative")
        self._page_size = page_size
        self._min_expected_symbols = min_expected_symbols
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds
        self._page_interval_seconds = page_interval_seconds
        self._raw_snapshot_directory = (
            Path(raw_snapshot_directory) if raw_snapshot_directory is not None else None
        )
        self._fetch_json = fetch_json or _urlopen_json
        self._sleep = sleep

    def fetch_realtime_quotes(self) -> tuple[QuoteSnapshot, ...]:
        """Fetch all pages sequentially, validate them, then persist one raw snapshot."""

        first_page = self._fetch_with_retry(self._quote_url(page=1))
        first_data = _data_mapping(first_page)
        total = _positive_int(first_data.get("total"), "quote total")
        pages = math.ceil(total / self._page_size)
        page_payloads = [first_page]
        rows = _quote_rows(first_data)
        for page in range(2, pages + 1):
            # The public endpoint can reset a connection when hit as a tight
            # pagination burst.  A small deterministic pace is cheaper and
            # safer than parallel requests; 56 pages finish in about 25s.
            self._sleep(self._page_interval_seconds)
            payload = self._fetch_with_retry(self._quote_url(page=page))
            page_payloads.append(payload)
            rows.extend(_quote_rows(_data_mapping(payload)))

        observed_at = datetime.now().astimezone()
        quotes = tuple(_quote_from_row(row, observed_at) for row in rows)
        self._validate_snapshot(quotes, expected_total=total)
        self._persist_raw_snapshot(observed_at, total, page_payloads)
        return quotes

    def fetch_research_contexts(
        self, codes: Sequence[str], as_of: datetime
    ) -> dict[str, ResearchContext]:
        """Load completed daily bars only after the candidate pool is formed."""

        contexts: dict[str, ResearchContext] = {}
        for code in codes:
            payload = self._fetch_with_retry(self._history_url(code, as_of))
            data = _data_mapping(payload)
            raw_bars = data.get("klines")
            if not isinstance(raw_bars, list):
                raise FreeDataProviderError(f"History response for {code} has no kline list")
            bars = tuple(_daily_bar(item, code) for item in raw_bars)
            contexts[code] = ResearchContext(code=code, daily_bars=bars)
        return contexts

    def _quote_url(self, *, page: int) -> str:
        query = urlencode(
            {
                "pn": page,
                "pz": self._page_size,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f12",
                "fs": self._QUOTE_MARKETS,
                "fields": self._QUOTE_FIELDS,
            }
        )
        return f"{self._QUOTE_ENDPOINT}?{query}"

    def _history_url(self, code: str, as_of: datetime) -> str:
        beginning = (as_of - timedelta(days=400)).strftime("%Y%m%d")
        query = urlencode(
            {
                "secid": _security_id(code),
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": 101,
                "fqt": 1,
                "beg": beginning,
                "end": "20500101",
                "lmt": 300,
            }
        )
        return f"{self._HISTORY_ENDPOINT}?{query}"

    def _fetch_with_retry(self, url: str) -> JsonObject:
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                payload = self._fetch_json(url)
                if not isinstance(payload, Mapping):
                    raise FreeDataProviderError("Public endpoint returned a non-object JSON payload")
                return payload
            except (FreeDataProviderError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < self._max_retries:
                    self._sleep(self._retry_delay_seconds * (2**attempt))
        raise FreeDataProviderError("Public endpoint was unavailable after bounded retries") from last_error

    def _validate_snapshot(self, quotes: Sequence[QuoteSnapshot], *, expected_total: int) -> None:
        codes = [quote.code for quote in quotes]
        if expected_total < self._min_expected_symbols:
            raise SnapshotIncompleteError(
                f"Provider reported {expected_total} symbols; expected at least {self._min_expected_symbols}"
            )
        if len(quotes) != expected_total:
            raise SnapshotIncompleteError(
                f"Fetched {len(quotes)} quotes but provider reported {expected_total} symbols"
            )
        if len(set(codes)) != len(codes):
            raise SnapshotIncompleteError("Duplicate security codes in public quote snapshot")
        valid_quotes = sum(quote.last_price > 0 and quote.turnover_amount >= 0 for quote in quotes)
        if valid_quotes / len(quotes) < 0.95:
            raise SnapshotIncompleteError("More than 5% of quotes have unusable price fields")

    def _persist_raw_snapshot(
        self, observed_at: datetime, total: int, pages: Sequence[JsonObject]
    ) -> None:
        if self._raw_snapshot_directory is None:
            return
        self._raw_snapshot_directory.mkdir(parents=True, exist_ok=True)
        target = self._raw_snapshot_directory / observed_at.strftime("%Y%m%dT%H%M%S%z.json")
        document = {
            "provider": self.name,
            "observed_at": observed_at.isoformat(),
            "reported_total": total,
            "pages": pages,
        }
        target.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")


def _urlopen_json(url: str) -> JsonObject:
    request = Request(
        url,
        headers={
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
            "User-Agent": "PersonalQuantTradingAgent/0.1 (+local-research)",
        },
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310 - endpoint is module constant
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise FreeDataProviderError("Public endpoint JSON root is not an object")
    return payload


def _data_mapping(payload: JsonObject) -> JsonObject:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise FreeDataProviderError("Public endpoint response has no data object")
    return data


def _quote_rows(data: JsonObject) -> list[JsonObject]:
    rows = data.get("diff")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise FreeDataProviderError("Public endpoint response has no quote list")
    return list(rows)


def _quote_from_row(row: JsonObject, observed_at: datetime) -> QuoteSnapshot:
    code = str(row.get("f12", "")).zfill(6)
    if len(code) != 6 or not code.isdigit():
        raise SnapshotIncompleteError(f"Invalid code in quote row: {code!r}")
    name = str(row.get("f14", "")).strip()
    if not name:
        raise SnapshotIncompleteError(f"Missing name for {code}")
    return QuoteSnapshot(
        code=code,
        name=name,
        # Suspended securities may have a missing price. Preserve the row for a
        # complete universe audit; the deterministic scanner will reject its 0 price.
        last_price=_number(row.get("f2")) or 0.0,
        pct_change=_number(row.get("f3")) or 0.0,
        turnover_amount=_number(row.get("f6")) or 0.0,
        volume=_number(row.get("f5")) or 0.0,
        observed_at=observed_at,
        open_price=_number(row.get("f17")),
        high_price=_number(row.get("f15")),
        low_price=_number(row.get("f16")),
        previous_close=_number(row.get("f18")),
        is_st="ST" in name.upper(),
        is_delisting="退" in name,
    )


def _daily_bar(item: object, code: str) -> DailyBar:
    if not isinstance(item, str):
        raise FreeDataProviderError(f"Invalid daily-bar record for {code}")
    values = item.split(",")
    if len(values) < 7:
        raise FreeDataProviderError(f"Incomplete daily-bar record for {code}")
    try:
        return DailyBar(
            trade_date=datetime.fromisoformat(values[0]),
            open_price=float(values[1]),
            close_price=float(values[2]),
            high_price=float(values[3]),
            low_price=float(values[4]),
            volume=float(values[5]),
            turnover_amount=float(values[6]),
        )
    except ValueError as exc:
        raise FreeDataProviderError(f"Invalid daily-bar fields for {code}") from exc


def _security_id(code: str) -> str:
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"Invalid A-share code: {code}")
    exchange = "1" if code.startswith(("5", "6", "9")) else "0"
    return f"{exchange}.{code}"


def _positive_int(value: object, label: str) -> int:
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise FreeDataProviderError(f"Invalid {label}") from exc
    if integer <= 0:
        raise FreeDataProviderError(f"Invalid {label}")
    return integer


def _number(value: object) -> float | None:
    try:
        if value is None or str(value).lower() in {"nan", "-"}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
