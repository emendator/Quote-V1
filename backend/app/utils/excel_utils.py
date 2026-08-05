"""Excel 解析工具 —— 支持图片提取（浮动图片 + 行内图片 + Place-in-Cell 图片）"""
import io
import re
import base64
import logging
import zipfile
from typing import Tuple, List, Any, Dict, Optional
import pandas as pd
import openpyxl

logger = logging.getLogger("excel_utils")


# ---- 内部辅助：图片数据转 base64 ----

def _image_bytes_to_base64(raw_data: Any) -> str:
    """将图片原始字节转换为 base64 字符串（限制最大宽度 200px）"""
    try:
        from PIL import Image as PILImage
        pil_img = PILImage.open(io.BytesIO(raw_data))
        max_width = 200
        if pil_img.width > max_width:
            ratio = max_width / pil_img.width
            new_height = int(pil_img.height * ratio)
            pil_img = pil_img.resize((max_width, new_height), PILImage.Resampling.LANCZOS)
        buf = io.BytesIO()
        img_format = pil_img.format or "PNG"
        if img_format.upper() not in ("PNG", "JPEG", "GIF", "WEBP"):
            img_format = "PNG"
        pil_img.save(buf, format=img_format)
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        mime = f"image/{img_format.lower()}"
        return f"data:{mime};base64,{b64_str}"
    except Exception as e:
        logger.warning(f"图片转换失败: {e}")
        return ""


# ---- 方式1: 浮动图片 (openpyxl ws._images) ----

def _extract_floating_images(ws: Any) -> Dict[int, str]:
    """通过 openpyxl 的 ws._images 提取浮动图片，返回 {0-based行: base64}"""
    result: Dict[int, str] = {}
    for img in getattr(ws, "_images", []) or []:
        try:
            anchor = img.anchor
            row_idx = None
            if hasattr(anchor, "_from"):
                row_idx = anchor._from.row
            elif hasattr(anchor, "row"):
                row_idx = anchor.row
            if row_idx is None:
                continue

            # 获取原始字节
            raw_data = None
            if hasattr(img, "_data") and callable(img._data):
                raw_data = img._data()
            if not raw_data and hasattr(img, "ref") and img.ref is not None:
                raw_data = img.ref.read() if hasattr(img.ref, "read") else img.ref
            if not raw_data:
                continue

            b64 = _image_bytes_to_base64(raw_data)
            if b64:
                result[row_idx] = b64
        except Exception as e:
            logger.warning(f"浮动图片提取失败: {e}")
            continue
    return result


# ---- 方式2: 传统 Drawing 图片 (xl/drawings/drawing*.xml) ----

