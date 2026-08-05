"""公司管理 —— 公司数据库密码的创建、验证、修改

数据隔离基于：公司名 + 公司数据库密码。
- 用户：只能通过提供正确的公司名 + 数据库密码加入已有公司
- 管理员：可新注册公司（创建密码）或加入已有公司，并可修改本公司数据库密码
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
