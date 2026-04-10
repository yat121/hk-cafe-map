#!/usr/bin/env python3
"""
Alpha Backtester - All 11 Strategies, 3 Timeframes
"""

import json, math, os, sys, itertools
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
RESULTS_DIR = os.path.join(WORK_DIR, "results")
KNOWLEDGE_DIR = os.path.join(WORK_DIR, "knowledge")
PLOTS_DIR = os.path.join(WORK_DIR, "plots")

SLIPPAGE = 0.001  # 0.1%
FEE = 0.001  # 0.1%


# ─────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────
def get_btc_data(tf_str):
    """Get BTC data. Uses Binance API for 1H/4H (longer history), yfinance for 1D."""
    now = datetime.now()

    if tf_str in ("1H", "4H"):
        # Use Binance for historical depth
        return _fetch_binance(tf_str)
    else:
        # yfinance for daily
        return _fetch_yfinance(tf_str)


def _fetch_binance(tf_str):
    """Fetch BTCUSDT from Binance REST API with pagination."""
    import urllib.request, time

    interval_map = {"1H": "1h", "4H": "4h", "1D": "1d"}
    interval = interval_map.get(tf_str, "1h")

    # Binance limits: 1h max ~730 days; 4h similar
    limit = 1000
    end_ms = int(datetime.now().timestamp() * 1000)
    if tf_str == "1H":
        start_ms = end_ms - (730 * 86400 * 1000)
    elif tf_str == "4H":
        start_ms = end_ms - (730 * 86400 * 1000)
    else:
        start_ms = end_ms - (5 * 365 * 86400 * 1000)

    all_rows = []
    current = start_ms
    while current < end_ms:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol=BTCUSDT&interval={interval}"
            f"&startTime={current}&endTime={end_ms}&limit={limit}"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            if not data:
                break
            for row in data:
                all_rows.append(
                    {
                        "timestamp": pd.to_datetime(row[0], unit="ms"),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                    }
                )
            current = data[-1][0] + 1
            time.sleep(0.15)
        except Exception as e:
            print(f"    Binance fetch error: {e}")
            break

    if not all_rows:
        return None
    df = pd.DataFrame(all_rows)
    df.set_index("timestamp", inplace=True)
    return df


