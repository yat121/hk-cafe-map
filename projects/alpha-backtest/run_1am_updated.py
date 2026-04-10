#!/usr/bin/env python3
"""
Updated backtest — All 11 strategies with Desmond's custom definitions
Fee: 0.045% per side | Min 20 trades/year | 5 years BTC/USDT
"""

import json, os, math, glob, time
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
FEE = 0.00045


# ── Helpers ──────────────────────────────────────────────────────────────────
def load_ohlcv(tf="1h", months=60):
    path = f"{DATA_DIR}/BTC_USDT_{tf.replace('/','_')}.json"
    if os.path.exists(path) and os.path.getsize(path) > 50000:
        with open(path) as f:
            d = json.load(f)
            print(f"  {tf}: {len(d)} candles cached")
            return d
    if not HAS_CCXT:
        print(f"  {tf}: ERROR — no data and ccxt unavailable")
        return []
    exchange = ccxt.binance({"enableRateLimit": True})
    since = exchange.parse8601(
        (datetime.now(timezone.utc) - timedelta(days=months * 30)).isoformat()
    )
    all_data, current_since = [], since
    for batch in range(50):
        batch_data = exchange.fetch_ohlcv(
            "BTC/USDT:USDT", tf, since=current_since, limit=1000
        )
        if not batch_data:
            break
        all_data.extend(batch_data)
        current_since = batch_data[-1][0] + 1
        if len(batch_data) < 1000:
            break
        time.sleep(0.3)
    with open(path, "w") as f:
        json.dump(all_data, f)
    print(f"  {tf}: {len(all_data)} candles saved")
    return all_data


def backtest(closes, longs, shorts):
    if not longs or not shorts:
        return []
    all_s = sorted(
        [(i, 1) for i in longs] + [(i, -1) for i in shorts], key=lambda x: x[0]
    )
    trades, pos, entry_px = [], 0, 0
    for idx, side in all_s:
        if pos == 0:
            pos, entry_px = side, closes[idx]
        elif side != pos:
            pnl = pos * (closes[idx] / entry_px - 1) - FEE * 2
            trades.append({"side": pos, "pnl": pnl})
            pos, entry_px = side, closes[idx]
    return trades


def metrics(trades, years=5):
    if not trades:
        return None
    pnls = np.array([t["pnl"] for t in trades])
    wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
    total = float(np.sum(pnls))
    n = len(pnls)
    ann = n / years
    sharpe = (
        float((np.mean(pnls) / np.std(pnls)) * math.sqrt(ann))
        if np.std(pnls) > 1e-10
        else 0.0
    )
    mdd, cum, peak = 0.0, 1.0, 1.0
    for p in pnls:
        cum *= 1 + p
        peak = max(peak, cum)
        mdd = max(mdd, (peak - cum) / peak)
    return {
        "total_return": round(total * 100, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(mdd * 100, 1),
        "win_rate": round(len(wins) / n * 100, 1),
        "profit_factor": (
            round(abs(np.sum(wins) / abs(np.sum(losses))), 2)
            if len(losses) > 0 and np.sum(losses) != 0
            else 999
        ),
        "total_trades": n,
        "ann_trades": round(ann, 1),
    }


def rsi(closes, period=14):
    deltas = np.diff(closes)
    gains = np.maximum(deltas, 0)
    losses = np.maximum(-deltas, 0)
    ag = np.convolve(gains, np.ones(period) / period, mode="full")[: len(gains)]
    al = np.convolve(losses, np.ones(period) / period, mode="full")[: len(gains)]
    rs = ag / (al + 1e-10)
    vals = 100 - (100 / (1 + rs))
    return np.concatenate([np.full(period, 50.0), vals])


def ema_arr(closes, period):
    k = 2.0 / (period + 1)
    ev = [float(closes[0])]
    for p in closes[1:]:
        ev.append(p * k + ev[-1] * (1 - k))
    return np.array(ev)


def bollinger(closes, period=20, std_mult=2.0):
    mid = np.convolve(closes, np.ones(period) / period, mode="valid")
    std_arr = np.array([np.std(closes[i : i + period]) for i in range(len(mid))])
    return mid + std_mult * std_arr, mid - std_mult * std_arr


def supertrend(highs, lows, closes, period=10, mult=3.0):
    """Returns 1=green(up), -1=red(down)"""
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.abs(highs[1:] - closes[:-1]),
        np.abs(lows[1:] - closes[:-1]),
    )
    atr = np.convolve(tr, np.ones(period) / period, mode="full")[: len(tr)]
    hl2 = (highs[1:] + lows[1:]) / 2
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    direction = np.ones(len(closes))
    trend = np.ones(len(closes))
    for i in range(1, len(closes)):
        if closes[i] > upper[i - 1]:
            trend[i] = 1
        elif closes[i] < lower[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]
        direction[i] = trend[i]
    return direction  # 1=up, -1=down


