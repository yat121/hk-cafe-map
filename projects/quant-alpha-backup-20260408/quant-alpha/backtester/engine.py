"""Core backtesting engine with walk-forward split."""

import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from .data_fetcher import fetch_futures
from .metrics import compute_metrics
from .slippage import compute_slippage
from .costs import compute_costs


class SIDE:
    LONG, SHORT, EXIT = 1, -1, 0


class Signal:
    def __init__(self, side, size=1):
        self.side = side
        self.size = size


class Backtester:
    def __init__(
        self, market, strategy_class, months=14, oos_months=2, contract_size=1
    ):
        self.market = market
        self.strategy_class = strategy_class
        self.is_months = months
        self.oos_months = oos_months
        self.contract_size = contract_size
        self.trades = []
        self.equity = []
        self.in_sample_trades = []
        self.out_sample_trades = []

    def run(self):
        # Fetch data
        end = datetime.now()
        start = end - timedelta(days=(self.is_months + self.oos_months) * 35)
        df = fetch_futures(self.market, start, end)
        if df is None or len(df) < 200:
            print("Data fetch failed or insufficient data")
            return {"error": "insufficient data"}

        # Walk-forward split
        trading_days_per_month = 21
        is_days = self.is_months * trading_days_per_month
        oos_days = self.oos_months * trading_days_per_month
        total_needed = is_days + oos_days
        df = df.tail(total_needed).copy().reset_index(drop=True)

        split_idx = len(df) - oos_days
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()

        # Run strategy on train (in-sample)
        strat = self.strategy_class()
        strat.train(train_df)
        is_trades = self._run_trading(train_df, strat)
        is_equity = self._equity_from_trades(is_trades, train_df)

        # Run strategy on test (out-of-sample)
        strat2 = self.strategy_class()
        strat2.train(train_df)  # Use same trained params
        oos_trades = self._run_trading(test_df, strat2)
        oos_equity = self._equity_from_trades(oos_trades, test_df)

        # Combine equity
        all_equity = is_equity + oos_equity
        all_trades = is_trades + oos_trades

        # Compute metrics
        metrics = compute_metrics(all_trades, all_equity)
        metrics["in_sample"] = compute_metrics(
            is_trades, is_equity, include_detail=True
        )
        metrics["out_sample"] = compute_metrics(
            oos_trades, oos_equity, include_detail=True
        )
        metrics["split_index"] = split_idx
        metrics["total_trades"] = len(all_trades)

        self.trades = all_trades
        self.equity = all_equity
        self.in_sample_trades = is_trades
        self.out_sample_trades = oos_trades
        return metrics

    def _run_trading(self, df, strat):
        trades = []
        position = 0
        entry_price = 0
        entry_time = None
        entry_rsi = None

        for i in range(20, len(df)):
            signal = strat.on_bar(df, i)
            bar = df.iloc[i]
            close = bar["Close"]

            if signal is not None and signal.side == SIDE.LONG and position == 0:
                # Entry
                slip = compute_slippage(close * 0.01, close * 0.02, urgency=1.0)
                entry = close * (1 + slip / 10000)
                cost = compute_costs(1)
                position = 1
                entry_price = entry
                entry_time = bar.name if hasattr(bar, "name") else i
                entry_rsi = bar.get("RSI", 50)
                trades.append(
                    {
                        "entry_time": entry_time,
                        "entry_price": entry,
                        "side": "LONG",
                        "rsi_at_entry": entry_rsi,
                        "costs": cost,
                    }
                )
            elif signal is not None and signal.side == SIDE.EXIT and position > 0:
                # Exit
                slip = compute_slippage(close * 0.01, close * 0.02, urgency=1.0)
                exit_price = close * (1 - slip / 10000)
                cost = compute_costs(1)
                pnl = (exit_price - entry_price) * self.contract_size - cost
                if trades:
                    trades[-1]["exit_time"] = bar.name if hasattr(bar, "name") else i
                    trades[-1]["exit_price"] = exit_price
                    trades[-1]["pnl"] = pnl
                    trades[-1]["return_pct"] = (
                        (exit_price - entry_price) / entry_price * 100
                    )
                    trades[-1]["duration_bars"] = i - (
                        entry_time if isinstance(entry_time, int) else 0
                    )
                    trades[-1]["costs"] = trades[-1].get("costs", 0) + cost
                position = 0

        # Close any open position at end
        if position > 0 and len(df) > 0:
            bar = df.iloc[-1]
            exit_price = bar["Close"]
            cost = compute_costs(1)
            pnl = (exit_price - entry_price) * self.contract_size - cost
            if trades:
                trades[-1]["exit_time"] = (
                    bar.name if hasattr(bar, "name") else len(df) - 1
                )
                trades[-1]["exit_price"] = exit_price
                trades[-1]["pnl"] = pnl
                trades[-1]["return_pct"] = (
                    (exit_price - entry_price) / entry_price * 100
                )
                trades[-1]["costs"] = trades[-1].get("costs", 0) + cost

        return trades

    def _equity_from_trades(self, trades, df):
        equity = [10000]  # Start with $10k
        for trade in trades:
            pnl = trade.get("pnl", 0)
            equity.append(equity[-1] + pnl)
        # Pad to match df length if needed
        while len(equity) < len(df):
            equity.append(equity[-1])
        return equity[: len(df)]
