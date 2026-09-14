"""Security helpers for password hashing (simple, personal use)."""
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password: str) -> str:
    """Hash password using werkzeug default (pbkdf2:sha256)."""
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify password against hash."""
    return check_password_hash(password_hash, password)
