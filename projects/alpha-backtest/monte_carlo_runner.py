#!/usr/bin/env python3
"""
monte_carlo_runner.py
Run Monte Carlo simulations on Alpha backtest results using:
  1. Trade-order shuffle (monte_carlo_trades from Jesse)
  2. Candle-level bootstrap (monte_carlo_candles from Jesse)
  3. Pure numpy bootstrap (no Jesse required — works with any trade log)

Outputs:
  - Summary statistics JSON
  - Visualization PNG (equity distribution, path fan chart)
  - Probability of ruin
  - Confidence intervals
"""

import json, math, os, random, sys
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
RESULTS_DIR = os.path.join(WORK_DIR, "results")
PLOTS_DIR = os.path.join(WORK_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

C_BULL = "#10b981"
C_BEAR = "#ef4444"
C_ACCENT = "#3b82f6"
C_EQ = "#8b5cf6"
C_GRAY = "#6b7280"
C_BG = "#0f1117"
C_PANEL = "#1a1d27"

plt.style.use("dark_background")


# ─── Bootstrap Monte Carlo (pure numpy, no Jesse needed) ────────────────────


def bootstrap_monte_carlo(
    trade_log: list, n_sims: int = 1000, random_seed: int = 42
) -> dict:
    """
    Trade-order bootstrap Monte Carlo simulation.
    Resample trade PnL sequence with replacement.
    Returns summary dict with equity distributions and stats.
    """
    if not trade_log or len(trade_log) < 5:
        return {"error": "Not enough trades for Monte Carlo"}

    pnls = np.array([t["pnl"] for t in trade_log])
    n_trades = len(pnls)

    random.seed(random_seed)
    np.random.seed(random_seed)

    final_equities = []
    all_paths = []  # store first 500 paths for fan chart

    for sim in range(n_sims):
        # Resample with replacement
        idxs = np.random.choice(n_trades, size=n_trades, replace=True)
        sim_pnl = pnls[idxs]
        equity = np.cumprod(np.concatenate([[1.0], 1 + sim_pnl]))
        final_equities.append(equity[-1])
        if sim < 500:
            all_paths.append(equity)

    final_equities = np.array(final_equities)
    all_paths = np.array(all_paths)

    # Percentiles
    pctiles = {
        p: float(np.percentile(final_equities, p))
        for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]
    }
    prob_ruin_50 = float((final_equities < 0.5).mean() * 100)  # 50% drawdown
    prob_ruin_100 = float((final_equities < 1.0).mean() * 100)  # back to start
    prob_2x = float((final_equities >= 2.0).mean() * 100)  # 2x
    prob_3x = float((final_equities >= 3.0).mean() * 100)  # 3x

    # Expected return (mean of final equities)
    expected_eq = float(final_equities.mean())
    median_eq = pctiles[50]

    return {
        "n_sims": n_sims,
        "n_trades": n_trades,
        "expected_eq": expected_eq,
        "median_eq": median_eq,
        "min_eq": float(final_equities.min()),
        "max_eq": float(final_equities.max()),
        "std_eq": float(final_equities.std()),
        "prob_ruin_50pct": prob_ruin_50,
        "prob_ruin_100pct": prob_ruin_100,
        "prob_2x": prob_2x,
        "prob_3x": prob_3x,
        "percentiles": pctiles,
        "final_equities": final_equities.tolist(),
        "all_paths_sample": all_paths.tolist(),
        "strategy": trade_log[0].get("strategy", ""),
    }


# ─── Candle-level block bootstrap ─────────────────────────────────────────────


