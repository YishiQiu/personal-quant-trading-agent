"""与数据厂商无关的强类型数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class QuoteSnapshot:
    """由数据源插件提供并完成标准化的 A 股行情快照。"""

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
    """通过确定性市场漏斗的流动性候选股。"""

    quote: QuoteSnapshot
    liquidity_score: float


@dataclass(frozen=True, slots=True)
class Rejection:
    """市场漏斗中可追溯的排除记录。"""

    quote: QuoteSnapshot
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScanResult:
    """完整扫描结果，同时保留排除项方便复核。"""

    scanned_at: datetime
    candidates: tuple[Candidate, ...]
    rejections: tuple[Rejection, ...] = field(default_factory=tuple)
    input_count: int | None = None

    @property
    def scanned_count(self) -> int:
        return self.input_count if self.input_count is not None else len(self.candidates) + len(self.rejections)


@dataclass(frozen=True, slots=True)
class DailyBar:
    """已经收盘的日线 OHLCV；盘中数据不能存入这里。"""

    trade_date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    turnover_amount: float


@dataclass(frozen=True, slots=True)
class NewsItem:
    """保留原始来源的新闻或公告记录。"""

    headline: str
    published_at: datetime
    source: str
    # Tushare major_news 只有带来源的正文，没有统一原文链接；宁可保留 None，也不伪造链接。
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
    """研究单只入围股票所需的全部非行情证据。"""

    code: str
    daily_bars: tuple[DailyBar, ...] = field(default_factory=tuple)
    news: tuple[NewsItem, ...] = field(default_factory=tuple)
    sector: SectorSnapshot = field(default_factory=SectorSnapshot)
    fundamentals: FundamentalSnapshot = field(default_factory=FundamentalSnapshot)
    capital_flow: CapitalFlowSnapshot = field(default_factory=CapitalFlowSnapshot)