def _extract_drawing_images(file_path: str, sheet_idx: int) -> Dict[int, str]:
    """从 xl/drawings/ 中解析图片锚点，返回 {0-based行: base64}"""
    result: Dict[int, str] = {}
    try:
        from lxml import etree  # type: ignore[import-not-found]
    except ImportError:
        return result

    try:
        with zipfile.ZipFile(file_path, "r") as z:
            # 定位 sheet XML 得到 drawing 关系
            sheet_path = f"xl/worksheets/sheet{sheet_idx}.xml"
            if sheet_path not in z.namelist():
                return result

            sheet_xml = etree.fromstring(z.read(sheet_path))
            ns_s = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            ns_pkg = "http://schemas.openxmlformats.org/package/2006/relationships"

            for drawing_ref in sheet_xml.findall(f".//{{{ns_s}}}drawing"):
                rel_id = drawing_ref.get(f"{{{ns_r}}}id")
                if not rel_id:
                    continue

                # 解析 sheet 的 rels 找到 drawing 文件路径
                rels_path = f"xl/worksheets/_rels/sheet{sheet_idx}.xml.rels"
                if rels_path not in z.namelist():
                    continue
                rels_xml = etree.fromstring(z.read(rels_path))
                drawing_target = None
                for rel in rels_xml.findall(f"{{{ns_pkg}}}Relationship"):
                    if rel.get("Id") == rel_id:
                        drawing_target = rel.get("Target", "")
                        break
                if not drawing_target:
                    continue

                # 拼接 drawing 文件路径
                if drawing_target.startswith("../"):
                    drawing_path = drawing_target.replace("../", "xl/")
                else:
                    drawing_path = f"xl/worksheets/{drawing_target}"
                if drawing_path not in z.namelist():
                    drawing_path = f"xl/drawings/drawing{sheet_idx}.xml"
                if drawing_path not in z.namelist():
                    continue

                draw_xml = etree.fromstring(z.read(drawing_path))
                draw_ns_xdr = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
                draw_ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"

                for anchor_elem in draw_xml.findall(f".//{{{draw_ns_xdr}}}twoCellAnchor") + \
                                     draw_xml.findall(f".//{{{draw_ns_xdr}}}oneCellAnchor"):
                    row_elem = anchor_elem.find(f".//{{{draw_ns_xdr}}}row")
                    if row_elem is None or row_elem.text is None:
                        continue
                    drawing_row = int(row_elem.text)
                    blip = anchor_elem.find(f".//{{{draw_ns_a}}}blip")
                    if blip is None:
                        continue
                    img_rel_id = (blip.get(f"{{{ns_r}}}embed") or
                                  blip.get(f"{{{ns_r}}}link"))
                    if not img_rel_id or drawing_row in result:
                        continue

                    # 从 drawing 的 rels 中找到图片文件路径
                    draw_rels_path = drawing_path.replace("/drawings/", "/_rels/") + ".rels"
                    if draw_rels_path not in z.namelist():
                        continue
                    draw_rels_xml = etree.fromstring(z.read(draw_rels_path))
                    for img_rel in draw_rels_xml.findall(f"{{{ns_pkg}}}Relationship"):
                        if img_rel.get("Id") == img_rel_id:
                            img_target = img_rel.get("Target", "")
                            # 尝试多种路径
                            candidates = [
                                f"xl/media/{img_target}" if not img_target.startswith("/")
                                else img_target.lstrip("/"),
                                f"xl/medias/{img_target}",
                            ]
                            for c in candidates:
                                if c in z.namelist():
                                    raw = z.read(c)
                                    b64 = _image_bytes_to_base64(raw)
                                    if b64:
                                        result[drawing_row] = b64
                                    break
                            break
    except Exception as e:
        logger.warning(f"Drawing 图片提取失败: {e}")
    return result


# ---- 方式3: Place-in-Cell 图片 (Office 365 图片嵌入单元格) ----

