# tests/test_date_calculator_unit.py
from datetime import date, time
import pytest
from app.utils.date_calculator import calculate_day_number, calculate_duration_minutes, is_weekend

def test_day_number_skips_weekend():
    # 2024-01-01 Pazartesi
    assert calculate_day_number(date(2024, 1, 1), date(2024, 1, 1)) == 1
    assert calculate_day_number(date(2024, 1, 1), date(2024, 1, 5)) == 5
    assert calculate_day_number(date(2024, 1, 1), date(2024, 1, 8)) == 6  # Pazartesi

def test_day_number_rejects_target_before_start():
    with pytest.raises(ValueError):
        calculate_day_number(date(2024, 1, 5), date(2024, 1, 1))

def test_duration_floor_and_validation():
    assert calculate_duration_minutes(time(9, 0), time(17, 30)) == 510
    assert calculate_duration_minutes(time(9, 0, 30), time(9, 1, 29)) == 0  # floor
    assert calculate_duration_minutes(None, time(9, 0)) is None
    with pytest.raises(ValueError):
        calculate_duration_minutes(time(10, 0), time(9, 0))

def test_is_weekend():
    assert is_weekend(date(2024, 1, 6)) is True   # Cumartesi
    assert is_weekend(date(2024, 1, 7)) is True   # Pazar
    assert is_weekend(date(2024, 1, 8)) is False  # Pazartesi
