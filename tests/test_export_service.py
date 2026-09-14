# tests/test_export_service.py
from datetime import date
from app.extensions import db
from app.models.user import User
from app.models.internship import Internship
from app.services.export_service import ExportService
from app.services.log_service import LogService
from app.core.exceptions import NotFoundError
import pytest

def _mk(app, email="exp@t.com"):
    with app.app_context():
        u = User(email=email, password_hash="x", full_name="E")
        db.session.add(u); db.session.commit()
        ins = Internship(user_id=u.id, company_name="C", start_date=date(2024, 1, 1), end_date=date(2024, 6, 1), total_expected_days=10)
        db.session.add(ins); db.session.commit()
        return u.id, ins.id

def test_get_export_dicts_returns_owned_logs(app):
    uid, iid = _mk(app)
    with app.app_context():
        LogService.create_log(uid, iid, "T1", "hello world", date_override="2024-01-02")
        rows, truncated = ExportService.get_export_dicts(uid, iid)
        assert len(rows) == 1
        assert truncated is False
        assert rows[0]["raw_content"] == "hello world"
        assert rows[0]["internship_id"] == iid

def test_get_export_dicts_foreign_internship_404(app):
    uid, iid = _mk(app, email="a@t.com")
    uid2, _ = _mk(app, email="b@t.com")
    with app.app_context():
        with pytest.raises(NotFoundError):
            ExportService.get_export_dicts(uid2, iid)

def test_get_export_dicts_empty_without_internship(app):
    uid2, _ = _mk(app, email="empty@t.com")
    with app.app_context():
        from app.models.internship import Internship as _Ins
        _Ins.query.filter_by(user_id=uid2).delete()
        db.session.commit()
        rows, truncated = ExportService.get_export_dicts(uid2)
        assert rows == []
        assert truncated is False