def macd(closes, fast=12, slow=26, signal=9):
    ef = ema_arr(closes, fast)
    es = ema_arr(closes, slow)
    macd_line = ef - es
    sig = ema_arr(macd_line, signal)
    return macd_line, sig, macd_line - sig  # macd, signal, histogram


def vol_ma(volumes, period=20):
    return np.convolve(volumes, np.ones(period) / period, mode="valid")


def donch(closes, period):
    h, l = [], []
    for i in range(period - 1, len(closes)):
        h.append(max(closes[i - period + 1 : i + 1]))
        l.append(min(closes[i - period + 1 : i + 1]))
    return np.array(h), np.array(l)


def run(name, tf, closes, grid, long_fn, short_fn):
    print(f"\n=== {name} ({tf}) ===")
    results = []
    for params in grid:
        try:
            longs = long_fn(closes, **params)
            shorts = short_fn(closes, **params)
            trades = backtest(closes, longs, shorts)
            m = metrics(trades)
            if m and m["ann_trades"] >= 20:
                m["params"] = params
                results.append(m)
        except Exception as e:
            print(f"  Error {params}: {e}")
    if not results:
        print(f"  No valid results")
        return
    results.sort(key=lambda x: x["sharpe"], reverse=True)
    b = results[0]
    print(
        f"  Best: Sharpe={b['sharpe']} Return={b['total_return']}% MDD={b['max_drawdown']}% Trades={b['total_trades']} | {b['params']}"
    )
    with open(f"{OUT_DIR}/{name}_{tf}.json", "w") as f:
        json.dump({"all": results, "best": results[:5]}, f, indent=2)


# ── Load data ────────────────────────────────────────────────────────────────
print("Loading BTC/USDT 5-year data...")
closes_1h = (
    np.array([c[4] for c in load_ohlcv("1h")]) if load_ohlcv("1h") else np.array([])
)
closes_4h = (
    np.array([c[4] for c in load_ohlcv("4h")]) if load_ohlcv("4h") else np.array([])
)
closes_1d = (
    np.array([c[4] for c in load_ohlcv("1d")]) if load_ohlcv("1d") else np.array([])
)


# Also load highs/lows/volumes for indicators
def load_hlcv(tf):
    path = f"{DATA_DIR}/BTC_USDT_{tf.replace('/','_')}.json"
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        highs = np.array([c[2] for c in data])
        lows = np.array([c[3] for c in data])
        vols = np.array([c[5] for c in data])
        print(f"  {tf}: HLCV loaded ({len(data)} candles)")
        return highs, lows, vols
    return np.array([]), np.array([]), np.array([])


print("Loading HLCV data...")
h_1h, l_1h, v_1h = load_hlcv("1h")
h_4h, l_4h, v_4h = load_hlcv("4h")
h_1d, l_1d, v_1d = load_hlcv("1d")

# ── DESMOND'S 4 CUSTOM STRATEGIES ───────────────────────────────────────────


# 1. DAY DRIVER LONG: price <= lower_bb AND RSI < 30 AND price > EMA200 → LONG
def day_driver_long(closes, bb_p, bb_std, ema200_p):
    upper, lower = bollinger(closes, bb_p, bb_std)
    r = rsi(closes, 14)
    ema200 = ema_arr(closes, ema200_p)
    longs = []
    for i in range(bb_p + 1, len(closes) - 1):
        off = i - (bb_p - 1)  # BB array offset
        if off < 0 or off >= len(lower):
            continue
        if closes[i] <= lower[off] and r[i] < 30 and closes[i] > ema200[i]:
            longs.append(i)
    return longs


