from __future__ import annotations

import pytest

from trading_agent.bootstrap import build_provider_registry
from trading_agent.config import MarketScannerConfig
from trading_agent.config_news import load_news_config
from trading_agent.providers.demo import DemoMarketDataProvider
from trading_agent.providers.registry import ProviderRegistry


def test_config_rejects_invalid_price_range() -> None:
    with pytest.raises(ValueError, match="max_price"):
        MarketScannerConfig.from_mapping(
            {
                "exclude_st": True,
                "exclude_delisting": True,
                "min_price": 10,
                "max_price": 10,
                "min_turnover_amount": 1,
                "max_abs_pct_change": 9.5,
                "max_candidates": 1,
            }
        )


def test_registry_creates_registered_provider() -> None:
    registry = ProviderRegistry()
    registry.register(DemoMarketDataProvider)

    assert registry.names == ("demo",)
    assert registry.create("DEMO").name == "demo"


def test_default_registry_exposes_the_dependency_free_provider() -> None:
    registry = build_provider_registry()

    assert "eastmoney_free" in registry.names
    assert "sina_free" in registry.names


def test_default_news_config_uses_free_sources_without_paid_tushare_news() -> None:
    config = load_news_config("configs/news.yaml")

    assert config.cninfo.enabled is True
    assert config.eastmoney_stock_news.enabled is True
    assert config.tushare.enabled is False
