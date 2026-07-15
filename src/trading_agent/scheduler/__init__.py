"""Trading-calendar aware schedule guards; deployment scheduler stays replaceable."""

from trading_agent.scheduler.window import is_tail_research_window

__all__ = ["is_tail_research_window"]
