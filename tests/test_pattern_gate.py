from __future__ import annotations

from datetime import datetime

from trading_agent.config_workflow import PatternGateConfig
from trading_agent.domain.models import Candidate, QuoteSnapshot
from trading_agent.market_scanner.pattern_gate import PatternGate


def _strict_config(max_candidates: int) -> PatternGateConfig:
    return PatternGateConfig(
        require_bullish_close=True,
        min_range_ratio=0.03,
        perfect_doji_max_body_ratio=0.02,
        perfect_doji_min_shadow_ratio=0.45,
        perfect_doji_max_shadow_imbalance_ratio=0.06,
        hammer_min_body_ratio=0.03,
        hammer_max_body_ratio=0.3,
        hammer_min_lower_shadow_to_body=2.0,
        hammer_max_upper_shadow_to_body=0.5,
        hammer_min_lower_shadow_ratio=0.6,
        max_candidates=max_candidates,
    )


def test_pattern_gate_identifies_only_perfect_doji_and_hammer() -> None:
    now = datetime(2026, 7, 13, 14, 30)
    doji = Candidate(
        QuoteSnapshot("000001", "十字星", 10.01, 0, 200_000_000, 20_000_000, now, 10.0, 10.5, 9.5),
        1.5,
    )
    t_line = Candidate(
        QuoteSnapshot("000003", "T字线", 10.01, 0, 200_000_000, 20_000_000, now, 10.0, 10.01, 9.0),
        1.45,
    )
    hammer = Candidate(
        QuoteSnapshot("000002", "锤头线", 10.1, 0, 200_000_000, 20_000_000, now, 10.0, 10.1, 9.2),
        1.4,
    )
    gate = PatternGate(_strict_config(10))

    selected = {item.candidate.quote.code: item.candle.patterns for item in gate.select((doji, t_line, hammer))}

    assert selected == {
        "000001": ("bullish_perfect_doji",),
        "000002": ("bullish_hammer",),
    }


def test_pattern_gate_keeps_every_match_when_limit_is_zero() -> None:
    now = datetime(2026, 7, 13, 14, 30)
    candidates = tuple(
        Candidate(
            QuoteSnapshot(
                f"00000{index}",
                f"十字星{index}",
                10.01,
                0,
                200_000_000,
                20_000_000,
                now,
                10.0,
                10.5,
                9.5,
            ),
            1.5,
        )
        for index in range(1, 4)
    )

    selected = PatternGate(_strict_config(0)).select(candidates)

    assert [item.candidate.quote.code for item in selected] == ["000001", "000002", "000003"]


def test_pattern_gate_rejects_bearish_and_small_doji() -> None:
    now = datetime(2026, 7, 13, 14, 30)
    bearish_doji = Candidate(
        QuoteSnapshot("000001", "阴十字", 9.99, 0, 200_000_000, 20_000_000, now, 10.0, 10.5, 9.5),
        1.5,
    )
    small_bullish_doji = Candidate(
        QuoteSnapshot("000002", "小十字", 10.01, 0, 200_000_000, 20_000_000, now, 10.0, 10.1, 9.9),
        1.5,
    )

    selected = PatternGate(_strict_config(0)).select((bearish_doji, small_bullish_doji))

    assert selected == ()


def test_pattern_gate_rejects_lopsided_cross() -> None:
    now = datetime(2026, 7, 13, 14, 30)
    lopsided = Candidate(
        QuoteSnapshot("000004", "不对称十字", 10.01, 0, 200_000_000, 20_000_000, now, 10.0, 10.1, 9.1),
        1.5,
    )

    selected = PatternGate(_strict_config(0)).select((lopsided,))

    assert selected == ()
