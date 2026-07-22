"""智能方案服务 —— 客户需求分析、商品筛选、方案管理、DOCX 导出"""
import io
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy import select, text, or_, and_
from app.database import sync_engine
from app.models import Product
from app.services.query_engine import query_engine
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL

logger = logging.getLogger("solution_service")

# DeepSeek 提示词：分析客户项目需求（基础模板，运行时动态拼接参考数据）
SOLUTION_SYSTEM_PROMPT = """你是一个智能报价系统的方案顾问。请从客户需求中提取结构化信息，以 JSON 格式返回。

数据库字段及别称（用户可能使用任意一种）：
品牌/牌子 → brand
品类/分类 → category_level1 / category_level2 / category_level3
代发价/报价/价格 → price
进货价/进价/成本价 → purchase_price
零售价 → retail_price
投标价 → bid_price  集采价 → group_purchase_price
新活动价 → new_event_price  备货商谈价 → negotiation_price
运费 → shipping_fee  毛重/重量 → gross_weight
折扣率 → discount_rate  销量 → sales_volume
供货状态 → supply_status  规格 → specification
快查型号 → quick_model  型号/货号 → product_model
产品名称 → product_name  69码 → barcode_69
箱规 → box_spec  合作等级 → cooperation_level
链接 → shop_url  备注 → remark

JSON 格式：
{{
  "brand": "品牌名",
  "category_level1": "一级品类",
  "category_level2": "二级品类",
  "category_level3": "三级品类",
  "price_min": 最低代发价, "price_max": 最高代发价,
  "purchase_price_min": 最低进价, "purchase_price_max": 最高进价,
  "retail_price_min": 最低零售价, "retail_price_max": 最高零售价,
  "negotiation_price_min": ..., "negotiation_price_max": ...,
  "bid_price_min": ..., "bid_price_max": ...,
  "group_purchase_price_min": ..., "group_purchase_price_max": ...,
  "new_event_price_min": ..., "new_event_price_max": ...,
  "shipping_fee_min": ..., "shipping_fee_max": ...,
  "gross_weight_min": ..., "gross_weight_max": ...,
  "discount_rate_min": ..., "discount_rate_max": ...,
  "sales_volume_min": 最低销量,
  "supply_status": "供货状态",
  "specification": "规格",
  "keywords": ["其他关键词"],
  "summary": "需求摘要"
}}

示例：
输入："进一批200元以下的飞利浦插线板"
输出：{"brand": "飞利浦", "category_level2": "插线板", "purchase_price_max": 200, "keywords": [], "summary": "进一批200元以下的飞利浦插线板"}

输入："需要20个华为充电宝50-100元"
输出：{"brand": "华为", "category_level2": "充电宝", "price_min": 50, "price_max": 100, "keywords": [], "summary": "华为充电宝50-100元"}

输入："找零售价300以内的飞利浦排插新款"
输出：{"brand": "飞利浦", "category_level2": "排插", "retail_price_max": 300, "keywords": ["新款"], "summary": "飞利浦排插零售价300以内"}

规则：
- 品牌和品类必须从下方的参考数据中精确匹配，不要编造
- "xx以下/以内" → _max；"xx以上/以上" → _min
- 无法识别的关键词放 keywords 数组
- 只返回 JSON，不要额外解释
"""


