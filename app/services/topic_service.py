"""TopicService - Business logic for topics domain (Faz 3).

SSOT: architecture.md:96-108, docs/kurallar.md:31
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.extensions import db
from app.models.topic import Topic, log_topics
from app.utils.time import iso_or_none
from app.utils.validators import normalize_name, today_utc

__all__ = ["TopicService"]

logger = logging.getLogger(__name__)


class TopicService:
    """Service Layer for topics (no HTTP logic, kurallar.md:4)."""

    @staticmethod
    def create_topic(
        user_id: str,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Topic:
        """Create a new topic with user isolation.

        Args:
            user_id: Current user id (from JWT).
            name: Topic name (required, max 255).
            description: Optional description.
            parent_id: Optional parent topic id.

        Returns:
            Created Topic instance.

        Raises:
            BadRequestError: Validation failures.
            NotFoundError: Parent topic not found / not owned.
            ConflictError: Duplicate topic (user_id+parent_id+normalized_name).
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")

        name = (name or "").strip()
        if not name:
            raise BadRequestError("Konu adı zorunludur")
        if len(name) > 255:
            raise BadRequestError("Konu adı en fazla 255 karakter olabilir")

        if description is not None:
            description = description.strip() or None
            if description and len(description) > 5000:
                raise BadRequestError("Açıklama en fazla 5000 karakter olabilir")

        # Parent validation with user isolation
        if parent_id is not None:
            parent_id = str(parent_id).strip() or None
        if parent_id:
            parent = Topic.query.filter_by(id=parent_id, user_id=user_id).first()
            if not parent:
                raise NotFoundError("Üst konu bulunamadı")
        else:
            parent_id = None

        # Unique check: user_id + parent_id + normalized_name
        normalized = normalize_name(name)
        query = Topic.query.filter(Topic.user_id == user_id, Topic.normalized_name == normalized)
        if parent_id is None:
            query = query.filter(Topic.parent_id.is_(None))
        else:
            query = query.filter(Topic.parent_id == parent_id)
        existing = query.first()
        if existing:
            raise ConflictError("Bu isimde bir konu zaten mevcut")

        topic = Topic(
            user_id=user_id,
            name=name,
            normalized_name=normalized,
            description=description,
            parent_id=parent_id,
            first_seen_at=today_utc(),
            usage_count=0,
        )
        db.session.add(topic)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            err_str = str(e).lower()
            orig_str = str(getattr(e, "orig", "")).lower()
            combined = err_str + " " + orig_str
            if "foreign key" in combined:
                logger.warning("Foreign key violation on topic create user_id=%s parent_id=%s: %s", user_id, parent_id, e)
                raise BadRequestError("Geçersiz log veya topic")
            logger.debug("Topic create conflict user_id=%s parent_id=%s normalized=%s: %s", user_id, parent_id, normalized, e)
            raise ConflictError("Bu isimde bir konu zaten mevcut (aynı üst konu altında)")

        return topic

    @staticmethod
    def get_or_create(
        user_id: str,
        name: str,
        parent_id: Optional[str] = None,
        commit: bool = True,
    ) -> Topic:
        """Get existing topic by user_id+parent_id+normalized_name or create new.

        Args:
            user_id: Owner user id.
            name: Topic name.
            parent_id: Optional parent topic id (defaults to None for root topics).

        Returns:
            Topic instance (existing or newly created).

        Raises:
            BadRequestError: Validation failures.
            NotFoundError: Parent topic not found.
            ConflictError: Race conflict unresolvable.
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        if not name or not name.strip():
            raise BadRequestError("Konu adı zorunludur")
        stripped = name.strip()
        if len(stripped) > 255:
            raise BadRequestError("Konu adı en fazla 255 karakter olabilir")
        normalized = normalize_name(stripped)

        # Normalize parent_id
        if parent_id is not None:
            parent_id = str(parent_id).strip() or None
        if parent_id == "":
            parent_id = None

        # Check existing via normalized_name
        query = Topic.query.filter(Topic.user_id == user_id, Topic.normalized_name == normalized)
        if parent_id is None:
            query = query.filter(Topic.parent_id.is_(None))
        else:
            query = query.filter(Topic.parent_id == parent_id)
        existing = query.first()
        if existing:
            return existing

        # Try to create
        try:
            if commit:
                return TopicService.create_topic(user_id, stripped, description=None, parent_id=parent_id)
            topic = Topic(
                user_id=user_id,
                name=stripped,
                normalized_name=normalized,
                description=None,
                parent_id=parent_id,
                first_seen_at=today_utc(),
                usage_count=0,
            )
            db.session.add(topic)
            db.session.flush()
            return topic
        except ConflictError:
            # Race: fetch again
            existing = query.first()
            if existing:
                return existing
            raise

    @staticmethod
    def get_tree(user_id: str) -> List[Dict]:
        """Get full topic tree for user.

        Single query, no N+1. Roots are topics with parent_id None.

        Args:
            user_id: Current user id.

        Returns:
            List of root node dicts, each with children recursively.

        Raises:
            BadRequestError: Missing user_id.
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")

        topics = Topic.query.filter_by(user_id=user_id).order_by(Topic.created_at.asc()).all()

        # Build id -> node map
        id_to_node: Dict[str, Dict] = {}
        for t in topics:
            node = t.to_dict()
            node["children"] = []
            id_to_node[t.id] = node

        roots: List[Dict] = []
        for t in topics:
            node = id_to_node[t.id]
            if t.parent_id is None:
                roots.append(node)
            else:
                parent_node = id_to_node.get(t.parent_id)
                if parent_node is not None:
                    parent_node["children"].append(node)
                else:
                    # Orphan (parent not in user scope) -> treat as root
                    roots.append(node)

        return roots

    @staticmethod
    def get_progress(user_id: str, topic_id: str) -> Dict:
        """Get progress info for a topic.

        Args:
            user_id: Current user id.
            topic_id: Topic id.

        Returns:
            Dict with topic info, usage_count, log_count, first_seen_at etc.

        Raises:
            BadRequestError, NotFoundError
        """
        if not user_id or not topic_id:
            raise BadRequestError("user_id ve topic_id zorunludur")

        topic = Topic.query.filter_by(id=topic_id, user_id=user_id).first()
        if not topic:
            raise NotFoundError("Konu bulunamadı")

        # Log count via log_topics join
        log_count = db.session.query(func.count()).select_from(log_topics).filter(
            log_topics.c.topic_id == topic_id
        ).scalar() or 0

        return {
            "topic": topic.to_dict(),
            "usage_count": topic.usage_count,
            "log_count": int(log_count),
            "first_seen_at": iso_or_none(topic.first_seen_at),
            "progress": topic.usage_count,
        }

    @staticmethod
    def increment_usage(user_id: str, topic_id: str, commit: bool = True) -> Topic:
        """Increment usage_count for a topic (internal helper).

        Args:
            user_id: Current user id for isolation.
            topic_id: Topic id.

        Returns:
            Updated Topic.

        Raises:
            BadRequestError, NotFoundError
        """
        if not user_id or not topic_id:
            raise BadRequestError("user_id ve topic_id zorunludur")

        topic = Topic.query.filter_by(id=topic_id, user_id=user_id).first()
        if not topic:
            raise NotFoundError("Konu bulunamadı")

        topic.usage_count = (topic.usage_count or 0) + 1
        try:
            if commit:
                db.session.commit()
            else:
                db.session.flush()
        except IntegrityError:
            if commit:
                db.session.rollback()
            raise ConflictError("Kullanım sayısı güncellenemedi")

        return topic

    @staticmethod
    def link_to_log(
        user_id: str,
        log_id: str,
        topic_id: str,
        is_ai_suggested: bool = False,
        commit: bool = True,
    ) -> None:
        """Link a topic to a log via log_topics (helper).

        Ownership checks are enforced. Duplicate inserts are ignored.

        Args:
            user_id: Owner user id (for isolation).
            log_id: DailyLog id.
            topic_id: Topic id.
            is_ai_suggested: Whether AI suggested the link.

        Raises:
            BadRequestError: Missing ids or FK violation.
            NotFoundError: Topic not found/owned or log not owned.
        """
        if not user_id or not log_id or not topic_id:
            raise BadRequestError("user_id, log_id ve topic_id zorunludur")

        # Ownership: topic must belong to user
        topic = Topic.query.filter_by(id=topic_id, user_id=user_id).first()
        if not topic:
            raise NotFoundError("Konu bulunamadı")

        # Ownership: log must belong to user via internship
        from app.models.daily_log import DailyLog
        from app.models.internship import Internship

        log_owned = (
            db.session.query(DailyLog.id)
            .join(Internship, DailyLog.internship_id == Internship.id)
            .filter(DailyLog.id == log_id, Internship.user_id == user_id)
            .first()
        )
        if not log_owned:
            raise NotFoundError("Günlük bulunamadı")

        # Duplicate guard
        existing = db.session.execute(
            db.select(log_topics).where(
                (log_topics.c.log_id == log_id) & (log_topics.c.topic_id == topic_id)
            )
        ).first()
        if existing:
            return

        try:
            db.session.execute(
                log_topics.insert().values(
                    log_id=log_id, topic_id=topic_id, is_ai_suggested=is_ai_suggested
                )
            )
            if commit:
                db.session.commit()
            else:
                db.session.flush()
        except IntegrityError as e:
            if commit:
                db.session.rollback()
            err_str = str(e).lower()
            orig_str = str(getattr(e, "orig", "")).lower()
            combined = err_str + " " + orig_str
            if "foreign key" in combined:
                logger.warning("Foreign key violation on log_topics insert log_id=%s topic_id=%s: %s", log_id, topic_id, e)
                raise BadRequestError("Geçersiz log veya topic")
            logger.debug("log_topics insert conflict log_id=%s topic_id=%s", log_id, topic_id)
