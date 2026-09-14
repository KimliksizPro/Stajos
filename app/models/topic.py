"""Topic model for StajOS - tree structure for learning topics (architecture.md:96-108)."""

import uuid

from app.extensions import db
from app.utils.time import iso_or_none, utcnow as _utcnow
from app.utils.validators import today_utc

__all__ = ["Topic", "log_topics"]

# Association table: daily_logs <-> topics (architecture.md:105-108)
log_topics = db.Table(
    "log_topics",
    db.Column("log_id", db.String(36), db.ForeignKey("daily_logs.id", ondelete="CASCADE"), primary_key=True),
    db.Column("topic_id", db.String(36), db.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
    db.Column("is_ai_suggested", db.Boolean, nullable=False, default=False, server_default=db.text("0")),
)


class Topic(db.Model):
    """Learning topic with self-referential tree (architecture.md:96-104)."""

    __tablename__ = "topics"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = db.Column(db.String(36), db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    normalized_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    first_seen_at = db.Column(db.Date, nullable=False, default=today_utc)
    usage_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "parent_id", "normalized_name", name="uq_topics_user_parent_normalized"),
    )

    # Self-referential tree
    parent = db.relationship("Topic", remote_side=[id], backref=db.backref("children", lazy="dynamic", cascade="all, delete-orphan"))
    user = db.relationship("User", backref=db.backref("topics", lazy="dynamic", cascade="all, delete-orphan"))

    # Many-to-many to DailyLog via log_topics
    daily_logs = db.relationship(
        "DailyLog",
        secondary=log_topics,
        backref=db.backref("topics", lazy="select"),
        lazy="dynamic",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "description": self.description,
            "first_seen_at": iso_or_none(self.first_seen_at),
            "usage_count": self.usage_count,
            "created_at": iso_or_none(self.created_at),
            "updated_at": iso_or_none(self.updated_at),
        }

    def __repr__(self):
        return f"<Topic {self.id} {self.name}>"
