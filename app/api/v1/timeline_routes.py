from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.core.exceptions import BadRequestError
from app.core.response import success_response
from app.services.timeline_service import TimelineService
from app.utils.validators import parse_date

__all__ = ["timeline_bp"]

timeline_bp = Blueprint("timeline", __name__, url_prefix="/api/v1/timeline")


@timeline_bp.route("", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_timeline():
    user_id = get_jwt_identity()
    internship_id = request.args.get("internship_id")
    if not internship_id or not str(internship_id).strip():
        raise BadRequestError("internship_id query parametresi zorunludur")

    year_raw = request.args.get("year")
    month_raw = request.args.get("month")
    start_date_raw = request.args.get("start_date")
    end_date_raw = request.args.get("end_date")

    year = None
    month = None

    # Validate year/month pairing
    has_year = year_raw is not None and str(year_raw).strip() != ""
    has_month = month_raw is not None and str(month_raw).strip() != ""
    if has_year ^ has_month:
        raise BadRequestError("year ve month birlikte verilmeli")

    if has_year and has_month:
        try:
            year = int(str(year_raw).strip())
        except (ValueError, TypeError):
            raise BadRequestError("year sayı olmalı")
        try:
            month = int(str(month_raw).strip())
        except (ValueError, TypeError):
            raise BadRequestError("month sayı olmalı")
        if not 2000 <= year <= 2100:
            raise BadRequestError("year 2000-2100 arasında olmalı")
        if not 1 <= month <= 12:
            raise BadRequestError("month 1-12 arasında olmalı")

    s_date = None
    e_date = None
    if start_date_raw is not None and str(start_date_raw).strip() != "":
        s_date = parse_date(start_date_raw, "start_date")
    if end_date_raw is not None and str(end_date_raw).strip() != "":
        e_date = parse_date(end_date_raw, "end_date")

    if (has_year or has_month) and (s_date is not None or e_date is not None):
        raise BadRequestError("year/month ile start_date/end_date birlikte kullanılamaz")

    if s_date is not None and e_date is not None and s_date > e_date:
        raise BadRequestError("start_date end_date'den sonra olamaz")

    timeline, meta = TimelineService.get_timeline(
        user_id=user_id,
        internship_id=internship_id,
        year=year,
        month=month,
        start_date=s_date,
        end_date=e_date,
    )
    return success_response(data=timeline, meta=meta, status=200)
