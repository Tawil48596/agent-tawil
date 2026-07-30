"""Auth API — API Key + JWT 认证"""

import hashlib
import os
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=expires_hours),
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


# ── 依赖注入 ──

async def get_current_user(
    request: Request,
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> str:
    """从请求中提取并验证用户身份"""
    # 尝试 Bearer Token (JWT)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user_id = jwt_handler.verify(token)
        if user_id:
            return user_id

    # 尝试 API Key
    if x_api_key:
        user_id = api_keys.validate(x_api_key)
        if user_id:
            return user_id

    raise HTTPException(401, "Missing or invalid authentication")


# ── API ──

@router.post("/api-key")
async def create_api_key(request: Request, name: str = ""):
    """生成 API Key (需要已有认证)"""
    # In dev: allow
    key = api_keys.create_key("default_user", name)
    return {"api_key": key, "name": name, "note": "Store this securely. It won't be shown again."}


@router.post("/token")
async def login(username: str = "admin", password: str = ""):
    """获取 JWT Token (简化版)"""
    token = jwt_handler.create_token(username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/verify")
async def verify_token(request: Request):
    """验证当前 Token"""
    try:
        user = await get_current_user(request, request.headers.get("Authorization"))
        return {"valid": True, "user": user}
    except HTTPException:
        return {"valid": False}


@router.post("/revoke")
async def revoke_token(request: Request, token: str = ""):
    jwt_handler.revoke(token)
    return {"ok": True}
