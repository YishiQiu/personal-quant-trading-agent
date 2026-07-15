"""候选股研究流程生成的强类型、可追溯结果。"""

from __future__ import annotations

from dataclasses import dataclass, field

from trading_agent.domain.models import Candidate, NewsItem


@dataclass(frozen=True, slots=True)
class CandleMetrics:
    body_ratio: float
    upper_shadow_ratio: float
    lower_shadow_ratio: float
    patterns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PatternCandidate:
    candidate: Candidate
    candle: CandleMetrics


@dataclass(frozen=True, slots=True)
class KlineTrendFinding:
    patterns: tuple[str, ...]
    trend: str
    moving_averages: dict[str, float]


@dataclass(frozen=True, slots=True)
class VolumeFinding:
    volume_state: str
    relative_volume: float | None


@dataclass(frozen=True, slots=True)
class CatalystFinding:
    industry: str | None
    matched_headlines: tuple[str, ...]
    sector_heat: float | None


@dataclass(frozen=True, slots=True)
class RiskFinding:
    risk_level: str
    capital_flow_score: float | None
    fundamental_risk_score: float | None


@dataclass(frozen=True, slots=True)
class LlmResearchFinding:
    enabled: bool
    recommendation_index: float | None
    thesis: str
    stop_loss: float | None = None
    take_profit: float | None = None
    expected_holding_period: str | None = None


@dataclass(frozen=True, slots=True)
class Recommendation:
    code: str
    name: str
    total_score: float
    verdict: str
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    vetoed: bool = False
    # 带来源的记录会一直传到 API，让前端可以展示原始证据，而不是只展示模型结论。
    news: tuple[NewsItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    scanned_count: int
    observation_pool_count: int
    research_pool_count: int
    recommendations: tuple[Recommendation, ...]
    vetoed: tuple[Recommendation, ...] = field(default_factory=tuple)
    # 所有进入历史、新闻和模型研究的候选股按最终得分排列；recommendations 只保留 Top N。
    research_results: tuple[Recommendation, ...] = field(default_factory=tuple)
