from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.core.exceptions import BadRequestError
from app.core.response import success_response
from app.services.topic_service import TopicService

learning_bp = Blueprint("learning", __name__, url_prefix="/api/v1/topics")

__all__ = ["learning_bp"]


@learning_bp.route("", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_topic() -> tuple:
    """Create topic endpoint."""
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    description = data.get("description")
    parent_id = data.get("parent_id")

    if not name or not str(name).strip():
        raise BadRequestError("name zorunludur")

    topic = TopicService.create_topic(
        user_id=user_id,
        name=name,
        description=description,
        parent_id=parent_id,
    )
    return success_response(data=topic.to_dict(), status=201)


@learning_bp.route("/tree", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_tree() -> tuple:
    """Get topic tree endpoint."""
    user_id = get_jwt_identity()
    tree = TopicService.get_tree(user_id)
    return success_response(data=tree, status=200)


@learning_bp.route("/<string:topic_id>/progress", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_progress(topic_id: str) -> tuple:
    """Get topic progress endpoint."""
    user_id = get_jwt_identity()
    progress = TopicService.get_progress(user_id, topic_id)
    return success_response(data=progress, status=200)
