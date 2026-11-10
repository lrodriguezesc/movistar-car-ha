"""Pure helper functions (no Home Assistant imports, so they are easy to test)."""

from __future__ import annotations

from datetime import date, datetime, timezone


def ms_to_datetime(value) -> datetime | None:
    """Convert a millisecond Unix timestamp to an aware UTC datetime."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def ms_to_date(value) -> date | None:
    dt = ms_to_datetime(value)
    return dt.date() if dt else None


def itv_days_left(data: dict, today: date | None = None) -> int | None:
    """Days until the next ITV. Negative means overdue."""
    due = ms_to_date(data.get("next_itv_date"))
    if due is None:
        return None
    return (due - (today or date.today())).days


def score_month(data: dict, today: date | None = None):
    """Driving score of the current month. The API uses -1 for "no data"."""
    scores = data.get("scoring_monthly")
    if not isinstance(scores, dict):
        return None
    today = today or date.today()
    months = scores.get(str(today.year)) or []
    value = months[today.month - 1] if len(months) >= today.month else None
    return value if value is not None and value >= 0 else None


def score_history(data: dict) -> dict | None:
    """Monthly scores as {"YYYY-MM": score}, without the "no data" months."""
    scores = data.get("scoring_monthly")
    if not isinstance(scores, dict):
        return None
    return {
        f"{year}-{i + 1:02d}": v
        for year, months in scores.items()
        for i, v in enumerate(months)
        if v is not None and v >= 0
    }
