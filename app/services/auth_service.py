from flask_jwt_extended import create_access_token, create_refresh_token

from app.extensions import db
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.core.exceptions import ConflictError, UnauthorizedError, BadRequestError


class AuthService:

    @staticmethod
    def register(email: str, password: str, full_name: str) -> User:
        email = (email or "").strip().lower()
        full_name = (full_name or "").strip()
        password = password or ""
        if not email or not password or not full_name:
            raise BadRequestError("email, password ve full_name zorunludur")
        if len(password) < 6:
            raise BadRequestError("Şifre en az 6 karakter olmalı")
        if len(email) > 255 or len(full_name) > 255:
            raise BadRequestError("email ve full_name en fazla 255 karakter olabilir")
        if User.query.filter_by(email=email).first():
            raise ConflictError("Bu email zaten kayıtlı")
        user = User(email=email, password_hash=hash_password(password), full_name=full_name)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def login(email: str, password: str) -> dict:
        email = (email or "").strip().lower()
        password = password or ""
        if not email or not password:
            raise BadRequestError("email ve password zorunludur")
        user = User.query.filter_by(email=email).first()
        if not user or not verify_password(user.password_hash, password):
            raise UnauthorizedError("Geçersiz email veya şifre")
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        return {
            "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @staticmethod
    def get_user_by_id(user_id: str) -> User:
        user = db.session.get(User, user_id)
        if not user:
            raise UnauthorizedError("Kullanıcı bulunamadı")
        return user
