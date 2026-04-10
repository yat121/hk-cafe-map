#!/usr/bin/env python3
"""
run_jesse_backtest.py
Run Jesse backtests for all 11 Alpha strategies across timeframes.
Outputs results in Alpha's JSON format with enhanced metrics:
  Sharpe, Sortino, Calmar Ratio, MAE, Kelly Criterion, Win Rate, etc.
"""

import json, math, os, sys, itertools
from datetime import datetime
from typing import Generator

import numpy as np
import pandas as pd

# ─── Add paths ────────────────────────────────────────────────────────────────
WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
RESULTS_DIR = os.path.join(WORK_DIR, "results")
sys.path.insert(0, WORK_DIR)
os.chdir(WORK_DIR)

from jesse_data_formatter import load_alpha_data, make_jesse_candles_dict

# Jesse imports
from jesse.research import backtest
from jesse.config import config as jesse_config, reset_config, set_config
from jesse.routes import router

# ─── Strategy params grids ───────────────────────────────────────────────────

RSI_PERIODS = [10, 14, 20, 28]
RSI_LEVELS = [(30, 70), (35, 65), (40, 60), (45, 55)]
BB_PERIODS = [15, 20, 25]
BB_STDS = [1.5, 2.0, 2.5]
SL_TP_VALS = [0.01, 0.02, 0.03]
FAST_SMAs = [5, 10, 20]
SLOW_SMAs = [30, 50, 100]

# ─── Grid generators ─────────────────────────────────────────────────────────


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
                        "lookback": 20,
                        "fast_period": 10,
                        "slow_period": 50,
                    }


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
                                "lookback": 20,
                                "fast_period": 10,
                                "slow_period": 50,
                            }


def sma_grid():
    for fast in FAST_SMAs:
        for slow in SLOW_SMAs:
            if fast >= slow:
                continue
            for sl in SL_TP_VALS:
                for tp in SL_TP_VALS:
                    yield {
                        "fast_period": fast,
                        "slow_period": slow,
                        "rsi_period": 14,
                        "rsi_low": 30,
                        "rsi_high": 70,
                        "bb_period": 20,
                        "bb_std": 2.0,
                        "sl_pct": sl,
                        "tp_pct": tp,
                        "lookback": 20,
                    }


STRAT_GRIDS = {
    "momentum_flip": fast_grid,
    "swing_sniper": full_grid,
    "trend_follower": sma_grid,
    "institutional_macro": fast_grid,
    "overextended_reversal": full_grid,
    "hidden_divergence": fast_grid,
    "previous_day_sweep": fast_grid,
    "2b_reversal": fast_grid,
    "bb_headfake": full_grid,
    "equal_highs_liquidity_grab": fast_grid,
    "day_driver": fast_grid,
}

STRATEGY_FAST_GRID = {
    "momentum_flip",
    "institutional_macro",
    "hidden_divergence",
    "previous_day_sweep",
    "2b_reversal",
    "equal_highs_liquidity_grab",
    "day_driver",
}

# ─── Metrics computation ─────────────────────────────────────────────────────


