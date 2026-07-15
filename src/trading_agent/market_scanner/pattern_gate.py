"""Second deterministic funnel: daily provisional-candle shape screening."""

from __future__ import annotations

from collections.abc import Iterable

from trading_agent.config_workflow import PatternGateConfig
from trading_agent.domain.analysis import PatternCandidate
from trading_agent.domain.models import Candidate
from trading_agent.features.candles import calculate_candle_metrics


class PatternGate:
    def __init__(self, config: PatternGateConfig) -> None:
        self._config = config

    def select(self, candidates: Iterable[Candidate]) -> tuple[PatternCandidate, ...]:
        selected: list[PatternCandidate] = []
        for candidate in candidates:
            candle = calculate_candle_metrics(candidate.quote, self._config)
            if candle is not None and candle.patterns:
                selected.append(PatternCandidate(candidate=candidate, candle=candle))
        selected.sort(
            key=lambda item: (len(item.candle.patterns), item.candidate.liquidity_score),
            reverse=True,
        )
        if self._config.max_candidates > 0:
            selected = selected[: self._config.max_candidates]
        return tuple(selected)
