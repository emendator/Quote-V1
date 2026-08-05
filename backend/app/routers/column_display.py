"""列显示配置 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import (
    ApiResponse,
    ColumnDisplayUpdateRequest,
)
from app.services import column_display_service as cds
from app.models import User
from app.utils.auth_utils import get_current_user

router = APIRouter(prefix="/api/column-display", tags=["列显示配置"])


@router.get("/{page_type}", response_model=ApiResponse)
async def get_column_display(
    page_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定页面的列显示配置（所有登录用户可用）"""
    if page_type not in ("product_db", "query_result", "batch_query", "solution_items"):
        return ApiResponse(code=400, message="无效的页面类型，可选: product_db, query_result, batch_query, solution_items")

    columns = await cds.get_column_display_config(db, current_user.id, page_type)
    return ApiResponse(data={
        "page_type": page_type,
        "columns": columns,
    })


@router.put("/{page_type}", response_model=ApiResponse)
async def update_column_display(
    page_type: str,
    data: ColumnDisplayUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新指定页面的列显示配置

    权限：
    - product_db（产品库）：仅管理员和最高级管理员可配置
    - query_result / batch_query（查询结果）：所有登录用户可配置
    """
    if page_type not in ("product_db", "query_result", "batch_query", "solution_items"):
        return ApiResponse(code=400, message="无效的页面类型，可选: product_db, query_result, batch_query, solution_items")

    # 权限检查：产品库配置仅管理员以上
    if page_type == "product_db" and current_user.role not in ("super_admin", "admin"):
        return ApiResponse(code=403, message="仅管理员和最高级管理员可配置产品库列显示")

    columns = [c.model_dump() for c in data.columns]
    saved = await cds.save_column_display_config(db, current_user.id, page_type, columns)
    return ApiResponse(data={
        "page_type": page_type,
        "columns": saved,
    }, message="列显示配置已更新")


@router.get("/available-columns/{page_type}", response_model=ApiResponse)
async def get_available_columns(
    page_type: str,
    current_user: User = Depends(get_current_user),
):
    """获取指定页面类型的所有可用列（所有登录用户可用）"""
    if page_type not in ("product_db", "query_result", "batch_query", "solution_items"):
        return ApiResponse(code=400, message="无效的页面类型，可选: product_db, query_result, batch_query, solution_items")

    columns = cds.get_available_columns(page_type)
    return ApiResponse(data={
        "page_type": page_type,
        "columns": columns,
    })
