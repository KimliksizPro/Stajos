from datetime import date, datetime, timezone

from sqlalchemy import DateTime, JSON

from app.models.daily_log import AIStatus, DailyLog


def test_daily_log_declares_persisted_ai_state_columns():
    assert AIStatus.PROCESSING.value == "PROCESSING"

    columns = DailyLog.__table__.columns
    for name in (
        "ai_suggested_technologies",
        "ai_suggested_topics",
        "ai_suggested_tags",
    ):
        assert isinstance(columns[name].type, JSON)
        assert columns[name].nullable is True

    started_at = columns["ai_processing_started_at"]
    assert isinstance(started_at.type, DateTime)
    assert started_at.type.timezone is True
    assert started_at.nullable is True


def test_daily_log_serializes_unset_suggestions_as_empty_lists():
    log = DailyLog(
        internship_id="internship-id",
        date=date(2026, 9, 14),
        day_number=1,
        title="AI persistence",
        raw_content="Implement persisted state.",
        ai_processing_started_at=datetime.now(timezone.utc),
    )

    serialized = log.to_dict()

    assert serialized["ai_suggested_technologies"] == []
    assert serialized["ai_suggested_topics"] == []
    assert serialized["ai_suggested_tags"] == []
    assert "ai_processing_started_at" not in serialized


def test_daily_log_serializes_suggestion_values_unchanged():
    log = DailyLog(
        internship_id="internship-id",
        date=date(2026, 9, 14),
        day_number=1,
        title="AI persistence",
        raw_content="Implement persisted state.",
        ai_suggested_technologies=[{"name": "Flask"}],
        ai_suggested_topics=[{"name": "Migrations"}],
        ai_suggested_tags=["backend", "database"],
    )

    serialized = log.to_dict()

    assert serialized["ai_suggested_technologies"] == [{"name": "Flask"}]
    assert serialized["ai_suggested_topics"] == [{"name": "Migrations"}]
    assert serialized["ai_suggested_tags"] == ["backend", "database"]
