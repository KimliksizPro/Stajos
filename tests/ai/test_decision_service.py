"""Task 6 RED: accept/reject service tests (must FAIL before implementation)."""

import uuid
from datetime import date

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.extensions import db
from app.models.daily_log import AIStatus, DailyLog
from app.models.internship import Internship
from app.models.tag import Tag, log_tags
from app.models.technology import Technology, log_technologies
from app.models.topic import Topic, log_topics
from app.models.user import User
from app.services.log_service import LogService
from app.services.tag_service import TagService
from app.services.technology_service import TechnologyService
from app.services.topic_service import TopicService


def _make_user_internship(email=None):
    user = User(
        email=email or f"decision-{uuid.uuid4()}@example.com",
        password_hash="hash",
        full_name="Decision User",
    )
    db.session.add(user)
    db.session.flush()
    internship = Internship(
        user_id=user.id,
        company_name="ACME",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        total_expected_days=500,
    )
    db.session.add(internship)
    db.session.commit()
    return user, internship


def _make_refined_log(user, internship, date_override="2024-01-02", **suggestions):
    log = LogService.create_log(
        user.id,
        internship.id,
        "Day one",
        "Bugun cok sey ogrendim ve uyguladim.",
        date_override=date_override,
    )
    log.ai_refined_content = "Refined content here."
    log.ai_suggested_technologies = suggestions.get("technologies", [])
    log.ai_suggested_topics = suggestions.get("topics", [])
    log.ai_suggested_tags = suggestions.get("tags", [])
    log.ai_status = AIStatus.REFINED
    db.session.commit()
    return log


def _topic_link_row(log_id, topic_id):
    return db.session.execute(
        db.select(log_topics).where(
            (log_topics.c.log_id == log_id) & (log_topics.c.topic_id == topic_id)
        )
    ).first()


# ---- accept happy path ----

def test_accept_ai_links_all_suggestions_atomically(app):
    user, internship = _make_user_internship()
    root = TopicService.create_topic(user.id, "Docker")
    log = _make_refined_log(
        user, internship,
        technologies=["Flask"],
        topics=["Docker"],
        tags=["backend"],
    )
    raw_before = log.raw_content
    refined_before = log.ai_refined_content

    result = LogService.accept_ai(user.id, log.id)

    assert result.ai_status == AIStatus.ACCEPTED
    assert result.raw_content == raw_before
    assert result.ai_refined_content == refined_before
    # tech linked (case-insensitive get-or-create)
    tech = Technology.query.filter_by(normalized_name="flask").one()
    assert db.session.execute(
        db.select(log_technologies).where(
            (log_technologies.c.log_id == log.id)
            & (log_technologies.c.technology_id == tech.id)
        )
    ).first() is not None
    # tag linked user-scoped
    tag = Tag.query.filter_by(user_id=user.id, normalized_name="backend").one()
    assert db.session.execute(
        db.select(log_tags).where(
            (log_tags.c.log_id == log.id) & (log_tags.c.tag_id == tag.id)
        )
    ).first() is not None
    # topic linked as AI-suggested with usage increment
    row = _topic_link_row(log.id, root.id)
    assert row is not None
    assert bool(row.is_ai_suggested) is True
    db.session.expire_all()
    assert db.session.get(Topic, root.id).usage_count == 1


def test_accept_ai_matches_technology_case_insensitively_without_duplicates(app):
    user, internship = _make_user_internship()
    TechnologyService.get_or_create("Flask")
    assert Technology.query.count() == 1
    log = _make_refined_log(user, internship, technologies=["  FLASK  "])

    LogService.accept_ai(user.id, log.id)

    assert Technology.query.count() == 1


def test_accept_ai_matches_tag_case_insensitively_without_duplicates(app):
    user, internship = _make_user_internship()
    TagService.get_or_create(user.id, "Backend")
    log = _make_refined_log(user, internship, tags=["BACKEND"])

    LogService.accept_ai(user.id, log.id)

    assert Tag.query.filter_by(user_id=user.id).count() == 1


# ---- accept guards ----

