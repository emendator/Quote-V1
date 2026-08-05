"""商品管理业务逻辑"""
import io
import json
from typing import Optional, List, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from app.models import Product
from app.utils.excel_utils import add_image_embedded_in_cell, normalize_datetime_string


async def get_products(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    company_id: Optional[int] = None,
    filters: Optional[Dict[str, List[str]]] = None,
) -> Tuple[List[Product], int]:
    """分页查询商品列表（数据隔离：按公司ID过滤）"""
    query = select(Product)
    count_query = select(func.count(Product.id))

    # 数据隔离：按 company_id 过滤（同一公司共享数据）
    if company_id:
        query = query.where(Product.company_id == company_id)
        count_query = count_query.where(Product.company_id == company_id)

    # 关键词搜索（快查型号/商品型号/品牌/产品名称/69码）
    if keyword:
        kw_filter = or_(
            Product.quick_model.ilike(f"%{keyword}%"),
            Product.product_model.ilike(f"%{keyword}%"),
            Product.brand.ilike(f"%{keyword}%"),
            Product.product_name.ilike(f"%{keyword}%"),
            Product.barcode_69.ilike(f"%{keyword}%"),
        )
        query = query.where(kw_filter)
        count_query = count_query.where(kw_filter)

    # 分类筛选（一级品类）
    if category:
        query = query.where(
            or_(Product.category_level1 == category, Product.category_level2 == category)
        )
        count_query = count_query.where(
            or_(Product.category_level1 == category, Product.category_level2 == category)
        )

    # 价格区间
    if price_min is not None:
        query = query.where(Product.price >= price_min)
        count_query = count_query.where(Product.price >= price_min)
    if price_max is not None:
        query = query.where(Product.price <= price_max)
        count_query = count_query.where(Product.price <= price_max)

    # ---- 表头下拉筛选（多值 OR 匹配）----
    if filters:
        field_map = {
            "quick_model": Product.quick_model,
            "product_model": Product.product_model,
            "product_name": Product.product_name,
            "brand": Product.brand,
            "category_level1": Product.category_level1,
            "category_level2": Product.category_level2,
            "category_level3": Product.category_level3,
            "price_update": Product.price_update,
            "shop_url": Product.shop_url,
            "box_spec": Product.box_spec,
            "cooperation_level": Product.cooperation_level,
            "supply_status": Product.supply_status,
            "specification": Product.specification,
            "remark": Product.remark,
            "barcode_69": Product.barcode_69,
            "recommendation": Product.recommendation,
            "parameters": Product.parameters,
            "cert_3c": Product.cert_3c,
        }
        for field_name, values in filters.items():
            if field_name not in field_map:
                continue
            if not values or not isinstance(values, list):
                continue
            col = field_map[field_name]
            # 生成 OR 条件：匹配任一选中值
            or_conds = [col == v for v in values]
            query = query.where(or_(*or_conds))
            count_query = count_query.where(or_(*or_conds))

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
    sort_order: str = "asc",
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    company_id: Optional[int] = None,
) -> bytes:
    """导出全部符合条件的商品到 Excel 文件（无分页，数据隔离）"""
    query = select(Product)

    # 数据隔离：按 company_id 过滤
    if company_id:
        query = query.where(Product.company_id == company_id)

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

    return _build_products_excel(items)


async def export_products_by_ids(
    db: AsyncSession,
    product_ids: List[int],
    company_id: Optional[int] = None,
) -> bytes:
    """根据商品 ID 列表导出 Excel（含图片嵌入）"""
    query = select(Product).where(Product.id.in_(product_ids))
    if company_id:
        query = query.where(Product.company_id == company_id)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return _build_products_excel(items)


def _build_products_excel(items: List[Product]) -> bytes:
    """将 Product ORM 对象列表生成为 Excel 字节流（含图片）"""
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "商品数据"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    headers = [
        ("序号", 6), ("快查型号", 18), ("型号", 18),
        ("产品名称", 20), ("品牌", 14), ("一级品类", 14),
        ("二级品类", 14), ("三级品类", 14), ("备货商谈价(元)", 14), ("报价更新", 14),
        ("上次进货价(元)", 14), ("进货价(元)", 12), ("零售价(元)", 12),
        ("折扣率(%)", 10), ("新活动价(元)", 14), ("链接", 30), ("投标价(元)", 12),
        ("集采价/项目(元)", 14), ("代发价(元)", 12), ("毛重(kg)", 10),
        ("箱规", 12), ("合作等级", 12), ("供货状态", 12),
        ("规格", 20), ("备注", 20), ("代发运费(元)", 14),
        ("69码", 16), ("销量", 10), ("推荐理由", 20),
        ("参数", 20), ("3C", 16), ("图片", 12),
    ]
    for col_idx, (header_text, width) in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    price_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    for row_idx, item in enumerate(items, 2):
        seq = row_idx - 1
        values = [
            seq, item.quick_model, item.product_model,
            item.product_name, item.brand, item.category_level1,
            item.category_level2, item.category_level3, item.negotiation_price or 0, normalize_datetime_string(item.price_update),
            item.last_purchase_price or 0, item.purchase_price or 0, item.retail_price or 0,
            item.discount_rate, item.new_event_price or 0, item.shop_url, item.bid_price or 0,
            item.group_purchase_price or 0, item.price, item.gross_weight or 0,
            item.box_spec, item.cooperation_level, item.supply_status,
            item.specification, item.remark, item.shipping_fee or 0,
            item.barcode_69, item.sales_volume, item.recommendation,
            item.parameters, item.cert_3c,
            "",  # 图片占位（后面单独处理）
        ]
        for col_idx, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")
            if col_idx == 18:
                cell.fill = price_fill
                cell.number_format = '#,##0.00'
            elif col_idx in (8, 10, 11, 12, 14, 16, 17, 19, 25):
                cell.number_format = '#,##0.00'

        # ---- 图片列：以 TwoCellAnchor 嵌入单元格（随单元格移动/缩放）----
        if not add_image_embedded_in_cell(
            ws, row_idx, 32, item.image or "", col_width=12, row_height=40
        ):
            # 无图或图片解析失败时写入占位文本
            ws.cell(row=row_idx, column=32).value = "[图片]"

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(len(headers))}{len(items) + 1}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


