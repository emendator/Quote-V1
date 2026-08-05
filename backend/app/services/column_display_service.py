"""列显示配置服务 —— 用户可自定义各页面的列显示和表头名称"""
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import ColumnDisplayConfig

logger = logging.getLogger("column_display_service")

# ========== 默认列配置（各页面类型） ==========

DEFAULT_COLUMNS: Dict[str, List[Dict[str, Any]]] = {
    "product_db": [
        {"key": "index", "label": "序号", "visible": True, "width": 56, "fixed": None},
        {"key": "quick_model", "label": "快查型号", "visible": True, "width": 160},
        {"key": "product_model", "label": "型号", "visible": True, "width": 130},
        {"key": "image", "label": "图片", "visible": True, "width": 65},
        {"key": "product_name", "label": "产品名称", "visible": True, "width": 160},
        {"key": "brand", "label": "品牌", "visible": True, "width": 70},
        {"key": "category_level1", "label": "一级品类", "visible": True, "width": 80},
        {"key": "category_level2", "label": "二级品类", "visible": True, "width": 80},
        {"key": "category_level3", "label": "三级品类", "visible": True, "width": 80},
        {"key": "negotiation_price", "label": "备货商谈价", "visible": True, "width": 80},
        {"key": "price_update", "label": "报价更新", "visible": True, "width": 95},
        {"key": "last_purchase_price", "label": "上次进货价", "visible": False, "width": 80},
        {"key": "purchase_price", "label": "进货价", "visible": True, "width": 80},
        {"key": "retail_price", "label": "零售价", "visible": True, "width": 80},
        {"key": "discount_rate", "label": "折扣率", "visible": True, "width": 70},
        {"key": "new_event_price", "label": "新活动价", "visible": True, "width": 80},
        {"key": "shop_url", "label": "链接", "visible": False, "width": 180},
        {"key": "bid_price", "label": "投标价", "visible": False, "width": 80},
        {"key": "group_purchase_price", "label": "集采价/项目", "visible": True, "width": 80},
        {"key": "price", "label": "代发价", "visible": True, "width": 80},
        {"key": "gross_weight", "label": "毛重(kg)", "visible": False, "width": 70},
        {"key": "box_spec", "label": "箱规", "visible": True, "width": 120},
        {"key": "cooperation_level", "label": "合作等级", "visible": False, "width": 70},
        {"key": "supply_status", "label": "供货状态", "visible": True, "width": 70},
        {"key": "specification", "label": "规格", "visible": True, "width": 130},
        {"key": "remark", "label": "备注", "visible": True, "width": 150},
        {"key": "shipping_fee", "label": "代发运费", "visible": False, "width": 80},
        {"key": "barcode_69", "label": "69码", "visible": True, "width": 150},
        {"key": "sales_volume", "label": "销量", "visible": False, "width": 60},
        {"key": "recommendation", "label": "推荐理由", "visible": False, "width": 150},
        {"key": "parameters", "label": "参数", "visible": False, "width": 100},
        {"key": "cert_3c", "label": "3C", "visible": False, "width": 70},
        {"key": "created_at", "label": "导入时间", "visible": True, "width": 160},
        {"key": "action", "label": "操作", "visible": True, "width": 120, "fixed": "right"},
    ],
    "query_result": [
        {"key": "image", "label": "图片", "visible": True, "width": 55},
        {"key": "quick_model", "label": "快查型号", "visible": True, "width": 115},
        {"key": "product_name", "label": "产品名称", "visible": True, "width": 125},
        {"key": "product_model", "label": "型号", "visible": True, "width": 110},
        {"key": "brand", "label": "品牌", "visible": True, "width": 55},
        {"key": "category_level1", "label": "一级品类", "visible": True, "width": 75},
        {"key": "category_level2", "label": "二级品类", "visible": True, "width": 75},
        {"key": "category_level3", "label": "三级品类", "visible": True, "width": 75},
        {"key": "price_update", "label": "报价更新", "visible": False, "width": 95},
        {"key": "negotiation_price", "label": "备货商谈价", "visible": False, "width": 75},
        {"key": "price", "label": "代发价", "visible": True, "width": 75},
        {"key": "purchase_price", "label": "进货价", "visible": False, "width": 75},
        {"key": "retail_price", "label": "零售价", "visible": False, "width": 75},
        {"key": "new_event_price", "label": "新活动价", "visible": False, "width": 75},
        {"key": "group_purchase_price", "label": "集采价", "visible": False, "width": 75},
        {"key": "bid_price", "label": "投标价", "visible": False, "width": 75},
        {"key": "discount_rate", "label": "折扣率", "visible": True, "width": 65},
        {"key": "shop_url", "label": "链接", "visible": False, "width": 150},
        {"key": "barcode_69", "label": "69码", "visible": True, "width": 140},
        {"key": "specification", "label": "规格", "visible": True, "width": 110},
        {"key": "box_spec", "label": "箱规", "visible": False, "width": 110},
        {"key": "cooperation_level", "label": "合作等级", "visible": False, "width": 65},
        {"key": "supply_status", "label": "供货状态", "visible": True, "width": 65},
        {"key": "gross_weight", "label": "毛重(kg)", "visible": False, "width": 65},
        {"key": "shipping_fee", "label": "代发运费", "visible": False, "width": 75},
        {"key": "sales_volume", "label": "销量", "visible": False, "width": 55},
        {"key": "recommendation", "label": "推荐理由", "visible": False, "width": 130},
        {"key": "parameters", "label": "参数", "visible": False, "width": 100},
        {"key": "cert_3c", "label": "3C", "visible": False, "width": 65},
        {"key": "remark", "label": "备注", "visible": False, "width": 140},
        {"key": "solution", "label": "方案", "visible": True, "width": 70, "fixed": "right"},
    ],
    "batch_query": [
        {"key": "image", "label": "图片", "visible": True, "width": 55},
        {"key": "quick_model", "label": "快查型号", "visible": True, "width": 130},
        {"key": "product_name", "label": "产品名称", "visible": True, "width": 140},
        {"key": "brand", "label": "品牌", "visible": True, "width": 55},
        {"key": "product_model", "label": "型号", "visible": True, "width": 110},
        {"key": "price_update", "label": "报价更新", "visible": False, "width": 95},
        {"key": "price", "label": "代发价", "visible": True, "width": 85},
        {"key": "purchase_price", "label": "进货价", "visible": False, "width": 80},
        {"key": "retail_price", "label": "零售价", "visible": False, "width": 80},
        {"key": "new_event_price", "label": "新活动价", "visible": False, "width": 75},
        {"key": "group_purchase_price", "label": "集采价", "visible": False, "width": 75},
        {"key": "discount_rate", "label": "折扣率", "visible": True, "width": 70},
        {"key": "supply_status", "label": "供货状态", "visible": True, "width": 70},
        {"key": "barcode_69", "label": "69码", "visible": True, "width": 130},
        {"key": "solution", "label": "方案", "visible": True, "width": 60, "fixed": "right"},
    ],
    "solution_items": [
        {"key": "image", "label": "图片", "visible": True, "width": 55},
        {"key": "quick_model", "label": "快查型号", "visible": True, "width": 130},
        {"key": "product_model", "label": "型号", "visible": True, "width": 110},
        {"key": "product_name", "label": "产品名称", "visible": True, "width": 160},
        {"key": "brand", "label": "品牌", "visible": True, "width": 60},
        {"key": "category_level1", "label": "一级品类", "visible": True, "width": 70},
        {"key": "category_level2", "label": "二级品类", "visible": False, "width": 70},
        {"key": "category_level3", "label": "三级品类", "visible": False, "width": 70},
        {"key": "negotiation_price", "label": "备货商谈价", "visible": False, "width": 75},
        {"key": "price_update", "label": "报价更新", "visible": False, "width": 95},
        {"key": "last_purchase_price", "label": "上次进货价", "visible": False, "width": 75},
        {"key": "purchase_price", "label": "进货价", "visible": False, "width": 75},
        {"key": "retail_price", "label": "零售价", "visible": False, "width": 70},
        {"key": "new_event_price", "label": "新活动价", "visible": False, "width": 75},
        {"key": "group_purchase_price", "label": "集采价", "visible": False, "width": 75},
        {"key": "bid_price", "label": "投标价", "visible": False, "width": 75},
        {"key": "discount_rate", "label": "折扣率", "visible": True, "width": 60},
        {"key": "price", "label": "代发价", "visible": True, "width": 70},
        {"key": "shop_url", "label": "链接", "visible": False, "width": 150},
        {"key": "gross_weight", "label": "毛重(kg)", "visible": False, "width": 65},
        {"key": "box_spec", "label": "箱规", "visible": False, "width": 110},
        {"key": "cooperation_level", "label": "合作等级", "visible": False, "width": 65},
        {"key": "supply_status", "label": "供货状态", "visible": False, "width": 65},
        {"key": "specification", "label": "规格", "visible": False, "width": 110},
        {"key": "remark", "label": "备注", "visible": False, "width": 140},
        {"key": "shipping_fee", "label": "代发运费", "visible": False, "width": 75},
        {"key": "barcode_69", "label": "69码", "visible": False, "width": 130},
        {"key": "sales_volume", "label": "销量", "visible": False, "width": 55},
        {"key": "recommendation", "label": "推荐理由", "visible": False, "width": 130},
        {"key": "parameters", "label": "参数", "visible": False, "width": 100},
        {"key": "cert_3c", "label": "3C", "visible": False, "width": 65},
        {"key": "created_at", "label": "导入时间", "visible": False, "width": 150},
        {"key": "quantity", "label": "数量", "visible": True, "width": 60},
        {"key": "subtotal", "label": "小计", "visible": True, "width": 80},
    ],
}

