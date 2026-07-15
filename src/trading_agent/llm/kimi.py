"""Backward-compatible Kimi alias for the generic OpenAI-compatible adapter."""

from trading_agent.llm.openai_compatible import (
    LlmProviderResearchError as KimiResearchError,
)
from trading_agent.llm.openai_compatible import (
    OpenAiCompatibleLlmResearchClient as KimiLlmResearchClient,
)

__all__ = ["KimiLlmResearchClient", "KimiResearchError"]