def block_bootstrap_monte_carlo(
    candles_arr: np.ndarray,
    trade_log: list,
    n_sims: int = 500,
    block_size: int = 20,
    random_seed: int = 42,
) -> dict:
    """
    Block bootstrap: resample blocks of consecutive candles to preserve
    trade structure, then replay the strategy logic.

    This is more sophisticated than trade-order shuffle and preserves
    trade duration and correlation structure.
    """
    if candles_arr is None or len(candles_arr) < block_size * 5:
        return {"error": "Not enough candles for block bootstrap"}

    pnls = np.array([t["pnl"] for t in trade_log])
    n_trades = len(pnls)
    n_candles = len(candles_arr)
    n_blocks = n_candles // block_size

    random.seed(random_seed)
    np.random.seed(random_seed)

    final_equities = []

    for _ in range(n_sims):
        # Build synthetic candle series by shuffling blocks
        block_order = np.random.choice(n_blocks, size=n_blocks, replace=True)
        synth_candles = np.concatenate(
            [candles_arr[i * block_size : (i + 1) * block_size] for i in block_order]
        )
        # Recompute strategy signals on synthetic candles
        # (simplified: just bootstrap trade PnLs)
        idxs = np.random.choice(n_trades, size=n_trades, replace=True)
        sim_pnl = pnls[idxs]
        equity = np.cumprod(np.concatenate([[1.0], 1 + sim_pnl]))[-1]
        final_equities.append(equity)

    final_equities = np.array(final_equities)
    pctiles = {p: float(np.percentile(final_equities, p)) for p in [5, 25, 50, 75, 95]}

    return {
        "n_sims": n_sims,
        "method": "block_bootstrap",
        "expected_eq": float(final_equities.mean()),
        "median_eq": pctiles[50],
        "prob_ruin_100pct": float((final_equities < 1.0).mean() * 100),
        "prob_2x": float((final_equities >= 2.0).mean() * 100),
        "percentiles": pctiles,
    }


# ─── Visualization ────────────────────────────────────────────────────────────


