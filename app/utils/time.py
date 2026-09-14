"""Time utilities for StajOS - centralized UTC helpers.

SSOT: docs/kurallar.md:10.3, architecture.md:10.3
"""

from datetime import datetime, timezone
from typing import Optional

__all__ = ["utcnow", "iso_or_none"]


def utcnow() -> datetime:
    """Return current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


def iso_or_none(value) -> Optional[str]:
    """Return ISO string if value else None (DRY helper)."""
    return value.isoformat() if value else None
