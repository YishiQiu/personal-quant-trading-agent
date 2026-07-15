"""Candidate-only free news fallback using AKShare's Eastmoney adapter.

This is deliberately not part of the all-market scanner.  Eastmoney's public
web search is queried only after deterministic pattern selection, and returned
articles retain their original link for manual verification.  It is a best-
effort personal-research source rather than a licensed or SLA-backed feed.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

from trading_agent.domain.models import NewsItem
from trading_agent.news.base import NewsProvider, NewsTarget

logger = logging.getLogger(__name__)

FrameFetcher = Callable[[str], object]
Row = Mapping[str, Any]


class EastmoneyStockNewsProvider(NewsProvider):
    """Retrieve recent, source-attributed articles for each research candidate."""

    name = "eastmoney_stock_news"

    def __init__(
        self,
        *,
        request_interval_seconds: float,
        fetch_frame: FrameFetcher | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if request_interval_seconds < 0:
            raise ValueError("Eastmoney request interval cannot be negative")
        self._request_interval_seconds = request_interval_seconds
        self._fetch_frame = fetch_frame or _akshare_stock_news
        self._sleep = sleep

    def fetch(
        self, targets: Sequence[NewsTarget], since: datetime, until: datetime
    ) -> Sequence[NewsItem]:
        if since > until:
            raise ValueError("Eastmoney start time cannot be after end time")
        items: list[NewsItem] = []
        for index, target in enumerate(targets):
            if index:
                self._sleep(self._request_interval_seconds)
            try:
                rows = _rows(self._fetch_frame(target.code))
            except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
                # A public-source failure for one candidate must not discard
                # successfully collected evidence for the remaining candidates.
                logger.warning(
                    "Eastmoney candidate-news lookup failed",
                    extra={"provider": self.name, "code": target.code, "reason": str(exc)},
                )
                continue
            items.extend(_items_from_rows(rows, target, since, until))
        return tuple(items)


def _akshare_stock_news(code: str) -> object:
    try:
        import akshare as ak
    except ImportError as exc:  # pragma: no cover - optional dependency boundary
        raise ImportError("Install the data extra to use Eastmoney candidate news") from exc
    return ak.stock_news_em(symbol=code)


def _rows(frame: object) -> Sequence[Row]:
    to_dict = getattr(frame, "to_dict", None)
    if not callable(to_dict):
        raise ValueError("AKShare Eastmoney response is not a tabular result")
    rows = to_dict(orient="records")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("AKShare Eastmoney response contains invalid rows")
    return rows


def _items_from_rows(
    rows: Sequence[Row], target: NewsTarget, since: datetime, until: datetime
) -> tuple[NewsItem, ...]:
    items: list[NewsItem] = []
    for row in rows:
        headline = _text(row.get("新闻标题"))
        summary = _text(row.get("新闻内容"))
        published_at = _published_at(row.get("发布时间"), since)
        if (
            not headline
            or published_at is None
            or not since <= published_at <= until
            or not _mentions_target(target, headline, summary)
        ):
            continue
        url = _canonical_url(_text(row.get("新闻链接")))
        media = _text(row.get("文章来源")) or "东方财富"
        items.append(
            NewsItem(
                headline=headline,
                published_at=published_at,
                source=f"东方财富/{media}",
                url=url,
                related_codes=(target.code,),
                summary=summary[:800] or None,
            )
        )
    return tuple(items)


def _text(value: object) -> str:
    return re.sub(r"<[^>]+>", "", str(value or "")).strip()


def _published_at(value: object, since: datetime) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    for candidate in (text, text.replace(" ", "T", 1)):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=since.tzinfo)
        except ValueError:
            continue
    return None


def _canonical_url(url: str) -> str | None:
    if not url:
        return None
    if url.startswith("http://finance.eastmoney.com/"):
        return "https://" + url.removeprefix("http://")
    return url if url.startswith("https://") else None


def _mentions_target(target: NewsTarget, headline: str, summary: str) -> bool:
    """Avoid treating a broad search result as evidence for a candidate stock."""

    text = headline + "\n" + summary
    return target.code in text or (len(target.name) >= 2 and target.name in text)
