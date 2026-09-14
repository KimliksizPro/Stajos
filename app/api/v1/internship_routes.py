from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.internship_service import InternshipService
from app.core.response import success_response
from app.core.exceptions import BadRequestError

internship_bp = Blueprint("internships", __name__, url_prefix="/api/v1/internships")


@internship_bp.route("", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_internship():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    company_name = data.get("company_name")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    total_expected_days = data.get("total_expected_days")

    # Basic presence validation before service (service does deep validation)
    if company_name is None or start_date is None or end_date is None or total_expected_days is None:
        raise BadRequestError("company_name, start_date, end_date ve total_expected_days zorunludur")

    internship = InternshipService.create_internship(
        user_id=user_id,
        company_name=company_name,
        start_date=start_date,
        end_date=end_date,
        total_expected_days=total_expected_days,
    )
    return success_response(data=internship.to_dict(), status=201)


@internship_bp.route("/active", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_active_internship():
    user_id = get_jwt_identity()
    internship = InternshipService.get_active_internship(user_id)
    return success_response(data=internship.to_dict(), status=200)


@internship_bp.route("/<string:internship_id>", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_internship_by_id(internship_id: str):
    user_id = get_jwt_identity()
    internship = InternshipService.get_by_id(user_id, internship_id)
    return success_response(data=internship.to_dict(), status=200)
