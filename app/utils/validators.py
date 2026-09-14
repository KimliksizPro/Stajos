"""Validators utility for StajOS - centralized date/time parsing.

SSOT: docs/kurallar.md:38, architecture.md:4,10.1
"""

from datetime import date, datetime, time, timezone
from typing import Optional

from app.core.exceptions import BadRequestError

__all__ = ["parse_date", "parse_time", "today_utc", "normalize_name"]


def parse_date(value, field_name: str) -> date:
    """Parse YYYY-MM-DD string or return date object. Raises BadRequestError on failure."""
    if value is None:
        raise BadRequestError(f"{field_name} zorunludur")
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise BadRequestError(f"{field_name} zorunludur")
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise BadRequestError(f"{field_name} geçerli bir tarih olmalı (YYYY-MM-DD)")
    raise BadRequestError(f"{field_name} geçersiz format")


def parse_time(value, field_name: str) -> Optional[time]:
    """Parse HH:MM or HH:MM:SS string to time object. Returns None if empty/None.

    Raises BadRequestError on invalid format.
    """
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        # Try HH:MM:SS then HH:MM
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
        raise BadRequestError(f"{field_name} geçerli bir saat olmalı (HH:MM veya HH:MM:SS)")
    raise BadRequestError(f"{field_name} geçersiz format")


def today_utc() -> date:
    """Return today's date in UTC."""
    return datetime.now(timezone.utc).date()


def normalize_name(name: str) -> str:
    """Normalize name to stripped lowercase (DRY helper)."""
    return (name or "").strip().lower()
