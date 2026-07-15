from __future__ import annotations

import json

import pytest

from trading_agent.config_llm import LlmProviderConfig
from trading_agent.domain.analysis import CandleMetrics, PatternCandidate
from trading_agent.domain.models import Candidate
from trading_agent.llm.kimi import KimiLlmResearchClient, KimiResearchError


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _config() -> LlmProviderConfig:
    return LlmProviderConfig(
        enabled=True,
        provider="kimi",
        model="kimi-k2.6",
        base_url="https://api.moonshot.ai/v1",
        api_key_env="MOONSHOT_API_KEY",
        timeout_seconds=30,
        max_completion_tokens=900,
    )


def _candidate(quote_factory) -> PatternCandidate:
    return PatternCandidate(
        candidate=Candidate(quote_factory(open_price=10.0, high_price=10.5, low_price=9.5), 1.5),
        candle=CandleMetrics(0.01, 0.49, 0.5, ("doji",)),
    )


def test_kimi_client_sends_json_mode_and_parses_research(monkeypatch, quote_factory) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout: float):
        captured["request"] = request
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "recommendation_index": 67.5,
                                    "thesis": "形态与趋势一致，但缺少新闻证据。",
                                    "stop_loss": 9.5,
                                    "take_profit": 10.8,
                                    "expected_holding_period": "1 个交易日",
                                }
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("trading_agent.llm.openai_compatible.urlopen", fake_urlopen)
    finding = KimiLlmResearchClient("private-key", _config()).research(
        _candidate(quote_factory), ("Trend: bullish",)
    )

    request = captured["request"]
    body = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "https://api.moonshot.ai/v1/chat/completions"
    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    assert finding.recommendation_index == 67.5
    assert finding.stop_loss == 9.5
    assert finding.expected_holding_period == "1 个交易日"


def test_kimi_client_rejects_an_invalid_research_score(monkeypatch, quote_factory) -> None:
    def fake_urlopen(request, timeout: float):
        return _FakeResponse(
            {"choices": [{"message": {"content": '{"recommendation_index": 101, "thesis": "x"}'}}]}
        )

    monkeypatch.setattr("trading_agent.llm.openai_compatible.urlopen", fake_urlopen)

    with pytest.raises(KimiResearchError, match="invalid research JSON"):
        KimiLlmResearchClient("private-key", _config()).research(_candidate(quote_factory), ())