def _fetch_yfinance(tf_str):
    """Fetch via yfinance (for 1D)."""
    now = datetime.now()
    start = now - pd.Timedelta(days=5 * 365 + 30)
    yf_tf = "1d"
    df = yf.download("BTC-USD", start=start, end=now, interval=yf_tf, progress=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()
    ts_col = "Datetime" if "Datetime" in df.columns else df.columns[0]
    if isinstance(df[ts_col].dtype, pd.DatetimeTZDtype):
        df[ts_col] = df[ts_col].dt.tz_localize(None)
    df["timestamp"] = pd.to_datetime(df[ts_col])
    df.set_index("timestamp", inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    return df


# ─────────────────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────────────────
def calc_rsi(closes_arr, period=14):
    """Calculate RSI using Wilder smoothing."""
    arr = np.asarray(closes_arr, dtype=float).flatten()
    deltas = np.diff(arr, prepend=arr[0])
    deltas[0] = 0.0
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.zeros(len(arr))
    avg_loss = np.zeros(len(arr))

    avg_gain[period - 1] = np.mean(gains[:period])
    avg_loss[period - 1] = np.mean(losses[:period])

    for i in range(period, len(arr)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i]) / period

    rs = np.zeros(len(arr))
    for i in range(len(arr)):
        if avg_loss[i] == 0 or np.isnan(avg_loss[i]):
            rs[i] = 100.0 if avg_gain[i] > 0 else 0.0
        else:
            rs[i] = avg_gain[i] / avg_loss[i]

    rsi = 100 - 100 / (1 + rs)
    rsi[: period - 1] = 50.0
    return rsi


def calc_bollinger(closes_arr, period=20, std_mult=2.0):
    """Calculate Bollinger Bands."""
    s = pd.Series(closes_arr, dtype=float)
    sma = s.rolling(period, min_periods=period).mean().values
    std = s.rolling(period, min_periods=period).std().values
    upper = sma + std_mult * std
    lower = sma - std_mult * std
    return sma, upper, lower


def calc_atr(highs, lows, closes, period=14):
    tr = np.maximum(
        np.maximum(highs[1:] - lows[1:], np.abs(highs[1:] - closes[:-1])),
        np.abs(lows[1:] - closes[:-1]),
    )
    tr = np.insert(tr, 0, highs[0] - lows[0])
    atr = np.zeros_like(tr)
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


# ─────────────────────────────────────────────────────────
# STRATEGY DEFINITIONS
# ─────────────────────────────────────────────────────────
def apply_strategy(name, df, params):
    n = len(df)
    closes = np.asarray(df["close"].values, dtype=float).flatten()
    highs = np.asarray(df["high"].values, dtype=float).flatten()
    lows = np.asarray(df["low"].values, dtype=float).flatten()
    opens = np.asarray(df["open"].values, dtype=float).flatten()

    rsi_p = params.get("rsi_period", 14)
    rsi_low = params.get("rsi_low", 30)
    rsi_high = params.get("rsi_high", 70)
    bb_p = params.get("bb_period", 20)
    bb_std = params.get("bb_std", 2.0)
    sl_pct = params.get("sl_pct", 0.02)
    tp_pct = params.get("tp_pct", 0.02)

    rsi = calc_rsi(closes, rsi_p)
    bb_sma, bb_upper, bb_lower = calc_bollinger(closes, bb_p, bb_std)

    # Precompute local highs/lows for relevant strategies
    local_highs = np.zeros(n)
    local_lows = np.zeros(n)
    for i in range(20, n):
        local_highs[i] = np.max(highs[i - 20 : i + 1])
        local_lows[i] = np.min(lows[i - 20 : i + 1])

    # Previous candle high/low (for sweep strategies)
    prev_high = np.zeros(n)
    prev_low = np.zeros(n)
    for i in range(1, n):
        prev_high[i] = highs[i - 1]
        prev_low[i] = lows[i - 1]

    signals = [None] * n

    if name == "day_driver":
        # Trade the "driver" candle: strong momentum candles that continue
        # Entry: price breaks above prior day high with RSI confirmation
        # Use daily-level structure even on intraday
        for i in range(50, n):
            body = abs(closes[i] - opens[i])
            range_ = highs[i] - lows[i]
            is_bullish = closes[i] > opens[i]
            # Driver: body > 60% of range, volume spike assumed
            if range_ > 0:
                strength = body / range_
            else:
                strength = 0
            if is_bullish and strength > 0.6 and rsi[i] > rsi_low:
                # Price momentum bullish
                if closes[i] > bb_sma[i] and rsi[i] > rsi_low:
                    signals[i] = "LONG"
            elif not is_bullish and strength > 0.6 and rsi[i] < rsi_high:
                if closes[i] < bb_sma[i] and rsi[i] < rsi_high:
                    signals[i] = "SHORT"

    elif name == "swing_sniper":
        # Swing sniper: RSI at extreme + BB touch/break
        for i in range(50, n):
            if rsi[i - 1] < rsi_low and rsi[i] >= rsi_low and closes[i] > bb_lower[i]:
                signals[i] = "LONG"
            elif (
                rsi[i - 1] > rsi_high and rsi[i] <= rsi_high and closes[i] < bb_upper[i]
            ):
                signals[i] = "SHORT"

    elif name == "institutional_macro":
        # Macro: use longer lookback for trend; trade with the macro trend
        # Macro trend = 50 SMA direction
        macro_sma = pd.Series(closes).rolling(50).mean().values
        for i in range(55, n):
            macro_trend = closes[i] > macro_sma[i]
            micro_rsi_oversold = rsi[i] <= rsi_low
            micro_rsi_overbought = rsi[i] >= rsi_high
            if macro_trend and micro_rsi_oversold:
                signals[i] = "LONG"
            elif not macro_trend and micro_rsi_overbought:
                signals[i] = "SHORT"

    elif name == "momentum_flip":
        # Momentum flip: RSI crosses from extreme (momentum exhaustion)
        for i in range(2, n):
            if rsi[i - 1] < rsi_low and rsi[i] >= rsi_low:
                signals[i] = "LONG"
            elif rsi[i - 1] > rsi_high and rsi[i] <= rsi_high:
                signals[i] = "SHORT"

    elif name == "overextended_reversal":
        # Overextended: price is far from BB mean + RSI extreme
        for i in range(50, n):
            bb_pos = (closes[i] - bb_lower[i]) / (bb_upper[i] - bb_lower[i] + 1e-9)
            if bb_pos < 0.1 and rsi[i] <= rsi_low:  # Near lower BB
                signals[i] = "LONG"
            elif bb_pos > 0.9 and rsi[i] >= rsi_high:  # Near upper BB
                signals[i] = "SHORT"

    elif name == "hidden_divergence":
        # Hidden divergence: price makes new low but RSI makes higher low (bullish)
        # or price new high, RSI makes lower high (bearish)
        for i in range(30, n):
            lookback = 15
            price_low_i = np.argmin(lows[i - lookback : i + 1]) + (i - lookback)
            price_high_i = np.argmax(highs[i - lookback : i + 1]) + (i - lookback)
            rsi_window = rsi[i - lookback : i + 1]
            rsi_low_i = np.argmin(rsi_window) + (i - lookback)
            rsi_high_i = np.argmax(rsi_window) + (i - lookback)

            # Bullish hidden div: price lower low, RSI higher low
            if lows[i] < lows[price_low_i] and rsi[i] > rsi[rsi_low_i]:
                signals[i] = "LONG"
            # Bearish hidden div: price higher high, RSI lower high
            elif highs[i] > highs[price_high_i] and rsi[i] < rsi[rsi_high_i]:
                signals[i] = "SHORT"

    elif name == "previous_day_sweep":
        # Previous day sweep: sweep of prior day high/low and reverse
        for i in range(2, n):
            # For intraday: sweep of previous candle high/low
            swept_high = highs[i] > prev_high[i] and closes[i] < prev_high[i]
            swept_low = lows[i] < prev_low[i] and closes[i] > prev_low[i]
            if swept_high and rsi[i] < rsi_high:
                signals[i] = "SHORT"
            elif swept_low and rsi[i] > rsi_low:
                signals[i] = "LONG"

    elif name == "2b_reversal":
        # 2B reversal (Tucker): price pierces swing high/low then closes back
        for i in range(20, n):
            lookback = 10
            # Check if price pierced recent high then reversed
            recent_high_max = np.max(highs[i - lookback : i])
            recent_low_min = np.min(lows[i - lookback : i])
            # Price exceeds recent high then closes below - failure = SHORT
            if highs[i] > recent_high_max and closes[i] < recent_high_max:
                if rsi[i] < rsi_high:
                    signals[i] = "SHORT"
            # Price below recent low then closes above - failure = LONG
            elif lows[i] < recent_low_min and closes[i] > recent_low_min:
                if rsi[i] > rsi_low:
                    signals[i] = "LONG"

    elif name == "bb_headfake":
        # BB headfake: price compresses to BB edge, breaks out, then reverses
        # Use the pre-breakout squeeze
        for i in range(bb_p + 5, n):
            lookback = bb_p
            bb_width_recent = bb_upper[i] - bb_lower[i]
            bb_width_prev = bb_upper[i - 1] - bb_lower[i - 1]
            # Squeeze: BB narrowing
            squeeze = bb_width_recent < 0.7 * np.mean(
                bb_upper[i - lookback : i] - bb_lower[i - lookback : i]
            )

            if squeeze:
                if highs[i] > bb_upper[i] and closes[i] < bb_upper[i]:
                    signals[i] = "SHORT"
                elif lows[i] < bb_lower[i] and closes[i] > bb_lower[i]:
                    signals[i] = "LONG"

    elif name == "equal_highs_liquidity_grab":
        # Equal highs liquidity: price reaches equal highs, liquidity grabbed, reverses
        for i in range(20, n):
            lookback = 20
            # Find equal highs (within 0.2%)
            recent_highs_ = highs[i - lookback : i]
            curr_high = highs[i]
            eq_high_mask = (
                np.abs(recent_highs_ - curr_high) / (curr_high + 1e-9) < 0.003
            )
            if np.any(eq_high_mask):
                # Price tapped equal highs and reversed
                if closes[i] < opens[i]:  # Rejected lower
                    signals[i] = "SHORT"
                elif closes[i] > opens[i]:
                    signals[i] = "LONG"

    elif name == "trend_follower":
        # Trend follower: SMA crossover
        fast_p = params.get("fast_period", 10)
        slow_p = params.get("slow_period", 50)
        if fast_p >= slow_p:
            fast_p = slow_p - 1
        fast_sma = pd.Series(closes).rolling(fast_p).mean().values
        slow_sma = pd.Series(closes).rolling(slow_p).mean().values
        for i in range(slow_p + 1, n):
            if fast_sma[i - 1] < slow_sma[i - 1] and fast_sma[i] > slow_sma[i]:
                if rsi[i] > rsi_low:  # Trend confirmation
                    signals[i] = "LONG"
            elif fast_sma[i - 1] > slow_sma[i - 1] and fast_sma[i] < slow_sma[i]:
                if rsi[i] < rsi_high:
                    signals[i] = "SHORT"

    return signals


# ─────────────────────────────────────────────────────────
# BACKTEST ENGINE
# ─────────────────────────────────────────────────────────
def run_backtest(signals, df, params):
    n = len(df)
    closes = np.asarray(df["close"].values, dtype=float).flatten()
    highs = np.asarray(df["high"].values, dtype=float).flatten()
    lows = np.asarray(df["low"].values, dtype=float).flatten()
    sl_pct = params.get("sl_pct", 0.02)
    tp_pct = params.get("tp_pct", 0.02)

    trades = []
    position = None
    entry_price = 0.0
    entry_idx = 0

    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0

    trade_log = []

    for i in range(n):
        price = closes[i]

        # Apply SL/TP if in position
        if position:
            hit_sl = (position == "LONG" and lows[i] <= entry_price * (1 - sl_pct)) or (
                position == "SHORT" and highs[i] >= entry_price * (1 + sl_pct)
            )
            hit_tp = (
                position == "LONG" and highs[i] >= entry_price * (1 + tp_pct)
            ) or (position == "SHORT" and lows[i] <= entry_price * (1 - tp_pct))

            if hit_sl or hit_tp:
                exit_price = (
                    entry_price * (1 + sl_pct)
                    if (position == "LONG" and hit_sl)
                    or (position == "SHORT" and hit_tp)
                    else (
                        entry_price * (1 - sl_pct)
                        if (position == "LONG" and hit_tp)
                        or (position == "SHORT" and hit_sl)
                        else price
                    )
                )
                # Apply slippage + fee
                slip = SLIPPAGE * exit_price
                fee = FEE * exit_price
                exit_price_with_cost = (
                    exit_price - slip - fee
                    if position == "LONG"
                    else exit_price + slip + fee
                )

                if position == "LONG":
                    pnl = (exit_price_with_cost - entry_price) / entry_price
                else:
                    pnl = (entry_price - exit_price_with_cost) / entry_price

                equity *= 1 + pnl
                peak = max(peak, equity)
                dd = (peak - equity) / peak
                max_dd = max(max_dd, dd)

                if pnl > 0:
                    wins += 1
                    gross_profit += abs(pnl)
                else:
                    losses += 1
                    gross_loss += abs(pnl)

                trade_log.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "type": position,
                        "entry": entry_price,
                        "exit": exit_price_with_cost,
                        "pnl": pnl,
                        "equity": equity,
                    }
                )
                position = None

        # Entry signals (only if flat)
        if position is None and signals[i]:
            direction = signals[i]
            # Apply slippage on entry
            slip = SLIPPAGE * price
            fee = FEE * price
            if direction == "LONG":
                entry = price + slip + fee
            else:
                entry = price - slip - fee
            position = direction
            entry_price = entry
            entry_idx = i

    total = wins + losses
    if total == 0:
        return None

    win_rate = wins / total * 100
    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (float("inf") if gross_profit > 0 else 0)
    )

    # Sharpe & Sortino
    if len(trade_log) > 1:
        returns = [t["pnl"] for t in trade_log]
        avg_r = np.mean(returns)
        std_r = np.std(returns, ddof=1)
        sharpe = (avg_r / std_r * math.sqrt(252)) if std_r > 1e-9 else 0
        downside = (
            np.std([r for r in returns if r < 0], ddof=1)
            if any(r < 0 for r in returns)
            else 1e-9
        )
        sortino = (
            (avg_r / max(downside, 1e-6) * math.sqrt(252)) if downside > 1e-9 else 0
        )
        sortino = max(min(sortino, 100), -100)  # Cap to reasonable range
    else:
        sharpe = sortino = 0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_factor": pf,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_dd": max_dd * 100,
        "final_equity": equity,
        "return_pct": (equity - 1) * 100,
        "trade_log": trade_log,
    }


