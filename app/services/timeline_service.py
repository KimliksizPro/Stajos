"""TimelineService - Calendar/Timeline logic (Faz 4).

SSOT: architecture.md:225-226 (GET /api/v1/timeline)
"""

import calendar
import logging
from datetime import date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.daily_log import DailyLog
from app.models.internship import Internship
from app.utils.date_calculator import calculate_day_number, is_weekend
from app.utils.validators import parse_date

__all__ = ["TimelineService"]

logger = logging.getLogger(__name__)


class TimelineService:
    """Service Layer for timeline/calendar view (no HTTP logic, kurallar.md:4)."""

    @staticmethod
    def get_timeline(
        user_id: str,
        internship_id: str,
        year: Optional[int] = None,
        month: Optional[int] = None,
        start_date=None,
        end_date=None,
    ) -> Tuple[List[dict], dict]:
        """Build timeline grouped by date.

        Args:
            user_id: Current user id (from JWT).
            internship_id: Target internship id (required, ownership checked).
            year: Optional year (2000-2100), must be paired with month.
            month: Optional month (1-12), must be paired with year.
            start_date: Optional filter start (YYYY-MM-DD or date).
            end_date: Optional filter end (YYYY-MM-DD or date).

        Returns:
            (timeline, meta) where timeline is list of
            {date, day_number, is_weekend, logs: [to_dict...]}

        Raises:
            BadRequestError: Validation failures.
            NotFoundError: Internship not found / not owned.
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        if not internship_id:
            raise BadRequestError("internship_id zorunludur")

        # Ownership check mandatory (user_id filter)
        internship = Internship.query.filter_by(id=internship_id, user_id=user_id).first()
        if not internship:
            raise NotFoundError("Staj bulunamadı veya yetkiniz yok")

        # Normalize year/month (route already validates but keep guard)
        has_year = year is not None and str(year).strip() != ""
        has_month = month is not None and str(month).strip() != ""
        if has_year ^ has_month:
            raise BadRequestError("year ve month birlikte verilmeli")

        has_start = start_date is not None and str(start_date).strip() != "" if isinstance(start_date, str) else start_date is not None
        has_end = end_date is not None and str(end_date).strip() != "" if isinstance(end_date, str) else end_date is not None

        # Mutual exclusivity: calendar mode vs range mode
        if (has_year or has_month) and (has_start or has_end):
            raise BadRequestError("year/month ile start_date/end_date birlikte kullanılamaz")

        # Prepare range for calendar expansion — single parse cache (DRY)
        range_start: Optional[date] = None
        range_end: Optional[date] = None
        s_date: Optional[date] = None
        e_date: Optional[date] = None
        meta: dict = {}

        if has_year and has_month:
            # parse to int (route may already pass int)
            try:
                y = int(year)  # type: ignore[arg-type]
                m = int(month)  # type: ignore[arg-type]
            except (ValueError, TypeError):
                raise BadRequestError("year ve month sayı olmalı")
            if not 2000 <= y <= 2100:
                raise BadRequestError("year 2000-2100 arasında olmalı")
            if not 1 <= m <= 12:
                raise BadRequestError("month 1-12 arasında olmalı")
            last_day = calendar.monthrange(y, m)[1]
            range_start = date(y, m, 1)
            range_end = date(y, m, last_day)
            # keep normalized values for meta
            year = y
            month = m
        elif has_start or has_end:
            if has_start:
                s_date = parse_date(start_date, "start_date")
            if has_end:
                e_date = parse_date(end_date, "end_date")
            if s_date and e_date and s_date > e_date:
                raise BadRequestError("start_date end_date'den sonra olamaz")
            if s_date and e_date and (e_date - s_date).days + 1 > 366:
                raise BadRequestError("Tarih aralığı en fazla 366 gün olabilir")
            range_start = s_date
            range_end = e_date

        # Build query with N+1 guard (selectinload)
        query = DailyLog.query.filter_by(internship_id=internship_id)

        # Apply date filters — reuse single parse (s_date/e_date)
        if has_year and has_month:
            query = query.filter(DailyLog.date >= range_start, DailyLog.date <= range_end)  # type: ignore[arg-type]
        elif s_date is not None or e_date is not None:
            if s_date is not None and e_date is not None:
                query = query.filter(DailyLog.date >= s_date, DailyLog.date <= e_date)
            elif s_date is not None:
                query = query.filter(DailyLog.date >= s_date)
            elif e_date is not None:
                query = query.filter(DailyLog.date <= e_date)

        # N+1 guard: eager load M2M
        try:
            query = query.options(
                selectinload(DailyLog.technologies),
                selectinload(DailyLog.tags),
            )
            if hasattr(DailyLog, "topics"):
                query = query.options(selectinload(DailyLog.topics))
        except Exception as error:
            logger.warning("Failed to configure eager loading for timeline logs: %s", error)

        query = query.order_by(DailyLog.date.asc())
        logs: List[DailyLog] = query.all()

        # Group by date
        grouped: dict[date, List[DailyLog]] = {}
        for log in logs:
            grouped.setdefault(log.date, []).append(log)

        timeline: List[dict] = []

        # Determine if we should do calendar expansion (full month or full range with both dates)
        do_calendar = False
        if has_year and has_month:
            do_calendar = True
        elif s_date is not None and e_date is not None:
            do_calendar = True

        if do_calendar and range_start and range_end:
            # Calendar view: iterate every day
            cur = range_start
            while cur <= range_end:
                day_logs = grouped.get(cur, [])
                # day_number calculation (skip weekends, handle before start)
                try:
                    dn = calculate_day_number(internship.start_date, cur)
                except (ValueError, TypeError):
                    dn = 0
                # If logs exist, prefer stored day_number for first log (consistency)
                # but keep calculated for empty days
                if day_logs:
                    # use first log's day_number if available, else calculated
                    stored = day_logs[0].day_number
                    dn = stored if stored is not None else dn
                timeline.append(
                    {
                        "date": cur.isoformat(),
                        "day_number": dn,
                        "is_weekend": is_weekend(cur),
                        "logs": [l.to_dict() for l in day_logs],
                    }
                )
                cur += timedelta(days=1)

            if has_year and has_month:
                meta = {
                    "year": year,
                    "month": month,
                    "total_days": (range_end - range_start).days + 1,
                    "total_logs": len(logs),
                }
            else:
                meta = {
                    "start_date": range_start.isoformat(),
                    "end_date": range_end.isoformat(),
                    "total_days": (range_end - range_start).days + 1,
                    "total_logs": len(logs),
                }
        else:
            # Flat grouped view: only dates with logs (or empty if no logs)
            for d in sorted(grouped.keys()):
                day_logs = grouped[d]
                # day_number from first log
                dn = day_logs[0].day_number if day_logs else 0
                # fallback if dn is None
                if dn is None:
                    try:
                        dn = calculate_day_number(internship.start_date, d)
                    except Exception:
                        dn = 0
                timeline.append(
                    {
                        "date": d.isoformat(),
                        "day_number": dn,
                        "is_weekend": is_weekend(d),
                        "logs": [l.to_dict() for l in day_logs],
                    }
                )
            # meta for flat view — reuse cached dates
            if s_date is not None or e_date is not None:
                meta = {
                    "total_logs": len(logs),
                    "total_days": len(timeline),
                }
                if s_date is not None:
                    meta["start_date"] = s_date.isoformat()
                if e_date is not None:
                    meta["end_date"] = e_date.isoformat()
            else:
                meta = {"total_logs": len(logs), "total_days": len(timeline)}

        return timeline, meta
