"""公司管理 —— 公司数据库密码的创建、验证、修改

数据隔离基于：公司名 + 公司数据库密码。
- 用户：只能通过提供正确的公司名 + 数据库密码加入已有公司
- 管理员：可新注册公司（创建密码）或加入已有公司，并可修改本公司数据库密码
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models import Company
from app.utils.auth_utils import hash_password, verify_password

logger = logging.getLogger("company_service")


async def create_company(
    db: AsyncSession,
    company_name: str,
    password: str,
    created_by: int = 0,
) -> Company:
    """创建公司（公司名唯一，创建后不可修改）。名称已存在时抛 ValueError"""
    company_name = (company_name or "").strip()
    if not company_name:
        raise ValueError("公司名称不能为空")
    if not password or len(password) < 6:
        raise ValueError("公司数据库密码至少6个字符")

    existing = await db.execute(select(Company).where(Company.company_name == company_name))
    if existing.scalar_one_or_none():
        raise ValueError("该公司名称已存在")

    company = Company(
        company_name=company_name,
        password_hash=hash_password(password),
        created_by=created_by,
    )
    db.add(company)
    await db.flush()
    return company


async def verify_company(
    db: AsyncSession,
    company_name: str,
    password: str,
) -> Optional[Company]:
    """校验公司名 + 数据库密码是否匹配，匹配返回 Company，否则返回 None"""
    company_name = (company_name or "").strip()
    if not company_name or not password:
        return None
    result = await db.execute(select(Company).where(Company.company_name == company_name))
    company = result.scalar_one_or_none()
    if not company:
        return None
    if not verify_password(password, company.password_hash):
        return None
    return company


async def change_company_password(
    db: AsyncSession,
    current_user,
    old_password: str,
    new_password: str,
    company_name: str = "",
) -> bool:
    """修改公司数据库密码。返回是否成功；参数错误抛 ValueError。

    - 普通管理员：只能修改自己所在公司（company_id）
    - 最高级管理员：可通过 company_name 修改任意公司的密码（留空则修改自己所在公司）
    均需提供该公司当前密码（old_password）才允许修改。
    """
    if not new_password or len(new_password) < 6:
        raise ValueError("新密码至少6个字符")

    # 确定目标公司
    target_name = (company_name or "").strip()
    if target_name:
        result = await db.execute(select(Company).where(Company.company_name == target_name))
        company = result.scalar_one_or_none()
        if not company:
            return False
        # 非最高级管理员不能改别的公司的密码
        if current_user.role != "super_admin" and company.id != current_user.company_id:
            return False
    else:
        result = await db.execute(select(Company).where(Company.id == current_user.company_id))
        company = result.scalar_one_or_none()
        if not company:
            return False

    if not verify_password(old_password, company.password_hash):
        return False
    company.password_hash = hash_password(new_password)
    await db.flush()
    logger.info(f"公司 #{company.id}「{company.company_name}」数据库密码已修改（操作人 user#{current_user.id}）")
    return True


def cleanup_orphan_companies(conn) -> list:
    """清理「没有任何用户账号」的公司及其全部业务数据。

    判定标准：companies 表中不存在任何 users.company_id 指向的公司。
    清理内容：
      - 该公司的业务数据（products / solution_plans / solution_items / import_logs）
      - companies 表记录（公司名 + 公司数据库密码哈希）

    参数 conn：SQLAlchemy 同步连接（调用方负责 commit）。
    返回被清理的公司名称列表。
    """
    rows = conn.execute(text("""
        SELECT c.id, c.company_name
        FROM companies c
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.company_id = c.id
        )
    """)).fetchall()

    removed = []
    for cid, cname in rows:
        # 1. 删除该公司的方案明细（通过方案ID）
        plan_ids = conn.execute(
            text("SELECT id FROM solution_plans WHERE company_id = :cid"), {"cid": cid}
        ).fetchall()
        for pid_row in plan_ids:
            conn.execute(text("DELETE FROM solution_items WHERE plan_id = :pid"), {"pid": pid_row[0]})
        # 2. 删除该公司的方案主表
        conn.execute(text("DELETE FROM solution_plans WHERE company_id = :cid"), {"cid": cid})
        # 3. 删除该公司的商品
        conn.execute(text("DELETE FROM products WHERE company_id = :cid"), {"cid": cid})
        # 4. 删除该公司的导入日志
        conn.execute(text("DELETE FROM import_logs WHERE company_id = :cid"), {"cid": cid})
        # 5. 删除公司记录（公司名 + 公司数据库密码）
        conn.execute(text("DELETE FROM companies WHERE id = :cid"), {"cid": cid})
        removed.append(cname)
        logger.info(f"已自动清理无账号公司 #{cid}「{cname}」及其全部业务数据")

    return removed


def _parse_dt(value) -> Optional[datetime]:
    """把数据库读出的时间值（字符串或 datetime）解析为 naive datetime，解析失败返回 None"""
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


def cleanup_expired_guests(conn) -> list:
    """清理已过期的游客账号及其独立公司、业务数据。

    兜底机制：游客未主动退出（直接关闭浏览器）时，会话到期后由系统自动清除所有痕迹。
    参数 conn：SQLAlchemy 同步连接（调用方负责 commit）。返回被清理的游客用户ID列表。
    """
    from datetime import datetime, timezone, timedelta

    rows = conn.execute(text(
        "SELECT id, company_id, expires_at FROM users WHERE role = 'guest'"
    )).fetchall()
    now = datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)
    removed_users = []
    for uid, cid, exp_raw in rows:
        exp = _parse_dt(exp_raw)
        if exp is None or exp > now:
            continue
        # 1. 删除该游客公司的方案明细（通过方案ID）
        plan_ids = conn.execute(
            text("SELECT id FROM solution_plans WHERE company_id = :cid"), {"cid": cid}
        ).fetchall()
        for pid_row in plan_ids:
            conn.execute(text("DELETE FROM solution_items WHERE plan_id = :pid"), {"pid": pid_row[0]})
        # 2. 删除该游客公司的方案主表
        conn.execute(text("DELETE FROM solution_plans WHERE company_id = :cid"), {"cid": cid})
        # 3. 删除该游客公司的商品
        conn.execute(text("DELETE FROM products WHERE company_id = :cid"), {"cid": cid})
        # 4. 删除该游客公司的导入日志
        conn.execute(text("DELETE FROM import_logs WHERE company_id = :cid"), {"cid": cid})
        # 5. 删除该游客的列显示配置
        conn.execute(text("DELETE FROM column_display_configs WHERE user_id = :uid"), {"uid": uid})
        # 6. 删除游客用户
        conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
        removed_users.append(uid)
        logger.info(f"已自动清理过期游客 user#{uid}（公司#{cid}）")
    # 7. 清理因此产生的孤儿公司（游客公司已无用户）
    if removed_users:
        cleanup_orphan_companies(conn)
    return removed_users
