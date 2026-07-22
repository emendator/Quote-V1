"""商品 CRUD API"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    BatchDeleteRequest, ApiResponse,
    RecommendedProductRequest, RecommendedProduct,
)
from app.services import product_service
from app.models import User
from app.utils.auth_utils import get_current_user
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """商品列表（分页、搜索、筛选、排序，仅显示当前用户的数据）"""
    items, total = await product_service.get_products(
        db, page, page_size, keyword, category, sort_by, sort_order, price_min, price_max,
        owner_id=current_user.id
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出商品数据为 Excel 文件（仅当前用户数据）"""
    excel_bytes = await product_service.export_products(
        db, keyword, category, sort_by, sort_order, price_min, price_max,
        owner_id=current_user.id
    )
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=products.xlsx",
            "Content-Length": str(len(excel_bytes)),
        },
    )


@router.get("/categories", response_model=ApiResponse)
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有一级品类（当前用户数据）"""
    cats = await product_service.get_all_categories(db, owner_id=current_user.id)
    return ApiResponse(data=cats)


@router.get("/brands", response_model=ApiResponse)
async def list_brands(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有品牌（当前用户数据）"""
    brands = await product_service.get_all_brands(db, owner_id=current_user.id)
    return ApiResponse(data=brands)


@router.get("/categories/level2", response_model=ApiResponse)
async def list_category_level2(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有二级品类（当前用户数据）"""
    cats = await product_service.get_all_category_level2(db, owner_id=current_user.id)
    return ApiResponse(data=cats)


@router.get("/categories/level3", response_model=ApiResponse)
async def list_category_level3(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有三级品类（当前用户数据）"""
    cats = await product_service.get_all_category_level3(db, owner_id=current_user.id)
    return ApiResponse(data=cats)


@router.post("/batch-detail", response_model=ApiResponse)
async def batch_product_detail(
    data: BatchDetailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量获取商品详情（仅当前用户数据）"""
    products = await product_service.get_products_by_ids(db, data.ids, owner_id=current_user.id)
    return ApiResponse(data=[ProductResponse.model_validate(p).model_dump() for p in products])


class BatchDetailRequest(BaseModel):
    ids: List[int]


@router.get("/{product_id}", response_model=ApiResponse)
async def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """商品详情（仅当前用户数据）"""
    product = await product_service.get_product_by_id(db, product_id, owner_id=current_user.id)
    if not product:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump())


@router.post("", response_model=ApiResponse)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新增商品（绑定到当前用户）"""
    product = await product_service.create_product(db, data.model_dump(by_alias=True), owner_id=current_user.id)
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump(), message="新增成功")


@router.put("/{product_id}", response_model=ApiResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """编辑商品（仅当前用户数据）"""
    update_data = data.model_dump(exclude_none=True, by_alias=True)
    product = await product_service.update_product(db, product_id, update_data, owner_id=current_user.id)
    if not product:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump(), message="更新成功")


@router.delete("/{product_id}", response_model=ApiResponse)
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除商品（仅当前用户数据）"""
    success = await product_service.delete_product(db, product_id, owner_id=current_user.id)
    if not success:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(message="删除成功")


@router.post("/batch/delete", response_model=ApiResponse)
async def batch_delete(
    data: BatchDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量删除商品（仅当前用户数据）"""
    count = await product_service.batch_delete_products(db, data.ids, owner_id=current_user.id)
    return ApiResponse(data={"deleted": count}, message=f"成功删除 {count} 个商品")


@router.post("/recommended", response_model=ApiResponse)
async def get_recommended_products(
    data: RecommendedProductRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取推荐产品：基于邀请链，只推荐直属上级及其以上权限账号的产品

    推荐规则（按邀请链溯源）：
    - 用户 d 被管理员 a 邀请 → d 的推荐来源：a（直接邀请人）+ S（a的邀请人，即最高级管理员）
    - 管理员 a 被最高级管理员 S 邀请 → a 的推荐来源：S
    - 排序：最高级管理员优先，然后是直接邀请人
    """
    from app.models import User as UserModel
    from app.models import InviteCode
    from sqlalchemy import select, or_

    # 最高级管理员无推荐
    if current_user.role == "super_admin":
        return ApiResponse(data={
            "items": [], "total": 0,
            "page": data.page, "page_size": data.page_size,
            "recommendation_note": "",
        })

    # 沿邀请链向上查找所有来源用户（含当前用户的邀请人 + 邀请人的邀请人...）
    source_user_ids = []
    source_user_map = {}
    visited = set()
    next_user_id = current_user.id

    while next_user_id and next_user_id not in visited:
        visited.add(next_user_id)
        # 查找该用户使用了哪个邀请码注册的
        invite_result = await db.execute(
            select(InviteCode).where(
                InviteCode.used_by == next_user_id,
                InviteCode.is_used == True,
            )
        )
        invite = invite_result.scalar_one_or_none()
        if not invite:
            break
        inviter_id = invite.created_by
        if inviter_id == next_user_id or inviter_id in visited:
            break
        # 查询邀请人信息
        inviter_result = await db.execute(
            select(UserModel).where(UserModel.id == inviter_id, UserModel.is_active == True)
        )
        inviter = inviter_result.scalar_one_or_none()
        if not inviter:
            break
        source_user_ids.append(inviter.id)
        source_user_map[inviter.id] = inviter
        next_user_id = inviter.id  # 继续溯源

    if not source_user_ids:
        return ApiResponse(data={
            "items": [], "total": 0,
            "page": data.page, "page_size": data.page_size,
            "recommendation_note": "暂无推荐产品",
        })

    # 构建查询
    from app.models import Product
    query = select(Product).where(Product.owner_id.in_(source_user_ids))
    count_query = select(func.count(Product.id)).where(Product.owner_id.in_(source_user_ids))

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

    # 分页并排序（邀请链越近的越靠前，但最高级管理员始终在最前）
    offset = (data.page - 1) * data.page_size
    query = query.order_by(Product.owner_id.asc(), Product.id.desc())
    query = query.offset(offset).limit(data.page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    # 组装结果（附加来源公司信息）
    items = []
    for p in products:
        owner = source_user_map.get(p.owner_id)
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

    # 按来源角色排序（super_admin 在前，然后按邀请链顺序）
    # source_user_ids 的顺序是：直接邀请人 → 邀请人的邀请人 → ... → 根
    # 先找出 super_admin 的 ID，把它们排到最前面
    super_admin_ids = [uid for uid in source_user_ids if source_user_map[uid].role == "super_admin"]
    other_ids = [uid for uid in source_user_ids if source_user_map[uid].role != "super_admin"]
    sorted_owner_ids = super_admin_ids + other_ids
    owner_rank = {uid: i for i, uid in enumerate(sorted_owner_ids)}
    items.sort(key=lambda x: owner_rank.get(x.get("owner_id", 0), 999))

    note = "以下为推荐产品，来自其他公司，如需购买请联系对应公司"

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": data.page,
        "page_size": data.page_size,
        "recommendation_note": note,
    })
