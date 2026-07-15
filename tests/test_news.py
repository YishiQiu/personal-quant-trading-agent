from __future__ import annotations

import json
from datetime import datetime, timezone

from trading_agent.config_news import (
    CninfoNewsConfig,
    EastmoneyStockNewsConfig,
    NewsConfig,
    TushareNewsConfig,
)
from trading_agent.domain.models import NewsItem, ResearchContext
from trading_agent.news.base import NewsProvider, NewsTarget
from trading_agent.news.cninfo import CninfoPublicDisclosureProvider
from trading_agent.news.eastmoney import EastmoneyStockNewsProvider
from trading_agent.news.enricher import NewsEnricher
from trading_agent.news.tushare import TushareMajorNewsProvider


def test_cninfo_provider_keeps_official_announcement_link() -> None:
    captured: dict[str, object] = {}

    def post(url: str, payload: object) -> object:
        captured["url"] = url
        captured["payload"] = payload
        return {
            "announcements": [
                {
                    "secCode": "000001",
                    "announcementTitle": "平安银行：关于回购股份的公告",
                    "announcementTime": 1_784_000_000_000,
                    "adjunctUrl": "finalpage/2026-07-14/123.pdf",
                }
            ]
        }

    provider = CninfoPublicDisclosureProvider(
        page_size=5,
        request_interval_seconds=0,
        post_json=post,
        get_json=lambda _: {"stockList": [{"code": "000001", "orgId": "gssz0000001"}]},
    )
    items = provider.fetch(
        (NewsTarget("000001", "平安银行"),),
        datetime(2026, 7, 13, tzinfo=timezone.utc),
        datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert captured["url"] == "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    assert captured["payload"] == {
        "pageNum": 1,
        "pageSize": 5,
        "column": "szse",
        "tabName": "fulltext",
        "plate": "",
        "stock": "000001,gssz0000001",
        "searchkey": "",
        "secid": "",
        "category": "",
        "trade": "",
        "seDate": "2026-07-13~2026-07-14",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    assert items[0].url == "https://static.cninfo.com.cn/finalpage/2026-07-14/123.pdf"
    assert items[0].related_codes == ("000001",)


def test_cninfo_provider_drops_rows_when_the_server_returns_a_different_code() -> None:
    provider = CninfoPublicDisclosureProvider(
        page_size=5,
        request_interval_seconds=0,
        post_json=lambda _url, _payload: {
            "announcements": [
                {
                    "secCode": "600519",
                    "announcementTitle": "无关公告",
                    "announcementTime": 1_784_000_000_000,
                }
            ]
        },
        get_json=lambda _: {"stockList": [{"code": "000001", "orgId": "gssz0000001"}]},
    )

    items = provider.fetch(
        (NewsTarget("000001", "平安银行"),),
        datetime(2026, 7, 13, tzinfo=timezone.utc),
        datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert items == ()


def test_tushare_provider_matches_only_named_candidates() -> None:
    def post(url: str, payload: object) -> object:
        return {
            "code": 0,
            "data": {
                "fields": ["title", "content", "pub_time", "src"],
                "items": [
                    ["平安银行获批新业务", "000001 平安银行发布公告", "2026-07-14 13:45:00", "财联社"],
                    ["宏观政策新闻", "与候选公司无关", "2026-07-14 13:40:00", "财联社"],
                ],
            },
        }

    provider = TushareMajorNewsProvider(
        token="test-token",
        source="财联社",
        endpoint="https://api.waditu.com",
        post_json=post,
    )
    items = provider.fetch(
        (NewsTarget("000001", "平安银行"), NewsTarget("300001", "特锐德")),
        datetime(2026, 7, 13),
        datetime(2026, 7, 14),
    )

    assert len(items) == 1
    assert items[0].related_codes == ("000001",)
    assert items[0].source == "Tushare/财联社"
    assert items[0].url is None


def test_eastmoney_provider_keeps_only_in_window_source_attributed_candidate_news() -> None:
    class Frame:
        def to_dict(self, *, orient: str):  # type: ignore[no-untyped-def]
            assert orient == "records"
            return [
                {
                    "新闻标题": "<em>平安银行</em>发布回购方案",
                    "新闻内容": "<em>平安银行</em>公告回购股份",
                    "发布时间": "2026-07-14 13:45:00",
                    "文章来源": "证券时报",
                    "新闻链接": "http://finance.eastmoney.com/a/202607141234.html",
                },
                {
                    "新闻标题": "过期新闻",
                    "新闻内容": "不应进入结果",
                    "发布时间": "2026-07-12 13:45:00",
                    "文章来源": "证券时报",
                    "新闻链接": "https://finance.eastmoney.com/a/old.html",
                },
                {
                    "新闻标题": "无关市场新闻",
                    "新闻内容": "没有候选公司名称或代码",
                    "发布时间": "2026-07-14 13:40:00",
                    "文章来源": "证券时报",
                    "新闻链接": "https://finance.eastmoney.com/a/unrelated.html",
                },
            ]

    provider = EastmoneyStockNewsProvider(
        request_interval_seconds=0,
        fetch_frame=lambda _code: Frame(),
    )
    items = provider.fetch(
        (NewsTarget("000001", "平安银行"),),
        datetime(2026, 7, 13, 14, 30, tzinfo=timezone.utc),
        datetime(2026, 7, 14, 14, 30, tzinfo=timezone.utc),
    )

    assert len(items) == 1
    assert items[0].headline == "平安银行发布回购方案"
    assert items[0].source == "东方财富/证券时报"
    assert items[0].url == "https://finance.eastmoney.com/a/202607141234.html"
    assert items[0].related_codes == ("000001",)


def test_news_enricher_attaches_records_and_archives_source_evidence(tmp_path) -> None:
    class StaticProvider(NewsProvider):
        name = "static"

        def fetch(self, targets, since, until):  # type: ignore[no-untyped-def]
            return (
                NewsItem(
                    headline="平安银行回购股份",
                    published_at=datetime(2026, 7, 14, 14, 0, tzinfo=timezone.utc),
                    source="CNINFO announcement",
                    url="https://example.test/a.pdf",
                    related_codes=("000001",),
                ),
            )

    config = NewsConfig(
        enabled=True,
        lookback_hours=30,
        max_items_per_stock=5,
        raw_cache_directory=tmp_path,
        cninfo=CninfoNewsConfig(True, 10, 0),
        eastmoney_stock_news=EastmoneyStockNewsConfig(True, 0),
        tushare=TushareNewsConfig(True, "TUSHARE_TOKEN", "财联社", "https://api.waditu.com"),
    )
    result = NewsEnricher(config, (StaticProvider(),)).enrich(
        {"000001": ResearchContext(code="000001")},
        (NewsTarget("000001", "平安银行"),),
        datetime(2026, 7, 14, 14, 30, tzinfo=timezone.utc),
    )

    assert result["000001"].news[0].headline == "平安银行回购股份"
    evidence_files = list(tmp_path.glob("news-evidence-*.json"))
    assert len(evidence_files) == 1
    document = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert document["providers"] == ["static"]
    assert document["items"][0]["url"] == "https://example.test/a.pdf"
