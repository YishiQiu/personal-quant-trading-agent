"""Deterministic provider for local development and API smoke tests."""

from __future__ import annotations

from datetime import datetime, timedelta

from trading_agent.domain.models import (
    CapitalFlowSnapshot,
    DailyBar,
    FundamentalSnapshot,
    NewsItem,
    QuoteSnapshot,
    ResearchContext,
    SectorSnapshot,
)
from trading_agent.providers.base import CandidateResearchProvider, MarketDataProvider


class DemoMarketDataProvider(MarketDataProvider, CandidateResearchProvider):
    name = "demo"

    def fetch_realtime_quotes(self) -> tuple[QuoteSnapshot, ...]:
        now = datetime.now().astimezone()
        return (
            QuoteSnapshot(
                "000001", "平安银行", 11.20, 1.35, 1_280_000_000, 114_000_000, now,
                open_price=11.19, high_price=11.60, low_price=10.80, previous_close=11.05,
            ),
            QuoteSnapshot(
                "300001", "特锐德", 18.00, 0.05, 730_000_000, 40_000_000, now,
                open_price=17.95, high_price=18.00, low_price=17.10, previous_close=17.99,
            ),
            QuoteSnapshot(
                "600519", "贵州茅台", 1_465.0, 0.42, 2_500_000_000, 1_700_000, now,
                open_price=1_458.0, high_price=1_470.0, low_price=1_450.0, previous_close=1_458.9,
            ),
            QuoteSnapshot(
                "600001", "示例ST", 5.15, 0.20, 180_000_000, 35_000_000, now,
                open_price=5.10, high_price=5.20, low_price=5.00, previous_close=5.14, is_st=True,
            ),
            QuoteSnapshot(
                "000002", "低流动性样本", 8.50, 0.10, 20_000_000, 2_300_000, now,
                open_price=8.48, high_price=8.55, low_price=8.42, previous_close=8.49,
            ),
            QuoteSnapshot(
                "000003", "涨停样本", 9.10, 10.00, 600_000_000, 66_000_000, now,
                open_price=8.30, high_price=9.10, low_price=8.30, previous_close=8.27,
            ),
        )

    def fetch_research_contexts(
        self, codes: tuple[str, ...] | list[str], as_of: datetime
    ) -> dict[str, ResearchContext]:
        contexts: dict[str, ResearchContext] = {}
        for code in codes:
            bars = self._daily_bars(as_of)
            contexts[code] = ResearchContext(
                code=code,
                daily_bars=bars,
                news=(
                    NewsItem(
                        headline="示例行业政策推动数字化基础设施建设",
                        published_at=as_of - timedelta(hours=2),
                        source="demo",
                        url="https://example.invalid/demo-news",
                        related_codes=(code,),
                        related_themes=("数字经济",),
                    ),
                ),
                sector=SectorSnapshot(
                    industry="示例行业", concepts=("数字经济",), sector_heat=72.0, sector_flow_score=65.0
                ),
                fundamentals=FundamentalSnapshot(pe_ttm=18.0, pb=1.2, roe=10.0, revenue_growth=8.0, profit_growth=6.0),
                capital_flow=CapitalFlowSnapshot(main_net_inflow=24_000_000, northbound_net_inflow=4_000_000),
            )
        return contexts

    @staticmethod
    def _daily_bars(as_of: datetime) -> tuple[DailyBar, ...]:
        bars: list[DailyBar] = []
        for offset in range(30, 0, -1):
            close = 10.0 + (30 - offset) * 0.045
            bars.append(
                DailyBar(
                    trade_date=as_of - timedelta(days=offset),
                    open_price=close - 0.08,
                    high_price=close + 0.12,
                    low_price=close - 0.16,
                    close_price=close,
                    volume=75_000_000 + (30 - offset) * 400_000,
                    turnover_amount=800_000_000 + (30 - offset) * 5_000_000,
                )
            )
        return tuple(bars)
