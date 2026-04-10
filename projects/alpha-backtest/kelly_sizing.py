#!/usr/bin/env python3
"""
Kelly Criterion Position Sizing for Alpha's Trading System

Kelly Formula: f = (b × p - q) / b
  where b = avg_win / avg_loss (odds), p = win_rate, q = 1 - p

Conservative approach: use Half-Kelly (f/2) capped at 25%
"""

import json, os, sys
import numpy as np
import pandas as pd

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
RESULTS_DIR = os.path.join(WORK_DIR, "results")


# ─────────────────────────────────────────────────────────
# KELLY FORMULA
# ─────────────────────────────────────────────────────────
def kelly_fraction(win_rate, avg_win, avg_loss):
    """
    Full Kelly fraction: f = (b × p - q) / b = p - q/b
    where b = avg_win / avg_loss (odds), p = win_rate, q = 1 - p

    Parameters:
        win_rate:  fraction of winning trades (0.0–1.0)
        avg_win:   average win (absolute value, e.g. $200)
        avg_loss:  average loss (absolute value, e.g. $100)

    Returns:
        Kelly fraction (0.0–1.0), uncapped
    """
    if avg_loss <= 0:
        return 0.0
    b = avg_win / avg_loss  # odds (how many $ you win per $ you lose)
    p = float(win_rate)
    q = 1.0 - p
    # Kelly: f = (b*p - q) / b  [but (b*p - q)/b = p - q/b]
    f = p - q / b
    return float(f)


def kelly_fraction_pct(win_rate, avg_win_pct, avg_loss_pct):
    """
    Kelly fraction using percentage returns instead of absolute $.

    Parameters:
        win_rate:    fraction of winning trades (0.0–1.0)
        avg_win_pct: average win as decimal (e.g. 0.03 for 3%)
        avg_loss_pct: average loss as decimal (e.g. 0.015 for 1.5%)

    Returns:
        Kelly fraction (0.0–1.0), uncapped
    """
    return kelly_fraction(win_rate, avg_win_pct, avg_loss_pct)


def kelly_size(equity, win_rate, avg_win, avg_loss, style="half_kelly", max_kelly=0.25):
    """
    Calculate dollar position size using Kelly criterion.

    Parameters:
        equity:       current account equity ($)
        win_rate:     fraction of winning trades
        avg_win:      average win amount ($)
        avg_loss:     average loss amount ($)
        style:        "full_kelly" | "half_kelly" | "quarter_kelly"
        max_kelly:    maximum Kelly fraction to allow (safety cap)

    Returns:
        dict with position_size ($) and metadata
    """
    raw = kelly_fraction(win_rate, avg_win, avg_loss)

    if style == "full_kelly":
        f = raw
    elif style == "half_kelly":
        f = raw / 2.0
    elif style == "quarter_kelly":
        f = raw / 4.0
    else:
        f = raw / 2.0

    f = max(0.0, min(float(f), max_kelly))
    position_size = equity * f

    return {
        "position_size": round(float(position_size), 2),
        "kelly_fraction": round(f, 4),
        "full_kelly": round(float(max(0, raw)), 4),
        "style": style,
        "equity": round(float(equity), 2),
        "win_rate": round(float(win_rate), 4),
        "avg_win": round(float(avg_win), 2),
        "avg_loss": round(float(avg_loss), 2),
        "edge": round(float(raw * avg_win / (avg_loss + 1e-9)), 4),
    }


def kelly_from_trade_history(trades):
    """
    Calculate Kelly from a list of trade results.

    Parameters:
        trades: list of dicts with keys "pnl" or "return"

    Returns:
        dict with Kelly analysis
    """
    if not trades:
        return {"error": "No trades provided"}

    pnls = []
    for t in trades:
        if "pnl" in t:
            pnls.append(float(t["pnl"]))
        elif "return" in t:
            pnls.append(float(t["return"]))
        elif "roi" in t:
            pnls.append(float(t["roi"]))

    if not pnls:
        return {"error": "Could not extract PnL from trades"}

    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p <= 0]

    n = len(pnls)
    nw = len(wins)
    nl = len(losses)

    win_rate = nw / n if n > 0 else 0
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    raw_kelly = kelly_fraction(win_rate, avg_win, avg_loss)
    half_k = raw_kelly / 2.0
    capped = max(0.0, min(half_k, 0.25))

    return {
        "n_trades": n,
        "n_wins": nw,
        "n_losses": nl,
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "full_kelly": round(float(raw_kelly), 4),
        "half_kelly": round(float(half_k), 4),
        "quarter_kelly": round(float(raw_kelly / 4.0), 4),
        "recommended_pct": round(float(capped * 100), 2),  # % of equity
        "recommended": "half_kelly (capped 25%)",
    }


