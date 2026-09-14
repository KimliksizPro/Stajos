# Fix-2 API Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve health, stats, and timeline API contracts while removing duplicate timeline route date parsing.

**Architecture:** Keep HTTP normalization in `get_timeline()` and the range cap in `TimelineService`. Cache parsed dates in the route, use them for ordering and delegation, and lock already-correct health/stats behavior with regressions.

**Tech Stack:** Python 3.12, Flask, Flask-JWT-Extended, Flask-SQLAlchemy, pytest.

## Global Constraints

- Production changes: `app/api/v1/timeline_routes.py` only.
- Tests: create `tests/test_fix2_api_consistency.py` only.
- Preserve `{success, data, meta, errors}`, statuses, messages, and 366/367 behavior.
- Do not modify health/stats production code or refactor `TimelineService`.
- This is not a Git repository; do not run commit commands.

---

### Task 1: Write Contract Tests (RED)

**Files:**
- Create: `tests/test_fix2_api_consistency.py`

**Interfaces:**
- Consumes: existing `app`/`client` fixtures, `create_access_token`, `User`, `Internship`, route `parse_date`, `TimelineService.get_timeline`, and `StatsService._query_logs_per_month`.
- Produces: endpoint regressions and the failing single-parse structural test.

- [ ] **Step 1: Add fixtures local to the test module**

```python
import inspect
from datetime import date

from flask_jwt_extended import create_access_token

from app.api.v1 import timeline_routes
from app.extensions import db
from app.models.internship import Internship
from app.models.user import User
from app.services.stats_service import StatsService


def create_user(email="fix2@example.com"):
    user = User(email=email, password_hash="hash", full_name="Fix Two")
    db.session.add(user)
    db.session.commit()
    return user


def create_internship(user):
    internship = Internship(
        user_id=user.id,
        company_name="Example",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 1, 1),
        total_expected_days=500,
    )
    db.session.add(internship)
    db.session.commit()
    return internship


def auth_headers(user_id):
    token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 2: Add health and stats regression tests**

```python
def test_health_contract_accepts_trailing_slash(client):
    expected = {
        "success": True,
        "data": {"status": "ok"},
        "meta": None,
        "errors": [],
    }
    for path in ("/api/v1/health", "/api/v1/health/"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 200
        assert response.json == expected


def test_stats_contract_and_bind_lookup(app, client):
    user = create_user()
    response = client.get(
        "/api/v1/dashboard/stats", headers=auth_headers(user.id)
    )
    data = response.json["data"]

    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["meta"] is None
    assert response.json["errors"] == []
    assert set(data) == {
        "total_internships", "active_internship", "total_logs", "total_days",
        "total_duration_minutes", "average_duration", "logs_per_month",
        "top_technologies", "top_topics", "recent_logs",
    }
    assert data["total_internships"] == data["total_logs"] == data["total_days"] == 0
    assert data["total_duration_minutes"] == data["average_duration"] == 0
    assert data["active_internship"] is None
    assert len(data["logs_per_month"]) == 6
    assert all(item["count"] == 0 for item in data["logs_per_month"])
    assert data["top_technologies"] == data["top_topics"] == data["recent_logs"] == []

    source = inspect.getsource(StatsService._query_logs_per_month)
    assert "db.session.get_bind()" in source
    assert "db.engine" not in source
```

- [ ] **Step 3: Add the route structure test**

```python
def test_timeline_route_parses_dates_once_and_reuses_objects(app, client, monkeypatch):
    user = create_user()
    parsed = {
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 1, 2),
    }
    parse_calls = []
    service_calls = []

    def fake_parse_date(value, field_name):
        parse_calls.append((value, field_name))
        return parsed[field_name]

    def fake_get_timeline(**kwargs):
        service_calls.append(kwargs)
        return [], {"total_logs": 0, "total_days": 0}

    monkeypatch.setattr(timeline_routes, "parse_date", fake_parse_date)
    monkeypatch.setattr(timeline_routes.TimelineService, "get_timeline", fake_get_timeline)

    response = client.get(
        "/api/v1/timeline?internship_id=i-1&start_date=2024-01-01&end_date=2024-01-02",
        headers=auth_headers(user.id),
    )

    assert response.status_code == 200
    assert parse_calls == [
        ("2024-01-01", "start_date"),
        ("2024-01-02", "end_date"),
    ]
    assert service_calls[0]["start_date"] is parsed["start_date"]
    assert service_calls[0]["end_date"] is parsed["end_date"]
