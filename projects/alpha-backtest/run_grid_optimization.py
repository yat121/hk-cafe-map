#!/usr/bin/env python3
"""Grid search optimizer for RSI strategy across given timeframe.
Outputs JSON with metadata, all_results (top 200 by profit factor), best_params (top 10), passing_count.
"""

import json, os, hashlib, math, sys
from datetime import datetime
from itertools import product
import rsi_backtest as rbt  # assuming rsi_backtest.py is in same dir and defines run_backtest


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: run_grid_optimization.py <timeframe> <fee_percent> <slippage_percent> <output_file>"
        )
        sys.exit(1)
    timeframe = sys.argv[1]  # e.g., 4H or 1D (will map to Binance interval)
    fee_percent = float(sys.argv[2])  # e.g., 0.045 for 0.045%
    slippage_percent = float(sys.argv[3])  # e.g., 5 for 5%
    output_file = sys.argv[4]
    # Parameter ranges
    periods = range(8, 21)  # inclusive 20
    lows = range(15, 41)
    highs = range(60, 86)
    # fetch data once
    binance_map = {"1H": "1h", "4H": "4h", "1D": "1d"}
    binance_tf = binance_map.get(timeframe.upper())
    if not binance_tf:
        print(f"Unsupported timeframe {timeframe}")
        sys.exit(1)
    # Use 180 days data
    data = rbt.fetch_btc_usdc_data(binance_tf, 180)
    if not data:
        print("No data fetched")
        sys.exit(1)
    results = []
    for period, low, high in product(periods, lows, highs):
        if low >= high:
            continue
        res = rbt.run_backtest(
            data,
            low,
            high,
            period,
            taker_fee=fee_percent / 100,
            slippage=slippage_percent / 100,
        )
        if "error" in res:
            continue
        # include params
        res_entry = {
            "rsi_period": period,
            "rsi_low": low,
            "rsi_high": high,
            "metrics": {
                "total_trades": res["total_trades"],
                "profit_factor": res["profit_factor"],
                "sharpe_ratio": res["sharpe_ratio"],
                "max_drawdown_pct": res["max_drawdown_pct"],
                "final_equity": res["final_equity"],
                "total_profit_pct": res["total_profit_pct"],
            },
            "trade_log": res.get("trade_log", []),
        }
        results.append(res_entry)
    # sort by profit factor descending
    results.sort(key=lambda x: x["metrics"]["profit_factor"], reverse=True)
    top200 = results[:200]
    best10 = top200[:10]
    # count passing criteria
    passing = [
        r
        for r in results
        if r["metrics"]["max_drawdown_pct"] < 15
        and r["metrics"]["sharpe_ratio"] > 2.0
        and r["metrics"]["profit_factor"] > 1.75
        and r["metrics"]["total_trades"] >= 10
    ]
    output = {
        "metadata": {
            "timeframe": timeframe,
            "symbol": "BTC/USDT",
            "date": datetime.utcnow().isoformat(),
            "param_hash": hashlib.md5(f"{timeframe}".encode()).hexdigest()[:8],
        },
        "all_results": top200,
        "best_params": best10,
        "passing_count": len(passing),
    }
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