def test_accept_ai_foreign_log_is_404(app):
    owner, internship = _make_user_internship()
    stranger, _ = _make_user_internship(email=f"stranger-{uuid.uuid4()}@example.com")
    log = _make_refined_log(owner, internship)

    with pytest.raises(NotFoundError):
        LogService.accept_ai(stranger.id, log.id)


def test_accept_ai_missing_log_is_404(app):
    user, _ = _make_user_internship()
    with pytest.raises(NotFoundError):
        LogService.accept_ai(user.id, "does-not-exist")


@pytest.mark.parametrize("status", [
    AIStatus.PENDING, AIStatus.PROCESSING, AIStatus.ACCEPTED,
    AIStatus.REJECTED, AIStatus.ERROR,
])
def test_accept_ai_requires_refined_status(app, status):
    user, internship = _make_user_internship()
    log = LogService.create_log(
        user.id, internship.id, "Day one",
        "Bugun cok sey ogrendim ve uyguladim.",
        date_override="2024-01-02",
    )
    log.ai_status = status
    db.session.commit()

    with pytest.raises(ConflictError):
        LogService.accept_ai(user.id, log.id)


def test_accept_ai_repeated_accept_is_409(app):
    user, internship = _make_user_internship()
    log = _make_refined_log(user, internship)

    LogService.accept_ai(user.id, log.id)
    with pytest.raises(ConflictError):
        LogService.accept_ai(user.id, log.id)


# ---- topic rules ----

def test_accept_ai_never_creates_missing_topic(app):
    user, internship = _make_user_internship()
    log = _make_refined_log(user, internship, topics=["GhostTopic"])

    LogService.accept_ai(user.id, log.id)

    assert Topic.query.filter_by(user_id=user.id).count() == 0
    assert db.session.execute(
        db.select(log_topics).where(log_topics.c.log_id == log.id)
    ).first() is None


def test_accept_ai_ignores_child_topic_with_same_name(app):
    user, internship = _make_user_internship()
    parent = TopicService.create_topic(user.id, "Parent")
    child = TopicService.create_topic(user.id, "Docker", parent_id=parent.id)
    log = _make_refined_log(user, internship, topics=["docker"])

    LogService.accept_ai(user.id, log.id)

    # only root topics match: child must not be linked, no new root created
    assert _topic_link_row(log.id, child.id) is None
    assert Topic.query.filter_by(user_id=user.id).count() == 2
    db.session.expire_all()
    assert db.session.get(Topic, child.id).usage_count == 0


def test_accept_ai_keeps_manual_topic_link_and_skips_usage_increment(app):
    user, internship = _make_user_internship()
    root = TopicService.create_topic(user.id, "Docker")
    log = _make_refined_log(user, internship, topics=["Docker"])
    TopicService.link_to_log(user.id, log.id, root.id, is_ai_suggested=False)
    TopicService.increment_usage(user.id, root.id)
    db.session.expire_all()
    assert db.session.get(Topic, root.id).usage_count == 1

    LogService.accept_ai(user.id, log.id)

    row = _topic_link_row(log.id, root.id)
    assert row is not None
    assert bool(row.is_ai_suggested) is False  # manual stays manual
    db.session.expire_all()
    assert db.session.get(Topic, root.id).usage_count == 1  # no double increment


def test_accept_ai_does_not_match_other_users_topic(app):
    owner, internship = _make_user_internship()
    other, _ = _make_user_internship(email=f"other-{uuid.uuid4()}@example.com")
    TopicService.create_topic(other.id, "Docker")
    log = _make_refined_log(owner, internship, topics=["Docker"])

    LogService.accept_ai(owner.id, log.id)

    assert Topic.query.filter_by(user_id=owner.id).count() == 0
    assert db.session.execute(
        db.select(log_topics).where(log_topics.c.log_id == log.id)
    ).first() is None


# ---- atomicity / rollback ----

