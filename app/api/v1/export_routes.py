# app/api/v1/export_routes.py
from flask import Blueprint, Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.core.response import success_response
from app.services.export_service import EXPORT_MAX_ROWS, ExportService
from app.utils.exporters import logs_to_csv_rows

export_bp = Blueprint("export", __name__, url_prefix="/api/v1/export")

__all__ = ["export_bp"]

def _export_meta(rows: list, truncated: bool) -> dict:
    return {"total": len(rows), "limit": EXPORT_MAX_ROWS, "truncated": truncated}

@export_bp.route("/json", methods=["GET"], strict_slashes=False)
@jwt_required()
def export_json():
    user_id = get_jwt_identity()
    internship_id = request.args.get("internship_id") or None
    rows, truncated = ExportService.get_export_dicts(user_id, internship_id)
    return success_response(data=rows, meta=_export_meta(rows, truncated), status=200)

@export_bp.route("/csv", methods=["GET"], strict_slashes=False)
@jwt_required()
def export_csv():
    user_id = get_jwt_identity()
    internship_id = request.args.get("internship_id") or None
    rows, _truncated = ExportService.get_export_dicts(user_id, internship_id)
    csv_text = logs_to_csv_rows(rows)
    return Response(csv_text, mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=stajos-export.csv"})
