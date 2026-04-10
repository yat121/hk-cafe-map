#!/usr/bin/env python3
"""Fast runner - max 200 combos per strategy for speed."""

import json, os, sys, time, warnings

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
sys.path.insert(0, WORK_DIR)


# Detect already-done combos
def done(strat, tf):
    return os.path.exists(os.path.join(WORK_DIR, "results", f"{strat}_{tf}_best.json"))


TO_RUN = []
for strat, tfs in [
    ("overextended_reversal", ["1H", "4H", "1D"]),
    ("hidden_divergence", ["1H", "4H", "1D"]),
    ("equal_highs_liquidity_grab", ["1H", "4H"]),
    ("bb_headfake", ["4H"]),
    ("2b_reversal", ["1H", "4H"]),
    ("previous_day_sweep", ["1H", "4H"]),
]:
    for tf in tfs:
        if not done(strat, tf):
            TO_RUN.append((strat, tf))

print(f"Combos to run: {len(TO_RUN)}")

import alpha_backtester as ab
import pandas as pd

# Pre-fetch all needed timeframes
needed_tfs = list({tf for _, tf in TO_RUN})
cache = {}
for t in needed_tfs:
    df = ab.get_btc_data(t)
    if df is not None:
        df = df.dropna()
    cache[t] = df
    print(f"  {t}: {len(df) if df is not None else 0} candles")

# Override get_btc_data to use cache
ab.get_btc_data = lambda t: cache.get(t)

summary_updates = []

for strat, tf in TO_RUN:
    t0 = time.time()
    print(f"\n{'='*50} {strat.upper()} | {tf}", flush=True)
    result = ab.run_strategy(strat, tf, max_combos=200)
    elapsed = time.time() - t0
    if result:
        m = result["metrics"]
        summary_updates.append(
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
            f"  ✅ {elapsed:.0f}s | Sharpe:{m['sharpe']:.3f} MDD:{m['max_dd']:.1f}% WR:{m['win_rate']:.1f}% Trades:{m['total_trades']}"
        )
    else:
        print(f"  ⚠  No result after {elapsed:.0f}s")

# Update FINAL_SUMMARY
sf = os.path.join(WORK_DIR, "results", "FINAL_SUMMARY.json")
existing = json.load(open(sf)) if os.path.exists(sf) else []
seen = {s["strategy"]: s for s in existing}
for s in summary_updates:
    seen[s["strategy"]] = s
final = sorted(seen.values(), key=lambda x: x.get("sharpe", 0), reverse=True)
with open(sf, "w") as f:
    json.dump(final, f, indent=2)

print(f"\n{'='*60}")
print("FINAL SUMMARY")
print(f"{'='*60}")
print(f"{'Strategy':<40} {'Sharpe':>7} {'MDD%':>6} {'WR%':>5} {'Trades':>6}")
for s in final:
    print(
        f"{s['strategy']:<40} {s['sharpe']:>7.3f} {s['mdd']:>6.1f} {s['win_rate']:>5.1f} {s['trades']:>6}"
    )
