"""邀请码管理 API：创建、列表、验证"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db, sync_engine
from app.models import User, InviteCode, Product, SolutionPlan, SolutionItem
from app.schemas import ApiResponse, InviteCodeCreateRequest, InviteCodeResponse, InviteCodeVerifyResponse, InviteCodeRenewRequest
from app.utils.auth_utils import (
    generate_invite_code,
    require_company_admin,
)
from sqlalchemy import text

logger = logging.getLogger("invites")

router = APIRouter(prefix="/api/invites", tags=["邀请码管理"])


def _parse_dt(value) -> Optional[datetime]:
    """把数据库读出的时间值（字符串或 datetime）解析为 naive datetime，无法解析返回 None。

    SQLite 中 DATETIME 以文本存储（如 '2026-08-05 16:14:49.188025'），
    通过原生 text() SQL 读回时是字符串，直接对其调用 .replace(tzinfo=...) 会报错。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    s = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _invite_to_response(invite: InviteCode, used_user: Optional[User] = None) -> InviteCodeResponse:
    return InviteCodeResponse(
        id=invite.id,
        code=invite.code,
        type=invite.type,
        created_by=invite.created_by,
        used_by=invite.used_by,
        used_by_username=used_user.get_plain_username() if used_user else "",
        used_by_company=used_user.company_name or "" if used_user else "",
        used_by_last_login=used_user.last_login_at.isoformat() if used_user and used_user.last_login_at else None,
        used_at=invite.used_at.isoformat() if invite.used_at else None,
        expires_at=invite.expires_at.isoformat() if invite.expires_at else None,
        is_used=bool(invite.is_used),
        company_name=invite.company_name or "",
        created_at=invite.created_at.isoformat() if invite.created_at else None,
    )


