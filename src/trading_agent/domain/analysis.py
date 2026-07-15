"""Typed, auditable products of the candidate research workflow."""

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
    # Source-attributed records are carried through to the API so the UI can
    # link users to primary evidence instead of presenting LLM-only claims.
    news: tuple[NewsItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    scanned_count: int
    observation_pool_count: int
    research_pool_count: int
    recommendations: tuple[Recommendation, ...]
    vetoed: tuple[Recommendation, ...] = field(default_factory=tuple)
    # Every candidate that reached historical/news/LLM research, ordered by
    # final score. ``recommendations`` remains the concise Top-N decision list.
    research_results: tuple[Recommendation, ...] = field(default_factory=tuple)
