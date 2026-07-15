"""确定性筛选后才会使用的可选模型适配器。"""

from trading_agent.llm.deepseek import DeepSeekLlmResearchClient
from trading_agent.llm.kimi import KimiLlmResearchClient

__all__ = ["DeepSeekLlmResearchClient", "KimiLlmResearchClient"]
