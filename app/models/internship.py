"""Internship model for StajOS."""

import enum
import uuid

from app.extensions import db
from app.utils.time import iso_or_none, utcnow as _utcnow

__all__ = ["Internship", "InternshipStatus"]


class InternshipStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"


class Internship(db.Model):
    __tablename__ = "internships"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_name = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_expected_days = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.Enum(InternshipStatus, name="internship_status"),
        nullable=False,
        default=InternshipStatus.ACTIVE,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    user = db.relationship("User", backref=db.backref("internships", lazy="dynamic"))
    # daily_logs relationship is declared on DailyLog side via backref="internship".
    # When app/models/daily_log.py is added (Faz 2 - DailyLog domain), the
    # DailyLog model should define:
    #   internship = db.relationship("Internship", backref=db.backref("daily_logs", lazy="dynamic", cascade="all, delete-orphan"))
    # Keeping string reference here would break mapper configuration until
    # DailyLog class is importable (SQLAlchemy InvalidRequestError), so the
    # explicit relationship is deferred to DailyLog model.

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "start_date": iso_or_none(self.start_date),
            "end_date": iso_or_none(self.end_date),
            "total_expected_days": self.total_expected_days,
            "status": self.status.value if isinstance(self.status, InternshipStatus) else str(self.status),
            "created_at": iso_or_none(self.created_at),
            "updated_at": iso_or_none(self.updated_at),
        }

    def __repr__(self):
        return f"<Internship {self.id} {self.company_name}>"
