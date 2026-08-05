"""公司管理 API：绑定公司（加入/新注册）、修改公司数据库密码

数据隔离：公司名 + 公司数据库密码。
- 所有角色：绑定公司时提供公司名 + 公司数据库密码加入已有公司
- 管理员（含最高级管理员）：可新注册公司（创建公司数据库密码）、修改本公司数据库密码
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import ApiResponse, CompanyBindRequest, CompanyPasswordChangeRequest
from app.services.company_service import create_company, verify_company, change_company_password
from app.utils.auth_utils import get_current_user, require_company_admin

logger = logging.getLogger("company")

router = APIRouter(prefix="/api/company", tags=["公司管理"])


@router.post("/bind", response_model=ApiResponse)
async def bind_company(
    data: CompanyBindRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """绑定公司：join=加入已有公司；create=新注册公司（仅管理员/最高级管理员）

    绑定成功后 company_id 固定，不可再更改公司。
    """
    if current_user.company_id:
        return ApiResponse(code=400, message="已绑定公司，公司归属不可更改")

    mode = data.mode
    try:
        if mode == "create":
            if current_user.role not in ("super_admin", "admin"):
                return ApiResponse(code=403, message="仅管理员可新注册公司")
            company = await create_company(db, data.company_name, data.company_password, created_by=current_user.id)
        else:  # join
            company = await verify_company(db, data.company_name, data.company_password)
            if not company:
                return ApiResponse(code=400, message="公司名称或公司数据库密码错误，请核对后重试")
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))

    # 绑定公司
    current_user.company_id = company.id
    current_user.company_name = company.company_name
    current_user.contact_person = data.contact_person or ""
    current_user.contact_phone = data.contact_phone or ""
    current_user.company_address = data.company_address or ""
    await db.flush()

    from app.routers.auth import _user_to_response
    return ApiResponse(
        data=_user_to_response(current_user).model_dump(),
        message="公司信息绑定成功",
    )


@router.put("/password", response_model=ApiResponse)
async def change_db_password(
    data: CompanyPasswordChangeRequest,
    current_user: User = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改公司数据库密码。

    普通管理员只能修改自己所在公司；最高级管理员可通过 company_name 指定任意公司。
    均需提供该公司当前密码（old_password）。
    """
    try:
        ok = await change_company_password(db, current_user, data.old_password, data.new_password, data.company_name)
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))
    if not ok:
        return ApiResponse(code=400, message="公司数据库密码错误，或无权限修改该公司")
    return ApiResponse(message="公司数据库密码修改成功")
