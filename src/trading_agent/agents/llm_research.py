"""LLM boundary. A model is optional and must return structured, attributable data."""

from __future__ import annotations

from abc import ABC, abstractmethod

from trading_agent.agents.base import AgentOutput
from trading_agent.domain.analysis import LlmResearchFinding, PatternCandidate


class LlmResearchClient(ABC):
    @abstractmethod
    def research(self, candidate: PatternCandidate, evidence: tuple[str, ...]) -> LlmResearchFinding:
        """Return validated research JSON. Network calls belong only in an adapter."""


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
        except Exception:  # A provider failure must not hide deterministic research evidence.
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
