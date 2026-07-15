"""Learning operates on persisted recommendations, never on opaque LLM fine-tuning."""

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
    """Produces labels; weight optimization is intentionally deferred until evidence accumulates."""

    def label(self, recommendation: Recommendation, outcome: Outcome) -> str:
        if outcome.next_day_return_pct > 0 and outcome.max_drawdown_pct >= -2.0:
            return "successful"
        if outcome.max_drawdown_pct <= -4.0:
            return "risk_failure"
        return "neutral"
