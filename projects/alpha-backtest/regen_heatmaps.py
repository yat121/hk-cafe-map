#!/usr/bin/env python3
"""Regenerate missing heatmaps (no hidden_divergence)."""

import json, os, sys, warnings

warnings.filterwarnings("ignore")

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
sys.path.insert(0, WORK_DIR)
PLOTS_DIR = os.path.join(WORK_DIR, "plots")

MISSING = [
    ("swing_sniper", "1H"),
    ("overextended_reversal", "1D"),
    ("overextended_reversal", "1H"),
    ("overextended_reversal", "4H"),
    ("bb_headfake", "4H"),
]

from alpha_backtester import get_btc_data, run_strategy

# Pre-cache data
cache = {}
for tf in set(tf for _, tf in MISSING):
    df = get_btc_data(tf)
    cache[tf] = df.dropna() if df is not None else None
import alpha_backtester as ab

ab.get_btc_data = lambda t: cache.get(t)

for strat, tf in MISSING:
    print(f"Regenerating heatmap for {strat}_{tf}...")
    result = run_strategy(strat, tf, max_combos=200)
    if result:
        print(f"  ✅ Done")
    else:
        print(f"  ⚠ Failed")
