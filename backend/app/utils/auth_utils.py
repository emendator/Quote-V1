"""认证工具模块：密码哈希、JWT Token、依赖注入"""
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.models import User

logger = logging.getLogger("auth_utils")

# ========== 密码哈希 ==========

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码与哈希是否匹配"""
    return pwd_context.verify(password, password_hash)


# ========== JWT Token ==========

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """解码 JWT token，返回 payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        logger.warning(f"JWT 解码失败: {e}")
        raise


# ========== 邀请码生成 ==========

def generate_invite_code(code_type: str) -> str:
    """
    生成邀请码
    格式: INV-{TYPE}-{16位随机十六进制}
    示例: INV-ADMIN-A3F2B8C9D1E0F4A7
    """
    prefix = "ADMIN" if code_type == "admin" else "USER"
    random_hex = secrets.token_hex(8).upper()
    return f"INV-{prefix}-{random_hex}"


# ========== FastAPI 依赖注入 ==========

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """验证 Bearer Token 并返回当前用户对象"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except Exception:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    # 检查账号是否过期
    from datetime import datetime, timezone, timedelta
    if user.expires_at and user.expires_at.replace(tzinfo=None) < datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已过期，无法执行操作",
        )
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """可选的用户认证，不存在时返回 None（用于公开接口）"""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """限制仅最高级管理员可访问"""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，需要最高级管理员权限")
    return current_user


async def require_admin_or_above(current_user: User = Depends(get_current_user)) -> User:
    """限制管理员及以上可访问"""
    if current_user.role not in ("super_admin", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，需要管理员及以上权限")
    return current_user


async def require_company(current_user: User = Depends(get_current_user)) -> User:
    """限制已完成公司绑定（公司名 + 公司数据库密码）的用户可访问"""
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先完善公司信息（公司名称 + 公司数据库密码）",
        )
    return current_user


async def require_company_admin(current_user: User = Depends(require_company)) -> User:
    """限制管理员及以上，且已完成公司绑定"""
    if current_user.role not in ("super_admin", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，需要管理员及以上权限")
    return current_user