@router.post("/create", response_model=ApiResponse)
async def create_invite(
    data: InviteCodeCreateRequest,
    current_user: User = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建邀请码

    最高级管理员可创建 admin/user 类型
    管理员仅可创建 user 类型
    """
    # 权限校验
    if current_user.role == "user":
        return ApiResponse(code=403, message="用户无权创建邀请码")
    if data.code_type == "admin" and current_user.role != "super_admin":
        return ApiResponse(code=403, message="仅最高级管理员可创建一级邀请码")

    # 生成邀请码
    code_str = generate_invite_code(data.code_type)
    try:
        expires_at = datetime.strptime(data.expires_at, "%Y-%m-%d %H:%M")
        expires_at = expires_at.replace(tzinfo=timezone(timedelta(hours=8)))
    except ValueError:
        return ApiResponse(code=400, message="过期时间格式错误，请使用 YYYY-MM-DD HH:mm 格式")
    
    invite = InviteCode(
        code=code_str,
        type=data.code_type,
        created_by=current_user.id,
        company_name=data.company_name,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.flush()

    return ApiResponse(
        data=_invite_to_response(invite).model_dump(),
        message="邀请码创建成功",
    )


@router.get("/list", response_model=ApiResponse)
async def list_invites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    code_type: str = Query(None, alias="type"),
    status: str = Query(None, alias="status"),
    current_user: User = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db),
):
    """查看邀请码列表

    最高级管理员可查看所有邀请码
    管理员仅可查看自己创建的邀请码
    """
    query = select(InviteCode)

    # 所有用户（含最高级管理员）只看到自己创建的邀请码
    query = query.where(InviteCode.created_by == current_user.id)

    if code_type:
        query = query.where(InviteCode.type == code_type)
    if status == "used":
        query = query.where(InviteCode.is_used == True)
    elif status == "unused":
        query = query.where(InviteCode.is_used == False)

    # 总数量
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(InviteCode.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    invites = result.scalars().all()

    # 批量查询使用者信息
    used_user_ids = [inv.used_by for inv in invites if inv.used_by]
    user_map = {}
    if used_user_ids:
        user_result = await db.execute(
            select(User).where(User.id.in_(used_user_ids))
        )
        for u in user_result.scalars().all():
            user_map[u.id] = u

    return ApiResponse(data={
        "items": [_invite_to_response(inv, user_map.get(inv.used_by)).model_dump() for inv in invites],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/verify/{code}", response_model=ApiResponse)
async def verify_invite(code: str, db: AsyncSession = Depends(get_db)):
    """验证邀请码有效性（公开接口，注册时调用）"""
    result = await db.execute(select(InviteCode).where(InviteCode.code == code))
    invite = result.scalar_one_or_none()

    if not invite:
        return ApiResponse(data=InviteCodeVerifyResponse(valid=False, message="邀请码不存在").model_dump())

    if invite.is_used:
        return ApiResponse(data=InviteCodeVerifyResponse(valid=False, message="邀请码已被使用").model_dump())

    now = datetime.now(timezone(timedelta(hours=8)))
    if invite.expires_at.replace(tzinfo=None) < now.replace(tzinfo=None):
        return ApiResponse(data=InviteCodeVerifyResponse(valid=False, message="邀请码已过期").model_dump())

    return ApiResponse(data=InviteCodeVerifyResponse(
        valid=True,
        type=invite.type,
        message="邀请码有效",
        company_name=invite.company_name or "",
    ).model_dump())


def _safe_delete_owner_rows(conn, table: str, user_id: int):
    """安全删除某表的 owner_id 行；表不存在时静默跳过（旧版遗留表容错）"""
    try:
        conn.execute(text(f"DELETE FROM {table} WHERE owner_id = :uid"), {"uid": user_id})
    except Exception:
        pass


def _cascade_delete_user(user_id: int, conn=None):
    """级联删除用户及其所有相关数据

    使用传入的连接（conn）执行，保证同一事务。
    递归时也传入同一连接，避免 SQLite 锁冲突。
    """
    if conn is None:
        with sync_engine.connect() as c:
            _cascade_delete_user(user_id, c)
            c.commit()
        return

    # 1. 查找该用户创建的所有邀请码
    created_codes = conn.execute(
        text("SELECT id, used_by FROM invite_codes WHERE created_by = :uid"),
        {"uid": user_id}
    ).fetchall()

    # 2. 递归删除这些邀请码的使用者（子用户），复用 conn
    for cid, used_by in created_codes:
        if used_by:
            _cascade_delete_user(used_by, conn)

    # 3. 删除该用户创建的邀请码
    conn.execute(text("DELETE FROM invite_codes WHERE created_by = :uid"), {"uid": user_id})

    # 4. 删除该用户的方案明细（通过方案ID）
    plan_ids = conn.execute(
        text("SELECT id FROM solution_plans WHERE owner_id = :uid"), {"uid": user_id}
    ).fetchall()
    for pid_row in plan_ids:
        conn.execute(text("DELETE FROM solution_items WHERE plan_id = :pid"), {"pid": pid_row[0]})
    # 删除方案主表
    conn.execute(text("DELETE FROM solution_plans WHERE owner_id = :uid"), {"uid": user_id})

    # 5. 删除该用户的商品
    conn.execute(text("DELETE FROM products WHERE owner_id = :uid"), {"uid": user_id})

    # 6. 删除该用户的平台配置（旧版遗留表，可能不存在，需容错）
    _safe_delete_owner_rows(conn, "platform_configs", user_id)

    # 7. 删除该用户的上架日志（旧版遗留表，可能不存在，需容错）
    _safe_delete_owner_rows(conn, "listing_logs", user_id)

    # 8. 删除该用户的导入日志
    conn.execute(text("DELETE FROM import_logs WHERE owner_id = :uid"), {"uid": user_id})

    # 9. 删除用户自身
    conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})


@router.delete("/{invite_id}", response_model=ApiResponse)
async def delete_invite(
    invite_id: int,
    current_user: User = Depends(require_company_admin),
):
    """删除邀请码（级联删除关联用户及数据）

    最高级管理员：可删除任何邀请码
    管理员：仅可删除自己创建的邀请码
    """
    try:
        # 使用同步引擎执行全部操作（避免异步/同步事务冲突）
        with sync_engine.connect() as conn:
            # 查询邀请码
            invite_row = conn.execute(
                text("SELECT id, code, created_by, used_by FROM invite_codes WHERE id = :id"),
                {"id": invite_id}
            ).fetchone()

            if not invite_row:
                return ApiResponse(code=404, message="邀请码不存在")

            invite_code_str = invite_row[1]
            created_by = invite_row[2]
            used_by = invite_row[3]

            # 权限校验
            if current_user.role != "super_admin" and created_by != current_user.id:
                return ApiResponse(code=403, message="无权删除此邀请码")

            # 不允许删除最高级管理员（id=1）
            if used_by == 1:
                return ApiResponse(code=400, message="不能删除最高级管理员账号")

            # 只有账号过期后才允许删除
            if used_by:
                user_row = conn.execute(
                    text("SELECT expires_at FROM users WHERE id = :uid"),
                    {"uid": used_by}
                ).fetchone()
                if user_row:
                    expires_at = _parse_dt(user_row[0])
                    now = datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)
                    if expires_at is None or expires_at > now:
                        return ApiResponse(code=400, message="该账号尚未过期，无法删除；请先续期或等待其过期后再删除")

            logger.info(
                f"级联删除邀请码 #{invite_id} ({invite_code_str}), "
                f"创建者={created_by}, 使用者={used_by}, "
                f"由用户 {current_user.get_plain_username()}({current_user.id}) 执行"
            )

            # 先删除邀请码自身（避免递归时重复处理）
            conn.execute(text("DELETE FROM invite_codes WHERE id = :id"), {"id": invite_id})

            if used_by:
                # 级联删除使用者及其所有下游（复用当前连接，避免锁冲突）
                _cascade_delete_user(used_by, conn)

            conn.commit()

        return ApiResponse(message="邀请码及关联数据已全部删除")
    except Exception as e:
        logger.error(f"删除邀请码失败: {e}", exc_info=True)
        return ApiResponse(code=500, message=f"删除失败: {str(e)}")


@router.post("/{invite_id}/renew", response_model=ApiResponse)
async def renew_invite(
    invite_id: int,
    data: InviteCodeRenewRequest,
    current_user: User = Depends(require_company_admin),
):
    """续期邀请码关联的账号（仅管理员以上可操作）

    为已过期的账号设置新的过期时间，使其恢复可用。
    """
    if current_user.role not in ("super_admin", "admin"):
        return ApiResponse(code=403, message="权限不足")

    try:
        with sync_engine.connect() as conn:
            # 查询邀请码
            invite_row = conn.execute(
                text("SELECT id, created_by, used_by FROM invite_codes WHERE id = :id"),
                {"id": invite_id}
            ).fetchone()

            if not invite_row:
                return ApiResponse(code=404, message="邀请码不存在")

            created_by = invite_row[1]
            used_by = invite_row[2]

            # 权限校验：管理员只能操作自己创建的邀请码
            if current_user.role != "super_admin" and created_by != current_user.id:
                return ApiResponse(code=403, message="无权操作此邀请码")

            if not used_by:
                return ApiResponse(code=400, message="该邀请码尚未被使用，无关联账号")

            # 解析新的过期时间
            try:
                new_expires_at = datetime.strptime(data.expires_at, "%Y-%m-%d %H:%M")
                new_expires_at = new_expires_at.replace(tzinfo=timezone(timedelta(hours=8)))
            except ValueError:
                return ApiResponse(code=400, message="过期时间格式错误，请使用 YYYY-MM-DD HH:mm 格式")

            # 更新用户的过期时间
            conn.execute(
                text("UPDATE users SET expires_at = :expires_at WHERE id = :uid"),
                {"expires_at": new_expires_at, "uid": used_by}
            )
            # 同时更新邀请码的过期时间（保持同步）
            conn.execute(
                text("UPDATE invite_codes SET expires_at = :expires_at WHERE id = :id"),
                {"expires_at": new_expires_at, "id": invite_id}
            )
            conn.commit()

        return ApiResponse(message=f"账号已续期至 {data.expires_at}")
    except Exception as e:
        logger.error(f"续期失败: {e}", exc_info=True)
        return ApiResponse(code=500, message=f"续期失败: {str(e)}")
