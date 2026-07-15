"""为兼容旧配置保留的 Kimi 适配器别名。"""

from trading_agent.llm.openai_compatible import (
    LlmProviderResearchError as KimiResearchError,
)
from trading_agent.llm.openai_compatible import (
    OpenAiCompatibleLlmResearchClient as KimiLlmResearchClient,
)

__all__ = ["KimiLlmResearchClient", "KimiResearchError"]
