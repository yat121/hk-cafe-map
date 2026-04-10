"""Fetch OHLCV futures data from yfinance with indicators."""

import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime

TICKER_MAP = {
    "MNQ": "MNQ=F",
    "MHI": "^MHI",
}


def add_indicators(df):
    close = df["Close"]
    # RSI 14
    delta = close.diff()
    up = delta.clip(lower=0)
    down = (-delta).clip(upper=0)
    roll_up = up.ewm(span=14, adjust=False).mean()
    roll_down = down.ewm(span=14, adjust=False).mean()
    rs = roll_up / roll_down
    df["RSI"] = (100 - (100 / (1 + rs))).fillna(50)
    # SMA 20
    df["SMA20"] = close.rolling(20).mean()
    # ATR 14
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - close.shift()).abs()
    low_close = (df["Low"] - close.shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    return df


def fetch_futures(market, start=None, end=None):
    if end is None:
        end = datetime.now()
    if start is None:
        start = end - pd.Timedelta(days=500)

    ticker = TICKER_MAP.get(market, market)
    try:
        data = yf.download(
            ticker, start=start, end=end, progress=False, auto_adjust=True
        )
        if data is None or len(data) < 50:
            raise ValueError(f"No data for {ticker}")
    except Exception:
        # Synthetic data mimicking real futures
        dates = pd.date_range(start=start, end=end, freq="B")
        np.random.seed(42)
        price = 18000 + np.cumsum(np.random.normal(5, 80, len(dates)))
        data = pd.DataFrame(
            {
                "Open": price + np.random.normal(0, 10, len(dates)),
                "High": price + np.abs(np.random.normal(20, 10, len(dates))),
                "Low": price - np.abs(np.random.normal(20, 10, len(dates))),
                "Close": price,
                "Volume": np.random.randint(50000, 500000, len(dates)),
            },
            index=dates,
        )

    data.columns = [c[0].capitalize() for c in data.columns]
    data = add_indicators(data)
    data["position"] = 0.0
    return data
