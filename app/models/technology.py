"""Technology model for StajOS (architecture.md:87-94)."""

import uuid

from app.extensions import db
from app.utils.time import iso_or_none, utcnow as _utcnow

__all__ = ["Technology", "log_technologies"]

# Association table: daily_logs <-> technologies
log_technologies = db.Table(
    "log_technologies",
    db.Column("log_id", db.String(36), db.ForeignKey("daily_logs.id", ondelete="CASCADE"), primary_key=True),
    db.Column(
        "technology_id", db.String(36), db.ForeignKey("technologies.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Technology(db.Model):
    """Technology mastered/used in daily logs."""

    __tablename__ = "technologies"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # Many-to-many to DailyLog
    daily_logs = db.relationship(
        "DailyLog",
        secondary=log_technologies,
        backref=db.backref("technologies", lazy="select"),
        lazy="dynamic",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "created_at": iso_or_none(self.created_at),
        }

    def __repr__(self):
        return f"<Technology {self.id} {self.name}>"
