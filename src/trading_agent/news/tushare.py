"""使用 Tushare ``major_news`` 交叉核对候选股催化信息。"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from trading_agent.domain.models import NewsItem
from trading_agent.news.base import NewsProvider, NewsProviderError, NewsTarget

JsonObject = Mapping[str, Any]
JsonPoster = Callable[[str, Mapping[str, object]], object]


class TushareMajorNewsProvider(NewsProvider):
    """读取范围受限的单一资讯源，只匹配明确出现的股票代码或名称。"""

    name = "tushare_major_news"

    def __init__(
        self,
        *,
        token: str,
        source: str,
        endpoint: str,
        post_json: JsonPoster | None = None,
    ) -> None:
        if not token.strip() or not source.strip() or not endpoint.startswith("https://"):
            raise ValueError("Tushare requires a token, source, and HTTPS endpoint")
        self._token = token
        self._source = source
        self._endpoint = endpoint.rstrip("/")
        self._post_json = post_json or _post_json

    def fetch(
        self, targets: Sequence[NewsTarget], since: datetime, until: datetime
    ) -> Sequence[NewsItem]:
        if since > until:
            raise ValueError("Tushare start time cannot be after end time")
        document = self._request(since, until)
        return _matched_items(document, targets, self._source)

    def _request(self, since: datetime, until: datetime) -> JsonObject:
        payload = {
            "api_name": "major_news",
            "token": self._token,
            "params": {
                "src": self._source,
                "start_date": since.strftime("%Y%m%d"),
                "end_date": until.strftime("%Y%m%d"),
            },
            "fields": "title,content,pub_time,src",
        }
        try:
            document = self._post_json(self._endpoint, payload)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise NewsProviderError("Tushare major_news request failed") from exc
        if not isinstance(document, Mapping):
            raise NewsProviderError("Tushare returned an invalid response")
        if int(document.get("code", 0)) != 0:
            message = str(document.get("msg", "unknown error")).strip()
            raise NewsProviderError(f"Tushare major_news rejected the request: {message}")
        return document


def _post_json(url: str, payload: Mapping[str, object]) -> object:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "PersonalQuantTradingAgent/0.1"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310 - 配置项限定为 HTTPS 地址
        return json.loads(response.read().decode("utf-8"))


def _matched_items(
    document: JsonObject, targets: Sequence[NewsTarget], configured_source: str
) -> tuple[NewsItem, ...]:
    data = document.get("data")
    if not isinstance(data, Mapping):
        raise NewsProviderError("Tushare major_news response has no data object")
    fields = data.get("fields")
    rows = data.get("items")
    if not isinstance(fields, list) or not isinstance(rows, list):
        raise NewsProviderError("Tushare major_news response has invalid rows")
    positions = {str(field): index for index, field in enumerate(fields)}
    required = {"title", "content", "pub_time", "src"}
    if not required.issubset(positions):
        raise NewsProviderError("Tushare major_news response is missing requested fields")
    items: list[NewsItem] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < len(fields):
            continue
        title = str(row[positions["title"]] or "").strip()
        content = str(row[positions["content"]] or "").strip()
        published_at = _parse_time(row[positions["pub_time"]])
        if not title or published_at is None:
            continue
        matched = tuple(target.code for target in targets if _mentions(target, title, content))
        if not matched:
            continue
        source = str(row[positions["src"]] or configured_source).strip() or configured_source
        items.append(
            NewsItem(
                headline=title,
                published_at=published_at,
                source=f"Tushare/{source}",
                url=None,
                related_codes=matched,
                summary=content[:800] or None,
            )
        )
    return tuple(items)


def _mentions(target: NewsTarget, title: str, content: str) -> bool:
    text = title + "\n" + content
    return target.code in text or (len(target.name.strip()) >= 2 and target.name in text)


def _parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for candidate in (text, text.replace(" ", "T", 1)):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None
