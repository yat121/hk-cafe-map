#!/usr/bin/env python3
"""
Run all 11 strategies across all 3 timeframes.
Skips combos already in results/.
"""

import json, os, sys, time
from datetime import datetime

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
sys.path.insert(0, WORK_DIR)

# Already-done combos (from FINAL_SUMMARY + bb_headfake_1h + trend_follower_4h)
DONE = set()
r = json.load(open(os.path.join(WORK_DIR, "results", "FINAL_SUMMARY.json")))
for x in r:
    DONE.add(x["strategy"])
for f in os.listdir(os.path.join(WORK_DIR, "results")):
    if f.endswith("_best.json"):
        parts = f.replace("_best.json", "").rsplit("_", 1)
        if len(parts) == 2:
            DONE.add(f"{parts[0]}_{parts[1]}")

# All strategies + required timeframes
# Format: (strategy_name, [timeframes])
ALL_COMBOS = [
    # Already done (reference only):
    # momentum_flip_1h, momentum_flip_4h, momentum_flip_30m,
    # bb_headfake_1h, trend_follower_4h, momentum_flip_1d
    # ── NEW COMBOS TO RUN ──
    ("day_driver", ["1H", "4H", "1D"]),
    ("swing_sniper", ["1H", "4H", "1D"]),
    ("institutional_macro", ["1H", "4H", "1D"]),
    ("momentum_flip", ["1D"]),  # 1H,4H done
    ("overextended_reversal", ["1H", "4H", "1D"]),
    ("hidden_divergence", ["1H", "4H", "1D"]),
    ("previous_day_sweep", ["1H", "4H", "1D"]),
    ("2b_reversal", ["1H", "4H", "1D"]),
    ("bb_headfake", ["4H", "1D"]),  # 1H done
    ("equal_highs_liquidity_grab", ["1H", "4H", "1D"]),
    ("trend_follower", ["1H", "1D"]),  # 4H done
]


def already_done(strategy, tf):
    key = f"{strategy}_{tf}"
    path = os.path.join(WORK_DIR, "results", f"{strategy}_{tf}_best.json")
    return os.path.exists(path)


# Import the backtester
from alpha_backtester import run_strategy, RESULTS_DIR, get_btc_data


def main():
    from alpha_backtester import run_strategy

    total = 0
    to_run = []
    for strat, tfs in ALL_COMBOS:
        for tf in tfs:
            if already_done(strat, tf):
                print(f"⏭  SKIP  {strat}_{tf} (already done)")
            else:
                to_run.append((strat, tf))
                total += 1

    print(f"\n{'='*60}")
    print(f"  Total combos to run: {total}")
    print(f"{'='*60}\n")

    if not to_run:
        print("All done!")
        return

    # Pre-fetch data for each timeframe (download once)
    data_cache = {}
    for tf in set(t[1] for t in to_run):
        print(f"Fetching data for {tf}...")
        import pandas as pd
        from alpha_backtester import get_btc_data

        df = get_btc_data(tf)
        if df is not None:
            df = df.dropna()
        data_cache[tf] = df
        print(f"  {tf}: {len(df) if df is not None else 0} candles")

    # Inject cached data to avoid re-downloading
    import alpha_backtester as ab

    orig_get = ab.get_btc_data

    def cached_get(tf):
        return data_cache.get(tf)

    ab.get_btc_data = cached_get

    summary = []
    for strat, tf in to_run:
        print(f"\n{'='*60}")
        print(f"  Running: {strat.upper()} | {tf}")
        print(f"{'='*60}")
        t0 = time.time()
        result = run_strategy(strat, tf)
        elapsed = time.time() - t0
        if result:
            m = result["metrics"]
            summary.append(
                {
                    "strategy": f"{strat}_{tf}",
                    "sharpe": m["sharpe"],
                    "sortino": m["sortino"],
                    "mdd": m["max_dd"],
                    "win_rate": m["win_rate"],
                    "trades": m["total_trades"],
                    "return_pct": m["return_pct"],
                    "pf": m["profit_factor"],
                    "params": result["best_params"],
                }
            )
            print(
                f"\n  ⏱  {elapsed:.0f}s | Sharpe: {m['sharpe']:.3f} | MDD: {m['max_dd']:.1f}% | WR: {m['win_rate']:.1f}%"
            )
        else:
            print(f"  ⚠ No result for {strat}_{tf}")

    # Update FINAL_SUMMARY
    summary_path = os.path.join(WORK_DIR, "results", "FINAL_SUMMARY.json")
    existing = []
    if os.path.exists(summary_path):
        existing = json.load(open(summary_path))

    # Deduplicate by strategy name (keep newest)
    seen = {}
    for s in existing:
        seen[s["strategy"]] = s
    for s in summary:
        seen[s["strategy"]] = s

    final = sorted(seen.values(), key=lambda x: x["sharpe"], reverse=True)
    with open(summary_path, "w") as f:
        json.dump(final, f, indent=2)

    print(f"\n\n{'='*60}")
    print("  FINAL SUMMARY")
    print(f"{'='*60}")
    print(
        f"{'Strategy':<35} {'Sharpe':>7} {'Sortino':>8} {'MDD%':>6} {'WR%':>5} {'Trades':>6}"
    )
    print("-" * 70)
    for s in final:
        print(
            f"{s['strategy']:<35} {s['sharpe']:>7.3f} {s['sortino']:>8.3f} {s['mdd']:>6.1f} {s['win_rate']:>5.1f} {s['trades']:>6}"
        )
    print(f"\nSaved to {summary_path}")


if __name__ == "__main__":
    main()
