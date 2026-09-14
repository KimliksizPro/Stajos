import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _env_bool(name, default):
    value = os.getenv(name)
    return default if value is None else value.lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    AI_ENABLED = _env_bool("AI_ENABLED", False)
    AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
    AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
    AI_MAX_WORKERS = int(os.getenv("AI_MAX_WORKERS", "2"))
    AI_RECOVERY_ENABLED = _env_bool("AI_RECOVERY_ENABLED", True)
    AI_RECOVERY_BATCH_SIZE = int(os.getenv("AI_RECOVERY_BATCH_SIZE", "100"))
    AI_STALE_AFTER_SECONDS = int(os.getenv("AI_STALE_AFTER_SECONDS", "300"))

    @classmethod
    def validate_ai(cls):
        if not cls.AI_ENABLED:
            return
        for setting in ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL"):
            if not getattr(cls, setting):
                raise ValueError(f"{setting} must be set when AI is enabled")
        for setting in (
            "AI_TIMEOUT_SECONDS",
            "AI_MAX_WORKERS",
            "AI_RECOVERY_BATCH_SIZE",
            "AI_STALE_AFTER_SECONDS",
        ):
            if getattr(cls, setting) <= 0:
                raise ValueError(f"{setting} must be positive")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'stajos_dev.db'}"
    )


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-jwt-secret-min-32-chars-long-please"
    AI_ENABLED = False
    AI_RECOVERY_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")

    @classmethod
    def validate(cls):
        if not os.getenv("DATABASE_URL"):
            raise ValueError("DATABASE_URL must be set in production")
        secret = os.getenv("SECRET_KEY", "")
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        if not secret or not jwt_secret:
            raise ValueError("SECRET_KEY and JWT_SECRET_KEY must be set in production")
        if len(secret) < 32 or secret == "dev-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be at least 32 characters and not the default dev value")
        if len(jwt_secret) < 32 or jwt_secret == "dev-jwt-secret-change-in-production":
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters and not the default dev value")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
