"""Tag model for StajOS (architecture.md:110-117)."""

import uuid

from app.extensions import db
from app.utils.time import iso_or_none, utcnow as _utcnow

__all__ = ["Tag", "log_tags"]

# Association table: daily_logs <-> tags
log_tags = db.Table(
    "log_tags",
    db.Column("log_id", db.String(36), db.ForeignKey("daily_logs.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.String(36), db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(db.Model):
    """User-scoped tag for daily logs."""

    __tablename__ = "tags"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "normalized_name", name="uq_tags_user_normalized"),
    )

    user = db.relationship("User", backref=db.backref("tags", lazy="dynamic", cascade="all, delete-orphan"))

    # Many-to-many to DailyLog
    daily_logs = db.relationship(
        "DailyLog",
        secondary=log_tags,
        backref=db.backref("tags", lazy="select"),
        lazy="dynamic",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "created_at": iso_or_none(self.created_at),
        }

    def __repr__(self):
        return f"<Tag {self.id} {self.name}>"
