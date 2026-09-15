# Faz 6 Export Docs Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faz 6'yı kapat: JSON/CSV export endpointleri, bağımlılık-free OpenAPI/Swagger docs ve eksik unit testler.

**Architecture:** Service layer'da `ExportService` (ownership + fetch), pure CSV/JSON helper'lar `app/utils/exporters.py` içinde stdlib ile, thin Blueprint `app/api/v1/export_routes.py`, docs için statik OpenAPI dict + Swagger UI (`app/api/v1/docs_routes.py`). Yeni DB migration yok.

**Tech Stack:** Python 3.11+, Flask 3.x, SQLAlchemy 2.0, pytest 8.4.0, stdlib `csv`/`io`/`json`. Yeni pip bağımlılığı yok.

## Global Constraints

- İş mantığı service layer'da kalır; Blueprint/controller yalnız request, service ve response akışını yönetir.
- Tüm API yanıtları `success`, `data`, `meta`, `errors` alanlı standart envelope kullanır (CSV dosya indirme hariç — `text/csv` döner).
- Kimlik doğrulama JWT ile yapılır; servis sorgularında ownership `current_user.id` ile doğrulanır; IDOR'a izin verilmez.
- `raw_content` değişmez kullanıcı verisidir; export sadece okur, asla yazmaz.
- Route'lar slash farkında `308` üretmez; `strict_slashes=False` davranışı korunur.
- `raw_content` en fazla 50000 kuralı gevşetilmez; export'ta limit/pagination korunur (max 1000 satır default).
- En küçük doğru değişiklik; ilgisiz refactor yok.
- Secret/token/`.env`/credential kod/test/log/commit'e konmaz.
- Migration gerekiyorsa dosya üretilir ve disposable DB'de `upgrade/current/check` yapılır (bu planda migration beklenmiyor).

---

### Task 1: Exporter pure helpers (CSV/JSON)

**Files:**
- Modify: `app/utils/exporters.py:1-2`
- Test: `tests/test_exporters_unit.py`

**Interfaces:**
- Consumes: `DailyLog.to_dict()` dict'leri (`app/models/daily_log.py:65-91`)
- Produces: `logs_to_csv_rows(log_dicts: list[dict]) -> str`, `CSV_COLUMNS: list[str]`, `logs_to_jsonable(log_dicts: list[dict]) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exporters_unit.py
from app.utils.exporters import CSV_COLUMNS, logs_to_csv_rows

def test_csv_columns_stable():
    assert CSV_COLUMNS == ["id", "internship_id", "date", "day_number", "title", "raw_content", "ai_status", "duration_minutes", "start_time", "end_time", "created_at"]

def test_logs_to_csv_rows_escapes_commas_and_quotes():
    rows = logs_to_csv_rows([{"id": "1", "internship_id": "i1", "date": "2024-01-02", "day_number": 1, "title": 'a,"b', "raw_content": "x\ny", "ai_status": "PENDING", "duration_minutes": 60, "start_time": "09:00", "end_time": "10:00", "created_at": "2024-01-02T00:00:00"}])
    assert '"a,""b"' in rows
    assert rows.splitlines()[0] == ",".join(CSV_COLUMNS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_exporters_unit.py -v`
Expected: FAIL with "ImportError" / "cannot import name" (exporters.py şu an boş, `__all__ = []`).

- [ ] **Step 3: Write minimal implementation**

```python
# app/utils/exporters.py
"""CSV/JSON export helpers (Faz 6). Pure functions, no DB/HTTP."""
import csv
import io

CSV_COLUMNS = ["id", "internship_id", "date", "day_number", "title", "raw_content", "ai_status", "duration_minutes", "start_time", "end_time", "created_at"]

__all__ = ["CSV_COLUMNS", "logs_to_csv_rows", "logs_to_jsonable"]

def logs_to_jsonable(log_dicts):
    return [dict(d) for d in (log_dicts or [])]

def logs_to_csv_rows(log_dicts):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for d in (log_dicts or []):
        w.writerow({c: d.get(c, "") if d.get(c, "") is not None else "" for c in CSV_COLUMNS})
    return buf.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_exporters_unit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/utils/exporters.py tests/test_exporters_unit.py
git commit -m "feat: add export csv/json helpers"
```

---

### Task 2: ExportService (ownership + fetch)

