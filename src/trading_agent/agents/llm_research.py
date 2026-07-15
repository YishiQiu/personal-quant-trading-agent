"""大模型调用边界；模型可选，但必须返回结构化、可追溯的数据。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from trading_agent.agents.base import AgentOutput
from trading_agent.domain.analysis import LlmResearchFinding, PatternCandidate


class LlmResearchClient(ABC):
    @abstractmethod
    def research(self, candidate: PatternCandidate, evidence: tuple[str, ...]) -> LlmResearchFinding:
        """返回校验后的研究 JSON；网络调用只能放在适配器中。"""


class LlmResearchAgent:
    name = "llm_research"

    def __init__(self, client: LlmResearchClient | None = None) -> None:
        self._client = client

    def run(self, candidate: PatternCandidate, upstream_evidence: tuple[str, ...]) -> AgentOutput[LlmResearchFinding]:
        if self._client is None:
            finding = LlmResearchFinding(False, None, "AI 辅助分析尚未启用")
            return AgentOutput(
                agent_name=self.name,
                score=None,
                confidence=0.0,
                evidence=(finding.thesis,),
                risks=("本次结果未使用 AI 辅助结论",),
                payload=finding,
            )
        try:
            finding = self._client.research(candidate, upstream_evidence)
        except Exception:  # 数据源失败时仍要保留已经得到的确定性研究证据。
            finding = LlmResearchFinding(False, None, "AI 辅助分析暂时不可用")
            return AgentOutput(
                agent_name=self.name,
                score=None,
                confidence=0.0,
                evidence=(finding.thesis,),
                risks=("本次结果未使用 AI 辅助结论",),
                payload=finding,
            )
        return AgentOutput(
            agent_name=self.name,
            score=finding.recommendation_index,
            confidence=0.6,
            evidence=(finding.thesis,),
            risks=(),
            payload=finding,
        )
