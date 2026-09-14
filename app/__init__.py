import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.core.response import error_response, success_response

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(dotenv_path=BASE_DIR / ".env")

from app.extensions import db, migrate, jwt
from config import config_by_name


def create_app(config_name: str = None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.config.from_object(config_by_name[config_name])
    if config_name == "production":
        config_by_name[config_name].validate()

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # AI wiring (Faz 5 Task 5): disabled -> no client/executor/extensions.
    # Recovery is NOT auto-run here; call start_ai_recovery explicitly from
    # the real startup path after migrations (never during tests/CLI migrate).
    from app.ai.factory import create_ai_executor, create_ai_provider

    _ai_provider = create_ai_provider(app.config)
    if _ai_provider is not None:
        create_ai_executor(app, _ai_provider)

    # JWT error handlers -> standardized response format
    @jwt.unauthorized_loader
    def handle_missing_token(reason):
        return error_response(errors=[reason], status=401)

    @jwt.invalid_token_loader
    def handle_invalid_token(reason):
        return error_response(errors=[reason], status=401)

    @jwt.expired_token_loader
    def handle_expired_token(jwt_header, jwt_payload):
        return error_response(errors=["Token süresi dolmuş"], status=401)

    @jwt.revoked_token_loader
    def handle_revoked(jwt_header, jwt_payload):
        return error_response(errors=["Token iptal edilmiş"], status=401)

    from app.models import User, Internship, DailyLog, Topic, Technology, Tag  # noqa: F401 - register models for Alembic

    # Register blueprints
    from app.api.v1.auth_routes import auth_bp
    from app.api.v1.dashboard_routes import dashboard_bp
    from app.api.v1.internship_routes import internship_bp
    from app.api.v1.log_routes import log_bp
    from app.api.v1.learning_routes import learning_bp
    from app.api.v1.export_routes import export_bp
    from app.api.v1.timeline_routes import timeline_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(internship_bp)
    app.register_blueprint(log_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(timeline_bp)

    # Health check
    @app.route("/api/v1/health", methods=["GET"], strict_slashes=False)
    def health():
        return success_response(data={"status": "ok"}, status=200)

    # Global error handlers
    from app.core.exceptions import register_error_handlers
    register_error_handlers(app)

    return app
