"""Date/time calculation helpers for StajOS (Faz 2 - Core Domain).

SSOT: architecture.md:253-259 (calculate_day_number)
"""

from datetime import date, time, datetime, timedelta
from typing import Optional

__all__ = ["calculate_day_number", "calculate_duration_minutes", "is_weekend"]


def is_weekend(d: date) -> bool:
    """Return True if date falls on Saturday (5) or Sunday (6).

    Args:
        d: Date to check.

    Returns:
        True if weekend, False otherwise.
    """
    return d.weekday() >= 5


def calculate_day_number(start_date: date, target_date: date) -> int:
    """Calculate internship day number skipping weekends.

    Counts weekdays (Mon-Fri) from start_date to target_date inclusive.
    start_date itself is day 1 IF it is a weekday; if start_date is a
    weekend it is not counted (only weekdays are counted).

    Args:
        start_date: Internship start date.
        target_date: Date to calculate day number for (usually today).

    Returns:
        Day number (1-indexed weekday count).

    Raises:
        ValueError: If target_date < start_date.
        TypeError: If inputs are not date objects.
    """
    if not isinstance(start_date, date) or not isinstance(target_date, date):
        raise TypeError("start_date and target_date must be date objects")
    # Guard: datetime is subclass of date - normalize to date
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(target_date, datetime):
        target_date = target_date.date()

    if target_date < start_date:
        raise ValueError("target_date cannot be earlier than start_date")

    count = 0
    current = start_date
    delta = timedelta(days=1)
    while current <= target_date:
        if not is_weekend(current):
            count += 1
        current += delta

    # If start_date was weekend and target_date is same weekend day,
    # count will be 0. Caller should treat 0 as no valid business day yet.
    # For consistency with spec (starts at 1), if count == 0 but
    # target_date itself is weekend, the number is still 0; service layer
    # may decide to reject or keep 0. If you want at least 0, return count.
    return count


def calculate_duration_minutes(
    start_time: Optional[time], end_time: Optional[time]
) -> Optional[int]:
    """Calculate duration in minutes between two time objects.

    Args:
        start_time: Start time (or None).
        end_time: End time (or None).

    Returns:
        Duration in minutes as int, or None if either input is None.

    Raises:
        ValueError: If end_time <= start_time.
        TypeError: If inputs are not time objects (when not None).
    """
    if start_time is None or end_time is None:
        return None

    if not isinstance(start_time, time) or not isinstance(end_time, time):
        raise TypeError("start_time and end_time must be time objects or None")

    # Convert to minutes since midnight for comparison
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    # Include seconds if present (round down)
    # Seconds are not critical but handle precisely
    start_seconds = start_time.second
    end_seconds = end_time.second

    # Use total seconds for precise duration
    start_total = start_minutes * 60 + start_seconds
    end_total = end_minutes * 60 + end_seconds

    if end_total <= start_total:
        raise ValueError("end_time must be after start_time")

    duration = (end_total - start_total) // 60
    # If seconds remainder exists, we floor to minutes (consistent)
    # If exact minute calculation without seconds preferred: end_minutes - start_minutes
    return int(duration)