# 所有可用列的完整定义（用于前端选择）
ALL_AVAILABLE_COLUMNS: Dict[str, List[Dict[str, Any]]] = {
    "product_db": [
        {"key": "index", "default_label": "序号", "default_width": 56},
        {"key": "quick_model", "default_label": "快查型号", "default_width": 160},
        {"key": "product_model", "default_label": "型号", "default_width": 130},
        {"key": "image", "default_label": "图片", "default_width": 65},
        {"key": "product_name", "default_label": "产品名称", "default_width": 160},
        {"key": "brand", "default_label": "品牌", "default_width": 70},
        {"key": "category_level1", "default_label": "一级品类", "default_width": 80},
        {"key": "category_level2", "default_label": "二级品类", "default_width": 80},
        {"key": "category_level3", "default_label": "三级品类", "default_width": 80},
        {"key": "negotiation_price", "default_label": "备货商谈价", "default_width": 80},
        {"key": "price_update", "default_label": "报价更新", "default_width": 95},
        {"key": "last_purchase_price", "default_label": "上次进货价", "default_width": 80},
        {"key": "purchase_price", "default_label": "进货价", "default_width": 80},
        {"key": "retail_price", "default_label": "零售价", "default_width": 80},
        {"key": "discount_rate", "default_label": "折扣率", "default_width": 70},
        {"key": "new_event_price", "default_label": "新活动价", "default_width": 80},
        {"key": "shop_url", "default_label": "链接", "default_width": 180},
        {"key": "bid_price", "default_label": "投标价", "default_width": 80},
        {"key": "group_purchase_price", "default_label": "集采价/项目", "default_width": 80},
        {"key": "price", "default_label": "代发价", "default_width": 80},
        {"key": "gross_weight", "default_label": "毛重(kg)", "default_width": 70},
        {"key": "box_spec", "default_label": "箱规", "default_width": 120},
        {"key": "cooperation_level", "default_label": "合作等级", "default_width": 70},
        {"key": "supply_status", "default_label": "供货状态", "default_width": 70},
        {"key": "specification", "default_label": "规格", "default_width": 130},
        {"key": "remark", "default_label": "备注", "default_width": 150},
        {"key": "shipping_fee", "default_label": "代发运费", "default_width": 80},
        {"key": "barcode_69", "default_label": "69码", "default_width": 150},
        {"key": "sales_volume", "default_label": "销量", "default_width": 60},
        {"key": "recommendation", "default_label": "推荐理由", "default_width": 150},
        {"key": "parameters", "default_label": "参数", "default_width": 100},
        {"key": "cert_3c", "default_label": "3C", "default_width": 70},
        {"key": "created_at", "default_label": "导入时间", "default_width": 160},
        {"key": "action", "default_label": "操作", "default_width": 120},
    ],
    "query_result": [
        {"key": "image", "default_label": "图片", "default_width": 55},
        {"key": "quick_model", "default_label": "快查型号", "default_width": 115},
        {"key": "product_name", "default_label": "产品名称", "default_width": 125},
        {"key": "product_model", "default_label": "型号", "default_width": 110},
        {"key": "brand", "default_label": "品牌", "default_width": 55},
        {"key": "category_level1", "default_label": "一级品类", "default_width": 75},
        {"key": "category_level2", "default_label": "二级品类", "default_width": 75},
        {"key": "category_level3", "default_label": "三级品类", "default_width": 75},
        {"key": "price_update", "default_label": "报价更新", "default_width": 95},
        {"key": "negotiation_price", "default_label": "备货商谈价", "default_width": 75},
        {"key": "price", "default_label": "代发价", "default_width": 75},
        {"key": "purchase_price", "default_label": "进货价", "default_width": 75},
        {"key": "retail_price", "default_label": "零售价", "default_width": 75},
        {"key": "new_event_price", "default_label": "新活动价", "default_width": 75},
        {"key": "group_purchase_price", "default_label": "集采价", "default_width": 75},
        {"key": "bid_price", "default_label": "投标价", "default_width": 75},
        {"key": "discount_rate", "default_label": "折扣率", "default_width": 65},
        {"key": "shop_url", "default_label": "链接", "default_width": 150},
        {"key": "barcode_69", "default_label": "69码", "default_width": 140},
        {"key": "specification", "default_label": "规格", "default_width": 110},
        {"key": "box_spec", "default_label": "箱规", "default_width": 110},
        {"key": "cooperation_level", "default_label": "合作等级", "default_width": 65},
        {"key": "supply_status", "default_label": "供货状态", "default_width": 65},
        {"key": "gross_weight", "default_label": "毛重(kg)", "default_width": 65},
        {"key": "shipping_fee", "default_label": "代发运费", "default_width": 75},
        {"key": "sales_volume", "default_label": "销量", "default_width": 55},
        {"key": "recommendation", "default_label": "推荐理由", "default_width": 130},
        {"key": "parameters", "default_label": "参数", "default_width": 100},
        {"key": "cert_3c", "default_label": "3C", "default_width": 65},
        {"key": "remark", "default_label": "备注", "default_width": 140},
        {"key": "solution", "default_label": "方案", "default_width": 70},
    ],
    "batch_query": [
        {"key": "image", "default_label": "图片", "default_width": 55},
        {"key": "quick_model", "default_label": "快查型号", "default_width": 130},
        {"key": "product_name", "default_label": "产品名称", "default_width": 140},
        {"key": "brand", "default_label": "品牌", "default_width": 55},
        {"key": "product_model", "default_label": "型号", "default_width": 110},
        {"key": "price_update", "default_label": "报价更新", "default_width": 95},
        {"key": "price", "default_label": "代发价", "default_width": 85},
        {"key": "purchase_price", "default_label": "进货价", "default_width": 80},
        {"key": "retail_price", "default_label": "零售价", "default_width": 80},
        {"key": "new_event_price", "default_label": "新活动价", "default_width": 75},
        {"key": "group_purchase_price", "default_label": "集采价", "default_width": 75},
        {"key": "discount_rate", "default_label": "折扣率", "default_width": 70},
        {"key": "supply_status", "default_label": "供货状态", "default_width": 70},
        {"key": "barcode_69", "default_label": "69码", "default_width": 130},
        {"key": "solution", "default_label": "方案", "default_width": 60},
    ],
    "solution_items": [
        {"key": "image", "default_label": "图片", "default_width": 55},
        {"key": "quick_model", "default_label": "快查型号", "default_width": 130},
        {"key": "product_model", "default_label": "型号", "default_width": 110},
        {"key": "product_name", "default_label": "产品名称", "default_width": 160},
        {"key": "brand", "default_label": "品牌", "default_width": 60},
        {"key": "category_level1", "default_label": "一级品类", "default_width": 70},
        {"key": "category_level2", "default_label": "二级品类", "default_width": 70},
        {"key": "category_level3", "default_label": "三级品类", "default_width": 70},
        {"key": "negotiation_price", "default_label": "备货商谈价", "default_width": 75},
        {"key": "price_update", "default_label": "报价更新", "default_width": 95},
        {"key": "last_purchase_price", "default_label": "上次进货价", "default_width": 75},
        {"key": "purchase_price", "default_label": "进货价", "default_width": 75},
        {"key": "retail_price", "default_label": "零售价", "default_width": 70},
        {"key": "new_event_price", "default_label": "新活动价", "default_width": 75},
        {"key": "group_purchase_price", "default_label": "集采价", "default_width": 75},
        {"key": "bid_price", "default_label": "投标价", "default_width": 75},
        {"key": "discount_rate", "default_label": "折扣率", "default_width": 60},
        {"key": "price", "default_label": "代发价", "default_width": 70},
        {"key": "shop_url", "default_label": "链接", "default_width": 150},
        {"key": "gross_weight", "default_label": "毛重(kg)", "default_width": 65},
        {"key": "box_spec", "default_label": "箱规", "default_width": 110},
        {"key": "cooperation_level", "default_label": "合作等级", "default_width": 65},
        {"key": "supply_status", "default_label": "供货状态", "default_width": 65},
        {"key": "specification", "default_label": "规格", "default_width": 110},
        {"key": "remark", "default_label": "备注", "default_width": 140},
        {"key": "shipping_fee", "default_label": "代发运费", "default_width": 75},
        {"key": "barcode_69", "default_label": "69码", "default_width": 130},
        {"key": "sales_volume", "default_label": "销量", "default_width": 55},
        {"key": "recommendation", "default_label": "推荐理由", "default_width": 130},
        {"key": "parameters", "default_label": "参数", "default_width": 100},
        {"key": "cert_3c", "default_label": "3C", "default_width": 65},
        {"key": "created_at", "default_label": "导入时间", "default_width": 150},
        {"key": "quantity", "default_label": "数量", "default_width": 60},
        {"key": "subtotal", "default_label": "小计", "default_width": 80},
    ],
}


