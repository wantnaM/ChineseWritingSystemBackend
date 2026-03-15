"""
app/api/auth_routes.py
认证路由 — POST /api/v1/auth/login  |  POST /api/v1/auth/logout

依赖：
  - python-jose[cryptography]  （JWT）
  - bcrypt            （密码哈希）
  以上库需加入 requirements.txt
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.models.models import User
from app.schemas.schemas import LoginRequest, TokenResponse, UserRead

import bcrypt

try:
    from jose import jwt
    _JWT_AVAILABLE = True
except ImportError:
    _JWT_AVAILABLE = False


auth_router = APIRouter(prefix="/auth", tags=["认证 Auth"])
DB = Annotated[AsyncSession, Depends(get_session)]

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(user_id: int, role: str) -> tuple[str, int]:
    """返回 (access_token, expires_in_seconds)。"""
    if not _JWT_AVAILABLE:
        return f"dev-token-{user_id}", 86400
    expire_seconds: int = getattr(settings, "JWT_EXPIRE_SECONDS", 86400)
    secret: str = getattr(settings, "JWT_SECRET", "dev-secret-change-me")
    algorithm: str = getattr(settings, "JWT_ALGORITHM", "HS256")
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expire_seconds),
    }
    return jwt.encode(payload, secret, algorithm=algorithm), expire_seconds


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@auth_router.post("/login", response_model=TokenResponse, summary="用户登录（学生/教师）")
async def login(body: LoginRequest, db: DB):
    """
    统一登录入口。

    - `role = "student"` → 用学号 + 密码登录，跳转学生端
    - `role = "teacher"` → 用工号 + 密码登录，跳转教师端

    成功后返回 JWT Bearer Token，前端存入 localStorage 并在后续请求
    Headers 中携带 `Authorization: Bearer <token>`。

    **开发期说明**：若数据库尚无 users 表数据，后端返回 mock token
    （`dev-token-*`），前端可直接使用，无需验证签名。
    """
    user_row = (
        await db.execute(
            select(User).where(
                User.username == body.username,
                User.role == body.role,
            )
        )
    ).scalar_one_or_none()

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
        )

    if not user_row.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系教师",
        )

    if not _verify_password(body.password, user_row.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
        )

    # 更新最后登录时间
    await db.execute(
        update(User)
        .where(User.id == user_row.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()

    token, expires_in = _create_token(user_row.id, user_row.role)

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user_row),
    )


@auth_router.post("/logout", summary="登出（前端清除 Token 即可）")
async def logout():
    """
    服务端无状态，前端清除本地存储的 Token 即可。
    此接口保留作为语义占位，始终返回成功。
    """
    return {"message": "已退出登录", "success": True}
