from datetime import date

import pytest

from app.core.exceptions import BadRequestError
from app.extensions import db
from app.models.daily_log import DailyLog
from app.models.internship import Internship
from app.models.topic import Topic, log_topics
from app.models.user import User
from app.services.log_service import LogService
from app.services.timeline_service import TimelineService
from app.services.topic_service import TopicService
from app.utils.validators import normalize_name


def create_user_and_internship():
    user = User(email="fix1@example.com", password_hash="hash", full_name="Fix One")
    db.session.add(user)
    db.session.flush()
    internship = Internship(
        user_id=user.id,
        company_name="Example",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 1, 1),
        total_expected_days=500,
    )
    db.session.add(internship)
    db.session.commit()
    return user, internship


def test_timeline_accepts_366_calendar_days(app):
    user, internship = create_user_and_internship()

    timeline, meta = TimelineService.get_timeline(
        user.id,
        internship.id,
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    assert len(timeline) == 366
    assert meta["total_days"] == 366


def test_timeline_rejects_367_calendar_days(app):
    user, internship = create_user_and_internship()

    with pytest.raises(BadRequestError):
        TimelineService.get_timeline(
            user.id,
            internship.id,
            start_date="2024-01-01",
            end_date="2025-01-01",
        )


def test_topic_bulk_linking_is_atomic(app, monkeypatch):
    user, internship = create_user_and_internship()
    original = TopicService.link_to_log
    calls = 0

    def fail_on_second_link(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("forced bulk failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(TopicService, "link_to_log", fail_on_second_link)

    log = LogService.create_log(
        user.id,
        internship.id,
        "Atomic topics",
        "Content",
        date_override="2024-01-02",
        topics=["Python", "Flask"],
    )

    assert db.session.get(DailyLog, log.id) is not None
    assert db.session.execute(
        db.select(log_topics).where(log_topics.c.log_id == log.id)
    ).all() == []
    assert Topic.query.filter_by(user_id=user.id).all() == []


def test_find_or_create_topic_delegates_to_topic_service(app, monkeypatch):
    expected = object()
    calls = []

    def fake_get_or_create(user_id, name, parent_id=None, commit=True):
        calls.append((user_id, name, parent_id, commit))
        return expected

    monkeypatch.setattr(TopicService, "get_or_create", fake_get_or_create)

    assert LogService._find_or_create_topic("user-1", " Python ", commit=False) is expected
    assert calls == [("user-1", " Python ", None, False)]


def test_topic_filter_uses_normalized_name(app):
    user, internship = create_user_and_internship()
    log = DailyLog(
        internship_id=internship.id,
        date=date(2024, 1, 2),
        day_number=2,
        title="Normalization",
        raw_content="Content",
    )
    topic = Topic(
        user_id=user.id,
        name="  PyThOn  ",
        normalized_name=normalize_name("  PyThOn  "),
        first_seen_at=date(2024, 1, 2),
        usage_count=1,
    )
    db.session.add_all([log, topic])
    db.session.flush()
    db.session.execute(log_topics.insert().values(log_id=log.id, topic_id=topic.id))
    db.session.commit()

    items, total = LogService.get_logs(user.id, internship.id, topic=" PYTHON ")

    assert total == 1
    assert [item.id for item in items] == [log.id]