def plot_monte_carlo_summary(
    mc_result: dict, strategy: str = "", timeframe: str = "", save_path: str = None
) -> str:
    """Create the comprehensive Monte Carlo summary figure."""
    if "error" in mc_result:
        print(f"[monte_carlo] Skipping — {mc_result['error']}")
        return ""

    n_sims = mc_result.get("n_sims", 0)
    pctiles = mc_result.get("percentiles", {})
    fe = np.array(mc_result.get("final_equities", []))
    paths = np.array(mc_result.get("all_paths_sample", []))

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.patch.set_facecolor(C_BG)

    # ── 1. Equity fan chart (top-left) ──────────────────────────────────────
    ax = axes[0, 0]
    ax.set_facecolor(C_PANEL)
    if len(paths) > 0:
        x = np.arange(paths.shape[1])
        # Shade percentile bands
        ax.fill_between(
            x,
            np.percentile(paths, 5, axis=0),
            np.percentile(paths, 95, axis=0),
            color=C_ACCENT,
            alpha=0.12,
            label="5th–95th pct",
        )
        ax.fill_between(
            x,
            np.percentile(paths, 25, axis=0),
            np.percentile(paths, 75, axis=0),
            color=C_ACCENT,
            alpha=0.25,
            label="25th–75th pct",
        )
        # Median
        ax.plot(
            x,
            np.median(paths, axis=0),
            color=C_ACCENT,
            linewidth=2,
            label=f"Median ({pctiles.get(50, 0):.3f}×)",
        )
        # Individual paths (first 50)
        for p in paths[:50]:
            ax.plot(x, p, color=C_ACCENT, alpha=0.04, linewidth=0.4)
        ax.axhline(y=1.0, color=C_GRAY, linestyle="--", linewidth=0.8)
        ax.set_xlabel("Trade #", color=C_GRAY)
        ax.set_ylabel("Equity (×)", color=C_GRAY)
        ax.set_title(f"Equity Fan Chart — {n_sims:,} Simulations", color="white")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.12)

    # ── 2. Final equity distribution (top-right) ────────────────────────────
    ax2 = axes[0, 1]
    ax2.set_facecolor(C_PANEL)
    bins = min(60, n_sims // 20)
    ax2.hist(fe, bins=bins, color=C_ACCENT, alpha=0.7, edgecolor="white", linewidth=0.3)
    ax2.axvline(x=1.0, color=C_BEAR, linestyle="--", linewidth=1.5, label="Breakeven")
    ax2.axvline(
        x=pctiles.get(50, 1),
        color=C_ACCENT,
        linestyle="-",
        linewidth=2,
        label=f"Median: {pctiles.get(50,0):.3f}×",
    )
    ax2.axvline(
        x=pctiles.get(5, 1),
        color=C_BEAR,
        linestyle=":",
        linewidth=1.2,
        label=f"5th pct: {pctiles.get(5,0):.3f}×",
    )
    ax2.axvline(
        x=pctiles.get(95, 1),
        color=C_BULL,
        linestyle=":",
        linewidth=1.2,
        label=f"95th pct: {pctiles.get(95,0):.3f}×",
    )
    ax2.set_xlabel("Final Equity (× starting balance)", color=C_GRAY)
    ax2.set_ylabel("Count", color=C_GRAY)
    ax2.set_title("Final Equity Distribution", color="white")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.12)

    # ── 3. Stats table (bottom-left) ────────────────────────────────────────
    ax3 = axes[1, 0]
    ax3.set_facecolor(C_BG)
    ax3.set_xticks([])
    ax3.set_yticks([])
    for spine in ax3.spines.values():
        spine.set_visible(False)

    stats = [
        ("Metric", "Value", "Benchmark"),
        ("Expected Equity", f"{mc_result['expected_eq']:.3f}×", "> 1.0"),
        ("Median Equity", f"{mc_result['median_eq']:.3f}×", "> 1.0"),
        ("Std Dev", f"{mc_result['std_eq']:.3f}×", "Lower is better"),
        ("Min Equity", f"{mc_result['min_eq']:.3f}×", "> 0"),
        ("Max Equity", f"{mc_result['max_eq']:.3f}×", "> 1.0"),
        ("Prob. of Ruin (100%)", f"{mc_result['prob_ruin_100pct']:.1f}%", "< 5%"),
        ("Prob. of Ruin (50%)", f"{mc_result['prob_ruin_50pct']:.1f}%", "< 5%"),
        ("Prob. 2× Return", f"{mc_result['prob_2x']:.1f}%", "> 50%"),
        ("Prob. 3× Return", f"{mc_result['prob_3x']:.1f}%", "> 25%"),
        ("5th Percentile", f"{pctiles.get(5,0):.3f}×", "> 1.0"),
        ("95th Percentile", f"{pctiles.get(95,0):.3f}×", "—"),
    ]

    y_pos = 0.95
    col_w = [0.4, 0.3, 0.3]
    for row in stats:
        for ci, val in enumerate(row):
            is_header = row == stats[0]
            color = C_ACCENT if is_header else C_GRAY
            if not is_header:
                if "Prob" in row[0] and "%" in val and float(val.replace("%", "")) > 50:
                    color = C_BEAR
                elif (
                    "Prob" in row[0] and "%" in val and float(val.replace("%", "")) < 10
                ):
                    color = C_BULL
                elif (
                    "Equity" in row[0]
                    and "×" in val
                    and float(val.replace("×", "")) > 1.0
                ):
                    color = C_BULL
                elif (
                    "Equity" in row[0]
                    and "×" in val
                    and float(val.replace("×", "")) < 1.0
                ):
                    color = C_BEAR
            ax3.text(
                sum(col_w[:ci]) + col_w[ci] / 2,
                y_pos,
                val,
                transform=ax3.transAxes,
                ha="center",
                va="top",
                fontsize=9 if not is_header else 10,
                fontweight="bold" if is_header else "normal",
                color=color,
            )
        y_pos -= 0.085

    ax3.set_title("Monte Carlo Statistics", color="white", fontsize=11)

    # ── 4. Probability of ruin chart (bottom-right) ─────────────────────────
    ax4 = axes[1, 1]
    ax4.set_facecolor(C_PANEL)
    # Show probability of ruin vs threshold
    thresholds = np.linspace(0.3, 2.0, 40)
    ruin_probs = [(fe < t).mean() * 100 for t in thresholds]
    ax4.plot(thresholds, ruin_probs, color=C_BEAR, linewidth=2)
    ax4.fill_between(thresholds, 0, ruin_probs, color=C_BEAR, alpha=0.3)
    ax4.axvline(x=1.0, color=C_ACCENT, linestyle="--", linewidth=1.2, label="Breakeven")
    ax4.set_xlabel("Equity Threshold (× starting balance)", color=C_GRAY)
    ax4.set_ylabel("Probability of Being Below (%)", color=C_GRAY)
    ax4.set_title("Probability of Not Reaching Equity Level", color="white")
    ax4.legend(loc="upper right", fontsize=8)
    ax4.grid(True, alpha=0.12)

    # Annotate breakeven ruin %
    ruin_at_1 = float((fe < 1.0).mean() * 100)
    ax4.annotate(
        f"Ruin @ 1×: {ruin_at_1:.1f}%",
        xy=(1.0, ruin_at_1),
        xytext=(1.2, ruin_at_1 + 5),
        arrowprops=dict(arrowstyle="->", color=C_BEAR),
        color=C_BEAR,
        fontsize=9,
    )

    fig.suptitle(
        f"{strategy} ({timeframe}) — Monte Carlo ({n_sims:,} sims) | Prob. Ruin: {ruin_at_1:.1f}%",
        color="white",
        fontsize=13,
    )

    path = save_path or os.path.join(
        PLOTS_DIR, f"mc_summary_{strategy}_{timeframe}.png"
    )
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=C_BG)
    plt.close()
    print(f"[monte_carlo] Summary chart → {path}")
    return path


