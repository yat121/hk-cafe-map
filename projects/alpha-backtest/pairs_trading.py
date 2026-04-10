#!/usr/bin/env python3
"""
Pairs Trading — BTC/ETH mean-reversion strategy
- Fetches BTC and ETH price data
- Calculates spread via linear regression hedge ratio
- Signals: spread z-score > 2 → short BTC/long ETH
            spread z-score < -2 → long BTC/short ETH
- Backtests on 2020-2024 data
"""

import json, os, sys, time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
DATA_DIR = os.path.join(WORK_DIR, "data")
OUT_DIR = os.path.join(WORK_DIR, "results")
os.makedirs(OUT_DIR, exist_ok=True)

HAS_CCXT = False
try:
    import ccxt

    HAS_CCXT = True
except:
    pass


# ─────────────────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────────────────
def fetch_crypto_data(symbol, tf="1d", months=60):
    """Fetch OHLCV data for a symbol via ccxt Binance."""
    cache_path = os.path.join(
        DATA_DIR, f"{symbol.replace('/','_')}_{tf.replace('/','_')}.json"
    )

    # Check cache
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 5000:
        with open(cache_path) as f:
            raw = json.load(f)
        if raw:
            df = pd.DataFrame(
                raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            for c in ["open", "high", "low", "close", "volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            print(f"  [{symbol}] {len(df)} candles loaded from cache")
            return df

    if not HAS_CCXT:
        print(f"  [{symbol}] ERROR — ccxt unavailable and no cache")
        return pd.DataFrame()

    exchange = ccxt.binance({"enableRateLimit": True})
    since = exchange.parse8601(
        (datetime.now(timezone.utc) - timedelta(days=months * 30)).isoformat()
    )
    sym_ccxt = symbol.replace("/", "/USDT:USDT")  # USDT perpetual
    all_data = []
    for _ in range(80):
        batch = exchange.fetch_ohlcv(sym_ccxt, tf, since=since, limit=1000)
        if not batch:
            break
        all_data.extend(batch)
        since = batch[-1][0] + 1
        if len(batch) < 1000:
            break
        time.sleep(0.25)

    if not all_data:
        print(f"  [{symbol}] No data fetched")
        return pd.DataFrame()

    df = pd.DataFrame(
        all_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[~df.index.duplicated(keep="first")]
    df.sort_index(inplace=True)
    df.to_json(cache_path)
    print(f"  [{symbol}] {len(df)} candles saved to {cache_path}")
    return df


def load_cached(symbol, tf="1d"):
    """Try to load from cache, return empty df if not found."""
    cache_path = os.path.join(
        DATA_DIR, f"{symbol.replace('/','_')}_{tf.replace('/','_')}.json"
    )
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 5000:
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
        return df
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────
# PAIRS ANALYSIS
# ─────────────────────────────────────────────────────────
def calculate_spread(btc, eth, lookback=None):
    """
    Calculate spread = BTC - k * ETH using OLS hedge ratio.
    Returns spread series, z-score series, and hedge ratio k.
    """
    if lookback:
        btc = btc[-lookback:]
        eth = eth[-lookback:]

    # Align by index
    df = pd.DataFrame({"btc": btc, "eth": eth}).dropna()
    if len(df) < 30:
        return None, None, None

    # OLS hedge ratio: BTC = a + k * ETH
    x = df["eth"].values
    y = df["btc"].values
    x_mean, y_mean = x.mean(), y.mean()
    k = np.sum((x - x_mean) * (y - y_mean)) / (np.sum((x - x_mean) ** 2) + 1e-9)
    a = y_mean - k * x_mean

    spread = df["btc"].values - k * df["eth"].values - a
    spread_mean = np.mean(spread)
    spread_std = np.std(spread) + 1e-9
    z_score = (spread - spread_mean) / spread_std

    return spread, z_score, float(k)


def cointegration_test(btc, eth):
    """
    Engle-Granger style cointegration test.
    Returns cointegration flag and p-value estimate.
    """
    df = pd.DataFrame({"btc": np.asarray(btc), "eth": np.asarray(eth)}).dropna()
    if len(df) < 30:
        return False, 1.0

    # Residual-based test
    x = df["eth"].values
    y = df["btc"].values
    x_mean, y_mean = x.mean(), y.mean()
    k = np.sum((x - x_mean) * (y - y_mean)) / (np.sum((x - x_mean) ** 2) + 1e-9)
    residuals = y - k * x

    # ADF-like test on residuals (simplified)
    res_mean = np.mean(residuals)
    res_std = np.std(residuals) + 1e-9
    t_stat = np.mean(residuals[:-1] - residuals[1:]) / (
        res_std / np.sqrt(len(residuals))
    )

    # Rough p-value from t-stat
    from scipy import stats

    p_value = 2 * (1 - stats.norm.cdf(abs(t_stat)))

    # Heuristic: if mean residual is close to 0 and t-stat is significant → cointegrated
    cointegrated = (abs(res_mean / res_std) < 0.5) and (p_value < 0.05)
    return cointegrated, round(float(p_value), 4)


# ─────────────────────────────────────────────────────────
# PAIRS BACKTEST
# ─────────────────────────────────────────────────────────
def backtest_pairs(
    df_btc, df_eth, z_entry=2.0, z_exit=0.5, initial_capital=10000, fee=0.0009
):
    """
    Backtest pairs trading strategy.

    Parameters:
        z_entry: z-score threshold to enter trade
        z_exit:  z-score threshold to exit trade
    """
    # Align data
    combined = pd.DataFrame(
        {
            "btc": df_btc["close"],
            "eth": df_eth["close"],
        }
    ).dropna()

    if len(combined) < 100:
        return {"error": "Insufficient data"}

    # Calculate rolling spread (60-day lookback)
    lookback = 60
    spreads, zscores, hedge_ratios = [], [], []

    for i in range(lookback, len(combined)):
        btc_win = combined["btc"].values[:i]
        eth_win = combined["eth"].values[:i]
        sp, zs, k = calculate_spread(btc_win, eth_win, lookback=lookback)
        if sp is not None:
            spreads.append(sp[-1])
            zscores.append(zs[-1])
            hedge_ratios.append(k)
        else:
            spreads.append(np.nan)
            zscores.append(np.nan)
            hedge_ratios.append(np.nan)

    combined = combined.iloc[lookback:].copy()
    combined["spread"] = spreads[: len(combined)]
    combined["zscore"] = zscores[: len(combined)]
    combined["hedge_k"] = hedge_ratios[: len(combined)]

    combined["btc_ret"] = combined["btc"].pct_change()
    combined["eth_ret"] = combined["eth"].pct_change()

    # Trade simulation — track completed trades properly
    position = 0  # 1 = long BTC short ETH, -1 = short BTC long ETH, 0 = flat
    entry_equity = initial_capital
    equity = [initial_capital]
    completed_trades = []  # list of dicts with pnl
    trade_log = []  # for display

    for i in range(1, len(combined)):
        zs = combined["zscore"].iloc[i]
        k = combined["hedge_k"].iloc[i]
        if np.isnan(zs) or np.isnan(k):
            equity.append(equity[-1])
            continue

        btc_ret = combined["btc_ret"].iloc[i]
        eth_ret = combined["eth_ret"].iloc[i]

        btc_price = combined["btc"].iloc[i]
        eth_price = combined["eth"].iloc[i]
        k_scaled = k * (eth_price / btc_price) if btc_price > 0 else k
        pairs_ret = btc_ret - k_scaled * eth_ret

        prev_pos = position

        # Entry / exit signals
        if position == 0:
            if zs > z_entry:
                position = -1  # short BTC, long ETH
            elif zs < -z_entry:
                position = 1  # long BTC, short ETH
        else:
            if position == 1 and zs > -z_exit:
                position = 0  # exit long BTC
            elif position == -1 and zs < z_exit:
                position = 0  # exit short BTC

        # Record entry
        if prev_pos == 0 and position != 0:
            entry_equity = equity[-1]
            trade_log.append(
                {
                    "date": str(combined.index[i].date()),
                    "action": "ENTRY",
                    "direction": (
                        "LONG_BTC_SHORT_ETH" if position == 1 else "SHORT_BTC_LONG_ETH"
                    ),
                    "zscore": round(zs, 3),
                }
            )

        # Record exit: was in a trade, now flat
        if prev_pos != 0 and position == 0:
            ret = pairs_ret * prev_pos
            fee_cost = entry_equity * fee * 2  # entry + exit commissions
            pnl = entry_equity * ret - fee_cost
            completed_trades.append({"pnl": pnl, "ret": ret, "direction": prev_pos})
            entry_equity = equity[-1] + pnl
            trade_log.append(
                {
                    "date": str(combined.index[i].date()),
                    "action": "EXIT",
                    "pnl": round(pnl, 2),
                    "zscore": round(zs, 3),
                }
            )

        # P&L for the day
        if position != 0:
            pnl = entry_equity * pairs_ret * position
        else:
            pnl = 0

        equity.append(equity[-1] + pnl)

    equity = np.array(equity)
    returns = np.diff(equity) / equity[:-1]

    # Stats from completed trades
    total_return = (equity[-1] / initial_capital - 1) * 100
    n_trades = len(completed_trades)
    if completed_trades:
        pnls = [t["pnl"] for t in completed_trades]
        win_trades = sum(1 for p in pnls if p > 0)
        win_rate = win_trades / n_trades if n_trades > 0 else 0
    else:
        win_trades = 0
        win_rate = 0.0
    max_dd = 0
    peak = equity[0]
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak
        if dd > max_dd:
            max_dd = dd

    sharpe = (
        (np.mean(returns) / (np.std(returns) + 1e-9)) * np.sqrt(365)
        if len(returns) > 5
        else 0
    )

    return {
        "total_return_pct": round(float(total_return), 2),
        "final_equity": round(float(equity[-1]), 2),
        "initial_capital": initial_capital,
        "max_drawdown_pct": round(float(max_dd * 100), 2),
        "n_trades": n_trades,
        "n_wins": win_trades,
        "win_rate": round(float(win_rate), 3),
        "sharpe_ratio": round(float(sharpe), 3),
        "hedge_ratio_avg": round(float(np.nanmean(hedge_ratios)), 4),
        "trades": trade_log[-20:],  # last 20 trade events
    }


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def run_pairs_analysis(start_year=2020, end_year=2024, tf="1d"):
    print("\n" + "=" * 60)
    print("PAIRS TRADING ANALYSIS — BTC/ETH")
    print("=" * 60)

    # Load data
    df_btc = load_cached("BTC/USDT", tf)
    df_eth = load_cached("ETH/USDT", tf)

    if df_btc.empty or df_eth.empty:
        print("  Fetching data via ccxt...")
        df_btc = fetch_crypto_data("BTC/USDT", tf)
        df_eth = fetch_crypto_data("ETH/USDT", tf)

    if df_btc.empty or df_eth.empty:
        print("  ERROR: Could not load BTC or ETH data")
        return {}

    # Filter date range
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    df_btc = df_btc[start_date:end_date]
    df_eth = df_eth[start_date:end_date]
    print(f"\n  Period: {df_btc.index[0].date()} → {df_btc.index[-1].date()}")
    print(f"  BTC candles: {len(df_btc)}, ETH candles: {len(df_eth)}")

    # Cointegration test
    cointegrated, p_value = cointegration_test(df_btc["close"], df_eth["close"])
    print(f"\n  ── Cointegration Test ──")
    print(f"  Cointegrated: {'✅ YES' if cointegrated else '❌ NO'}")
    print(f"  P-value:      {p_value}")

    # Spread analysis
    spread, zscore, k = calculate_spread(df_btc["close"].values, df_eth["close"].values)
    if spread is not None:
        print(f"\n  ── Spread Analysis ──")
        print(f"  Hedge Ratio (k): {k:.4f} BTC per ETH")
        print(f"  Spread mean:     {np.mean(spread):.2f}")
        print(f"  Spread std:      {np.std(spread):.2f}")
        print(f"  Z-score range:   {np.min(zscore):.2f} to {np.max(zscore):.2f}")

    # Backtest
    result = backtest_pairs(df_btc, df_eth)
    print(f"\n  ── Backtest Results (z_entry=2.0, z_exit=0.5) ──")
    if "error" in result:
        print(f"  ERROR: {result['error']}")
    else:
        print(f"  Total Return:    {result['total_return_pct']:.2f}%")
        print(f"  Final Equity:   ${result['final_equity']:,.2f}")
        print(f"  Max Drawdown:   {result['max_drawdown_pct']:.2f}%")
        print(f"  Sharpe Ratio:   {result['sharpe_ratio']:.3f}")
        print(f"  N Trades:        {result['n_trades']}")
        print(f"  Win Rate:       {result['win_rate']:.1%}")
        print(f"  Avg Hedge Ratio:{result['hedge_ratio_avg']:.4f}")
        print(f"\n  Last 10 trades:")
        for t in result["trades"][-10:]:
            print(
                f"    {t['date']} | {t['action']:5s} | {t['direction']:25s} | z={t['zscore']}"
            )

    # Save result
    out_path = os.path.join(OUT_DIR, "pairs_trading_result.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Results saved → {out_path}")

    return result


if __name__ == "__main__":
    start_yr = int(sys.argv[1]) if len(sys.argv) > 1 else 2020
    end_yr = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
    run_pairs_analysis(start_year=start_yr, end_year=end_yr)
