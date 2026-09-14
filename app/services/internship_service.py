"""InternshipService - Business logic for internships domain.

SSOT: architecture.md:1.1, docs/kurallar.md:4
"""

from datetime import date

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.extensions import db
from app.models.internship import Internship, InternshipStatus
from app.utils.validators import parse_date

__all__ = ["InternshipService"]


class InternshipService:
    """Service Layer for internships domain. No HTTP logic here (kurallar.md:4, architecture.md:1.1)."""

    @staticmethod
    def create_internship(
        user_id: str,
        company_name: str,
        start_date,
        end_date,
        total_expected_days,
    ) -> Internship:
        if not user_id:
            raise BadRequestError("user_id zorunludur")

        company_name = (company_name or "").strip()
        if not company_name:
            raise BadRequestError("Şirket adı zorunludur")
        if len(company_name) > 255:
            raise BadRequestError("Şirket adı en fazla 255 karakter olabilir")

        s_date = parse_date(start_date, "start_date")
        e_date = parse_date(end_date, "end_date")

        if s_date > e_date:
            raise BadRequestError("Başlangıç tarihi bitiş tarihinden sonra olamaz")

        # total_expected_days validation
        if total_expected_days is None or (isinstance(total_expected_days, str) and not total_expected_days.strip()):
            raise BadRequestError("total_expected_days zorunludur")
        try:
            total_expected_days = int(total_expected_days)
        except (ValueError, TypeError):
            raise BadRequestError("total_expected_days sayı olmalı")
        if total_expected_days <= 0:
            raise BadRequestError("total_expected_days 0'dan büyük olmalı")

        # Solo mode: only one ACTIVE internship per user
        existing = Internship.query.filter_by(user_id=user_id, status=InternshipStatus.ACTIVE).first()
        if existing:
            raise ConflictError("Zaten aktif bir stajınız bulunuyor. Önce mevcut stajı tamamlayın veya duraklatın.")

        internship = Internship(
            user_id=user_id,
            company_name=company_name,
            start_date=s_date,
            end_date=e_date,
            total_expected_days=total_expected_days,
            status=InternshipStatus.ACTIVE,
        )
        db.session.add(internship)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ConflictError("Zaten aktif staj var")
        return internship

    @staticmethod
    def get_active_internship(user_id: str) -> Internship:
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        internship = Internship.query.filter_by(user_id=user_id, status=InternshipStatus.ACTIVE).first()
        if not internship:
            raise NotFoundError("Aktif staj bulunamadı")
        return internship

    @staticmethod
    def get_by_id(user_id: str, internship_id: str) -> Internship:
        """Fetch by id with mandatory user_id filter (kurallar.md:31 - veri izolasyonu)."""
        if not user_id or not internship_id:
            raise BadRequestError("user_id ve internship_id zorunludur")
        internship = Internship.query.filter_by(id=internship_id, user_id=user_id).first()
        if not internship:
            raise NotFoundError("Staj bulunamadı")
        return internship

    @staticmethod
    def list_by_user(user_id: str):
        """Helper: list all internships for user (ordered by created_at desc)."""
        if not user_id:
            raise BadRequestError("user_id zorunludur")
        return Internship.query.filter_by(user_id=user_id).order_by(Internship.created_at.desc()).all()
