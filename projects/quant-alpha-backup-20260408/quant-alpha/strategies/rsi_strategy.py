"""RSI 4-hour strategy."""

import pandas as pd
import numpy as np
from backtester.engine import SIDE, Signal


class RSI4HStrategy:
    params = {"rsi_period": 14, "rsi_buy": 30, "rsi_sell": 70}

    def train(self, df):
        # No training needed for RSI strategy - just store params
        pass

    def on_bar(self, df, i):
        if i < self.params["rsi_period"]:
            return None
        rsi = df["RSI"].iloc[i]
        pos = df.get("position", pd.Series([0] * len(df))).iloc[i] if i > 0 else 0
        if rsi < self.params["rsi_buy"] and pos == 0:
            return Signal(SIDE.LONG, size=1)
        elif rsi > self.params["rsi_sell"] and pos > 0:
            return Signal(SIDE.EXIT, size=0)
        return None

    def name(self):
        return "RSI4H"
