"""Pluggable market-data provider interfaces and built-in adapters."""

from trading_agent.providers.base import CandidateResearchProvider, MarketDataProvider
from trading_agent.providers.eastmoney import EastmoneyFreeProvider
from trading_agent.providers.registry import ProviderRegistry
from trading_agent.providers.sina import SinaFreeProvider

__all__ = [
    "CandidateResearchProvider",
    "EastmoneyFreeProvider",
    "MarketDataProvider",
    "ProviderRegistry",
    "SinaFreeProvider",
]
