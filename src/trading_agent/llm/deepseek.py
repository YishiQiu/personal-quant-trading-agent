"""通用 OpenAI 兼容研究适配器的 DeepSeek 别名。"""

from trading_agent.llm.openai_compatible import (
    LlmProviderResearchError as DeepSeekResearchError,
)
from trading_agent.llm.openai_compatible import (
    OpenAiCompatibleLlmResearchClient as DeepSeekLlmResearchClient,
)

__all__ = ["DeepSeekLlmResearchClient", "DeepSeekResearchError"]
