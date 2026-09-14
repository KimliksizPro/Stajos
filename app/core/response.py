from flask import jsonify

from typing import Any

__all__ = ["success_response", "error_response"]


def success_response(data: Any = None, meta: Any = None, status: int = 200) -> tuple:
    """Build success JSON response."""
    return jsonify({"success": True, "data": data, "meta": meta, "errors": []}), status


def error_response(errors: Any, status: int = 400, data: Any = None, meta: Any = None) -> tuple:
    """Build error JSON response."""
    if isinstance(errors, str):
        errors = [errors]
    return jsonify({"success": False, "data": data, "meta": meta, "errors": errors}), status