```

- [ ] **Step 4: Add real timeline contract/boundary coverage**

```python
def test_timeline_endpoint_preserves_contract_and_boundaries(app, client):
    user = create_user()
    internship = create_internship(user)
    headers = auth_headers(user.id)
    base = f"/api/v1/timeline?internship_id={internship.id}"

    valid = client.get(
        f"{base}&start_date=2024-01-01&end_date=2024-01-02", headers=headers
    )
    assert valid.status_code == 200
    assert valid.json["success"] is True
    assert valid.json["errors"] == []
    assert valid.json["meta"] == {
        "start_date": "2024-01-01", "end_date": "2024-01-02",
        "total_days": 2, "total_logs": 0,
    }
    assert [item["date"] for item in valid.json["data"]] == [
        "2024-01-01", "2024-01-02",
    ]

    reversed_range = client.get(
        f"{base}&start_date=2024-01-02&end_date=2024-01-01", headers=headers
    )
    assert reversed_range.status_code == 400
    assert reversed_range.json == {
        "success": False, "data": None, "meta": None,
        "errors": ["start_date end_date'den sonra olamaz"],
    }

    accepted = client.get(
        f"{base}&start_date=2024-01-01&end_date=2024-12-31", headers=headers
    )
    assert accepted.status_code == 200
    assert accepted.json["meta"]["total_days"] == 366

    rejected = client.get(
        f"{base}&start_date=2024-01-01&end_date=2025-01-01", headers=headers
    )
    assert rejected.status_code == 400
    assert rejected.json == {
        "success": False, "data": None, "meta": None,
        "errors": ["Tarih aralığı en fazla 366 gün olabilir"],
    }
```

- [ ] **Step 5: Confirm RED**

Run: `python -m pytest -v tests/test_fix2_api_consistency.py`

Expected: health, stats, and real timeline behavior pass; `test_timeline_route_parses_dates_once_and_reuses_objects` fails because dates are parsed twice and raw strings are delegated.

---

### Task 2: Cache And Reuse Parsed Dates (GREEN)

**Files:**
- Modify: `app/api/v1/timeline_routes.py:50-81`
- Test: `tests/test_fix2_api_consistency.py`

**Interfaces:**
- Consumes: `parse_date(value, field_name) -> datetime.date`; service accepts strings or dates.
- Produces: `s_date` / `e_date`, parsed at most once and passed unchanged.

- [ ] **Step 1: Replace both parsing blocks and simplify exclusivity/order checks**

```python
    s_date = None
    e_date = None
    if start_date_raw is not None and str(start_date_raw).strip() != "":
        s_date = parse_date(start_date_raw, "start_date")
    if end_date_raw is not None and str(end_date_raw).strip() != "":
        e_date = parse_date(end_date_raw, "end_date")

    if (has_year or has_month) and (s_date is not None or e_date is not None):
        raise BadRequestError("year/month ile start_date/end_date birlikte kullanılamaz")

    if s_date is not None and e_date is not None and s_date > e_date:
        raise BadRequestError("start_date end_date'den sonra olamaz")
```

- [ ] **Step 2: Pass cached dates to the existing service call**

```python
        start_date=s_date,
        end_date=e_date,
```

- [ ] **Step 3: Confirm GREEN**

Run: `python -m pytest -v tests/test_fix2_api_consistency.py`

Expected: 4 passed.

- [ ] **Step 4: Re-run existing service boundary tests**

Run: `python -m pytest -v tests/test_fix1_data_quality.py::test_timeline_accepts_366_calendar_days tests/test_fix1_data_quality.py::test_timeline_rejects_367_calendar_days`

Expected: 2 passed.

---

### Task 3: Full Verification

**Files:**
- Verify: `app/api/v1/timeline_routes.py`
- Verify: `tests/test_fix2_api_consistency.py`

**Interfaces:**
- Consumes: completed implementation.
- Produces: test/compilation evidence; no commit.

- [ ] **Step 1: Run all tests**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Run direct syntax compilation**

Run: `python -m py_compile app/api/v1/timeline_routes.py tests/test_fix2_api_consistency.py`

Expected: exit code 0 and no output.

- [ ] **Step 3: Compile all application and test modules**

Run: `python -m compileall -q app tests`

Expected: exit code 0 and no errors.

- [ ] **Step 4: Review scope and evidence**

Confirm only `app/api/v1/timeline_routes.py` and `tests/test_fix2_api_consistency.py` were changed during implementation, no placeholders remain, health/stats production files are untouched, and record exact command results. Do not commit because the workspace is not a Git repository.
