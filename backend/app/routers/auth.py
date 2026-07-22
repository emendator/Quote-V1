"""用户认证 API：登录、注册、获取用户信息、完善公司信息、修改密码"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, InviteCode
from app.schemas import (
    ApiResponse,
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
    CompanyInfoUpdate,
    PasswordChangeRequest,
)
from app.utils.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger("auth")

router = APIRouter(prefix="/api/auth", tags=["用户认证"])


def _user_to_response(user: User) -> UserResponse:
    """将 User ORM 对象转换为 UserResponse"""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        company_name=user.company_name or "",
        contact_person=user.contact_person or "",
        contact_phone=user.contact_phone or "",
        company_address=user.company_address or "",
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.post("/register", response_model=ApiResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册（需提供邀请码）"""
    # 1. 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        return ApiResponse(code=400, message="用户名已存在")

    # 2. 查询邀请码
    result = await db.execute(select(InviteCode).where(InviteCode.code == data.invite_code))
    invite = result.scalar_one_or_none()

    if not invite:
        return ApiResponse(code=400, message="邀请码不存在")
    if invite.is_used:
        return ApiResponse(code=400, message="邀请码已被使用")
    if invite.expires_at.replace(tzinfo=None) < datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None):
        return ApiResponse(code=400, message="邀请码已过期")

    # 3. 根据邀请码类型确定角色
    role = "admin" if invite.type == "admin" else "user"

    # 4. 创建用户
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        email=data.email,
        role=role,
        company_name="",
    )
    db.add(user)
    await db.flush()  # 获取 user.id

    # 5. 标记邀请码已使用
    invite.is_used = True
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone(timedelta(hours=8)))
    await db.flush()

    # 6. 生成 JWT Token
    access_token = create_access_token(data={
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "company_name": user.company_name or "",
    })

    return ApiResponse(
        data=LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=_user_to_response(user),
        ).model_dump(),
        message="注册成功",
    )


@router.post("/login", response_model=ApiResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    # 1. 查询用户
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user:
        return ApiResponse(code=401, message="用户名或密码错误")
    if not user.is_active:
        return ApiResponse(code=401, message="账号已被禁用")

    # 2. 验证密码
    if not verify_password(data.password, user.password_hash):
        return ApiResponse(code=401, message="用户名或密码错误")

    # 3. 更新最后登录时间
    user.last_login_at = datetime.now(timezone(timedelta(hours=8)))

    # 4. 生成 JWT Token
    access_token = create_access_token(data={
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "company_name": user.company_name or "",
    })

    return ApiResponse(
        data=LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=_user_to_response(user),
        ).model_dump(),
        message="登录成功",
    )


@router.get("/me", response_model=ApiResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return ApiResponse(data=_user_to_response(current_user).model_dump())


@router.put("/me/company", response_model=ApiResponse)
async def update_company(
    data: CompanyInfoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """完善公司信息（管理员注册后必填）"""
    current_user.company_name = data.company_name
    current_user.contact_person = data.contact_person or ""
    current_user.contact_phone = data.contact_phone or ""
    current_user.company_address = data.company_address or ""
    await db.flush()

    return ApiResponse(
        data=_user_to_response(current_user).model_dump(),
        message="公司信息更新成功",
    )


@router.put("/me/password", response_model=ApiResponse)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(data.old_password, current_user.password_hash):
        return ApiResponse(code=400, message="旧密码错误")

    # 更新新密码
    current_user.password_hash = hash_password(data.new_password)
    await db.flush()

    return ApiResponse(message="密码修改成功")
