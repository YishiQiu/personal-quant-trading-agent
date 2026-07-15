"""Strongly typed, vendor-neutral data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class QuoteSnapshot:
    """A normalized real-time A-share quote supplied by a provider plugin."""

    code: str
    name: str
    last_price: float
    pct_change: float
    turnover_amount: float
    volume: float
    observed_at: datetime
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    previous_close: float | None = None
    is_st: bool = False
    is_delisting: bool = False
    is_final_bar: bool = False


@dataclass(frozen=True, slots=True)
class Candidate:
    """A liquid stock that passed the deterministic market funnel."""

    quote: QuoteSnapshot
    liquidity_score: float


@dataclass(frozen=True, slots=True)
class Rejection:
    """An auditable exclusion from the market funnel."""

    quote: QuoteSnapshot
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Complete scanner outcome, including exclusions for later review."""

    scanned_at: datetime
    candidates: tuple[Candidate, ...]
    rejections: tuple[Rejection, ...] = field(default_factory=tuple)
    input_count: int | None = None

    @property
    def scanned_count(self) -> int:
        return self.input_count if self.input_count is not None else len(self.candidates) + len(self.rejections)


@dataclass(frozen=True, slots=True)
class DailyBar:
    """A completed daily OHLCV bar. Intraday bars must never be stored here."""

    trade_date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    turnover_amount: float


@dataclass(frozen=True, slots=True)
class NewsItem:
    """A raw, attributable news or announcement record."""

    headline: str
    published_at: datetime
    source: str
    # Tushare's major_news response contains attributed text but no canonical
    # article URL.  ``None`` is preferable to inventing a link.
    url: str | None = None
    related_codes: tuple[str, ...] = field(default_factory=tuple)
    related_themes: tuple[str, ...] = field(default_factory=tuple)
    summary: str | None = None


@dataclass(frozen=True, slots=True)
class FundamentalSnapshot:
    pe_ttm: float | None = None
    pb: float | None = None
    roe: float | None = None
    revenue_growth: float | None = None
    profit_growth: float | None = None


@dataclass(frozen=True, slots=True)
class CapitalFlowSnapshot:
    main_net_inflow: float | None = None
    northbound_net_inflow: float | None = None
    margin_balance_change: float | None = None


@dataclass(frozen=True, slots=True)
class SectorSnapshot:
    industry: str | None = None
    concepts: tuple[str, ...] = field(default_factory=tuple)
    sector_heat: float | None = None
    sector_flow_score: float | None = None


@dataclass(frozen=True, slots=True)
class ResearchContext:
    """All non-quote evidence required to research one shortlisted candidate."""

    code: str
    daily_bars: tuple[DailyBar, ...] = field(default_factory=tuple)
    news: tuple[NewsItem, ...] = field(default_factory=tuple)
    sector: SectorSnapshot = field(default_factory=SectorSnapshot)
    fundamentals: FundamentalSnapshot = field(default_factory=FundamentalSnapshot)
    capital_flow: CapitalFlowSnapshot = field(default_factory=CapitalFlowSnapshot)
