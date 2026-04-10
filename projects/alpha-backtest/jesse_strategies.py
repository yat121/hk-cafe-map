#!/usr/bin/env python3
"""
jesse_strategies.py
All 11 Alpha strategies implemented as Jesse Strategy subclasses.
Each strategy inherits from jesse.Strategy and implements:
  - hyperparameters (hp) for grid search
  - should_long() / should_short()
  - go_long() / go_short()
  - optional: filters(), on_close_position()

Indicators are implemented inline using numpy to avoid Jesse's indicator library
dependencies and keep logic identical to Alpha's original strategies.
"""

import math
import numpy as np
import pandas as pd
from jesse import Strategy
from jesse.models import Order, Trade
from jesse import utils

# ─── Indicator helpers (identical to alpha_backtester.py) ─────────────────────


def calc_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index."""
    n = len(closes)
    rsi = np.zeros(n)
    deltas = np.diff(closes, prepend=closes[0])
    for i in range(1, n):
        if i < period:
            gain = deltas[1 : i + 1][deltas[1 : i + 1] > 0].sum()
            loss = -deltas[1 : i + 1][deltas[1 : i + 1] < 0].sum()
        else:
            gain = deltas[i - period + 1 : i + 1][
                deltas[i - period + 1 : i + 1] > 0
            ].sum()
            loss = -deltas[i - period + 1 : i + 1][
                deltas[i - period + 1 : i + 1] < 0
            ].sum()
        rs = gain / (loss + 1e-9)
        rsi[i] = 100 - (100 / (1 + rs))
    return rsi


def calc_bollinger(closes: np.ndarray, period: int = 20, std_mult: float = 2.0):
    """Bollinger Bands: returns (sma, upper, lower) arrays."""
    n = len(closes)
    sma = np.zeros(n)
    upper = np.zeros(n)
    lower = np.zeros(n)
    for i in range(n):
        if i < period - 1:
            sma[i] = closes[: i + 1].mean()
        else:
            window = closes[i - period + 1 : i + 1]
            sma[i] = window.mean()
            std = window.std(ddof=0)
            upper[i] = sma[i] + std_mult * std
            lower[i] = sma[i] - std_mult * std
    return sma, upper, lower


def calc_sma(closes: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average."""
    n = len(closes)
    sma = np.zeros(n)
    for i in range(n):
        if i < period - 1:
            sma[i] = closes[: i + 1].mean()
        else:
            sma[i] = closes[i - period + 1 : i + 1].mean()
    return sma


def local_highs_lows(highs: np.ndarray, lows: np.ndarray, n: int) -> tuple:
    """Rolling swing highs/lows over n periods."""
    nh = len(highs)
    lh = np.zeros(nh)
    ll = np.zeros(nh)
    for i in range(n, nh):
        lh[i] = np.max(highs[i - n : i + 1])
        ll[i] = np.min(lows[i - n : i + 1])
    return lh, ll


# ─── Precompute indicators once per backtest session ─────────────────────────

_STRAT_INDICATORS = {}  # strategy_name -> computed dict


def compute_indicators(candles: np.ndarray, params: dict) -> dict:
    """
    Precompute all indicators needed for all strategies on a given candle array.
    candles: np.ndarray shape (n, 6) = [ts, o, h, l, c, v]
    Returns dict of indicator arrays keyed by name.
    """
    n = len(candles)
    closes = candles[:, 4]
    highs = candles[:, 2]
    lows = candles[:, 3]
    opens = candles[:, 1]

    rsi_p = params.get("rsi_period", 14)
    bb_p = params.get("bb_period", 20)
    bb_std = params.get("bb_std", 2.0)
    fast_p = params.get("fast_period", 10)
    slow_p = params.get("slow_period", 50)
    lookback = params.get("lookback", 20)

    rsi = calc_rsi(closes, rsi_p)
    bb_sma, bb_upper, bb_lower = calc_bollinger(closes, bb_p, bb_std)
    fast_sma = calc_sma(closes, fast_p) if fast_p > 0 else np.zeros(n)
    slow_sma = calc_sma(closes, slow_p) if slow_p > 0 else np.zeros(n)
    macro_sma = calc_sma(closes, 50)

    # Local swing highs/lows
    lh, ll = local_highs_lows(highs, lows, lookback)

    # Previous candle high/low
    prev_high = np.zeros(n)
    prev_low = np.zeros(n)
    for i in range(1, n):
        prev_high[i] = highs[i - 1]
        prev_low[i] = lows[i - 1]

    return {
        "rsi": rsi,
        "bb_sma": bb_sma,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "fast_sma": fast_sma,
        "slow_sma": slow_sma,
        "macro_sma": macro_sma,
        "lh": lh,
        "ll": ll,
        "prev_high": prev_high,
        "prev_low": prev_low,
        "closes": closes,
        "highs": highs,
        "lows": lows,
        "opens": opens,
    }


