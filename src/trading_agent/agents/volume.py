"""成交量上下文分析；盘中归一化留作后续明确扩展。"""

from __future__ import annotations

from trading_agent.agents.base import AgentOutput
from trading_agent.domain.analysis import PatternCandidate, VolumeFinding
from trading_agent.domain.models import ResearchContext


class VolumeAgent:
    name = "volume"

    def run(self, candidate: PatternCandidate, context: ResearchContext) -> AgentOutput[VolumeFinding]:
        quote = candidate.candidate.quote
        # 完整日 K 可能已经是历史序列最后一行，因此应与之前五天比较，不能把自身算进去。
        bars = (
            context.daily_bars[-6:-1]
            if quote.is_final_bar and len(context.daily_bars) >= 6
            else context.daily_bars[-5:]
        )
        historical = [bar.volume for bar in bars]
        if not historical:
            return AgentOutput(
                agent_name=self.name,
                score=None,
                confidence=0.0,
                evidence=("缺少历史成交量，暂时无法判断量能变化",),
                risks=("本次未计入量能结论",),
                payload=VolumeFinding("unknown", None),
            )
        reference = sum(historical) / len(historical)
        relative_volume = candidate.candidate.quote.volume / reference if reference else None
        state = _volume_state(relative_volume)
        score = {"contracting": 72.0, "normal": 60.0, "expanding": 66.0, "extreme": 45.0}[state]
        evidence_label = (
            "当日成交量相对过去 5 日平均值"
            if quote.is_final_bar
            else "当前成交量相对过去 5 日平均值"
        )
        risks = () if quote.is_final_bar else (
            "盘中成交量尚未完成，只能作为临时参考",
        )
        return AgentOutput(
            agent_name=self.name,
            score=score,
            confidence=0.45,
            evidence=(f"{evidence_label}：{relative_volume:.2f} 倍（{_VOLUME_LABELS[state]}）",),
            risks=risks,
            payload=VolumeFinding(state, round(relative_volume, 4)),
        )


def _volume_state(relative_volume: float | None) -> str:
    if relative_volume is None:
        return "unknown"
    if relative_volume < 0.7:
        return "contracting"
    if relative_volume <= 1.5:
        return "normal"
    if relative_volume <= 2.5:
        return "expanding"
    return "extreme"


_VOLUME_LABELS = {
    "unknown": "数据不足",
    "contracting": "明显缩量",
    "normal": "量能正常",
    "expanding": "温和放量",
    "extreme": "异常放量",
}