def _extract_placeincell_images(file_path: str) -> Dict[int, str]:
    """
    提取 Excel 365 的 "Place in Cell" 图片。
    这种图片存储为 rich data (XLRICHVALUE / _localImage)，
    在 sheet XML 中 cell 带有 vm 属性指向 valueMetadata，
    再经过 rich value → rich value rel → media 文件路径 的链路。
    返回 {0-based行: base64}。
    """
    result: Dict[int, str] = {}
    try:
        from lxml import etree  # type: ignore[import-not-found]
    except ImportError:
        return result

    try:
        with zipfile.ZipFile(file_path, "r") as z:
            # ---- 读取 rich data 元数据 ----
            # 1. metadata.xml → valueMetadata
            if "xl/metadata.xml" not in z.namelist():
                return result
            md = etree.fromstring(z.read("xl/metadata.xml"))
            ns_s = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            ns_xlrd = "http://schemas.microsoft.com/office/spreadsheetml/2017/richdata"

            # valueMetadata: 每个 bk 下的 rc 的 v 属性就是 rich value 的索引
            value_metadata: List[int] = []  # list of rich value index
            for bk in md.findall(f".//{{{ns_s}}}valueMetadata/{{{ns_s}}}bk"):
                rc = bk.find(f"{{{ns_s}}}rc")
                if rc is not None and rc.get("v") is not None:
                    value_metadata.append(int(rc.get("v")))

            if not value_metadata:
                return result

            # 2. rdrichvalue.xml → rich values (每个 rv 的第一个 v 是 LocalImageIdentifier)
            if "xl/richData/rdrichvalue.xml" not in z.namelist():
                return result
            rd = etree.fromstring(z.read("xl/richData/rdrichvalue.xml"))
            ns_rd = "http://schemas.microsoft.com/office/spreadsheetml/2017/richdata"

            rich_value_image_ids: List[int] = []  # list of image identifier (0-based)
            for rv in rd.findall(f".//{{{ns_rd}}}rv"):
                first_v = rv.find(f"{{{ns_rd}}}v")
                if first_v is not None and first_v.text is not None:
                    rich_value_image_ids.append(int(first_v.text))

            if not rich_value_image_ids:
                return result

            # 3. richValueRel.xml → rel 列表 (按顺序对应 rich_value_image_ids)
            if "xl/richData/richValueRel.xml" not in z.namelist():
                return result
            rvr = etree.fromstring(z.read("xl/richData/richValueRel.xml"))
            ns_rvr = "http://schemas.microsoft.com/office/spreadsheetml/2022/richvaluerel"
            ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

            rel_ids: List[str] = []  # list of rId strings, index = LocalImageIdentifier
            for rel_elem in rvr.findall(f".//{{{ns_rvr}}}rel"):
                rid = rel_elem.get(f"{{{ns_r}}}id")
                if rid:
                    rel_ids.append(rid)

            if not rel_ids:
                return result

            # 4. richValueRel.xml.rels → rId → 图片文件路径
            # 注意: .rels 文件使用 package 命名空间，不同于 officeDocument
            rels_path = "xl/richData/_rels/richValueRel.xml.rels"
            if rels_path not in z.namelist():
                return result
            rels_xml = etree.fromstring(z.read(rels_path))
            ns_pkg = "http://schemas.openxmlformats.org/package/2006/relationships"

            rid_to_image: Dict[str, str] = {}
            for rel in rels_xml.findall(f"{{{ns_pkg}}}Relationship"):
                rid = rel.get("Id")
                target = rel.get("Target", "")
                # Target 是相对路径，如 "../media/image1.png"
                if target.startswith("../"):
                    target = target.replace("../", "xl/")
                rid_to_image[rid] = target

            # ---- 解析 sheet XML 获取每个 cell 的 vm 属性 ----
            # 找出所有 worksheets
            for idx in range(1, 20):  # 最多20个 sheet
                sheet_path = f"xl/worksheets/sheet{idx}.xml"
                if sheet_path not in z.namelist():
                    continue
                sheet_xml = etree.fromstring(z.read(sheet_path))

                for row in sheet_xml.findall(f".//{{{ns_s}}}sheetData/{{{ns_s}}}row"):
                    row_num = int(row.get("r", "0"))
                    if row_num == 0:
                        continue
                    for cell in row.findall(f"{{{ns_s}}}c"):
                        vm_str = cell.get("vm")
                        if vm_str is None:
                            continue
                        vm_idx = int(vm_str) - 1  # vm 是 1-based → 0-based
                        if vm_idx < 0 or vm_idx >= len(value_metadata):
                            continue

                        rv_idx = value_metadata[vm_idx]
                        if rv_idx < 0 or rv_idx >= len(rich_value_image_ids):
                            continue

                        img_id = rich_value_image_ids[rv_idx]
                        if img_id < 0 or img_id >= len(rel_ids):
                            continue

                        rid = rel_ids[img_id]
                        img_path = rid_to_image.get(rid)
                        if not img_path or img_path not in z.namelist():
                            continue

                        # 0-based row (sheet 行号 1-based → 0-based)
                        zero_based_row = row_num - 1
                        if zero_based_row in result:
                            continue  # 已提取过

                        raw = z.read(img_path)
                        b64 = _image_bytes_to_base64(raw)
                        if b64:
                            result[zero_based_row] = b64
                # 只处理第一个 sheet
                break
    except Exception as e:
        logger.warning(f"Place-in-Cell 图片提取失败: {e}")
    return result


# ---- 日期时间规范化：无时分秒不存储/显示 00:00:00 ----

# 匹配 "2026-01-01 00:00:00" / "2026-01-01T00:00" 等纯日期 + 零时刻 的形式
_DATETIME_ZERO_TIME_RE = re.compile(r"^(\d{4}[-/]\d{1,2}[-/]\d{1,2})(?:[ T]00:00(?::00)?(?:\.\d+)?)$")


def normalize_datetime_string(value: Any) -> Any:
    """规范化日期时间值：去掉无意义的 00:00 / 00:00:00 时分秒，仅保留日期部分。

    Excel 原生日期单元格（无时分秒）经 pandas(dtype=str) 读取后会变成
    '2026-01-01 00:00:00'，此函数将其还原为 '2026-01-01'；
    真正有时分秒的值（如 '2026-01-01 10:30:45'）保持不变。
    """
    if value is None:
        return value
    s = str(value).strip()
    m = _DATETIME_ZERO_TIME_RE.match(s)
    if m:
        return m.group(1)
    return value


def normalize_datetime_columns(df: "pd.DataFrame") -> "pd.DataFrame":
    """对 DataFrame 所有单元格做日期时间规范化（去掉 00:00:00 尾缀）"""
    for col in df.columns:
        df[col] = df[col].map(normalize_datetime_string)
    return df


# ---- 统一入口 ----

