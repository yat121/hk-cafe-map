"""Quant-Alpha Backtest CLI."""

import argparse
import sys

sys.path.insert(0, ".")

from backtester.engine import Backtester
from strategies.rsi_strategy import RSI4HStrategy


def load_strategy(name):
    if name.lower() in ("rsi4h", "rsi"):
        return RSI4HStrategy
    raise ValueError(f"Unknown strategy: {name}")


def main():
    parser = argparse.ArgumentParser(description="Quant-Alpha Backtest")
    parser.add_argument("--market", required=True, help="MNQ or MHI")
    parser.add_argument("--strategy", required=True, help="rsi4h, macd, etc.")
    parser.add_argument("--months", type=int, default=14, help="In-sample months")
    parser.add_argument("--oos", type=int, default=2, help="Out-of-sample months")
    args = parser.parse_args()

    strat = load_strategy(args.strategy)
    bt = Backtester(args.market, strat, months=args.months, oos_months=args.oos)
    metrics = bt.run()

    print("\n" + "=" * 50)
    print(f"  QUANT-ALPHA BACKTEST RESULTS")
    print(f"  Market: {args.market}  |  Strategy: {args.strategy}")
    print(f"  In-sample: {args.months}m  |  Out-of-sample: {args.oos}m")
    print("=" * 50)
    print(f"\n  OVERALL PERFORMANCE:")
    print(f"  Total Return:     {metrics.get('total_return',0):.2f}%")
    print(f"  Net Return:       ${metrics.get('net_return',0):.2f}")
    print(f"  CAGR:             {metrics.get('cagr',0):.2f}%")
    print(f"  Sharpe Ratio:     {metrics.get('sharpe',0):.2f}")
    print(f"  Sortino Ratio:    {metrics.get('sortino',0):.2f}")
    print(f"  Max Drawdown:     {metrics.get('max_drawdown',0):.2f}%")
    print(f"  Win Rate:         {metrics.get('win_rate',0):.1f}%")
    print(f"  Profit Factor:    {metrics.get('profit_factor',0):.2f}")
    print(f"  Total Trades:     {metrics.get('total_trades',0)}")
    print(f"  Cost Impact:      {metrics.get('cost_impact_pct',0):.2f}%")
    print(f"  Avg Trade P&L:    ${metrics.get('avg_trade_pnl',0):.2f}")

    is_m = metrics.get("in_sample", {})
    os_m = metrics.get("out_sample", {})
    if is_m:
        print(f"\n  IN-SAMPLE ({args.months}m):")
        print(
            f"    Sharpe: {is_m.get('sharpe',0):.2f}  |  Return: {is_m.get('total_return',0):.2f}%  |  Trades: {is_m.get('total_trades',0)}"
        )
    if os_m:
        print(f"\n  OUT-OF-SAMPLE ({args.oos}m):")
        print(
            f"    Sharpe: {os_m.get('sharpe',0):.2f}  |  Return: {os_m.get('total_return',0):.2f}%  |  Trades: {os_m.get('total_trades',0)}"
        )
    print()


if __name__ == "__main__":
    main()
