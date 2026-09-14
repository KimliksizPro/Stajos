# app/services/export_service.py
"""ExportService - read-only export fetch (Faz 6)."""
from sqlalchemy.orm import selectinload
from app.core.exceptions import BadRequestError, NotFoundError
from app.extensions import db
from app.models.daily_log import DailyLog
from app.models.internship import Internship

__all__ = ["ExportService"]

_MAX_EXPORT_ROWS = 1000

class ExportService:
    @staticmethod
    def get_export_dicts(user_id: str, internship_id: str | None = None) -> list[dict]:
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        q = Internship.query.filter_by(user_id=user_id)
        if internship_id:
            internship = q.filter_by(id=internship_id).first()
            if not internship:
                raise NotFoundError("Staj bulunamadı veya yetkiniz yok")
            ids = [internship.id]
        else:
            ids = [i.id for i in q.all()]
            if not ids:
                return []
        query = (
            DailyLog.query.filter(DailyLog.internship_id.in_(ids))
            .order_by(DailyLog.date.asc())
            .limit(_MAX_EXPORT_ROWS)
        )
        try:
            query = query.options(selectinload(DailyLog.technologies), selectinload(DailyLog.tags))
        except Exception:
            pass
        return [l.to_dict() for l in query.all()]
