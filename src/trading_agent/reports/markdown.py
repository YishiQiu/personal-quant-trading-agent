"""Markdown 报告渲染器，不在渲染过程中偷偷调用行情接口。"""

from __future__ import annotations

from datetime import datetime

from trading_agent.domain.analysis import WorkflowResult


class MarkdownReportRenderer:
    def render(self, result: WorkflowResult, generated_at: datetime | None = None) -> str:
        timestamp = (generated_at or datetime.now().astimezone()).isoformat(timespec="seconds")
        lines = [
            "# 前收盘形态候选研究报告",
            "",
            f"生成时间：{timestamp}",
            "",
            f"全市场扫描：{result.scanned_count} 只；观察池：{result.observation_pool_count} 只；"
            f"形态研究池：{result.research_pool_count} 只。",
            "",
            "## 推荐关注",
            "",
        ]
        if not result.recommendations:
            lines.append("本次没有满足阈值的前收盘形态候选。")
        for index, recommendation in enumerate(result.recommendations, start=1):
            lines.extend(
                [
                    f"### {index}. {recommendation.code} {recommendation.name} — {recommendation.total_score:.2f}",
                    "",
                    f"结论：`{recommendation.verdict}`",
                    "",
                    "证据：" + "；".join(recommendation.reasons),
                    "",
                    "风险：" + ("；".join(recommendation.risks) or "未发现结构化风险"),
                    "",
                ]
            )
        if result.vetoed:
            lines.extend(["## 已否决", ""])
            lines.extend(f"- {item.code} {item.name}：{'；'.join(item.risks)}" for item in result.vetoed)
        return "\n".join(lines) + "\n"