def test_accept_ai_rolls_back_everything_on_db_error(app, monkeypatch):
    user, internship = _make_user_internship()
    root = TopicService.create_topic(user.id, "Docker")
    log = _make_refined_log(
        user, internship,
        technologies=["Flask"],
        topics=["Docker"],
        tags=["backend"],
    )

    def _boom(name, *, commit=True):
        raise RuntimeError("boom")

    monkeypatch.setattr(TechnologyService, "get_or_create", _boom)

    with pytest.raises(Exception):
        LogService.accept_ai(user.id, log.id)

    db.session.expire_all()
    fresh = db.session.get(DailyLog, log.id)
    assert fresh.ai_status == AIStatus.REFINED
    assert Technology.query.count() == 0
    assert Tag.query.filter_by(user_id=user.id).count() == 0
    assert db.session.execute(
        db.select(log_technologies).where(log_technologies.c.log_id == log.id)
    ).first() is None
    assert db.session.execute(
        db.select(log_tags).where(log_tags.c.log_id == log.id)
    ).first() is None
    assert _topic_link_row(log.id, root.id) is None
    db.session.expire_all()
    assert db.session.get(Topic, root.id).usage_count == 0


# ---- reject ----

def test_reject_ai_changes_only_status(app):
    user, internship = _make_user_internship()
    root = TopicService.create_topic(user.id, "Docker")
    log = _make_refined_log(
        user, internship,
        technologies=["Flask"],
        topics=["Docker"],
        tags=["backend"],
    )
    raw_before = log.raw_content
    refined_before = log.ai_refined_content

    result = LogService.reject_ai(user.id, log.id)

    assert result.ai_status == AIStatus.REJECTED
    assert result.raw_content == raw_before
    assert result.ai_refined_content == refined_before
    # suggestions preserved
    assert result.ai_suggested_technologies == ["Flask"]
    assert result.ai_suggested_topics == ["Docker"]
    assert result.ai_suggested_tags == ["backend"]
    # no relations created
    assert Technology.query.count() == 0
    assert Tag.query.filter_by(user_id=user.id).count() == 0
    assert _topic_link_row(log.id, root.id) is None


def test_reject_ai_foreign_log_is_404(app):
    owner, internship = _make_user_internship()
    stranger, _ = _make_user_internship(email=f"stranger-{uuid.uuid4()}@example.com")
    log = _make_refined_log(owner, internship)

    with pytest.raises(NotFoundError):
        LogService.reject_ai(stranger.id, log.id)


@pytest.mark.parametrize("status", [
    AIStatus.PENDING, AIStatus.PROCESSING, AIStatus.ACCEPTED,
    AIStatus.REJECTED, AIStatus.ERROR,
])
def test_reject_ai_requires_refined_status(app, status):
    user, internship = _make_user_internship()
    log = LogService.create_log(
        user.id, internship.id, "Day one",
        "Bugun cok sey ogrendim ve uyguladim.",
        date_override="2024-01-02",
    )
    log.ai_status = status
    db.session.commit()

    with pytest.raises(ConflictError):
        LogService.reject_ai(user.id, log.id)


def test_reject_ai_repeated_reject_is_409(app):
    user, internship = _make_user_internship()
    log = _make_refined_log(user, internship)

    LogService.reject_ai(user.id, log.id)
    with pytest.raises(ConflictError):
        LogService.reject_ai(user.id, log.id)


def test_reject_ai_rolls_back_on_unexpected_commit_error(app, monkeypatch):
    user, internship = _make_user_internship()
    log = _make_refined_log(user, internship)
    log_id = log.id

    rollback_calls = []
    real_rollback = db.session.rollback

    def _spy_rollback():
        rollback_calls.append(1)
        return real_rollback()

    def _boom_commit():
        raise RuntimeError("boom")

    monkeypatch.setattr(db.session, "commit", _boom_commit)
    monkeypatch.setattr(db.session, "rollback", _spy_rollback)

    with pytest.raises(RuntimeError):
        LogService.reject_ai(user.id, log_id)

    assert len(rollback_calls) == 1
    # session clean: usable for new queries/writes after rollback
    db.session.expire_all()
    fresh = db.session.get(DailyLog, log_id)
    assert fresh.ai_status == AIStatus.REFINED
    assert db.session.execute(
        db.select(DailyLog).where(DailyLog.id == log_id)
    ).scalar_one_or_none() is not None
