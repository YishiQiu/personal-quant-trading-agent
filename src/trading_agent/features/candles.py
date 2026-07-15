"""Intraday provisional candle calculations for the 14:30 snapshot."""

from __future__ import annotations

from trading_agent.config_workflow import PatternGateConfig
from trading_agent.domain.analysis import CandleMetrics
from trading_agent.domain.models import QuoteSnapshot


def calculate_candle_metrics(quote: QuoteSnapshot, config: PatternGateConfig) -> CandleMetrics | None:
    """Recognize large red doji/hammer shapes from one completed daily bar."""

    if None in (quote.open_price, quote.high_price, quote.low_price):
        return None
    assert quote.open_price is not None
    assert quote.high_price is not None
    assert quote.low_price is not None
    if quote.open_price <= 0:
        return None
    high = max(quote.high_price, quote.open_price, quote.last_price)
    low = min(quote.low_price, quote.open_price, quote.last_price)
    candle_range = high - low
    if candle_range <= 0:
        return None
    body = abs(quote.last_price - quote.open_price)
    upper_shadow = high - max(quote.last_price, quote.open_price)
    lower_shadow = min(quote.last_price, quote.open_price) - low
    body_ratio = body / candle_range
    upper_ratio = upper_shadow / candle_range
    lower_ratio = lower_shadow / candle_range
    range_ratio = candle_range / quote.open_price
    bullish = quote.last_price > quote.open_price
    patterns: list[str] = []
    is_large = range_ratio >= config.min_range_ratio
    passes_direction = bullish or not config.require_bullish_close
    if passes_direction and is_large:
        # 完美十字要求实体近乎为零，且上下影线几乎对称。T 字线因为
        # 上下影严重不对称，会在这里自然被排除。
        is_perfect_doji = (
            body_ratio <= config.perfect_doji_max_body_ratio
            and upper_ratio >= config.perfect_doji_min_shadow_ratio
            and lower_ratio >= config.perfect_doji_min_shadow_ratio
            and abs(upper_ratio - lower_ratio) <= config.perfect_doji_max_shadow_imbalance_ratio
        )
        # 锤子线必须有清晰的小实体；下影主导且上影明显受限。
        is_hammer = (
            body_ratio > config.hammer_min_body_ratio
            and body_ratio <= config.hammer_max_body_ratio
            and lower_shadow / body >= config.hammer_min_lower_shadow_to_body
            and upper_shadow / body <= config.hammer_max_upper_shadow_to_body
            and lower_ratio >= config.hammer_min_lower_shadow_ratio
        )
        if is_perfect_doji:
            patterns.append("bullish_perfect_doji")
        elif is_hammer:
            patterns.append("bullish_hammer")
    return CandleMetrics(
        body_ratio=round(body_ratio, 4),
        upper_shadow_ratio=round(upper_ratio, 4),
        lower_shadow_ratio=round(lower_ratio, 4),
        patterns=tuple(patterns),
    )
