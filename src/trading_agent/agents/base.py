"""供后续 LangGraph 节点复用的统一结构化输出协议。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class AgentOutput(Generic[T]):
    agent_name: str
    score: float | None
    confidence: float
    evidence: tuple[str, ...]
    risks: tuple[str, ...] = field(default_factory=tuple)
    veto: bool = False
    payload: T | None = None