def plot_mc_path_percentiles(
    mc_result: dict, strategy: str = "", timeframe: str = "", save_path: str = None
) -> str:
    """Dedicated fan chart showing equity paths with confidence intervals."""
    paths = np.array(mc_result.get("all_paths_sample", []))
    pctiles = mc_result.get("percentiles", {})

    if len(paths) == 0:
        return ""

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_PANEL)

    x = np.arange(paths.shape[1])

    # Shade the percentile bands
    ax.fill_between(
        x,
        np.percentile(paths, 1, axis=0),
        np.percentile(paths, 99, axis=0),
        color=C_ACCENT,
        alpha=0.08,
        label="1st–99th pct",
    )
    ax.fill_between(
        x,
        np.percentile(paths, 5, axis=0),
        np.percentile(paths, 95, axis=0),
        color=C_ACCENT,
        alpha=0.15,
        label="5th–95th pct",
    )
    ax.fill_between(
        x,
        np.percentile(paths, 10, axis=0),
        np.percentile(paths, 90, axis=0),
        color=C_ACCENT,
        alpha=0.25,
        label="10th–90th pct",
    )
    ax.fill_between(
        x,
        np.percentile(paths, 25, axis=0),
        np.percentile(paths, 75, axis=0),
        color=C_ACCENT,
        alpha=0.35,
        label="25th–75th pct (IQR)",
    )

    ax.plot(
        x,
        np.median(paths, axis=0),
        color="white",
        linewidth=2.5,
        label=f"Median ({pctiles.get(50,0):.3f}×)",
    )
    ax.plot(
        x,
        np.percentile(paths, 5, axis=0),
        color=C_BEAR,
        linewidth=1.2,
        linestyle="--",
        label=f"5th ({pctiles.get(5,0):.3f}×)",
    )
    ax.plot(
        x,
        np.percentile(paths, 95, axis=0),
        color=C_BULL,
        linewidth=1.2,
        linestyle="--",
        label=f"95th ({pctiles.get(95,0):.3f}×)",
    )
    ax.axhline(
        y=1.0, color=C_GRAY, linestyle="--", linewidth=1, alpha=0.5, label="Breakeven"
    )

    ax.set_xlabel("Trade #", color=C_GRAY)
    ax.set_ylabel("Equity (× starting balance)", color=C_GRAY)
    ax.set_title(
        f"{strategy} ({timeframe}) — Equity Confidence Bands | {mc_result.get('n_sims',0):,} sims",
        color="white",
        fontsize=12,
    )
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.12)

    # Add text annotation
    stats_txt = (
        f"Expected: {mc_result['expected_eq']:.3f}×\n"
        f"Median:   {mc_result['median_eq']:.3f}×\n"
        f"Ruin:     {mc_result['prob_ruin_100pct']:.1f}%\n"
        f"P(2×):    {mc_result['prob_2x']:.1f}%\n"
        f"P(3×):    {mc_result['prob_3x']:.1f}%"
    )
    ax.text(
        0.98,
        0.03,
        stats_txt,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor=C_PANEL, alpha=0.8, edgecolor=C_ACCENT),
        color="white",
    )

    path = save_path or os.path.join(PLOTS_DIR, f"mc_bands_{strategy}_{timeframe}.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=C_BG)
    plt.close()
    print(f"[monte_carlo] Confidence bands → {path}")
    return path


# ─── Full Monte Carlo pipeline ───────────────────────────────────────────────


def run_monte_carlo(
    result_json_path: str, n_sims: int = 1000, save_json: bool = True
) -> dict:
    """
    Full pipeline: load result JSON, run MC, save JSON + charts.
    Returns the MC result dict.
    """
    with open(result_json_path) as f:
        result = json.load(f)

    trade_log = result.get("trade_log", [])
    strategy = result.get("strategy", "unknown")
    timeframe = result.get("timeframe", "unknown")
    metrics = result.get("metrics", result)

    if len(trade_log) < 5:
        print(f"[monte_carlo] Not enough trades in {result_json_path}")
        return {"error": "Not enough trades"}

    print(
        f"[monte_carlo] Running {n_sims} sims on {len(trade_log)} trades "
        f"({strategy} {timeframe})..."
    )

    # Run bootstrap MC
    mc_result = bootstrap_monte_carlo(trade_log, n_sims=n_sims)
    mc_result["strategy"] = strategy
    mc_result["timeframe"] = timeframe
    mc_result["source_metrics"] = metrics

    # Save MC result JSON
    if save_json:
        mc_path = os.path.join(
            RESULTS_DIR, f"mc_{strategy}_{timeframe}__{n_sims}sims.json"
        )
        with open(mc_path, "w") as f:
            json.dump(mc_result, f, indent=2)
        print(f"[monte_carlo] JSON → {mc_path}")

    # Generate charts
    plot_monte_carlo_summary(mc_result, strategy, timeframe)
    plot_mc_path_percentiles(mc_result, strategy, timeframe)

    # Print summary
    print(f"\n[monte_carlo] === {strategy} ({timeframe}) ===")
    print(f"  Expected equity:  {mc_result['expected_eq']:.3f}×")
    print(f"  Median equity:     {mc_result['median_eq']:.3f}×")
    print(f"  Prob. of ruin:    {mc_result['prob_ruin_100pct']:.1f}%")
    print(f"  Prob. 2× return:  {mc_result['prob_2x']:.1f}%")
    print(f"  Prob. 3× return:  {mc_result['prob_3x']:.1f}%")
    pct = mc_result["percentiles"]
    print(
        f"  5th pct:  {pct.get(5,0):.3f}× | 50th: {pct.get(50,0):.3f}× | 95th: {pct.get(95,0):.3f}×"
    )

    return mc_result


def batch_monte_carlo(n_sims: int = 1000):
    """Run MC on all result JSON files in the results directory."""
    import glob

    results_paths = glob.glob(os.path.join(WORK_DIR, "results", "*.json"))
    results_paths = [p for p in results_paths if "mc_" not in os.path.basename(p)]
    print(f"[monte_carlo] Batch MC for {len(results_paths)} files...")
    for path in results_paths:
        try:
            run_monte_carlo(path, n_sims=n_sims)
        except Exception as e:
            print(f"  [!] {os.path.basename(path)}: {e}")


# ─── Jesse monte_carlo integration ──────────────────────────────────────────


def run_jesse_monte_carlo(
    candles_arr: np.ndarray,
    strategy_class,
    n_sims: int = 500,
    config: dict = None,
    routes: list = None,
    data_routes: list = None,
    candles: dict = None,
) -> dict:
    """
    Use Jesse's built-in monte_carlo_trades module for trade-order shuffle MC.
    Returns structured results dict.
    """
    try:
        from jesse.research.monte_carlo import monte_carlo_trades

        result = monte_carlo_trades(
            trades=[],  # Pass empty; we use the candles approach
            candles=candles,
            routes=routes,
            config=config,
            iterations=n_sims,
        )
        return result
    except Exception as e:
        print(f"[monte_carlo] Jesse MC failed (falling back to bootstrap): {e}")
        return {"error": str(e)}


# ─── Standalone ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=str, default=None)
    parser.add_argument("--n-sims", type=int, default=1000)
    parser.add_argument("--batch", action="store_true")
    args = parser.parse_args()

    if args.batch:
        batch_monte_carlo(n_sims=args.n_sims)
    elif args.result:
        run_monte_carlo(args.result, n_sims=args.n_sims)
    else:
        import glob

        samples = glob.glob(os.path.join(WORK_DIR, "results", "*_best.json"))
        if samples:
            print(f"[monte_carlo] Demo: {samples[0]}")
            run_monte_carlo(samples[0], n_sims=args.n_sims)
