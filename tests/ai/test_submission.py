"""Task 5 RED: post-commit submission tests (must FAIL before implementation)."""

import logging
import uuid
from concurrent.futures import Future
from datetime import date
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError
from app.extensions import db
from app.models.daily_log import AIStatus, DailyLog
from app.models.internship import Internship
from app.models.user import User
from app.services.log_service import LogService


class FakeExecutor:
    def __init__(self, fail=False):
        self.submitted_ids = []
        self.fail = fail

    def submit(self, log_id):
        if self.fail:
            raise RuntimeError("queue full")
        self.submitted_ids.append(log_id)
        future = Future()
        future.set_result(None)
        return future


def _make_user_internship(email=None):
    user = User(
        email=email or f"submit-{uuid.uuid4()}@example.com",
        password_hash="hash",
        full_name="Submit User",
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


def test_create_log_submits_only_committed_log(app):
    user, internship = _make_user_internship()
    fake = FakeExecutor()

    log = LogService.create_log(
        user.id,
        internship.id,
        "Day one",
        "Bugun cok sey ogrendim ve uyguladim.",
        date_override="2024-01-02",
        ai_executor=fake,
    )

    assert fake.submitted_ids == [log.id]
    assert log.ai_status == AIStatus.PENDING


def test_create_log_without_executor_skips_submission(app):
    user, internship = _make_user_internship()

    log = LogService.create_log(
        user.id,
        internship.id,
        "No executor",
        "Executor olmadan da kayit olusmali.",
        date_override="2024-01-02",
    )

    assert db.session.get(DailyLog, log.id) is not None


def test_create_log_resolves_executor_from_app_extensions(app):
    user, internship = _make_user_internship()
    fake = FakeExecutor()
    app.extensions["ai_executor"] = fake
    try:
        log = LogService.create_log(
            user.id,
            internship.id,
            "Extension executor",
            "Extension uzerinden submit edilmeli.",
            date_override="2024-01-02",
        )
    finally:
        app.extensions.pop("ai_executor", None)

    assert fake.submitted_ids == [log.id]


def test_create_log_does_not_submit_after_failed_commit(app, monkeypatch):
    user, internship = _make_user_internship()
    fake = FakeExecutor()
    monkeypatch.setattr(
        db.session,
        "commit",
        Mock(side_effect=IntegrityError("x", {}, None)),
    )

    with pytest.raises(ConflictError):
        LogService.create_log(
            user.id,
            internship.id,
            "Will fail",
            "Commit basarisiz olunca submit yok.",
            date_override="2024-01-03",
            ai_executor=fake,
        )

    assert fake.submitted_ids == []


def test_create_log_submit_failure_warns_and_keeps_pending(app, caplog):
    user, internship = _make_user_internship()
    failing = FakeExecutor(fail=True)

    with caplog.at_level(logging.WARNING, logger="app.services.log_service"):
        log = LogService.create_log(
            user.id,
            internship.id,
            "Submit fails",
            "Submit patlasa da kayit PENDING kalmali.",
            date_override="2024-01-02",
            ai_executor=failing,
        )

    assert log.ai_status == AIStatus.PENDING
    assert db.session.get(DailyLog, log.id) is not None
    assert any(
        record.levelno >= logging.WARNING and "AI submission failed" in record.message
        for record in caplog.records
    )
