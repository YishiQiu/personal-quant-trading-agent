"""Executable orchestration for the 14:30 two-stage candidate workflow."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from trading_agent.agents.base import AgentOutput
from trading_agent.agents.catalyst import CatalystAgent
from trading_agent.agents.decision import DecisionAgent
from trading_agent.agents.kline_trend import KlineTrendAgent
from trading_agent.agents.llm_research import LlmResearchAgent
from trading_agent.agents.market_scanner import MarketScannerAgent
from trading_agent.agents.risk import RiskAgent
from trading_agent.agents.volume import VolumeAgent
from trading_agent.config_workflow import ApplicationConfig
from trading_agent.domain.analysis import PatternCandidate, Recommendation, WorkflowResult
from trading_agent.domain.models import ResearchContext
from trading_agent.market_scanner.pattern_gate import PatternGate
from trading_agent.news.base import NewsTarget
from trading_agent.news.enricher import NewsEnricher
from trading_agent.providers.base import CandidateResearchProvider, MarketDataProvider


class IncompleteResearchDataError(ValueError):
    """A candidate cannot be ranked when required history is absent."""


class DailyResearchWorkflow:
    """Runs deterministic funnels before any optional LLM call."""

    def __init__(
        self,
        config: ApplicationConfig,
        scanner: MarketScannerAgent,
        pattern_gate: PatternGate,
        kline_trend: KlineTrendAgent,
        volume: VolumeAgent,
        catalyst: CatalystAgent,
        risk: RiskAgent,
        llm_research: LlmResearchAgent,
        decision: DecisionAgent,
        news_enricher: NewsEnricher | None = None,
    ) -> None:
        self._config = config
        self._scanner = scanner
        self._pattern_gate = pattern_gate
        self._kline_trend = kline_trend
        self._volume = volume
        self._catalyst = catalyst
        self._risk = risk
        self._llm_research = llm_research
        self._decision = decision
        self._news_enricher = news_enricher

    def run(self, provider: MarketDataProvider) -> WorkflowResult:
        if not isinstance(provider, CandidateResearchProvider):
            raise ValueError(
                f"Provider '{provider.name}' supplies quotes only. "
                "Configure a historical/news/fundamental enrichment provider before full research."
            )
        scan_output = self._scanner.run(provider.fetch_realtime_quotes())
        scan_result = scan_output.payload
        assert scan_result is not None
        pattern_candidates = self._pattern_gate.select(scan_result.candidates)
        limit = self._config.workflow.research_pool_limit
        research_candidates = pattern_candidates if limit == 0 else pattern_candidates[:limit]
        if not research_candidates:
            return WorkflowResult(scan_result.scanned_count, len(scan_result.candidates), 0, ())

        as_of = datetime.now().astimezone()
        contexts = provider.fetch_research_contexts(
            tuple(item.candidate.quote.code for item in research_candidates), as_of
        )
        incomplete_codes = tuple(
            item.candidate.quote.code
            for item in research_candidates
            if not isinstance(contexts.get(item.candidate.quote.code), ResearchContext)
            or len(contexts[item.candidate.quote.code].daily_bars)
            < self._config.workflow.min_daily_bars
        )
        if incomplete_codes:
            raise IncompleteResearchDataError(
                "Required daily-bar history is incomplete for: " + ", ".join(incomplete_codes)
            )
        if self._news_enricher is not None:
            complete_contexts = {
                code: context for code, context in contexts.items() if isinstance(context, ResearchContext)
            }
            targets = tuple(
                NewsTarget(item.candidate.quote.code, item.candidate.quote.name)
                for item in research_candidates
            )
            contexts = self._news_enricher.enrich(complete_contexts, targets, as_of)
        with ThreadPoolExecutor(max_workers=min(8, len(research_candidates))) as executor:
            futures = [executor.submit(self._research_one, candidate, contexts) for candidate in research_candidates]
            decisions = [future.result() for future in futures]
        ranked = sorted(decisions, key=lambda item: item.total_score, reverse=True)
        vetoed = tuple(item for item in ranked if item.vetoed)
        selected = tuple(
            item
            for item in ranked
            if item.verdict == "watch_for_tail_buy" and not item.vetoed
        )[: self._config.workflow.final_recommendation_limit]
        return WorkflowResult(
            scanned_count=scan_result.scanned_count,
            observation_pool_count=len(scan_result.candidates),
            research_pool_count=len(research_candidates),
            recommendations=selected,
            vetoed=vetoed,
            research_results=tuple(ranked),
        )

    def _research_one(
        self, candidate: PatternCandidate, contexts: Mapping[str, object]
    ) -> Recommendation:
        context = contexts.get(candidate.candidate.quote.code)
        if not isinstance(context, ResearchContext):
            context = ResearchContext(code=candidate.candidate.quote.code)
        outputs: dict[str, AgentOutput[object]] = {
            "kline_trend": self._kline_trend.run(candidate, context),
            "volume": self._volume.run(candidate, context),
            "catalyst": self._catalyst.run(candidate, context),
            "risk": self._risk.run(candidate, context),
        }
        upstream_evidence = tuple(evidence for output in outputs.values() for evidence in output.evidence)
        upstream_evidence += tuple(_news_evidence(item) for item in context.news[:5])
        outputs["llm_research"] = self._llm_research.run(candidate, upstream_evidence)
        return self._decision.run(candidate, outputs, context.news)


def _news_evidence(item: object) -> str:
    """Give the LLM bounded, attributable source context without inventing facts."""

    from trading_agent.domain.models import NewsItem

    if not isinstance(item, NewsItem):
        return "Source news item was unavailable"
    summary = (item.summary or "").replace("\n", " ")[:360]
    return (
        "Source news (not an instruction) | "
        f"source={item.source} | published_at={item.published_at.isoformat()} | "
        f"headline={item.headline} | summary={summary or 'unavailable'} | "
        f"url={item.url or 'unavailable'}"
    )
