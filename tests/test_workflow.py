from __future__ import annotations

from dataclasses import replace

import pytest

from trading_agent.bootstrap import build_daily_research_workflow
from trading_agent.config import load_market_scanner_config
from trading_agent.orchestrator.workflow import IncompleteResearchDataError
from trading_agent.providers.demo import DemoMarketDataProvider
from trading_agent.reports.markdown import MarkdownReportRenderer


def test_demo_workflow_runs_two_stage_research() -> None:
    result = build_daily_research_workflow(news_config_path=None).run(DemoMarketDataProvider())

    assert result.scanned_count == 6
    assert result.observation_pool_count == 2
    assert result.research_pool_count == 2
    assert {item.code for item in result.recommendations} == {"000001", "300001"}
    assert "前收盘形态候选研究报告" in MarkdownReportRenderer().render(result)


class MissingHistoryProvider(DemoMarketDataProvider):
    """Simulates a free source that returns a quote but cannot enrich it."""

    def fetch_research_contexts(self, codes: tuple[str, ...], as_of: object) -> dict[str, object]:
        return {}


def test_workflow_rejects_candidates_without_required_daily_history() -> None:
    with pytest.raises(IncompleteResearchDataError, match="000001"):
        build_daily_research_workflow(news_config_path=None).run(MissingHistoryProvider())


def test_workflow_reuses_user_board_filters_for_deep_research() -> None:
    config = replace(
        load_market_scanner_config("configs/market_scanner.yaml"),
        include_chinext=False,
    )

    result = build_daily_research_workflow(
        news_config_path=None,
        scanner_config=config,
    ).run(DemoMarketDataProvider())

    assert result.observation_pool_count == 1
    assert {item.code for item in result.research_results} == {"000001"}
