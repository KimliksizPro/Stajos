import json
import uuid
from datetime import date, timedelta

from app.ai.base_provider import AIProviderInterface
from app.extensions import db
from app.models.daily_log import AIStatus, DailyLog
from app.models.internship import Internship
from app.models.user import User
from app.utils.time import utcnow


class FakeProvider(AIProviderInterface):
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = 0
        self.seen_inputs = []

    def refine(self, raw_content: str) -> str:
        self.calls += 1
        self.seen_inputs.append(raw_content)
        if self.error is not None:
            raise self.error
        return self.payload


def valid_payload(refined="Refined text"):
    return json.dumps(
        {
            "refined_content": refined,
            "technologies": ["Python"],
            "topics": ["API"],
            "tags": ["backend"],
        }
    )


def _make_log(status=AIStatus.PENDING, raw="raw content here", started_at=None):
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
        date=date(2026, 9, 10),
        day_number=1,
        title="Day log",
        raw_content=raw,
        ai_status=status,
        ai_processing_started_at=started_at,
    )
    db.session.add(log)
    db.session.commit()
    log_id = log.id
    db.session.expunge_all()
    return log_id, raw


def test_process_log_success_saves_refined_and_preserves_raw(app):
    from app.services.ai_service import AIService

    log_id, raw = _make_log()
    provider = FakeProvider(payload=valid_payload())

    # No outer app_context on purpose: worker must open its own.
    AIService.process_log(app, log_id, provider)

    with app.app_context():
        log = db.session.get(DailyLog, log_id)
        assert log.ai_status == AIStatus.REFINED
        assert log.ai_refined_content == "Refined text"
        assert list(log.ai_suggested_technologies) == ["Python"]
        assert list(log.ai_suggested_topics) == ["API"]
        assert list(log.ai_suggested_tags) == ["backend"]
        assert log.ai_processing_started_at is None
        assert log.raw_content == raw
        assert provider.calls == 1
        assert provider.seen_inputs == [raw]


def test_process_log_provider_error_sets_error_and_preserves_raw(app):
    from app.ai.base_provider import AIProviderError
    from app.services.ai_service import AIService

    log_id, raw = _make_log()
    provider = FakeProvider(error=AIProviderError("boom"))

    AIService.process_log(app, log_id, provider)

    with app.app_context():
        log = db.session.get(DailyLog, log_id)
        assert log.ai_status == AIStatus.ERROR
        assert log.ai_refined_content is None
        assert log.ai_processing_started_at is None
        assert log.raw_content == raw


def test_process_log_parser_error_sets_error(app):
    from app.services.ai_service import AIService

    log_id, raw = _make_log()
    provider = FakeProvider(payload="not-json{{{")
    before = raw

    AIService.process_log(app, log_id, provider)

    with app.app_context():
        log = db.session.get(DailyLog, log_id)
        assert log.ai_status == AIStatus.ERROR
        assert log.ai_processing_started_at is None
        assert log.raw_content == before


def test_process_log_without_pending_claim_never_calls_provider(app):
    from app.services.ai_service import AIService

    log_id, raw = _make_log(
        status=AIStatus.PROCESSING, started_at=utcnow()
    )
    provider = FakeProvider(payload=valid_payload())

    AIService.process_log(app, log_id, provider)

    assert provider.calls == 0
    with app.app_context():
        log = db.session.get(DailyLog, log_id)
        assert log.ai_status == AIStatus.PROCESSING
        assert log.raw_content == raw


def test_duplicate_claim_second_worker_provider_called_once(app):
    from app.services.ai_service import AIService

    log_id, _raw = _make_log()
    provider = FakeProvider(payload=valid_payload())

    AIService.process_log(app, log_id, provider)
    AIService.process_log(app, log_id, provider)

    assert provider.calls == 1
    with app.app_context():
        log = db.session.get(DailyLog, log_id)
        assert log.ai_status == AIStatus.REFINED


def test_process_log_missing_id_exits_without_provider_call(app):
    from app.services.ai_service import AIService

    provider = FakeProvider(payload=valid_payload())

    AIService.process_log(app, "does-not-exist", provider)

    assert provider.calls == 0