def kelly_from_json_results(result_file):
    """Load backtest results JSON and compute Kelly sizing from it."""
    with open(result_file) as f:
        r = json.load(f)

    trades = r.get("trades", [])
    if not trades:
        # Try to extract from equity curve
        equity = r.get("equity_curve", [])
        if len(equity) > 1:
            rets = np.diff(equity) / equity[:-1]
            wins = [1 for e in rets if e > 0]
            losses = [abs(e) for e in rets if e <= 0]
            n = len(rets)
            nw = len(wins)
            nl = len(losses)
            win_rate = nw / n if n > 0 else 0
            avg_win = np.mean(wins) if wins else 0.01
            avg_loss = np.mean(losses) if losses else 0.01
        else:
            return {"error": "No trades or equity curve found"}
    else:
        res = kelly_from_trade_history(trades)
        return res

    raw_kelly = kelly_fraction(win_rate, avg_win, avg_loss)
    return {
        "source": os.path.basename(result_file),
        "win_rate": round(win_rate, 4),
        "avg_win": round(float(avg_win), 4),
        "avg_loss": round(float(avg_loss), 4),
        "full_kelly": round(float(raw_kelly), 4),
        "half_kelly": round(float(raw_kelly / 2), 4),
        "quarter_kelly": round(float(raw_kelly / 4), 4),
        "recommended_pct": round(float(max(0, min(raw_kelly / 2, 0.25)) * 100), 2),
    }


def apply_kelly_to_backtester(result_files, equity=10000):
    """
    Apply Kelly sizing to all strategies in results directory.

    Returns:
        DataFrame with Kelly sizing recommendations for each strategy
    """
    rows = []
    for f in sorted(result_files):
        try:
            r = kelly_from_json_results(f)
            if "error" in r:
                continue
            strat_name = (
                os.path.basename(f).replace("_v1.json", "").replace("_v2.json", "")
            )
            half_k = r["half_kelly"]
            capped = max(0.0, min(half_k, 0.25))
            pos_size = equity * capped
            rows.append(
                {
                    "strategy": strat_name,
                    "win_rate": r["win_rate"],
                    "avg_win": r["avg_win"],
                    "avg_loss": r["avg_loss"],
                    "full_kelly": r["full_kelly"],
                    "half_kelly": round(half_k, 4),
                    "position_size": round(pos_size, 2),
                    "position_pct": round(capped * 100, 2),
                    "leverage_safe": (
                        round(1.0 / capped, 1) if capped > 0 else float("inf")
                    ),
                }
            )
        except Exception as e:
            print(f"  ⚠ Error processing {f}: {e}")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("half_kelly", ascending=False)
    return df


