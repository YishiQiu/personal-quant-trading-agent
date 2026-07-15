"""Deterministic, configurable candidate funnel."""

from trading_agent.market_scanner.service import MarketScanner
from trading_agent.market_scanner.pattern_gate import PatternGate

__all__ = ["MarketScanner", "PatternGate"]
