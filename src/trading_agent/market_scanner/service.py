"""Fast deterministic filtering; deliberately no LLM calls live here."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from trading_agent.config import MarketScannerConfig
from trading_agent.domain.models import Candidate, QuoteSnapshot, Rejection, ScanResult


class MarketScanner:
    def __init__(self, config: MarketScannerConfig) -> None:
        self._config = config

    def scan(self, quotes: Iterable[QuoteSnapshot], scanned_at: datetime | None = None) -> ScanResult:
        candidates: list[Candidate] = []
        rejections: list[Rejection] = []
        input_count = 0
        for quote in quotes:
            input_count += 1
            reasons = self._rejection_reasons(quote)
            if reasons:
                rejections.append(Rejection(quote=quote, reasons=tuple(reasons)))
                continue
            candidates.append(Candidate(quote=quote, liquidity_score=self._liquidity_score(quote)))

        ranked = sorted(
            candidates,
            key=lambda candidate: (candidate.liquidity_score, candidate.quote.turnover_amount),
            reverse=True,
        )
        if self._config.max_candidates > 0:
            ranked = ranked[: self._config.max_candidates]
        return ScanResult(
            scanned_at=scanned_at or datetime.now().astimezone(),
            candidates=tuple(ranked),
            rejections=tuple(rejections),
            input_count=input_count,
        )

    def _rejection_reasons(self, quote: QuoteSnapshot) -> list[str]:
        reasons: list[str] = []
        if self._config.exclude_st and quote.is_st:
            reasons.append("st")
        if self._config.exclude_delisting and quote.is_delisting:
            reasons.append("delisting")
        if not self._config.min_price <= quote.last_price <= self._config.max_price:
            reasons.append("price_out_of_range")
        if not self._config.include_chinext and is_chinext_code(quote.code):
            reasons.append("chinext_excluded")
        if not self._config.include_star_market and is_star_market_code(quote.code):
            reasons.append("star_market_excluded")
        if quote.turnover_amount < self._config.min_turnover_amount:
            reasons.append("insufficient_turnover")
        if abs(quote.pct_change) > self._config.max_abs_pct_change:
            reasons.append("pct_change_out_of_range")
        return reasons

    def _liquidity_score(self, quote: QuoteSnapshot) -> float:
        # Amount is in CNY. The log keeps a few ultra-liquid names from dominating the ranking.
        return round((quote.turnover_amount / self._config.min_turnover_amount) ** 0.5, 4)


def is_chinext_code(code: str) -> bool:
    """Return whether a normalized A-share code belongs to ChiNext."""

    normalized = code.strip()[-6:]
    return normalized.startswith(("300", "301"))


def is_star_market_code(code: str) -> bool:
    """Return whether a normalized A-share code belongs to the STAR Market."""

    normalized = code.strip()[-6:]
    return normalized.startswith(("688", "689"))
