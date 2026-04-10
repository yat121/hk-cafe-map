#!/usr/bin/env python3
"""
Walk-Forward Analysis for Alpha's Trading Strategies

Rolling train/test windows:
  - Train window: 2 years
  - Test window:  6 months
  - Step:          3 months

This validates strategy robustness — avoids overfitting to a single period.
"""

import json, os, sys, copy
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
DATA_DIR = os.path.join(WORK_DIR, "data")
OUT_DIR = os.path.join(WORK_DIR, "results")
os.makedirs(OUT_DIR, exist_ok=True)

# Import alpha backtester functions if available
sys.path.insert(0, WORK_DIR)
HAS_BACKTESTER = False
_run_backtest = None

try:
    from alpha_backtester import run_single_strategy_backtest, get_btc_data

    HAS_BACKTESTER = True
except ImportError:
    pass


# ─────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────
def load_btc_data(tf="1d"):
    """Load BTC data from local cache."""
    cache_path = os.path.join(DATA_DIR, f"BTC_USDT_{tf.replace('/','_')}.json")
    if not os.path.exists(cache_path):
        print(f"  No cache at {cache_path}")
        return pd.DataFrame()
    with open(cache_path) as f:
        raw = json.load(f)
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame(
        raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_index()


def load_all_timeframes():
    """Load all available timeframes."""
    return {
        "1H": load_btc_data("1H"),
        "4H": load_btc_data("4H"),
        "1D": load_btc_data("1D"),
    }


# ─────────────────────────────────────────────────────────
# SIMPLE BACKTEST (used for walk-forward without Jesse)
# ─────────────────────────────────────────────────────────
def simple_backtest(df, strategy_fn=None):
    """
    Simple equity curve backtest on OHLCV data.
    strategy_fn: function(df) -> dict with 'longs' and 'shorts' index lists
                 If None, uses buy-and-hold baseline.
    Returns equity curve and metrics.
    """
    closes = df["close"].values
    n = len(closes)

    if strategy_fn is None:
        # Buy-and-hold: equity = cumulative return
        equity = [1.0]
        for i in range(1, n):
            daily_ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            equity.append(equity[-1] * (1 + daily_ret))
        equity = np.array(equity)
    else:
        longs = np.ones(n, dtype=bool)
        shorts = np.zeros(n, dtype=bool)
        try:
            result = strategy_fn(df)
            longs = result.get("longs", np.ones(n, dtype=bool))
            shorts = result.get("shorts", np.zeros(n, dtype=bool))
        except Exception:
            pass

        fee = 0.0009
        position = 0
        prev_pos = 0
        equity = [1.0]

        for i in range(1, n):
            daily_ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            pnl = 0

            # Entry/exit detection
            if longs[i] and not longs[i - 1] and position == 0:
                position = 1
            elif shorts[i] and not shorts[i - 1] and position == 0:
                position = -1
            elif (not longs[i] and position == 1) or (not shorts[i] and position == -1):
                position = 0

            if position != 0:
                pnl = daily_ret * position
                if position != prev_pos:
                    pnl -= fee

            prev_pos = position
            equity.append(equity[-1] * (1 + pnl))
        equity = np.array(equity)

    equity = np.array(equity)
    returns = np.diff(equity) / equity[:-1]

    total_return = (equity[-1] - 1) * 100
    n_days = n
    cagr = ((equity[-1] / equity[0]) ** (365.0 / max(n_days, 1)) - 1) * 100

    peak = np.maximum.accumulate(equity)
    drawdowns = (peak - equity) / peak
    max_dd = float(np.max(drawdowns)) * 100

    sharpe = (
        float(np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(365))
        if len(returns) > 5
        else 0.0
    )

    return {
        "total_return": round(total_return, 2),
        "cagr": round(float(cagr), 2),
        "max_drawdown": round(max_dd, 2),
        "sharpe": round(sharpe, 3),
        "n_days": n,
        "equity_curve": [round(float(e), 6) for e in equity],
    }


# ─────────────────────────────────────────────────────────
# WALK-FORWARD ANALYSIS
# ─────────────────────────────────────────────────────────
def walk_forward_analysis(
    data, train_days=730, test_days=180, step_days=90, strategy_fn=None
):
    """
    Walk-forward analysis with rolling train/test windows.

    Parameters:
        data:         pd.DataFrame with OHLCV data (index=DatetimeIndex)
        train_days:   training window in days (default 2 years)
        test_days:    testing window in days (default 6 months)
        step_days:    walk-forward step in days (default 3 months)
        strategy_fn:  function to run backtest on a DataFrame slice

    Returns:
        list of dicts with train/test results per window
    """
    if isinstance(data.index, pd.RangeIndex):
        # Non-datetime index — use simple index slicing
        return _wfa_index_based(data, train_days, test_days, step_days, strategy_fn)

    df = data.sort_index()
    n_total = len(df)

    # Estimate ~days per candle from data
    avg_candle_days = 1.0
    if len(df) >= 2:
        total_span = (df.index[-1] - df.index[0]).days
        avg_candle_days = total_span / max(len(df) - 1, 1)

    train_candles = int(train_days / avg_candle_days)
    test_candles = int(test_days / avg_candle_days)
    step_candles = int(step_days / avg_candle_days)

    results = []
    start = train_candles

    while start + test_candles <= n_total:
        train_df = df.iloc[start - train_candles : start]
        test_df = df.iloc[start : start + test_candles]

        train_res = simple_backtest(train_df, strategy_fn)
        test_res = simple_backtest(test_df, strategy_fn)

        train_period = f"{train_df.index[0].date()} → {train_df.index[-1].date()}"
        test_period = f"{test_df.index[0].date()}  → {test_df.index[-1].date()}"

        # Walk-forward efficiency ratio
        wfe = (
            test_res["total_return"] / abs(train_res["total_return"] + 1e-9)
            if train_res["total_return"] != 0
            else 0
        )

        results.append(
            {
                "window": len(results) + 1,
                "train_period": train_period,
                "test_period": test_period,
                "train_return": train_res["total_return"],
                "test_return": test_res["total_return"],
                "train_cagr": train_res["cagr"],
                "test_cagr": test_res["cagr"],
                "train_sharpe": train_res["sharpe"],
                "test_sharpe": test_res["sharpe"],
                "train_max_dd": train_res["max_drawdown"],
                "test_max_dd": test_res["max_drawdown"],
                "wfe": round(float(wfe), 3),  # Walk-Forward Efficiency
            }
        )

        start += step_candles

    return results


def _wfa_index_based(data, train_days, test_days, step_days, strategy_fn):
    """Walk-forward when data has no datetime index (use integer offsets)."""
    n = len(data)
    step = step_days
    results = []
    start = train_days

    while start + test_days <= n:
        train_df = data.iloc[start - train_days : start]
        test_df = data.iloc[start : start + test_days]
        train_res = simple_backtest(train_df, strategy_fn)
        test_res = simple_backtest(test_df, strategy_fn)

        wfe = (
            test_res["total_return"] / abs(train_res["total_return"] + 1e-9)
            if train_res["total_return"] != 0
            else 0
        )

        results.append(
            {
                "window": len(results) + 1,
                "train_slice": f"[{start - train_days}:{start}]",
                "test_slice": f"[{start}:{start + test_days}]",
                "train_return": train_res["total_return"],
                "test_return": test_res["total_return"],
                "train_cagr": train_res["cagr"],
                "test_cagr": test_res["cagr"],
                "train_sharpe": train_res["sharpe"],
                "test_sharpe": test_res["sharpe"],
                "wfe": round(float(wfe), 3),
            }
        )
        start += step

    return results


def walk_forward_summary(results):
    """Summarize walk-forward results into aggregate stats."""
    if not results:
        return {}

    train_returns = [r["train_return"] for r in results]
    test_returns = [r["test_return"] for r in results]
    wfes = [r["wfe"] for r in results]
    train_sharpes = [r["train_sharpe"] for r in results]
    test_sharpes = [r["test_sharpe"] for r in results]

    summary = {
        "n_windows": len(results),
        "train_avg_return": round(float(np.mean(train_returns)), 2),
        "test_avg_return": round(float(np.mean(test_returns)), 2),
        "train_std": round(float(np.std(train_returns)), 2),
        "test_std": round(float(np.std(test_returns)), 2),
        "train_avg_sharpe": round(float(np.mean(train_sharpes)), 3),
        "test_avg_sharpe": round(float(np.mean(test_sharpes)), 3),
        "avg_wfe": round(float(np.mean(wfes)), 3),
        "wfe_std": round(float(np.std(wfes)), 3),
        # Consistency: how many test windows were profitable
        "test_win_rate": round(
            sum(1 for r in test_returns if r > 0) / len(test_returns), 3
        ),
        "all_windows": results,
    }
    return summary


# ─────────────────────────────────────────────────────────
# RSI STRATEGY (used as example walk-forward strategy)
# ─────────────────────────────────────────────────────────
def rsi_strategy(df, rsi_period=14, oversold=30, overbought=70):
    """Simple RSI mean-reversion strategy."""
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    n = len(closes)

    # RSI
    deltas = np.diff(closes, prepend=closes[0])
    deltas[0] = 0
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.zeros(n)
    avg_loss = np.zeros(n)
    avg_gain[rsi_period - 1] = np.mean(gains[:rsi_period])
    avg_loss[rsi_period - 1] = np.mean(losses[:rsi_period])
    for i in range(rsi_period, n):
        avg_gain[i] = (avg_gain[i - 1] * (rsi_period - 1) + gains[i]) / rsi_period
        avg_loss[i] = (avg_loss[i - 1] * (rsi_period - 1) + losses[i]) / rsi_period
    rs = np.where(avg_loss == 0, 100, avg_gain / (avg_loss + 1e-9))
    rsi = 100 - (100 / (1 + rs))

    longs = np.zeros(n, dtype=bool)
    shorts = np.zeros(n, dtype=bool)
    for i in range(rsi_period, n - 1):
        if rsi[i] < oversold and rsi[i - 1] >= oversold:
            longs[i + 1] = True  # entry next candle
        if rsi[i] > overbought and rsi[i - 1] <= overbought:
            shorts[i + 1] = True

    return {"longs": longs, "shorts": shorts}


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def run_walkforward_analysis(tf="1d"):
    print("\n" + "=" * 60)
    print("WALK-FORWARD ANALYSIS")
    print("=" * 60)

    df = load_btc_data(tf)
    if df.empty:
        print("  ERROR: No data available")
        return {}

    print(f"\n  Data loaded: {len(df)} candles")
    print(f"  Period:      {df.index[0].date()} → {df.index[-1].date()}")
    print(f"\n  Walk-Forward Config:")
    print(f"    Train window: 2 years  (~730 days)")
    print(f"    Test window:  6 months (~180 days)")
    print(f"    Step:         3 months (~90 days)")
    print(f"\n  Running walk-forward (Buy-and-Hold baseline)...")

    # Run walk-forward
    results = walk_forward_analysis(
        df,
        train_days=730,
        test_days=180,
        step_days=90,
        strategy_fn=None,  # None = buy-and-hold
    )

    summary = walk_forward_summary(results)

    print(f"\n  ── Walk-Forward Results ({summary['n_windows']} windows) ──")
    print(
        f"  {'Win':>3} | {'Train Period':>26} | {'Test Period':>26} | "
        f"{'Train%':>8} | {'Test%':>8} | {'WFE':>6}"
    )
    print(f"  {'-'*3}-+{'-'*26}-+{'-'*26}-+---------+---------+------")

    for r in results:
        print(
            f"  {r['window']:>3} | {r['train_period']:>26} | {r['test_period']:>26} | "
            f"{r['train_return']:>8.1f} | {r['test_return']:>8.1f} | {r['wfe']:>6.3f}"
        )

    print(f"\n  ── Aggregate Summary ──")
    print(
        f"  Train avg return: {summary['train_avg_return']:.1f}%  (std: {summary['train_std']:.1f}%)"
    )
    print(
        f"  Test  avg return: {summary['test_avg_return']:.1f}%  (std: {summary['test_std']:.1f}%)"
    )
    print(f"  Train avg Sharpe: {summary['train_avg_sharpe']:.3f}")
    print(f"  Test  avg Sharpe: {summary['test_avg_sharpe']:.3f}")
    print(
        f"  Avg WFE:          {summary['avg_wfe']:.3f}  (WFE > 0.5 = strategy transfers well)"
    )
    print(
        f"  Test win rate:    {summary['test_win_rate']:.1%}  "
        f"({int(summary['test_win_rate']*summary['n_windows'])}/{summary['n_windows']} windows profitable)"
    )

    # Also run with RSI strategy
    print(f"\n  Running walk-forward (RSI strategy)...")
    rsi_results = walk_forward_analysis(
        df,
        train_days=730,
        test_days=180,
        step_days=90,
        strategy_fn=lambda d: rsi_strategy(d),
    )
    rsi_summary = walk_forward_summary(rsi_results)

    print(f"\n  ── RSI Strategy Summary ──")
    print(f"  Test avg return: {rsi_summary['test_avg_return']:.1f}%")
    print(f"  Test win rate:   {rsi_summary['test_win_rate']:.1%}")
    print(f"  Avg WFE:         {rsi_summary['avg_wfe']:.3f}")

    # Save
    out = os.path.join(OUT_DIR, "walkforward_results.json")
    save_data = {"summary": summary, "rsi_summary": rsi_summary, "windows": results}
    with open(out, "w") as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Results saved → {out}")

    return {"summary": summary, "rsi_summary": rsi_summary}


if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "1d"
    run_walkforward_analysis(tf)
