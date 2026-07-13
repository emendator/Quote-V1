"""商品管理业务逻辑"""
import io
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from app.models import Product


async def get_products(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "desc",
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> Tuple[List[Product], int]:
    """分页查询商品列表"""
    query = select(Product)
    count_query = select(func.count(Product.id))

    # 关键词搜索（商品型号/品牌/69码）
    if keyword:
        kw_filter = or_(
            Product.product_model.ilike(f"%{keyword}%"),
            Product.brand.ilike(f"%{keyword}%"),
            Product.barcode_69.ilike(f"%{keyword}%"),
        )
        query = query.where(kw_filter)
        count_query = count_query.where(kw_filter)

    # 分类筛选
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)

    # 价格区间
    if price_min is not None:
        query = query.where(Product.price >= price_min)
        count_query = count_query.where(Product.price >= price_min)
    if price_max is not None:
        query = query.where(Product.price <= price_max)
        count_query = count_query.where(Product.price <= price_max)

    # 排序
    sort_col = getattr(Product, sort_by, Product.id)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # 执行查询
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def export_products(
    db: AsyncSession,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "desc",
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> bytes:
    """导出全部符合条件的商品到 Excel 文件（无分页）"""
    query = select(Product)

    if keyword:
        kw_filter = or_(
            Product.product_model.ilike(f"%{keyword}%"),
            Product.brand.ilike(f"%{keyword}%"),
            Product.barcode_69.ilike(f"%{keyword}%"),
        )
        query = query.where(kw_filter)
    if category:
        query = query.where(Product.category == category)
    if price_min is not None:
        query = query.where(Product.price >= price_min)
    if price_max is not None:
        query = query.where(Product.price <= price_max)

    sort_col = getattr(Product, sort_by, Product.id)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    result = await db.execute(query)
    items = list(result.scalars().all())

    # 写入 Excel
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "商品数据"

    # 表头样式
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # 表头
    headers = [
        ("ID", 6), ("品牌", 14), ("商品图片", 30), ("类别", 12),
        ("商品型号", 18), ("规格", 22), ("京东划线价(元)", 14),
        ("成本价(元)", 12), ("代发价(元)", 12), ("69码", 16),
        ("供应商", 16), ("店铺链接", 30), ("折扣率(%)", 10),
        ("库存", 8), ("备注", 20),
    ]
    for col_idx, (header_text, width) in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    # 数据行
    price_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    for row_idx, item in enumerate(items, 2):
        values = [
            item.id, item.brand, item.product_image, item.category,
            item.product_model, item.specification, item.jd_price or 0,
            item.cost_price or 0, item.price, item.barcode_69,
            item.supplier, item.shop_url, item.discount_rate,
            item.stock, item.remark,
        ]
        for col_idx, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")
            # 代发价列淡黄色背景
            if col_idx == 9:
                cell.fill = price_fill
                cell.number_format = '#,##0.00'
            elif col_idx in (7, 8, 13):
                cell.number_format = '#,##0.00'
        # 冻结首行
        ws.freeze_panes = "A2"

    # 自动筛选
    ws.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(len(headers))}{len(items) + 1}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
    """根据 ID 获取商品"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, data: dict) -> Product:
    """新增商品"""
    product = Product(**data)
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def update_product(db: AsyncSession, product_id: int, data: dict) -> Optional[Product]:
    """更新商品"""
    product = await get_product_by_id(db, product_id)
    if not product:
        return None
    for key, value in data.items():
        if value is not None and hasattr(product, key):
            setattr(product, key, value)
    await db.flush()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, product_id: int) -> bool:
    """删除单个商品"""
    product = await get_product_by_id(db, product_id)
    if not product:
        return False
    await db.delete(product)
    await db.flush()
    return True


async def batch_delete_products(db: AsyncSession, ids: List[int]) -> int:
    """批量删除商品，返回删除数量"""
    result = await db.execute(delete(Product).where(Product.id.in_(ids)))
    await db.flush()
    return result.rowcount


async def get_all_categories(db: AsyncSession) -> List[str]:
    """获取所有分类"""
    result = await db.execute(select(Product.category).distinct().where(Product.category != ""))
    return [row[0] for row in result.all()]