def day_driver_short(closes, bb_p, bb_std, ema200_p):
    upper, lower = bollinger(closes, bb_p, bb_std)
    r = rsi(closes, 14)
    ema200 = ema_arr(closes, ema200_p)
    shorts = []
    for i in range(bb_p + 1, len(closes) - 1):
        off = i - (bb_p - 1)
        if off < 0 or off >= len(upper):
            continue
        if closes[i] >= upper[off] and r[i] > 70 and closes[i] < ema200[i]:
            shorts.append(i)
    return shorts


# 2. SWING SNIPER SHORT: BB squeeze AND price_close < lower_bb AND volume > vol_ma * 1.2
def bb_squeeze(closes, bb_p=20, threshold=0.5):
    upper, lower = bollinger(closes, bb_p, 2.0)
    width = upper - lower
    avg_width = np.mean(width[-20:])
    return width < avg_width * threshold


def swing_sniper_long(closes, bb_p, vol_ma_p):
    upper, lower = bollinger(closes, bb_p, 2.0)
    r = rsi(closes, 14)
    squeeze = bb_squeeze(closes, bb_p)
    vol_ma_vals = vol_ma(
        v_1h if len(closes) == len(v_1h) else np.full(len(closes), 1), vol_ma_p
    )
    longs = []
    for i in range(bb_p + 1, len(closes) - 1):
        off = i - (bb_p - 1)
        if off < 0 or off >= len(lower):
            continue
        vi = min(i, len(vol_ma_vals) - 1)
        if (
            squeeze[i]
            and closes[i] >= upper[off]
            and r[i] > 70
            and v_1h[i] > vol_ma_vals[vi] * 1.2
        ):
            longs.append(i)
    return longs


def swing_sniper_short(closes, bb_p, vol_ma_p):
    upper, lower = bollinger(closes, bb_p, 2.0)
    r = rsi(closes, 14)
    squeeze = bb_squeeze(closes, bb_p)
    vol_ma_vals = vol_ma(
        v_1h if len(closes) == len(v_1h) else np.full(len(closes), 1), vol_ma_p
    )
    shorts = []
    for i in range(bb_p + 1, len(closes) - 1):
        off = i - (bb_p - 1)
        if off < 0 or off >= len(lower):
            continue
        vi = min(i, len(vol_ma_vals) - 1)
        if (
            squeeze[i]
            and closes[i] <= lower[off]
            and r[i] < 30
            and v_1h[i] > vol_ma_vals[vi] * 1.2
        ):
            shorts.append(i)
    return shorts


# 3. TREND FOLLOWER LONG: supertrend = 'green' (up) AND MACD histogram > 0
def trend_follower_long(closes, st_p, st_mult, ema200_p):
    highs = (
        np.array(
            [
                c[2]
                for c in (
                    [(closes[i], closes[i], closes[i]) for i in range(len(closes))]
                )
            ]
        )
        if len(closes) < 1000
        else h_1h[: len(closes)]
    )
    lows = (
        np.array(
            [
                c[3]
                for c in (
                    [(closes[i], closes[i], closes[i]) for i in range(len(closes))]
                )
            ]
        )
        if len(closes) < 1000
        else l_1h[: len(closes)]
    )
    st = supertrend(h_1h[: len(closes)], l_1h[: len(closes)], closes, st_p, st_mult)
    macd_h = macd(closes)[2]
    longs = []
    for i in range(st_p * 2, len(closes) - 1):
        if st[i] == 1 and macd_h[i] > 0:
            longs.append(i)
    return longs


def trend_follower_short(closes, st_p, st_mult, ema200_p):
    highs = h_1h[: len(closes)]
    lows = l_1h[: len(closes)]
    st = supertrend(highs, lows, closes, st_p, st_mult)
    macd_h = macd(closes)[2]
    shorts = []
    for i in range(st_p * 2, len(closes) - 1):
        if st[i] == -1 and macd_h[i] < 0:
            shorts.append(i)
    return shorts


# 4. MACRO SHORT: EMA50 crosses BELOW EMA200 → SHORT
def macro_long(closes, ema50_p, ema200_p):
    e50 = ema_arr(closes, ema50_p)
    e200 = ema_arr(closes, ema200_p)
    longs = []
    for i in range(ema200_p + 1, len(closes) - 1):
        if e50[i - 1] > e200[i - 1] and e50[i] <= e200[i]:
            longs.append(i)
    return longs


