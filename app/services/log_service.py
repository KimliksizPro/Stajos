"""LogService - Business logic for daily_logs domain (Faz 2).

SSOT: architecture.md:66-79, 211-218, 253-259, docs/agents.md:40-43,57
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.extensions import db
from app.models.daily_log import AIStatus, DailyLog
from app.models.internship import Internship
from app.services.tag_service import TagService
from app.services.technology_service import TechnologyService
from app.services.topic_service import TopicService
from app.utils.date_calculator import calculate_day_number, calculate_duration_minutes, is_weekend
from app.utils.validators import parse_date, parse_time, today_utc

logger = logging.getLogger(__name__)

__all__ = ["LogService"]


class LogService:
    """Service Layer for daily_logs (no HTTP logic, kurallar.md:4)."""

    @staticmethod
    def _find_or_create_topic(user_id: str, topic_name: str, commit: bool = True):
        """Find existing topic (case-insensitive, parent_id None) or create (DRY helper).

        Delegates directly to TopicService.get_or_create for DRY and correct
        UniqueConstraint handling (Faz3: user_id+parent_id+normalized_name).
        Uses Topic.normalized_name semantics, not lower(name).
        """
        return TopicService.get_or_create(user_id, topic_name, parent_id=None, commit=commit)

    @staticmethod
    def create_log(
        user_id: str,
        internship_id: str,
        title: str,
        raw_content: str,
        start_time_str=None,
        end_time_str=None,
        date_override=None,
        technologies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        topics: Optional[List] = None,
        ai_executor=None,
    ) -> DailyLog:
        """Create a new daily log with ownership, day_number and duration logic.

        Args:
            user_id: Current user id (from JWT).
            internship_id: Target internship id.
            title: Log title.
            raw_content: Raw content (never overwritten by AI).
            start_time_str: Optional start time as 'HH:MM' string or time object.
            end_time_str: Optional end time as 'HH:MM' string or time object.
            date_override: Optional date string/date object for testing/backfill.
                           If None, uses today UTC.
            technologies: Optional list of technology names (global).
            tags: Optional list of tag names (user-scoped).
            topics: Optional list of topic names or dicts with 'name'.

        Returns:
            Created DailyLog instance.

        Raises:
            BadRequestError: Validation failures.
            NotFoundError: Internship not found / not owned.
            ConflictError: Duplicate log for same internship+date (409).
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        if not internship_id:
            raise BadRequestError("internship_id zorunludur")

        title = (title or "").strip()
        if not title:
            raise BadRequestError("Başlık zorunludur")
        if len(title) > 255:
            raise BadRequestError("Başlık en fazla 255 karakter olabilir")

        raw_content = (raw_content or "").strip()
        if not raw_content:
            raise BadRequestError("İçerik (raw_content) zorunludur")
        if len(raw_content) > 50000:
            raise BadRequestError("İçerik çok uzun (maks 50000 karakter)")

        # Ownership check: internship must belong to user
        internship = Internship.query.filter_by(id=internship_id, user_id=user_id).first()
        if not internship:
            raise NotFoundError("Staj bulunamadı veya yetkiniz yok")

        # Date handling: override or today UTC
        if date_override is not None:
            target_date = parse_date(date_override, "date")
        else:
            target_date = today_utc()

        # Future date guard (Solo DoS / data quality)
        if target_date > today_utc():
            raise BadRequestError("Gelecek tarih için günlük oluşturulamaz")

        # Calculate day_number skipping weekends (architecture.md:253-259)
        try:
            day_number = calculate_day_number(internship.start_date, target_date)
        except ValueError as e:
            raise BadRequestError(str(e))
        except TypeError as e:
            raise BadRequestError(str(e))

        if day_number == 0:
            raise BadRequestError("Hafta sonu için günlük oluşturulamaz")
        if is_weekend(target_date):
            raise BadRequestError("Hafta sonu için günlük oluşturulamaz")

        # Duration calculation if both times provided
        start_t = parse_time(start_time_str, "start_time")
        end_t = parse_time(end_time_str, "end_time")

        duration = None
        # Only calculate if at least one provided; if only one provided keep other None and duration None
        if start_t is not None or end_t is not None:
            # If only one side provided, treat as incomplete -> duration stays None
            # But if both provided, calculate and validate end > start
            if start_t is not None and end_t is not None:
                try:
                    duration = calculate_duration_minutes(start_t, end_t)
                except ValueError as e:
                    raise BadRequestError(str(e))
            else:
                # One missing -> duration None, keep times as is
                duration = None
                # Optional: if you want to enforce both together, uncomment:
                # raise BadRequestError("start_time ve end_time birlikte verilmeli")

        # Duplicate check: unique per internship per date (409)
        existing = DailyLog.query.filter_by(internship_id=internship_id, date=target_date).first()
        if existing:
            raise ConflictError("Bu tarih için zaten bir günlük mevcut (aynı stajda aynı günde tek log)")

        log = DailyLog(
            internship_id=internship_id,
            date=target_date,
            day_number=day_number,
            start_time=start_t,
            end_time=end_t,
            duration_minutes=duration,
            title=title,
            raw_content=raw_content,
            ai_refined_content=None,
            ai_status=AIStatus.PENDING,
        )
        db.session.add(log)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ConflictError("Bu tarih için zaten bir günlük mevcut")

        # Faz3: Link technologies/tags/topics after log commit (log.id available)
        # Failures are silent (log.error) and do not rollback the log.
        if technologies:
            try:
                TechnologyService.link_to_log(log.id, technologies)
            except Exception as e:
                logger.error("Failed to link technologies for log %s: %s", log.id, e)
        if tags:
            try:
                TagService.link_to_log(log.id, user_id, tags)
            except Exception as e:
                logger.error("Failed to link tags for log %s: %s", log.id, e)
        if topics:
            try:
                for item in topics:
                    if item is None:
                        continue
                    if isinstance(item, dict):
                        topic_name = item.get("name") or item.get("title") or ""
                    else:
                        topic_name = str(item)
                    topic_name = topic_name.strip()
                    if not topic_name:
                        continue
                    existing_topic = LogService._find_or_create_topic(user_id, topic_name, commit=False)
                    if not existing_topic:
                        continue
                    TopicService.link_to_log(
                        user_id,
                        log.id,
                        existing_topic.id,
                        is_ai_suggested=False,
                        commit=False,
                    )
                    TopicService.increment_usage(user_id, existing_topic.id, commit=False)
                db.session.commit()
            except (BadRequestError, ConflictError, IntegrityError) as e:
                db.session.rollback()
                logger.warning("Failed to link topics for log %s: %s", log.id, e)
            except Exception:
                db.session.rollback()
                logger.exception("Unexpected error linking topics for log %s", log.id)

        # TODO Faz5: AI async processing via threading.Thread
        # try:
        #     import threading
        #     from app.services.ai_service import process_log_ai  # Faz5
        #     thread = threading.Thread(target=process_log_ai, args=(log.id,))
        #     thread.daemon = True
        #     thread.start()
        # except Exception:
        #     # Do not fail request if thread spawn fails; log error and set ai_status=ERROR inside thread
        #     pass

        # Faz5 Task 5: submit only after successful commit. Submission failure
        # logs a warning and leaves ai_status=PENDING for startup recovery.
        executor = ai_executor
        if executor is None:
            try:
                from flask import current_app, has_app_context

                if has_app_context() and current_app:
                    executor = current_app.extensions.get("ai_executor")
            except Exception:
                executor = None
        if executor is not None:
            try:
                executor.submit(log.id)
            except Exception:
                logger.warning("AI submission failed for log %s", log.id)

        return log

    @staticmethod
    def get_logs(
        user_id: str,
        internship_id: str,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        start_date=None,
        end_date=None,
        tech: Optional[str] = None,
        tag: Optional[str] = None,
        topic: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> Tuple[List[DailyLog], int]:
        """List logs with mandatory user+internship isolation and optional filters.

        Args:
            user_id: Current user id.
            internship_id: Internship to filter by (required).
            page: Page number (1-indexed).
            per_page: Items per page.
            search: Optional search term for title/raw_content.
            start_date: Optional filter start date (inclusive).
            end_date: Optional filter end date (inclusive).
            tech: Optional technology filter (exact normalized match).
            tag: Optional tag filter (exact normalized match, user-scoped).
            topic: Optional topic filter (exact normalized match, user-scoped) -> log_topics join.
            sort: Optional sort field: 'date' (default) or 'day_number'.
            order: Optional sort direction: 'asc' or 'desc' (default desc).

        Returns:
            (items, total) tuple for pagination.

        Raises:
            BadRequestError: Missing params.
            NotFoundError: Internship not found/owned.
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        if not internship_id:
            raise BadRequestError("internship_id zorunludur (query param gerekli)")

        internship = Internship.query.filter_by(id=internship_id, user_id=user_id).first()
        if not internship:
            raise NotFoundError("Staj bulunamadı veya yetkiniz yok")

        query = DailyLog.query.filter_by(internship_id=internship_id)

        if search:
            search = search.strip()
            if search:
                escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                like = f"%{escaped}%"
                query = query.filter(
                    db.or_(
                        DailyLog.title.ilike(like, escape="\\"),
                        DailyLog.raw_content.ilike(like, escape="\\"),
                    )
                )

        if start_date is not None:
            s_date = parse_date(start_date, "start_date")
            query = query.filter(DailyLog.date >= s_date)
        if end_date is not None:
            e_date = parse_date(end_date, "end_date")
            query = query.filter(DailyLog.date <= e_date)

        # Tech filter (global, exact normalized match)
        if tech is not None and str(tech).strip():
            from app.models.technology import Technology, log_technologies

            normalized_tech = TechnologyService.normalize(tech)
            query = (
                query.join(log_technologies, log_technologies.c.log_id == DailyLog.id)
                .join(Technology, Technology.id == log_technologies.c.technology_id)
                .filter(Technology.normalized_name == normalized_tech)
            )

        # Tag filter (user-scoped, exact normalized match)
        if tag is not None and str(tag).strip():
            from app.models.tag import Tag, log_tags

            normalized_tag = TagService.normalize(tag)
            query = (
                query.join(log_tags, log_tags.c.log_id == DailyLog.id)
                .join(Tag, Tag.id == log_tags.c.tag_id)
                .filter(Tag.normalized_name == normalized_tag)
                .filter(Tag.user_id == user_id)
            )

        # Topic filter (user-scoped, exact normalized match via log_topics join)
        if topic is not None and str(topic).strip():
            from app.models.topic import Topic, log_topics
            from app.utils.validators import normalize_name

            normalized_topic = normalize_name(topic)
            query = (
                query.join(log_topics, log_topics.c.log_id == DailyLog.id)
                .join(Topic, Topic.id == log_topics.c.topic_id)
                .filter(Topic.normalized_name == normalized_topic)
                .filter(Topic.user_id == user_id)
            )

        # Distinct after joins to avoid duplicates
        if (
            (tech and str(tech).strip())
            or (tag and str(tag).strip())
            or (topic and str(topic).strip())
        ):
            query = query.distinct()

        # N+1 guard: eager load M2M relationships (kurallar.md:75)
        # Backref relationships exist via Technology/Tag/Topic models
        try:
            query = query.options(
                selectinload(DailyLog.technologies),
                selectinload(DailyLog.tags),
            )
            # topics may also be eager loaded if relationship exists
            if hasattr(DailyLog, "topics"):
                query = query.options(selectinload(DailyLog.topics))
        except Exception as error:
            # If relationships not configured (e.g., backref not yet built), ignore eager load
            logger.warning("Failed to configure eager loading for log list: %s", error)

        # Sort / order handling (Faz4): date (default desc) or day_number, asc/desc
        allowed_sorts = {
            "date": DailyLog.date,
            "day_number": DailyLog.day_number,
        }
        sort_key = (sort or "date").strip().lower() if sort else "date"
        sort_col = allowed_sorts.get(sort_key, DailyLog.date)
        order_val = (order or "desc").strip().lower() if order else "desc"
        if order_val not in ("asc", "desc"):
            order_val = "desc"
        if order_val == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        total = query.order_by(None).distinct().count()
        # Alternatif PG distinct count: from sqlalchemy import func; total = db.session.query(func.count(func.distinct(DailyLog.id))).select_from(query.subquery()).scalar()
        # Pagination already sanitized via get_pagination_params in route; no clamp here (idempotent - DRY)

        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    @staticmethod
    def get_log_by_id(user_id: str, log_id: str) -> DailyLog:
        """Fetch single log with isolation control (user must own internship).

        Raises:
            BadRequestError, NotFoundError
        """
        if not user_id or not log_id:
            raise BadRequestError("user_id ve log_id zorunludur")

        log = DailyLog.query.filter_by(id=log_id).first()
        if not log:
            raise NotFoundError("Günlük bulunamadı")

        # Verify ownership via internship
        internship = Internship.query.filter_by(id=log.internship_id, user_id=user_id).first()
        if not internship:
            raise NotFoundError("Günlük bulunamadı")

        return log

    @staticmethod
    def get_log_by_date(user_id: str, target_date) -> Optional[DailyLog]:
        """Get log(s) for a specific date across user's internships (MCP hazırlığı).

        This is used by MCP tools: get_today_log(user_id, date).
        Searches all internships owned by user for a log on target_date.

        Args:
            user_id: Current user id.
            target_date: Date string (YYYY-MM-DD) or date object.

        Returns:
            DailyLog if found, otherwise None or raises NotFound if strict.

        Raises:
            BadRequestError: Invalid inputs.
            NotFoundError: No internship/log found (configurable strict).
        """
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        if target_date is None:
            raise BadRequestError("target_date zorunludur")

        t_date = parse_date(target_date, "target_date")

        # Find internships owned by user
        internships = Internship.query.filter_by(user_id=user_id).all()
        if not internships:
            raise NotFoundError("Staj bulunamadı")

        internship_ids = [i.id for i in internships]
        log = (
            DailyLog.query.filter(
                DailyLog.internship_id.in_(internship_ids), DailyLog.date == t_date
            )
            .order_by(DailyLog.created_at.desc())
            .first()
        )
        if not log:
            raise NotFoundError("Bu tarih için günlük bulunamadı")
        return log

    @staticmethod
    def _owner_scoped_log(user_id: str, log_id: str) -> DailyLog:
        """Fetch log with internship ownership (foreign log is 404, never 403)."""
        if not user_id or not log_id:
            raise BadRequestError("user_id ve log_id zorunludur")

        log = DailyLog.query.filter_by(id=log_id).first()
        if not log:
            raise NotFoundError("Günlük bulunamadı")

        internship = Internship.query.filter_by(id=log.internship_id, user_id=user_id).first()
        if not internship:
            raise NotFoundError("Günlük bulunamadı")

        return log

    @staticmethod
    def _suggestion_name(item) -> str:
        """Extract a clean name from an AI suggestion entry (str or dict)."""
        if item is None:
            return ""
        if isinstance(item, dict):
            item = item.get("name") or item.get("title") or ""
        return str(item).strip()

    @staticmethod
    def accept_ai(user_id: str, log_id: str) -> DailyLog:
        """Accept a REFINED AI result atomically (Faz5 Task 6).

        Links suggested technologies/tags via case-insensitive get-or-create,
        matches suggested topics only to the owner's existing root topics
        (parent_id IS NULL, never created). New topic links are AI-suggested
        with usage increment; existing manual links stay manual. raw_content
        and ai_refined_content are never written. Any DB error rolls back
        everything.

        Raises:
            BadRequestError: Missing ids.
            NotFoundError: Log not found / not owned (404, no 403 leak).
            ConflictError: Status is not REFINED (409), incl. repeated accept.
        """
        from app.models.tag import log_tags
        from app.models.technology import log_technologies
        from app.models.topic import Topic, log_topics
        from app.utils.validators import normalize_name

        log = LogService._owner_scoped_log(user_id, log_id)
        if log.ai_status != AIStatus.REFINED:
            raise ConflictError("Yalnızca REFINED günlükler kabul edilebilir")

        tech_names = list(log.ai_suggested_technologies or [])
        tag_names = list(log.ai_suggested_tags or [])
        topic_names = list(log.ai_suggested_topics or [])

        try:
            for raw_item in tech_names:
                name = LogService._suggestion_name(raw_item)
                if not name:
                    continue
                tech = TechnologyService.get_or_create(name, commit=False)
                exists = db.session.execute(
                    db.select(log_technologies).where(
                        (log_technologies.c.log_id == log.id)
                        & (log_technologies.c.technology_id == tech.id)
                    )
                ).first()
                if exists:
                    continue
                db.session.execute(
                    log_technologies.insert().values(log_id=log.id, technology_id=tech.id)
                )
                db.session.flush()

            for raw_item in tag_names:
                name = LogService._suggestion_name(raw_item)
                if not name:
                    continue
                tag = TagService.get_or_create(user_id, name, commit=False)
                exists = db.session.execute(
                    db.select(log_tags).where(
                        (log_tags.c.log_id == log.id) & (log_tags.c.tag_id == tag.id)
                    )
                ).first()
                if exists:
                    continue
                db.session.execute(log_tags.insert().values(log_id=log.id, tag_id=tag.id))
                db.session.flush()

            for raw_item in topic_names:
                name = LogService._suggestion_name(raw_item)
                if not name:
                    continue
                normalized = normalize_name(name)
                if not normalized:
                    continue
                topic = (
                    Topic.query.filter_by(user_id=user_id, normalized_name=normalized)
                    .filter(Topic.parent_id.is_(None))
                    .first()
                )
                if not topic:
                    continue  # never create topics on accept
                exists = db.session.execute(
                    db.select(log_topics).where(
                        (log_topics.c.log_id == log.id)
                        & (log_topics.c.topic_id == topic.id)
                    )
                ).first()
                if exists:
                    continue  # manual stays manual, no double usage increment
                TopicService.link_to_log(
                    user_id, log.id, topic.id, is_ai_suggested=True, commit=False
                )
                TopicService.increment_usage(user_id, topic.id, commit=False)

            log.ai_status = AIStatus.ACCEPTED
            db.session.commit()
        except (BadRequestError, NotFoundError, ConflictError):
            db.session.rollback()
            raise
        except IntegrityError as e:
            db.session.rollback()
            logger.warning("AI accept conflict for log %s: %s", log.id, e)
            raise ConflictError("Kabul işlemi çakışma nedeniyle tamamlanamadı")
        except Exception:
            db.session.rollback()
            raise

        return log

    @staticmethod
    def reject_ai(user_id: str, log_id: str) -> DailyLog:
        """Reject a REFINED AI result (Faz5 Task 6).

        Only flips status to REJECTED; relations and suggestions preserved.

        Raises:
            BadRequestError: Missing ids.
            NotFoundError: Log not found / not owned (404, no 403 leak).
            ConflictError: Status is not REFINED (409), incl. repeated reject.
        """
        log = LogService._owner_scoped_log(user_id, log_id)
        if log.ai_status != AIStatus.REFINED:
            raise ConflictError("Yalnızca REFINED günlükler reddedilebilir")

        log.ai_status = AIStatus.REJECTED
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            logger.warning("AI reject conflict for log %s: %s", log.id, e)
            raise ConflictError("Ret işlemi çakışma nedeniyle tamamlanamadı")
        except Exception:
            db.session.rollback()
            raise

        return log
