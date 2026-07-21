"""User authentication service with bcrypt password hashing and JWT tokens."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt


class AuthService:
    """Handles user registration, login, and JWT token management."""

    def __init__(self, repository: RemoteTemplateRepository | None = None):
        self._repo = repository
        self._secret_key = os.environ.get("TEMPLATE_REPO_SECRET_KEY", "dev-secret-key-change-in-production")
        self._token_expiry_days = 7

    def set_repository(self, repository: RemoteTemplateRepository) -> None:
        """Set the remote repository after construction (for lazy init)."""
        self._repo = repository

    def _ensure_repo(self) -> None:
        if self._repo is None:
            raise RuntimeError("AuthService repository not initialized. Call set_repository() first.")

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    def register(self, username: str, password: str, email: str = "") -> str:
        """Register a new user. Returns the user ID.

        Raises:
            ValueError: If username is empty, password is too short, or username already exists.
        """
        self._ensure_repo()
        if not username or not username.strip():
            raise ValueError("用户名不能为空")
        if len(password) < 4:
            raise ValueError("密码长度不能少于4位")
        existing = self._repo.get_user_by_username(username.strip())
        if existing is not None:
            raise ValueError(f"用户名已存在: {username}")

        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)
        self._repo.save_user(
            id=user_id,
            username=username.strip(),
            password_hash=password_hash,
            email=email,
        )
        return user_id

    def login(self, username: str, password: str) -> str:
        """Verify credentials and return a JWT token.

        Raises:
            ValueError: If credentials are invalid.
        """
        self._ensure_repo()
        user = self._repo.get_user_by_username(username.strip())
        if user is None:
            raise ValueError("用户名或密码错误")
        if not self._verify_password(password, user.password_hash):
            raise ValueError("用户名或密码错误")

        payload = {
            "user_id": user.id,
            "username": user.username,
            "exp": datetime.now(timezone.utc) + timedelta(days=self._token_expiry_days),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, self._secret_key, algorithm="HS256")

    def verify_token(self, token: str) -> dict:
        """Verify a JWT token and return the payload.

        Returns:
            dict with keys: user_id, username, exp, iat

        Raises:
            ValueError: If the token is invalid or expired.
        """
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise ValueError("Token已过期")
        except jwt.InvalidTokenError:
            raise ValueError("无效的Token")
        if "user_id" not in payload or "username" not in payload:
            raise ValueError("Token数据不完整")
        return payload
