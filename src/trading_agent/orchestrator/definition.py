"""Framework-neutral graph specification, ready to map into LangGraph nodes."""

WORKFLOW_NODES = (
    "market_scanner",
    "pattern_gate",
    "research_context_loader",
    "kline_trend",
    "volume",
    "catalyst",
    "risk",
    "llm_research",
    "decision",
    "report",
)

WORKFLOW_EDGES = (
    ("market_scanner", "pattern_gate"),
    ("pattern_gate", "research_context_loader"),
    ("research_context_loader", "kline_trend"),
    ("research_context_loader", "volume"),
    ("research_context_loader", "catalyst"),
    ("research_context_loader", "risk"),
    ("kline_trend", "llm_research"),
    ("volume", "llm_research"),
    ("catalyst", "llm_research"),
    ("risk", "llm_research"),
    ("llm_research", "decision"),
    ("decision", "report"),
)
