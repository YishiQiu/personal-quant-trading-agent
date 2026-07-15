from __future__ import annotations

import json

from trading_agent.config_llm import LlmProviderConfig
from trading_agent.llm.deepseek import DeepSeekLlmResearchClient


class _FakeResponse:
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        return False

    def read(self) -> bytes:
        return b'{"choices":[{"message":{"content":"{\\"recommendation_index\\":50,\\"thesis\\":\\"test\\",\\"stop_loss\\":null,\\"take_profit\\":null,\\"expected_holding_period\\":null}"}}]}'


def test_deepseek_client_uses_its_current_model_endpoint_and_max_tokens(monkeypatch, quote_factory) -> None:
    from trading_agent.domain.analysis import CandleMetrics, PatternCandidate
    from trading_agent.domain.models import Candidate

    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout: float):
        captured["request"] = request
        return _FakeResponse()

    monkeypatch.setattr("trading_agent.llm.openai_compatible.urlopen", fake_urlopen)
    config = LlmProviderConfig(
        enabled=True,
        provider="deepseek",
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        timeout_seconds=30,
        max_completion_tokens=256,
    )
    candidate = PatternCandidate(
        Candidate(quote_factory(open_price=10.0, high_price=10.5, low_price=9.5), 1.5),
        CandleMetrics(0.01, 0.49, 0.5, ("doji",)),
    )

    result = DeepSeekLlmResearchClient("private-key", config).research(candidate, ())
    request = captured["request"]
    body = json.loads(request.data.decode("utf-8"))

    assert request.full_url == "https://api.deepseek.com/chat/completions"
    assert body["model"] == "deepseek-v4-flash"
    assert body["max_tokens"] == 256
    assert "max_completion_tokens" not in body
    assert result.recommendation_index == 50