# ─────────────────────────────────────────────────────────
# KELLY VALIDATION / SANITY CHECKS
# ─────────────────────────────────────────────────────────
def validate_kelly(win_rate, avg_win_pct, avg_loss_pct):
    """Print Kelly analysis with sanity checks."""
    raw = kelly_fraction_pct(win_rate, avg_win_pct, avg_loss_pct)
    half = raw / 2
    quarter = raw / 4
    capped = max(0, min(half, 0.25))

    checks = []
    checks.append(("Kelly positive", raw > 0))
    checks.append(("Half-Kelly < 25%", half <= 0.25))
    checks.append(("Win rate > 50%", win_rate > 0.5))
    checks.append(("Positive edge", avg_win_pct > avg_loss_pct))

    return {
        "win_rate": win_rate,
        "avg_win_pct": avg_win_pct,
        "avg_loss_pct": avg_loss_pct,
        "full_kelly": round(float(raw), 4),
        "half_kelly": round(float(half), 4),
        "quarter_kelly": round(float(quarter), 4),
        "recommended_pct": round(float(capped * 100), 2),
        "sanity_checks": {k: v for k, v in checks},
        "passed": all(v for _, v in checks),
    }


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def run_kelly_analysis():
    print("\n" + "=" * 60)
    print("KELLY CRITERION POSITION SIZING ANALYSIS")
    print("=" * 60)

    # Test the Kelly formula with various scenarios
    scenarios = [
        {
            "label": "Typical RSI strategy",
            "win_rate": 0.42,
            "avg_win_pct": 0.03,
            "avg_loss_pct": 0.015,
        },
        {
            "label": "High-win rate",
            "win_rate": 0.62,
            "avg_win_pct": 0.02,
            "avg_loss_pct": 0.012,
        },
        {
            "label": "Low-win rate",
            "win_rate": 0.35,
            "avg_win_pct": 0.05,
            "avg_loss_pct": 0.02,
        },
        {
            "label": "Breakout strategy",
            "win_rate": 0.38,
            "avg_win_pct": 0.06,
            "avg_loss_pct": 0.03,
        },
        {
            "label": "Conservative",
            "win_rate": 0.55,
            "avg_win_pct": 0.015,
            "avg_loss_pct": 0.01,
        },
    ]

    print("\n  ── Kelly Scenarios ──")
    print(
        f"  {'Scenario':<25} | {'W%':>5} | {'AvgW%':>6} | {'AvgL%':>6} | {'FullK':>7} | {'HalfK':>7} | {'Capped%':>7} | {'✅'}"
    )
    print(f"  {'-'*25}-+-----+-------+-------+--------+--------+--------+---")

    for s in scenarios:
        v = validate_kelly(s["win_rate"], s["avg_win_pct"], s["avg_loss_pct"])
        flag = "✅" if v["passed"] else "⚠️"
        print(
            f"  {s['label']:<25} | {s['win_rate']:>5.1%} | "
            f"{s['avg_win_pct']:>6.2%} | {s['avg_loss_pct']:>6.2%} | "
            f"{v['full_kelly']:>7.2%} | {v['half_kelly']:>7.2%} | "
            f"{v['recommended_pct']:>7.2%} | {flag}"
        )

    # Apply to existing results
    result_files = []
    results_dir = os.path.join(WORK_DIR, "results")
    if os.path.exists(results_dir):
        result_files = [
            os.path.join(results_dir, f)
            for f in os.listdir(results_dir)
            if f.endswith(".json") and "pairs" not in f
        ]

    if result_files:
        print(f"\n  ── Kelly Sizing for Existing Strategies ──")
        df = apply_kelly_to_backtester(result_files)
        if not df.empty:
            print(
                df[
                    [
                        "strategy",
                        "win_rate",
                        "half_kelly",
                        "position_pct",
                        "position_size",
                    ]
                ].to_string(index=False)
            )
            # Save
            out = os.path.join(RESULTS_DIR, "kelly_sizing_recommendations.json")
            df.to_json(out, orient="records", indent=2)
            print(f"\n  Results saved → {out}")
        else:
            print("  No strategy results found.")
    else:
        print("\n  No result files found — skipping strategy Kelly analysis.")

    # Example: $10,000 equity with various Kelly fractions
    equity = 10000
    print(f"\n  ── Position Sizes on ${equity:,.0f} Equity ──")
    print(f"  {'Kelly Style':<20} | {'Fraction':>8} | {'$ Size':>10}")
    print(f"  {'-'*20}-+---------+----------")
    for style, f in [
        ("Full Kelly", 0.15),
        ("Half Kelly", 0.075),
        ("Quarter Kelly", 0.0375),
        ("Fixed 2%", 0.02),
    ]:
        print(f"  {style:<20} | {f:>8.2%} | ${equity*f:>9,.0f}")

    return True


if __name__ == "__main__":
    run_kelly_analysis()
