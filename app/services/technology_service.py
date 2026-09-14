"""TechnologyService - Business logic for technologies domain (Faz 3).

Global scope (user independent), normalized_name unique.
"""

import logging
from typing import List

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BadRequestError, ConflictError
from app.extensions import db
from app.models.technology import Technology, log_technologies
from app.utils.validators import normalize_name

__all__ = ["TechnologyService"]

logger = logging.getLogger(__name__)


class TechnologyService:
    """Service Layer for technologies (global, no user isolation)."""

    @staticmethod
    def normalize(name: str) -> str:
        """Normalize technology name to lower().strip() (delegates to validators.normalize_name)."""
        return normalize_name(name)

    @staticmethod
    def get_or_create(name: str) -> Technology:
        """Get existing technology by normalized_name or create new.

        Global unique via normalized_name. Handles race via IntegrityError.

        Args:
            name: Technology name.

        Returns:
            Technology instance.

        Raises:
            BadRequestError: Validation failures.
        """
        if not name or not name.strip():
            raise BadRequestError("Teknoloji adı zorunludur")
        stripped = name.strip()
        if len(stripped) > 100:
            raise BadRequestError("Teknoloji adı en fazla 100 karakter olabilir")
        normalized = TechnologyService.normalize(name)
        if not normalized:
            raise BadRequestError("Teknoloji adı zorunludur")

        existing = Technology.query.filter_by(normalized_name=normalized).first()
        if existing:
            return existing

        tech = Technology(name=stripped, normalized_name=normalized)
        db.session.add(tech)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            err_str = str(e).lower()
            orig_str = str(getattr(e, "orig", "")).lower()
            combined = err_str + " " + orig_str
            if "foreign key" in combined:
                logger.warning("Foreign key violation on technology create normalized=%s: %s", normalized, e)
                raise BadRequestError("Geçersiz log veya topic")
            # Race: another request created same normalized_name
            existing = Technology.query.filter_by(normalized_name=normalized).first()
            if existing:
                return existing
            logger.debug("Technology create conflict normalized=%s: %s", normalized, e)
            raise ConflictError("Teknoloji oluşturulamadı (çakışma)")

        return tech

    @staticmethod
    def link_to_log(log_id: str, tech_names: List[str]) -> None:
        """Link technologies to a log. Creates missing technologies.

        Duplicate associations are ignored.

        Args:
            log_id: DailyLog id.
            tech_names: List of technology name strings.
        """
        if not log_id:
            raise BadRequestError("log_id zorunludur")
        if not tech_names:
            return

        for raw_name in tech_names:
            if raw_name is None:
                continue
            name = str(raw_name).strip()
            if not name:
                continue
            try:
                tech = TechnologyService.get_or_create(name)
            except Exception as e:
                logger.error("Technology get_or_create failed for %s: %s", name, e)
                continue

            # Duplicate guard
            existing = db.session.execute(
                db.select(log_technologies).where(
                    (log_technologies.c.log_id == log_id)
                    & (log_technologies.c.technology_id == tech.id)
                )
            ).first()
            if existing:
                continue

            try:
                db.session.execute(
                    log_technologies.insert().values(log_id=log_id, technology_id=tech.id)
                )
                db.session.flush()
            except IntegrityError as e:
                db.session.rollback()
                err_str = str(e).lower()
                orig_str = str(getattr(e, "orig", "")).lower()
                combined = err_str + " " + orig_str
                if "foreign key" in combined:
                    logger.warning("Foreign key violation on log_technologies insert log_id=%s tech=%s: %s", log_id, tech.id, e)
                    raise BadRequestError("Geçersiz log veya topic")
                logger.debug("log_technologies insert conflict log_id=%s tech=%s", log_id, tech.id)

        # Bulk commit: single commit outside loop (was per-iteration commit)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            err_str = str(e).lower()
            orig_str = str(getattr(e, "orig", "")).lower()
            combined = err_str + " " + orig_str
            if "foreign key" in combined:
                logger.warning("Foreign key violation on log_technologies bulk commit log_id=%s: %s", log_id, e)
                raise BadRequestError("Geçersiz log veya topic")
            logger.debug("log_technologies bulk commit conflict log_id=%s", log_id)

    @staticmethod
    def search_by_tech(tech_name: str) -> List[Technology]:
        """Search technology by normalized name (helper).

        Args:
            tech_name: Technology name to search.

        Returns:
            List of matching Technology (exact normalized match).
        """
        if not tech_name or not tech_name.strip():
            return []
        normalized = TechnologyService.normalize(tech_name)
        return Technology.query.filter_by(normalized_name=normalized).all()
