# app/services/export_service.py
"""ExportService - read-only export fetch (Faz 6)."""
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.daily_log import DailyLog
from app.models.internship import Internship

__all__ = ["ExportService", "EXPORT_MAX_ROWS"]

EXPORT_MAX_ROWS = 1000

class ExportService:
    @staticmethod
    def get_export_dicts(user_id: str, internship_id: str | None = None) -> tuple[list[dict], bool]:
        """Fetch owned logs as dicts with truncation flag.

        Returns:
            (rows, truncated): rows en fazla EXPORT_MAX_ROWS satir icerir;
            truncated True ise cikti limit nedeniyle kirpilmistir.
        """
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
                return [], False
        # limit+1 cekilerek kirpma tespiti yapilir (ekstra count sorgusu yok).
        fetched = (
            DailyLog.query.filter(DailyLog.internship_id.in_(ids))
            .order_by(DailyLog.date.asc(), DailyLog.id.asc())
            .limit(EXPORT_MAX_ROWS + 1)
            .all()
        )
        truncated = len(fetched) > EXPORT_MAX_ROWS
        rows = [l.to_dict() for l in fetched[:EXPORT_MAX_ROWS]]
        return rows, truncated
