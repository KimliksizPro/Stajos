import enum
import uuid

from app.extensions import db
from app.utils.time import iso_or_none, utcnow as _utcnow

__all__ = ["DailyLog", "AIStatus"]


class AIStatus(enum.Enum):
    """AI processing status for daily logs (architecture.md:77)."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    REFINED = "REFINED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class DailyLog(db.Model):
    """Daily log model - one entry per internship per date (architecture.md:66-79)."""

    __tablename__ = "daily_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    internship_id = db.Column(
        db.String(36),
        db.ForeignKey("internships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = db.Column(db.Date, nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(255), nullable=False)
    raw_content = db.Column(db.Text, nullable=False)
    ai_refined_content = db.Column(db.Text, nullable=True)
    ai_suggested_technologies = db.Column(db.JSON, nullable=True)
    ai_suggested_topics = db.Column(db.JSON, nullable=True)
    ai_suggested_tags = db.Column(db.JSON, nullable=True)
    ai_processing_started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ai_status = db.Column(
        db.Enum(AIStatus, name="ai_status"),
        nullable=False,
        default=AIStatus.PENDING,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("internship_id", "date", name="uq_daily_logs_internship_date"),
    )

    # Relationship to Internship - backref creates Internship.daily_logs (lazy dynamic)
    internship = db.relationship(
        "Internship",
        backref=db.backref("daily_logs", lazy="dynamic", cascade="all, delete-orphan"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "internship_id": self.internship_id,
            "date": iso_or_none(self.date),
            "day_number": self.day_number,
            "start_time": iso_or_none(self.start_time),
            "end_time": iso_or_none(self.end_time),
            "duration_minutes": self.duration_minutes,
            "title": self.title,
            "raw_content": self.raw_content,
            "ai_refined_content": self.ai_refined_content,
            "ai_suggested_technologies": self.ai_suggested_technologies or [],
            "ai_suggested_topics": self.ai_suggested_topics or [],
            "ai_suggested_tags": self.ai_suggested_tags or [],
            "ai_status": self.ai_status.value
            if isinstance(self.ai_status, AIStatus)
            else str(self.ai_status),
            "created_at": iso_or_none(self.created_at),
            "updated_at": iso_or_none(self.updated_at),
        }

    def __repr__(self):
        return f"<DailyLog {self.id} day={self.day_number} date={self.date}>"
