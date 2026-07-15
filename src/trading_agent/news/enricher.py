"""为研究候选股容错补充新闻，并在本地保留原始证据。"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timedelta
from trading_agent.config_news import NewsConfig
from trading_agent.domain.models import NewsItem, ResearchContext
from trading_agent.news.base import NewsProvider, NewsProviderError, NewsTarget

logger = logging.getLogger(__name__)


class NewsEnricher:
    """附加可追溯来源的记录，新闻源中断时仍允许研究继续。"""

    def __init__(self, config: NewsConfig, providers: Sequence[NewsProvider]) -> None:
        self._config = config
        self._providers = tuple(providers)

    def enrich(
        self,
        contexts: Mapping[str, ResearchContext],
        targets: Sequence[NewsTarget],
        as_of: datetime,
    ) -> dict[str, ResearchContext]:
        if not self._config.enabled or not targets:
            return dict(contexts)
        since = as_of - timedelta(hours=self._config.lookback_hours)
        records: list[NewsItem] = []
        successful_providers: list[str] = []
        for provider in self._providers:
            try:
                records.extend(provider.fetch(targets, since, as_of))
                successful_providers.append(provider.name)
            except NewsProviderError as exc:
                logger.warning("News source unavailable", extra={"provider": provider.name, "reason": str(exc)})
        self._archive(records, successful_providers, since, as_of)
        records_by_code = _group_records(records, self._config.max_items_per_stock)
        return {
            code: replace(context, news=_merge(context.news, records_by_code.get(code, ())))
            for code, context in contexts.items()
        }

    def _archive(
        self,
        records: Sequence[NewsItem],
        successful_providers: Sequence[str],
        since: datetime,
        as_of: datetime,
    ) -> None:
        directory = self._config.raw_cache_directory
        if directory is None:
            return
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / as_of.strftime("news-evidence-%Y%m%dT%H%M%S%z.json")
        document = {
            "kind": "source-attributed-news-evidence",
            "collected_at": as_of.isoformat(),
            "window_start": since.isoformat(),
            "providers": list(successful_providers),
            "items": [
                {
                    "headline": item.headline,
                    "published_at": item.published_at.isoformat(),
                    "source": item.source,
                    "url": item.url,
                    "related_codes": list(item.related_codes),
                    "summary": item.summary,
                }
                for item in records
            ],
        }
        target.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")


def _group_records(records: Sequence[NewsItem], limit: int) -> dict[str, tuple[NewsItem, ...]]:
    grouped: dict[str, list[NewsItem]] = {}
    for item in records:
        for code in item.related_codes:
            grouped.setdefault(code, []).append(item)
    return {
        code: tuple(sorted(items, key=lambda item: item.published_at, reverse=True)[:limit])
        for code, items in grouped.items()
    }


def _merge(existing: Sequence[NewsItem], fetched: Sequence[NewsItem]) -> tuple[NewsItem, ...]:
    merged: list[NewsItem] = []
    seen: set[tuple[str, str, datetime, str | None]] = set()
    for item in (*existing, *fetched):
        key = (item.source, item.headline, item.published_at, item.url)
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return tuple(sorted(merged, key=lambda item: item.published_at, reverse=True))