**Files:**
- Create: `app/services/export_service.py`
- Test: `tests/test_export_service.py`

**Interfaces:**
- Consumes: `LogService.get_logs` pattern, `DailyLog` (`app/models/daily_log.py`), `Internship` (`app/models/internship.py`), `exporters.logs_to_*`
- Produces: `ExportService.get_export_dicts(user_id: str, internship_id: str | None) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
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
        rows = ExportService.get_export_dicts(uid, iid)
        assert len(rows) == 1
        assert rows[0]["raw_content"] == "hello world"
        assert rows[0]["internship_id"] == iid

def test_get_export_dicts_foreign_internship_404(app):
    uid, iid = _mk(app, email="a@t.com")
    uid2, _ = _mk(app, email="b@t.com")
    with app.app_context():
        with pytest.raises(NotFoundError):
            ExportService.get_export_dicts(uid2, iid)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_export_service.py -v`
Expected: FAIL with "No module named app.services.export_service"

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_export_service.py tests/test_exporters_unit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/export_service.py tests/test_export_service.py
git commit -m "feat: add export service with ownership"
```

---

### Task 3: Export routes (JSON envelope + CSV download)

**Files:**
- Create: `app/api/v1/export_routes.py`
- Modify: `app/__init__.py:60-72` (blueprint register)
- Test: `tests/test_export_api.py`

**Interfaces:**
- Consumes: `ExportService.get_export_dicts` (Task 2), `logs_to_csv_rows` (Task 1), `success_response` (`app/core/response.py:8`)
- Produces: `GET /api/v1/export/json`, `GET /api/v1/export/csv` (JWT, `?internship_id=` opsiyonel)

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_export_api.py -v`
Expected: FAIL with 404 ("Endpoint not found") — route henüz yok.

- [ ] **Step 3: Write minimal implementation**

```python
# app/api/v1/export_routes.py
from flask import Blueprint, Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.core.response import success_response
from app.services.export_service import ExportService
from app.utils.exporters import logs_to_csv_rows

export_bp = Blueprint("export", __name__, url_prefix="/api/v1/export")

__all__ = ["export_bp"]

@export_bp.route("/json", methods=["GET"], strict_slashes=False)
@jwt_required()
def export_json():
    user_id = get_jwt_identity()
    internship_id = request.args.get("internship_id") or None
    rows = ExportService.get_export_dicts(user_id, internship_id)
    return success_response(data=rows, meta={"total": len(rows)}, status=200)

@export_bp.route("/csv", methods=["GET"], strict_slashes=False)
@jwt_required()
def export_csv():
    user_id = get_jwt_identity()
    internship_id = request.args.get("internship_id") or None
    rows = ExportService.get_export_dicts(user_id, internship_id)
    csv_text = logs_to_csv_rows(rows)
    return Response(csv_text, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=stajos-export.csv"})
```

Register in `app/__init__.py` (mevcut importların altına ekle):

```python
from app.api.v1.export_routes import export_bp
app.register_blueprint(export_bp)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_export_api.py tests/test_export_service.py tests/test_exporters_unit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/export_routes.py app/__init__.py tests/test_export_api.py
git commit -m "feat: add json csv export endpoints"
```

---

### Task 4: OpenAPI/Swagger docs (bağımlılık-free)

**Files:**
- Create: `app/api/v1/docs_routes.py`
- Modify: `app/__init__.py` (docs_bp register)
- Test: `tests/test_docs_api.py`

**Interfaces:**
- Consumes: hiçbir servis (statik spec); Flask `jsonify`
- Produces: `GET /api/v1/openapi.json` (JSON), `GET /api/v1/docs` (Swagger UI HTML)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs_api.py
def test_openapi_json_lists_export_paths(client):
    r = client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    paths = r.json["paths"]
    assert "/api/v1/export/json" in paths
    assert "/api/v1/export/csv" in paths
    assert "/api/v1/health" in paths

def test_docs_html(client):
    r = client.get("/api/v1/docs")
    assert r.status_code == 200
    assert "swagger-ui" in r.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docs_api.py -v`
Expected: FAIL with 404.

- [ ] **Step 3: Write minimal implementation**

```python
# app/api/v1/docs_routes.py
from flask import Blueprint, jsonify, Response

docs_bp = Blueprint("docs", __name__)

__all__ = ["docs_bp", "build_openapi_spec"]

