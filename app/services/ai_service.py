import logging
from datetime import timedelta

from flask import Flask

from app.ai.base_provider import AIProviderInterface
from app.ai.parser import parse_ai_output
from app.extensions import db
from app.models.daily_log import AIStatus, DailyLog
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

__all__ = ["AIService"]


class AIService:
    """Background AI worker and startup recovery (Faz 5 Task 4)."""

    @staticmethod
    def process_log(app: Flask, log_id: str, provider: AIProviderInterface) -> None:
        with app.app_context():
            try:
                now = utcnow()
                claimed = (
                    db.session.query(DailyLog)
                    .filter(
                        DailyLog.id == log_id,
                        DailyLog.ai_status == AIStatus.PENDING,
                    )
                    .update(
                        {
                            DailyLog.ai_status: AIStatus.PROCESSING,
                            DailyLog.ai_processing_started_at: now,
                        },
                        synchronize_session=False,
                    )
                )
                db.session.commit()
                if not claimed:
                    return

                log = db.session.get(DailyLog, log_id)
                if log is None:
                    return
                raw_content = log.raw_content

                try:
                    payload = provider.refine(raw_content)
                    parsed = parse_ai_output(payload)
                except Exception as exc:
                    db.session.rollback()
                    failed = db.session.get(DailyLog, log_id)
                    if failed is not None:
                        failed.ai_status = AIStatus.ERROR
                        failed.ai_processing_started_at = None
                        db.session.commit()
                    logger.error(
                        "AI processing failed for log %s: %s",
                        log_id,
                        type(exc).__name__,
                    )
                    return

                current = db.session.get(DailyLog, log_id)
                if current is None:
                    return
                current.ai_refined_content = parsed.refined_content
                current.ai_suggested_technologies = list(parsed.technologies)
                current.ai_suggested_topics = list(parsed.topics)
                current.ai_suggested_tags = list(parsed.tags)
                current.ai_status = AIStatus.REFINED
                current.ai_processing_started_at = None
                db.session.commit()
            finally:
                db.session.remove()

    @staticmethod
    def recover_pending(
        app: Flask, executor, *, batch_size: int, stale_after_seconds: int
    ) -> int:
        with app.app_context():
            try:
                threshold = utcnow() - timedelta(seconds=stale_after_seconds)
                db.session.query(DailyLog).filter(
                    DailyLog.ai_status == AIStatus.PROCESSING,
                    DailyLog.ai_processing_started_at.is_not(None),
                    DailyLog.ai_processing_started_at < threshold,
                ).update(
                    {
                        DailyLog.ai_status: AIStatus.PENDING,
                        DailyLog.ai_processing_started_at: None,
                    },
                    synchronize_session=False,
                )
                db.session.commit()

                rows = (
                    db.session.query(DailyLog.id)
                    .filter(DailyLog.ai_status == AIStatus.PENDING)
                    .order_by(DailyLog.created_at)
                    .limit(batch_size)
                    .all()
                )
                submitted = 0
                for (pending_id,) in rows:
                    try:
                        executor.submit(pending_id)
                        submitted += 1
                    except Exception:
                        logger.error("AI recovery submit failed for log %s", pending_id)
                return submitted
            finally:
                db.session.remove()
