from datetime import date

from movistar_car.helpers import (
    itv_days_left,
    ms_to_date,
    ms_to_datetime,
    score_history,
    score_month,
)


def test_ms_to_datetime():
    assert ms_to_datetime(None) is None
    assert ms_to_datetime("bad") is None
    assert ms_to_datetime(0).year == 1970


def test_ms_to_date():
    assert ms_to_date(1742252400000) == date(2025, 3, 17)


def test_itv_days_left_negative_when_overdue():
    data = {"next_itv_date": 1742252400000}
    assert itv_days_left(data, today=date(2025, 3, 20)) == -3  # overdue
    assert itv_days_left(data, today=date(2025, 3, 10)) == 7  # still ahead
    assert itv_days_left({}, today=date(2025, 3, 10)) is None


def test_score_month_uses_current_month_and_ignores_minus_one():
    data = {"scoring_monthly": {"2026": [82, 94, 99, -1] + [-1] * 8}}
    assert score_month(data, today=date(2026, 3, 5)) == 99
    assert score_month(data, today=date(2026, 4, 5)) is None  # -1 = no data
    assert score_month(data, today=date(2027, 1, 5)) is None  # year missing
    assert score_month({}, today=date(2026, 3, 5)) is None


def test_score_history_drops_no_data_months():
    data = {"scoring_monthly": {"2026": [82, -1, 99] + [-1] * 9}}
    assert score_history(data) == {"2026-01": 82, "2026-03": 99}
    assert score_history({"scoring_monthly": "bad"}) is None
