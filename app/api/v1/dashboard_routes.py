from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.core.response import success_response
from app.services.stats_service import StatsService

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")

__all__ = ["dashboard_bp"]


@dashboard_bp.route("/stats", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_dashboard_stats():
    """GET /api/v1/dashboard/stats - Dashboard statistics."""
    user_id = get_jwt_identity()
    internship_id = request.args.get("internship_id")
    if internship_id is not None:
        internship_id = str(internship_id).strip() or None
    data = StatsService.get_dashboard_stats(user_id=user_id, internship_id=internship_id)
    return success_response(data=data, status=200)
