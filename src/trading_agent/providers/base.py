"""隔离数据厂商细节，避免它们渗透到 Agent 层。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from trading_agent.domain.models import QuoteSnapshot, ResearchContext


class MarketDataProvider(ABC):
    """标准化行情数据插件接口。"""

    name: str

    @abstractmethod
    def fetch_realtime_quotes(self) -> Sequence[QuoteSnapshot]:
        """返回当前市场快照对应的标准化 A 股行情。"""


class CandidateResearchProvider(ABC):
    """批量补充研究信息的边界，禁止每个 Agent 各自调用外部接口。"""

    @abstractmethod
    def fetch_research_contexts(
        self, codes: Sequence[str], as_of: datetime
    ) -> dict[str, ResearchContext]:
        """按股票代码返回历史、新闻、板块、资金流和基本面信息。"""
