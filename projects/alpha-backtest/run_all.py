#!/usr/bin/env python3
"""
All 11 strategies backtest — BTC/USDT 5 years
Fee: 0.045% per side | Min 20 trades/year
"""

import json, os, sys, math, glob, time
from datetime import datetime, timedelta, timezone
import numpy as np

HAS_CCXT = False
try:
    import ccxt

    HAS_CCXT = True
except:
    pass

DATA_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest/data"
OUT_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest/results"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

FEE = 0.00045  # 0.045%


# ── Load or fetch data ──────────────────────────────────────────────────────
def load_ohlcv(tf="1h", months=60):
    path = f"{DATA_DIR}/BTC_USDT_{tf.replace('/','_')}.json"
    if os.path.exists(path) and os.path.getsize(path) > 50000:
        with open(path) as f:
            d = json.load(f)
            print(f"  {tf}: loaded {len(d)} candles from cache")
            return d
    if not HAS_CCXT:
        print(f"  {tf}: ERROR — no cache and ccxt not available")
        return []
    exchange = ccxt.binance({"enableRateLimit": True})
    since = exchange.parse8601(
        (datetime.now(timezone.utc) - timedelta(days=months * 30)).isoformat()
    )
    print(f"  {tf}: fetching {months} months in batches...")
    try:
        all_data = []
        current_since = since
        for batch in range(10):  # fetch up to 10 batches
            batch_data = exchange.fetch_ohlcv(
                "BTC/USDT:USDT", tf, since=current_since, limit=1000
            )
            if not batch_data or len(batch_data) == 0:
                break
            all_data.extend(batch_data)
            current_since = batch_data[-1][0] + 1
            if len(batch_data) < 1000:
                break
            print(
                f"  {tf}: batch {batch+1} got {len(batch_data)} candles, total={len(all_data)}"
            )
            import time

            time.sleep(0.5)
        with open(path, "w") as f:
            json.dump(all_data, f)
        print(f"  {tf}: saved {len(all_data)} candles total")
        return all_data
    except Exception as e:
        print(f"  {tf}: fetch error — {e}")
        return []


# ── Core backtest ────────────────────────────────────────────────────────────
def backtest(closes, longs, shorts):
    if not longs or not shorts:
        return []
    all_signals = sorted(
        [(i, 1) for i in longs] + [(i, -1) for i in shorts], key=lambda x: x[0]
    )
    trades = []
    pos = 0
    entry_idx = 0
    entry_px = 0
    for idx, side in all_signals:
        if pos == 0:
            pos = side
            entry_idx = idx
            entry_px = closes[idx]
        elif side != pos:
            exit_px = closes[idx]
            pnl = pos * (exit_px / entry_px - 1) - FEE * 2
            trades.append(
                {"entry_idx": entry_idx, "exit_idx": idx, "side": pos, "pnl": pnl}
            )
            pos = side
            entry_idx = idx
            entry_px = exit_px
    return trades


