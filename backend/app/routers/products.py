"""商品 CRUD API"""
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    BatchDeleteRequest, ApiResponse,
    RecommendedProductRequest, RecommendedProduct,
)
from app.services import product_service
from app.models import User
from app.utils.auth_utils import require_company, require_company_admin
from sqlalchemy import func

router = APIRouter(prefix="/api/products", tags=["商品管理"])


@router.get("", response_model=ApiResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    filters: Optional[str] = Query(None, description="JSON 编码的列筛选条件，如 {\"brand\":[\"飞利浦\"]}"),
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """商品列表（分页、搜索、筛选、排序，仅显示当前用户的数据）"""
    import json
    parsed_filters = None
    if filters:
        try:
            parsed_filters = json.loads(filters)
        except (json.JSONDecodeError, TypeError):
            pass

    items, total = await product_service.get_products(
        db, page, page_size, keyword, category, sort_by, sort_order, price_min, price_max,
        company_id=current_user.company_id,
        filters=parsed_filters,
    )
    return ApiResponse(data={
        "items": [ProductResponse.model_validate(p).model_dump() for p in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/export")
async def export_products(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """导出商品数据为 Excel 文件（仅当前用户数据）"""
    excel_bytes = await product_service.export_products(
        db, keyword, category, sort_by, sort_order, price_min, price_max,
        company_id=current_user.company_id
    )
    from urllib.parse import quote
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('products.xlsx')}",
            "Content-Length": str(len(excel_bytes)),
        },
    )


@router.get("/categories", response_model=ApiResponse)
async def list_categories(
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """获取所有一级品类（当前用户数据）"""
    cats = await product_service.get_all_categories(db, company_id=current_user.company_id)
    return ApiResponse(data=cats)


@router.get("/brands", response_model=ApiResponse)
async def list_brands(
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """获取所有品牌（当前用户数据）"""
    brands = await product_service.get_all_brands(db, company_id=current_user.company_id)
    return ApiResponse(data=brands)


@router.get("/categories/level2", response_model=ApiResponse)
async def list_category_level2(
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """获取所有二级品类（当前用户数据）"""
    cats = await product_service.get_all_category_level2(db, company_id=current_user.company_id)
    return ApiResponse(data=cats)


@router.get("/categories/level3", response_model=ApiResponse)
async def list_category_level3(
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """获取所有三级品类（当前用户数据）"""
    cats = await product_service.get_all_category_level3(db, company_id=current_user.company_id)
    return ApiResponse(data=cats)


@router.get("/filter-options", response_model=ApiResponse)
async def list_filter_options(
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """获取所有可筛选列的全局可选值（表头下拉筛选用），支持数据隔离"""
    options = await product_service.get_filter_options(db, company_id=current_user.company_id)
    return ApiResponse(data=options)


class BatchDetailRequest(BaseModel):
    ids: List[int]


@router.post("/batch-detail", response_model=ApiResponse)
async def batch_product_detail(
    data: BatchDetailRequest,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """批量获取商品详情（仅当前用户数据）"""
    products = await product_service.get_products_by_ids(db, data.ids, company_id=current_user.company_id)
    return ApiResponse(data=[ProductResponse.model_validate(p).model_dump() for p in products])


@router.get("/{product_id}", response_model=ApiResponse)
async def get_product(
    product_id: int,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """商品详情（仅当前用户数据）"""
    product = await product_service.get_product_by_id(db, product_id, company_id=current_user.company_id)
    if not product:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump())


@router.post("", response_model=ApiResponse)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db),
):
    """新增商品（仅管理员/最高级管理员可操作）"""
    product = await product_service.create_product(db, data.model_dump(by_alias=True), company_id=current_user.company_id, company_name=current_user.company_name)
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump(), message="新增成功")


@router.put("/{product_id}", response_model=ApiResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑商品（仅管理员/最高级管理员可操作）"""
    update_data = data.model_dump(exclude_none=True, by_alias=True)
    product = await product_service.update_product(db, product_id, update_data, company_id=current_user.company_id)
    if not product:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump(), message="更新成功")


@router.delete("/{product_id}", response_model=ApiResponse)
async def delete_product(
    product_id: int,
    current_user: User = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除商品（仅管理员/最高级管理员可操作）"""
    success = await product_service.delete_product(db, product_id, company_id=current_user.company_id)
    if not success:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(message="删除成功")


@router.post("/batch/delete", response_model=ApiResponse)
async def batch_delete(
    data: BatchDeleteRequest,
    current_user: User = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量删除商品（仅管理员/最高级管理员可操作）"""
    count = await product_service.batch_delete_products(db, data.ids, company_id=current_user.company_id)
    return ApiResponse(data={"deleted": count}, message=f"成功删除 {count} 个商品")


@router.post("/recommended", response_model=ApiResponse)
async def get_recommended_products(
    data: RecommendedProductRequest,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """获取推荐产品（基于邀请链）

    推荐规则（基于邀请码的创建关系）：
    - 最高级管理员无推荐（没有更高级别）
    - 沿着邀请链向上查找：找到创建者的公司，如果不同公司且角色更高则推荐其产品
    - 例如：用户A创建邀请码给用户B，B注册后在自己的公司下，A的公司与B不同
      → A的产品会推荐给B
    - 同级或低权限不推荐
    - 同公司不推荐
    """
    from app.models import User as UserModel
    from app.models import Product, InviteCode
    from sqlalchemy import select, or_

    # 最高级管理员无推荐
    if current_user.role == "super_admin":
        return ApiResponse(data={
            "items": [], "total": 0,
            "page": data.page, "page_size": data.page_size,
            "recommendation_note": "",
        })

    user_company_id = current_user.company_id
    if not user_company_id:
        return ApiResponse(data={
            "items": [], "total": 0,
            "page": data.page, "page_size": data.page_size,
            "recommendation_note": "暂无推荐产品（请先完善公司信息）",
        })

    # 沿着邀请链向上收集来源公司
    source_company_ids = []
    current_user_id = current_user.id
    visited_user_ids = {current_user_id}

    while True:
        # 查找当前用户使用的邀请码（即谁邀请的 ta）
        invite_result = await db.execute(
            select(InviteCode).where(
                InviteCode.used_by == current_user_id,
                InviteCode.is_used == True,
            )
        )
        invite = invite_result.scalar_one_or_none()
        if not invite:
            break

        creator_id = invite.created_by
        if creator_id in visited_user_ids:
            break  # 防止循环
        visited_user_ids.add(creator_id)

        # 查询创建者信息
        creator_result = await db.execute(
            select(UserModel).where(UserModel.id == creator_id, UserModel.is_active == True)
        )
        creator = creator_result.scalar_one_or_none()
        if not creator:
            break

        creator_company_id = creator.company_id
        # 同公司不推荐
        if creator_company_id == user_company_id or not creator_company_id:
            current_user_id = creator_id
            continue

        # 只有角色更高才推荐（super_admin > admin > user）
        role_hierarchy = {"super_admin": 3, "admin": 2, "user": 1}
        current_level = role_hierarchy.get(current_user.role, 0)
        creator_level = role_hierarchy.get(creator.role, 0)
        if creator_level > current_level and creator_company_id not in source_company_ids:
            source_company_ids.append(creator_company_id)

        # 继续向上查找
        current_user_id = creator_id

    if not source_company_ids:
        return ApiResponse(data={
            "items": [], "total": 0,
            "page": data.page, "page_size": data.page_size,
            "recommendation_note": "暂无推荐产品",
        })

    # 查询来源公司的用户信息（获取角色）
    source_users_result = await db.execute(
        select(UserModel).where(
            UserModel.company_id.in_(source_company_ids),
            UserModel.is_active == True,
        )
    )
    source_users = source_users_result.scalars().all()
    source_user_map = {u.id: u for u in source_users}

    # 构建产品查询（不同公司的产品）
    query = select(Product).where(Product.company_id.in_(source_company_ids))
    count_query = select(func.count(Product.id)).where(Product.company_id.in_(source_company_ids))

    filters = data.filters or {}
    if filters.get("brand"):
        query = query.where(Product.brand.ilike(f"%{filters['brand']}%"))
        count_query = count_query.where(Product.brand.ilike(f"%{filters['brand']}%"))
    if filters.get("category_level1"):
        query = query.where(Product.category_level1 == filters["category_level1"])
        count_query = count_query.where(Product.category_level1 == filters["category_level1"])
    if filters.get("price_min") is not None:
        query = query.where(Product.price >= filters["price_min"])
        count_query = count_query.where(Product.price >= filters["price_min"])
    if filters.get("price_max") is not None:
        query = query.where(Product.price <= filters["price_max"])
        count_query = count_query.where(Product.price <= filters["price_max"])
    if filters.get("keyword"):
        kw = filters["keyword"]
        kw_filter = or_(
            Product.quick_model.ilike(f"%{kw}%"),
            Product.product_name.ilike(f"%{kw}%"),
            Product.brand.ilike(f"%{kw}%"),
        )
        query = query.where(kw_filter)
        count_query = count_query.where(kw_filter)

    # 总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页（按公司角色排序：super_admin 公司在前）
    offset = (data.page - 1) * data.page_size
    query = query.order_by(Product.company_id.asc(), Product.id.desc())
    query = query.offset(offset).limit(data.page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    # 找出 super_admin 的公司名列表（用于排序）
    super_admin_companies = set(
        u.company_name for u in source_users if u.role == "super_admin"
    )

    # 组装结果（附加来源公司信息）
    items = []
    for p in products:
        # 找到该产品公司对应的一个来源用户作为代表（获取公司名和角色）
        owner = next((u for u in source_users if u.company_id == p.company_id), None)
        items.append(RecommendedProduct(
            id=p.id,
            owner_id=p.owner_id,
            quick_model=p.quick_model or "",
            product_model=p.product_model or "",
            product_name=p.product_name or "",
            brand=p.brand or "",
            category_level1=p.category_level1 or "",
            category_level2=p.category_level2 or "",
            category_level3=p.category_level3 or "",
            price=p.price or 0,
            specification=p.specification or "",
            supply_status=p.supply_status or "",
            image=p.image or "",
            source_company_name=owner.company_name if owner else "",
            source_role=owner.role if owner else "",
        ).model_dump())

    # 排序：super_admin 的公司在前，其他在后
    items.sort(key=lambda x: (
        0 if x.get("source_company_name") in super_admin_companies else 1,
        x.get("source_company_name", ""),
    ))

    note = "以下为推荐产品，来自其他公司，如需购买请联系对应公司"

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": data.page,
        "page_size": data.page_size,
        "recommendation_note": note,
    })