# ─────────────────────────────────────────────────────────
# GRID SEARCH
# ─────────────────────────────────────────────────────────
RSI_PERIODS = [10, 14, 20, 28]
RSI_LEVELS = [(30, 70), (35, 65), (40, 60), (45, 55)]
BB_PERIODS = [15, 20, 25]
BB_STDS = [1.5, 2.0, 2.5]
SL_TP_VALS = [0.01, 0.02, 0.03]


# Fast grid (only RSI+SL/TP for all strategies)
def fast_grid():
    for rp in RSI_PERIODS:
        for rlo, rhi in RSI_LEVELS:
            for sl in SL_TP_VALS:
                for tp in SL_TP_VALS:
                    yield {
                        "rsi_period": rp,
                        "rsi_low": rlo,
                        "rsi_high": rhi,
                        "bb_period": 20,
                        "bb_std": 2.0,
                        "sl_pct": sl,
                        "tp_pct": tp,
                    }


# Full grid for BB-sensitive strategies
def full_grid():
    for rp in RSI_PERIODS:
        for rlo, rhi in RSI_LEVELS:
            for bbp in BB_PERIODS:
                for bbs in BB_STDS:
                    for sl in SL_TP_VALS:
                        for tp in SL_TP_VALS:
                            yield {
                                "rsi_period": rp,
                                "rsi_low": rlo,
                                "rsi_high": rhi,
                                "bb_period": bbp,
                                "bb_std": bbs,
                                "sl_pct": sl,
                                "tp_pct": tp,
                            }


