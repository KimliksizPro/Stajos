"""StatsService - Dashboard statistics (Faz 4).

SSOT: architecture.md:224-225 (GET /api/v1/dashboard/stats)
"""

import logging
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.extensions import db
from app.models.daily_log import DailyLog
from app.models.internship import Internship, InternshipStatus
from app.models.technology import Technology, log_technologies
from app.models.topic import Topic, log_topics
from app.utils.time import iso_or_none
from app.utils.validators import today_utc

__all__ = ["StatsService"]

logger = logging.getLogger(__name__)


class StatsService:
    """Service Layer for dashboard stats (no HTTP logic, kurallar.md:4)."""

    @staticmethod
    def get_dashboard_stats(user_id: str, internship_id: Optional[str] = None) -> Dict:
        """Build dashboard statistics.

        Args:
            user_id: Current user id (from JWT).
            internship_id: Optional internship id to filter by.
                If provided, only that internship's logs are counted (ownership checked).
                If None, all user's internships are considered.

        Returns:
            Dict with keys:
                total_internships, active_internship, total_logs, total_days,
                total_duration_minutes, average_duration, logs_per_month,
                top_technologies, top_topics, recent_logs

        Raises:
            BadRequestError: Missing user_id.
            NotFoundError: Internship not found / not owned when internship_id given.
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")

        # Normalize internship_id (empty string -> None)
        if internship_id is not None:
            internship_id = str(internship_id).strip() or None

        # Ownership check when internship_id provided
        target_internship: Optional[Internship] = None
        if internship_id:
            target_internship = Internship.query.filter_by(id=internship_id, user_id=user_id).first()
            if not target_internship:
                raise NotFoundError("Staj bulunamadı veya yetkiniz yok")
            internship_ids = [target_internship.id]
        else:
            # All internships for user
            internships = Internship.query.filter_by(user_id=user_id).all()
            internship_ids = [i.id for i in internships]

        # total_internships - efficient count
        total_internships = db.session.query(func.count(Internship.id)).filter(Internship.user_id == user_id).scalar() or 0

        # active_internship - single query, no N+1
        active = Internship.query.filter_by(user_id=user_id, status=InternshipStatus.ACTIVE).first()
        if active:
            active_internship = {
                "id": active.id,
                "company_name": active.company_name,
                "status": active.status.value if hasattr(active.status, "value") else str(active.status),
                "start_date": iso_or_none(active.start_date),
                "end_date": iso_or_none(active.end_date),
            }
        else:
            active_internship = None

        # Early return when no internships (avoid IN () empty query)
        if not internship_ids:
            return {
                "total_internships": int(total_internships),
                "active_internship": active_internship,
                "total_logs": 0,
                "total_days": 0,
                "total_duration_minutes": 0,
                "average_duration": 0,
                "logs_per_month": StatsService._build_logs_per_month({}, today_utc()),
                "top_technologies": [],
                "top_topics": [],
                "recent_logs": [],
            }

        # total_logs - efficient func.count
        total_logs = (
            db.session.query(func.count(DailyLog.id))
            .filter(DailyLog.internship_id.in_(internship_ids))
            .scalar()
            or 0
        )

        # total_days - distinct dates
        total_days = (
            db.session.query(func.count(func.distinct(DailyLog.date)))
            .filter(DailyLog.internship_id.in_(internship_ids))
            .scalar()
            or 0
        )

        # total_duration_minutes - coalesce sum
        total_duration_minutes = (
            db.session.query(func.coalesce(func.sum(DailyLog.duration_minutes), 0))
            .filter(DailyLog.internship_id.in_(internship_ids))
            .scalar()
            or 0
        )
        total_duration_minutes = int(total_duration_minutes)

        # average_duration
        average_duration = round(total_duration_minutes / total_logs, 2) if total_logs else 0

        # logs_per_month (last 6 months) - efficient group by
        logs_per_month = StatsService._query_logs_per_month(internship_ids)

        # top_technologies - efficient join + group by, no N+1
        top_technologies = StatsService._query_top_technologies(internship_ids)

        # top_topics - efficient join + group by scoped to user's internships
        top_topics = StatsService._query_top_topics(user_id, internship_ids)

        # recent_logs - last 5, N+1 guard with selectinload
        recent_logs = StatsService._query_recent_logs(internship_ids)

        return {
            "total_internships": int(total_internships),
            "active_internship": active_internship,
            "total_logs": int(total_logs),
            "total_days": int(total_days),
            "total_duration_minutes": int(total_duration_minutes),
            "average_duration": average_duration,
            "logs_per_month": logs_per_month,
            "top_technologies": top_technologies,
            "top_topics": top_topics,
            "recent_logs": recent_logs,
        }

    @staticmethod
    def _build_logs_per_month(rows_map: Dict[str, int], today: date) -> List[Dict]:
        """Build 6-month list filling missing months with 0."""
        months: List[str] = []
        y = today.year
        m = today.month
        for i in range(5, -1, -1):
            month = m - i
            year = y
            while month <= 0:
                month += 12
                year -= 1
            while month > 12:
                month -= 12
                year += 1
            months.append(f"{year:04d}-{month:02d}")
        result = []
        for mon in months:
            result.append({"month": mon, "count": int(rows_map.get(mon, 0))})
        return result

    @staticmethod
    def _query_logs_per_month(internship_ids: List[str]) -> List[Dict]:
        today = today_utc()
        # first day of 5 months ago
        y = today.year
        m = today.month
        start_month = m - 5
        start_year = y
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        start_date = date(start_year, start_month, 1)

        # Build month expression dialect-aware (SA2 compatible)
        try:
            bind = db.session.get_bind()
            dialect = bind.dialect.name if bind is not None else "sqlite"
        except Exception:
            try:
                engine = db.get_engine()  # Flask-SQLAlchemy fallback
                dialect = engine.dialect.name if engine is not None else "sqlite"
            except Exception:
                dialect = "sqlite"

        if dialect == "postgresql":
            month_expr = func.to_char(DailyLog.date, "YYYY-MM")
        else:
            # sqlite / fallback
            month_expr = func.strftime("%Y-%m", DailyLog.date)

        rows = (
            db.session.query(month_expr.label("month"), func.count(DailyLog.id).label("cnt"))
            .filter(DailyLog.internship_id.in_(internship_ids), DailyLog.date >= start_date)
            .group_by(month_expr)
            .order_by(month_expr)
            .all()
        )
        rows_map = {r.month: int(r.cnt) for r in rows if r.month}
        return StatsService._build_logs_per_month(rows_map, today)

    @staticmethod
    def _query_top_technologies(internship_ids: List[str]) -> List[Dict]:
        rows = (
            db.session.query(
                Technology.id,
                Technology.name,
                Technology.normalized_name,
                func.count(log_technologies.c.log_id).label("cnt"),
            )
            .join(log_technologies, Technology.id == log_technologies.c.technology_id)
            .join(DailyLog, DailyLog.id == log_technologies.c.log_id)
            .filter(DailyLog.internship_id.in_(internship_ids))
            .group_by(Technology.id, Technology.name, Technology.normalized_name)
            .order_by(func.count(log_technologies.c.log_id).desc())
            .limit(5)
            .all()
        )
        result = []
        for r in rows:
            result.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "normalized_name": r.normalized_name,
                    "count": int(r.cnt),
                }
            )
        return result

    @staticmethod
    def _query_top_topics(user_id: str, internship_ids: List[str]) -> List[Dict]:
        # Scoped to internship_ids via log_topics -> daily_logs
        rows = (
            db.session.query(
                Topic.id,
                Topic.name,
                Topic.normalized_name,
                Topic.usage_count,
                func.count(log_topics.c.log_id).label("cnt"),
            )
            .join(log_topics, Topic.id == log_topics.c.topic_id)
            .join(DailyLog, DailyLog.id == log_topics.c.log_id)
            .filter(Topic.user_id == user_id, DailyLog.internship_id.in_(internship_ids))
            .group_by(Topic.id, Topic.name, Topic.normalized_name, Topic.usage_count)
            .order_by(func.count(log_topics.c.log_id).desc(), Topic.usage_count.desc())
            .limit(5)
            .all()
        )
        result = []
        for r in rows:
            result.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "normalized_name": r.normalized_name,
                    "usage_count": int(r.usage_count or 0),
                    "count": int(r.cnt),
                }
            )
        # Fallback if no linked logs but user has topics with usage_count
        if not result:
            topics = (
                Topic.query.filter_by(user_id=user_id)
                .order_by(Topic.usage_count.desc())
                .limit(5)
                .all()
            )
            for t in topics:
                if t.usage_count and t.usage_count > 0:
                    result.append(
                        {
                            "id": t.id,
                            "name": t.name,
                            "normalized_name": t.normalized_name,
                            "usage_count": int(t.usage_count or 0),
                            "count": int(t.usage_count or 0),
                        }
                    )
        return result

    @staticmethod
    def _query_recent_logs(internship_ids: List[str]) -> List[Dict]:
        query = DailyLog.query.filter(DailyLog.internship_id.in_(internship_ids))
        # N+1 guard
        try:
            query = query.options(
                selectinload(DailyLog.technologies),
                selectinload(DailyLog.tags),
            )
            if hasattr(DailyLog, "topics"):
                query = query.options(selectinload(DailyLog.topics))
        except Exception as error:
            logger.warning("Failed to configure eager loading for recent logs: %s", error)
        logs = query.order_by(DailyLog.date.desc(), DailyLog.created_at.desc()).limit(5).all()
        return [l.to_dict() for l in logs]
