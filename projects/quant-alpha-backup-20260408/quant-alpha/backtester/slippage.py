"""Slippage model for futures trading.

Provides a simple volume‑based slippage estimate and an apply function.
"""


def compute_slippage(
    volume: float, avg_volume_20: float, urgency: float = 1.0
) -> float:
    """Return slippage in basis points.

    Args:
        volume: trade volume (contracts) for the bar.
        avg_volume_20: 20‑day average volume for the instrument.
        urgency: multiplier indicating how aggressive the order is (default 1.0).
    """
    participation = min(0.05, volume / (avg_volume_20 * 100))
    slippage_bps = participation * urgency * 5
    return slippage_bps


def apply_slippage(df):
    """Apply slippage to a DataFrame of trades.
    Assumes df has 'volume' column and uses 20‑day SMA of volume.
    Returns df with a new column 'slippage' (as price adjustment).
    """
    if "volume" not in df.columns:
        df["volume"] = 0
    df["avg_volume_20"] = df["volume"].rolling(window=20, min_periods=1).mean()
    df["slippage_bps"] = df.apply(
        lambda row: compute_slippage(row["volume"], row["avg_volume_20"]), axis=1
    )
    # Convert bps to price impact assuming price ~ close
    df["slippage"] = df["close"] * df["slippage_bps"] / 10000
    return df
