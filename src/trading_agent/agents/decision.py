"""确定性最终排序；大模型永远不掌握最终决定权。"""

from __future__ import annotations

from collections.abc import Mapping

from trading_agent.agents.base import AgentOutput
from trading_agent.config_workflow import WorkflowConfig
from trading_agent.domain.analysis import PatternCandidate, Recommendation
from trading_agent.domain.models import NewsItem


class DecisionAgent:
    name = "decision"

    def __init__(self, config: WorkflowConfig) -> None:
        self._config = config

    def run(
        self,
        candidate: PatternCandidate,
        outputs: Mapping[str, AgentOutput[object]],
        news: tuple[NewsItem, ...] = (),
    ) -> Recommendation:
        vetoed = any(output.veto for output in outputs.values())
        reasons = tuple(evidence for output in outputs.values() for evidence in output.evidence)
        risks = tuple(risk for output in outputs.values() for risk in output.risks)
        if self._config.require_llm_research and outputs["llm_research"].score is None:
            vetoed = True
            risks += ("策略要求使用 AI 辅助分析，但本次未能取得结果",)
        score = _weighted_score(outputs, self._config.weights)
        if vetoed:
            verdict = "rejected"
        elif score >= self._config.min_decision_score:
            verdict = "watch_for_tail_buy"
        else:
            verdict = "not_recommended"
        quote = candidate.candidate.quote
        return Recommendation(quote.code, quote.name, score, verdict, reasons, risks, vetoed, news)


def _weighted_score(outputs: Mapping[str, AgentOutput[object]], weights: Mapping[str, float]) -> float:
    total_weight = 0.0
    total_score = 0.0
    output_names = {
        "kline_trend": "kline_trend",
        "volume": "volume",
        "catalyst": "catalyst",
        "risk": "risk",
        "llm": "llm_research",
    }
    for weight_name, output_name in output_names.items():
        score = outputs[output_name].score
        if score is not None:
            total_score += score * weights[weight_name]
            total_weight += weights[weight_name]
    return round(total_score / total_weight, 2) if total_weight else 0.0
