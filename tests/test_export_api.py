# tests/test_export_api.py
from datetime import date
from flask_jwt_extended import create_access_token
from app.extensions import db
from app.models.user import User
from app.models.internship import Internship
from app.services.log_service import LogService

def _setup(app):
    with app.app_context():
        u = User(email="api-exp@t.com", password_hash="x", full_name="E")
        db.session.add(u); db.session.commit()
        ins = Internship(user_id=u.id, company_name="C", start_date=date(2024, 1, 1), end_date=date(2024, 6, 1), total_expected_days=10)
        db.session.add(ins); db.session.commit()
        LogService.create_log(u.id, ins.id, "T1", "csv içerik", date_override="2024-01-02")
        tok = create_access_token(identity=u.id)
        return tok, ins.id

def test_export_json_envelope(app, client):
    tok, iid = _setup(app)
    r = client.get(f"/api/v1/export/json?internship_id={iid}", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json["success"] is True
    assert isinstance(r.json["data"], list)
    assert r.json["data"][0]["raw_content"] == "csv içerik"

def test_export_csv_download(app, client):
    tok, iid = _setup(app)
    r = client.get(f"/api/v1/export/csv?internship_id={iid}", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert "text/csv" in r.content_type
    assert "attachment" in r.headers.get("Content-Disposition", "")
    assert "raw_content" in r.text.splitlines()[0]

def test_export_requires_auth(client):
    r = client.get("/api/v1/export/json")
    assert r.status_code == 401
    assert r.json["success"] is False

def test_export_json_meta_reports_limit(app, client):
    tok, iid = _setup(app)
    r = client.get(f"/api/v1/export/json?internship_id={iid}", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json["meta"] == {"total": 1, "limit": 1000, "truncated": False}

def test_export_json_foreign_internship_404(app, client):
    tok_a, iid_a = _setup(app)
    with app.app_context():
        u2 = User(email="other@t.com", password_hash="x", full_name="O")
        db.session.add(u2); db.session.commit()
        ins2 = Internship(user_id=u2.id, company_name="C2", start_date=date(2024, 1, 1), end_date=date(2024, 6, 1), total_expected_days=10)
        db.session.add(ins2); db.session.commit()
        tok_b = create_access_token(identity=u2.id)
    r = client.get(f"/api/v1/export/json?internship_id={iid_a}", headers={"Authorization": f"Bearer {tok_b}"})
    assert r.status_code == 404
    assert r.json["success"] is False

def test_export_json_without_filter_returns_all(app, client):
    tok, iid = _setup(app)
    r = client.get("/api/v1/export/json", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json["success"] is True
    assert len(r.json["data"]) == 1
    assert r.json["meta"]["truncated"] is False
