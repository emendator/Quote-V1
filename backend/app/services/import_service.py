"""数据导入业务逻辑"""
import uuid
import os
import traceback
import logging
from typing import List, Dict, Any
import pandas as pd
from sqlalchemy import text
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from app.database import sync_engine
from app.utils.excel_utils import parse_excel, get_preview

logger = logging.getLogger("import_service")


# ========== 列名别名映射表（支持模糊语义匹配）==========
COLUMN_ALIAS_MAP: Dict[str, List[str]] = {
    "quick_model": ["快查型号", "快查", "快查码", "快速查询型号", "quick_model", "quickmodel", "速查型号", "快捷型号"],
    "product_model": ["型号", "商品型号", "产品型号", "货号", "商品编码", "产品编码", "物料编码", "model", "product_code", "item_code", "产品货号"],
    "product_name": ["产品名称", "商品名称", "名称", "品名", "product_name", "name", "商品名", "货品名称"],
    "brand": ["品牌", "商标", "brand", "trademark", "品牌名", "品牌名称", "牌子"],
    "category_level1": ["一级品类", "大类", "一级分类", "品类一", "cat1", "category1", "category_level1", "主分类", "一级类别"],
    "category_level2": ["二级品类", "小类", "二级分类", "品类二", "cat2", "category2", "category_level2", "子分类", "二级类别"],
    "negotiation_price": ["备货商谈价", "商谈价", "备货价", "谈判价", "negotiation_price", "商议价", "协商价", "备货商谈价格"],
    "price_update": ["报价更新", "更新", "价格更新", "最新报价", "price_update", "报价变动", "价格变动"],
    "last_purchase_price": ["上次进货价", "上次进价", "上期进货价", "上回进货价", "last_purchase_price", "上回进价", "上次采购价"],
    "purchase_price": ["进货价", "进价", "采购价", "进货价格", "purchase_price", "buy_price", "成本价", "cost_price", "cost", "成本", "成本价格"],
    "retail_price": ["零售价", "零售价格", "retail_price", "retail", "门店价", "售卖价", "市场零售价"],
    "new_event_price": ["新活动价", "活动价", "促销价", "event_price", "new_event_price", "优惠价", "活动价格", "新品活动价"],
    "shop_url": ["链接", "店铺链接", "商品链接", "url", "shop_url", "store_url", "购买链接", "店铺地址"],
    "bid_price": ["投标价", "投标价格", "竞标价", "bid_price", "bid", "招标价", "投标报价"],
    "group_purchase_price": ["集采价", "集采价/项目", "项目价", "集采价格", "团购价", "group_purchase_price", "集采", "项目价格", "批量采购价"],
    "price": ["代发价", "报价", "价格", "单价", "售价", "销售价", "批发价", "price", "sale_price", "retail_price_old", "unit_price", "供货价", "代理价", "代发价格"],
    "gross_weight": ["毛重", "总重", "毛重量", "gross_weight", "gross", "带包装重量", "含包装重"],
    "box_spec": ["箱规", "箱规格", "装箱规格", "box_spec", "box", "装箱数", "每箱数量", "箱装规格", "包装箱规"],
    "cooperation_level": ["合作等级", "合作级别", "等级", "cooperation_level", "level", "合作程度", "合作评级", "协作等级"],
    "supply_status": ["供货状态", "供货情况", "供应状态", "supply_status", "status", "在售状态", "供货状况", "库存状态"],
    "specification": ["规格", "产品规格", "包装规格", "商品规格", "spec", "specification", "packing", "包装", "规格型号", "产品参数(旧)"],
    "remark": ["备注", "说明", "描述", "remark", "description", "note", "memo", "备注信息", "补充说明"],
    "shipping_fee": ["代发运费", "运费", "代发邮费", "shipping_fee", "shipping", "配送费", "邮寄费", "快递费", "代发快递费"],
    "barcode_69": ["69码", "条形码", "barcode", "商品条码", "条码", "EAN码", "EAN13", "ean", "bar_code", "barcode69", "code69", "69条码"],
    "sales_volume": ["销量", "销售量", "销售数量", "sales_volume", "sales", "volume", "出售量", "已售", "卖出数量"],
    "recommendation": ["推荐理由", "推荐", "推荐语", "recommendation", "recommend", "推荐说明", "主推理由", "荐推"],
    "parameters": ["参数", "商品参数", "技术参数", "parameters", "params", "规格参数", "详细参数", "性能参数"],
    "cert_3c": ["3C", "3C认证", "CCC认证", "cert_3c", "ccc", "3c证书", "CCC", "3C编号", "强制认证"],
    "image": ["图片", "产品图片", "商品图片", "image", "pic", "picture", "photo", "图像", "产品图", "主图"],
}

# 存储上传文件的临时数据（生产环境应使用 Redis 等）
_upload_cache: Dict[str, Dict[str, Any]] = {}

