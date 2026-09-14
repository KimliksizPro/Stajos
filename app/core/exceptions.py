import logging

from app.core.response import error_response

__all__ = [
    "AppError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "register_error_handlers",
]


class AppError(Exception):
    status_code = 400
    message = "Application error"

    def __init__(self, message=None, status_code=None, errors=None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        self.errors = errors or []


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401
    message = "Unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    message = "Forbidden"


class NotFoundError(AppError):
    status_code = 404
    message = "Resource not found"


class ConflictError(AppError):
    status_code = 409


class ValidationError(AppError):
    status_code = 422


def register_error_handlers(app):
    from marshmallow import ValidationError as MarshmallowValidationError

    @app.errorhandler(AppError)
    def handle_app_error(e):
        errors = e.errors if e.errors else ([e.message] if isinstance(e.message, str) else e.message if isinstance(e.message, list) else [str(e.message)])
        return error_response(errors=errors, status=e.status_code)

    @app.errorhandler(MarshmallowValidationError)
    def handle_marshmallow_error(e):
        return error_response(errors=e.messages, status=422)

    @app.errorhandler(404)
    def handle_404(e):
        return error_response(errors=["Endpoint not found"], status=404)

    @app.errorhandler(405)
    def handle_405(e):
        return error_response(errors=["Method not allowed"], status=405)

    @app.errorhandler(500)
    def handle_500(e):
        logging.getLogger(__name__).exception("Unhandled 500")
        return error_response(errors=["Internal server error"], status=500)

    # JWTManager callbacks are registered in app/__init__.py via @jwt.*_loader (no duplicate handler here)
    return app
