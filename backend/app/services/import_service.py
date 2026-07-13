"""数据导入业务逻辑"""
import uuid
import json
import os
import re
from typing import Tuple, List, Dict, Any
import pandas as pd
from sqlalchemy import text
from app.config import UPLOAD_DIR, IMAGES_DIR, ALLOWED_EXTENSIONS
from app.database import sync_engine
from app.utils.excel_utils import parse_excel, get_preview
from app.models import Product

# ========== 列名别名映射表 ==========
COLUMN_ALIAS_MAP: Dict[str, List[str]] = {
    "barcode_69": ["69码", "条形码", "barcode", "商品条码", "条码", "EAN码", "EAN13", "ean", "bar_code", "barcode69", "code69"],
    "product_model": ["商品型号", "产品型号", "型号", "货号", "商品编码", "产品编码", "物料编码", "model", "product_code", "item_code"],
    "brand": ["品牌", "商标", "brand", "trademark"],
    "product_image": ["商品图片", "图片", "图片链接", "图片URL", "img", "image", "product_image"],
    "category": ["类别", "分类", "商品分类", "产品分类", "品类", "category", "type", "class"],
    "specification": ["规格", "产品规格", "包装规格", "商品规格", "spec", "specification", "packing", "包装", "规格型号"],
    "cost_price": ["成本价", "进价", "进货价", "采购价", "成本", "cost", "cost_price", "purchase_price"],
    "jd_price": ["京东划线价", "京东价", "划线价", "京东价格", "jd_price", "market_price", "list_price"],
    "price": ["代发价", "报价", "价格", "单价", "售价", "销售价", "零售价", "批发价", "price", "sale_price", "retail_price", "unit_price"],
    "supplier": ["供应商", "供货商", "供货方", "supplier", "vendor"],
    "shop_url": ["店铺链接", "链接", "店铺地址", "商品链接", "url", "shop_url", "store_url"],
    "stock": ["库存", "库存量", "库存数量", "存货", "stock", "inventory", "qty"],
    "remark": ["备注", "说明", "描述", "remark", "description", "note", "memo"],
}

# 存储上传文件的临时数据（生产环境应使用 Redis 等）
_upload_cache: Dict[str, Dict[str, Any]] = {}


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
    """处理上传文件：解析并缓存"""
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")

    columns, df, total_rows = parse_excel(file_path)
    suggested_mapping = auto_map_columns(columns)
    preview_rows = get_preview(df)

    # 提取 Excel 中嵌入的图片（如果有）
    # openpyxl 的 _images 属性按插入顺序存储嵌入图片
    # anchor._from.row 指示图片所在的行号（1-based）
    embedded_images = _extract_embedded_images(file_path)

    file_id = str(uuid.uuid4())
    _upload_cache[file_id] = {
        "file_path": file_path,
        "df": df,
        "columns": columns,
        "embedded_images": embedded_images,  # {row_index: img_data}
    }

    return {
        "file_id": file_id,
        "file_name": original_name,
        "columns": columns,
        "preview_rows": preview_rows,
        "total_rows": total_rows,
        "suggested_mapping": suggested_mapping,
    }


def _extract_embedded_images(file_path: str) -> Dict[int, bytes]:
    """
    从 Excel 文件中提取嵌入的图片。
    返回: {行号(1-based): 图片二进制数据}
    """
    images_map = {}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        if hasattr(ws, '_images') and ws._images:
            for img in ws._images:
                try:
                    anchor = img.anchor
                    row = anchor._from.row  # 1-based行号
                    img_data = img._data()
                    if img_data and len(img_data) > 100:  # 过滤极小图片
                        # 用行号去重，保留第一张图片（通常每行只有一张）
                        if row not in images_map:
                            images_map[row] = img_data
                except Exception:
                    continue
        wb.close()
    except Exception:
        pass  # 非 Excel 或没有嵌入图片时静默跳过
    return images_map


def execute_import(file_id: str, column_mapping: Dict[str, str], duplicate_strategy: str) -> Dict[str, Any]:
    """执行数据导入"""
    if file_id not in _upload_cache:
        raise ValueError("文件已过期，请重新上传")

    cache = _upload_cache[file_id]
    df: pd.DataFrame = cache["df"].copy()
    embedded_images: Dict[int, bytes] = cache.get("embedded_images", {})

    # 找出 "商品图片" 在映射中的原始列名
    image_source_col = None
    for col, field in column_mapping.items():
        if field == "product_image":
            image_source_col = col
            break

    # 重命名列
    rename_map = {k: v for k, v in column_mapping.items() if k in df.columns}
    df.rename(columns=rename_map, inplace=True)

    # 保留已知字段
    known_fields = list(COLUMN_ALIAS_MAP.keys())
    existing_fields = [f for f in known_fields if f in df.columns]
    df = df[existing_fields]

    # 类型转换
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    if "cost_price" in df.columns:
        df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").fillna(0)
    if "jd_price" in df.columns:
        df["jd_price"] = pd.to_numeric(df["jd_price"], errors="coerce").fillna(0)
    if "stock" in df.columns:
        df["stock"] = pd.to_numeric(df["stock"], errors="coerce").fillna(0).astype(int)

    # 填充 NaN
    df = df.fillna("")
    for f in existing_fields:
        if f not in df.columns:
            df[f] = ""

    total_rows = len(df)
    success_rows = 0
    skip_rows = 0
    error_rows = 0
    errors = []

    with sync_engine.connect() as conn:
        for idx, row in df.iterrows():
            try:
                row_data = {f: row[f] for f in existing_fields}
                # 确保代发价(price)有效
                try:
                    row_data["price"] = float(row_data.get("price", 0))
                except (ValueError, TypeError):
                    row_data["price"] = 0
                if row_data["price"] <= 0:
                    error_rows += 1
                    errors.append({"row": int(idx) + 2, "reason": "代发价无效或为空"})
                    continue

                # 去重检查（按69码去重）
                barcode = str(row_data.get("barcode_69", "")).strip()
                existing = None
                if barcode:
                    existing = conn.execute(
                        text("SELECT id FROM products WHERE barcode_69 = :bc"),
                        {"bc": barcode}
                    ).fetchone()

                # 处理图片：如果该行有嵌入图片，保存到文件并设置 URL
                image_url = str(row_data.get("product_image", "")).strip()
                excel_row_num = int(idx) + 2  # Excel 行号（1-based 表头+data）
                if excel_row_num in embedded_images and not image_url:
                    img_data = embedded_images[excel_row_num]
                    ext = ".png"  # 默认图片格式
                    img_filename = f"{uuid.uuid4()}{ext}"
                    img_save_path = IMAGES_DIR / img_filename
                    with open(img_save_path, "wb") as img_f:
                        img_f.write(img_data)
                    image_url = f"/uploads/images/{img_filename}"
                    row_data["product_image"] = image_url

                if existing:
                    if duplicate_strategy == "skip":
                        skip_rows += 1
                        continue
                    elif duplicate_strategy == "overwrite":
                        update_fields = {k: v for k, v in row_data.items() if k in existing_fields}
                        update_fields["id"] = existing[0]
                        set_clause = ", ".join([f"{f}=:{f}" for f in update_fields if f != "id"])
                        conn.execute(
                            text(f"UPDATE products SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE id=:id"),
                            update_fields
                        )
                        success_rows += 1
                        continue
                    elif duplicate_strategy == "error":
                        error_rows += 1
                        errors.append({"row": int(idx) + 2, "reason": "商品已存在（69码重复）"})
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
        "errors": errors[:50],  # 最多返回前50条错误
    }
