"""商品 CRUD API"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    PaginatedResponse, BatchDeleteRequest, ApiResponse,
)
from app.services import product_service

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
    db: AsyncSession = Depends(get_db),
):
    """商品列表（分页、搜索、筛选、排序）"""
    items, total = await product_service.get_products(
        db, page, page_size, keyword, category, sort_by, sort_order, price_min, price_max
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
    db: AsyncSession = Depends(get_db),
):
    """导出商品数据为 Excel 文件"""
    excel_bytes = await product_service.export_products(
        db, keyword, category, sort_by, sort_order, price_min, price_max
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
async def list_categories(db: AsyncSession = Depends(get_db)):
    """获取所有一级品类"""
    cats = await product_service.get_all_categories(db)
    return ApiResponse(data=cats)


@router.get("/brands", response_model=ApiResponse)
async def list_brands(db: AsyncSession = Depends(get_db)):
    """获取所有品牌"""
    brands = await product_service.get_all_brands(db)
    return ApiResponse(data=brands)


@router.get("/categories/level2", response_model=ApiResponse)
async def list_category_level2(db: AsyncSession = Depends(get_db)):
    """获取所有二级品类"""
    cats = await product_service.get_all_category_level2(db)
    return ApiResponse(data=cats)


@router.get("/{product_id}", response_model=ApiResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """商品详情"""
    product = await product_service.get_product_by_id(db, product_id)
    if not product:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump())


@router.post("", response_model=ApiResponse)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    """新增商品"""
    product = await product_service.create_product(db, data.model_dump(by_alias=True))
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump(), message="新增成功")


@router.put("/{product_id}", response_model=ApiResponse)
async def update_product(product_id: int, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    """编辑商品"""
    update_data = data.model_dump(exclude_none=True, by_alias=True)
    product = await product_service.update_product(db, product_id, update_data)
    if not product:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(data=ProductResponse.model_validate(product).model_dump(), message="更新成功")


@router.delete("/{product_id}", response_model=ApiResponse)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """删除商品"""
    success = await product_service.delete_product(db, product_id)
    if not success:
        return ApiResponse(code=404, message="商品不存在")
    return ApiResponse(message="删除成功")


@router.post("/batch/delete", response_model=ApiResponse)
async def batch_delete(data: BatchDeleteRequest, db: AsyncSession = Depends(get_db)):
    """批量删除商品"""
    count = await product_service.batch_delete_products(db, data.ids)
    return ApiResponse(data={"deleted": count}, message=f"成功删除 {count} 个商品")