def _extract_images_from_excel(file_path: str) -> Dict[int, str]:
    """
    从 Excel 文件中提取图片，返回 {0-based行号: base64字符串} 的字典。
    综合三种图片存储方式：
      1. 浮动图片 (openpyxl ws._images)
      2. 传统 Drawing 图片 (xl/drawings/)
      3. Place-in-Cell 图片 (Office 365 rich data)
    支持 .xlsx 格式，不支持 .xls 和 .csv。
    """
    result: Dict[int, str] = {}
    if not file_path.lower().endswith(".xlsx"):
        return result

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        for ws in wb.worksheets:
            sheet_idx = list(wb.worksheets).index(ws) + 1

            # 方式1: 浮动图片
            floating = _extract_floating_images(ws)
            for row_idx, b64 in floating.items():
                if row_idx not in result:
                    result[row_idx] = b64

            # 方式2: Drawing 图片
            drawing = _extract_drawing_images(file_path, sheet_idx)
            for row_idx, b64 in drawing.items():
                if row_idx not in result:
                    result[row_idx] = b64

        wb.close()

        # 方式3: Place-in-Cell 图片（不需要 wb）
        pic = _extract_placeincell_images(file_path)
        for row_idx, b64 in pic.items():
            if row_idx not in result:
                result[row_idx] = b64

    except Exception as e:
        logger.warning(f"打开 Excel 提取图片失败: {e}")

    return result


def parse_excel(file_path: str) -> Tuple[List[str], "pd.DataFrame", int]:
    """解析 Excel/CSV 文件，返回 (列名列表, DataFrame, 总行数)。
    Excel 中的图片（浮动图片 + 行内图片）会被提取并作为 base64 编码存入 image 列。
    如果 Excel 中已有名为"图片"或"image"的列，优先使用该列数据；
    否则自动从 Excel 图形中提取图片绑定到对应行。
    """
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path, dtype=str)
        df = normalize_datetime_columns(df)
        return list(df.columns), df, len(df)

    # 先读取原始数据（保留所有列为字符串，方便后续列名映射）
    df = pd.read_excel(file_path, dtype=str)
    original_cols = [str(col).strip() for col in df.columns]
    df.columns = original_cols
    df = normalize_datetime_columns(df)

    # 检查是否已有图片列
    image_col_names = {"图片", "image", "img", "产品图片", "商品图片", "pic", "picture", "_excel_image"}
    existing_image_col = next((c for c in original_cols if c.lower() in image_col_names), None)

    # 提取图片（仅 .xlsx）
    image_map = _extract_images_from_excel(file_path)
    if image_map:
        if existing_image_col:
            # 已有图片列：确保为 object 类型（空列可能被 pandas 推断为 float64，写入 base64 会报类型错误）
            df[existing_image_col] = df[existing_image_col].astype(object)
            # 对于该列没有值的行填入提取的图片
            for row_idx, b64 in image_map.items():
                data_row = row_idx - 1 if row_idx >= 1 else row_idx
                if 0 <= data_row < len(df):
                    current_val = str(df.at[data_row, existing_image_col] or "")
                    if not current_val or current_val in ("", "nan", "None"):
                        df.at[data_row, existing_image_col] = b64
        else:
            # 没有图片列：创建 _excel_image 列（object 类型）
            df["_excel_image"] = pd.Series([None] * len(df), dtype=object)
            for row_idx, b64 in image_map.items():
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
    image_cols = {"图片", "image", "img", "产品图片", "商品图片", "pic", "picture", "_excel_image"}
    result = []
    for _, row in preview_df.iterrows():
        row_vals = []
        for col in df.columns:
            val = row[col]
            if col.lower() in image_cols and val and str(val).startswith("data:image"):
                row_vals.append("[图片]")
            else:
                row_vals.append(val)
        result.append(row_vals)
    return result


# ---- 导出：图片嵌入单元格（TwoCellAnchor 双单元格锚点）----

_EMU_PER_PX = 9525      # 1 像素 = 9525 EMU
_EMU_PER_PT = 12700     # 1 磅 = 12700 EMU


def _col_width_to_px(chars: float) -> float:
    """列宽（字符数）转像素（Excel 默认字体 Calibri 11 的近似换算：宽*7+5）"""
    return max(chars * 7 + 5, 10)


def _col_width_to_emu(chars: float) -> int:
    return int(_col_width_to_px(chars) * _EMU_PER_PX)


def _pt_to_emu(pt: float) -> int:
    return int(pt * _EMU_PER_PT)


