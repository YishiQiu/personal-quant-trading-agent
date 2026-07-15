from __future__ import annotations

from dataclasses import replace

from trading_agent.market_scanner.service import MarketScanner


def test_scanner_filters_and_ranks_candidates(scanner_config, quote_factory) -> None:
    result = MarketScanner(scanner_config).scan(
        [
            quote_factory(code="000001", turnover_amount=200_000_000),
            quote_factory(code="000002", turnover_amount=900_000_000),
            quote_factory(code="000003", is_st=True),
            quote_factory(code="000004", pct_change=9.8),
            quote_factory(code="000005", turnover_amount=50_000_000),
        ]
    )

    assert [candidate.quote.code for candidate in result.candidates] == ["000002", "000001"]
    assert result.scanned_count == 5
    assert {rejection.quote.code for rejection in result.rejections} == {"000003", "000004", "000005"}


def test_scanner_records_every_applicable_rejection_reason(scanner_config, quote_factory) -> None:
    result = MarketScanner(scanner_config).scan(
        [quote_factory(last_price=1.0, turnover_amount=10.0, is_st=True, pct_change=10.0)]
    )

    assert result.rejections[0].reasons == (
        "st",
        "price_out_of_range",
        "insufficient_turnover",
        "pct_change_out_of_range",
    )


def test_scanner_preserves_the_full_input_count_when_observation_pool_is_limited(
    scanner_config, quote_factory
) -> None:
    result = MarketScanner(replace(scanner_config, max_candidates=1)).scan(
        [
            quote_factory(code="000001", turnover_amount=200_000_000),
            quote_factory(code="000002", turnover_amount=900_000_000),
        ]
    )

    assert result.scanned_count == 2
    assert [candidate.quote.code for candidate in result.candidates] == ["000002"]


def test_scanner_keeps_every_eligible_stock_when_limit_is_zero(scanner_config, quote_factory) -> None:
    result = MarketScanner(replace(scanner_config, max_candidates=0)).scan(
        [
            quote_factory(code="000001", turnover_amount=200_000_000),
            quote_factory(code="000002", turnover_amount=900_000_000),
        ]
    )

    assert [candidate.quote.code for candidate in result.candidates] == ["000002", "000001"]
