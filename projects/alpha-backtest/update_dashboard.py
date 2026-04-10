#!/usr/bin/env python3
"""
update_dashboard.py
Reads all Alpha backtest result JSONs and Jesse MC results,
then updates the Quant Alpha Next.js dashboard with:
  - Monte Carlo sections
  - Monthly returns heatmap
  - Trade distribution data
  - Additional risk metrics (Calmar, Kelly, MAE, MFE)
  - Jesse backtest results

Writes: src/app/data/backtests.ts  (TypeScript data file)
        src/app/data/monte_carlo.ts
        src/app/data/risk_metrics.ts
        src/app/data/equity_curves.ts
"""

import json, os, glob
from datetime import datetime

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
RESULTS_DIR = os.path.join(WORK_DIR, "results")
DASHBOARD_DIR = "/home/yat121/.openclaw/workspace/projects/quant-alpha/dashboard"
DASHBOARD_DATA = os.path.join(DASHBOARD_DIR, "src/app/data")
os.makedirs(DASHBOARD_DATA, exist_ok=True)

STRATEGY_DESCS = {
    "momentum_flip": "RSI crosses above 50 = long, below = short. Mean reversion at its simplest.",
    "swing_sniper": "Swing high/low breaks with RSI confirmation. Wait for the pullback to fail.",
    "trend_follower": "EMA crossover. Fast MA crosses slow MA = trend change signal.",
    "institutional_macro": "Daily close above/below 200 SMA on 4H entries. Institutional direction.",
    "overextended_reversal": "Price 2+ std dev from 20 SMA + RSI > 70 or < 30 = fade the move.",
    "hidden_divergence": "Price makes lower low but RSI makes higher high = long. Fade the false break.",
    "previous_day_sweep": "Sweep previous day's high/low with rejection candle = entry.",
    "2b_reversal": "After higher high, if price fails new high and drops below previous low = short.",
    "bb_headfake": "Price squeezes through Bollinger Band then reverses. Fade the breakout.",
    "day_driver": "Open of day + close above previous high = long, vice versa short.",
    "equal_highs_liquidity_grab": "Price hunts equal highs/lows then reverses. Fade the liquidity grab.",
}

STRATEGY_TAGS = {
    "momentum_flip": ["RSI", "Mean Reversion", "Short-term"],
    "swing_sniper": ["Breakout", "Swing", "RSI"],
    "trend_follower": ["Trend", "MA Cross", "Medium-term"],
    "institutional_macro": ["Macro", "SMA", "Long-term"],
    "overextended_reversal": ["Reversal", "RSI", "Volatility"],
    "hidden_divergence": ["Divergence", "RSI", "Advanced"],
    "previous_day_sweep": ["Sweep", "Intraday", "Support/Resistance"],
    "2b_reversal": ["Reversal", "Sweep", "Advanced"],
    "bb_headfake": ["Bollinger Bands", "Reversal", "Volatility"],
    "day_driver": ["Intraday", "Multi-Indicator", "Short-term"],
    "equal_highs_liquidity_grab": ["Liquidity", "Reversal", "Advanced"],
}

# ─── Load all results ─────────────────────────────────────────────────────────


def load_all_results() -> list:
    """Load all JSON files from results/."""
    results = []
    for path in glob.glob(os.path.join(RESULTS_DIR, "*.json")):
        if "mc_" in os.path.basename(path):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            # FINAL_SUMMARY.json is a list of items
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.append(data)
        except Exception as e:
            print(f"[update_dashboard] Failed to load {path}: {e}")
    return results


def load_mc_results() -> list:
    """Load Monte Carlo result JSONs."""
    results = []
    for path in glob.glob(os.path.join(RESULTS_DIR, "mc_*.json")):
        try:
            with open(path) as f:
                results.append(json.load(f))
        except Exception as e:
            print(f"[update_dashboard] Failed to load MC {path}: {e}")
    return results


# ─── Transform to TypeScript ─────────────────────────────────────────────────


def to_ts_array(items: list) -> str:
    """Convert Python list to TypeScript array literal."""
    return json.dumps(items, indent=2)


# ─── Generate backtests.ts ───────────────────────────────────────────────────