class SolutionService:
    """智能方案服务"""

    # ========== 规则引擎分析 ==========

    def _parse_by_rules(self, requirement: str) -> Dict[str, Any]:
        """通过规则引擎解析客户需求"""
        intent: Dict[str, Any] = {}
        text = requirement.strip()
        if not text:
            intent["summary"] = ""
            return intent

        # 品牌提取（支持 "品牌为飞利浦" 和 "飞利浦" 等常见表述）
        brand_match = re.search(r"(?:品牌|牌子)[是为]?\s*(.{1,20}?)(?:的|商品|产品|报价|价格|，|。|$)", text)
        if brand_match:
            intent["brand"] = brand_match.group(1).strip()
        else:
            # 检查常见品牌名称（中文品牌通常2-4字）
            known_brands = ["飞利浦", "华为", "小米", "苹果", "三星", "联想", "戴尔", "索尼", "松下", "美的",
                           "格力", "海尔", "海信", "TCL", "长虹", "创维", "康佳", "奥克斯", "苏泊尔", "九阳",
                           "公牛", "绿联", "倍思", "安克", "罗马仕", "品胜", "爱国者"]
            for brand in known_brands:
                if brand in text:
                    intent["brand"] = brand
                    break

        # 价格区间提取
        price_range = re.search(r"(?:价格|报价|价位|单价)[在为]?\s*(\d+\.?\d*)\s*[~\-–到至]\s*(\d+\.?\d*)\s*(?:元|块)?", text)
        if price_range:
            intent["price_min"] = float(price_range.group(1))
            intent["price_max"] = float(price_range.group(2))
        else:
            price_lt = re.search(r"(?:价格|报价|价位)[在为]?\s*(?:小于|低于|不超过|以下)\s*(\d+\.?\d*)", text)
            price_gt = re.search(r"(?:价格|报价|价位)[在为]?\s*(?:大于|高于|超过|以上)\s*(\d+\.?\d*)", text)
            if price_lt:
                intent["price_max"] = float(price_lt.group(1))
            elif price_gt:
                intent["price_min"] = float(price_gt.group(1))

        # 品类提取
        cat1_match = re.search(r"(?:一级品类|大类)[是为]?\s*(.{1,20}?)(?:的|商品|产品|，|。|$)", text)
        if cat1_match:
            intent["category_level1"] = cat1_match.group(1).strip()
        cat2_match = re.search(r"(?:二级品类|品类|类别|分类)[是为]?\s*(.{1,20}?)(?:的|商品|产品|，|。|$)", text)
        if cat2_match:
            intent["category_level2"] = cat2_match.group(1).strip()

        # 规格关键词
        spec_match = re.search(r"(?:规格|包装)[是为]?\s*(.{1,20}?)(?:的|商品|产品|，|。|$)", text)
        if spec_match:
            intent["specification"] = spec_match.group(1).strip()

        # 供货状态
        status_match = re.search(r"(?:供货|在售|状态)[是为]?\s*(.{1,10}?)(?:的|商品|产品|，|。|$)", text)
        if status_match:
            intent["supply_status"] = status_match.group(1).strip()

        # 检测输入是否为型号列表（每行/每段是一个型号模式，如 SPB4034W/93）
        model_lines = [l.strip() for l in re.split(r'[\n\r,，、\s]+', text) if l.strip()]
        model_pattern = r'^[A-Za-z0-9]+[A-Za-z0-9/\-_.]{2,}$'
        is_model_list = (
            len(model_lines) >= 2
            and all(re.match(model_pattern, ml) for ml in model_lines)
        )

        if is_model_list:
            # 完整保留型号，不分词、不删数字
            intent["model_numbers"] = model_lines
        else:
            # 提取关键词：去掉已识别的品牌名后，剩余的所有非停用词作为关键词搜索
            remaining = text
            for v in intent.values():
                if isinstance(v, str) and v:
                    remaining = remaining.replace(v, "")
            # 清理剩余文本中的标点、空格等
            remaining = re.sub(r'[，。、！？：；""\'\'（）【】《》\s\d.]+', " ", remaining).strip()
            keywords = [kw.strip() for kw in remaining.split() if kw.strip() and len(kw.strip()) >= 2]

            if keywords:
                intent["keywords"] = keywords
            # 如果没有任何结构化条件也没有关键词，把整个文本当作关键词搜索
            elif not any(k in intent for k in ["brand", "category_level1", "category_level2",
                                                "category_level3", "price_min", "price_max",
                                                "specification", "supply_status"]):
                # 按常见分隔符拆分文本
                parts = re.split(r"[\s,，、]+", text)
                intent["keywords"] = [p.strip() for p in parts if p.strip() and len(p.strip()) >= 1]

        intent["summary"] = text[:100] if len(text) > 100 else text
        return intent

    # ========== AI 分析 ==========

    def _get_reference_data(self) -> str:
        """从数据库采样参考数据，帮助 AI 理解实际存在的值"""
        try:
            with sync_engine.connect() as conn:
                # 品牌（全部数据供AI匹配）
                brand_rows = conn.execute(
                    text("SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL AND brand != '' ORDER BY brand LIMIT 200")
                ).fetchall()
                brands = [r[0] for r in brand_rows if r[0]]

                # 一级品类（全部数据供AI匹配）
                cat1_rows = conn.execute(
                    text("SELECT DISTINCT category_level1 FROM products WHERE category_level1 IS NOT NULL AND category_level1 != '' ORDER BY category_level1 LIMIT 200")
                ).fetchall()
                cat1_list = [r[0] for r in cat1_rows if r[0]]

                # 二级品类（全部数据供AI匹配）
                cat2_rows = conn.execute(
                    text("SELECT DISTINCT category_level2 FROM products WHERE category_level2 IS NOT NULL AND category_level2 != '' ORDER BY category_level2 LIMIT 200")
                ).fetchall()
                cat2_list = [r[0] for r in cat2_rows if r[0]]

                # 三级品类（全部数据供AI匹配）
                cat3_rows = conn.execute(
                    text("SELECT DISTINCT category_level3 FROM products WHERE category_level3 IS NOT NULL AND category_level3 != '' ORDER BY category_level3 LIMIT 200")
                ).fetchall()
                cat3_list = [r[0] for r in cat3_rows if r[0]]

                # 供货状态（示例1个）
                status_row = conn.execute(
                    text("SELECT DISTINCT supply_status FROM products WHERE supply_status IS NOT NULL AND supply_status != '' LIMIT 1")
                ).fetchone()
                status_val = status_row[0] if status_row else None

            lines = []
            lines.append("========== 参考数据（用于品牌/品类精确匹配） ==========")
            lines.append("请将用户口语化表达与下方实际值匹配：")
            lines.append("")
            if brands:
                lines.append(f"brand(品牌) -> {', '.join(brands)}")
            if cat1_list:
                lines.append(f"category_level1(一级品类) -> {', '.join(cat1_list)}")
            if cat2_list:
                lines.append(f"category_level2(二级品类) -> {', '.join(cat2_list)}")
            if cat3_list:
                lines.append(f"category_level3(三级品类) -> {', '.join(cat3_list)}")
            if status_val:
                lines.append(f"supply_status(供货状态) -> {status_val}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"获取参考数据失败: {e}")
            return ""

    async def _parse_by_ai(self, requirement: str, reference_data: str = "") -> Optional[Dict[str, Any]]:
        """通过 DeepSeek API 分析客户需求"""
        # 构建提示词：基础模板 + 参考数据
        system_content = SOLUTION_SYSTEM_PROMPT
        if reference_data:
            system_content = system_content + "\n\n" + reference_data

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": requirement},
            ],
            "temperature": 0.1,
            "max_tokens": 1024,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                return json.loads(content.strip())
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return None

    # ========== 商品筛选 ==========

    def _query_candidates(self, intent: Dict[str, Any], owner_id: Optional[int] = None) -> tuple:
        """根据分析结果从数据库筛选商品，支持多级回退，返回 (results, total, strategy_used)"""
        structured_conditions = []
        structured_params = {}
        keyword_conditions = []
        keyword_params = {}

        # 结构化条件
        if intent.get("brand"):
            structured_conditions.append("brand LIKE :brand")
            structured_params["brand"] = f"%{intent['brand']}%"

        if intent.get("category_level1"):
            structured_conditions.append("category_level1 LIKE :cat1")
            structured_params["cat1"] = f"%{intent['category_level1']}%"

        if intent.get("category_level2"):
            structured_conditions.append("category_level2 LIKE :cat2")
            structured_params["cat2"] = f"%{intent['category_level2']}%"

        if intent.get("category_level3"):
            structured_conditions.append("category_level3 LIKE :cat3")
            structured_params["cat3"] = f"%{intent['category_level3']}%"

        if intent.get("specification"):
            structured_conditions.append("specification LIKE :spec")
            structured_params["spec"] = f"%{intent['specification']}%"

        if intent.get("supply_status"):
            structured_conditions.append("supply_status LIKE :status")
            structured_params["status"] = f"%{intent['supply_status']}%"

        # --- 多价格/数值字段范围 ---
        price_field_map = {
            "price": "price",
            "purchase_price": "purchase_price",
            "retail_price": "retail_price",
            "negotiation_price": "negotiation_price",
            "bid_price": "bid_price",
            "group_purchase_price": "group_purchase_price",
            "new_event_price": "new_event_price",
            "shipping_fee": "shipping_fee",
            "gross_weight": "gross_weight",
        }
        for field, col in price_field_map.items():
            min_key = f"{field}_min"
            max_key = f"{field}_max"
            if intent.get(min_key) is not None:
                structured_conditions.append(f"{col} >= :{min_key}")
                structured_params[min_key] = intent[min_key]
            if intent.get(max_key) is not None:
                structured_conditions.append(f"{col} <= :{max_key}")
                structured_params[max_key] = intent[max_key]

        # discount_rate 是计算字段（price / retail_price * 100），没有独立列，需用表达式
        dr_min = intent.get("discount_rate_min")
        dr_max = intent.get("discount_rate_max")
        if dr_min is not None:
            structured_conditions.append("(price * 100.0 / NULLIF(retail_price, 0)) >= :dr_min")
            structured_params["dr_min"] = dr_min
        if dr_max is not None:
            structured_conditions.append("(price * 100.0 / NULLIF(retail_price, 0)) <= :dr_max")
            structured_params["dr_max"] = dr_max

        # 最低销量
        if intent.get("sales_volume_min") is not None:
            structured_conditions.append("sales_volume >= :sales_volume_min")
            structured_params["sales_volume_min"] = intent["sales_volume_min"]

        # 关键词条件（多个关键词之间用 OR，与结构化条件用 AND）
        keywords = intent.get("keywords", [])
        for i, kw in enumerate(keywords):
            pname = f"kw{i}"
            kw_cond = " OR ".join([
                f"product_name LIKE :{pname}",
                f"quick_model LIKE :{pname}",
                f"product_model LIKE :{pname}",
                f"specification LIKE :{pname}",
                f"brand LIKE :{pname}",
                f"remark LIKE :{pname}",
            ])
            keyword_conditions.append(f"({kw_cond})")
            keyword_params[pname] = f"%{kw}%"

        def _execute(structured, keywords, s_params, k_params, owner_id_val=None) -> tuple:
            """执行一次查询，返回 (results, count)（支持数据隔离）"""
            all_conditions = list(structured)
            # 数据隔离
            if owner_id_val is not None:
                all_conditions.append("owner_id = :owner_id")
                s_params["owner_id"] = owner_id_val
            # 多个关键词之间用 AND
            if keywords:
                all_conditions.extend(keywords)
            where_clause = " AND ".join(all_conditions) if all_conditions else "1=1"
            all_params = {**s_params, **k_params}
            sql = f"SELECT * FROM products WHERE {where_clause} ORDER BY price ASC LIMIT 200"
            with sync_engine.connect() as conn:
                rows = conn.execute(text(sql), all_params).fetchall()
                if not rows:
                    return [], 0
                # PRAGMA table_info 返回 (cid,name,type,notnull,dflt_value,pk)，name 是列名
                columns = [col[1] for col in conn.execute(text("PRAGMA table_info(products)")).fetchall()]
                results = [dict(zip(columns, row)) for row in rows]
            return results, len(results)

        # 策略0（优先）：型号列表 → 使用 OR 查询（匹配任一型号即可）
        model_numbers = intent.get("model_numbers", [])
        if model_numbers:
            model_conditions = []
            model_params = {}
            for i, mn in enumerate(model_numbers):
                pname = f"mn{i}"
                model_conditions.append(f"(quick_model LIKE :{pname} OR product_model LIKE :{pname})")
                model_params[pname] = f"%{mn}%"
            # 多个型号用 OR 连接
            mn_where = " OR ".join(model_conditions)
            def _execute_models(s_params, owner_id_val=None):
                all_cond = [f"({mn_where})"]
                if owner_id_val is not None:
                    all_cond.append("owner_id = :owner_id")
                    s_params["owner_id"] = owner_id_val
                where_clause = " AND ".join(all_cond)
                all_params = {**s_params, **model_params}
                sql = f"SELECT * FROM products WHERE {where_clause} ORDER BY price ASC"
                with sync_engine.connect() as conn:
                    rows = conn.execute(text(sql), all_params).fetchall()
                    if not rows:
                        return [], 0
                    columns = [col[1] for col in conn.execute(text("PRAGMA table_info(products)")).fetchall()]
                    results = [dict(zip(columns, row)) for row in rows]
                return results, len(results)
            results, total = _execute_models(structured_params, owner_id)
            return results, total, 0

        # 策略1：结构化条件 + 关键词（精确匹配）
        results, total = _execute(structured_conditions, keyword_conditions, structured_params, keyword_params, owner_id)
        if total > 0:
            return results, total, 1

        # 策略2：仅结构化条件（放宽关键词）
        if keyword_conditions:
            results, total = _execute(structured_conditions, [], structured_params, {}, owner_id)
            if total > 0:
                return results, total, 2

        # 策略3：仅关键词（放宽结构化条件）
        if keyword_conditions and structured_conditions:
            results, total = _execute([], keyword_conditions, {}, keyword_params, owner_id)
            if total > 0:
                return results, total, 3

        # 策略4：无条件，返回全部（仅当用户没有输入任何条件时才有意义）
        results, total = _execute([], [], {}, {}, owner_id)
        return results, total, 4
    # ========== 推荐产品查询 ==========

    def _get_recommended_products_by_intent(self, intent: Dict[str, Any], owner_id: int) -> list:
        """查询上级用户的推荐产品（基于邀请链溯源），按 intent 条件筛选"""
        recommended = []
        try:
            with sync_engine.connect() as conn:
                # 沿邀请链向上查找所有来源用户
                source_user_ids = []
                source_user_info = {}
                visited = set()
                next_user_id = owner_id

                while next_user_id and next_user_id not in visited:
                    visited.add(next_user_id)
                    invite_row = conn.execute(
                        text('SELECT created_by FROM invite_codes WHERE used_by = :uid AND is_used = 1 LIMIT 1'),
                        {'uid': next_user_id}
                    ).fetchone()
                    if not invite_row:
                        break
                    inviter_id = invite_row[0]
                    if inviter_id == next_user_id or inviter_id in visited:
                        break
                    user_row = conn.execute(
                        text('SELECT id, role, company_name FROM users WHERE id = :uid AND is_active = 1'),
                        {'uid': inviter_id}
                    ).fetchone()
                    if not user_row:
                        break
                    source_user_ids.append(inviter_id)
                    source_user_info[inviter_id] = {
                        'role': user_row[1] or '',
                        'company_name': user_row[2] or '',
                    }
                    next_user_id = inviter_id

                if not source_user_ids:
                    return []

                # 构建查询条件
                conditions = []
                params = {}

                if intent.get('brand'):
                    conditions.append('brand LIKE :brand')
                    params['brand'] = '%%' + intent['brand'] + '%%'
                if intent.get('category_level1'):
                    conditions.append('category_level1 LIKE :cat1')
                    params['cat1'] = '%%' + intent['category_level1'] + '%%'
                if intent.get('category_level2'):
                    conditions.append('category_level2 LIKE :cat2')
                    params['cat2'] = '%%' + intent['category_level2'] + '%%'
                if intent.get('category_level3'):
                    conditions.append('category_level3 LIKE :cat3')
                    params['cat3'] = '%%' + intent['category_level3'] + '%%'
                if intent.get('specification'):
                    conditions.append('specification LIKE :spec')
                    params['spec'] = '%%' + intent['specification'] + '%%'
                if intent.get('supply_status'):
                    conditions.append('supply_status LIKE :status')
                    params['status'] = '%%' + intent['supply_status'] + '%%'

                # 价格字段范围
                price_field_map = {
                    'price': 'price',
                    'purchase_price': 'purchase_price',
                    'retail_price': 'retail_price',
                    'negotiation_price': 'negotiation_price',
                    'bid_price': 'bid_price',
                    'group_purchase_price': 'group_purchase_price',
                    'new_event_price': 'new_event_price',
                    'shipping_fee': 'shipping_fee',
                    'gross_weight': 'gross_weight',
                }
                for field, col in price_field_map.items():
                    min_key = field + '_min'
                    max_key = field + '_max'
                    if intent.get(min_key) is not None:
                        conditions.append(col + ' >= :' + min_key)
                        params[min_key] = intent[min_key]
                    if intent.get(max_key) is not None:
                        conditions.append(col + ' <= :' + max_key)
                        params[max_key] = intent[max_key]

                # 型号列表（优先，用 OR）
                model_numbers = intent.get('model_numbers', [])
                if model_numbers:
                    model_clauses = []
                    for i, mn in enumerate(model_numbers):
                        pname = 'rmn' + str(i)
                        model_clauses.append('(quick_model LIKE :' + pname + ' OR product_model LIKE :' + pname + ')')
                        params[pname] = '%%' + mn + '%%'
                    if model_clauses:
                        conditions.append('(' + ' OR '.join(model_clauses) + ')')
                else:
                    # 关键词条件（用 AND）
                    keywords = intent.get('keywords', [])
                    kw_clauses = []
                    for i, kw in enumerate(keywords):
                        pname = 'kw' + str(i)
                        kw_parts = [
                            'product_name LIKE :' + pname,
                            'quick_model LIKE :' + pname,
                            'product_model LIKE :' + pname,
                            'specification LIKE :' + pname,
                            'brand LIKE :' + pname,
                        ]
                        kw_clauses.append('(' + ' OR '.join(kw_parts) + ')')
                        params[pname] = '%%' + kw + '%%'
                    if kw_clauses:
                        conditions.extend(kw_clauses)

                # 组装 WHERE
                all_cond = list(conditions)
                owner_placeholders = []
                for idx, uid in enumerate(source_user_ids):
                    pk = 'src_uid_' + str(idx)
                    owner_placeholders.append(':' + pk)
                    params[pk] = uid
                all_cond.append('owner_id IN (' + ', '.join(owner_placeholders) + ')')

                where_clause = ' AND '.join(all_cond) if all_cond else '1=1'
                # 按权限级别排序：高级别用户的产品在前，同级别按价格升序
                order_cases = ' '.join(
                    f"WHEN owner_id = {uid} THEN {i}"
                    for i, uid in enumerate(reversed(source_user_ids))
                )
                order_by = f"CASE {order_cases} ELSE 999 END, price ASC"
                sql = 'SELECT id, owner_id, quick_model, product_model, product_name, brand, category_level1, category_level2, specification, price, supply_status, image FROM products WHERE ' + where_clause + ' ORDER BY ' + order_by + ' LIMIT 200'

                rows = conn.execute(text(sql), params).fetchall()
                for row in rows:
                    owner_info = source_user_info.get(row[1], {})
                    recommended.append({
                        'id': row[0],
                        'owner_id': row[1],
                        'quick_model': row[2] or '',
                        'product_model': row[3] or '',
                        'product_name': row[4] or '',
                        'brand': row[5] or '',
                        'category_level1': row[6] or '',
                        'category_level2': row[7] or '',
                        'specification': row[8] or '',
                        'price': float(row[9]) if row[9] else 0,
                        'supply_status': row[10] or '',
                        'image': row[11] or '',
                        'source_company_name': owner_info.get('company_name', ''),
                        'source_role': owner_info.get('role', ''),
                    })
        except Exception as e:
            logger.warning('获取推荐产品失败: ' + str(e))
        return recommended

    # ========== 对外接口 ==========


    async def analyze(self, requirement: str, use_ai: bool = False, filters: dict = None, owner_id: Optional[int] = None) -> Dict[str, Any]:
        """分析需求并返回候选商品（数据隔离）"""
        intent = {}

        if use_ai:
            # 获取数据库参考数据，帮助 AI 理解实际存在的值
            reference_data = self._get_reference_data()
            ai_result = await self._parse_by_ai(requirement, reference_data)
            if ai_result:
                intent = ai_result
                ai_summary = ai_result.get("summary", "")
            else:
                # AI 失败，回退到规则引擎
                intent = self._parse_by_rules(requirement)
                ai_summary = ""
        else:
            intent = self._parse_by_rules(requirement)
            ai_summary = ""

        # 合并前端筛选器传入的条件（覆盖自动解析的）
        if filters:
            for key in ["brand", "category_level1", "category_level2", "category_level3",
                         "price_min", "price_max", "negotiation_price_min", "negotiation_price_max",
                         "purchase_price_min", "purchase_price_max",
                         "retail_price_min", "retail_price_max",
                         "discount_rate_min", "discount_rate_max",
                         "supply_status", "specification"]:
                if key in filters and filters[key] is not None and filters[key] != "":
                    intent[key] = filters[key]

        # 查询候选商品（带数据隔离）
        candidates_raw, total, strategy = self._query_candidates(intent, owner_id=owner_id)

        # 判断是否需要给出提示：策略4（全量返回）且用户有输入条件，说明无匹配
        has_user_intent = bool(intent.get("brand") or intent.get("category_level1") or
                               intent.get("category_level2") or intent.get("category_level3") or
                               intent.get("keywords") or intent.get("price_min") is not None or
                               intent.get("price_max") is not None)

        # 格式化为前端需要的结构
        candidates = []
        for p in candidates_raw:
            candidates.append({
                "id": p.get("id"),
                "quick_model": p.get("quick_model", ""),
                "product_model": p.get("product_model", ""),
                "product_name": p.get("product_name", ""),
                "brand": p.get("brand", ""),
                "category_level1": p.get("category_level1", ""),
                "category_level2": p.get("category_level2", ""),
                "specification": p.get("specification", ""),
                "price": p.get("price", 0),
                "supply_status": p.get("supply_status", ""),
                "image": p.get("image", "") or "",
            })
        # 查询推荐产品（低权限账号可看到上级账号的商品）
        recommended_count = 0
        if owner_id is not None:
            recommended_raw = self._get_recommended_products_by_intent(intent, owner_id)
            if recommended_raw:
                existing_ids = {c["id"] for c in candidates}
                for p in recommended_raw:
                    if p["id"] not in existing_ids:
                        candidates.append({
                            "id": p.get("id"),
                            "quick_model": p.get("quick_model", ""),
                            "product_model": p.get("product_model", ""),
                            "product_name": p.get("product_name", ""),
                            "brand": p.get("brand", ""),
                            "category_level1": p.get("category_level1", ""),
                            "category_level2": p.get("category_level2", ""),
                            "specification": p.get("specification", ""),
                            "price": p.get("price", 0),
                            "supply_status": p.get("supply_status", ""),
                            "image": p.get("image", "") or "",
                            "is_recommended": True,
                            "source_company_name": p.get("source_company_name", ""),
                            "source_role": p.get("source_role", ""),
                        })
                        recommended_count += 1


        if total > 0 and strategy < 4:
            part1 = f"共找到 {total} 个符合条件的商品"
            message = part1 + (f"，此外还有 {recommended_count} 个推荐产品" if recommended_count > 0 else "")
        elif total > 0 and strategy == 4 and has_user_intent:
            # 策略4回退：用户有输入但无精确匹配
            if recommended_count > 0:
                # 保留推荐产品，只清除不相关的自有商品
                candidates = [c for c in candidates if c.get("is_recommended")]
                total = 0
                message = f"未找到与需求匹配的个人商品，但有 {recommended_count} 个推荐产品供参考"
            else:
                candidates = []
                total = 0
                message = (
                    "未找到与需求匹配的商品。"
                    "建议尝试：\n"
                    "1. 使用更简单的关键词：只需输入品牌 + 品类，如「飞利浦 充电宝」\n"
                    "2. 或输入快查型号/69码进行精确查找\n"
                    "3. 或使用普通模式（关闭AI），用筛选条件组合查询"
                )
        elif total > 0 and strategy == 4:
            message = f"共找到 {total} 个商品" + (f"，此外还有 {recommended_count} 个推荐产品" if recommended_count > 0 else "")
        else:
            if recommended_count > 0:
                message = f"未找到匹配的个人商品，但有 {recommended_count} 个推荐产品供参考"
            else:
                message = (
                    "未找到匹配的商品。"
                    "建议尝试：\n"
                    "1. 简化输入：只需品牌 + 品类，如「飞利浦 排插」「华为 充电器」\n"
                    "2. 或使用筛选条件组合查询\n"
                    "3. 或输入快查型号/69码精确查找"
                )

        return {
            "parsed_intent": intent,
            "ai_interpretation": ai_summary,
            "candidates": candidates,
            "total_candidates": total + recommended_count,
            "message": message,
        }

    def save_plan(self, name: str, requirement: str, ai_enabled: bool, items: list, remark: str = "", owner_id: int = 0) -> Dict[str, Any]:
        """保存方案到数据库（绑定 owner_id）"""
        total_amount = 0.0
        now_str = datetime.now(timezone(timedelta(hours=8))).isoformat()

        with sync_engine.connect() as conn:
            # 插入方案主表（带 owner_id）
            result = conn.execute(
                text("""INSERT INTO solution_plans (name, requirement, ai_enabled, total_amount, status, remark, owner_id, created_at, updated_at)
                        VALUES (:name, :requirement, :ai_enabled, 0, 'draft', :remark, :owner_id, :now, :now)"""),
                {"name": name, "requirement": requirement, "ai_enabled": 1 if ai_enabled else 0, "remark": remark, "owner_id": owner_id, "now": now_str}
            )
            plan_id = result.lastrowid

            # 插入明细
            for item in items:
                product_id = item.get("product_id")
                quantity = int(item.get("quantity", 1))
                if quantity < 1:
                    quantity = 1

                # 从数据库查询商品信息
                row = conn.execute(
                    text("SELECT quick_model, product_model, product_name, brand, specification, price FROM products WHERE id=:id"),
                    {"id": product_id}
                ).fetchone()

                if not row:
                    continue

                price = float(row[5]) if row[5] else 0
                subtotal = round(price * quantity, 2)
                total_amount += subtotal

                conn.execute(
                    text("""INSERT INTO solution_items
                            (plan_id, product_id, quick_model, product_model, product_name, brand, specification, price, quantity, subtotal, created_at)
                            VALUES (:plan_id, :product_id, :qm, :pm, :pn, :brand, :spec, :price, :qty, :subtotal, :now)"""),
                    {
                        "plan_id": plan_id,
                        "product_id": product_id,
                        "qm": row[0] or "",
                        "pm": row[1] or "",
                        "pn": row[2] or "",
                        "brand": row[3] or "",
                        "spec": row[4] or "",
                        "price": price,
                        "qty": quantity,
                        "subtotal": subtotal,
                        "now": now_str,
                    }
                )

            # 更新方案总金额
            conn.execute(
                text("UPDATE solution_plans SET total_amount=:amount WHERE id=:id"),
                {"amount": round(total_amount, 2), "id": plan_id}
            )
            conn.commit()

        return {
            "plan_id": plan_id,
            "name": name,
            "total_amount": round(total_amount, 2),
            "items_count": len(items),
        }

    def list_plans(self, owner_id: int = 0) -> list:
        """获取当前用户的历史方案列表"""
        with sync_engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, name, requirement, total_amount, status, created_at FROM solution_plans WHERE owner_id=:owner_id ORDER BY created_at DESC"),
                {"owner_id": owner_id}
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "name": r[1] or "",
                    "requirement": (r[2] or "")[:100],
                    "total_amount": r[3] or 0,
                    "status": r[4] or "draft",
                    "created_at": (str(r[5])[:19].replace('T', ' ')) if r[5] else "",
                }
                for r in rows
            ]

    def get_plan_detail(self, plan_id: int) -> dict:
        """获取方案详情（含明细）"""
        with sync_engine.connect() as conn:
            plan = conn.execute(
                text("SELECT * FROM solution_plans WHERE id=:id"), {"id": plan_id}
            ).fetchone()
            if not plan:
                raise ValueError("方案不存在")
            plan_cols = [col[1] for col in conn.execute(text("PRAGMA table_info(solution_plans)")).fetchall()]
            plan_dict = dict(zip(plan_cols, plan))

            items = conn.execute(
                text("SELECT * FROM solution_items WHERE plan_id=:pid ORDER BY id"), {"pid": plan_id}
            ).fetchall()
            item_cols = [col[1] for col in conn.execute(text("PRAGMA table_info(solution_items)")).fetchall()]
            items_list = [dict(zip(item_cols, row)) for row in items]

        plan_dict["items"] = items_list
        return plan_dict

    def delete_plan(self, plan_id: int) -> bool:
        """删除方案及其明细"""
        with sync_engine.connect() as conn:
            conn.execute(text("DELETE FROM solution_items WHERE plan_id=:pid"), {"pid": plan_id})
            conn.execute(text("DELETE FROM solution_plans WHERE id=:id"), {"id": plan_id})
            conn.commit()
        return True

    def export_docx(self, plan_id: int) -> bytes:
        """导出方案为 DOCX 文档"""
        from docx import Document
        from docx.shared import Pt, Inches, Cm
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml.ns import qn

        doc = Document()

        # 设置默认字体
        style = doc.styles['Normal']
        font = style.font
        font.name = '宋体'
        font.size = Pt(10.5)
        style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

        # 查询方案信息
        with sync_engine.connect() as conn:
            plan = conn.execute(
                text("SELECT * FROM solution_plans WHERE id=:id"),
                {"id": plan_id}
            ).fetchone()
            if not plan:
                raise ValueError("方案不存在")

            plan_cols = [col[1] for col in conn.execute(text("PRAGMA table_info(solution_plans)")).fetchall()]
            plan_dict = dict(zip(plan_cols, plan))

            items = conn.execute(
                text("SELECT * FROM solution_items WHERE plan_id=:pid ORDER BY id"),
                {"pid": plan_id}
            ).fetchall()
            item_cols = [col[1] for col in conn.execute(text("PRAGMA table_info(solution_items)")).fetchall()]
            items_list = [dict(zip(item_cols, row)) for row in items]

        # ---- 构建文档 ----
        # 标题
        title = doc.add_heading('产品推荐方案', level=0)
        title.alignment = 1  # 居中

        # 方案名称
        plan_name = plan_dict.get("name") or f"方案_{plan_id}"
        doc.add_heading(plan_name, level=1)

        # 生成日期
        doc.add_paragraph(f"生成日期：{datetime.now().strftime('%Y年%m月%d日')}")

        # 需求概述
        doc.add_heading('一、需求概述', level=1)
        req_text = plan_dict.get("requirement") or "（无）"
        doc.add_paragraph(req_text)

        # 方案明细表
        doc.add_heading('二、方案明细', level=1)

        if items_list:
            table = doc.add_table(rows=1, cols=7)
            table.style = 'Table Grid'
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            # 表头
            header_cells = table.rows[0].cells
            headers = ['序号', '商品型号', '商品名称', '品牌', '单价(元)', '数量', '小计(元)']
            for i, h in enumerate(headers):
                header_cells[i].text = h
                for paragraph in header_cells[i].paragraphs:
                    for run in paragraph.runs:
                        run.bold = True

            # 数据行
            for idx, item in enumerate(items_list, 1):
                row_cells = table.add_row().cells
                row_cells[0].text = str(idx)
                row_cells[1].text = item.get("product_model", "")
                row_cells[2].text = item.get("product_name", "")
                row_cells[3].text = item.get("brand", "")
                row_cells[4].text = f"{item.get('price', 0):.2f}"
                row_cells[5].text = str(item.get("quantity", 1))
                row_cells[6].text = f"{item.get('subtotal', 0):.2f}"

            # 汇总行
            total_amount = plan_dict.get("total_amount", 0)
            total_qty = sum(item.get("quantity", 0) for item in items_list)
            row_cells = table.add_row().cells
            row_cells[0].text = ""
            row_cells[1].text = "合计"
            row_cells[2].text = ""
            row_cells[3].text = f"{len(items_list)} 种商品"
            row_cells[4].text = ""
            row_cells[5].text = str(total_qty)
            row_cells[6].text = f"{total_amount:.2f}"

        # 备注
        doc.add_heading('三、备注', level=1)
        remark = plan_dict.get("remark") or "（无）"
        doc.add_paragraph(remark)

        # 保存到内存
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.getvalue()


solution_service = SolutionService()
