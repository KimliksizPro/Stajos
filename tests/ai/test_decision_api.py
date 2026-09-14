"""Task 6 RED: accept/reject API tests (must FAIL before implementation)."""

import uuid
from datetime import date

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.daily_log import AIStatus
from app.models.internship import Internship
from app.models.user import User
from app.services.log_service import LogService


def _make_user(email=None):
    user = User(
        email=email or f"api-{uuid.uuid4()}@example.com",
        password_hash="hash",
        full_name="API User",
    )
    db.session.add(user)
    db.session.commit()
    return user


def _make_internship(user):
    internship = Internship(
        user_id=user.id,
        company_name="ACME",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        total_expected_days=500,
    )
    db.session.add(internship)
    db.session.commit()
    return internship


def _make_refined_log(user, internship, date_override="2024-01-02"):
    log = LogService.create_log(
        user.id,
        internship.id,
        "Day one",
        "Bugun cok sey ogrendim ve uyguladim.",
        date_override=date_override,
    )
    log.ai_refined_content = "Refined content here."
    log.ai_suggested_technologies = ["Flask"]
    log.ai_suggested_tags = ["backend"]
    log.ai_suggested_topics = []
    log.ai_status = AIStatus.REFINED
    db.session.commit()
    return log


def _auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(identity=user_id)}"}


def test_accept_ai_returns_envelope_with_accepted_log(app, client):
    user = _make_user()
    internship = _make_internship(user)
    log = _make_refined_log(user, internship)

    resp = client.put(f"/api/v1/logs/{log.id}/accept-ai", headers=_auth(user.id))

    assert resp.status_code == 200
    body = resp.json
    assert body["success"] is True
    assert body["meta"] is None
    assert body["errors"] == []
    assert body["data"]["id"] == log.id
    assert body["data"]["ai_status"] == "ACCEPTED"


def test_reject_ai_returns_envelope_with_rejected_log(app, client):
    user = _make_user()
    internship = _make_internship(user)
    log = _make_refined_log(user, internship)

    resp = client.put(f"/api/v1/logs/{log.id}/reject-ai", headers=_auth(user.id))

    assert resp.status_code == 200
    assert resp.json["success"] is True
    assert resp.json["meta"] is None
    assert resp.json["errors"] == []
    assert resp.json["data"]["ai_status"] == "REJECTED"


def test_decision_endpoints_require_jwt(app, client):
    user = _make_user()
    internship = _make_internship(user)
    log = _make_refined_log(user, internship)

    for path in (f"/api/v1/logs/{log.id}/accept-ai", f"/api/v1/logs/{log.id}/reject-ai"):
        resp = client.put(path)
        assert resp.status_code == 401
        assert resp.json["success"] is False


def test_accept_ai_foreign_log_is_404(app, client):
    owner = _make_user()
    internship = _make_internship(owner)
    log = _make_refined_log(owner, internship)
    stranger = _make_user(email=f"stranger-{uuid.uuid4()}@example.com")

    resp = client.put(f"/api/v1/logs/{log.id}/accept-ai", headers=_auth(stranger.id))

    assert resp.status_code == 404
    assert resp.json["success"] is False


def test_reject_ai_missing_log_is_404(app, client):
    user = _make_user()

    resp = client.put("/api/v1/logs/does-not-exist/reject-ai", headers=_auth(user.id))

    assert resp.status_code == 404
    assert resp.json["success"] is False


def test_accept_ai_non_refined_is_409(app, client):
    user = _make_user()
    internship = _make_internship(user)
    log = LogService.create_log(
        user.id, internship.id, "Day one",
        "Bugun cok sey ogrendim ve uyguladim.",
        date_override="2024-01-02",
    )
    assert log.ai_status == AIStatus.PENDING

    resp = client.put(f"/api/v1/logs/{log.id}/accept-ai", headers=_auth(user.id))

    assert resp.status_code == 409
    assert resp.json["success"] is False


def test_reject_ai_repeated_is_409(app, client):
    user = _make_user()
    internship = _make_internship(user)
    log = _make_refined_log(user, internship)

    first = client.put(f"/api/v1/logs/{log.id}/reject-ai", headers=_auth(user.id))
    assert first.status_code == 200
    second = client.put(f"/api/v1/logs/{log.id}/reject-ai", headers=_auth(user.id))

    assert second.status_code == 409
    assert second.json["success"] is False


def test_accept_ai_repeated_is_409(app, client):
    user = _make_user()
    internship = _make_internship(user)
    log = _make_refined_log(user, internship)

    first = client.put(f"/api/v1/logs/{log.id}/accept-ai", headers=_auth(user.id))
    assert first.status_code == 200
    second = client.put(f"/api/v1/logs/{log.id}/accept-ai", headers=_auth(user.id))

    assert second.status_code == 409
    assert second.json["success"] is False


def test_decision_endpoints_have_no_trailing_slash_redirect(app, client):
    user = _make_user()
    internship = _make_internship(user)
    log_a = _make_refined_log(user, internship, date_override="2024-01-02")
    log_r = _make_refined_log(user, internship, date_override="2024-01-03")

    accept = client.put(
        f"/api/v1/logs/{log_a.id}/accept-ai/",
        headers=_auth(user.id),
        follow_redirects=False,
    )
    reject = client.put(
        f"/api/v1/logs/{log_r.id}/reject-ai/",
        headers=_auth(user.id),
        follow_redirects=False,
    )

    assert accept.status_code == 200, accept.json
    assert accept.json["data"]["ai_status"] == "ACCEPTED"
    assert reject.status_code == 200, reject.json
    assert reject.json["data"]["ai_status"] == "REJECTED"