def compute_metrics(trade_log: list, equity_curve: list) -> dict:
    """Compute enhanced metrics from Jesse backtest result."""
    if not trade_log:
        return {}

    pnls = np.array([t["pnl"] for t in trade_log])
    n = len(pnls)
    wins = int((pnls > 0).sum())
    losses = int((pnls < 0).sum())
    total = n

    win_rate = wins / total * 100
    gross_prof = pnls[pnls > 0].sum()
    gross_loss = abs(pnls[pnls < 0].sum())
    pf = gross_prof / (gross_loss + 1e-9)

    # Annualised metrics (assume ~365 trading days)
    avg_return = pnls.mean()
    std_return = pnls.std(ddof=1) if n > 1 else 1e-9
    downside = pnls[pnls < 0].std(ddof=1) if (pnls < 0).any() else 1e-9

    sharpe = (avg_return / std_return * math.sqrt(365)) if std_return > 1e-9 else 0.0
    sortino = (
        (avg_return / max(downside, 1e-9) * math.sqrt(365)) if downside > 1e-9 else 0.0
    )

    # Max Drawdown
    eq = np.array(equity_curve) if equity_curve else np.array([1.0])
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / peak
    max_dd = dd.max() * 100

    # Calmar Ratio
    ann_return = avg_return * 365
    calmar = ann_return / (max_dd / 100) if max_dd > 0.1 else 0.0

    # MAE / MFE
    longs = [t for t in trade_log if t.get("type") == "LONG"]
    shorts = [t for t in trade_log if t.get("type") == "SHORT"]
    mae = float(np.mean([abs(t["pnl"]) for t in trade_log if t["pnl"] < 0])) * 100
    mfe = float(np.mean([t["pnl"] for t in trade_log if t["pnl"] > 0])) * 100

    # Kelly Criterion
    if win_rate > 0 and win_rate < 100:
        W = win_rate / 100
        R = pf if pf > 0 else 1
        kelly = W - ((1 - W) / R) if R > 0 else 0.0
        kelly = max(min(kelly, 1.0), -1.0)
    else:
        kelly = 0.0

    # Trade duration stats
    durations = [t["exit_idx"] - t["entry_idx"] for t in trade_log]
    avg_duration = float(np.mean(durations)) if durations else 0

    # Final equity
    final_equity = float(eq[-1]) if len(eq) > 0 else 1.0
    total_return = (final_equity - 1.0) * 100

    # Consecutive wins / losses
    streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    cur = 0
    for p in pnls:
        if p > 0:
            cur = cur + 1 if p > 0 else 1
            max_win_streak = max(max_win_streak, cur)
        else:
            cur = 0
        max_loss_streak = max(max_loss_streak, abs(cur)) if p < 0 else max_loss_streak

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "profit_factor": round(pf, 3),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "calmar": round(calmar, 3),
        "max_dd": round(max_dd, 2),
        "return_pct": round(total_return, 2),
        "final_equity": round(final_equity, 4),
        "mae": round(mae, 4),
        "mfe": round(mfe, 4),
        "kelly": round(kelly, 4),
        "avg_duration": round(avg_duration, 1),
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
    }


# ─── Jesse backtest config ───────────────────────────────────────────────────


def jesse_config_for_run(
    symbol: str,
    timeframe: str,
    starting_balance: float = 50_000,
    leverage: int = 1,
    fee: float = 0.001,
) -> tuple:
    """
    Build the 4-part config tuple for jesse.research.backtest().
    Returns (config, routes, data_routes, candles).
    """
    exchange = "Binance"
    sym = symbol.replace("BTCUSDT", "BTC-USDT")
    tf_map = {"30m": "3m", "1h": "1m", "4h": "4m", "1d": "1D"}
    jesse_tf = tf_map.get(timeframe, "1m")

    cfg = {
        "starting_balance": starting_balance,
        "fee": fee,
        "type": "futures" if leverage > 1 else "spot",
        "futures_leverage": leverage,
        "futures_leverage_mode": "cross",
        "exchange": exchange,
        "warm_up_candles": 50,
    }
    routes = [
        {
            "exchange": exchange,
            "strategy": "Alpha_momentum_flip",
            "symbol": sym,
            "timeframe": jesse_tf,
        }
    ]
    data_routes = [{"exchange": exchange, "symbol": sym, "timeframe": jesse_tf}]
    return cfg, routes, data_routes


# ─── Single strategy runner ──────────────────────────────────────────────────


