"""微信群消息解析器 —— 从复制粘贴的聊天文本中提取查询信息"""
import re
from typing import List, Dict, Any


class MessageParser:
    """微信群客户询价消息解析器"""

    # 独立数字序列（可能是69码）
    BARCODE_PURE_PATTERN = re.compile(r"\b(69\d{11})\b")
    # 商品型号匹配
    MODEL_PATTERN = re.compile(r"(?:型号|货号|快查型号|快查)[是为]?\s*([A-Za-z0-9\-]{2,})")
    # 代发价/报价区间
    PRICE_RANGE_PATTERN = re.compile(r"(?:代发价|报价|价格|价钱)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块|块钱)?")
    # 进货价区间
    PURCHASE_PRICE_RANGE_PATTERN = re.compile(r"(?:进货价|进价|采购价|成本价|成本)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块)?")
    # 零售价区间
    RETAIL_PRICE_RANGE_PATTERN = re.compile(r"(?:零售价|零售价格|门店价)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块)?")
    # 投标价区间
    BID_PRICE_RANGE_PATTERN = re.compile(r"(?:投标价|竞标价|招标价)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块)?")
    # 集采价区间
    GROUP_PRICE_RANGE_PATTERN = re.compile(r"(?:集采价|集采|项目价|团购价)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块)?")
    # 新活动价区间
    EVENT_PRICE_RANGE_PATTERN = re.compile(r"(?:新活动价|活动价|促销价|优惠价)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块)?")
    # 备货商谈价区间
    NEGO_PRICE_RANGE_PATTERN = re.compile(r"(?:备货商谈价|商谈价|备货价|谈判价)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块)?")
    # 代发运费区间
    SHIPPING_FEE_RANGE_PATTERN = re.compile(r"(?:代发运费|运费|快递费|配送费)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:元|块)?")
    # 毛重区间
    WEIGHT_RANGE_PATTERN = re.compile(r"(?:毛重|重量)[在为]?\s*(\d{1,7}(?:\.\d{1,2})?)\s*[~\-–到至]\s*(\d{1,7}(?:\.\d{1,2})?)\s*(?:kg|公斤|千克)?")
    # 销量阈值
    SALES_PATTERN = re.compile(r"(?:销量|销售量)[在为]?\s*(?:大于|小于|不低于|不超过|少于|多于|>=|<=|>|<)?\s*(\d+)\s*(?:件|个|笔|单|以上|以下)?")
    # 折扣率区间（支持"50%到90%"或"50到90"等）
    DISCOUNT_RATE_PATTERN = re.compile(r"(?:折扣率|优惠度|折扣)[在为]?\s*(\d{1,3}(?:\.\d{1,2})?)\s*(?:%|折|百分比)?\s*[~\-–到至]\s*(\d{1,3}(?:\.\d{1,2})?)\s*(?:%|折|百分比)?")
    # 折扣率阈值
    DISCOUNT_RATE_THRESHOLD_PATTERN = re.compile(r"(?:折扣率|优惠度|折扣)[在为]?\s*(?:(大于|小于|低于|高于|超过|>=|<=|>|<|以上|以下)\s*(\d{1,3}(?:\.\d{1,2})?)\s*(?:%|折|百分比)?)")
    # 折扣率约数
    DISCOUNT_RATE_APPROX_PATTERN = re.compile(r"(?:折扣率|优惠度|折扣)[在为]?\s*(\d{1,3}(?:\.\d{1,2})?)\s*(?:%|折|百分比)?\s*(左右|上下)")
    # 规格关键词
    SPEC_PATTERN = re.compile(r"(?:规格[是为]?|包装[是为]?)\s*(.{1,30}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 品牌查询
    BRAND_PATTERN = re.compile(r"(?:品牌|牌子)[是为]?\s*(.{1,20}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 产品名称查询
    PRODUCT_NAME_PATTERN = re.compile(r"(?:产品名称|商品名称|品名|名称)[是为]?\s*(.{1,30}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 一级品类查询
    CATEGORY_LEVEL1_PATTERN = re.compile(r"(?:一级品类|大类|一级分类|主分类)[是为]?\s*(.{1,20}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 二级品类查询
    CATEGORY_LEVEL2_PATTERN = re.compile(r"(?:二级品类|小类|二级分类|子分类)[是为]?\s*(.{1,20}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 三级品类查询
    CATEGORY_LEVEL3_PATTERN = re.compile(r"(?:三级品类|三级分类|细分类|三级类别)[是为]?\s*(.{1,20}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 品类通用查询（一级+二级都用）
    CATEGORY_PATTERN = re.compile(r"(?:品类|分类|类别)[是为]?\s*(.{1,20}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 合作等级查询
    COOPERATION_LEVEL_PATTERN = re.compile(r"(?:合作等级|合作级别|等级)[是为]?\s*(.{1,20}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 供货状态查询
    SUPPLY_STATUS_PATTERN = re.compile(r"(?:供货状态|供应状态|在售状态)[是为]?\s*(.{1,20}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 箱规查询
    BOX_SPEC_PATTERN = re.compile(r"(?:箱规|箱规格|装箱规格)[是为]?\s*(.{1,20}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 3C查询
    CERT_3C_PATTERN = re.compile(r"(?:3C|3C认证|CCC)[是为]?\s*(.{1,30}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 推荐理由查询
    RECOMMENDATION_PATTERN = re.compile(r"(?:推荐理由|推荐)[是为]?\s*(.{1,30}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 报价更新查询
    PRICE_UPDATE_PATTERN = re.compile(r"(?:报价更新|价格更新)[是为]?\s*(.{1,30}?)(?:的|所有|商品|产品|报价|价格|，|。|$)")
    # 排序意图
    SORT_ASC_PATTERN = re.compile(r"(从小到大|从低到高|升序|便宜.+贵)")
    SORT_DESC_PATTERN = re.compile(r"(从大到小|从高到低|降序|贵.+便宜)")
    # 全量查询
    ALL_PATTERN = re.compile(r"(所有|全部|列出|查看)\s*.{0,5}\s*(商品|产品|报价)")
    # 通用名称/型号搜索
    GENERAL_SEARCH_PATTERN = re.compile(r"(?:查|找|搜|帮我看看)\s*(.{2,30}?)(?:的|报价|价格|多少钱|$)")
    # 单位/规格简写查询（如"一箱的那种"）
    UNIT_QUERY_PATTERN = re.compile(r"(一箱|箱装|瓶装|袋装|盒装|罐装|桶装)")
    # 价格阈值查询（支持"300以下"、"大于200"、"在100以上"等，适用于代发价/进货价/零售价等）
    PRICE_THRESHOLD_HEAD_PATTERN = re.compile(r"(?:代发价|报价|价格|价钱|进货价|进价|成本价|成本|零售价|投标价|集采价|活动价)[在为]?\s*(?:(大于|小于|低于|高于|超过|>=|<=|>|<)\s*(\d+\.?\d*)\s*(?:元|块)?)")
    PRICE_THRESHOLD_TAIL_PATTERN = re.compile(r"(?:代发价|报价|价格|价钱|进货价|进价|成本价|成本|零售价|投标价|集采价|活动价)[在为]?\s*(\d+\.?\d*)\s*(?:元|块)?\s*(以上|以下)")
    # 价格约数查询（支持"300左右"、"500元左右"等）
    PRICE_APPROX_PATTERN = re.compile(r"(?:代发价|报价|价格|价钱|进货价|进价|成本价|成本|零售价|投标价|集采价|活动价)[在为]?\s*(\d+\.?\d*)\s*(?:元|块)?\s*(左右|上下)")

    def parse(self, text: str) -> Dict[str, Any]:
        """解析消息，返回结构化的查询列表"""
        text = self._clean_text(text)

        queries: List[Dict[str, Any]] = []
        found_patterns = set()

        # 1. 提取代发价区间
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

        # 1.5 提取价格阈值（小于/大于/以上/以下）
        pt_head = self.PRICE_THRESHOLD_HEAD_PATTERN.search(text)
        pt_tail = self.PRICE_THRESHOLD_TAIL_PATTERN.search(text)
        pt_match = pt_head if pt_head else pt_tail
        if pt_match:
            matched_text = pt_match.group(0)
            is_purchase = any(kw in matched_text for kw in ["进货价", "进价", "成本价", "成本"])
            is_retail = any(kw in matched_text for kw in ["零售价"])
            is_bid = any(kw in matched_text for kw in ["投标价"])
            is_group = any(kw in matched_text for kw in ["集采价"])
            is_event = any(kw in matched_text for kw in ["活动价"])
            is_price = not (is_purchase or is_retail or is_bid or is_group or is_event)

            pt_val = 0.0
            operator_raw = ""

            if pt_head:
                operator_raw = (pt_head.group(1) or "").strip()
                pt_val = float(pt_head.group(2))
            elif pt_tail:
                operator_raw = (pt_tail.group(2) or "").strip()
                pt_val = float(pt_tail.group(1))

            is_upper = any(op in operator_raw for op in ["以上", "大于", "高于", "超过", ">"])
            is_lower = any(op in operator_raw for op in ["以下", "小于", "低于", "<"])

            if is_lower or is_upper:
                key = None
                q = None
                if is_lower and is_price:
                    key = f"price_threshold_{pt_val}_max"
                    q = {"type": "price_range", "price_min": 0, "price_max": pt_val}
                elif is_upper and is_price:
                    key = f"price_threshold_{pt_val}_min"
                    q = {"type": "price_range", "price_min": pt_val, "price_max": 999999}
                elif is_lower and is_purchase:
                    key = f"purchase_price_threshold_{pt_val}_max"
                    q = {"type": "purchase_price_range", "purchase_price_min": 0, "purchase_price_max": pt_val}
                elif is_upper and is_purchase:
                    key = f"purchase_price_threshold_{pt_val}_min"
                    q = {"type": "purchase_price_range", "purchase_price_min": pt_val, "purchase_price_max": 999999}
                elif is_lower and is_retail:
                    key = f"retail_price_threshold_{pt_val}_max"
                    q = {"type": "retail_price_range", "retail_price_min": 0, "retail_price_max": pt_val}
                elif is_upper and is_retail:
                    key = f"retail_price_threshold_{pt_val}_min"
                    q = {"type": "retail_price_range", "retail_price_min": pt_val, "retail_price_max": 999999}
                elif is_lower and is_bid:
                    key = f"bid_price_threshold_{pt_val}_max"
                    q = {"type": "bid_price_range", "bid_price_min": 0, "bid_price_max": pt_val}
                elif is_upper and is_bid:
                    key = f"bid_price_threshold_{pt_val}_min"
                    q = {"type": "bid_price_range", "bid_price_min": pt_val, "bid_price_max": 999999}
                elif is_lower and is_group:
                    key = f"group_price_threshold_{pt_val}_max"
                    q = {"type": "group_purchase_price_range", "group_purchase_price_min": 0, "group_purchase_price_max": pt_val}
                elif is_upper and is_group:
                    key = f"group_price_threshold_{pt_val}_min"
                    q = {"type": "group_purchase_price_range", "group_purchase_price_min": pt_val, "group_purchase_price_max": 999999}
                elif is_lower and is_event:
                    key = f"event_price_threshold_{pt_val}_max"
                    q = {"type": "new_event_price_range", "new_event_price_min": 0, "new_event_price_max": pt_val}
                elif is_upper and is_event:
                    key = f"event_price_threshold_{pt_val}_min"
                    q = {"type": "new_event_price_range", "new_event_price_min": pt_val, "new_event_price_max": 999999}

                if key and key not in found_patterns:
                    found_patterns.add(key)
                    queries.append(q)

        # 1.6 提取约数价格（"300左右" → ±15% 范围）
        pa_match = self.PRICE_APPROX_PATTERN.search(text)
        if pa_match:
            base_val = float(pa_match.group(1))
            margin = base_val * 0.15
            lo = round(base_val - margin, 2)
            hi = round(base_val + margin, 2)
            matched_text = pa_match.group(0)
            is_purchase = any(kw in matched_text for kw in ["进货价", "进价", "成本价", "成本"])
            is_retail = any(kw in matched_text for kw in ["零售价"])
            is_bid = any(kw in matched_text for kw in ["投标价"])
            is_group = any(kw in matched_text for kw in ["集采价"])
            is_event = any(kw in matched_text for kw in ["活动价"])
            if is_purchase:
                queries.append({"type": "purchase_price_range", "purchase_price_min": lo, "purchase_price_max": hi})
            elif is_retail:
                queries.append({"type": "retail_price_range", "retail_price_min": lo, "retail_price_max": hi})
            elif is_bid:
                queries.append({"type": "bid_price_range", "bid_price_min": lo, "bid_price_max": hi})
            elif is_group:
                queries.append({"type": "group_purchase_price_range", "group_purchase_price_min": lo, "group_purchase_price_max": hi})
            elif is_event:
                queries.append({"type": "new_event_price_range", "new_event_price_min": lo, "new_event_price_max": hi})
            else:
                queries.append({"type": "price_range", "price_min": lo, "price_max": hi})

        # 2. 提取进货价区间
        pp_matches = self.PURCHASE_PRICE_RANGE_PATTERN.findall(text)
        for pm in pp_matches:
            key = f"purchase_price_range_{pm[0]}_{pm[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "purchase_price_range",
                    "value": f"{pm[0]}-{pm[1]}",
                    "purchase_price_min": float(pm[0]),
                    "purchase_price_max": float(pm[1]),
                })

        # 2.5 零售价区间
        rp_matches = self.RETAIL_PRICE_RANGE_PATTERN.findall(text)
        for rm in rp_matches:
            key = f"retail_price_range_{rm[0]}_{rm[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "retail_price_range",
                    "value": f"{rm[0]}-{rm[1]}",
                    "retail_price_min": float(rm[0]),
                    "retail_price_max": float(rm[1]),
                })

        # 2.6 投标价区间
        bp_matches = self.BID_PRICE_RANGE_PATTERN.findall(text)
        for bm in bp_matches:
            key = f"bid_price_range_{bm[0]}_{bm[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "bid_price_range",
                    "value": f"{bm[0]}-{bm[1]}",
                    "bid_price_min": float(bm[0]),
                    "bid_price_max": float(bm[1]),
                })

        # 2.7 集采价区间
        gp_matches = self.GROUP_PRICE_RANGE_PATTERN.findall(text)
        for gm in gp_matches:
            key = f"group_purchase_price_range_{gm[0]}_{gm[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "group_purchase_price_range",
                    "value": f"{gm[0]}-{gm[1]}",
                    "group_purchase_price_min": float(gm[0]),
                    "group_purchase_price_max": float(gm[1]),
                })

        # 2.8 新活动价区间
        ep_matches = self.EVENT_PRICE_RANGE_PATTERN.findall(text)
        for em in ep_matches:
            key = f"new_event_price_range_{em[0]}_{em[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "new_event_price_range",
                    "value": f"{em[0]}-{em[1]}",
                    "new_event_price_min": float(em[0]),
                    "new_event_price_max": float(em[1]),
                })

        # 2.9 备货商谈价区间
        np_matches = self.NEGO_PRICE_RANGE_PATTERN.findall(text)
        for nm in np_matches:
            key = f"negotiation_price_range_{nm[0]}_{nm[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "negotiation_price_range",
                    "value": f"{nm[0]}-{nm[1]}",
                    "negotiation_price_min": float(nm[0]),
                    "negotiation_price_max": float(nm[1]),
                })

        # 2.10 代发运费区间
        sf_matches = self.SHIPPING_FEE_RANGE_PATTERN.findall(text)
        for sm in sf_matches:
            key = f"shipping_fee_range_{sm[0]}_{sm[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "shipping_fee_range",
                    "value": f"{sm[0]}-{sm[1]}",
                    "shipping_fee_min": float(sm[0]),
                    "shipping_fee_max": float(sm[1]),
                })

        # 2.11 毛重区间
        w_matches = self.WEIGHT_RANGE_PATTERN.findall(text)
        for wm in w_matches:
            key = f"gross_weight_range_{wm[0]}_{wm[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "gross_weight_range",
                    "value": f"{wm[0]}-{wm[1]}",
                    "gross_weight_min": float(wm[0]),
                    "gross_weight_max": float(wm[1]),
                })

        # 3. 提取折扣率区间
        dr_matches = self.DISCOUNT_RATE_PATTERN.findall(text)
        for dr in dr_matches:
            key = f"discount_rate_{dr[0]}_{dr[1]}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "discount_rate_range",
                    "value": f"{dr[0]}%-{dr[1]}%",
                    "discount_rate_min": float(dr[0]),
                    "discount_rate_max": float(dr[1]),
                })

        # 3.1 提取折扣率阈值
        drt_match = self.DISCOUNT_RATE_THRESHOLD_PATTERN.search(text)
        if drt_match:
            operator_raw = (drt_match.group(1) or "").strip()
            drt_val = float(drt_match.group(2))
            if operator_raw:
                if any(op in operator_raw for op in ["以下", "小于", "低于", "<", "<="]):
                    key = f"discount_rate_threshold_{drt_val}_max"
                    if key not in found_patterns:
                        found_patterns.add(key)
                        queries.append({
                            "type": "discount_rate_range",
                            "value": f"0%-{drt_val}%",
                            "discount_rate_min": 0,
                            "discount_rate_max": drt_val,
                        })
                elif any(op in operator_raw for op in ["以上", "大于", "高于", "超过", ">", ">="]):
                    key = f"discount_rate_threshold_{drt_val}_min"
                    if key not in found_patterns:
                        found_patterns.add(key)
                        queries.append({
                            "type": "discount_rate_range",
                            "value": f"{drt_val}%-100%",
                            "discount_rate_min": drt_val,
                            "discount_rate_max": 100,
                        })

        # 3.2 提取折扣率约数
        dra_match = self.DISCOUNT_RATE_APPROX_PATTERN.search(text)
        if dra_match:
            base_val = float(dra_match.group(1))
            margin = base_val * 0.15
            lo = round(base_val - margin, 2)
            hi = round(base_val + margin, 2)
            key = f"discount_rate_approx_{base_val}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({
                    "type": "discount_rate_range",
                    "value": f"{lo}%-{hi}%",
                    "discount_rate_min": lo,
                    "discount_rate_max": hi,
                })

        # 4. 提取69码区间
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

        # 5. 提取带"69码"前缀的精确条码
        barcode_explicit = re.findall(r"69码[是为]?\s*(\d{11,13})", text)
        for bc in barcode_explicit:
            key = f"exact_barcode_{bc}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "exact_barcode", "value": bc})

        # 6. 提取独立的13位69开头数字
        pure_barcodes = self.BARCODE_PURE_PATTERN.findall(text)
        for bc in pure_barcodes:
            key = f"exact_barcode_{bc}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "exact_barcode", "value": bc})

        # 7. 提取商品型号（含快查型号）
        model_matches = self.MODEL_PATTERN.findall(text)
        for m in model_matches:
            key = f"model_{m}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "model_search", "value": m})

        # 8. 提取品牌
        brand_matches = self.BRAND_PATTERN.findall(text)
        for b in brand_matches:
            b = b.strip()
            if b and len(b) >= 1:
                key = f"brand_{b}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "brand_search", "value": b})

        # 9. 提取产品名称
        pn_matches = self.PRODUCT_NAME_PATTERN.findall(text)
        for pn in pn_matches:
            pn = pn.strip()
            if pn and len(pn) >= 1:
                key = f"product_name_{pn}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "product_name_search", "value": pn})

        # 10. 提取一级品类
        cl1_matches = self.CATEGORY_LEVEL1_PATTERN.findall(text)
        for cl in cl1_matches:
            cl = cl.strip()
            if cl and len(cl) >= 1:
                key = f"category_level1_{cl}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "category_level1_search", "value": cl})

        # 11. 提取二级品类
        cl2_matches = self.CATEGORY_LEVEL2_PATTERN.findall(text)
        for cl in cl2_matches:
            cl = cl.strip()
            if cl and len(cl) >= 1:
                key = f"category_level2_{cl}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "category_level2_search", "value": cl})

        # 11.5 提取三级品类
        cl3_matches = self.CATEGORY_LEVEL3_PATTERN.findall(text)
        for cl in cl3_matches:
            cl = cl.strip()
            if cl and len(cl) >= 1:
                key = f"category_level3_{cl}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "category_level3_search", "value": cl})

        # 12. 提取品类（通用，同时搜一级+二级+三级）
        cat_matches = self.CATEGORY_PATTERN.findall(text)
        for c in cat_matches:
            c = c.strip()
            if c and len(c) >= 1:
                key = f"category_{c}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "category_search", "value": c})

        # 13. 提取合作等级
        coop_matches = self.COOPERATION_LEVEL_PATTERN.findall(text)
        for cl in coop_matches:
            cl = cl.strip()
            if cl and len(cl) >= 1:
                key = f"cooperation_level_{cl}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "cooperation_level_search", "value": cl})

        # 14. 提取供货状态
        ss_matches = self.SUPPLY_STATUS_PATTERN.findall(text)
        for ss in ss_matches:
            ss = ss.strip()
            if ss and len(ss) >= 1:
                key = f"supply_status_{ss}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "supply_status_search", "value": ss})

        # 15. 提取箱规
        bs_matches = self.BOX_SPEC_PATTERN.findall(text)
        for bs in bs_matches:
            bs = bs.strip()
            if bs and len(bs) >= 1:
                key = f"box_spec_{bs}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "box_spec_search", "value": bs})

        # 16. 提取3C
        c3c_matches = self.CERT_3C_PATTERN.findall(text)
        for c3 in c3c_matches:
            c3 = c3.strip()
            if c3 and len(c3) >= 1:
                key = f"cert_3c_{c3}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "cert_3c_search", "value": c3})

        # 17. 提取推荐理由
        rec_matches = self.RECOMMENDATION_PATTERN.findall(text)
        for rec in rec_matches:
            rec = rec.strip()
            if rec and len(rec) >= 1:
                key = f"recommendation_{rec}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "recommendation_search", "value": rec})

        # 18. 提取报价更新
        pu_matches = self.PRICE_UPDATE_PATTERN.findall(text)
        for pu in pu_matches:
            pu = pu.strip()
            if pu and len(pu) >= 1:
                key = f"price_update_{pu}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "price_update_search", "value": pu})

        # 19. 提取销量
        sales_matches = self.SALES_PATTERN.findall(text)
        for st in sales_matches:
            key = f"sales_{st}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "sales_volume_search", "value": int(st)})

        # 20. 提取规格关键词
        spec_matches = self.SPEC_PATTERN.findall(text)
        for sp in spec_matches:
            sp = sp.strip()
            if sp and len(sp) >= 1:
                key = f"spec_keyword_{sp}"
                if key not in found_patterns:
                    found_patterns.add(key)
                    queries.append({"type": "spec_keyword", "value": sp})

        # 21. 单位查询（如"一箱的那种"）
        unit_matches = self.UNIT_QUERY_PATTERN.findall(text)
        for um in unit_matches:
            key = f"spec_keyword_{um}"
            if key not in found_patterns:
                found_patterns.add(key)
                queries.append({"type": "spec_keyword", "value": um})

        # 22. 排序意图
        if self.SORT_ASC_PATTERN.search(text):
            queries.append({"type": "sort_order", "value": "asc"})
        elif self.SORT_DESC_PATTERN.search(text):
            queries.append({"type": "sort_order", "value": "desc"})

        # 23. 全量查询
        if self.ALL_PATTERN.search(text):
            queries.append({"type": "all_products", "value": "all"})

        # 如果没有识别到任何查询，尝试通用模糊搜索
        if not queries:
            gen_matches = self.GENERAL_SEARCH_PATTERN.findall(text)
            for nm in gen_matches:
                nm = nm.strip()
                if nm and len(nm) >= 1:
                    queries.append({"type": "fuzzy_search", "value": nm})
            if not queries and len(text) >= 2:
                queries.append({"type": "fuzzy_search", "value": text})

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
        text = re.sub(r"\[\w+\]", "", text)
        text = re.sub(r"@\S+", "", text)
        text = text.translate(str.maketrans("０１２３４５６７８９．", "0123456789."))
        text = re.sub(r"\s+", " ", text).strip()
        return text


message_parser = MessageParser()