def macro_short(closes, ema50_p, ema200_p):
    e50 = ema_arr(closes, ema50_p)
    e200 = ema_arr(closes, ema200_p)
    shorts = []
    for i in range(ema200_p + 1, len(closes) - 1):
        if e50[i - 1] < e200[i - 1] and e50[i] >= e200[i]:
            shorts.append(i)
    return shorts


# ── Run all strategies with grids ────────────────────────────────────────────
print("\n" + "=" * 60)
print("UPDATED BACKTEST — Desmond's Custom Strategies")
print("=" * 60)

# Day Driver Long (1H)
run(
    "day_driver_long",
    "1h",
    closes_1h,
    [
        {"bb_p": p, "bb_std": s, "ema200_p": 200}
        for p in [15, 20, 25]
        for s in [1.5, 2.0, 2.5]
    ],
    day_driver_long,
    day_driver_short,
)

# Swing Sniper (1H)
run(
    "swing_sniper",
    "1h",
    closes_1h,
    [{"bb_p": p, "vol_ma_p": v} for p in [15, 20, 25] for v in [15, 20, 30]],
    swing_sniper_long,
    swing_sniper_short,
)

# Trend Follower Supertrend (4H)
run(
    "trend_follower_st",
    "4h",
    closes_4h,
    [
        {"st_p": p, "st_mult": m, "ema200_p": 200}
        for p in [7, 10, 14]
        for m in [2, 3, 4]
    ],
    trend_follower_long,
    trend_follower_short,
)

# Macro EMA Cross (4H)
run(
    "macro_ema",
    "4h",
    closes_4h,
    [{"ema50_p": 50, "ema200_p": 200}],
    macro_long,
    macro_short,
)

# Also run on 1H
run(
    "macro_ema",
    "1h",
    closes_1h,
    [{"ema50_p": 50, "ema200_p": 200}],
    macro_long,
    macro_short,
)


# Momentum Flip (all timeframes) for comparison
def mf_long(closes, rp, buf):
    r = rsi(closes, rp)
    return [
        i for i in range(rp + 1, len(closes) - 1) if r[i - 1] < 50 - buf and r[i] >= 50
    ]


def mf_short(closes, rp, buf):
    r = rsi(closes, rp)
    return [
        i for i in range(rp + 1, len(closes) - 1) if r[i - 1] > 50 + buf and r[i] <= 50
    ]


for tf, closes in [("1h", closes_1h), ("4h", closes_4h), ("1d", closes_1d)]:
    if len(closes) > 100:
        run(
            f"momentum_flip",
            tf,
            closes,
            [{"rp": r, "buf": b} for r in [10, 14, 20] for b in [2, 3, 5]],
            mf_long,
            mf_short,
        )

# ── Final summary ────────────────────────────────────────────────────────────
print("\n\n" + "=" * 70)
print("FINAL SUMMARY — Updated Strategies Ranked by Sharpe")
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
                    "params": best.get("params", {}),
                }
            )
    except:
        pass

summary.sort(key=lambda x: x["sharpe"], reverse=True)
print(
    f"\n{'Rank':<5} {'Strategy':<30} {'Sharpe':>7} {'Return':>8} {'MDD':>6} {'WR':>5} {'Trades':>7}"
)
print("-" * 80)
for i, s in enumerate(summary, 1):
    print(
        f"{i:<5} {s['strategy']:<30} {s['sharpe']:>7.3f} {s['return']:>7.1f}% {s['mdd']:>5.1f}% {s['win_rate']:>5.1f}% {s['trades']:>7}"
    )

with open(f"{OUT_DIR}/FINAL_SUMMARY_UPDATED.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n✅ Done! {len(summary)} strategies saved to {OUT_DIR}/")
print(f"   FINAL_SUMMARY_UPDATED.json = ranked by Sharpe")


# ════════════════════════════════════════════════════════════════════════════
#  NEW: INTEGRATED ANALYSIS — Regime Detection, Pairs, Kelly, Walk-Forward
# ════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("INTEGRATED ANALYSIS — Regime · Pairs · Kelly · Walk-Forward")
print("=" * 70)