def run_strategy_jesse(
    strategy_name: str,
    timeframe: str,
    params: dict,
    candles_arr: np.ndarray,
    max_combos: int | None = None,
) -> dict | None:
    """
    Run a single parameter combo via Jesse research.backtest().
    Returns a metrics dict or None on failure.
    """
    import jesse_strategies as js
    from jesse_strategies import _global_indicators, _global_params

    sym = "BTC-USDT"

    # Precompute indicators for this candle set
    ind = js.compute_indicators(candles_arr, params)
    _global_indicators[sym] = ind
    _global_params[sym] = params

    # Get strategy class
    strat_cls = js.get_strategy_class(strategy_name)

    exchange = "Binance"
    sym_ji = sym
    tf_map = {"30m": "3m", "1h": "1m", "4h": "4m", "1d": "1D"}
    jesse_tf = tf_map.get(timeframe, "1m")

    cfg = {
        "starting_balance": 50_000,
        "fee": 0.001,
        "type": "spot",
        "exchange": exchange,
        "warm_up_candles": 50,
    }
    routes = [
        {
            "exchange": exchange,
            "strategy": strat_cls.__name__,
            "symbol": sym_ji,
            "timeframe": jesse_tf,
        }
    ]
    data_routes = [{"exchange": exchange, "symbol": sym_ji, "timeframe": jesse_tf}]

    # Build candles dict for Jesse
    candles = {
        f"{exchange}-{sym_ji}": {
            "exchange": exchange,
            "symbol": sym_ji,
            "candles": candles_arr,
        }
    }

    try:
        result = backtest(
            config=cfg,
            routes=routes,
            data_routes=data_routes,
            candles=candles,
            generate_equity_curve=True,
            generate_json=True,
        )
    except Exception as e:
        print(f"  [!] Jesse backtest error ({strategy_name} {timeframe}): {e}")
        return None

    if not result:
        return None

    # Extract metrics from Jesse result
    metrics = result.get("metrics", {})
    trades = result.get("trades", [])
    equity_curve = result.get("equity_curve", [])

    # Map Jesse metrics to our format
    jm = {}
    jm["total_trades"] = metrics.get("total", 0)
    jm["wins"] = metrics.get("win_rate", 0) / 100 * jm["total_trades"]
    jm["losses"] = jm["total_trades"] - jm["wins"]
    jm["win_rate"] = metrics.get("win_rate", 0)
    jm["profit_factor"] = metrics.get("profit_factor", 0)
    jm["sharpe"] = metrics.get("sharpe_ratio", 0)
    jm["sortino"] = metrics.get("sortino_ratio", 0)
    jm["max_dd"] = metrics.get("max_drawdown", 0)
    jm["return_pct"] = metrics.get("total_return", 0)
    jm["final_equity"] = result.get("final_equity", 1.0)

    # Build trade log in our format
    trade_log = []
    for t in trades:
        trade_log.append(
            {
                "entry_idx": 0,
                "exit_idx": 0,
                "type": t.get("type", "LONG"),
                "entry": t.get("entry_price", 0),
                "exit": t.get("exit_price", 0),
                "pnl": t.get("pnl", 0),
                "equity": t.get("equity", 1.0),
            }
        )

    # Enhance with our extra metrics
    extra = compute_metrics(trade_log, equity_curve)
    jm.update(extra)
    jm["jesse_metrics"] = {
        "sharpe": round(metrics.get("sharpe_ratio", 0), 3),
        "sortino": round(metrics.get("sortino_ratio", 0), 3),
        "calmar": round(
            (
                metrics.get("total_return", 0)
                / max(metrics.get("max_drawdown", 0.1), 0.1)
            ),
            3,
        ),
        "win_rate": round(metrics.get("win_rate", 0), 2),
        "total_trades": int(jm["total_trades"]),
        "profit_factor": round(metrics.get("profit_factor", 0), 3),
        "max_dd": round(metrics.get("max_drawdown", 0), 2),
        "return_pct": round(metrics.get("total_return", 0), 2),
        "kelly": round(extra.get("kelly", 0), 4),
        "mae": round(extra.get("mae", 0), 4),
        "mfe": round(extra.get("mfe", 0), 4),
    }

    return jm


