from __future__ import annotations

from datetime import datetime

import pytest

from trading_agent.config import MarketScannerConfig
from trading_agent.domain.models import QuoteSnapshot


@pytest.fixture
def scanner_config() -> MarketScannerConfig:
    return MarketScannerConfig(
        exclude_st=True,
        exclude_delisting=True,
        min_price=3.0,
        max_price=100.0,
        min_turnover_amount=100_000_000,
        max_abs_pct_change=9.5,
        max_candidates=2,
        include_chinext=True,
        include_star_market=True,
    )


@pytest.fixture
def quote_factory():
    def create(**overrides: object) -> QuoteSnapshot:
        values: dict[str, object] = {
            "code": "000001",
            "name": "测试股份",
            "last_price": 10.0,
            "pct_change": 1.0,
            "turnover_amount": 200_000_000.0,
            "volume": 20_000_000.0,
            "observed_at": datetime(2026, 7, 13, 14, 30),
        }
        values.update(overrides)
        return QuoteSnapshot(**values)  # type: ignore[arg-type]

    return create
