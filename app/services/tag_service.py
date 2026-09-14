"""TagService - Business logic for tags domain (Faz 3).

User-scoped: (user_id + normalized_name) unique.
"""

import logging
from typing import List

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BadRequestError, ConflictError
from app.extensions import db
from app.models.tag import Tag, log_tags
from app.utils.validators import normalize_name

__all__ = ["TagService"]

logger = logging.getLogger(__name__)


class TagService:
    """Service Layer for tags (user isolation mandatory)."""

    @staticmethod
    def normalize(name: str) -> str:
        """Normalize tag name to lower().strip() (delegates to validators.normalize_name)."""
        return normalize_name(name)

    @staticmethod
    def get_or_create(user_id: str, name: str) -> Tag:
        """Get existing tag by user_id+normalized_name or create new.

        Args:
            user_id: Owner user id.
            name: Tag name.

        Returns:
            Tag instance.

        Raises:
            BadRequestError: Validation failures.
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        if not name or not name.strip():
            raise BadRequestError("Etiket adı zorunludur")

        stripped = name.strip()
        if len(stripped) > 100:
            raise BadRequestError("Etiket adı en fazla 100 karakter olabilir")

        normalized = TagService.normalize(name)
        if not normalized:
            raise BadRequestError("Etiket adı zorunludur")

        existing = Tag.query.filter_by(user_id=user_id, normalized_name=normalized).first()
        if existing:
            return existing

        tag = Tag(user_id=user_id, name=stripped, normalized_name=normalized)
        db.session.add(tag)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            err_str = str(e).lower()
            orig_str = str(getattr(e, "orig", "")).lower()
            combined = err_str + " " + orig_str
            if "foreign key" in combined:
                logger.warning("Foreign key violation on tag create user_id=%s normalized=%s: %s", user_id, normalized, e)
                raise BadRequestError("Geçersiz log veya topic")
            existing = Tag.query.filter_by(user_id=user_id, normalized_name=normalized).first()
            if existing:
                return existing
            logger.debug("Tag create conflict user_id=%s normalized=%s: %s", user_id, normalized, e)
            raise ConflictError("Etiket oluşturulamadı (çakışma)")

        return tag

    @staticmethod
    def link_to_log(log_id: str, user_id: str, tag_names: List[str]) -> None:
        """Link tags to a log. Creates missing tags (user-scoped).

        Duplicate associations are ignored. User isolation enforced.

        Args:
            log_id: DailyLog id.
            user_id: Owner user id.
            tag_names: List of tag name strings.
        """
        if not log_id:
            raise BadRequestError("log_id zorunludur")
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        if not tag_names:
            return

        for raw_name in tag_names:
            if raw_name is None:
                continue
            name = str(raw_name).strip()
            if not name:
                continue
            try:
                tag = TagService.get_or_create(user_id, name)
            except Exception as e:
                logger.error("Tag get_or_create failed for %s user %s: %s", name, user_id, e)
                continue

            existing = db.session.execute(
                db.select(log_tags).where(
                    (log_tags.c.log_id == log_id) & (log_tags.c.tag_id == tag.id)
                )
            ).first()
            if existing:
                continue

            try:
                db.session.execute(log_tags.insert().values(log_id=log_id, tag_id=tag.id))
                db.session.flush()
            except IntegrityError as e:
                db.session.rollback()
                err_str = str(e).lower()
                orig_str = str(getattr(e, "orig", "")).lower()
                combined = err_str + " " + orig_str
                if "foreign key" in combined:
                    logger.warning("Foreign key violation on log_tags insert log_id=%s tag=%s: %s", log_id, tag.id, e)
                    raise BadRequestError("Geçersiz log veya topic")
                logger.debug("log_tags insert conflict log_id=%s tag=%s", log_id, tag.id)

        # Bulk commit: single commit outside loop (was per-iteration commit)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            logger.debug("log_tags bulk commit conflict log_id=%s", log_id)