# 将 _upload_cache 注入清理服务，以便清理过期缓存
from app.services.cleanup_service import set_upload_cache_ref
set_upload_cache_ref(_upload_cache)


def auto_map_columns(columns: List[str]) -> Dict[str, str]:
    """自动匹配列名到数据库字段"""
    mapping = {}
    for col in columns:
        col_lower = col.lower().strip()
        # 精确匹配
        for db_field, aliases in COLUMN_ALIAS_MAP.items():
            if col in aliases or col_lower in [a.lower() for a in aliases]:
                mapping[col] = db_field
                break
        # 模糊匹配（包含关系）
        if col not in mapping:
            for db_field, aliases in COLUMN_ALIAS_MAP.items():
                for alias in aliases:
                    if alias.lower() in col_lower or col_lower in alias.lower():
                        mapping[col] = db_field
                        break
                if col in mapping:
                    break
    return mapping


def handle_upload(file_path: str, original_name: str) -> Dict[str, Any]:
    """处理上传文件：解析并缓存，同时清理上次上传的旧文件"""
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")

    # ---- 清理上次上传的所有缓存和文件 ----
    _clean_previous_uploads(file_path)

    columns, df, total_rows = parse_excel(file_path)
    suggested_mapping = auto_map_columns(columns)
    preview_rows = get_preview(df)

    file_id = str(uuid.uuid4())
    _upload_cache[file_id] = {
        "file_path": file_path,
        "df": df,
        "columns": columns,
    }

    return {
        "file_id": file_id,
        "file_name": original_name,
        "columns": columns,
        "preview_rows": preview_rows,
        "total_rows": total_rows,
        "suggested_mapping": suggested_mapping,
    }


def _clean_previous_uploads(current_file_path: str):
    """清理 uploads 目录中不属于当前缓存的上传临时文件"""
    # 收集缓存中仍在使用的文件路径（不要删它们）
    active_paths = {os.path.normcase(v.get("file_path", "")) for v in _upload_cache.values() if v.get("file_path")}
    active_paths.add(os.path.normcase(current_file_path))

    # 清理 uploads 目录中不属于任何活跃缓存的残留文件
    if UPLOAD_DIR.exists():
        for fname in os.listdir(str(UPLOAD_DIR)):
            fpath = str(UPLOAD_DIR / fname)
            if os.path.isfile(fpath) and os.path.normcase(fpath) not in active_paths:
                try:
                    os.remove(fpath)
                    logger.info(f"已清理残留上传文件: {fname}")
                except Exception as e:
                    logger.warning(f"清理残留文件失败 {fname}: {e}")


