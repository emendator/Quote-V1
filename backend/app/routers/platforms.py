"""
平台配置管理与一键上架 API
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PlatformConfig
from app.schemas import (
    ApiResponse,
    PlatformConfigCreate,
    PlatformConfigUpdate,
    PlatformConfigResponse,
    ListingSubmitRequest,
    ListingLogResponse,
    ListingLogDetailResponse,
)
from app.services.listing_service import listing_service

router = APIRouter(prefix="/api", tags=["平台管理与一键上架"])
logger = logging.getLogger("platforms")


# ======================================================================
# 平台配置 CRUD
# ======================================================================

@router.get("/platforms", response_model=ApiResponse)
async def list_platforms(db: AsyncSession = Depends(get_db)):
    """获取所有平台配置"""
    from sqlalchemy import select
    result = await db.execute(select(PlatformConfig).order_by(PlatformConfig.id))
    platforms = result.scalars().all()
    return ApiResponse(data=[p.to_dict() for p in platforms])


@router.post("/platforms", response_model=ApiResponse)
async def create_platform(data: PlatformConfigCreate, db: AsyncSession = Depends(get_db)):
    """新增平台配置"""
    platform = PlatformConfig(
        name=data.name,
        platform_type=data.platform_type,
        api_base_url=data.api_base_url,
        api_key=data.api_key,
        api_secret=data.api_secret,
        shop_id=data.shop_id,
        extra_config=json.dumps(data.extra_config, ensure_ascii=False),
        is_active=1 if data.is_active else 0,
    )
    db.add(platform)
    await db.flush()
    await db.refresh(platform)
    logger.info(f"新增平台配置: {platform.name} ({platform.platform_type})")
    return ApiResponse(data=platform.to_dict(), message="新增成功")


@router.put("/platforms/{platform_id}", response_model=ApiResponse)
async def update_platform(
    platform_id: int,
    data: PlatformConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新平台配置"""
    from sqlalchemy import select
    result = await db.execute(select(PlatformConfig).where(PlatformConfig.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        return ApiResponse(code=404, message="平台配置不存在")

    update_dict = data.model_dump(exclude_none=True)
    # 处理特殊字段
    if "extra_config" in update_dict and update_dict["extra_config"] is not None:
        update_dict["extra_config"] = json.dumps(update_dict["extra_config"], ensure_ascii=False)
    if "is_active" in update_dict:
        update_dict["is_active"] = 1 if update_dict["is_active"] else 0

    for key, value in update_dict.items():
        setattr(platform, key, value)

    await db.flush()
    await db.refresh(platform)
    logger.info(f"更新平台配置: {platform.name}")
    return ApiResponse(data=platform.to_dict(), message="更新成功")


@router.delete("/platforms/{platform_id}", response_model=ApiResponse)
async def delete_platform(platform_id: int, db: AsyncSession = Depends(get_db)):
    """删除平台配置"""
    from sqlalchemy import select
    result = await db.execute(select(PlatformConfig).where(PlatformConfig.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        return ApiResponse(code=404, message="平台配置不存在")

    await db.delete(platform)
    await db.flush()
    logger.info(f"删除平台配置: {platform.name}")
    return ApiResponse(message="删除成功")


@router.post("/platforms/{platform_id}/test", response_model=ApiResponse)
async def test_platform_connection(platform_id: int, db: AsyncSession = Depends(get_db)):
    """测试平台连接"""
    result = await listing_service.test_platform_connection(db, platform_id)
    return ApiResponse(data=result, message=result.get("message", ""))


# ======================================================================
# 一键上架
# ======================================================================

@router.post("/listing/submit", response_model=ApiResponse)
async def submit_listing(data: ListingSubmitRequest, db: AsyncSession = Depends(get_db)):
    """提交商品上架"""
    if not data.product_ids:
        return ApiResponse(code=400, message="请选择要上架的商品")
    if not data.platform_ids:
        return ApiResponse(code=400, message="请选择目标平台")

    result = await listing_service.submit_listing(db, data.product_ids, data.platform_ids)
    return ApiResponse(data=result, message=f"上架完成: 成功{result['success']}个, 失败{result['failed']}个")


@router.get("/listing/logs", response_model=ApiResponse)
async def list_listing_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    status: Optional[str] = None,
    platform_id: Optional[int] = None,
    product_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """上架日志列表"""
    items, total = await listing_service.get_listing_logs(
        db, page, page_size, status, platform_id, product_id
    )
    return ApiResponse(data={
        "items": [ListingLogResponse.model_validate(log).model_dump() for log in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/listing/logs/{log_id}", response_model=ApiResponse)
async def get_listing_log_detail(log_id: int, db: AsyncSession = Depends(get_db)):
    """上架日志详情"""
    log = await listing_service.get_listing_log_detail(db, log_id)
    if not log:
        return ApiResponse(code=404, message="日志不存在")

    detail = ListingLogDetailResponse(
        id=log.id,
        product_id=log.product_id,
        product_model=log.product_model or "",
        product_name=log.product_name or "",
        platform_id=log.platform_id,
        platform_name=log.platform_name or "",
        status=log.status,
        platform_product_id=log.platform_product_id or "",
        error_message=log.error_message or "",
        created_at=log.created_at,
        request_data=json.loads(log.request_data) if log.request_data else {},
        response_data=json.loads(log.response_data) if log.response_data else {},
    )
    return ApiResponse(data=detail.model_dump())
