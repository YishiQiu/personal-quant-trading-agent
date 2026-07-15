"""交易时间窗口判断；部署层调度器可以自由替换。"""

from trading_agent.scheduler.window import is_tail_research_window

__all__ = ["is_tail_research_window"]