async def get_column_display_config(
    db: AsyncSession,
    user_id: int,
    page_type: str,
) -> List[Dict[str, Any]]:
    """获取用户的列显示配置，若未配置则返回默认值。
    如果已保存的配置缺少默认配置中的某些列（例如后续新增的列），
    会自动将其追加到用户配置中，确保新列可配置。
    """
    defaults = DEFAULT_COLUMNS.get(page_type, [])
    result = await db.execute(
        select(ColumnDisplayConfig).where(
            ColumnDisplayConfig.user_id == user_id,
            ColumnDisplayConfig.page_type == page_type,
        )
    )
    config = result.scalar_one_or_none()
    if config:
        # 旧式 Column 声明导致 Pylance 将实例属性推断为 Column 类型（运行时为 str）
        saved = json.loads(config.config_json) if config.config_json else []  # type: ignore[arg-type, truthy-function]
    else:
        return list(defaults)  # 没有保存过配置，返回默认值

    # 合并：用保存的配置覆盖默认值，但默认中有而保存中没有的列要追加
    saved_keys = {c["key"] for c in saved}
    saved_map = {c["key"]: c for c in saved}
    merged = list(saved)  # 先保留所有已保存的列
    for default_col in defaults:
        if default_col["key"] not in saved_keys:
            merged.append(dict(default_col))  # 追加新列（深拷贝）
    return merged


async def save_column_display_config(
    db: AsyncSession,
    user_id: int,
    page_type: str,
    columns: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """保存用户的列显示配置"""
    result = await db.execute(
        select(ColumnDisplayConfig).where(
            ColumnDisplayConfig.user_id == user_id,
            ColumnDisplayConfig.page_type == page_type,
        )
    )
    config = result.scalar_one_or_none()
    if config:
        config.config_json = json.dumps(columns, ensure_ascii=False)  # type: ignore[assignment]
    else:
        config = ColumnDisplayConfig(
            user_id=user_id,
            page_type=page_type,
            config_json=json.dumps(columns, ensure_ascii=False),
        )
        db.add(config)
    await db.flush()
    return columns


def get_available_columns(page_type: str) -> List[Dict[str, Any]]:
    """获取指定页面类型的所有可用列"""
    return ALL_AVAILABLE_COLUMNS.get(page_type, [])
