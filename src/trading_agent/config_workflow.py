"""Configuration of the candidate-research pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True, slots=True)
class PatternGateConfig:
    require_bullish_close: bool
    min_range_ratio: float
    perfect_doji_max_body_ratio: float
    perfect_doji_min_shadow_ratio: float
    perfect_doji_max_shadow_imbalance_ratio: float
    hammer_min_body_ratio: float
    hammer_max_body_ratio: float
    hammer_min_lower_shadow_to_body: float
    hammer_max_upper_shadow_to_body: float
    hammer_min_lower_shadow_ratio: float
    max_candidates: int


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    research_pool_limit: int
    final_recommendation_limit: int
    min_decision_score: float
    min_daily_bars: int
    require_llm_research: bool
    weights: dict[str, float]


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    workflow: WorkflowConfig
    pattern_gate: PatternGateConfig


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected a mapping at {path}")
    return value


def load_application_config(path: str | Path) -> ApplicationConfig:
    with Path(path).open(encoding="utf-8") as config_file:
        raw = _mapping(yaml.safe_load(config_file), "root")
    workflow = _mapping(raw.get("workflow"), "workflow")
    pattern = _mapping(raw.get("pattern_gate"), "pattern_gate")
    weights = {str(name): float(value) for name, value in _mapping(workflow.get("weights"), "weights").items()}
    if not weights or abs(sum(weights.values()) - 1.0) > 0.001:
        raise ValueError("Workflow weights must add up to 1.0")
    config = ApplicationConfig(
        workflow=WorkflowConfig(
            research_pool_limit=int(workflow["research_pool_limit"]),
            final_recommendation_limit=int(workflow["final_recommendation_limit"]),
            min_decision_score=float(workflow["min_decision_score"]),
            min_daily_bars=int(workflow["min_daily_bars"]),
            require_llm_research=bool(workflow["require_llm_research"]),
            weights=weights,
        ),
        pattern_gate=PatternGateConfig(
            require_bullish_close=bool(pattern["require_bullish_close"]),
            min_range_ratio=float(pattern["min_range_ratio"]),
            perfect_doji_max_body_ratio=float(pattern["perfect_doji_max_body_ratio"]),
            perfect_doji_min_shadow_ratio=float(pattern["perfect_doji_min_shadow_ratio"]),
            perfect_doji_max_shadow_imbalance_ratio=float(pattern["perfect_doji_max_shadow_imbalance_ratio"]),
            hammer_min_body_ratio=float(pattern["hammer_min_body_ratio"]),
            hammer_max_body_ratio=float(pattern["hammer_max_body_ratio"]),
            hammer_min_lower_shadow_to_body=float(pattern["hammer_min_lower_shadow_to_body"]),
            hammer_max_upper_shadow_to_body=float(pattern["hammer_max_upper_shadow_to_body"]),
            hammer_min_lower_shadow_ratio=float(pattern["hammer_min_lower_shadow_ratio"]),
            max_candidates=int(pattern["max_candidates"]),
        ),
    )
    if (
        config.workflow.research_pool_limit < 0
        or config.workflow.min_daily_bars <= 0
        or config.pattern_gate.max_candidates < 0
    ):
        raise ValueError("Research/pattern limits cannot be negative; daily-bar limit must be positive")
    if not (
        0 < config.pattern_gate.min_range_ratio <= 1
        and 0 < config.pattern_gate.perfect_doji_max_body_ratio <= 1
        and 0 < config.pattern_gate.perfect_doji_min_shadow_ratio < 0.5
        and 0 <= config.pattern_gate.perfect_doji_max_shadow_imbalance_ratio <= 1
        and 0 <= config.pattern_gate.hammer_min_body_ratio < config.pattern_gate.hammer_max_body_ratio <= 1
        and 0 < config.pattern_gate.hammer_min_lower_shadow_to_body
        and 0 <= config.pattern_gate.hammer_max_upper_shadow_to_body
        and 0 < config.pattern_gate.hammer_min_lower_shadow_ratio <= 1
        and config.pattern_gate.hammer_min_body_ratio >= config.pattern_gate.perfect_doji_max_body_ratio
    ):
        raise ValueError("Invalid bullish candle-pattern thresholds")
    return config
