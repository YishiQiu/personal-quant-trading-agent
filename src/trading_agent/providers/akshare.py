"""Optional AKShare adapter for the 14:30 all-market snapshot."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from trading_agent.domain.models import DailyBar, QuoteSnapshot, ResearchContext
from trading_agent.providers.base import CandidateResearchProvider, MarketDataProvider


class AkShareMarketDataProvider(MarketDataProvider, CandidateResearchProvider):
    """Normalizes ``stock_zh_a_spot_em`` without leaking DataFrames upstream."""

    name = "akshare"

    def fetch_realtime_quotes(self) -> tuple[QuoteSnapshot, ...]:
        try:
            import akshare as ak
        except ImportError as exc:  # pragma: no cover - optional integration
            raise RuntimeError('Install the data extra: pip install -e ".[data]"') from exc

        dataframe = ak.stock_zh_a_spot_em()
        observed_at = datetime.now().astimezone()
        quotes: list[QuoteSnapshot] = []
        for row in dataframe.to_dict(orient="records"):
            code = str(row["代码"]).zfill(6)
            name = str(row["名称"])
            quotes.append(
                QuoteSnapshot(
                    code=code,
                    name=name,
                    last_price=_number(row.get("最新价")) or 0.0,
                    pct_change=_number(row.get("涨跌幅")) or 0.0,
                    turnover_amount=_number(row.get("成交额")) or 0.0,
                    volume=_number(row.get("成交量")) or 0.0,
                    observed_at=observed_at,
                    open_price=_number(row.get("今开")),
                    high_price=_number(row.get("最高")),
                    low_price=_number(row.get("最低")),
                    previous_close=_number(row.get("昨收")),
                    is_st="ST" in name.upper(),
                    is_delisting="退" in name,
                )
            )
        return tuple(quotes)

    def fetch_research_contexts(
        self, codes: tuple[str, ...] | list[str], as_of: datetime
    ) -> dict[str, ResearchContext]:
        """Fetch completed daily bars only; enrichment is supplied by later provider plugins."""

        try:
            import akshare as ak
        except ImportError as exc:  # pragma: no cover - optional integration
            raise RuntimeError('Install the data extra: pip install -e ".[data]"') from exc
        start_date = (as_of - timedelta(days=400)).strftime("%Y%m%d")
        end_date = as_of.strftime("%Y%m%d")
        contexts: dict[str, ResearchContext] = {}
        for code in codes:
            dataframe = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            bars = tuple(
                DailyBar(
                    trade_date=datetime.fromisoformat(str(row["日期"])),
                    open_price=_number(row.get("开盘")) or 0.0,
                    high_price=_number(row.get("最高")) or 0.0,
                    low_price=_number(row.get("最低")) or 0.0,
                    close_price=_number(row.get("收盘")) or 0.0,
                    volume=_number(row.get("成交量")) or 0.0,
                    turnover_amount=_number(row.get("成交额")) or 0.0,
                )
                for row in dataframe.to_dict(orient="records")
            )
            contexts[code] = ResearchContext(code=code, daily_bars=bars)
        return contexts


def _number(value: Any) -> float | None:
    try:
        if value is None or str(value).lower() == "nan":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