# ── 1. REGIME DETECTION ───────────────────────────────────────────────────────
print("\n─── 1. REGIME DETECTION ───")
try:
    sys.path.insert(0, WORK_DIR)
    from regime_detector import (
        detect_regime,
        gaussian_hmm_detect,
        get_btc_data as rd_get_btc,
    )

    closes_arr = closes_4h if len(closes_4h) > 60 else closes_1h
    if len(closes_arr) >= 60:
        result_simple = detect_regime(closes_arr[-60:])
        result_hmm = gaussian_hmm_detect(closes_arr)
        print(
            f"  [Simple]  Regime: {result_simple['regime']} | "
            f"Ann.Vol: {result_simple['annualized_vol']:.2%} | "
            f"Trend: {result_simple['trend_daily_pct']:.3f}%/day"
        )
        print(
            f"  [HMM]     Regime: {result_hmm['regime']} | "
            f"Probs: {result_hmm['probabilities']}"
        )
        print(
            f"\n  Kelly sizing ADVISORY: Use 'half_kelly' sizing in "
            f"{'BULL' if result_simple['regime']=='BULL' else 'BEAR' if result_simple['regime']=='BEAR' else 'conservative_range'} mode"
        )
    else:
        print("  Not enough data for regime detection")
except Exception as e:
    print(f"  Regime detection skipped: {e}")


# ── 2. PAIRS TRADING (BTC/ETH) ───────────────────────────────────────────────
print("\n─── 2. PAIRS TRADING (BTC/ETH) ───")
try:
    from pairs_trading import (
        load_cached,
        backtest_pairs,
        calculate_spread,
        cointegration_test,
    )

    df_btc = load_cached("BTC/USDT", "1d")
    df_eth = load_cached("ETH/USDT", "1d")

    if not df_eth.empty and not df_btc.empty:
        # Align to same period
        common_start = max(df_btc.index.min(), df_eth.index.min())
        common_end = min(df_btc.index.max(), df_eth.index.max())
        df_btc = df_btc[common_start:common_end]
        df_eth = df_eth[common_start:common_end]
        print(f"  BTC/ETH aligned: {len(df_btc)} common candles")

        # Cointegration
        coint, pval = cointegration_test(df_btc["close"].values, df_eth["close"].values)
        print(f"  Cointegration: {'✅ YES' if coint else '❌ NO'} (p={pval})")

        # Spread stats
        spread, zscore, k = calculate_spread(
            df_btc["close"].values, df_eth["close"].values
        )
        if spread is not None:
            print(
                f"  Hedge Ratio k={k:.4f} | Z-score: {np.min(zscore):.2f} to {np.max(zscore):.2f}"
            )

        # Backtest
        pairs_result = backtest_pairs(df_btc, df_eth)
        if "error" not in pairs_result:
            print(
                f"  Backtest: Return={pairs_result['total_return_pct']:.1f}% | "
                f"Sharpe={pairs_result['sharpe_ratio']:.3f} | "
                f"Trades={pairs_result['n_trades']} | "
                f"WinRate={pairs_result['win_rate']:.1%}"
            )
        else:
            print(f"  Pairs backtest error: {pairs_result['error']}")
    else:
        print("  No ETH data available — skipping pairs trading")
except Exception as e:
    print(f"  Pairs trading skipped: {e}")


# ── 3. KELLY CRITERION POSITION SIZING ───────────────────────────────────────
print("\n─── 3. KELLY CRITERION POSITION SIZING ───")
try:
    from kelly_sizing import kelly_fraction, apply_kelly_to_backtester

    # Kelly for each strategy in the summary
    equity = 10000
    kelly_rows = []
    for s in summary:
        win_rate = s.get("win_rate", 0) / 100.0
        gross_win = s.get("return", 0) / max(s.get("ann_trades", 1), 1) * 0.01
        gross_loss = s.get("mdd", 5) / max(s.get("ann_trades", 1), 1) * 0.01
        if win_rate > 0 and gross_loss > 0:
            half_k = kelly_fraction(win_rate, gross_win, gross_loss) / 2
            capped = max(0, min(half_k, 0.25))
            pos_usd = equity * capped
            kelly_rows.append(
                {
                    "strategy": s["strategy"],
                    "win_rate": s["win_rate"],
                    "kelly_pct": round(capped * 100, 2),
                    "position_usd": round(pos_usd, 0),
                    "leverage": round(1 / capped, 1) if capped > 0 else float("inf"),
                }
            )

    if kelly_rows:
        print(f"  {'Strategy':<30} {'Win%':>6} {'Kelly%':>8} {'Pos $':>10} {'Lev':>6}")
        print(f"  {'-'*30}-+------+--------+----------+------")
        for row in sorted(kelly_rows, key=lambda x: x["kelly_pct"], reverse=True):
            print(
                f"  {row['strategy']:<30} {row['win_rate']:>5.1f}% "
                f"{row['kelly_pct']:>7.2f}% ${row['position_usd']:>9,.0f} "
                f"{row['leverage']:>5.1f}x"
            )
        print(
            f"\n  Note: Using half-Kelly (conservative) — max 25% of equity per trade"
        )
