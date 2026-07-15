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


def test_scanner_can_exclude_chinext_and_star_market(scanner_config, quote_factory) -> None:
    config = replace(scanner_config, include_chinext=False, include_star_market=False)

    result = MarketScanner(config).scan(
        [
            quote_factory(code="000001"),
            quote_factory(code="300001"),
            quote_factory(code="301001"),
            quote_factory(code="688001"),
            quote_factory(code="689001"),
        ]
    )

    assert [candidate.quote.code for candidate in result.candidates] == ["000001"]
    reasons = {rejection.quote.code: rejection.reasons for rejection in result.rejections}
    assert reasons["300001"] == ("chinext_excluded",)
    assert reasons["301001"] == ("chinext_excluded",)
    assert reasons["688001"] == ("star_market_excluded",)
    assert reasons["689001"] == ("star_market_excluded",)


def test_scanner_applies_user_price_range(scanner_config, quote_factory) -> None:
    config = replace(scanner_config, min_price=10.0, max_price=20.0, max_candidates=0)

    result = MarketScanner(config).scan(
        [
            quote_factory(code="000001", last_price=9.99),
            quote_factory(code="000002", last_price=10.0),
            quote_factory(code="000003", last_price=20.0),
            quote_factory(code="000004", last_price=20.01),
        ]
    )

    assert {candidate.quote.code for candidate in result.candidates} == {"000002", "000003"}
    assert {rejection.quote.code for rejection in result.rejections} == {"000001", "000004"}
