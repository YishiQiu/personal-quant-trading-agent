"""Vendor-neutral news boundaries used after the deterministic pattern funnel."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Sequence

from trading_agent.domain.models import NewsItem


class NewsProviderError(RuntimeError):
    """A bounded news-provider failure that must not erase market research."""


@dataclass(frozen=True, slots=True)
class NewsTarget:
    code: str
    name: str


class NewsProvider(ABC):
    """One source of attributable candidate-level news or announcements."""

    name: str

    @abstractmethod
    def fetch(self, targets: Sequence[NewsTarget], since: datetime, until: datetime) -> Sequence[NewsItem]:
        """Return source-attributed items; providers must not invent ticker mappings."""