def build_openapi_spec():
    return {
        "openapi": "3.0.3",
        "info": {"title": "StajOS API", "version": "1.0.0", "description": "StajOS Solo MVP API"},
        "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}},
        "security": [{"bearerAuth": []}],
        "paths": {
            "/api/v1/health": {"get": {"summary": "Health", "security": [], "responses": {"200": {"description": "ok"}}}},
            "/api/v1/auth/register": {"post": {"summary": "Register", "security": [], "responses": {"201": {"description": "created"}}}},
            "/api/v1/auth/login": {"post": {"summary": "Login", "security": [], "responses": {"200": {"description": "tokens"}}}},
            "/api/v1/internships": {"post": {"summary": "Create internship", "responses": {"201": {"description": "created"}}}},
            "/api/v1/logs": {
                "get": {"summary": "List logs", "parameters": [{"name": "internship_id", "in": "query", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "ok"}}},
                "post": {"summary": "Create log", "responses": {"201": {"description": "created"}}},
            },
            "/api/v1/export/json": {"get": {"summary": "Export JSON", "parameters": [{"name": "internship_id", "in": "query", "required": False, "schema": {"type": "string"}}], "responses": {"200": {"description": "envelope data=list"}}}},
            "/api/v1/export/csv": {"get": {"summary": "Export CSV", "parameters": [{"name": "internship_id", "in": "query", "required": False, "schema": {"type": "string"}}], "responses": {"200": {"description": "text/csv download"}}}},
            "/api/v1/dashboard/stats": {"get": {"summary": "Dashboard stats", "responses": {"200": {"description": "ok"}}}},
            "/api/v1/timeline": {"get": {"summary": "Timeline", "responses": {"200": {"description": "ok"}}}},
        },
    }

@docs_bp.route("/api/v1/openapi.json", methods=["GET"], strict_slashes=False)
def openapi_json():
    return jsonify(build_openapi_spec()), 200

@docs_bp.route("/api/v1/docs", methods=["GET"], strict_slashes=False)
def swagger_ui():
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>StajOS API Docs</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"></head><body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url: '/api/v1/openapi.json', dom_id: '#swagger-ui'});</script>
</body></html>"""
    return Response(html, mimetype="text/html")
```

Register in `app/__init__.py`:

```python
from app.api.v1.docs_routes import docs_bp
app.register_blueprint(docs_bp)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_docs_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/docs_routes.py app/__init__.py tests/test_docs_api.py
git commit -m "feat: add openapi json and swagger ui"
```

---

### Task 5: Eksik unit testler + final doğrulama

**Files:**
- Create: `tests/test_date_calculator_unit.py`
- Test: full suite

**Interfaces:**
- Consumes: `calculate_day_number`, `calculate_duration_minutes`, `is_weekend` (`app/utils/date_calculator.py:12-109`)

- [ ] **Step 1: Write the failing test (kapsanmayan edge'ler)**

```python
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
```

- [ ] **Step 2: Run test to verify it passes (pure fonksiyon — zaten PASS beklenir, eksik kapsama kapatılır)**

Run: `python -m pytest tests/test_date_calculator_unit.py -v`
Expected: PASS (kapsama kanıtı; FAIL beklenmez çünkü implementasyon Faz 2'den hazır).

- [ ] **Step 3: Run full suite + checks**

Run: `python -m pytest -q`
Expected: PASS, 0 failed (mevcut 147 + yeni ~15 test).

Run: `python -m compileall app tests config.py run.py`
Expected: exit 0

Run: `git diff --check`
Expected: clean (whitespace hatası yok)

Run: `git status --short`
Expected: sadece Faz 6 dosyaları (export/docs/test), ilgisiz değişiklik yok.

- [ ] **Step 4: Commit**

```bash
git add tests/test_date_calculator_unit.py
git commit -m "test: add date calculator unit tests"
```

---

## Self-Review

- Spec coverage: export JSON/CSV (Task 1-3), Swagger/OpenAPI (Task 4), unit testler (Task 1+5) — architecture.md Faz 6 maddeleri tamam.
- Placeholder scan: yok — tüm kod blokları tam, komutlar exact.
- Type consistency: `get_export_dicts(user_id: str, internship_id: str | None) -> list[dict]`, `logs_to_csv_rows(log_dicts: list[dict]) -> str` tüm task'larda aynı.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-14-faz6-export-docs-tests.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