async def get_product_by_id(db: AsyncSession, product_id: int, company_id: Optional[int] = None) -> Optional[Product]:
    """根据 ID 获取商品（数据隔离：按公司ID）"""
    query = select(Product).where(Product.id == product_id)
    if company_id:
        query = query.where(Product.company_id == company_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_products_by_ids(db: AsyncSession, ids: List[int], company_id: Optional[int] = None) -> List[Product]:
    """批量获取商品详情（数据隔离）"""
    query = select(Product).where(Product.id.in_(ids))
    if company_id:
        query = query.where(Product.company_id == company_id)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_product(db: AsyncSession, data: dict, company_id: Optional[int] = None, company_name: Optional[str] = None) -> Product:
    """新增商品（绑定 company_id 用于数据隔离，company_name 用于展示）"""
    if company_id:
        data["company_id"] = company_id
    if company_name:
        data["company_name"] = company_name
    product = Product(**data)
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def update_product(db: AsyncSession, product_id: int, data: dict, company_id: Optional[int] = None) -> Optional[Product]:
    """更新商品（数据隔离）"""
    product = await get_product_by_id(db, product_id, company_id=company_id)
    if not product:
        return None
    for key, value in data.items():
        if value is not None and hasattr(product, key):
            setattr(product, key, value)
    await db.flush()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, product_id: int, company_id: Optional[int] = None) -> bool:
    """删除单个商品（数据隔离）"""
    product = await get_product_by_id(db, product_id, company_id=company_id)
    if not product:
        return False
    await db.delete(product)
    await db.flush()
    return True


async def batch_delete_products(db: AsyncSession, ids: List[int], company_id: Optional[int] = None) -> int:
    """批量删除商品（数据隔离）"""
    query = delete(Product).where(Product.id.in_(ids))
    if company_id:
        query = query.where(Product.company_id == company_id)
    result = await db.execute(query)
    await db.flush()
    return result.rowcount


async def get_all_categories(db: AsyncSession, company_id: Optional[int] = None) -> List[str]:
    """获取所有一级品类（数据隔离）"""
    query = select(Product.category_level1).distinct().where(Product.category_level1 != "")
    if company_id:
        query = query.where(Product.company_id == company_id)
    query = query.order_by(Product.category_level1)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_all_brands(db: AsyncSession, company_id: Optional[int] = None) -> List[str]:
    """获取所有品牌（数据隔离）"""
    query = select(Product.brand).distinct().where(Product.brand != "")
    if company_id:
        query = query.where(Product.company_id == company_id)
    query = query.order_by(Product.brand)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_all_category_level2(db: AsyncSession, company_id: Optional[int] = None) -> List[str]:
    """获取所有二级品类（数据隔离）"""
    query = select(Product.category_level2).distinct().where(Product.category_level2 != "")
    if company_id:
        query = query.where(Product.company_id == company_id)
    query = query.order_by(Product.category_level2)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def get_all_category_level3(db: AsyncSession, company_id: Optional[int] = None) -> List[str]:
    """获取所有三级品类（数据隔离）"""
    query = select(Product.category_level3).distinct().where(Product.category_level3 != "")
    if company_id:
        query = query.where(Product.company_id == company_id)
    query = query.order_by(Product.category_level3)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


# 表头下拉筛选需要获取全量数据的所有可选值
FILTERABLE_COLUMN_FIELDS = {
    "quick_model": Product.quick_model,
    "product_model": Product.product_model,
    "product_name": Product.product_name,
    "brand": Product.brand,
    "category_level1": Product.category_level1,
    "category_level2": Product.category_level2,
    "category_level3": Product.category_level3,
    "price_update": Product.price_update,
    "shop_url": Product.shop_url,
    "box_spec": Product.box_spec,
    "cooperation_level": Product.cooperation_level,
    "supply_status": Product.supply_status,
    "specification": Product.specification,
    "remark": Product.remark,
    "barcode_69": Product.barcode_69,
    "recommendation": Product.recommendation,
    "parameters": Product.parameters,
    "cert_3c": Product.cert_3c,
}


async def get_filter_options(db: AsyncSession, company_id: Optional[int] = None) -> Dict[str, List[str]]:
    """获取所有可筛选列的全局可选值（跨分页、跨搜索），支持数据隔离"""
    result: Dict[str, List[str]] = {}
    for field_name, column in FILTERABLE_COLUMN_FIELDS.items():
        query = select(column).distinct().where(column != "", column.isnot(None))
        if company_id:
            query = query.where(Product.company_id == company_id)
        query = query.order_by(column)
        rows = await db.execute(query)
        result[field_name] = [row[0] for row in rows.all()]
    return result
