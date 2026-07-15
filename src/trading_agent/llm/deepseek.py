"""DeepSeek alias for the generic OpenAI-compatible research adapter."""

from trading_agent.llm.openai_compatible import (
    LlmProviderResearchError as DeepSeekResearchError,
)
from trading_agent.llm.openai_compatible import (
    OpenAiCompatibleLlmResearchClient as DeepSeekLlmResearchClient,
)

__all__ = ["DeepSeekLlmResearchClient", "DeepSeekResearchError"]
