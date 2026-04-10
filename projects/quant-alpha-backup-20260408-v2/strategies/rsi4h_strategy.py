"""RSI 4‑hour strategy module expected by backtest CLI."""

from .rsi_strategy import generate_signals

# expose function name expected
__all__ = ["generate_signals"]
