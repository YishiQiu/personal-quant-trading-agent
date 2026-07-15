"""Configuration for the optional, provider-pluggable LLM research stage."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True, slots=True)
class LlmProviderConfig:
    enabled: bool
    provider: str
    model: str
    base_url: str
    api_key_env: str
    timeout_seconds: float
    max_completion_tokens: int


def load_llm_provider_config(path: str | Path) -> LlmProviderConfig:
    with Path(path).open(encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file)
    if not isinstance(raw, Mapping) or not isinstance(raw.get("llm"), Mapping):
        raise ValueError("Expected an llm mapping in LLM configuration")
    llm: Mapping[str, Any] = raw["llm"]
    config = LlmProviderConfig(
        enabled=bool(llm["enabled"]),
        provider=str(llm["provider"]).casefold(),
        model=str(llm["model"]),
        base_url=str(llm["base_url"]).rstrip("/"),
        api_key_env=str(llm["api_key_env"]),
        timeout_seconds=float(llm["timeout_seconds"]),
        max_completion_tokens=int(llm["max_completion_tokens"]),
    )
    if config.provider not in {"kimi", "deepseek"}:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")
    if not config.base_url.startswith("https://"):
        raise ValueError("LLM base_url must use HTTPS")
    if not config.model or not config.api_key_env:
        raise ValueError("LLM model and api_key_env must not be empty")
    if config.timeout_seconds <= 0 or config.max_completion_tokens <= 0:
        raise ValueError("LLM timeout and max completion tokens must be positive")
    return config