except Exception as e:
    print(f"  Kelly sizing skipped: {e}")


# ── 4. WALK-FORWARD ANALYSIS ─────────────────────────────────────────────────
print("\n─── 4. WALK-FORWARD ANALYSIS ───")
try:
    from walkforward import walk_forward_analysis, walk_forward_summary, simple_backtest
    import pandas as pd

    # Build a DataFrame from 1D close data
    if len(closes_1d) > 200:
        dates_1d = pd.date_range(end=datetime.now(), periods=len(closes_1d), freq="D")
        wf_df = pd.DataFrame(
            {
                "close": closes_1d,
                "open": closes_1d,
                "high": closes_1d,
                "low": closes_1d,
                "volume": np.ones(len(closes_1d)),
            },
            index=dates_1d,
        )

        print(
            f"  WF Data: {len(wf_df)} daily candles | "
            f"{wf_df.index[0].date()} → {wf_df.index[-1].date()}"
        )
        print(f"  Config:  Train=2yr, Test=6mo, Step=3mo")

        wf_results = walk_forward_analysis(
            wf_df, train_days=730, test_days=180, step_days=90, strategy_fn=None
        )
        wf_summary = walk_forward_summary(wf_results)

        print(
            f"\n  {'Win':>3} | {'Train Return':>12} | {'Test Return':>12} | "
            f"{'Train Sharpe':>12} | {'Test Sharpe':>12} | {'WFE':>6}"
        )
        print(f"  {'-'*3}-+{'-'*12}-+{'-'*12}-+{'-'*12}-+{'-'*12}-+------")
        for r in wf_results:
            print(
                f"  {r['window']:>3} | {r['train_return']:>11.1f}% | "
                f"{r['test_return']:>11.1f}% | "
                f"{r['train_sharpe']:>12.3f} | {r['test_sharpe']:>12.3f} | {r['wfe']:>6.3f}"
            )

        print(
            f"\n  Aggregate: Train avg={wf_summary['train_avg_return']:.1f}% "
            f"(σ={wf_summary['train_std']:.1f}%) | "
            f"Test avg={wf_summary['test_avg_return']:.1f}% "
            f"(σ={wf_summary['test_std']:.1f}%) | "
            f"WFE={wf_summary['avg_wfe']:.3f} | "
            f"Test win rate={wf_summary['test_win_rate']:.0%}"
        )
    else:
        print("  Not enough 1D data for walk-forward analysis")
except Exception as e:
    import traceback

    print(f"  Walk-forward skipped: {e}")


# ── SAVE ENHANCED FINAL SUMMARY ───────────────────────────────────────────────
enhanced = {
    "timestamp": datetime.now().isoformat(),
    "n_strategies": len(summary),
    "strategies": summary,
    "regime": (
        result_simple.get("regime", "UNKNOWN")
        if "result_simple" in dir()
        else "UNKNOWN"
    ),
    "pairs_available": not df_eth.empty if "df_eth" in dir() else False,
    "kelly_recommendations": kelly_rows if "kelly_rows" in dir() else [],
    "walkforward_summary": wf_summary if "wf_summary" in dir() else {},
}

with open(f"{OUT_DIR}/FINAL_SUMMARY_ENHANCED.json", "w") as f:
    json.dump(enhanced, f, indent=2, default=str)

print(f"\n✅ Enhanced summary saved → {OUT_DIR}/FINAL_SUMMARY_ENHANCED.json")