def add_image_embedded_in_cell(
    ws: Any,
    row_idx: int,
    image_col: int,
    img_raw: str,
    col_width: float,
    row_height: float = 40,
    margin: float = 2,
) -> bool:
    """以 TwoCellAnchor（双单元格锚点）将图片嵌入单元格，替代浮动图片。

    与 OneCellAnchor（单点漂浮锚点：固定大小、漂在单元格上方）不同，
    TwoCellAnchor 的 from/to 两个标记都锚定在目标单元格上，通过偏移量
    圈出图片的实际大小，因此图片会随单元格移动/缩放，视觉即"嵌入单元格"。

    锚点数学（0-based 坐标系，一个单元格占据 row=行号-1 到 row=行号）：
      anchor_row = row_idx - 1                  # from 标记的 0-based 行（单元格顶部）
      为使图片严格落在单元格内且保持原尺寸（不拉伸），from/to 都放在同一单元格，
      通过偏移量圈出图片实际大小：
        col_off = (col_width_emu - sw_emu) // 2  # 水平居中
        row_off = (row_h_emu   - sh_emu) // 2    # 垂直居中
      from = (col, colOff=col_off,         row, rowOff=row_off)
      to   = (col, colOff=col_off+sw_emu,  row, rowOff=row_off+sh_emu)
      宽 = sw_emu，高 = sh_emu，且在单元格内居中。

    参数:
        ws: openpyxl Worksheet
        row_idx: 1-based 数据行号
        image_col: 图片所在列号（1-based）
        img_raw: data:image 开头的 base64 图片字符串
        col_width: 图片列列宽（字符单位，用于换算 EMU）
        row_height: 目标行高（磅），图片等比缩放至该行高内并垂直/水平居中
        margin: 行高上下留白（磅）

    返回:
        True 表示成功嵌入；False 表示无图或解析失败（调用方回退为占位文本）
    """
    if not img_raw or not img_raw.startswith("data:image"):
        return False
    try:
        import base64 as _b64
        from PIL import Image as PILImage
        from openpyxl.drawing.image import Image as XLImage
        from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, TwoCellAnchor

        b64_data = img_raw.split(",", 1)[1] if "," in img_raw else img_raw
        img_bytes = _b64.b64decode(b64_data)
        pil_img = PILImage.open(io.BytesIO(img_bytes))

        # 原图尺寸（EMU）
        ow_emu = pil_img.width * _EMU_PER_PX
        oh_emu = pil_img.height * _EMU_PER_PX

        # 单元格可用区域（EMU）：列宽上限 + 行高上限（扣除上下留白）
        col_w_emu = _col_width_to_emu(col_width)
        max_h_emu = max(int((row_height - 2 * margin) * _EMU_PER_PT), 1)

        # 等比缩放：先限高、再限宽，保证不超出单元格、不拉伸变形
        sw_emu, sh_emu = ow_emu, oh_emu
        if sh_emu > max_h_emu:
            ratio = max_h_emu / sh_emu
            sh_emu = max_h_emu
            sw_emu = int(ow_emu * ratio)
        if sw_emu > col_w_emu:
            ratio = col_w_emu / sw_emu
            sw_emu = col_w_emu
            sh_emu = int(sh_emu * ratio)

        # 单元格内居中偏移
        col_off = (col_w_emu - sw_emu) // 2
        row_off = (max_h_emu - sh_emu) // 2

        # 0-based 锚点（单元格顶部 / 左边界）
        anchor_row = row_idx - 1
        anchor_col = image_col - 1

        # 按缩放后的像素尺寸重新编码为 PNG
        img_w_px = max(round(sw_emu / _EMU_PER_PX), 1)
        img_h_px = max(round(sh_emu / _EMU_PER_PX), 1)
        pil_img_resized = pil_img.resize((img_w_px, img_h_px), PILImage.Resampling.LANCZOS)
        img_buf = io.BytesIO()
        pil_img_resized.save(img_buf, format="PNG")
        img_buf.seek(0)

        xl_img = XLImage(img_buf)
        from_marker = AnchorMarker(col=anchor_col, colOff=col_off, row=anchor_row, rowOff=row_off)
        to_marker = AnchorMarker(col=anchor_col, colOff=col_off + sw_emu,
                                 row=anchor_row, rowOff=row_off + sh_emu)
        ws.add_image(xl_img, TwoCellAnchor(_from=from_marker, to=to_marker))

        # 行高容纳图片
        ws.row_dimensions[row_idx].height = row_height
        return True
    except Exception as e:
        logger.warning(f"图片嵌入单元格失败(row={row_idx}): {e}")
        return False
