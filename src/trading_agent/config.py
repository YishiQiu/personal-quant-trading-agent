"""Configuration loading kept outside business logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True, slots=True)
class MarketScannerConfig:
    exclude_st: bool
    exclude_delisting: bool
    min_price: float
    max_price: float
    min_turnover_amount: float
    max_abs_pct_change: float
    max_candidates: int

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "MarketScannerConfig":
        try:
            config = cls(
                exclude_st=bool(raw["exclude_st"]),
                exclude_delisting=bool(raw["exclude_delisting"]),
                min_price=float(raw["min_price"]),
                max_price=float(raw["max_price"]),
                min_turnover_amount=float(raw["min_turnover_amount"]),
                max_abs_pct_change=float(raw["max_abs_pct_change"]),
                max_candidates=int(raw["max_candidates"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid market_scanner configuration") from exc
        if config.min_price < 0 or config.max_price <= config.min_price:
            raise ValueError("max_price must be greater than a non-negative min_price")
        if config.min_turnover_amount < 0 or config.max_candidates < 0:
            raise ValueError("min_turnover_amount and max_candidates must be non-negative")
        return config


def load_market_scanner_config(path: str | Path) -> MarketScannerConfig:
    """Load a market scanner configuration from a YAML document."""

    with Path(path).open(encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file)
    if not isinstance(raw, Mapping) or not isinstance(raw.get("market_scanner"), Mapping):
        raise ValueError("Expected a top-level market_scanner mapping")
    return MarketScannerConfig.from_mapping(raw["market_scanner"])