def get_signal(name: str, idx: int, ind: dict, params: dict) -> str | None:
    """Evaluate signal at candle index idx for strategy name. Returns 'LONG'/'SHORT'/None."""
    rsi = ind["rsi"]
    bb_sma = ind["bb_sma"]
    bb_up = ind["bb_upper"]
    bb_low = ind["bb_lower"]
    fast_sm = ind["fast_sma"]
    slow_sm = ind["slow_sma"]
    macro = ind["macro_sma"]
    lh = ind["lh"]
    ll = ind["ll"]
    prev_h = ind["prev_high"]
    prev_l = ind["prev_low"]
    closes = ind["closes"]
    highs = ind["highs"]
    lows = ind["lows"]
    opens = ind["opens"]

    rsi_p = params.get("rsi_period", 14)
    rsi_lo = params.get("rsi_low", 30)
    rsi_hi = params.get("rsi_high", 70)
    bb_p = params.get("bb_period", 20)
    bb_std = params.get("bb_std", 2.0)
    lookback = params.get("lookback", 20)

    if name == "momentum_flip":
        if idx < 2:
            return None
        if rsi[idx - 1] < rsi_lo and rsi[idx] >= rsi_lo:
            return "LONG"
        if rsi[idx - 1] > rsi_hi and rsi[idx] <= rsi_hi:
            return "SHORT"

    elif name == "swing_sniper":
        if idx < 50:
            return None
        if rsi[idx - 1] < rsi_lo and rsi[idx] >= rsi_lo and closes[idx] > bb_low[idx]:
            return "LONG"
        if rsi[idx - 1] > rsi_hi and rsi[idx] <= rsi_hi and closes[idx] < bb_up[idx]:
            return "SHORT"

    elif name == "institutional_macro":
        if idx < 55:
            return None
        macro_trend = closes[idx] > macro[idx]
        if macro_trend and rsi[idx] <= rsi_lo:
            return "LONG"
        if not macro_trend and rsi[idx] >= rsi_hi:
            return "SHORT"

    elif name == "overextended_reversal":
        if idx < 50:
            return None
        bb_pos = (closes[idx] - bb_low[idx]) / (bb_up[idx] - bb_low[idx] + 1e-9)
        if bb_pos < 0.1 and rsi[idx] <= rsi_lo:
            return "LONG"
        if bb_pos > 0.9 and rsi[idx] >= rsi_hi:
            return "SHORT"

    elif name == "hidden_divergence":
        if idx < 30:
            return None
        lb = 15
        price_low_i = np.argmin(lows[idx - lb : idx + 1]) + (idx - lb)
        price_high_i = np.argmax(highs[idx - lb : idx + 1]) + (idx - lb)
        rsi_window = rsi[idx - lb : idx + 1]
        rsi_low_i = np.argmin(rsi_window) + (idx - lb)
        rsi_high_i = np.argmax(rsi_window) + (idx - lb)
        if lows[idx] < lows[price_low_i] and rsi[idx] > rsi[rsi_low_i]:
            return "LONG"
        if highs[idx] > highs[price_high_i] and rsi[idx] < rsi[rsi_high_i]:
            return "SHORT"

    elif name == "previous_day_sweep":
        if idx < 2:
            return None
        swept_high = highs[idx] > prev_h[idx] and closes[idx] < prev_h[idx]
        swept_low = lows[idx] < prev_l[idx] and closes[idx] > prev_l[idx]
        if swept_high and rsi[idx] < rsi_hi:
            return "SHORT"
        if swept_low and rsi[idx] > rsi_lo:
            return "LONG"

    elif name == "2b_reversal":
        if idx < 20:
            return None
        lb = 10
        recent_high_max = np.max(highs[idx - lb : idx])
        recent_low_min = np.min(lows[idx - lb : idx])
        if highs[idx] > recent_high_max and closes[idx] < recent_high_max:
            if rsi[idx] < rsi_hi:
                return "SHORT"
        elif lows[idx] < recent_low_min and closes[idx] > recent_low_min:
            if rsi[idx] > rsi_lo:
                return "LONG"

    elif name == "bb_headfake":
        if idx < bb_p + 5:
            return None
        lookback = bb_p
        bb_width_recent = bb_up[idx] - bb_low[idx]
        bb_width_prev = bb_up[idx - 1] - bb_low[idx - 1]
        squeeze = bb_width_recent < 0.7 * np.mean(
            bb_up[idx - lookback : idx] - bb_low[idx - lookback : idx]
        )
        if squeeze:
            if highs[idx] > bb_up[idx] and closes[idx] < bb_up[idx]:
                return "SHORT"
            if lows[idx] < bb_low[idx] and closes[idx] > bb_low[idx]:
                return "LONG"

    elif name == "equal_highs_liquidity_grab":
        if idx < lookback:
            return None
        curr_high = highs[idx]
        recent_highs_ = highs[idx - lookback : idx]
        eq_high_mask = np.abs(recent_highs_ - curr_high) / (curr_high + 1e-9) < 0.003
        if np.any(eq_high_mask):
            if closes[idx] < opens[idx]:
                return "SHORT"
            if closes[idx] > opens[idx]:
                return "LONG"

    elif name == "trend_follower":
        if idx < slow_p + 1:
            return None
        p_fast = params.get("fast_period", 10)
        p_slow = params.get("slow_period", 50)
        if fast_sm[idx - 1] < slow_sm[idx - 1] and fast_sm[idx] > slow_sm[idx]:
            if rsi[idx] > rsi_lo:
                return "LONG"
        if fast_sm[idx - 1] > slow_sm[idx - 1] and fast_sm[idx] < slow_sm[idx]:
            if rsi[idx] < rsi_hi:
                return "SHORT"

    elif name == "day_driver":
        if idx < 50:
            return None
        body = abs(closes[idx] - opens[idx])
        range_ = highs[idx] - lows[idx]
        is_bullish = closes[idx] > opens[idx]
        strength = (body / range_) if range_ > 0 else 0
        if (
            is_bullish
            and strength > 0.6
            and closes[idx] > bb_sma[idx]
            and rsi[idx] > rsi_lo
        ):
            return "LONG"
        if (
            not is_bullish
            and strength > 0.6
            and closes[idx] < bb_sma[idx]
            and rsi[idx] < rsi_hi
        ):
            return "SHORT"

    return None