# SMA grid for trend follower
def sma_grid():
    for fast in [5, 10, 20]:
        for slow in [30, 50, 100]:
            if fast >= slow:
                continue
            for sl in SL_TP_VALS:
                for tp in SL_TP_VALS:
                    yield {
                        "fast_period": fast,
                        "slow_period": slow,
                        "sl_pct": sl,
                        "tp_pct": tp,
                        "rsi_period": 14,
                        "rsi_low": 30,
                        "rsi_high": 70,
                        "bb_period": 20,
                        "bb_std": 2.0,
                    }


# ─────────────────────────────────────────────────────────
# HEATMAP
# ─────────────────────────────────────────────────────────
def make_heatmap(
    results_list,
    strategy,
    timeframe,
    params_dim1,
    dim1_label,
    params_dim2,
    dim2_label,
    metric="sharpe",
):
    """Create a 2D heatmap of metric across parameter space. Returns path."""
    import matplotlib.pyplot as plt
    import numpy as np

    unique_d1 = sorted(set(p[params_dim1] for p in results_list))
    unique_d2 = sorted(set(p[params_dim2] for p in results_list), reverse=True)

    z = np.full((len(unique_d2), len(unique_d1)), np.nan)

    for r in results_list:
        d1_val = r["params"][params_dim1]
        d2_val = r["params"][params_dim2]
        i = unique_d2.index(d2_val)
        j = unique_d1.index(d1_val)
        z[i, j] = r.get(metric, np.nan)

    fig, ax = plt.subplots(figsize=(10, 7))
    cmap = plt.cm.RdYlGn
    norm = mcolors.TwoSlopeNorm(vmin=np.nanmin(z), vmax=np.nanmax(z), vcenter=0)

    im = ax.imshow(z, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(len(unique_d1)))
    ax.set_xticklabels([str(x) for x in unique_d1])
    ax.set_yticks(range(len(unique_d2)))
    ax.set_yticklabels([str(x) for x in unique_d2])
    ax.set_xlabel(dim1_label)
    ax.set_ylabel(dim2_label)
    ax.set_title(
        f"{strategy} ({timeframe}) — {metric.upper()}\nBest: {np.nanmax(z):.3f}"
    )

    plt.colorbar(im, ax=ax, label=metric.upper())

    # Annotate cells
    for i in range(len(unique_d2)):
        for j in range(len(unique_d1)):
            val = z[i, j]
            if not np.isnan(val):
                ax.text(
                    j,
                    i,
                    f"{val:.2f}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white" if abs(val) < 0.3 else "black",
                )

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, f"{strategy}_{timeframe}_heatmap.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
STRATEGY_GRIDS = {
    "day_driver": fast_grid,
    "swing_sniper": full_grid,
    "institutional_macro": fast_grid,
    "momentum_flip": fast_grid,
    "overextended_reversal": full_grid,
    "hidden_divergence": fast_grid,
    "previous_day_sweep": fast_grid,
    "2b_reversal": fast_grid,
    "bb_headfake": full_grid,
    "equal_highs_liquidity_grab": fast_grid,
    "trend_follower": sma_grid,
}