def calc_metrics(trades, years=5):
    if not trades:
        return None
    pnls = np.array([t["pnl"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    total = float(np.sum(pnls))
    n = len(pnls)
    ann_trades = n / years
    sharpe = 0.0
    if np.std(pnls) > 1e-10:
        sharpe = float((np.mean(pnls) / np.std(pnls)) * math.sqrt(ann_trades))
    mdd = 0.0
    cum = 1.0
    peak = 1.0
    for p in pnls:
        cum *= 1 + p
        peak = max(peak, cum)
        mdd = max(mdd, (peak - cum) / peak)
    return {
        "total_return": round(total * 100, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(mdd * 100, 1),
        "win_rate": round(len(wins) / n * 100, 1) if n > 0 else 0,
        "profit_factor": (
            round(float(abs(np.sum(wins)) / abs(np.sum(losses))), 2)
            if len(losses) > 0 and np.sum(losses) != 0
            else 999
        ),
        "total_trades": n,
        "ann_trades": round(ann_trades, 1),
    }


def rsi(closes, period=14):
    deltas = (
        np.diff(closes, axis=0) if len(np.array(closes).shape) > 1 else np.diff(closes)
    )
    if len(deltas) == 0:
        return np.array([50.0])
    gains = np.maximum(deltas, 0)
    losses = np.maximum(-deltas, 0)
    avg_g = np.convolve(gains, np.ones(period) / period, mode="full")[: len(gains)]
    avg_l = np.convolve(losses, np.ones(period) / period, mode="full")[: len(losses)]
    rs = avg_g / (avg_l + 1e-10)
    vals = 100 - (100 / (1 + rs))
    return np.concatenate([np.full(period, 50.0), vals])


def ema(closes, period):
    k = 2.0 / (period + 1)
    ema_vals = [float(closes[0])]
    for price in closes[1:]:
        ema_vals.append(float(price) * k + ema_vals[-1] * (1 - k))
    return np.array(ema_vals)


def donchian(closes, period):
    highs = []
    lows = []
    for i in range(period - 1, len(closes)):
        highs.append(max(closes[i - period + 1 : i + 1]))
        lows.append(min(closes[i - period + 1 : i + 1]))
    return np.array(highs), np.array(lows)


def bollinger(closes, period=20, std_mult=2.0):
    mid = np.convolve(closes, np.ones(period) / period, mode="valid")
    std_arr = np.array([np.std(closes[i : i + period]) for i in range(len(mid))])
    return mid + std_mult * std_arr, mid - std_mult * std_arr


def run_strategy(name, tf, closes, longs_fn, shorts_fn, param_grid):
    print(f"\n=== {name} ({tf}) ===")
    results = []
    for params in param_grid:
        longs = longs_fn(closes, **params)
        shorts = shorts_fn(closes, **params)
        trades = backtest(closes, longs, shorts)
        m = calc_metrics(trades)
        if m and m["ann_trades"] >= 20:
            m["params"] = params
            results.append(m)
    if not results:
        print(f"  No valid results (min trades not met)")
        return None
    results.sort(key=lambda x: x["sharpe"], reverse=True)
    best = results[0]
    print(
        f"  Best: Sharpe={best['sharpe']} Return={best['total_return']}% MDD={best['max_drawdown']}% Trades={best['total_trades']}"
    )
    print(f"  Params: {best['params']}")
    with open(f"{OUT_DIR}/{name}_{tf}.json", "w") as f:
        json.dump({"all": results, "best": results[:5]}, f, indent=2)
    return results


# ── Load data ────────────────────────────────────────────────────────────────
print("Loading BTC/USDT data (5 years)...")
data_1h = load_ohlcv(tf="1h", months=60)
data_4h = load_ohlcv(tf="4h", months=60)
data_1d = load_ohlcv(tf="1d", months=60)

closes_1h = np.array([c[4] for c in data_1h]) if data_1h else np.array([])
closes_4h = np.array([c[4] for c in data_4h]) if data_4h else np.array([])
closes_1d = np.array([c[4] for c in data_1d]) if data_1d else np.array([])

for tf, n in [("1h", len(closes_1h)), ("4h", len(closes_4h)), ("1d", len(closes_1d))]:
    print(f"  {tf}: {n} candles loaded")


# ── Strategy 1: Momentum Flip (1H) ─────────────────────────────────────────
def s1_long(closes, rsi_period, buffer):
    r = rsi(closes, rsi_period)
    return [
        i
        for i in range(rsi_period + 1, len(closes) - 1)
        if r[i - 1] < 50 - buffer and r[i] >= 50
    ]


def s1_short(closes, rsi_period, buffer):
    r = rsi(closes, rsi_period)
    return [
        i
        for i in range(rsi_period + 1, len(closes) - 1)
        if r[i - 1] > 50 + buffer and r[i] <= 50
    ]


run_strategy(
    "momentum_flip",
    "1h",
    closes_1h,
    s1_long,
    s1_short,
    [{"rsi_period": rp, "buffer": buf} for rp in [10, 14, 20] for buf in [2, 3, 5]],
)


# ── Strategy 2: Overextended Reversal (4H) ──────────────────────────────────
def s2_long(closes, rsi_period, lower, upper, confirm):
    r = rsi(closes, rsi_period)
    return [
        i
        for i in range(rsi_period + 1, len(closes) - 1)
        if r[i - 1] < lower and r[i] >= confirm
    ]


def s2_short(closes, rsi_period, lower, upper, confirm):
    r = rsi(closes, rsi_period)
    return [
        i
        for i in range(rsi_period + 1, len(closes) - 1)
        if r[i - 1] > upper and r[i] <= confirm
    ]


run_strategy(
    "overextended_reversal",
    "4h",
    closes_4h,
    s2_long,
    s2_short,
    [
        {"rsi_period": rp, "lower": lo, "upper": 100 - lo, "confirm": (lo + 30) // 2}
        for rp in [7, 14, 21]
        for lo in [15, 20, 25]
    ],
)


# ── Strategy 3: Trend Follower EMA Cross (4H) ──────────────────────────────
def s3_long(closes, fast, slow):
    ef = ema(closes, fast)
    es = ema(closes, slow)
    return [
        i
        for i in range(slow + 1, len(closes) - 1)
        if ef[i - 1] < es[i - 1] and ef[i] >= es[i]
    ]


def s3_short(closes, fast, slow):
    ef = ema(closes, fast)
    es = ema(closes, slow)
    return [
        i
        for i in range(slow + 1, len(closes) - 1)
        if ef[i - 1] > es[i - 1] and ef[i] <= es[i]
    ]


run_strategy(
    "trend_follower",
    "4h",
    closes_4h,
    s3_long,
    s3_short,
    [{"fast": f, "slow": s} for f in [10, 20, 30] for s in [50, 80, 100] if f < s],
)


# ── Strategy 4: Donchian Turtle (4H) ───────────────────────────────────────
def s4_long(closes, period):
    h, l = donchian(closes, period)
    off = period - 1
    return [
        i + off
        for i in range(period, len(h))
        if closes[i + off] > h[i] and (i == 0 or closes[i + off - 1] <= h[i - 1])
    ]


def s4_short(closes, period):
    h, l = donchian(closes, period)
    off = period - 1
    return [
        i + off
        for i in range(period, len(l))
        if closes[i + off] < l[i] and (i == 0 or closes[i + off - 1] >= l[i - 1])
    ]


run_strategy(
    "donchian_turtle",
    "4h",
    closes_4h,
    s4_long,
    s4_short,
    [{"period": p} for p in [15, 20, 25]],
)


# ── Strategy 5: Bollinger Band Head Fake (1H) ──────────────────────────────
def s5_long(closes, bb_period, std_mult):
    if len(closes) < bb_period + 2:
        return []
    r = rsi(closes, 14)
    upper, lower = bollinger(closes, bb_period, std_mult)
    longs, shorts = [], []
    in_pos = 0
    for i in range(bb_period + 1, len(closes) - 1):
        prev_outside = closes[i - 1] > upper[i - 2] if i >= 2 else False
        prev_under = closes[i - 1] < lower[i - 2] if i >= 2 else False
        curr_inside = lower[i - 1] <= closes[i] <= upper[i - 1] if i >= 1 else False
        if in_pos == 0 and prev_under and curr_inside and r[i] < 30:
            longs.append(i)
            in_pos = 1
        elif in_pos == 1 and r[i] >= 50:
            in_pos = 0
        if in_pos == 0 and prev_outside and curr_inside and r[i] > 70:
            shorts.append(i)
            in_pos = -1
        elif in_pos == -1 and r[i] <= 50:
            in_pos = 0
    return longs


def s5_short(closes, bb_period, std_mult):
    return s5_long(closes, bb_period, std_mult)  # same fn, uses in_pos logic


# Simpler: separate long/short
def s5_long_real(closes, bb_period, std_mult):
    if len(closes) < bb_period + 2:
        return []
    r = rsi(closes, 14)
    upper, lower = bollinger(closes, bb_period, std_mult)
    bb_len = len(upper)  # = len(closes) - bb_period + 1
    longs = []
    in_pos = 0
    for i in range(bb_period + 1, bb_len):
        # i in closes space; j in BB array space = i - (bb_period-1)
        j = i - (bb_period - 1)
        prev_under = closes[i - 1] < lower[j - 1] if j >= 1 else False
        curr_inside = lower[j] <= closes[i] <= upper[j]
        if in_pos == 0 and prev_under and curr_inside and r[i] < 30:
            longs.append(i)
            in_pos = 1
        elif in_pos == 1 and r[i] >= 50:
            in_pos = 0
    return longs


def s5_short_real(closes, bb_period, std_mult):
    if len(closes) < bb_period + 2:
        return []
    r = rsi(closes, 14)
    upper, lower = bollinger(closes, bb_period, std_mult)
    bb_len = len(upper)
    shorts = []
    in_pos = 0
    for i in range(bb_period + 1, bb_len):
        j = i - (bb_period - 1)
        prev_outside = closes[i - 1] > upper[j - 1] if j >= 1 else False
        curr_inside = lower[j] <= closes[i] <= upper[j]
        if in_pos == 0 and prev_outside and curr_inside and r[i] > 70:
            shorts.append(i)
            in_pos = -1
        elif in_pos == -1 and r[i] <= 50:
            in_pos = 0
    return shorts


run_strategy(
    "bb_headfake",
    "1h",
    closes_1h,
    s5_long_real,
    s5_short_real,
    [{"bb_period": p, "std_mult": s} for p in [15, 20, 25] for s in [1.5, 2.0, 2.5]],
)

# ── More strategies on different timeframes ─────────────────────────────────
run_strategy(
    "momentum_flip",
    "4h",
    closes_4h,
    s1_long,
    s1_short,
    [{"rsi_period": rp, "buffer": buf} for rp in [10, 14, 20] for buf in [2, 3, 5]],
)

run_strategy(
    "momentum_flip",
    "1d",
    closes_1d,
    s1_long,
    s1_short,
    [{"rsi_period": rp, "buffer": buf} for rp in [10, 14, 20] for buf in [2, 3, 5]],
)

run_strategy(
    "trend_follower",
    "1d",
    closes_1d,
    s3_long,
    s3_short,
    [{"fast": f, "slow": s} for f in [10, 20, 30] for s in [50, 100, 200] if f < s],
)

run_strategy(
    "overextended_reversal",
    "1d",
    closes_1d,
    s2_long,
    s2_short,
    [
        {"rsi_period": rp, "lower": lo, "upper": 100 - lo, "confirm": (lo + 30) // 2}
        for rp in [7, 14, 21]
        for lo in [15, 20, 25]
    ],
)

run_strategy(
    "donchian_turtle",
    "1d",
    closes_1d,
    s4_long,
    s4_short,
    [{"period": p} for p in [15, 20, 25]],
)

run_strategy(
    "bb_headfake",
    "4h",
    closes_4h,
    s5_long_real,
    s5_short_real,
    [{"bb_period": p, "std_mult": s} for p in [15, 20, 25] for s in [1.5, 2.0, 2.5]],
)

# ── Compile final summary ─────────────────────────────────────────────────────
print("\n\n" + "=" * 70)
print("FINAL SUMMARY — All Strategies Ranked by Sharpe Ratio")
print("=" * 70)
summary = []
for fpath in sorted(glob.glob(f"{OUT_DIR}/*.json")):
    name = os.path.basename(fpath).replace(".json", "")
    try:
        with open(fpath) as f:
            data = json.load(f)
        best = (data.get("best") or data.get("all") or [{}])[0]
        if best:
            summary.append(
                {
                    "strategy": name,
                    "sharpe": best.get("sharpe", 0),
                    "return": best.get("total_return", 0),
                    "mdd": best.get("max_drawdown", 0),
                    "win_rate": best.get("win_rate", 0),
                    "trades": best.get("total_trades", 0),
                    "ann_trades": best.get("ann_trades", 0),
                    "pf": best.get("profit_factor", 0),
                    "params": best.get("params", {}),
                }
            )
    except Exception as e:
        print(f"  Error reading {fpath}: {e}")

summary.sort(key=lambda x: x["sharpe"], reverse=True)
print(
    f"\n{'Rank':<5} {'Strategy':<35} {'Sharpe':>7} {'Return':>8} {'MDD':>6} {'WR':>5} {'Trades':>7} {'Ann/yr':>7}"
)
print("-" * 90)
for i, s in enumerate(summary, 1):
    print(
        f"{i:<5} {s['strategy']:<35} {s['sharpe']:>7.3f} {s['return']:>7.1f}% {s['mdd']:>5.1f}% {s['win_rate']:>5.1f}% {s['trades']:>7} {s['ann_trades']:>7.1f}"
    )

with open(f"{OUT_DIR}/FINAL_SUMMARY.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n✅ Saved {len(summary)} strategy results to {OUT_DIR}/")
print(f"   FINAL_SUMMARY.json = ranked by Sharpe")
