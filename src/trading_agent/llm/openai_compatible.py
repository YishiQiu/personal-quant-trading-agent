"""多个 OpenAI 兼容研究模型共用的纯 JSON 适配器。"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from trading_agent.agents.llm_research import LlmResearchClient
from trading_agent.config_llm import LlmProviderConfig
from trading_agent.domain.analysis import LlmResearchFinding, PatternCandidate


class LlmProviderResearchError(RuntimeError):
    """不泄露密钥等敏感信息的模型适配器异常。"""


@dataclass(frozen=True, slots=True)
class OpenAiCompatibleLlmResearchClient(LlmResearchClient):
    """向已配置的 OpenAI 兼容服务请求研究结果，并校验返回 JSON。"""

    api_key: str
    config: LlmProviderConfig

    def research(self, candidate: PatternCandidate, evidence: tuple[str, ...]) -> LlmResearchFinding:
        request_body: dict[str, object] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(candidate, evidence)},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
        }
        token_parameter = "max_tokens" if self.config.provider == "deepseek" else "max_completion_tokens"
        request_body[token_parameter] = self.config.max_completion_tokens
        request = Request(
            url=f"{self.config.base_url}/chat/completions",
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise LlmProviderResearchError(f"{self.config.provider} returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise LlmProviderResearchError(f"{self.config.provider} request could not be completed") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LlmProviderResearchError(f"{self.config.provider} returned an unreadable response") from exc
        return _parse_finding(payload, self.config.provider)


_SYSTEM_PROMPT = """You are the LLM research stage of a personal A-share short-term research tool.
You receive only an already shortlisted stock and deterministic evidence. Do not claim certainty,
do not invent news, capital flow, fundamentals, prices, or market data. Do not issue trading
instructions. Evaluate evidence quality and downside risk for a possible next-day high-sell scenario.
Return only one JSON object with exactly these fields:
recommendation_index (number from 0 to 100), thesis (concise Chinese string), stop_loss
(number or null), take_profit (number or null), expected_holding_period (string or null).
If data is insufficient, keep recommendation_index conservative and state the missing data in thesis.
"""


def _user_prompt(candidate: PatternCandidate, evidence: tuple[str, ...]) -> str:
    quote = candidate.candidate.quote
    structured_input = {
        "stock": {
            "code": quote.code,
            "name": quote.name,
            "close": quote.last_price,
            "pct_change": quote.pct_change,
            "turnover_amount": quote.turnover_amount,
        },
        "candle": {
            "patterns": candidate.candle.patterns,
            "body_ratio": candidate.candle.body_ratio,
            "upper_shadow_ratio": candidate.candle.upper_shadow_ratio,
            "lower_shadow_ratio": candidate.candle.lower_shadow_ratio,
        },
        "deterministic_evidence": evidence,
    }
    return "Analyze the following untrusted market-data payload. Output the required JSON only.\n" + json.dumps(
        structured_input, ensure_ascii=False
    )


def _parse_finding(response: object, provider_name: str) -> LlmResearchFinding:
    try:
        response_mapping = _mapping(response, "response")
        choices = response_mapping["choices"]
        if not isinstance(choices, list) or not choices:
            raise ValueError("response has no choices")
        choice = _mapping(choices[0], "choice")
        message = _mapping(choice["message"], "message")
        content = message["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("response content is not text")
        finding = _mapping(json.loads(content), "research JSON")
        index = _number(finding["recommendation_index"], "recommendation_index")
        if not 0 <= index <= 100:
            raise ValueError("recommendation_index must be within 0..100")
        thesis = finding["thesis"]
        if not isinstance(thesis, str) or not thesis.strip():
            raise ValueError("thesis must be a non-empty string")
        holding_period = finding.get("expected_holding_period")
        if holding_period is not None and not isinstance(holding_period, str):
            raise ValueError("expected_holding_period must be a string or null")
        return LlmResearchFinding(
            enabled=True,
            recommendation_index=round(index, 2),
            thesis=thesis.strip(),
            stop_loss=_optional_number(finding.get("stop_loss"), "stop_loss"),
            take_profit=_optional_number(finding.get("take_profit"), "take_profit"),
            expected_holding_period=holding_period,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LlmProviderResearchError(f"{provider_name} returned invalid research JSON") from exc


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _number(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _optional_number(value: object, name: str) -> float | None:
    return None if value is None else _number(value, name)