# ─── Grid search runner ──────────────────────────────────────────────────────


def run_strategy_grid(
    strategy_name: str,
    timeframe: str,
    candles_arr: np.ndarray,
    max_combos: int | None = 100,
) -> dict:
    """
    Run full grid search for a strategy on a timeframe.
    Returns the best result JSON (matching Alpha's format).
    """
    grid_fn = STRAT_GRIDS.get(strategy_name, fast_grid)
    grid = list(grid_fn())
    if max_combos:
        grid = grid[:max_combos]

    print(f"\n[run_jesse] {strategy_name} | {timeframe} | {len(grid)} combos")

    best_sharpe = -999
    best_result = None
    all_results = []

    for i, params in enumerate(grid):
        if i % 20 == 0:
            print(f"  [{i}/{len(grid)}] testing...")
        res = run_strategy_jesse(strategy_name, timeframe, params, candles_arr)
        if res and res.get("total_trades", 0) > 5:
            res["params"] = params
            all_results.append(res)
            if res["sharpe"] > best_sharpe:
                best_sharpe = res["sharpe"]
                best_result = res

    # Save best
    if best_result:
        suffix = f"{strategy_name}_{timeframe}_jesse_best.json"
        out_path = os.path.join(RESULTS_DIR, suffix)
        output = {
            "strategy": strategy_name,
            "timeframe": timeframe,
            "params": best_result.get("params", {}),
            "metrics": {
                "sharpe": best_result.get("sharpe", 0),
                "sortino": best_result.get("sortino", 0),
                "calmar": best_result.get("calmar", 0),
                "max_dd": best_result.get("max_dd", 0),
                "win_rate": best_result.get("win_rate", 0),
                "total_trades": best_result.get("total_trades", 0),
                "profit_factor": best_result.get("profit_factor", 0),
                "return_pct": best_result.get("return_pct", 0),
                "mae": best_result.get("mae", 0),
                "mfe": best_result.get("mfe", 0),
                "kelly": best_result.get("kelly", 0),
                "max_win_streak": best_result.get("max_win_streak", 0),
                "max_loss_streak": best_result.get("max_loss_streak", 0),
                "jesse_metrics": best_result.get("jesse_metrics", {}),
            },
        }
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"  [✓] Saved best result to {out_path}")
        print(
            f"      Sharpe={best_result['sharpe']:.3f} | Return={best_result['return_pct']:.1f}% | MDD={best_result['max_dd']:.1f}% | WinRate={best_result['win_rate']:.1f}%"
        )

    return best_result or {}


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Jesse backtest runner for Alpha")
    parser.add_argument(
        "--strategy", type=str, default=None, help="Run single strategy"
    )
    parser.add_argument(
        "--timeframe", type=str, default="1D", help="Timeframe: 30m, 1h, 4h, 1d"
    )
    parser.add_argument(
        "--max-combos", type=int, default=100, help="Max combos per strategy"
    )
    parser.add_argument("--all", action="store_true", help="Run all strategies")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Load candles
    tf = args.timeframe
    tf_map_alpha = {"30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d"}
    alpha_tf = tf_map_alpha.get(tf, "1d")
    candles_arr = load_alpha_data(alpha_tf)
    print(
        f"[run_jesse] Loaded {len(candles_arr)} candles | {candles_arr[0,0]} -> {candles_arr[-1,0]}"
    )

    if args.all:
        for sname in (
            js_strategies
            if False
            else [
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
        ):
            for tframe in ["1h", "4h", "1d"]:
                tf_arr = load_alpha_data(tframe)
                run_strategy_grid(sname, tframe, tf_arr, args.max_combos)
    elif args.strategy:
        run_strategy_grid(args.strategy, tf, candles_arr, args.max_combos)
    else:
        # Default: run momentum_flip on 1D as quick test
        run_strategy_grid("momentum_flip", "1d", candles_arr, args.max_combos)
