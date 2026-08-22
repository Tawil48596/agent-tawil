"""Auth API — API Key + JWT 认证"""

import hashlib
import os
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Require authentication for v1 APIs when enabled by the app factory."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            request.method == "OPTIONS"
            or not path.startswith("/api/v1/")
            or path == "/api/v1/auth/token"
        ):
            return await call_next(request)

        user_id = authenticate_headers(
            request.headers.get("Authorization"),
            request.headers.get("X-API-Key"),
        )
        if user_id is None:
            return JSONResponse({"detail": "Missing or invalid authentication"}, status_code=401)
        request.state.user_id = user_id
        return await call_next(request)


# ── API Key 管理 ──

class APIKeyManager:
    def __init__(self):
        self._keys: dict[str, dict] = {}  # hashed_key → {user_id, name, created_at}
        self._revoked: set[str] = set()

    def create_key(self, user_id: str, name: str = "") -> str:
        """生成新 API Key"""
        raw = f"sk-{hashlib.sha256(os.urandom(32)).hexdigest()[:32]}"
        hashed = self._hash(raw)
        self._keys[hashed] = {
            "user_id": user_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "last_used": None,
        }
        return raw

    def validate(self, raw_key: str) -> Optional[str]:
        """验证 API Key，返回 user_id"""
        hashed = self._hash(raw_key)
        if hashed in self._revoked:
            return None
        entry = self._keys.get(hashed)
        if entry:
            entry["last_used"] = datetime.now().isoformat()
            return entry["user_id"]
        return None

    def revoke(self, raw_key: str):
        self._revoked.add(self._hash(raw_key))

    @staticmethod
    def _hash(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()


# ── JWT ──

class JWTHandler:
    def __init__(self, secret: str = None):
        self._secret = secret or os.environ.get("JWT_SECRET", "dev-secret-change-me")
        self._blacklist: set[str] = set()

    def create_token(self, user_id: str, expires_hours: int = 720) -> str:
        """签发 JWT"""
        try:
            from jose import jwt
            payload = {
                "sub": user_id,
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=expires_hours),
            }
            return jwt.encode(payload, self._secret, algorithm="HS256")
        except ImportError:
            # 回退: 简单签名
            payload = f"{user_id}:{int(time.time()) + expires_hours * 3600}"
            sig = hashlib.sha256(f"{payload}:{self._secret}".encode()).hexdigest()[:16]
            return f"{payload}:{sig}"

    def verify(self, token: str) -> Optional[str]:
        """验证 JWT，返回 user_id"""
        if token in self._blacklist:
            return None
        try:
            from jose import jwt
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
            return payload.get("sub")
        except ImportError:
            parts = token.rsplit(":", 1)
            if len(parts) != 2:
                return None
            payload, sig = parts
            expected = hashlib.sha256(f"{payload}:{self._secret}".encode()).hexdigest()[:16]
            if sig != expected:
                return None
            user_id, exp_ts = payload.split(":", 1)
            if int(exp_ts) < time.time():
                return None
            return user_id

    def revoke(self, token: str):
        self._blacklist.add(token)


# ── 全局实例 ──

api_keys = APIKeyManager()
jwt_handler = JWTHandler()


def authenticate_headers(authorization: str = "", x_api_key: str = "") -> Optional[str]:
    authorization = authorization or ""
    x_api_key = x_api_key or ""
    if authorization.startswith("Bearer "):
        user_id = jwt_handler.verify(authorization[7:])
        if user_id:
            return user_id
    if x_api_key:
        return api_keys.validate(x_api_key)
    return None


# ── 依赖注入 ──

async def get_current_user(
    request: Request,
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> str:
    """从请求中提取并验证用户身份"""
    state_user = getattr(request.state, "user_id", None)
    if state_user:
        return state_user
    user_id = authenticate_headers(authorization or "", x_api_key or "")
    if user_id:
        return user_id

    raise HTTPException(401, "Missing or invalid authentication")


# ── API ──

@router.post("/api-key")
async def create_api_key(name: str = "", user_id: str = Depends(get_current_user)):
    """生成 API Key (需要已有认证)"""
    key = api_keys.create_key(user_id, name)
    return {"api_key": key, "name": name, "note": "Store this securely. It won't be shown again."}


@router.post("/token")
async def login(body: LoginRequest):
    """Issue a JWT after validating the configured local administrator."""
    expected_username = os.environ.get("AGENT_ADMIN_USERNAME", "admin")
    expected_password = os.environ.get("AGENT_ADMIN_PASSWORD", "")
    if not expected_password:
        raise HTTPException(503, "Administrator credentials are not configured")
    if not (
        secrets.compare_digest(body.username, expected_username)
        and secrets.compare_digest(body.password, expected_password)
    ):
        raise HTTPException(401, "Invalid username or password")
    token = jwt_handler.create_token(body.username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/verify")
async def verify_token(request: Request):
    """验证当前 Token"""
    try:
        user = await get_current_user(
            request,
            request.headers.get("Authorization"),
            request.headers.get("X-API-Key"),
        )
        return {"valid": True, "user": user}
    except HTTPException:
        return {"valid": False}


@router.post("/revoke")
async def revoke_token(request: Request, token: str = ""):
    jwt_handler.revoke(token)
    return {"ok": True}
