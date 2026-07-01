"""Display formatting helpers — money, percentages, dates."""

import pandas as pd


def money(value, decimals: int = 2) -> str:
    """Format a number as USD currency. Handles None/NaN gracefully."""
    if value is None or pd.isna(value):
        return "—"
    return f"${value:,.{decimals}f}"


def money_short(value) -> str:
    """Compact money format for KPI cards: $1.2K, $4.5M, etc."""
    if value is None or pd.isna(value):
        return "—"
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000: return f"{sign}${abs_val / 1_000_000:.1f}M"
    if abs_val >= 1_000:     return f"{sign}${abs_val / 1_000:.1f}K"
    return f"{sign}${abs_val:.0f}"


def pct(value, decimals: int = 1) -> str:
    """Format a number as a percentage string."""
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{decimals}f}%"


def delta_money(current, previous) -> str | None:
    """
    Compute a delta string for st.metric().
    Returns None if either value is missing.
    """
    if current is None or previous is None or pd.isna(current) or pd.isna(previous):
        return None
    diff = current - previous
    return f"{'+' if diff >= 0 else ''}{money(diff)}"


def month_label(year_month: str) -> str:
    """Convert '2026-04' to 'April 2026' for chart titles."""
    return pd.to_datetime(year_month).strftime("%B %Y")
