"""确定性形态筛选完成后使用的、与数据厂商无关的新闻接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Sequence

from trading_agent.domain.models import NewsItem


class NewsProviderError(RuntimeError):
    """可控的新闻源异常，不能因此丢弃已经完成的行情研究。"""


@dataclass(frozen=True, slots=True)
class NewsTarget:
    code: str
    name: str


class NewsProvider(ABC):
    """为候选股提供可追溯新闻或公告的单一数据源。"""

    name: str

    @abstractmethod
    def fetch(self, targets: Sequence[NewsTarget], since: datetime, until: datetime) -> Sequence[NewsItem]:
        """返回带来源的记录；数据源不得猜测股票映射关系。"""
