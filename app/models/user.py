"""User model for StajOS."""

import uuid

from app.extensions import db
from app.utils.time import iso_or_none, utcnow as _utcnow

__all__ = ["User"]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships (prepared for future phases, no cascade side-effects yet)
    # internships = db.relationship("Internship", backref="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": iso_or_none(self.created_at),
        }
