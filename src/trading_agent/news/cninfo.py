"""从巨潮资讯公开披露服务获取候选股公告。

巨潮资讯是法定信息披露平台。本适配器以较低频率访问其公开网页接口，
定位是备用来源，并非有服务协议保障的商业行情接口。每条记录都会保留
官方 PDF 链接，方便后续分析核对原文。
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from trading_agent.domain.models import NewsItem
from trading_agent.news.base import NewsProvider, NewsProviderError, NewsTarget

JsonObject = Mapping[str, Any]
JsonPoster = Callable[[str, Mapping[str, object]], object]
JsonFetcher = Callable[[str], object]


class CninfoPublicDisclosureProvider(NewsProvider):
    """只为已经入围的股票查询公司公告。"""

    name = "cninfo_public_disclosure"
    _ENDPOINT = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    _STOCK_DIRECTORY_ENDPOINT = "https://www.cninfo.com.cn/new/data/szse_stock.json"
    _PDF_PREFIX = "https://static.cninfo.com.cn/"

    def __init__(
        self,
        *,
        page_size: int,
        request_interval_seconds: float,
        post_json: JsonPoster | None = None,
        get_json: JsonFetcher | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if page_size <= 0 or request_interval_seconds < 0:
            raise ValueError("CNINFO page size must be positive and interval cannot be negative")
        self._page_size = page_size
        self._request_interval_seconds = request_interval_seconds
        self._post_json = post_json or _post_json
        self._get_json = get_json or _get_json
        self._sleep = sleep

    def fetch(
        self, targets: Sequence[NewsTarget], since: datetime, until: datetime
    ) -> Sequence[NewsItem]:
        if since > until:
            raise ValueError("CNINFO start time cannot be after end time")
        organization_ids = self._organization_ids(targets)
        items: list[NewsItem] = []
        requested = 0
        for target in targets:
            organization_id = organization_ids.get(target.code)
            if organization_id is None:
                continue
            if requested:
                self._sleep(self._request_interval_seconds)
            requested += 1
            document = self._request_target(target, organization_id, since, until)
            items.extend(_items_from_document(document, target))
        return tuple(items)

    def _request_target(
        self, target: NewsTarget, organization_id: str, since: datetime, until: datetime
    ) -> JsonObject:
        payload = {
            "pageNum": 1,
            "pageSize": self._page_size,
            "column": _exchange_column(target.code),
            "tabName": "fulltext",
            "plate": "",
            # 巨潮接口需要内部组织编号，不能传公司名称；传名称时接口会悄悄忽略筛选条件。
            "stock": f"{target.code},{organization_id}",
            "searchkey": "",
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": f"{since:%Y-%m-%d}~{until:%Y-%m-%d}",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        try:
            document = self._post_json(self._ENDPOINT, payload)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise NewsProviderError("CNINFO public disclosure request failed") from exc
        if not isinstance(document, Mapping):
            raise NewsProviderError("CNINFO returned an invalid response")
        return document

    def _organization_ids(self, targets: Sequence[NewsTarget]) -> dict[str, str]:
        try:
            document = self._get_json(self._STOCK_DIRECTORY_ENDPOINT)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise NewsProviderError("CNINFO stock directory request failed") from exc
        if not isinstance(document, Mapping):
            raise NewsProviderError("CNINFO stock directory returned an invalid response")
        rows = document.get("stockList")
        if not isinstance(rows, list):
            raise NewsProviderError("CNINFO stock directory has no stock list")
        required_codes = {target.code for target in targets}
        organization_ids: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            code = str(row.get("code", "")).strip().zfill(6)
            organization_id = str(row.get("orgId", "")).strip()
            if code in required_codes and organization_id:
                organization_ids[code] = organization_id
        return organization_ids


def _post_json(url: str, payload: Mapping[str, object]) -> object:
    request = Request(
        url,
        data=urlencode(payload).encode("utf-8"),
        headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.cninfo.com.cn",
            "Referer": "https://www.cninfo.com.cn/",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "PersonalQuantTradingAgent/0.1 (+local-research)",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310 - 地址是固定的公开接口
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> object:
    request = Request(
        url,
        headers={
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.cninfo.com.cn/",
            "User-Agent": "PersonalQuantTradingAgent/0.1 (+local-research)",
        },
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310 - 地址是固定的公开接口
        return json.loads(response.read().decode("utf-8"))


def _items_from_document(document: JsonObject, target: NewsTarget) -> tuple[NewsItem, ...]:
    rows = document.get("announcements", ())
    if not isinstance(rows, list):
        raise NewsProviderError("CNINFO response has no announcement list")
    items: list[NewsItem] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        # 服务端筛选一旦失效，返回内容就不能当作候选股证据。
        returned_code = str(row.get("secCode", "")).strip().zfill(6)
        if returned_code != target.code:
            continue
        title = str(row.get("announcementTitle", "")).strip()
        adjunct_url = str(row.get("adjunctUrl", "")).strip().lstrip("/")
        published_at = _published_at(row.get("announcementTime"))
        if not title or published_at is None:
            continue
        url = CninfoPublicDisclosureProvider._PDF_PREFIX + adjunct_url if adjunct_url else None
        items.append(
            NewsItem(
                headline=title,
                published_at=published_at,
                source="CNINFO announcement",
                url=url,
                related_codes=(target.code,),
                summary=None,
            )
        )
    return tuple(items)


def _published_at(value: object) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _exchange_column(code: str) -> str:
    if code.startswith(("5", "6", "9")):
        return "sse"
    return "szse"
