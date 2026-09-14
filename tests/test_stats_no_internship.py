from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.user import User


def test_dashboard_stats_returns_empty_stats_for_user_without_internship(app, client):
    user = User(
        email="no-internship@example.com",
        password_hash="hash",
        full_name="No Internship",
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=user.id)

    response = client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert set(response.json) == {"success", "data", "meta", "errors"}
    assert response.json["success"] is True
    assert response.json["meta"] is None
    assert response.json["errors"] == []

    data = response.json["data"]
    assert data["total_internships"] == 0
    assert data["active_internship"] is None
    assert data["total_logs"] == 0
    assert data["total_days"] == 0
    assert data["total_duration_minutes"] == 0
    assert data["average_duration"] == 0
    assert len(data["logs_per_month"]) == 6
    assert all(item["count"] == 0 for item in data["logs_per_month"])
    assert data["top_technologies"] == []
    assert data["top_topics"] == []
    assert data["recent_logs"] == []
