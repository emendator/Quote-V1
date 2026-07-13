"""微信群消息解析器 —— 从复制粘贴的聊天文本中提取查询信息"""
import re
from typing import List, Dict, Any


class MessageParser:
    """微信群客户询价消息解析器"""

    # 69码模式：中国标准以69开头的13位数字
    BARCODE_PATTERN = re.compile(r"(?:69码|条码|barcode)?\s*(\d{11,13})")
    # 独立数字序列（可能是69码）
    BARCODE_PURE_PATTERN = re.compile(r"\b(69\d{11})\b")
    # 商品型号/SKU模式（搜索时映射到 product_model）
    SKU_PATTERN = re.compile(r"(?:SKU|sku|货号|型号)[是为]?\s*([A-Za-z]{2,}-?\d{3,})")
    # 价格区间 —— 必须包含"价格"或"价钱"等关键词，限制数字长度避免误匹配69码
    PRICE_RANGE_PATTERN = re.compile(r"(?:价格[在为]?|价钱[在为]?)\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块|块钱)?")
    # 规格关键词
    SPEC_PATTERN = re.compile(r"(?:规格[是为]?|包装[是为]?)\s*(.{1,30}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 排序意图
    SORT_ASC_PATTERN = re.compile(r"(从小到大|从低到高|升序|便宜.+贵)")
    SORT_DESC_PATTERN = re.compile(r"(从大到小|从高到低|降序|贵.+便宜)")
    # 全量查询
    ALL_PATTERN = re.compile(r"(所有|全部|列出|查看)\s*.{0,5}\s*(商品|产品|报价)")
    # 名称查询
    NAME_PATTERN = re.compile(r"(?:查|找|搜|帮我看看)\s*(.{2,30}?)(?:的|报价|价格|多少钱|$)")
    # 单位/规格简写查询（如"一箱的那种"）
    UNIT_QUERY_PATTERN = re.compile(r"(一箱|箱装|瓶装|袋装|盒装|罐装|桶装)")
    # 价格阈值查询
    PRICE_THRESHOLD_PATTERN = re.compile(r"(?:价格|价钱)?\s*(?:在|大于|小于|低于|高于|超过)?\s*(\d+\.?\d*)\s*(?:以上|以下|以内|左右|元|块)?")

    def parse(self, text: str) -> Dict[str, Any]:
        """解析消息，返回结构化的查询列表"""
        text = self._clean_text(text)

        queries: List[Dict[str, Any]] = []
        found_patterns = set()

        # 1. 提取价格区间
        price_matches = self.PRICE_RANGE_PATTERN.findall(text)
        for pm in price_matches:
            key = f"price_range_{pm[0]}_{pm[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "price_range",
                    "value": f"{pm[0]}-{pm[1]}",
                    "price_min": float(pm[0]),
                    "price_max": float(pm[1]),
                })

        # 2. 提取69码区间（如"69码在123456到567890"）
        barcode_range_match = re.search(r"69码[在为]?\s*(\d+)\s*[~\-–到至]\s*(\d+)", text)
        if barcode_range_match:
            key = f"barcode_range_{barcode_range_match.group(1)}_{barcode_range_match.group(2)}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "barcode_range",
                    "value": f"{barcode_range_match.group(1)}-{barcode_range_match.group(2)}",
                    "barcode_min": barcode_range_match.group(1),
                    "barcode_max": barcode_range_match.group(2),
                })

        # 3. 提取带"69码"前缀的精确条码
        barcode_explicit = re.findall(r"69码[是为]?\s*(\d{11,13})", text)
        for bc in barcode_explicit:
            key = f"exact_barcode_{bc}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "exact_barcode", "value": bc})

        # 4. 提取独立的13位69开头数字（可能是不带前缀的条码）
        pure_barcodes = self.BARCODE_PURE_PATTERN.findall(text)
        for bc in pure_barcodes:
            key = f"exact_barcode_{bc}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "exact_barcode", "value": bc})

        # 5. 提取SKU
        sku_matches = self.SKU_PATTERN.findall(text)
        for sku in sku_matches:
            key = f"exact_sku_{sku}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "exact_sku", "value": sku})

        # 6. 提取规格关键词
        spec_matches = self.SPEC_PATTERN.findall(text)
        for sp in spec_matches:
            sp = sp.strip()
            if sp and len(sp) >= 1:
                key = f"spec_keyword_{sp}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "spec_keyword", "value": sp})

        # 7. 单位查询（如"一箱的那种"）
        unit_matches = self.UNIT_QUERY_PATTERN.findall(text)
        for um in unit_matches:
            key = f"spec_keyword_{um}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "spec_keyword", "value": um})

        # 8. 排序意图
        if self.SORT_ASC_PATTERN.search(text):
            queries.append({"type": "sort_order", "value": "asc"})
        elif self.SORT_DESC_PATTERN.search(text):
            queries.append({"type": "sort_order", "value": "desc"})

        # 9. 全量查询
        if self.ALL_PATTERN.search(text):
            queries.append({"type": "all_products", "value": "all"})

        # 如果没有识别到任何查询，尝试名称搜索
        if not queries:
            name_matches = self.NAME_PATTERN.findall(text)
            for nm in name_matches:
                nm = nm.strip()
                if nm and len(nm) >= 1:
                    queries.append({"type": "name_search", "value": nm})

        # 提取无法识别的部分（用于提示用户）
        recognized_texts = set()
        for q in queries:
            if "value" in q:
                recognized_texts.add(q["value"])

        return {
            "queries": queries,
            "sort_order": "asc" if self.SORT_ASC_PATTERN.search(text) else ("desc" if self.SORT_DESC_PATTERN.search(text) else None),
        }

    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        # 移除常见的微信消息噪音
        text = re.sub(r"\[\w+\]", "", text)  # 表情符号 [微笑]
        text = re.sub(r"@\S+", "", text)     # @提及
        # 全角数字转半角
        text = text.translate(str.maketrans("０１２３４５６７８９．", "0123456789."))
        # 合并多余空白
        text = re.sub(r"\s+", " ", text).strip()
        return text


message_parser = MessageParser()