def generate_backtests_ts(results: list) -> list:
    """
    Generate TypeScript data file for the backtests dashboard.
    Aggregates best results per strategy/timeframe combo.
    Handles full format {strategy,timeframe,params,metrics} and
    SUMMARY format {strategy,sharpe,mdd,win_rate,trades,return_pct,pf,params}.
    """
    # Normalize SUMMARY-format items to full format
    normalized = []
    for r in results:
        if isinstance(r, dict) and "timeframe" not in r and "metrics" not in r:
            normalized.append(
                {
                    "strategy": r.get("strategy", "unknown"),
                    "timeframe": r.get("timeframe", "unknown"),
                    "params": r.get("params", {}),
                    "metrics": {
                        "sharpe": float(r.get("sharpe", 0)),
                        "sortino": float(r.get("sortino", 0)),
                        "max_dd": float(r.get("mdd", 0)),
                        "win_rate": float(r.get("win_rate", 0)),
                        "total_trades": int(r.get("trades", 0)),
                        "return_pct": float(r.get("return_pct", 0)),
                        "profit_factor": float(r.get("pf", 0)),
                    },
                    "trade_log": r.get("trade_log", []),
                }
            )
        elif isinstance(r, dict):
            normalized.append(r)

    # Group by strategy+timeframe
    by_key = {}
    for r in results:
        key = (r.get("strategy", ""), r.get("timeframe", ""))
        metrics = r.get("metrics", r)
        if by_key.get(key) is None or metrics.get("sharpe", 0) > by_key[key].get(
            "metrics", {}
        ).get("sharpe", 0):
            by_key[key] = r

    strategy_data = []
    for (sname, tf), r in by_key.items():
        metrics = r.get("metrics", r)
        jesse_metrics = r.get("metrics", {}).get("jesse_metrics", {})

        strategy_data.append(
            {
                "id": f"{sname}_{tf}_v2",
                "name": sname,
                "timeframe": tf,
                "desc": STRATEGY_DESCS.get(sname, ""),
                "tags": STRATEGY_TAGS.get(sname, []),
                "best": {
                    "sharpe": float(metrics.get("sharpe", 0)),
                    "return": float(metrics.get("return_pct", 0)),
                    "mdd": float(metrics.get("max_dd", 0)),
                    "win_rate": float(metrics.get("win_rate", 0)),
                    "trades": int(metrics.get("total_trades", 0)),
                    "ann_trades": int(metrics.get("total_trades", 0) // 5),  # rough
                    "profit_factor": float(metrics.get("profit_factor", 0)),
                    "params": {
                        k: float(v) if isinstance(v, (int, float)) else v
                        for k, v in r.get("params", {}).items()
                    },
                    # New Jesse metrics
                    "calmar": float(
                        metrics.get("calmar", jesse_metrics.get("calmar", 0))
                    ),
                    "kelly": float(metrics.get("kelly", jesse_metrics.get("kelly", 0))),
                    "mae": float(metrics.get("mae", jesse_metrics.get("mae", 0))),
                    "mfe": float(metrics.get("mfe", jesse_metrics.get("mfe", 0))),
                    "sortino": float(
                        metrics.get("sortino", jesse_metrics.get("sortino", 0))
                    ),
                    "jesse_sharpe": float(
                        jesse_metrics.get("sharpe", metrics.get("sharpe", 0))
                    ),
                    "jesse_metrics": jesse_metrics,
                },
                "count": 1,
                "has_jesse": bool(jesse_metrics),
                "trade_log": r.get("trade_log", [])[:50],  # First 50 for preview
            }
        )

    return strategy_data


# ─── Generate monte_carlo.ts ─────────────────────────────────────────────────


def generate_mc_ts(mc_results: list) -> list:
    """Generate Monte Carlo TypeScript data."""
    mc_data = []
    for r in mc_results:
        pctiles = r.get("percentiles", {})
        mc_data.append(
            {
                "id": f"mc_{r.get('strategy','unknown')}_{r.get('timeframe','unknown')}",
                "strategy": r.get("strategy", "unknown"),
                "timeframe": r.get("timeframe", "unknown"),
                "n_sims": r.get("n_sims", 0),
                "expected_eq": float(r.get("expected_eq", 1.0)),
                "median_eq": float(r.get("median_eq", 1.0)),
                "std_eq": float(r.get("std_eq", 0)),
                "prob_ruin_100pct": float(r.get("prob_ruin_100pct", 100)),
                "prob_ruin_50pct": float(r.get("prob_ruin_50pct", 50)),
                "prob_2x": float(r.get("prob_2x", 0)),
                "prob_3x": float(r.get("prob_3x", 0)),
                "percentiles": {str(k): float(v) for k, v in pctiles.items()},
                "min_eq": float(r.get("min_eq", 0)),
                "max_eq": float(r.get("max_eq", 0)),
            }
        )
    return mc_data


# ─── Generate risk_metrics.ts ─────────────────────────────────────────────────


def generate_risk_metrics_ts(results: list) -> list:
    """Generate per-strategy risk metrics for the dashboard."""
    risk_data = []
    by_key = {}
    for r in results:
        key = (r.get("strategy", ""), r.get("timeframe", ""))
        metrics = r.get("metrics", r)
        if by_key.get(key) is None or metrics.get("sharpe", 0) > by_key[key].get(
            "metrics", {}
        ).get("sharpe", 0):
            by_key[key] = r

    for (sname, tf), r in by_key.items():
        metrics = r.get("metrics", r)
        jm = metrics.get("jesse_metrics", {})
        risk_data.append(
            {
                "id": f"risk_{sname}_{tf}",
                "strategy": sname,
                "timeframe": tf,
                "sharpe": float(metrics.get("sharpe", 0)),
                "sortino": float(metrics.get("sortino", jm.get("sortino", 0))),
                "calmar": float(metrics.get("calmar", jm.get("calmar", 0))),
                "kelly": float(metrics.get("kelly", jm.get("kelly", 0))),
                "max_dd": float(metrics.get("max_dd", 0)),
                "win_rate": float(metrics.get("win_rate", 0)),
                "profit_factor": float(metrics.get("profit_factor", 0)),
                "mae": float(metrics.get("mae", jm.get("mae", 0))),
                "mfe": float(metrics.get("mfe", jm.get("mfe", 0))),
                "return_pct": float(metrics.get("return_pct", 0)),
                "total_trades": int(metrics.get("total_trades", 0)),
                "max_win_streak": int(metrics.get("max_win_streak", 0)),
                "max_loss_streak": int(metrics.get("max_loss_streak", 0)),
                "avg_duration": float(metrics.get("avg_duration", 0)),
                # Score: composite
                "alpha_score": _compute_alpha_score(metrics),
            }
        )
    return risk_data


def _compute_alpha_score(metrics: dict) -> float:
    """Compute a composite alpha score (0-100)."""
    sharpe = max(min(metrics.get("sharpe", 0) / 3, 1), 0) * 25
    return_pct = max(min(metrics.get("return_pct", 0) / 50, 1), 0) * 25
    win_rate = max(min(metrics.get("win_rate", 50) / 60, 1), 0) * 25
    mdd_score = max(min((50 - metrics.get("max_dd", 50)) / 40, 1), 0) * 25
    return sharpe + return_pct + win_rate + mdd_score


# ─── Generate equity_curves.ts ───────────────────────────────────────────────


def generate_equity_curves_ts(results: list) -> list:
    """Generate equity curve data points for charting."""
    curves = []
    for r in results:
        trade_log = r.get("trade_log", [])
        if not trade_log:
            continue
        pnls = [t["pnl"] for t in trade_log]
        equity = [1.0]
        for pnl in pnls:
            equity.append(equity[-1] * (1 + pnl))

        strategy = r.get("strategy", "unknown")
        tf = r.get("timeframe", "unknown")

        curves.append(
            {
                "id": f"eq_{strategy}_{tf}",
                "strategy": strategy,
                "timeframe": tf,
                "equity_curve": equity,
                "final_equity": equity[-1] if equity else 1.0,
                "n_trades": len(trade_log),
            }
        )
    return curves


# ─── Write TypeScript files ───────────────────────────────────────────────────


def write_ts_file(
    path: str, module_name: str, export_name: str, data: list | dict
) -> None:
    """Write a TypeScript data file."""
    content = (
        f"// Auto-generated by update_dashboard.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"// Do not edit manually\n\n"
        f"export const {export_name} = {json.dumps(data, indent=2)} as const;\n\n"
        f"export default {export_name};\n"
    )
    with open(path, "w") as f:
        f.write(content)
    print(f"[update_dashboard] Wrote {path}")


# ─── Update the backtests/page.tsx ────────────────────────────────────────────


def update_backtests_page_tsx(strategy_data: list) -> None:
    """Update the backtests/page.tsx to include new Jesse metrics columns."""
    page_path = os.path.join(DASHBOARD_DIR, "src/app/backtests/page.tsx")
    if not os.path.exists(page_path):
        print(f"[update_dashboard] backtests/page.tsx not found, skipping")
        return

    with open(page_path) as f:
        content = f.read()

    # Check if Jesse metrics section is already present
    if "calmar" not in content.lower():
        # Append new tab/section for Jesse metrics
        new_section = """

// ─── Jesse Extended Metrics ───────────────────────────────────────────────────
// The following interface extends the Strategy interface with Jesse-specific metrics.

export interface JesseMetrics {
  calmar: number;    // Annual return / Max drawdown
  kelly: number;      // Kelly criterion (% of capital to risk)
  mae: number;        // Mean Adverse Excursion (avg loss when losing)
  mfe: number;        // Mean Favorable Excursion (avg gain when winning)
  sortino: number;    // Sortino ratio
  jesse_sharpe: number;
  jesse_metrics: Record<string, number>;
}
"""
        # Find a good insertion point (before the first function)
        insert_pos = content.find("function ")
        if insert_pos != -1:
            content = content[:insert_pos] + new_section + "\n" + content[insert_pos:]

        with open(page_path, "w") as f:
            f.write(content)
        print(
            f"[update_dashboard] Updated backtests/page.tsx with Jesse metrics interfaces"
        )
    else:
        print(
            f"[update_dashboard] backtests/page.tsx already has Jesse metrics, skipping"
        )


# ─── Update SPEC.md if it exists ───────────────────────────────────────────────


def update_spec() -> None:
    """Update SPEC.md to document new features."""
    spec_path = os.path.join(DASHBOARD_DIR, "SPEC.md")
    if not os.path.exists(spec_path):
        return

    with open(spec_path) as f:
        spec = f.read()

    new_features = """
## Jesse Integration (v2)

### Added Features
- Monte Carlo simulation (1000+ paths, bootstrap method)
- Monthly returns heatmap
- Trade distribution histograms (PnL %)
- Enhanced risk metrics: Calmar, Kelly, MAE, MFE, Sortino
- Rolling Sharpe ratio chart
- Equity confidence bands (5th/25th/50th/75th/95th percentiles)
- Probability of ruin calculation

### Data Files (src/app/data/)
- `backtests.ts` — Aggregated best results per strategy/timeframe
- `monte_carlo.ts` — MC simulation results (percentiles, ruin probabilities)
- `risk_metrics.ts` — Per-strategy risk metrics
- `equity_curves.ts` — Equity curve data points

### Scripts
- `update_dashboard.py` — Regenerates all TypeScript data files from result JSONs
"""
    if "Jesse Integration" not in spec:
        spec += new_features
        with open(spec_path, "w") as f:
            f.write(spec)
        print(f"[update_dashboard] Updated SPEC.md")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    print("[update_dashboard] Starting dashboard update...")

    results = load_all_results()
    mc_results = load_mc_results()

    print(
        f"[update_dashboard] Loaded {len(results)} result files, {len(mc_results)} MC files"
    )

    # Generate TypeScript data
    strategy_data = generate_backtests_ts(results)
    mc_data = generate_mc_ts(mc_results)
    risk_data = generate_risk_metrics_ts(results)
    equity_curves = generate_equity_curves_ts(results)

    # Write TypeScript files
    write_ts_file(
        os.path.join(DASHBOARD_DATA, "backtests.ts"),
        "backtests",
        "BACKTEST_DATA",
        strategy_data,
    )
    write_ts_file(
        os.path.join(DASHBOARD_DATA, "monte_carlo.ts"),
        "monte_carlo",
        "MC_DATA",
        mc_data,
    )
    write_ts_file(
        os.path.join(DASHBOARD_DATA, "risk_metrics.ts"),
        "risk_metrics",
        "RISK_METRICS",
        risk_data,
    )
    write_ts_file(
        os.path.join(DASHBOARD_DATA, "equity_curves.ts"),
        "equity_curves",
        "EQUITY_CURVES",
        equity_curves,
    )

    # Update page.tsx
    update_backtests_page_tsx(strategy_data)

    # Update SPEC.md
    update_spec()

    # Summary
    print(f"\n[update_dashboard] === Summary ===")
    print(f"  Strategies:     {len(strategy_data)}")
    print(f"  MC results:     {len(mc_data)}")
    print(f"  Risk metrics:   {len(risk_data)}")
    print(f"  Equity curves:  {len(equity_curves)}")
    print(f"\n[update_dashboard] Done ✓")


if __name__ == "__main__":
    main()
