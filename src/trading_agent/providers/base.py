"""Interfaces that prevent vendor details leaking into agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from trading_agent.domain.models import QuoteSnapshot, ResearchContext


class MarketDataProvider(ABC):
    """Provider plugin for normalized market data."""

    name: str

    @abstractmethod
    def fetch_realtime_quotes(self) -> Sequence[QuoteSnapshot]:
        """Return normalized A-share quotes for the current market snapshot."""


class CandidateResearchProvider(ABC):
    """Bulk enrichment boundary; never call one external API per agent."""

    @abstractmethod
    def fetch_research_contexts(
        self, codes: Sequence[str], as_of: datetime
    ) -> dict[str, ResearchContext]:
        """Return history, news, sector, capital-flow and fundamentals by code."""
