from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.log_service import LogService
from app.core.response import success_response
from app.core.exceptions import BadRequestError
from app.core.pagination import get_pagination_params

__all__ = ["log_bp"]

log_bp = Blueprint("logs", __name__, url_prefix="/api/v1/logs")


@log_bp.route("", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_log():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    internship_id = data.get("internship_id")
    title = data.get("title")
    raw_content = data.get("raw_content")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    # Optional date override for testing/backfill (YYYY-MM-DD)
    date_override = data.get("date")
    technologies = data.get("technologies")
    tags = data.get("tags")
    topics = data.get("topics")

    if internship_id is None or title is None or raw_content is None:
        raise BadRequestError("internship_id, title ve raw_content zorunludur")

    if technologies is not None and not isinstance(technologies, list):
        raise BadRequestError("technologies liste olmalı")
    if tags is not None and not isinstance(tags, list):
        raise BadRequestError("tags liste olmalı")
    if topics is not None and not isinstance(topics, list):
        raise BadRequestError("topics liste olmalı")

    log = LogService.create_log(
        user_id=user_id,
        internship_id=internship_id,
        title=title,
        raw_content=raw_content,
        start_time_str=start_time,
        end_time_str=end_time,
        date_override=date_override,
        technologies=technologies,
        tags=tags,
        topics=topics,
    )
    return success_response(data=log.to_dict(), status=201)


@log_bp.route("", methods=["GET"], strict_slashes=False)
@jwt_required()
def list_logs():
    user_id = get_jwt_identity()
    internship_id = request.args.get("internship_id")
    if not internship_id:
        raise BadRequestError("internship_id query parametresi zorunludur")

    page, per_page = get_pagination_params(default_per_page=20, max_per_page=100)
    search = request.args.get("search")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    tech = request.args.get("tech")
    tag = request.args.get("tag")
    topic = request.args.get("topic")
    sort = request.args.get("sort")
    order = request.args.get("order")

    items, total = LogService.get_logs(
        user_id=user_id,
        internship_id=internship_id,
        page=page,
        per_page=per_page,
        search=search,
        start_date=start_date,
        end_date=end_date,
        tech=tech,
        tag=tag,
        topic=topic,
        sort=sort,
        order=order,
    )
    data = [item.to_dict() for item in items]
    meta = {"page": page, "per_page": per_page, "total": total}
    return success_response(data=data, meta=meta, status=200)


@log_bp.route("/<string:log_id>", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_log(log_id: str):
    user_id = get_jwt_identity()
    log = LogService.get_log_by_id(user_id=user_id, log_id=log_id)
    return success_response(data=log.to_dict(), status=200)


@log_bp.route("/<string:log_id>/accept-ai", methods=["PUT"], strict_slashes=False)
@jwt_required()
def accept_ai(log_id: str):
    user_id = get_jwt_identity()
    log = LogService.accept_ai(user_id=user_id, log_id=log_id)
    return success_response(data=log.to_dict(), status=200)


@log_bp.route("/<string:log_id>/reject-ai", methods=["PUT"], strict_slashes=False)
@jwt_required()
def reject_ai(log_id: str):
    user_id = get_jwt_identity()
    log = LogService.reject_ai(user_id=user_id, log_id=log_id)
    return success_response(data=log.to_dict(), status=200)
