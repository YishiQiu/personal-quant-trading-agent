"""Adapters for optional model providers used only after deterministic filtering."""

from trading_agent.llm.deepseek import DeepSeekLlmResearchClient
from trading_agent.llm.kimi import KimiLlmResearchClient

__all__ = ["DeepSeekLlmResearchClient", "KimiLlmResearchClient"]
