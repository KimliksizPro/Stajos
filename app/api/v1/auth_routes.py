from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.services.auth_service import AuthService
from app.core.response import success_response, error_response

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/register", methods=["POST"], strict_slashes=False)
def register():
    data = request.get_json(silent=True) or {}
    user = AuthService.register(
        email=data.get("email", ""),
        password=data.get("password", ""),
        full_name=data.get("full_name", ""),
    )
    user_data = user.to_dict()
    public_user = {key: user_data[key] for key in ("id", "email", "full_name")}
    return success_response(data=public_user, status=201)


@auth_bp.route("/login", methods=["POST"], strict_slashes=False)
def login():
    data = request.get_json(silent=True) or {}
    result = AuthService.login(email=data.get("email", ""), password=data.get("password", ""))
    user = AuthService.get_user_by_id(result["user"]["id"])
    user_data = user.to_dict()
    result["user"] = {key: user_data[key] for key in ("id", "email", "full_name")}
    return success_response(data=result, status=200)


@auth_bp.route("/me", methods=["GET"], strict_slashes=False)
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = AuthService.get_user_by_id(user_id)
    return success_response(data=user.to_dict(), status=200)


@auth_bp.route("/refresh", methods=["POST"], strict_slashes=False)
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    new_access = create_access_token(identity=user_id)
    return success_response(data={"access_token": new_access}, status=200)
