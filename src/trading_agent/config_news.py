"""候选股新闻和公告补充模块的强类型配置。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True, slots=True)
class CninfoNewsConfig:
    enabled: bool
    page_size: int
    request_interval_seconds: float


@dataclass(frozen=True, slots=True)
class EastmoneyStockNewsConfig:
    enabled: bool
    request_interval_seconds: float


@dataclass(frozen=True, slots=True)
class TushareNewsConfig:
    enabled: bool
    api_key_env: str
    source: str
    endpoint: str


@dataclass(frozen=True, slots=True)
class NewsConfig:
    enabled: bool
    lookback_hours: float
    max_items_per_stock: int
    raw_cache_directory: Path | None
    cninfo: CninfoNewsConfig
    eastmoney_stock_news: EastmoneyStockNewsConfig
    tushare: TushareNewsConfig


def load_news_config(path: str | Path) -> NewsConfig:
    with Path(path).open(encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file)
    news = _mapping(_mapping(raw, "root").get("news"), "news")
    cninfo = _mapping(news.get("cninfo"), "news.cninfo")
    eastmoney = _mapping(news.get("eastmoney_stock_news"), "news.eastmoney_stock_news")
    tushare = _mapping(news.get("tushare"), "news.tushare")
    raw_directory = str(news["raw_cache_directory"]).strip()
    config = NewsConfig(
        enabled=bool(news["enabled"]),
        lookback_hours=float(news["lookback_hours"]),
        max_items_per_stock=int(news["max_items_per_stock"]),
        raw_cache_directory=Path(raw_directory) if raw_directory else None,
        cninfo=CninfoNewsConfig(
            enabled=bool(cninfo["enabled"]),
            page_size=int(cninfo["page_size"]),
            request_interval_seconds=float(cninfo["request_interval_seconds"]),
        ),
        eastmoney_stock_news=EastmoneyStockNewsConfig(
            enabled=bool(eastmoney["enabled"]),
            request_interval_seconds=float(eastmoney["request_interval_seconds"]),
        ),
        tushare=TushareNewsConfig(
            enabled=bool(tushare["enabled"]),
            api_key_env=str(tushare["api_key_env"]),
            source=str(tushare["source"]),
            endpoint=str(tushare["endpoint"]).rstrip("/"),
        ),
    )
    if config.lookback_hours <= 0 or config.max_items_per_stock <= 0:
        raise ValueError("News lookback and items-per-stock must be positive")
    if config.cninfo.page_size <= 0 or config.cninfo.request_interval_seconds < 0:
        raise ValueError("CNINFO page size must be positive and interval cannot be negative")
    if config.eastmoney_stock_news.request_interval_seconds < 0:
        raise ValueError("Eastmoney request interval cannot be negative")
    if not config.tushare.api_key_env or not config.tushare.source:
        raise ValueError("Tushare API-key environment variable and source are required")
    if not config.tushare.endpoint.startswith("https://"):
        raise ValueError("Tushare endpoint must use HTTPS")
    return config


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected a mapping at {path}")
    return value
