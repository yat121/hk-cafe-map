#!/usr/bin/env python3
"""
Alpha Agent - RSI Reversal Backtest Engine
Supports multi-timeframe backtesting with train/test split
"""

import json
import hashlib
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


# RSI Crossover Strategy
def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate RSI values"""
    if len(prices) < period + 1:
        return [50.0] * len(prices)

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi_values = [50.0] * period

    for i in range(period, len(prices)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

    return rsi_values


def check_signals(
    rsi_current: float, rsi_prev: float, rsi_low: int, rsi_high: int
) -> Optional[str]:
    """
    RSI Crossover Logic - Professional Entry: Wait for the hook back inside
    """
    # Hook back inside - RSI crosses from outside to inside
    if rsi_prev < rsi_low and rsi_current >= rsi_low:
        return "LONG"
    elif rsi_prev > rsi_high and rsi_current <= rsi_high:
        return "SHORT"
    return None


def fetch_btc_usdc_data(timeframe: str, days: int) -> List[Dict]:
    """
    Fetch historical BTC/USDT data from Binance
    Returns list of {'timestamp': int, 'open': float, 'high': float, 'low': float, 'close': float, 'volume': float}
    """
    import urllib.request
    import time

    # Binance klines endpoint
    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)

    current = start_time
    while current < end_time:
        url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={timeframe}&startTime={current}&endTime={end_time}&limit=1000"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
            if not data:
                break
            for row in data:
                all_data.append(
                    {
                        "timestamp": row[0] // 1000,  # Convert ms to seconds
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                    }
                )
            current = data[-1][0] + 1
            time.sleep(0.2)  # Rate limit
        except Exception as e:
            print(f"Error: {e}")
            break

    # Sort by timestamp
    all_data.sort(key=lambda x: x["timestamp"])
    return all_data


def resample_data(data: List[Dict], target_tf: str) -> List[Dict]:
    """Resample data to target timeframe"""
    # Binance already provides data at the requested interval
    # We just need to aggregate 15m to 1h or 4h if we fetched 15m data
    return data


def aggregate_to_hourly(data: List[Dict]) -> List[Dict]:
    if not data:
        return []
    # Group by hour
    hourly = {}
    for candle in data:
        ts = candle["timestamp"]
        hour_ts = (ts // 3600) * 3600
        if hour_ts not in hourly:
            hourly[hour_ts] = {
                "timestamp": hour_ts,
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle.get("volume", 0),
            }
        else:
            hourly[hour_ts]["high"] = max(hourly[hour_ts]["high"], candle["high"])
            hourly[hour_ts]["low"] = min(hourly[hour_ts]["low"], candle["low"])
            hourly[hour_ts]["close"] = candle["close"]
            hourly[hour_ts]["volume"] += candle.get("volume", 0)
    return list(hourly.values())


def aggregate_to_4h(data: List[Dict]) -> List[Dict]:
    if not data:
        return []
    # Group by 4 hours
    data_4h = {}
    for candle in data:
        ts = candle["timestamp"]
        four_h_ts = (ts // (4 * 3600)) * (4 * 3600)
        if four_h_ts not in data_4h:
            data_4h[four_h_ts] = {
                "timestamp": four_h_ts,
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle.get("volume", 0),
            }
        else:
            data_4h[four_h_ts]["high"] = max(data_4h[four_h_ts]["high"], candle["high"])
            data_4h[four_h_ts]["low"] = min(data_4h[four_h_ts]["low"], candle["low"])
            data_4h[four_h_ts]["close"] = candle["close"]
            data_4h[four_h_ts]["volume"] += candle.get("volume", 0)
    return list(data_4h.values())


def run_backtest(
    data: List[Dict],
    rsi_low: int,
    rsi_high: int,
    rsi_period: int,
    taker_fee: float = 0.00045,  # 0.045% updated taker fee
    slippage: float = 0.05,  # 5% slippage tolerance
) -> Dict:
    """
    Run RSI reversal backtest on price data
    Returns metrics dictionary
    """
    if len(data) < rsi_period + 2:
        return {"error": "Insufficient data"}

    closes = [c["close"] for c in data]
    rsi_values = calculate_rsi(closes, rsi_period)

    # Backtest simulation
    trades = []
    position = None  # None, 'LONG', or 'SHORT'
    entry_price = 0
    entry_idx = 0

    total_trades = 0
    winning_trades = 0
    gross_profit = 0
    gross_loss = 0
    peak_equity = 0
    equity = 1.0  # Start with $1
    max_drawndown = 0
    max_equity = 1.0

    trade_log = []

    for i in range(1, len(data)):
        signal = check_signals(rsi_values[i], rsi_values[i - 1], rsi_low, rsi_high)

        if signal and position is None:
            # Enter position
            fee = taker_fee * data[i]["close"]
            position = signal
            # Apply slippage: increase price for LONG entry, decrease for SHORT entry
            entry_price = (
                (data[i]["close"] * (1 + slippage))
                + (fee if signal == "LONG" else -fee)
                if signal == "LONG"
                else (data[i]["close"] * (1 - slippage)) - fee
            )
            entry_idx = i
        elif position:
            # Check exit on opposite signal or end
            should_exit = signal and signal != position
            if should_exit:
                # Exit
                # Apply slippage on exit price
                exit_price = (
                    (data[i]["close"] * (1 - slippage))
                    if position == "LONG"
                    else (data[i]["close"] * (1 + slippage))
                )
                fee = taker_fee * exit_price

                if position == "LONG":
                    pnl = (exit_price - entry_price - fee) / entry_price
                else:  # SHORT
                    pnl = (entry_price - exit_price - fee) / entry_price

                equity *= 1 + pnl
                total_trades += 1

                if pnl > 0:
                    winning_trades += 1
                    gross_profit += abs(pnl)
                else:
                    gross_loss += abs(pnl)

                trade_log.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": i,
                        "type": position,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "equity": equity,
                    }
                )

                position = None
                entry_price = 0

    # Calculate metrics
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf") if gross_profit > 0 else 0
    )

    # Calculate Max Drawdown
    running_equity = [1.0]
    for t in trade_log:
        running_equity.append(t["equity"])

    peak = running_equity[0]
    max_dd = 0
    for eq in running_equity:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd

    max_drawndown = max_dd * 100  # as percentage

    # Sharpe Ratio (simplified)
    if len(trade_log) > 1:
        returns = [t["pnl"] for t in trade_log]
        avg_return = sum(returns) / len(returns)
        std_return = math.sqrt(
            sum((r - avg_return) ** 2 for r in returns) / len(returns)
        )
        sharpe = (avg_return / std_return * math.sqrt(252)) if std_return > 0 else 0
    else:
        sharpe = 0

    # Recovery Factor
    total_profit = equity - 1.0
    recovery_factor = (
        total_profit / (max_drawndown / 100 * max_equity)
        if max_drawndown > 0
        else float("inf") if total_profit > 0 else 0
    )

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "win_rate": win_rate * 100,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_drawndown,
        "recovery_factor": recovery_factor,
        "final_equity": equity,
        "total_profit_pct": (equity - 1) * 100,
        "taker_fee": taker_fee * 100,
        "trade_log": trade_log[:20],  # First 20 trades for review
    }


def generate_filename(
    symbol: str, rsi_low: int, rsi_high: int, timeframe: str, version: int = 1
) -> str:
    """Generate standardized filename"""
    return f"{symbol}_RSI_{rsi_low}_{rsi_high}_{timeframe}_v{version}.json"


def run_full_backtest(
    symbol: str = "BTC/USDC",
    timeframes: List[str] = ["15m", "1h", "4h"],
    rsi_low: int = 30,
    rsi_high: int = 70,
    rsi_period: int = 14,
    period_days: int = 180,
    train_split: float = 0.70,
    taker_fee: float = 0.00035,
) -> Dict:
    """Run full backtest with train/test split"""

    results = {
        "metadata": {
            "symbol": symbol,
            "timeframes": timeframes,
            "rsi_low": rsi_low,
            "rsi_high": rsi_high,
            "rsi_period": rsi_period,
            "period_days": period_days,
            "train_split": train_split,
            "train_days": int(period_days * train_split),
            "test_days": int(period_days * (1 - train_split)),
            "taker_fee_pct": taker_fee * 100,
            "strategy": "RSI_CROSSOVER",
            "run_at": datetime.now().isoformat(),
            "param_hash": hashlib.md5(
                f"{rsi_low}_{rsi_high}_{timeframes}".encode()
            ).hexdigest()[:8],
        },
        "train_results": {},
        "test_results": {},
    }

    for tf in timeframes:
        print(f"\nFetching {period_days} days of {symbol} {tf} data...")
        # Map timeframe string to Binance interval
        tf_map = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
        binance_tf = tf_map.get(tf, "1h")

        raw_data = fetch_btc_usdc_data(binance_tf, period_days)

        if not raw_data or len(raw_data) < 100:
            print(f"Skipping {tf} - insufficient data ({len(raw_data)} candles)")
            continue

        # Sort by timestamp
        raw_data.sort(key=lambda x: x["timestamp"])

        # Split into train/test
        split_idx = int(len(raw_data) * train_split)
        train_data = raw_data[:split_idx]
        test_data = raw_data[split_idx:]

        print(
            f"  {tf}: {len(raw_data)} candles | Train: {len(train_data)} | Test: {len(test_data)}"
        )
        print(f"  Running {tf} backtest...")

        # Run on train (optimization data)
        train_result = run_backtest(
            train_data, rsi_low, rsi_high, rsi_period, taker_fee
        )
        results["train_results"][tf] = train_result

        # Run on test (out-of-sample)
        test_result = run_backtest(test_data, rsi_low, rsi_high, rsi_period, taker_fee)
        results["test_results"][tf] = test_result

    # Calculate overall metrics
    total_test_trades = sum(r["total_trades"] for r in results["test_results"].values())
    total_test_profit = sum(
        r["final_equity"] - 1.0 for r in results["test_results"].values()
    )

    avg_test_sharpe = sum(
        r["sharpe_ratio"] for r in results["test_results"].values()
    ) / len(timeframes)
    avg_test_mdd = sum(
        r["max_drawdown_pct"] for r in results["test_results"].values()
    ) / len(timeframes)
    avg_test_pf = sum(
        r["profit_factor"]
        for r in results["test_results"].values()
        if r["profit_factor"] < 100
    ) / len(timeframes)

    results["summary"] = {
        "total_test_trades": total_test_trades,
        "total_test_profit_pct": total_test_profit * 100,
        "avg_test_profit_factor": avg_test_pf,
        "avg_test_sharpe_ratio": avg_test_sharpe,
        "avg_test_max_drawdown_pct": avg_test_mdd,
        "recovery_factor": (
            total_test_profit / (avg_test_mdd / 100) if avg_test_mdd > 0 else 0
        ),
    }

    # Determine pass/fail
    pf_target = 1.75
    sharpe_target = 2.0
    mdd_target = 15.0
    rf_target = 3.0

    summary = results["summary"]
    notes = []

    if summary["avg_test_profit_factor"] < pf_target:
        notes.append(
            f"Failed: Profit Factor {summary['avg_test_profit_factor']:.2f} < {pf_target}"
        )
    if summary["avg_test_sharpe_ratio"] < sharpe_target:
        notes.append(
            f"Failed: Sharpe Ratio {summary['avg_test_sharpe_ratio']:.2f} < {sharpe_target}"
        )
    if summary["avg_test_max_drawdown_pct"] > mdd_target:
        notes.append(
            f"Failed: Max Drawdown {summary['avg_test_max_drawdown_pct']:.1f}% > {mdd_target}%"
        )
    if summary["recovery_factor"] < rf_target:
        notes.append(
            f"Failed: Recovery Factor {summary['recovery_factor']:.2f} < {rf_target}"
        )

    if not notes:
        notes.append("Passed: All metrics met targets")

    results["notes"] = notes
    results["metrics_goals"] = {
        "profit_factor": {
            "target": pf_target,
            "actual": summary["avg_test_profit_factor"],
        },
        "sharpe_ratio": {
            "target": sharpe_target,
            "actual": summary["avg_test_sharpe_ratio"],
        },
        "max_drawdown_pct": {
            "target": mdd_target,
            "actual": summary["avg_test_max_drawdown_pct"],
        },
        "recovery_factor": {"target": rf_target, "actual": summary["recovery_factor"]},
    }

    return results


if __name__ == "__main__":
    import sys

    # Default parameters
    symbol = "BTC/USDC"
    timeframes = ["15m", "1h", "4h"]
    rsi_low = 30
    rsi_high = 70
    period = 180
    train_ratio = 0.70
    taker_fee = 0.00035  # 0.035%

    print("=" * 60)
    print("Alpha Agent - RSI Reversal Backtest Engine")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"RSI Levels: {rsi_low} / {rsi_high}")
    print(f"Timeframes: {timeframes}")
    print(
        f"Period: {period} days ({int(period*train_ratio)} train / {int(period*(1-train_ratio))} test)"
    )
    print(f"Taker Fee: {taker_fee*100:.3f}%")
    print("=" * 60)

    results = run_full_backtest(
        symbol=symbol,
        timeframes=timeframes,
        rsi_low=rsi_low,
        rsi_high=rsi_high,
        period_days=period,
        train_split=train_ratio,
        taker_fee=taker_fee,
    )

    if "error" in results:
        print(f"Error: {results['error']}")
        sys.exit(1)

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    s = results["summary"]
    print(f"Total Test Trades: {s['total_test_trades']}")
    print(f"Total Test Profit: {s['total_test_profit_pct']:.2f}%")
    print(f"Profit Factor: {s['avg_test_profit_factor']:.2f} (target > 1.75)")
    print(f"Sharpe Ratio: {s['avg_test_sharpe_ratio']:.2f} (target > 2.0)")
    print(f"Max Drawdown: {s['avg_test_max_drawdown_pct']:.2f}% (target < 15%)")
    print(f"Recovery Factor: {s['recovery_factor']:.2f} (target > 3.0)")
    print("-" * 60)
    print("Notes:")
    for note in results["notes"]:
        print(f"  - {note}")

    print("\n" + "=" * 60)
    print("PER-TIMEFRAME RESULTS (Test Set)")
    print("=" * 60)
    for tf, r in results["test_results"].items():
        print(f"\n{tf}:")
        print(f"  Trades: {r['total_trades']}, Win Rate: {r['win_rate']:.1f}%")
        print(f"  Profit: {r['total_profit_pct']:.2f}%, PF: {r['profit_factor']:.2f}")
        print(f"  Sharpe: {r['sharpe_ratio']:.2f}, MDD: {r['max_drawdown_pct']:.2f}%")

    # Save to JSON
    version = 1
    filename = generate_filename("BTC", rsi_low, rsi_high, "4H", version)

    output_path = f"/home/yat121/.openclaw/workspace/projects/alpha-backtest/{filename}"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved to: {filename}")
