"""Agent adapter around the deterministic scanner service."""

from __future__ import annotations

from collections.abc import Sequence

from trading_agent.agents.base import AgentOutput
from trading_agent.domain.models import QuoteSnapshot, ScanResult
from trading_agent.market_scanner.service import MarketScanner


class MarketScannerAgent:
    name = "market_scanner"

    def __init__(self, scanner: MarketScanner) -> None:
        self._scanner = scanner

    def run(self, quotes: Sequence[QuoteSnapshot]) -> AgentOutput[ScanResult]:
        result = self._scanner.scan(quotes)
        return AgentOutput(
            agent_name=self.name,
            score=None,
            confidence=1.0,
            evidence=(f"Scanned {result.scanned_count} quotes", f"Kept {len(result.candidates)} candidates"),
            payload=result,
        )
