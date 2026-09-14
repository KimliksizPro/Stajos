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


def test_health_contract_accepts_trailing_slash(app, client):
    health_rules = {
        rule.rule: rule
        for rule in app.url_map.iter_rules()
        if rule.endpoint == "health"
    }
    assert "/api/v1/health" in health_rules
    assert health_rules["/api/v1/health"].strict_slashes is False

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
    create_internship(user)
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
    assert data["total_internships"] == 1
    assert data["total_logs"] == data["total_days"] == 0
    assert data["total_duration_minutes"] == data["average_duration"] == 0
    assert data["active_internship"]["company_name"] == "Example"
    assert len(data["logs_per_month"]) == 6
    assert all(item["count"] == 0 for item in data["logs_per_month"])
    assert data["top_technologies"] == data["top_topics"] == data["recent_logs"] == []

    source = inspect.getsource(StatsService._query_logs_per_month)
    assert "db.session.get_bind()" in source
    assert "db.engine" not in source


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
