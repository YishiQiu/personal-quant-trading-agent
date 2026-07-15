"""Explicit provider registry for replaceable data-source adapters."""

from __future__ import annotations

from typing import TypeAlias

from trading_agent.providers.base import MarketDataProvider

ProviderFactory: TypeAlias = type[MarketDataProvider]


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderFactory] = {}

    def register(self, provider: ProviderFactory) -> None:
        key = provider.name.strip().lower()
        if not key:
            raise ValueError("Provider name cannot be blank")
        if key in self._providers:
            raise ValueError(f"Provider already registered: {key}")
        self._providers[key] = provider

    def create(self, name: str) -> MarketDataProvider:
        try:
            return self._providers[name.lower()]()
        except KeyError as exc:
            available = ", ".join(sorted(self._providers)) or "none"
            raise ValueError(f"Unknown provider '{name}'. Available: {available}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))
