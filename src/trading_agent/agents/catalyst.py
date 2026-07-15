"""分析入围股票的板块信息和可追溯新闻。"""

from __future__ import annotations

from trading_agent.agents.base import AgentOutput
from trading_agent.domain.analysis import CatalystFinding, PatternCandidate
from trading_agent.domain.models import ResearchContext


class CatalystAgent:
    name = "catalyst"

    _POSITIVE_TERMS = ("中标", "签订", "回购", "增持", "业绩预增", "上调", "分红", "获批", "订单")
    _NEGATIVE_TERMS = ("立案", "处罚", "减持", "预亏", "终止", "诉讼", "风险提示", "ST", "问询")

    def run(self, candidate: PatternCandidate, context: ResearchContext) -> AgentOutput[CatalystFinding]:
        news_items = context.news[:5]
        headlines = tuple(item.headline for item in news_items)
        heat = context.sector.sector_heat
        headline_text = " ".join(headlines)
        has_positive = any(term in headline_text for term in self._POSITIVE_TERMS)
        has_negative = any(term in headline_text for term in self._NEGATIVE_TERMS)
        news_score = 30.0 if has_negative else 70.0 if has_positive else 55.0 if headlines else 50.0
        score = news_score if heat is None else (news_score * 0.6 + max(0.0, min(100.0, heat)) * 0.4)
        evidence = [f"所属行业：{context.sector.industry or '暂未获取'}"]
        if headlines:
            evidence.append(f"找到 {len(headlines)} 条与该股票相关的新闻或公告")
            evidence.extend(f"{item.source}：{item.headline}" for item in news_items[:2])
        else:
            evidence.append("暂未找到可明确归属于该股票的新闻或公告")
        return AgentOutput(
            agent_name=self.name,
            score=score,
            confidence=0.7 if headlines else 0.55 if heat is not None else 0.2,
            evidence=tuple(evidence),
            risks=("相关新闻中出现负面风险信号",) if has_negative else () if headlines else ("暂时缺少明确的消息催化",),
            payload=CatalystFinding(context.sector.industry, headlines, heat),
        )
