"""分析资金流和基本面风险，并提供可追溯的否决路径。"""

from __future__ import annotations

from trading_agent.agents.base import AgentOutput
from trading_agent.domain.analysis import PatternCandidate, RiskFinding
from trading_agent.domain.models import ResearchContext


class RiskAgent:
    name = "risk"

    def run(self, candidate: PatternCandidate, context: ResearchContext) -> AgentOutput[RiskFinding]:
        quote = candidate.candidate.quote
        capital = context.capital_flow.main_net_inflow
        growth = context.fundamentals.profit_growth
        capital_score = None if capital is None else 75.0 if capital >= 0 else 25.0
        veto = quote.is_st or quote.is_delisting or (capital is not None and capital < 0 and growth is not None and growth < 0)
        risk_level = "high" if veto else "medium" if capital is None or growth is None else "low"
        score = 20.0 if veto else 55.0 if risk_level == "medium" else 78.0
        risks: list[str] = []
        if quote.is_st:
            risks.append("该股票属于 ST 风险标的")
        if capital is not None and capital < 0:
            risks.append("主力资金呈净流出")
        if growth is not None and growth < 0:
            risks.append("利润增长为负")
        return AgentOutput(
            agent_name=self.name,
            score=score,
            confidence=0.7 if capital is not None and growth is not None else 0.35,
            evidence=(f"综合风险：{_RISK_LABELS[risk_level]}",),
            risks=tuple(risks),
            veto=veto,
            payload=RiskFinding(risk_level, capital_score, score),
        )


_RISK_LABELS = {"high": "较高", "medium": "中等", "low": "较低"}