# ─── Per-strategy Jesse Strategy class ───────────────────────────────────────

_STRATEGIES = [
    "momentum_flip",
    "swing_sniper",
    "trend_follower",
    "institutional_macro",
    "overextended_reversal",
    "hidden_divergence",
    "previous_day_sweep",
    "2b_reversal",
    "bb_headfake",
    "equal_highs_liquidity_grab",
    "day_driver",
]

# Global store for precomputed indicators (set before backtest)
_global_indicators: dict = {}
_global_params: dict = {}
_global_strategies_registered = False


def _make_strategy_class(strategy_name: str):
    """Factory: build a Jesse Strategy subclass for a given Alpha strategy name."""

    class JesseStrategy(Strategy):
        if strategy_name == "momentum_flip":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "swing_sniper":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "bb_period": 20,
                "bb_std": 2.0,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "trend_follower":
            hp = {
                "fast_period": 10,
                "slow_period": 50,
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "institutional_macro":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "overextended_reversal":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "bb_period": 20,
                "bb_std": 2.0,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "hidden_divergence":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "previous_day_sweep":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "2b_reversal":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "bb_headfake":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "bb_period": 20,
                "bb_std": 2.0,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "equal_highs_liquidity_grab":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "lookback": 20,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }
        elif strategy_name == "day_driver":
            hp = {
                "rsi_period": 14,
                "rsi_low": 30,
                "rsi_high": 70,
                "bb_period": 20,
                "bb_std": 2.0,
                "sl_pct": 0.02,
                "tp_pct": 0.02,
            }

        def should_long(self) -> bool:
            ind = _global_indicators.get(self.symbol, {})
            if not ind:
                return False
            sig = get_signal(strategy_name, self.index, ind, self.hp)
            return sig == "LONG"

        def should_short(self) -> bool:
            ind = _global_indicators.get(self.symbol, {})
            if not ind:
                return False
            sig = get_signal(strategy_name, self.index, ind, self.hp)
            return sig == "SHORT"

        def go_long(self) -> None:
            entry = self.price
            sl = entry * (1 - self.hp["sl_pct"])
            tp = entry * (1 + self.hp["tp_pct"])
            qty = self.stake / entry
            self.buy = qty
            self.stop_loss = sl
            self.take_profit = tp

        def go_short(self) -> None:
            entry = self.price
            sl = entry * (1 + self.hp["sl_pct"])
            tp = entry * (1 - self.hp["tp_pct"])
            qty = self.stake / entry
            self.sell = qty
            self.stop_loss = sl
            self.take_profit = tp

        def filters(self) -> list:
            # Only trade when leverage safety allows
            return []

    JesseStrategy.__name__ = f"Alpha_{strategy_name}"
    return JesseStrategy


# Build all strategy classes dynamically
_STRATEGY_CLASSES = {name: _make_strategy_class(name) for name in _STRATEGIES}


def get_strategy_class(name: str):
    return _STRATEGY_CLASSES[name]
