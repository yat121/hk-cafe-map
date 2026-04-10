#!/usr/bin/env python3
"""
Regime Detector — HMM-based market regime detection for BTC
Regimes: BULL (trending up), BEAR (trending down), RANGING (sideways)
"""

import json, os, sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
DATA_DIR = os.path.join(WORK_DIR, "data")

HAS_CCXT = False
try:
    import ccxt

    HAS_CCXT = True
except:
    pass


# ─────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────
def get_btc_data(tf_str="4H", months=18):
    """Get BTC data from local cache or fetch fresh."""
    cache_path = os.path.join(DATA_DIR, f"BTC_USDT_{tf_str.replace('/','_')}.json")

    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 10000:
        with open(cache_path) as f:
            raw = json.load(f)
        df = pd.DataFrame(
            raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    # Fallback: fetch via ccxt
    if not HAS_CCXT:
        print("  [regime] No data and ccxt unavailable — using cached data only")
        return pd.DataFrame()

    import time

    exchange = ccxt.binance({"enableRateLimit": True})
    since = exchange.parse8601(
        (datetime.now(timezone.utc) - timedelta(days=months * 30)).isoformat()
    )
    all_data = []
    for _ in range(50):
        batch = exchange.fetch_ohlcv("BTC/USDT:USDT", tf_str, since=since, limit=1000)
        if not batch:
            break
        all_data.extend(batch)
        since = batch[-1][0] + 1
        if len(batch) < 1000:
            break
        time.sleep(0.3)

    df = pd.DataFrame(
        all_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


# ─────────────────────────────────────────────────────────
# SIMPLE HMM-STYLE REGIME DETECTOR (volatility + trend based)
# ─────────────────────────────────────────────────────────
def detect_regime(
    prices,
    volatility_threshold=0.02,
    trend_threshold=0.01,
    vol_lookback=30,
    trend_lookback=20,
):
    """
    Simple regime detector based on volatility and trend.

    Returns:
        dict with keys: regime (str), volatility (float), trend (float),
                        probabilities (dict), signals (dict)
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) < max(vol_lookback, trend_lookback) + 2:
        return _result("UNKNOWN", 0, 0, _unknown_probs(), _neutral_signals())

    # Calculate returns
    returns = np.diff(prices) / prices[:-1]

    # Volatility = annualized daily std of returns
    vol = np.std(returns[-vol_lookback:]) * np.sqrt(365)
    trend = np.mean(returns[-trend_lookback:])  # daily avg return

    # Regime classification
    if vol < volatility_threshold and abs(trend) < trend_threshold:
        regime = "RANGING"
    elif trend > trend_threshold:
        regime = "BULL"
    else:
        regime = "BEAR"

    # Probability estimates based on distance from thresholds
    prob_bull = _sigmoid(trend - trend_threshold, scale=100)
    prob_bear = _sigmoid(-trend - trend_threshold, scale=100)
    prob_range = _sigmoid(volatility_threshold - vol, scale=50)
    total = prob_bull + prob_bear + prob_range + 1e-9
    probs = {
        "BULL": round(prob_bull / total, 3),
        "BEAR": round(prob_bear / total, 3),
        "RANGING": round(prob_range / total, 3),
    }

    signals = {
        "momentum": round(float(trend * 100), 4),  # % daily drift
        "volatility": round(float(vol), 4),  # annualized vol
        "signal": regime,
    }

    return _result(regime, float(vol), float(trend), probs, signals)


def _sigmoid(x, scale=100):
    return 1.0 / (1.0 + np.exp(-scale * x))


def _unknown_probs():
    return {"BULL": 0.333, "BEAR": 0.333, "RANGING": 0.333}


def _neutral_signals():
    return {"momentum": 0.0, "volatility": 0.0, "signal": "UNKNOWN"}


def _result(regime, vol, trend, probs, signals):
    return {
        "regime": regime,
        "annualized_vol": vol,
        "trend_daily_pct": trend * 100,
        "probabilities": probs,
        "signals": signals,
    }


# ─────────────────────────────────────────────────────────
# GAUSSIAN HMM (2-state for simplicity, no hmmlearn needed)
# ─────────────────────────────────────────────────────────
def gaussian_hmm_detect(closes, n_states=3, lookback=60):
    """
    Simple Gaussian HMM using K-means to initialize and EM-style iteration.
    States correspond to: 0=BEAR, 1=RANGING, 2=BULL (ordered by mean return)
    """
    closes = np.asarray(closes, dtype=float)
    if len(closes) < lookback:
        return detect_regime(closes)  # fallback

    data = closes[-lookback:]
    returns = np.diff(data) / data[:-1]
    X = returns.reshape(-1, 1)

    # Simple initialization: cluster by return level
    labels = _kmeans_labels(X, n_states)
    means = np.array([X[labels == i].mean() for i in range(n_states)])
    stds = np.array([max(X[labels == i].std(), 1e-6) for i in range(n_states)])
    pis = np.bincount(labels, minlength=n_states).astype(float) / len(labels)

    # EM iteration (3 steps)
    for _ in range(3):
        # E-step
        gammas = np.zeros((len(X), n_states))
        for j in range(n_states):
            gammas[:, j] = pis[j] * _normpdf(X.flatten(), means[j], stds[j])
        gammas /= gammas.sum(axis=1, keepdims=True) + 1e-9

        # M-step
        for j in range(n_states):
            pis[j] = max(gammas[:, j].mean(), 1e-9)
            means[j] = (gammas[:, j] * X.flatten()).sum() / (gammas[:, j].sum() + 1e-9)
            stds[j] = max(
                np.sqrt(
                    (gammas[:, j] * (X.flatten() - means[j]) ** 2).sum()
                    / (gammas[:, j].sum() + 1e-9)
                ),
                1e-6,
            )

    # Classify last observation
    posteriors = np.zeros(n_states)
    for j in range(n_states):
        posteriors[j] = pis[j] * _normpdf(X.flatten()[-1], means[j], stds[j])
    posteriors /= posteriors.sum() + 1e-9

    # Order states by mean (low→high)
    order = np.argsort(means)
    state_names = ["BEAR", "RANGING", "BULL"][:n_states]
    named = {
        order[i]: state_names[i] if i < len(state_names) else f"STATE_{i}"
        for i in range(n_states)
    }

    regime = named[np.argmax(posteriors)]
    prob_map = {
        named[i]: round(float(posteriors[order[i]]), 3) for i in range(n_states)
    }

    return {
        "regime": regime,
        "method": "gaussian_hmm_em",
        "probabilities": prob_map,
        "signals": {
            "momentum": round(float(np.mean(returns[-20:]) * 100), 4),
            "volatility": round(float(np.std(returns[-30:]) * np.sqrt(365)), 4),
            "signal": regime,
        },
        "state_means": {
            named[i]: round(float(means[order[i]] * 100), 4) for i in range(n_states)
        },
    }


def _kmeans_labels(X, k, max_iter=20):
    centroids = np.percentile(X, np.linspace(0, 100, k)).reshape(-1, 1)
    for _ in range(max_iter):
        dists = np.abs(X - centroids.T)
        labels = np.argmin(dists, axis=1)
        new_cents = np.array(
            [
                X[labels == i].mean() if (labels == i).any() else c
                for i, c in enumerate(centroids.flatten())
            ]
        )
        if np.allclose(centroids.flatten(), new_cents, atol=1e-6):
            break
        centroids = new_cents.reshape(-1, 1)
    return labels


def _normpdf(x, mu, sigma):
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def run_regime_analysis(tf="4H"):
    print("\n" + "=" * 60)
    print("REGIME DETECTION ANALYSIS")
    print("=" * 60)

    df = get_btc_data(tf_str=tf)
    if df.empty:
        print("  No data available.")
        return {}

    closes = df["close"].values
    n = len(closes)
    print(
        f"\n  Data: {n} candles loaded ({df.index[0].date()} → {df.index[-1].date()})"
    )

    # Simple rule-based
    result_simple = detect_regime(closes[-60:])
    print(f"\n  ── Simple Regime Detector ──")
    print(f"  Regime:        {result_simple['regime']}")
    print(f"  Ann. Vol:      {result_simple['annualized_vol']:.2%}")
    print(f"  Daily Trend:   {result_simple['trend_daily_pct']:.4f}%")
    print(f"  Probabilities: {result_simple['probabilities']}")

    # HMM
    result_hmm = gaussian_hmm_detect(closes)
    print(f"\n  ── Gaussian HMM (3-state EM) ──")
    print(f"  Regime:        {result_hmm['regime']}")
    print(f"  Probabilities: {result_hmm['probabilities']}")
    print(f"  State Means:   {result_hmm['state_means']}")

    # Regime history
    print(f"\n  ── Regime History (last 30 windows) ──")
    regimes_hist = []
    for i in range(30, 0, -1):
        window = (
            closes[-(i * 24) :] if tf == "1H" else closes[-(i * 6) :]
        )  # rough day windows
        r = detect_regime(window)
        regimes_hist.append(r["regime"])

    for label, color in [("BULL", "🟢"), ("BEAR", "🔴"), ("RANGING", "🟡")]:
        count = regimes_hist.count(label)
        bar = "█" * count
        print(f"  {color} {label:8s}: {bar} ({count})")

    print(f"\n  Current regime recommendation: {result_hmm['regime']}")
    return {
        "simple": result_simple,
        "hmm": result_hmm,
        "data_points": n,
        "period": f"{df.index[0].isoformat()} to {df.index[-1].isoformat()}",
    }


if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "4H"
    result = run_regime_analysis(tf)
