"""Composition root: the only place that wires implementations together."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from trading_agent.agents.catalyst import CatalystAgent
from trading_agent.agents.decision import DecisionAgent
from trading_agent.agents.kline_trend import KlineTrendAgent
from trading_agent.agents.llm_research import LlmResearchAgent
from trading_agent.agents.market_scanner import MarketScannerAgent
from trading_agent.agents.risk import RiskAgent
from trading_agent.agents.volume import VolumeAgent
from trading_agent.config import MarketScannerConfig, load_market_scanner_config
from trading_agent.config_llm import load_llm_provider_config
from trading_agent.config_news import load_news_config
from trading_agent.config_workflow import load_application_config
from trading_agent.llm.openai_compatible import OpenAiCompatibleLlmResearchClient
from trading_agent.market_scanner.pattern_gate import PatternGate
from trading_agent.news.cninfo import CninfoPublicDisclosureProvider
from trading_agent.news.eastmoney import EastmoneyStockNewsProvider
from trading_agent.news.enricher import NewsEnricher
from trading_agent.news.tushare import TushareMajorNewsProvider
from trading_agent.orchestrator.workflow import DailyResearchWorkflow
from trading_agent.providers.akshare import AkShareMarketDataProvider
from trading_agent.providers.demo import DemoMarketDataProvider
from trading_agent.providers.eastmoney import EastmoneyFreeProvider
from trading_agent.providers.registry import ProviderRegistry
from trading_agent.providers.sina import SinaFreeProvider

DEFAULT_SCANNER_CONFIG = Path("configs/market_scanner.yaml")
DEFAULT_WORKFLOW_CONFIG = Path("configs/workflow.yaml")
DEFAULT_LLM_CONFIG = Path("configs/llm.yaml")
DEFAULT_NEWS_CONFIG = Path("configs/news.yaml")


def build_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(DemoMarketDataProvider)
    registry.register(EastmoneyFreeProvider)
    registry.register(SinaFreeProvider)
    registry.register(AkShareMarketDataProvider)
    return registry


def build_market_scanner_agent(
    config_path: str | Path = DEFAULT_SCANNER_CONFIG,
    *,
    config: MarketScannerConfig | None = None,
) -> MarketScannerAgent:
    from trading_agent.market_scanner.service import MarketScanner

    return MarketScannerAgent(MarketScanner(config or load_market_scanner_config(config_path)))


def build_pattern_gate(workflow_config_path: str | Path = DEFAULT_WORKFLOW_CONFIG) -> PatternGate:
    """Build the deterministic candle-pattern gate for the first visible funnel."""

    return PatternGate(load_application_config(workflow_config_path).pattern_gate)


def build_llm_research_agent(config_path: str | Path = DEFAULT_LLM_CONFIG) -> LlmResearchAgent:
    """Build the configured provider only when its key exists in the server environment."""

    load_dotenv(override=False)
    config = load_llm_provider_config(config_path)
    fallback_key_env = "KIMI_API_KEY" if config.provider == "kimi" else "DEEPSEEK_API_KEY"
    api_key = os.environ.get(config.api_key_env) or os.environ.get(fallback_key_env)
    if not config.enabled or not api_key:
        return LlmResearchAgent()
    return LlmResearchAgent(OpenAiCompatibleLlmResearchClient(api_key=api_key, config=config))


def build_news_enricher(config_path: str | Path) -> NewsEnricher | None:
    """Build optional source collectors; a missing Tushare token never disables CNINFO."""

    load_dotenv(override=False)
    config = load_news_config(config_path)
    if not config.enabled:
        return None
    providers = []
    if config.cninfo.enabled:
        providers.append(
            CninfoPublicDisclosureProvider(
                page_size=config.cninfo.page_size,
                request_interval_seconds=config.cninfo.request_interval_seconds,
            )
        )
    if config.eastmoney_stock_news.enabled:
        providers.append(
            EastmoneyStockNewsProvider(
                request_interval_seconds=config.eastmoney_stock_news.request_interval_seconds,
            )
        )
    tushare_token = os.environ.get(config.tushare.api_key_env, "")
    if config.tushare.enabled and tushare_token.strip():
        providers.append(
            TushareMajorNewsProvider(
                token=tushare_token,
                source=config.tushare.source,
                endpoint=config.tushare.endpoint,
            )
        )
    return NewsEnricher(config=config, providers=providers)


def build_daily_research_workflow(
    scanner_config_path: str | Path = DEFAULT_SCANNER_CONFIG,
    workflow_config_path: str | Path = DEFAULT_WORKFLOW_CONFIG,
    news_config_path: str | Path | None = DEFAULT_NEWS_CONFIG,
    *,
    scanner_config: MarketScannerConfig | None = None,
) -> DailyResearchWorkflow:
    """Build the complete 14:30 research workflow with optional source-attributed news."""

    application_config = load_application_config(workflow_config_path)
    return DailyResearchWorkflow(
        config=application_config,
        scanner=build_market_scanner_agent(scanner_config_path, config=scanner_config),
        pattern_gate=PatternGate(application_config.pattern_gate),
        kline_trend=KlineTrendAgent(),
        volume=VolumeAgent(),
        catalyst=CatalystAgent(),
        risk=RiskAgent(),
        llm_research=build_llm_research_agent(),
        decision=DecisionAgent(application_config.workflow),
        news_enricher=build_news_enricher(news_config_path) if news_config_path is not None else None,
    )
