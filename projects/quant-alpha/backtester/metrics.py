"""Compute performance metrics from trades and equity curve."""

import numpy as np


def compute_metrics(trades, equity, include_detail=False):
    if not trades or not equity:
        return {
            "total_return": 0,
            "cagr": 0,
            "sharpe": 0,
            "sortino": 0,
            "max_drawdown": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "total_trades": 0,
            "cost_impact_pct": 0,
            "net_return": 0,
            "gross_return": 0,
            "avg_trade_pnl": 0,
            "in_sample": {},
            "out_sample": {},
        }

    pnls = [t.get("pnl", 0) for t in trades if t.get("pnl") is not None]
    gross = sum(pnls) + sum(t.get("costs", 0) for t in trades)
    total_costs = sum(t.get("costs", 0) for t in trades)
    net = gross - total_costs
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # Equity curve metrics
    eq = np.array(equity)
    running_max = np.maximum.accumulate(eq)
    drawdown = (eq - running_max) / running_max * 100
    max_dd = abs(drawdown.min())

    # Annualized metrics (252 trading days)
    days = max(1, len(eq))
    years = days / 252
    cagr = (
        ((eq[-1] / eq[0]) ** (1 / years) - 1) * 100 if eq[-1] > 0 and eq[0] > 0 else 0
    )

    returns = np.diff(eq) / eq[:-1]
    returns = returns[np.isfinite(returns)]
    if len(returns) > 0:
        sharpe = (
            (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        )
        downside = returns[returns < 0]
        sortino = (
            (returns.mean() / downside.std() * np.sqrt(252))
            if len(downside) > 0 and downside.std() > 0
            else 0
        )
    else:
        sharpe = sortino = 0

    total_return = (eq[-1] / eq[0] - 1) * 100 if eq[0] > 0 else 0
    win_rate = len(wins) / len(pnls) * 100 if pnls else 0
    profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
    cost_impact = abs(total_costs / gross * 100) if gross != 0 else 0
    avg_pnl = np.mean(pnls) if pnls else 0

    result = {
        "total_return": round(total_return, 2),
        "cagr": round(cagr, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "max_drawdown": round(max_dd, 2),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "total_trades": len(pnls),
        "cost_impact_pct": round(cost_impact, 2),
        "net_return": round(net, 2),
        "gross_return": round(gross, 2),
        "avg_trade_pnl": round(avg_pnl, 2),
        "gross_profit": round(sum(wins), 2) if wins else 0,
        "gross_loss": round(sum(losses), 2) if losses else 0,
        "in_sample": {},
        "out_sample": {},
    }
    return result
