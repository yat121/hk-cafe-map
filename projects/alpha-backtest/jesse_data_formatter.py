#!/usr/bin/env python3
"""
jesse_data_formatter.py
Reads Alpha's existing BTC data (from data/ folder) and converts to
Jesse's candle format: [[timestamp_ms, open, high, low, close, volume], ...]
Also supports fetching fresh data from Binance.
"""

import json, os, sys, time
from datetime import datetime

import numpy as np
import pandas as pd

WORK_DIR = "/home/yat121/.openclaw/workspace/projects/alpha-backtest"
DATA_DIR = os.path.join(WORK_DIR, "data")

# Map Alpha timeframe strings to Binance interval
TF_MAP = {"30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d"}

# Jesse candle format:
# [[timestamp_ms, open, high, low, close, volume], ...]


def load_alpha_data(tf: str) -> np.ndarray:
    """
    Load BTC data from Alpha's data folder.
    Returns numpy array of Jesse-format candles: [[ts_ms, o, h, l, c, v], ...]
    """
    # Map our TF strings to data filenames
    fname_map = {
        "30m": "BTC_USDT_30m.json",
        "1h": "BTC_USDT_1h.json",
        "4h": "BTC_USDT_4h.json",
        "1d": "BTC_USDT_1d.json",
    }
    fname = fname_map.get(tf)
    if not fname:
        raise ValueError(f"Unknown timeframe: {tf}")

    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        print(f"[jesse_data_formatter] {path} not found — fetching fresh from Binance")
        return fetch_and_convert(tf)

    with open(path) as f:
        raw = json.load(f)

    candles = []
    for row in raw:
        if isinstance(row, list) and len(row) >= 6:
            ts = (
                int(row[0])
                if isinstance(row[0], (int, float))
                else int(pd.Timestamp(row[0]).timestamp() * 1000)
            )
            candles.append(
                [
                    ts,
                    float(row[1]),
                    float(row[2]),
                    float(row[3]),
                    float(row[4]),
                    float(row[5]),
                ]
            )
        elif isinstance(row, dict):
            ts = int(row.get("timestamp", row.get("time", 0)))
            if isinstance(ts, float):
                ts = int(ts * 1000)
            candles.append(
                [
                    ts,
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"]),
                ]
            )
    candles.sort(key=lambda x: x[0])
    print(f"[jesse_data_formatter] Loaded {len(candles)} candles from {fname}")
    return np.array(candles, dtype=float)


def fetch_and_convert(tf: str) -> np.ndarray:
    """
    Fetch BTCUSDT from Binance REST API and convert to Jesse format.
    Returns numpy array of Jesse-format candles.
    """
    interval_map = {"30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d"}
    interval = interval_map.get(tf, "1h")

    limit = 1000
    end_ms = int(datetime.now().timestamp() * 1000)
    days_back = {"30m": 60, "1h": 730, "4h": 730, "1d": 1825}.get(tf, 730)
    start_ms = end_ms - (days_back * 86400 * 1000)

    all_rows = []
    current = start_ms

    while current < end_ms:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol=BTCUSDT&interval={interval}"
            f"&startTime={current}&endTime={end_ms}&limit={limit}"
        )
        try:
            import urllib.request

            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            if not data:
                break
            for row in data:
                all_rows.append(
                    [
                        int(row[0]),  # timestamp_ms
                        float(row[1]),  # open
                        float(row[2]),  # high
                        float(row[3]),  # low
                        float(row[4]),  # close
                        float(row[5]),  # volume
                    ]
                )
            current = data[-1][0] + 1
            time.sleep(0.15)
        except Exception as e:
            print(f"    Binance fetch error: {e}")
            break

    all_rows.sort(key=lambda x: x[0])
    arr = np.array(all_rows, dtype=float)
    print(f"[jesse_data_formatter] Fetched {len(arr)} candles from Binance for {tf}")
    return arr


def candles_to_jesse_format(candles_df: pd.DataFrame) -> np.ndarray:
    """
    Convert a pandas DataFrame with columns [timestamp, open, high, low, close, volume]
    to Jesse's expected numpy array format.
    """
    if isinstance(candles_df.index, pd.DatetimeIndex):
        ts_ms = candles_df.index.view(np.int64) // 1_000_000
    else:
        ts_ms = pd.to_datetime(candles_df["timestamp"]).view(np.int64) // 1_000_000

    result = np.column_stack(
        [
            ts_ms,
            candles_df["open"].values,
            candles_df["high"].values,
            candles_df["low"].values,
            candles_df["close"].values,
            candles_df["volume"].values,
        ]
    )
    return result.astype(float)


def make_jesse_candles_dict(
    candles_arr: np.ndarray, exchange: str = "Binance", symbol: str = "BTC-USDT"
) -> dict:
    """
    Build the candles dict expected by jesse.research.backtest().

    Structure:
    {
        'Binance-BTC-USDT': {
            'exchange': 'Binance',
            'symbol': 'BTC-USDT',
            'candles': np.array(shape=(n,6), dtype=float)
        }
    }
    candles_arr shape: (n, 6) = [[ts_ms, o, h, l, c, v], ...]
    """
    key = f"{exchange}-{symbol}"
    return {
        key: {
            "exchange": exchange,
            "symbol": symbol,
            "candles": candles_arr,
        }
    }


def save_candles_csv(candles_arr: np.ndarray, path: str) -> None:
    """Save Jesse-format candles to CSV."""
    header = "timestamp_ms,open,high,low,close,volume"
    rows = ["\n".join([header] + [",".join(map(str, row)) for row in candles_arr])]
    with open(path, "w") as f:
        f.write(header + "\n")
        for row in candles_arr:
            f.write(",".join(map(str, row)) + "\n")
    print(f"[jesse_data_formatter] Saved {len(candles_arr)} candles to {path}")


def load_candles_csv(path: str) -> np.ndarray:
    """Load candles from CSV back to Jesse format."""
    df = pd.read_csv(path)
    arr = df.values.astype(float)
    return arr


# ─── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    for tf in ["1h", "4h", "1d"]:
        arr = load_alpha_data(tf)
        print(f"  {tf}: {arr.shape} | {arr[0,0]} -> {arr[-1,0]} | sample: {arr[0,:]}")
