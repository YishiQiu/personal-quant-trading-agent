"""学习模块基于持久化推荐结果运行，不做不可解释的大模型微调。"""

from __future__ import annotations

from dataclasses import dataclass

from trading_agent.domain.analysis import Recommendation


@dataclass(frozen=True, slots=True)
class Outcome:
    code: str
    next_day_return_pct: float
    max_drawdown_pct: float
    user_bought: bool | None = None


class OutcomeEvaluator:
    """生成结果标签；积累足够样本后再进行权重优化。"""

    def label(self, recommendation: Recommendation, outcome: Outcome) -> str:
        if outcome.next_day_return_pct > 0 and outcome.max_drawdown_pct >= -2.0:
            return "successful"
        if outcome.max_drawdown_pct <= -4.0:
            return "risk_failure"
        return "neutral"
