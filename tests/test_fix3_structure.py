import ast
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from app.core import pagination
from app.extensions import db
from app.models.internship import Internship
from app.models.user import User
from app.services import log_service, stats_service, timeline_service
from app.services.log_service import LogService
from app.services.stats_service import StatsService
from app.services.timeline_service import TimelineService


ROOT = Path(__file__).resolve().parents[1]


def _create_user(email="fix3@example.com"):
    user = User(email=email, password_hash="secret", full_name="Fix Three")
    db.session.add(user)
    db.session.commit()
    return user


def _create_internship(user):
    internship = Internship(
        user_id=user.id,
        company_name="Example",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 31),
        total_expected_days=80,
    )
    db.session.add(internship)
    db.session.commit()
    return internship


def _imported_names(path):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def _assert_password_hash_absent(value):
    if isinstance(value, dict):
        assert "password_hash" not in value
        for item in value.values():
            _assert_password_hash_absent(item)
    elif isinstance(value, list):
        for item in value:
            _assert_password_hash_absent(item)


def test_user_to_dict_exact_and_safe():
    user = User(
        id="u1",
        email="a@b.com",
        full_name="A",
        password_hash="secret",
        created_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
    )

    assert user.to_dict() == {
        "id": "u1",
        "email": "a@b.com",
        "full_name": "A",
        "created_at": "2026-09-14T00:00:00+00:00",
    }
    user.created_at = None
    assert user.to_dict()["created_at"] is None


def test_auth_responses_preserve_exact_public_fields(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "auth@example.com", "password": "secret123", "full_name": "Auth User"},
    )
    assert register.status_code == 201
    assert set(register.json["data"]) == {"id", "email", "full_name"}

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "auth@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    assert set(login.json["data"]) == {"user", "access_token", "refresh_token"}
    assert set(login.json["data"]["user"]) == {"id", "email", "full_name"}

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json['data']['access_token']}"},
    )
    assert me.status_code == 200
    assert set(me.json["data"]) == {"id", "email", "full_name", "created_at"}

    for response in (register, login, me):
        _assert_password_hash_absent(response.json)


def test_nullable_serialization_and_structure(app):
    user = _create_user()
    internship = _create_internship(user)

    serialized = internship.to_dict()
    assert serialized["start_date"] == "2026-09-01"
    assert serialized["end_date"] == "2026-12-31"
    assert serialized["created_at"] is not None
    assert serialized["updated_at"] is not None

    active = StatsService.get_dashboard_stats(user.id)["active_internship"]
    assert active == {
        "id": internship.id,
        "company_name": "Example",
        "status": "ACTIVE",
        "start_date": "2026-09-01",
        "end_date": "2026-12-31",
    }

    assert pagination.__all__ == ["get_pagination_params", "paginate_query"]
    for path in (
        "app/models/internship.py",
        "app/models/user.py",
        "app/services/stats_service.py",
    ):
        assert "iso_or_none" in _imported_names(path)

    for path, forbidden in {
        "app/services/internship_service.py": {"datetime"},
        "app/services/log_service.py": {"date", "time", "TopicModel"},
        "app/services/stats_service.py": {"timedelta"},
        "app/services/timeline_service.py": {"db"},
    }.items():
        assert _imported_names(path).isdisjoint(forbidden)

    timeline_source = (ROOT / "app/services/timeline_service.py").read_text(encoding="utf-8")
    for expression in (
        "cur.isoformat()",
        "d.isoformat()",
        "range_start.isoformat()",
        "range_end.isoformat()",
    ):
        assert expression in timeline_source


def test_recent_logs_eager_load_failure_warns_and_continues(app, monkeypatch, caplog):
    user = _create_user("stats@example.com")
    internship = _create_internship(user)
    monkeypatch.setattr(stats_service, "selectinload", lambda relationship: (_ for _ in ()).throw(RuntimeError("loader unavailable")))

    with caplog.at_level(logging.WARNING, logger=stats_service.__name__):
        assert StatsService._query_recent_logs([internship.id]) == []

    assert [record.getMessage() for record in caplog.records] == [
        "Failed to configure eager loading for recent logs: loader unavailable"
    ]


def test_timeline_eager_load_failure_warns_and_continues(app, monkeypatch, caplog):
    user = _create_user("timeline@example.com")
    internship = _create_internship(user)
    monkeypatch.setattr(timeline_service, "selectinload", lambda relationship: (_ for _ in ()).throw(RuntimeError("loader unavailable")))

    with caplog.at_level(logging.WARNING, logger=timeline_service.__name__):
        assert TimelineService.get_timeline(user.id, internship.id) == (
            [],
            {"total_logs": 0, "total_days": 0},
        )

    assert [record.getMessage() for record in caplog.records] == [
        "Failed to configure eager loading for timeline logs: loader unavailable"
    ]


def test_log_list_eager_load_failure_warns_and_continues(app, monkeypatch, caplog):
    user = _create_user("logs@example.com")
    internship = _create_internship(user)
    monkeypatch.setattr(log_service, "selectinload", lambda relationship: (_ for _ in ()).throw(RuntimeError("loader unavailable")))

    with caplog.at_level(logging.WARNING, logger=log_service.__name__):
        assert LogService.get_logs(user.id, internship.id) == ([], 0)

    assert [record.getMessage() for record in caplog.records] == [
        "Failed to configure eager loading for log list: loader unavailable"
    ]