def execute_import(file_id: str, column_mapping: Dict[str, str], duplicate_strategy: str) -> Dict[str, Any]:
    """执行数据导入 —— 以快查型号为准去重"""
    if file_id not in _upload_cache:
        raise ValueError("文件已过期，请重新上传")

    cache = _upload_cache[file_id]
    df: pd.DataFrame = cache["df"].copy()

    # ---- 过滤无效映射（去掉映射为空/不导入的、重复映射到同一字段的） ----
    valid_mapping: Dict[str, str] = {}
    seen_fields: set = set()
    for excel_col, db_field in column_mapping.items():
        if not db_field or db_field.strip() == "":
            continue  # 跳过"不导入"
        if db_field in seen_fields:
            continue  # 跳过重复映射（保留第一个）
        if excel_col not in df.columns:
            continue
        valid_mapping[excel_col] = db_field
        seen_fields.add(db_field)

    if not valid_mapping:
        raise ValueError("没有有效的列映射，请至少映射「快查型号」和「型号」字段")

    # 重命名列
    df.rename(columns=valid_mapping, inplace=True)

    # 保留已知字段
    known_fields = list(COLUMN_ALIAS_MAP.keys())
    existing_fields = [f for f in known_fields if f in df.columns]
    if not existing_fields:
        raise ValueError("映射后没有匹配到任何数据库字段，请检查列映射配置")

    # ---- 处理从 Excel 提取的图片数据 ----
    if "_excel_image" in df.columns:
        # 将提取的图片数据合并到 image 字段
        if "image" not in existing_fields:
            existing_fields.append("image")
        for idx, row in df.iterrows():
            val = row.get("_excel_image")
            if val and str(val) != "nan" and str(val) != "None" and str(val).startswith("data:image"):
                # 如果用户也映射了图片列且有内容，不覆盖
                existing_img = row.get("image", "")
                if not existing_img or str(existing_img) in ("nan", "None", ""):
                    df.at[idx, "image"] = val
        # 移除临时列
        df.drop(columns=["_excel_image"], inplace=True, errors="ignore")
        # 确保 existing_fields 不包含 _excel_image
        existing_fields = [f for f in existing_fields if f != "_excel_image"]

    # 只保留已知字段的列（避免重复列名问题）
    existing_fields_in_df = [f for f in existing_fields if f in df.columns]
    if not existing_fields_in_df:
        raise ValueError("映射后没有匹配到任何数据库字段，请检查列映射配置")
    existing_fields = existing_fields_in_df
    df = df[existing_fields]

    # 确保没有重复列名（防御性检查）
    if len(df.columns) != len(set(df.columns)):
        dupes = [c for c in df.columns if list(df.columns).count(c) > 1]
        raise ValueError(f"检测到重复列名: {dupes}，请检查 Excel 中是否有同名列映射到了不同数据库字段")

    # 数值类型转换（无效值保留 NaN，不填充默认值）
    numeric_fields = [
        "negotiation_price", "last_purchase_price", "purchase_price",
        "retail_price", "new_event_price", "bid_price", "group_purchase_price",
        "price", "gross_weight", "shipping_fee",
    ]
    for nf in numeric_fields:
        if nf in df.columns:
            df[nf] = pd.to_numeric(df[nf], errors="coerce")

    int_fields = ["sales_volume"]
    for inf in int_fields:
        if inf in df.columns:
            df[inf] = pd.to_numeric(df[inf], errors="coerce")

    # 将 NaN 转为 None（写入数据库时变为 NULL）
    df = df.where(pd.notna(df), None)

    total_rows = len(df)
    success_rows = 0
    skip_rows = 0
    error_rows = 0
    errors = []

    with sync_engine.connect() as conn:
        for idx, row in df.iterrows():
            try:
                row_data = {f: (None if row[f] is None else row[f]) for f in existing_fields}

                # 确保快查型号有效（必填项，去重依据）
                quick_model = str(row_data.get("quick_model") or "").strip()
                if not quick_model:
                    error_rows += 1
                    errors.append({"row": int(idx) + 2, "reason": "快查型号为空"})
                    continue

                # 确保型号有效（必填项）
                product_model = str(row_data.get("product_model") or "").strip()
                if not product_model:
                    error_rows += 1
                    errors.append({"row": int(idx) + 2, "reason": "型号为空"})
                    continue

                # 69码若为空则填空白字符串（数据库 non-nullable）
                if row_data.get("barcode_69") is None:
                    row_data["barcode_69"] = ""

                # 其他字符字段若为 None 则转空白字符串，避免 NULL 冲突
                string_fields = ["product_name", "price_update", "shop_url", "box_spec",
                                 "cooperation_level", "supply_status", "specification",
                                 "remark", "recommendation", "parameters", "cert_3c", "image"]
                for sf in string_fields:
                    if sf in row_data and row_data[sf] is None:
                        row_data[sf] = ""

                # 确保型号有效（必填项）
                product_model = str(row_data.get("product_model") or "").strip()
                if not product_model:
                    error_rows += 1
                    errors.append({"row": int(idx) + 2, "reason": "型号为空"})
                    continue

                # 确保代发价(price)有效（必填项）
                try:
                    price_val = float(row_data.get("price", 0))
                except (ValueError, TypeError):
                    price_val = 0
                if price_val <= 0:
                    error_rows += 1
                    errors.append({"row": int(idx) + 2, "reason": "代发价为空或无效"})
                    continue
                row_data["price"] = price_val

                # 去重检查（以快查型号为准）
                existing = conn.execute(
                    text("SELECT id FROM products WHERE quick_model = :qm"),
                    {"qm": quick_model}
                ).fetchone()

                if existing:
                    if duplicate_strategy == "skip":
                        skip_rows += 1
                        errors.append({"row": int(idx) + 2, "reason": f"快查型号「{quick_model}」已存在，已跳过"})
                        continue
                    elif duplicate_strategy == "overwrite":
                        set_clause = ", ".join([f"{f}=:{f}" for f in existing_fields if f != "id"])
                        conn.execute(
                            text(f"""UPDATE products SET {set_clause},
                                    updated_at=CURRENT_TIMESTAMP WHERE id=:id"""),
                            {**row_data, "id": existing[0]}
                        )
                        success_rows += 1
                        errors.append({"row": int(idx) + 2, "reason": f"快查型号「{quick_model}」已存在，已覆盖更新"})
                        continue
                    elif duplicate_strategy == "error":
                        error_rows += 1
                        errors.append({"row": int(idx) + 2, "reason": f"快查型号「{quick_model}」已存在"})
                        continue

                # 插入新记录
                placeholders = ", ".join([f":{f}" for f in existing_fields])
                conn.execute(
                    text(f"INSERT INTO products ({', '.join(existing_fields)}) VALUES ({placeholders})"),
                    row_data
                )
                success_rows += 1

            except Exception as e:
                error_rows += 1
                errors.append({"row": int(idx) + 2, "reason": str(e)})

        conn.commit()

    # 清理缓存
    del _upload_cache[file_id]

    return {
        "total_rows": total_rows,
        "success_rows": success_rows,
        "skip_rows": skip_rows,
        "error_rows": error_rows,
        "errors": errors[:50],
    }

