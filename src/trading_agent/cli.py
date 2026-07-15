"""Local command line entry point for deterministic workflows."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from trading_agent.bootstrap import (
    DEFAULT_SCANNER_CONFIG,
    DEFAULT_WORKFLOW_CONFIG,
    build_daily_research_workflow,
    build_market_scanner_agent,
    build_provider_registry,
)
from trading_agent.reports.markdown import MarkdownReportRenderer
from trading_agent.storage.sqlite import SqliteRecommendationRepository
from trading_agent.orchestrator.workflow import IncompleteResearchDataError
from trading_agent.providers.eastmoney import FreeDataProviderError
from trading_agent.providers.selection import latest_sina_snapshot, resolve_provider
from trading_agent.providers.sina import SinaFreeProvider


def _provider_from_args(
    args: argparse.Namespace, *, prefer_cached_sina_snapshot: bool = False
):  # type: ignore[no-untyped-def]
    return resolve_provider(
        build_provider_registry(),
        args.provider,
        snapshot_path=getattr(args, "snapshot", None),
        prefer_cached_sina_snapshot=prefer_cached_sina_snapshot,
    )


def _market_scan(args: argparse.Namespace) -> int:
    provider = _provider_from_args(args)
    output = build_market_scanner_agent(args.config).run(provider.fetch_realtime_quotes())
    result = output.payload
    assert result is not None
    response = {
        "agent": output.agent_name,
        "evidence": output.evidence,
        "scanned_count": result.scanned_count,
        "candidates": [asdict(candidate) for candidate in result.candidates],
        "rejections": [
            {"code": rejection.quote.code, "name": rejection.quote.name, "reasons": rejection.reasons}
            for rejection in result.rejections
        ],
    }
    print(json.dumps(response, ensure_ascii=False, default=str, indent=2))
    return 0


def _research(args: argparse.Namespace) -> int:
    provider = _provider_from_args(args, prefer_cached_sina_snapshot=True)
    result = build_daily_research_workflow(args.scanner_config, args.workflow_config).run(provider)
    if args.database is not None:
        SqliteRecommendationRepository(args.database).save(result)
    print(MarkdownReportRenderer().render(result))
    return 0


def _capture_close(args: argparse.Namespace) -> int:
    if args.provider.casefold() != SinaFreeProvider.name:
        raise ValueError("capture-close currently supports only provider 'sina_free'")
    provider = SinaFreeProvider()
    quotes = provider.fetch_realtime_quotes()
    if not quotes or not all(quote.is_final_bar for quote in quotes):
        raise FreeDataProviderError("The current Sina quote snapshot is not a completed daily bar")
    snapshot = latest_sina_snapshot()
    print(
        json.dumps(
            {
                "provider": provider.name,
                "captured_symbols": len(quotes),
                "snapshot": str(snapshot),
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal Quant Trading Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scanner = subparsers.add_parser("market-scan", help="Run the deterministic candidate funnel")
    scanner.add_argument("--provider", default="demo", help="Registered market-data provider")
    scanner.add_argument("--config", type=Path, default=DEFAULT_SCANNER_CONFIG)
    scanner.add_argument("--snapshot", type=Path, help="Replay a cached sina_free snapshot")
    scanner.set_defaults(handler=_market_scan)
    research = subparsers.add_parser("research", help="Run the previous-close candidate workflow")
    research.add_argument("--provider", default="demo", help="Provider with quote and research capabilities")
    research.add_argument("--scanner-config", type=Path, default=DEFAULT_SCANNER_CONFIG)
    research.add_argument("--workflow-config", type=Path, default=DEFAULT_WORKFLOW_CONFIG)
    research.add_argument("--database", type=Path, help="Optional SQLite destination for recommendations")
    research.add_argument("--snapshot", type=Path, help="Replay a cached sina_free snapshot")
    research.set_defaults(handler=_research)
    capture = subparsers.add_parser("capture-close", help="Cache a completed A-share daily snapshot")
    capture.add_argument("--provider", default="sina_free", help="Completed-bar data provider")
    capture.set_defaults(handler=_capture_close)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.handler(args)
    except (FreeDataProviderError, IncompleteResearchDataError) as exc:
        print(
            json.dumps(
                {"status": "data_incomplete", "message": str(exc)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
