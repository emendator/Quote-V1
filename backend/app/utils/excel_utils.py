"""Excel 解析工具 —— 支持图片提取"""
import io
import base64
import logging
from typing import Tuple, List, Any, Dict
import pandas as pd
import openpyxl

logger = logging.getLogger("excel_utils")


def _extract_images_from_excel(file_path: str) -> Dict[int, str]:
    """
    从 Excel 文件中提取浮动图片，返回 {0-based行号: base64字符串} 的字典。
    支持 .xlsx 格式（openpyxl），不支持 .xls 和 .csv。
    """
    result: Dict[int, str] = {}
    if not file_path.lower().endswith(".xlsx"):
        return result

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        # 导入 PIL（延迟导入，避免非图片场景下的依赖报错）
        from PIL import Image as PILImage

        for ws in wb.worksheets:
            for img in ws._images:
                try:
                    # 获取图片锚定的起始行（0-based）
                    anchor = img.anchor
                    row_idx = None
                    # TwoCellAnchor / OneCellAnchor
                    if hasattr(anchor, "_from"):
                        row_idx = anchor._from.row
                    elif hasattr(anchor, "row"):
                        row_idx = anchor.row

                    if row_idx is None:
                        continue

                    # 读取图片原始数据
                    img_data = img._data()
                    if not img_data:
                        continue

                    # 转换为 base64
                    pil_img = PILImage.open(io.BytesIO(img_data))
                    # 限制图片尺寸：最大宽度 200px，保持比例
                    max_width = 200
                    if pil_img.width > max_width:
                        ratio = max_width / pil_img.width
                        new_height = int(pil_img.height * ratio)
                        pil_img = pil_img.resize((max_width, new_height), PILImage.LANCZOS)

                    # 转换为 base64
                    buf = io.BytesIO()
                    img_format = pil_img.format or "PNG"
                    if img_format.upper() not in ("PNG", "JPEG", "GIF", "WEBP"):
                        img_format = "PNG"
                    pil_img.save(buf, format=img_format)
                    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                    mime = f"image/{img_format.lower()}"
                    result[row_idx] = f"data:{mime};base64,{b64_str}"

                except Exception as e:
                    logger.warning(f"提取图片失败: {e}")
                    continue

        wb.close()
    except Exception as e:
        logger.warning(f"打开 Excel 提取图片失败: {e}")

    return result


def parse_excel(file_path: str) -> Tuple[List[str], "pd.DataFrame", int]:
    """解析 Excel/CSV 文件，返回 (列名列表, DataFrame, 总行数)。
    Excel 中的浮动图片会被提取并作为 base64 编码存入 image 列（0-based 行号对应）。
    """
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path, dtype=str)
        return list(df.columns), df, len(df)

    # 读取数据
    df = pd.read_excel(file_path, dtype=str)
    df.columns = [str(col).strip() for col in df.columns]

    # 提取浮动图片（仅 .xlsx）
    image_map = _extract_images_from_excel(file_path)
    if image_map:
        # 将图片数据映射到对应行
        # openpyxl 行号是 0-based，pandas read_excel 默认 header=0（第0行为表头）
        # 因此 openpyxl 行号 N → DataFrame index N-1（跳过表头行）
        df["_excel_image"] = None
        for row_idx, b64 in image_map.items():
            # 图片在表头行（row 0）或之前，跳过
            data_row = row_idx - 1 if row_idx >= 1 else row_idx
            if 0 <= data_row < len(df):
                df.at[data_row, "_excel_image"] = b64
        logger.info(f"从 Excel 中提取了 {len(image_map)} 张图片")

    columns = list(df.columns)
    total_rows = len(df)
    return columns, df, total_rows


def get_preview(df: "pd.DataFrame", n: int = 10) -> List[List[Any]]:
    """获取前 N 行预览数据（图片列显示为 [图片] 占位符）"""
    preview_df = df.head(n).fillna("")
    # 对于预览，图片列只显示数量标记
    result = []
    for _, row in preview_df.iterrows():
        row_vals = []
        for col in df.columns:
            val = row[col]
            if col == "_excel_image" and val and str(val).startswith("data:image"):
                row_vals.append("[图片]")
            else:
                row_vals.append(val)
        result.append(row_vals)
    return result
