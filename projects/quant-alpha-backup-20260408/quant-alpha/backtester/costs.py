"""Transaction cost model for IBKR futures trading."""


def compute_costs(size: int) -> float:
    """Return total round‑trip cost for given contract size.

    Args:
        size: number of contracts traded (positive for long, negative for short).
    """
    cost_per_contract = 1.10
    return abs(size) * cost_per_contract


def apply_costs(df):
    """Apply transaction costs to DataFrame.
    Assumes a column 'signal' indicating number of contracts traded.
    """
    if "signal" not in df.columns:
        df["signal"] = 0
    df["cost"] = df["signal"].apply(compute_costs)
    # subtract costs from returns later; here just store
    return df
