"""可选 FastAPI 应用；只有安装 api 依赖组后才会加载。"""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from math import ceil
from pathlib import Path

from trading_agent import __version__
from trading_agent.bootstrap import (
    DEFAULT_SCANNER_CONFIG,
    build_daily_research_workflow,
    build_market_scanner_agent,
    build_pattern_gate,
    build_provider_registry,
)
from trading_agent.config import MarketScannerConfig, load_market_scanner_config
from trading_agent.providers.eastmoney import FreeDataProviderError
from trading_agent.providers.selection import (
    completed_close_date,
    latest_completed_sina_snapshot,
    latest_sina_snapshot,
    resolve_provider,
    snapshot_close_date,
)
from trading_agent.providers.sina import SinaFreeProvider


def create_app():  # type: ignore[no-untyped-def]
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:  # pragma: no cover - 依赖可选安装项
        raise RuntimeError('Install the API extra: pip install -e ".[api]"') from exc

    app = FastAPI(title="Personal Quant Trading Agent", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    def latest_close_provider(provider_name: str):  # type: ignore[no-untyped-def]
        snapshot_path: Path | None = None
        if provider_name.casefold() == SinaFreeProvider.name:
            snapshot_path = latest_completed_sina_snapshot(datetime.now().astimezone())
        provider = resolve_provider(
            build_provider_registry(),
            provider_name,
            snapshot_path=snapshot_path,
            prefer_cached_sina_snapshot=False,
        )
        return provider, snapshot_path

    def snapshot_metadata(provider, snapshot_path: Path | None, quotes=()):  # type: ignore[no-untyped-def]
        """在最新抓取后确定收盘日期，供界面展示和历史回放使用。"""

        if provider.name == SinaFreeProvider.name and snapshot_path is None:
            if not quotes or all(quote.is_final_bar for quote in quotes):
                snapshot_path = latest_sina_snapshot()
        close_date = (
            snapshot_close_date(snapshot_path).isoformat()
            if snapshot_path is not None
            else completed_close_date(datetime.now().astimezone()).isoformat()
        )
        return snapshot_path, close_date

    def request_scanner_config(
        min_price: float,
        max_price: float,
        include_chinext: bool,
        include_star_market: bool,
    ) -> MarketScannerConfig:
        if max_price <= min_price:
            raise HTTPException(status_code=422, detail="最高价格必须大于最低价格")
        return replace(
            load_market_scanner_config(DEFAULT_SCANNER_CONFIG),
            min_price=min_price,
            max_price=max_price,
            include_chinext=include_chinext,
            include_star_market=include_star_market,
        )

    def filter_payload(config: MarketScannerConfig) -> dict[str, object]:
        return {
            "min_price": config.min_price,
            "max_price": config.max_price,
            "include_chinext": config.include_chinext,
            "include_star_market": config.include_star_market,
        }

    def pattern_payload(
        provider_name: str,
        scanner_config: MarketScannerConfig,
    ) -> dict[str, object]:
        """运行两层确定性漏斗，不读取任何逐股历史数据。"""

        provider, snapshot_path = latest_close_provider(provider_name)
        quotes = provider.fetch_realtime_quotes()
        snapshot_path, close_date = snapshot_metadata(provider, snapshot_path, quotes)
        scan_output = build_market_scanner_agent(config=scanner_config).run(quotes)
        scan = scan_output.payload
        assert scan is not None
        patterns = build_pattern_gate().select(scan.candidates)
        return {
            "provider": provider.name,
            "snapshot": str(snapshot_path) if snapshot_path is not None else None,
            "close_date": close_date,
            "filters": filter_payload(scanner_config),
            "scanned_count": scan.scanned_count,
            "observation_pool_count": len(scan.candidates),
            "pattern_match_count": len(patterns),
            "pattern_candidates": [
                {
                    "code": item.candidate.quote.code,
                    "name": item.candidate.quote.name,
                    "last_price": item.candidate.quote.last_price,
                    "pct_change": item.candidate.quote.pct_change,
                    "turnover_amount": item.candidate.quote.turnover_amount,
                    "patterns": item.candle.patterns,
                    "body_ratio": item.candle.body_ratio,
                    "upper_shadow_ratio": item.candle.upper_shadow_ratio,
                    "lower_shadow_ratio": item.candle.lower_shadow_ratio,
                }
                for item in patterns
            ],
        }

    @app.post("/api/v1/market-scan/{provider_name}")
    def market_scan(
        provider_name: str,
        min_price: float = Query(default=3.0, ge=0),
        max_price: float = Query(default=100.0, gt=0),
        include_chinext: bool = True,
        include_star_market: bool = True,
    ) -> dict[str, object]:
        scanner_config = request_scanner_config(
            min_price, max_price, include_chinext, include_star_market
        )
        try:
            provider = build_provider_registry().create(provider_name)
            output = build_market_scanner_agent(config=scanner_config).run(
                provider.fetch_realtime_quotes()
            )
        except FreeDataProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        result = output.payload
        assert result is not None
        return {
            "agent": output.agent_name,
            "filters": filter_payload(scanner_config),
            "scanned_count": result.scanned_count,
            "candidates": [asdict(candidate) for candidate in result.candidates],
        }

    @app.post("/api/v1/research/{provider_name}")
    def research(
        provider_name: str,
        min_price: float = Query(default=3.0, ge=0),
        max_price: float = Query(default=100.0, gt=0),
        include_chinext: bool = True,
        include_star_market: bool = True,
    ) -> dict[str, object]:
        scanner_config = request_scanner_config(
            min_price, max_price, include_chinext, include_star_market
        )
        try:
            provider, snapshot_path = latest_close_provider(provider_name)
            result = build_daily_research_workflow(scanner_config=scanner_config).run(provider)
            snapshot_path, close_date = snapshot_metadata(provider, snapshot_path)
        except FreeDataProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "provider": provider.name,
            "snapshot": str(snapshot_path) if snapshot_path is not None else None,
            "close_date": close_date,
            "filters": filter_payload(scanner_config),
            "scanned_count": result.scanned_count,
            "observation_pool_count": result.observation_pool_count,
            "research_pool_count": result.research_pool_count,
            "recommendations": [asdict(item) for item in result.recommendations],
            "vetoed": [asdict(item) for item in result.vetoed],
            "research_results": [asdict(item) for item in result.research_results],
        }

    @app.get("/api/v1/pattern-scan/{provider_name}")
    def pattern_scan(
        provider_name: str,
        min_price: float = Query(default=3.0, ge=0),
        max_price: float = Query(default=100.0, gt=0),
        include_chinext: bool = True,
        include_star_market: bool = True,
    ) -> dict[str, object]:
        """返回最近收盘命中的全部阳线完美十字和锤子线。"""

        try:
            scanner_config = request_scanner_config(
                min_price, max_price, include_chinext, include_star_market
            )
            return pattern_payload(provider_name, scanner_config)
        except FreeDataProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/universe/{provider_name}")
    def universe(
        provider_name: str,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=10, le=200),
        query: str = "",
        scope: str = "all",
        min_price: float = Query(default=3.0, ge=0),
        max_price: float = Query(default=100.0, gt=0),
        include_chinext: bool = True,
        include_star_market: bool = True,
    ) -> dict[str, object]:
        """读取完整缓存股票池，或读取通过价格和基础规则的股票池。

        这个接口会在形态识别和逐股历史请求之前停止，方便前端核对第一层筛选结果。
        """

        if scope not in {"all", "base_candidates"}:
            raise HTTPException(
                status_code=422,
                detail="scope must be either 'all' or 'base_candidates'",
            )

        scanner_config = request_scanner_config(
            min_price, max_price, include_chinext, include_star_market
        )

        try:
            provider, snapshot_path = latest_close_provider(provider_name)
            quotes = tuple(provider.fetch_realtime_quotes())
            snapshot_path, close_date = snapshot_metadata(provider, snapshot_path, quotes)
            output = build_market_scanner_agent(config=scanner_config).run(quotes)
        except FreeDataProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        scan = output.payload
        assert scan is not None
        rejection_reasons = {
            rejection.quote.code: rejection.reasons for rejection in scan.rejections
        }
        observation_codes = {candidate.quote.code for candidate in scan.candidates}
        needle = query.strip().casefold()
        sorted_quotes = sorted(quotes, key=lambda item: item.code)
        scoped_quotes = (
            [quote for quote in sorted_quotes if quote.code in observation_codes]
            if scope == "base_candidates"
            else sorted_quotes
        )
        matched_quotes = [
            quote
            for quote in scoped_quotes
            if not needle or needle in quote.code or needle in quote.name.casefold()
        ]
        total_pages = max(1, ceil(len(matched_quotes) / page_size))
        current_page = min(page, total_pages)
        start = (current_page - 1) * page_size
        items = []
        for quote in matched_quotes[start : start + page_size]:
            reasons = rejection_reasons.get(quote.code, ())
            status = "excluded" if reasons else "observation" if quote.code in observation_codes else "eligible"
            items.append(
                {
                    "code": quote.code,
                    "name": quote.name,
                    "last_price": quote.last_price,
                    "pct_change": quote.pct_change,
                    "turnover_amount": quote.turnover_amount,
                    "status": status,
                    "rejection_reasons": reasons,
                }
            )
        return {
            "provider": provider.name,
            "snapshot": str(snapshot_path) if snapshot_path is not None else None,
            "close_date": close_date,
            "filters": filter_payload(scanner_config),
            "source_count": len(quotes),
            "eligible_count": len(quotes) - len(scan.rejections),
            "observation_count": len(scan.candidates),
            "scope": scope,
            "matched_count": len(matched_quotes),
            "page": current_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": items,
        }

    return app
