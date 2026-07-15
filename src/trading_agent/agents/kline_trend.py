"""Historical K-line and trend analysis for pattern-gated candidates only."""

from __future__ import annotations

from trading_agent.agents.base import AgentOutput
from trading_agent.domain.analysis import KlineTrendFinding, PatternCandidate
from trading_agent.domain.models import ResearchContext


class KlineTrendAgent:
    name = "kline_trend"

    def run(self, candidate: PatternCandidate, context: ResearchContext) -> AgentOutput[KlineTrendFinding]:
        quote = candidate.candidate.quote
        closes = [bar.close_price for bar in context.daily_bars]
        averages = {label: _average(closes[-period:]) for label, period in (("ma5", 5), ("ma10", 10), ("ma20", 20)) if len(closes) >= period}
        trend = _trend(closes, averages)
        score = 60.0 + (15.0 if trend == "bullish" else -10.0 if trend == "bearish" else 0.0)
        pattern_label = "收盘形态" if quote.is_final_bar else "盘中暂定形态"
        patterns = "、".join(_PATTERN_LABELS.get(item, item) for item in candidate.candle.patterns)
        evidence = [f"{pattern_label}：{patterns}", f"均线趋势：{_TREND_LABELS[trend]}"]
        if averages:
            evidence.append("已结合近 5 日、10 日和 20 日均线判断")
        risks = () if quote.is_final_bar else ("今日尚未收盘，K 线形态仍可能变化",)
        return AgentOutput(
            agent_name=self.name,
            score=max(0.0, min(100.0, score)),
            confidence=0.65 if averages else 0.35,
            evidence=tuple(evidence),
            risks=risks,
            payload=KlineTrendFinding(candidate.candle.patterns, trend, averages),
        )


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4)


def _trend(closes: list[float], averages: dict[str, float]) -> str:
    if not closes or "ma5" not in averages:
        return "unknown"
    latest = closes[-1]
    if latest > averages["ma5"] and averages.get("ma5", 0) >= averages.get("ma10", 0):
        return "bullish"
    if latest < averages["ma5"] and averages.get("ma5", 0) <= averages.get("ma10", float("inf")):
        return "bearish"
    return "neutral"


_PATTERN_LABELS = {
    "bullish_perfect_doji": "阳线完美十字",
    "bullish_hammer": "阳线锤子",
    "doji": "十字星",
    "hammer": "锤子线",
}
_TREND_LABELS = {"bullish": "偏强", "bearish": "偏弱", "neutral": "横盘", "unknown": "数据不足"}
