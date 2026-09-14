import uuid
from concurrent.futures import Future
from datetime import date, timedelta

from app.extensions import db
from app.models.daily_log import AIStatus, DailyLog
from app.models.internship import Internship
from app.models.user import User
from app.utils.time import utcnow


class FakeExecutor:
    def __init__(self, fail_ids=None):
        self.submitted = []
        self.fail_ids = set(fail_ids or [])

    def submit(self, log_id):
        if log_id in self.fail_ids:
            raise RuntimeError("queue full")
        self.submitted.append(log_id)
        future = Future()
        future.set_result(None)
        return future


def _make_log(status=AIStatus.PENDING, started_at=None, day=10):
    user = User(
        email=f"u-{uuid.uuid4()}@example.com",
        password_hash="hash",
        full_name="Test User",
    )
    db.session.add(user)
    db.session.flush()
    internship = Internship(
        user_id=user.id,
        company_name="ACME",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 31),
        total_expected_days=80,
    )
    db.session.add(internship)
    db.session.flush()
    log = DailyLog(
        internship_id=internship.id,
        date=date(2026, 9, day),
        day_number=day,
        title=f"Day {day} {uuid.uuid4()}",
        raw_content="raw content",
        ai_status=status,
        ai_processing_started_at=started_at,
    )
    db.session.add(log)
    db.session.commit()
    log_id = log.id
    db.session.expunge_all()
    return log_id


def _status_of(app, log_id):
    with app.app_context():
        log = db.session.get(DailyLog, log_id)
        status = log.ai_status
        db.session.expunge_all()
        return status


def test_recover_resets_stale_processing_and_submits_batch(app):
    from app.services.ai_service import AIService

    with app.app_context():
        stale_id = _make_log(
            status=AIStatus.PROCESSING,
            started_at=utcnow() - timedelta(seconds=1000),
            day=10,
        )
        pending_a = _make_log(status=AIStatus.PENDING, day=11)
        pending_b = _make_log(status=AIStatus.PENDING, day=12)
        db.session.expunge_all()

    executor = FakeExecutor()

    count = AIService.recover_pending(
        app, executor, batch_size=2, stale_after_seconds=300
    )

    assert count == 2
    assert len(executor.submitted) == 2
    # Stale must have been reset to PENDING before submit selection.
    assert _status_of(app, stale_id) == AIStatus.PENDING
    # Batch limit respected: only 2 of 3 pending submitted.
    assert set(executor.submitted).issubset({stale_id, pending_a, pending_b})


def test_recover_never_submits_terminal_or_fresh_processing(app):
    from app.services.ai_service import AIService

    with app.app_context():
        fresh_id = _make_log(
            status=AIStatus.PROCESSING, started_at=utcnow(), day=10
        )
        refined_id = _make_log(status=AIStatus.REFINED, day=11)
        accepted_id = _make_log(status=AIStatus.ACCEPTED, day=12)
        rejected_id = _make_log(status=AIStatus.REJECTED, day=13)
        error_id = _make_log(status=AIStatus.ERROR, day=14)
        pending_id = _make_log(status=AIStatus.PENDING, day=15)
        db.session.expunge_all()

    executor = FakeExecutor()

    count = AIService.recover_pending(
        app, executor, batch_size=100, stale_after_seconds=300
    )

    assert count == 1
    assert executor.submitted == [pending_id]
    assert _status_of(app, fresh_id) == AIStatus.PROCESSING
    assert _status_of(app, refined_id) == AIStatus.REFINED
    assert _status_of(app, accepted_id) == AIStatus.ACCEPTED
    assert _status_of(app, rejected_id) == AIStatus.REJECTED
    assert _status_of(app, error_id) == AIStatus.ERROR


def test_recover_batch_limit_respected(app):
    from app.services.ai_service import AIService

    with app.app_context():
        ids = [_make_log(status=AIStatus.PENDING, day=10 + i) for i in range(5)]
        db.session.expunge_all()

    executor = FakeExecutor()

    count = AIService.recover_pending(
        app, executor, batch_size=3, stale_after_seconds=300
    )

    assert count == 3
    assert len(executor.submitted) == 3
    assert set(executor.submitted).issubset(set(ids))


def test_recover_submit_failure_keeps_pending_and_continues(app):
    from app.services.ai_service import AIService

    with app.app_context():
        first_id = _make_log(status=AIStatus.PENDING, day=10)
        second_id = _make_log(status=AIStatus.PENDING, day=11)
        db.session.expunge_all()

    executor = FakeExecutor(fail_ids={first_id})

    count = AIService.recover_pending(
        app, executor, batch_size=100, stale_after_seconds=300
    )

    assert count == len(executor.submitted)
    assert second_id in executor.submitted
    # Failed submission stays PENDING for a later retry.
    assert _status_of(app, first_id) == AIStatus.PENDING


def test_executor_submit_delegates_to_process_log_with_id_only(app):
    from app.ai.executor import AIExecutor
    from app.ai.base_provider import AIProviderInterface

    calls = []

    class RecordingProvider(AIProviderInterface):
        def refine(self, raw_content: str) -> str:
            calls.append(raw_content)
            raise RuntimeError("stop here")

    provider = RecordingProvider()
    worker = AIExecutor(app, provider, max_workers=1)
    try:
        with app.app_context():
            log_id = _make_log(status=AIStatus.PENDING, day=10)
            db.session.expunge_all()

        future = worker.submit(log_id)
        future.result(timeout=10)

        assert _status_of(app, log_id) == AIStatus.ERROR
        assert calls == ["raw content"]
    finally:
        worker.shutdown(wait=True)