# Strategies that need full (BB) grid
BB_STRATS = {"swing_sniper", "overextended_reversal", "bb_headfake"}


def run_strategy(strategy, timeframe, max_combos=None):
    print(f"\n{'='*60}")
    print(f"  {strategy.upper()} — {timeframe}")
    print(f"{'='*60}")

    # Load data
    df = get_btc_data(timeframe)
    if df is None or len(df) < 200:
        print(f"  ⚠ No data for {timeframe}, skipping")
        return None

    df = df.dropna()
    print(f"  Loaded {len(df)} candles")

    grid_fn = STRATEGY_GRIDS.get(strategy, fast_grid)
    all_params = list(grid_fn())

    if max_combos and len(all_params) > max_combos:
        all_params = all_params[:max_combos]

    print(f"  Testing {len(all_params)} param combos...")

    # Dimension for heatmap: use RSI_period x SL (or BB_period)
    if strategy in BB_STRATS:
        dim1, d1_label = "bb_period", "BB Period"
        dim2, d2_label = "rsi_period", "RSI Period"
    else:
        dim1, d1_label = "sl_pct", "Stop Loss %"
        dim2, d2_label = "tp_pct", "Take Profit %"

    results = []
    for idx, params in enumerate(all_params):
        signals = apply_strategy(strategy, df, params)
        bt = run_backtest(signals, df, params)
        if bt:
            bt["params"] = params
            results.append(bt)

        if (idx + 1) % 200 == 0:
            print(f"  Progress: {idx+1}/{len(all_params)} combos")

    if not results:
        print(f"  ⚠ No valid results")
        return None

    # Sort by Sharpe
    results.sort(key=lambda x: x["sharpe"], reverse=True)
    best = results[0]

    # Summary
    print(f"\n  ✅ BEST RESULT:")
    print(f"     Sharpe:   {best['sharpe']:.3f}")
    print(f"     Sortino:  {best['sortino']:.3f}")
    print(f"     Max DD:   {best['max_dd']:.1f}%")
    print(f"     Win Rate: {best['win_rate']:.1f}%")
    print(f"     Trades:   {best['total_trades']}")
    print(f"     Return:   {best['return_pct']:.1f}%")
    print(f"     Params:   {best['params']}")

    # Save heatmap (RSI_period x SL/TP heatmap for top TP/SL combo)
    # Aggregate results by dim1/dim2 for heatmap
    try:
        heatmap_data = []
        best_tp = best["params"]["tp_pct"]
        best_sl = best["params"]["sl_pct"]
        for r in results:
            # Find average Sharpe per (dim1, dim2) across all SL/TP combos
            heatmap_data.append(
                {
                    "params": {
                        k: r["params"][k] for k in [dim1, dim2, "tp_pct", "sl_pct"]
                    },
                    "sharpe": r["sharpe"],
                }
            )

        # Make heatmap across RSI_period x SL for a fixed good TP
        # Actually, let's make RSI_period x SL heatmap (average across all others)
        from collections import defaultdict

        cell_map = defaultdict(list)
        for r in results:
            key = (
                r["params"].get("rsi_period", r["params"].get("bb_period", 20)),
                r["params"].get("sl_pct", 0.02),
            )
            cell_map[key].append(r["sharpe"])

        # Use BB period x RSI period for BB strategies
        cell_map2d = defaultdict(list)
        for r in results:
            if strategy in BB_STRATS:
                key = (r["params"]["bb_period"], r["params"]["rsi_period"])
            else:
                key = (
                    int(r["params"]["sl_pct"] * 100),
                    int(r["params"]["tp_pct"] * 100),
                )
            cell_map2d[key].append(r["sharpe"])

        z_data = []
        if strategy in BB_STRATS:
            unique_bbp = sorted(set(k[0] for k in cell_map2d))
            unique_rsi = sorted(set(k[1] for k in cell_map2d))
            z = np.zeros((len(unique_rsi), len(unique_bbp)))
            for i, rp in enumerate(unique_rsi):
                for j, bbp in enumerate(unique_bbp):
                    vals = cell_map2d.get((bbp, rp), [np.nan])
                    z[i, j] = np.nanmean(vals)
            xlabels = [str(x) for x in unique_bbp]
            ylabels = [str(x) for x in unique_rsi]
            xl = "BB Period"
            yl = "RSI Period"
        else:
            unique_sl = sorted(set(k[0] for k in cell_map2d))
            unique_tp = sorted(set(k[1] for k in cell_map2d), reverse=True)
            z = np.zeros((len(unique_tp), len(unique_sl)))
            for i, tp in enumerate(unique_tp):
                for j, sl in enumerate(unique_sl):
                    vals = cell_map2d.get((sl, tp), [np.nan])
                    z[i, j] = np.nanmean(vals)
            xlabels = [str(x / 100) for x in unique_sl]
            ylabels = [str(x / 100) for x in unique_tp]
            xl = "Stop Loss %"
            yl = "Take Profit %"

        fig, ax = plt.subplots(figsize=(10, 7))
        vmin, vmax = np.nanmin(z), np.nanmax(z)
        if vmin > 0:
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        else:
            norm = mcolors.TwoSlopeNorm(vmin=vmin, vmax=vmax, vcenter=0)
        cmap = plt.cm.RdYlGn
        im = ax.imshow(z, cmap=cmap, norm=norm, aspect="auto")
        ax.set_xticks(range(len(xlabels)))
        ax.set_xticklabels(xlabels)
        ax.set_yticks(range(len(ylabels)))
        ax.set_yticklabels(ylabels)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(
            f"{strategy.upper()} ({timeframe}) — Sharpe Ratio Heatmap\nBest Sharpe: {np.nanmax(z):.3f}"
        )
        plt.colorbar(im, ax=ax, label="Sharpe Ratio")
        for i in range(z.shape[0]):
            for j in range(z.shape[1]):
                val = z[i, j]
                if not np.isnan(val):
                    ax.text(
                        j,
                        i,
                        f"{val:.2f}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white" if abs(val) < 0.3 else "black",
                    )
        plt.tight_layout()
        hp_path = os.path.join(PLOTS_DIR, f"{strategy}_{timeframe}_heatmap.png")
        plt.savefig(hp_path, dpi=150)
        plt.close()
        print(f"  📊 Heatmap saved: {hp_path}")
    except Exception as e:
        print(f"  ⚠ Heatmap error: {e}")

    # Save results JSON
    out_path = os.path.join(RESULTS_DIR, f"{strategy}_{timeframe}.json")
    save_data = {
        "strategy": strategy,
        "timeframe": timeframe,
        "best_params": best["params"],
        "metrics": {
            "sharpe": round(best["sharpe"], 3),
            "sortino": round(best["sortino"], 3),
            "max_dd": round(best["max_dd"], 1),
            "win_rate": round(best["win_rate"], 1),
            "total_trades": best["total_trades"],
            "profit_factor": round(best["profit_factor"], 3),
            "return_pct": round(best["return_pct"], 1),
            "wins": best["wins"],
            "losses": best["losses"],
        },
        "all_results_summary": [
            {
                k: round(v, 4) if isinstance(v, float) else v
                for k, v in {
                    **r["params"],
                    **{
                        "sharpe": r["sharpe"],
                        "sortino": r["sortino"],
                        "max_dd": r["max_dd"],
                        "win_rate": r["win_rate"],
                        "trades": r["total_trades"],
                        "pf": r["profit_factor"],
                    },
                }.items()
            }
            for r in results[:200]
        ],
    }
    with open(out_path, "w") as f:
        json.dump(save_data, f, indent=2)
    print(f"  💾 Saved: {out_path}")

    # Save best params
    best_path = os.path.join(RESULTS_DIR, f"{strategy}_{timeframe}_best.json")
    with open(best_path, "w") as f:
        json.dump(
            {
                "strategy": strategy,
                "timeframe": timeframe,
                "params": best["params"],
                "metrics": save_data["metrics"],
            },
            f,
            indent=2,
        )

    return save_data


if __name__ == "__main__":
    # Run a quick test
    result = run_strategy("momentum_flip", "1D", max_combos=100)
    print("\nTest complete:", result)
