"""通过 AKShare 的东方财富适配器，为候选股补充免费新闻。

这个来源不会加入全市场扫描。只有确定性形态筛选结束后，才会查询东方财富
公开网页搜索，返回文章也会保留原始链接供人工核对。它适合尽力而为的个人
研究，不是获得授权或服务等级协议保障的数据服务。
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
    """为每只研究候选股获取近期且带来源的文章。"""

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
                # 单只候选股的公开源请求失败，不能丢掉其他候选股已经收集成功的证据。
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
    except ImportError as exc:  # pragma: no cover - 可选依赖的边界
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
    """避免把宽泛的搜索结果误当成候选股证据。"""

    text = headline + "\n" + summary
    return target.code in text or (len(target.name) >= 2 and target.name in text)
