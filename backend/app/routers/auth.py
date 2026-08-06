"""用户认证 API：登录、注册、获取用户信息、完善公司信息、修改密码、游客登录"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db, sync_engine
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

# 游客会话有效期（小时）：到期后由系统定时清理，不留任何痕迹
GUEST_TTL_HOURS = 24


def _user_to_response(user: User) -> UserResponse:
    """将 User ORM 对象转换为 UserResponse"""
    return UserResponse(
        id=user.id,
        username=user.get_plain_username(),
        email=user.email,
        role=user.role,
        company_id=user.company_id,
        company_name=user.company_name or "",
        contact_person=user.contact_person or "",
        contact_phone=user.contact_phone or "",
        company_address=user.company_address or "",
        is_active=bool(user.is_active),
        has_api_key=bool(user.api_key),
        total_tokens_used=user.total_tokens_used or 0,
        expires_at=user.expires_at.isoformat() if user.expires_at else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.post("/register", response_model=ApiResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册（需提供邀请码）"""
    # 1. 检查用户名是否已存在（通过 username_hash 等值查询）
    from app.utils.crypto_utils import hash_username, encrypt_username
    result = await db.execute(select(User).where(User.username_hash == hash_username(data.username)))
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

    # 3. 根据邀请码类型确定角色（邀请码仅决定角色，不再预设公司名）
    role = "admin" if invite.type == "admin" else "user"

    user = User(
        username=encrypt_username(data.username),
        username_hash=hash_username(data.username),
        password_hash=hash_password(data.password),
        email=data.email,
        role=role,
        expires_at=invite.expires_at,  # 继承邀请码的过期时间
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
        "username": user.get_plain_username(),
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
    # 1. 查询用户（通过 username_hash 等值查询）
    from app.utils.crypto_utils import hash_username
    result = await db.execute(select(User).where(User.username_hash == hash_username(data.username)))
    user = result.scalar_one_or_none()

    if not user:
        return ApiResponse(code=401, message="用户名或密码错误")
    if not user.is_active:
        return ApiResponse(code=401, message="账号已被禁用")
    if user.expires_at and user.expires_at.replace(tzinfo=None) < datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None):
        return ApiResponse(code=401, message="账号已过期，已禁止登录，请联系管理员续期")

    # 2. 验证密码
    if not verify_password(data.password, user.password_hash):
        return ApiResponse(code=401, message="用户名或密码错误")

    # 3. 更新最后登录时间
    user.last_login_at = datetime.now(timezone(timedelta(hours=8)))

    # 4. 生成 JWT Token
    access_token = create_access_token(data={
        "sub": str(user.id),
        "username": user.get_plain_username(),
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
    """更新公司联系方式（公司归属通过 /api/company/bind 绑定，此处仅更新联系人信息）"""
    current_user.contact_person = data.contact_person or ""
    current_user.contact_phone = data.contact_phone or ""
    current_user.company_address = data.company_address or ""
    await db.flush()

    return ApiResponse(
        data=_user_to_response(current_user).model_dump(),
        message="公司信息更新成功",
    )


@router.put("/me/apikey", response_model=ApiResponse)
async def update_api_key(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """保存当前用户的 DeepSeek API Key（加密存储）"""
    api_key = data.get("api_key", "").strip()
    if not api_key:
        return ApiResponse(code=400, message="API Key 不能为空")

    from app.utils.crypto_utils import encrypt_api_key
    encrypted = encrypt_api_key(api_key)
    current_user.api_key = encrypted
    await db.flush()

    return ApiResponse(message="API Key 已保存（加密存储）")


@router.get("/me/apikey/status", response_model=ApiResponse)
async def get_api_key_status(
    current_user: User = Depends(get_current_user),
):
    """查看当前用户 API Key 配置状态"""
    return ApiResponse(data={
        "has_api_key": bool(current_user.api_key),
        "total_tokens_used": current_user.total_tokens_used or 0,
    })


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


# ========== 游客模式 ==========

def _cleanup_guest_session(user_id: int, company_id: int):
    """清除游客会话的全部痕迹：业务数据、列配置、用户、公司、上传文件与内存缓存"""
    with sync_engine.connect() as conn:
        # 1. 删除该游客公司的方案明细（通过方案ID）
        plan_ids = conn.execute(
            text("SELECT id FROM solution_plans WHERE company_id = :cid"), {"cid": company_id}
        ).fetchall()
        for pid_row in plan_ids:
            conn.execute(text("DELETE FROM solution_items WHERE plan_id = :pid"), {"pid": pid_row[0]})
        # 2. 删除该游客公司的方案主表
        conn.execute(text("DELETE FROM solution_plans WHERE company_id = :cid"), {"cid": company_id})
        # 3. 删除该游客公司的商品
        conn.execute(text("DELETE FROM products WHERE company_id = :cid"), {"cid": company_id})
        # 4. 删除该游客公司的导入日志
        conn.execute(text("DELETE FROM import_logs WHERE company_id = :cid"), {"cid": company_id})
        # 5. 删除该游客的列显示配置
        conn.execute(text("DELETE FROM column_display_configs WHERE user_id = :uid"), {"uid": user_id})
        # 6. 删除游客用户
        conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
        # 7. 删除游客公司（若该公司已无其他用户）
        conn.execute(text(
            "DELETE FROM companies WHERE id = :cid AND NOT EXISTS "
            "(SELECT 1 FROM users WHERE company_id = :cid)"
        ), {"cid": company_id})
        conn.commit()

    # 8. 清除上传的临时文件与内存解析缓存（游客不保留任何使用痕迹）
    from app.services.cleanup_service import clean_upload_files, clean_memory_cache
    try:
        clean_upload_files(0)
    except Exception:
        pass
    try:
        clean_memory_cache()
    except Exception:
        pass


@router.post("/guest", response_model=ApiResponse)
async def guest_login(db: AsyncSession = Depends(get_db)):
    """游客登录：创建独立的游客账号与游客公司，可体验智能查询/数据管理/智能方案。

    - 游客数据完全隔离在独立的临时公司内，退出登录或会话过期后自动全部清除
    - 游客无用户管理权限；使用 AI 功能需自行配置 API Key
    - 游客会话有效期 GUEST_TTL_HOURS 小时，到期由系统自动清理
    """
    import uuid
    from app.models import Company
    from app.utils.crypto_utils import encrypt_username, hash_username

    # 生成唯一的游客账号与游客公司（避免随机碰撞）
    guest_name = ""
    company_name = ""
    company_pwd = ""
    for _ in range(5):
        suffix = uuid.uuid4().hex[:10]
        candidate_name = f"guest_{suffix}"
        exists = await db.execute(
            select(User).where(User.username_hash == hash_username(candidate_name))
        )
        if not exists.scalar_one_or_none():
            guest_name = candidate_name
            company_name = f"游客_{suffix}"
            company_pwd = uuid.uuid4().hex[:12]
            break
    if not guest_name:
        return ApiResponse(code=500, message="游客账号创建失败，请稍后重试")

    # 创建游客独立公司（随机公司名 + 随机数据库密码，游客无需记忆）
    company = Company(
        company_name=company_name,
        password_hash=hash_password(company_pwd),
        created_by=0,
    )
    db.add(company)
    await db.flush()

    # 创建游客用户（角色 guest，会话到期时间）
    expires_at = datetime.now(timezone(timedelta(hours=8))) + timedelta(hours=GUEST_TTL_HOURS)
    guest = User(
        username=encrypt_username(guest_name),
        username_hash=hash_username(guest_name),
        password_hash=hash_password(company_pwd),  # 随机密码，游客不通过账号密码登录
        email="guest@local",
        role="guest",
        company_name=company_name,
        company_id=company.id,
        expires_at=expires_at,
    )
    db.add(guest)
    await db.flush()

    access_token = create_access_token(data={
        "sub": str(guest.id),
        "username": guest.get_plain_username(),
        "role": guest.role,
        "company_name": guest.company_name or "",
    })

    logger.info(f"游客登录: user#{guest.id} 公司#{company.id}「{company_name}」")
    return ApiResponse(
        data=LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=_user_to_response(guest),
        ).model_dump(),
        message="游客登录成功（数据为临时体验数据，退出登录后自动清除）",
    )


@router.post("/guest/cleanup", response_model=ApiResponse)
async def guest_cleanup(
    current_user: User = Depends(get_current_user),
):
    """清除当前游客会话的全部使用痕迹（仅游客可调用）"""
    if current_user.role != "guest":
        return ApiResponse(code=403, message="仅游客可执行清除操作")

    _cleanup_guest_session(current_user.id, current_user.company_id or 0)
    logger.info(f"游客会话已清除: user#{current_user.id} 公司#{current_user.company_id}")
    return ApiResponse(message="游客数据已全部清除")
