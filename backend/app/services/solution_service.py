"""智能方案服务 —— 客户需求分析、商品筛选、方案管理、Excel 导出"""
import io
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from app.database import sync_engine
from app.services.api_key_service import call_deepseek_with_user_key
from app.services.combination_engine import is_any_category
from app.utils.excel_utils import add_image_embedded_in_cell, normalize_datetime_string

logger = logging.getLogger("solution_service")

# DeepSeek 提示词：分析产品组合需求，提取组合约束条件（v3.0，适配多块输入结构）
SOLUTION_SYSTEM_PROMPT = """你是一个智能报价系统的产品组合方案顾问。用户会提出产品组合需求（如礼盒搭配），请从需求中提取组合约束条件，以 JSON 格式返回。

约束字段说明（与系统的多块输入结构一致）：
- total_price: 目标总价（数字，如 500）
- total_price_op: 总价限制方式，取值为 "gt"(大于) / "lt"(小于) / "around"(左右)
- max_discount_rate: 总折扣率限制值（数字，如 70；无限制则为 null）
- max_discount_op: 总折扣率限制方式，取值为 "gt"(大于) / "lt"(小于) / "around"(左右)，无限制则为 null
- items: 数组，每个元素代表一个商品位置的约束，包含：
  - category: 三级品类（字符串，务必从参考数据 category_level3 中精确匹配，不要编造）
  - quantity: 数量（整数，默认 1）
  - price_op: 该商品价格限制方式 "gt"(大于) / "lt"(小于) / "around"(左右)，无限制则为 ""
  - price: 该商品价格限制值（数字；无限制则为 null）
  - discount_op: 该商品折扣率限制方式 "gt"(大于) / "lt"(小于) / "around"(左右)，无限制则为 ""
  - discount: 该商品折扣率限制值（数字，百分比；无限制则为 null）

JSON 格式：
{{
  "total_price": 目标总价,
  "total_price_op": "around",
  "max_discount_rate": 70,
  "max_discount_op": "lt",
  "items": [
    {{"category": "三级品类1", "quantity": 1, "price_op": "gt", "price": 300, "discount_op": "", "discount": null}},
    {{"category": "三级品类2", "quantity": 2, ...}}
  ],
  "summary": "需求摘要"
}}

示例1：
输入："我要一个价值500的礼盒，其中包含三个产品，整体的折扣率需要低于70%，产品分别是移动电源、自拍杆、数据线，其中移动电源价值不低于300，剩下两个随意"
输出：{{"total_price": 500, "total_price_op": "around", "max_discount_rate": 70, "max_discount_op": "lt", "items": [{{"category": "移动电源", "quantity": 1, "price_op": "gt", "price": 300}}, {{"category": "自拍杆", "quantity": 1}}, {{"category": "数据线", "quantity": 1}}], "summary": "价值500礼盒：移动电源(≥300)+自拍杆+数据线"}}

示例2：
输入："需要搭配一个500元以内的礼品包，放三个产品，要一个飞利浦的小家电价值200以上，一个华为的电子产品价值100以上，再来一个随意"
输出：{{"total_price": 500, "total_price_op": "lt", "max_discount_rate": null, "max_discount_op": null, "items": [{{"category": "小家电", "quantity": 1, "price_op": "gt", "price": 200}}, {{"category": "电子产品", "quantity": 1, "price_op": "gt", "price": 100}}, {{"category": "商品", "quantity": 1}}], "summary": "500元礼品包：小家电(≥200)+电子产品(≥100)+随意"}}

示例3：
输入："帮我找三个产品凑到300块，都要是日用品，其中一个不能低于100"
输出：{{"total_price": 300, "total_price_op": "around", "max_discount_rate": null, "max_discount_op": null, "items": [{{"category": "日用品", "quantity": 1}}, {{"category": "日用品", "quantity": 1}}, {{"category": "日用品", "quantity": 1, "price_op": "gt", "price": 100}}], "summary": "三个日用品凑300元"}}

规则：
- 数量识别："三个"=3、"两件"=2，写入对应 item 的 quantity；若商品总数大于 item 数，补足空 item
- "xx以下/以内/不超过/低于/最多" → price_op="lt"；"xx以上/不低于/至少/超过" → price_op="gt"；"xx左右/上下/大概/约" → price_op="around"
- 总价："总价不超过X" → total_price_op="lt"；"总价不低于X" → "gt"；"总价X左右/大约" → "around"
- 折扣率同理用 discount_op / discount（百分比数字）
- "随意/都可以/任意/任意商品" 表示该位置是"任意商品"槽位：category 填 ""（或 "任意商品"），且无价格/折扣约束（price_op=""，price=null）；不要把它当作真实三级品类
- 品类必须从参考数据 category_level3 列表中精确匹配（把用户口语化表达映射到最接近的三级品类）
- 如果需求没有明确总价，total_price 用 null；无折扣率则 max_discount_rate / max_discount_op 用 null
- 只返回 JSON，不要额外解释
"""


class SolutionService:
    """智能方案服务"""

    # ========== AI 分析 ==========

    def _get_reference_data(self, company_id: int = 0) -> str:
        """从数据库采样参考数据，帮助 AI 理解实际存在的值（仅在用户公司范围内）"""
        try:
            with sync_engine.connect() as conn:
                company_filter = " AND company_id=:company_id" if company_id else ""
                company_params = {"company_id": company_id} if company_id else {}

                # 品牌（当前公司数据供AI匹配）
                brand_rows = conn.execute(
                    text("SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL AND brand != ''" + company_filter + " ORDER BY brand LIMIT 200"),
                    company_params
                ).fetchall()
                brands = [r[0] for r in brand_rows if r[0]]

                # 一级品类
                cat1_rows = conn.execute(
                    text("SELECT DISTINCT category_level1 FROM products WHERE category_level1 IS NOT NULL AND category_level1 != ''" + company_filter + " ORDER BY category_level1 LIMIT 200"),
                    company_params
                ).fetchall()
                cat1_list = [r[0] for r in cat1_rows if r[0]]

                # 二级品类
                cat2_rows = conn.execute(
                    text("SELECT DISTINCT category_level2 FROM products WHERE category_level2 IS NOT NULL AND category_level2 != ''" + company_filter + " ORDER BY category_level2 LIMIT 200"),
                    company_params
                ).fetchall()
                cat2_list = [r[0] for r in cat2_rows if r[0]]

                # 三级品类
                cat3_rows = conn.execute(
                    text("SELECT DISTINCT category_level3 FROM products WHERE category_level3 IS NOT NULL AND category_level3 != ''" + company_filter + " ORDER BY category_level3 LIMIT 200"),
                    company_params
                ).fetchall()
                cat3_list = [r[0] for r in cat3_rows if r[0]]

                # 供货状态（示例1个）
                status_row = conn.execute(
                    text("SELECT DISTINCT supply_status FROM products WHERE supply_status IS NOT NULL AND supply_status != ''" + company_filter + " LIMIT 1"),
                    company_params
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

    async def _parse_by_ai(self, requirement: str, reference_data: str = "",
                           company_id: int = 0, user_id: int = 0) -> Tuple[Optional[Dict[str, Any]], int]:
        """通过 DeepSeek API 分析客户需求，返回 (结果, 消耗token数)"""
        # 构建提示词：基础模板 + 参考数据
        system_content = SOLUTION_SYSTEM_PROMPT
        if reference_data:
            system_content = system_content + "\n\n" + reference_data

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": requirement},
        ]

        # 优先使用 user_id 对应的 API Key，否则按公司名查找
        data, tokens_used = await call_deepseek_with_user_key(
            user_id=user_id,
            messages=messages,
            max_tokens=2048,
            temperature=0.1,
        )
        if not data:
            return None, 0

        try:
            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip()), tokens_used
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return None, tokens_used

    # ========== 规则引擎解析组合约束 ==========

    def _parse_combination_by_rules(self, requirement: str) -> Dict[str, Any]:
        """通过规则引擎解析产品组合需求（非AI模式），适配各种口语化表述"""
        constraints: Dict[str, Any] = {"items": []}
        text = requirement.strip()
        if not text:
            return constraints

        # ---- 总价 / 价格范围 ----
        # 匹配"价值500"、"总价500"、"预算500"、"500元以内/左右"、"不超过500"、"100以内"等
        total_patterns = [
            # "总价/价格/价值 300" 等
            r"(?:价值|总价|总共|合计|一共|预算|整体价格|总价格|价格)[约为]?\s*(\d+\.?\d*)\s*(?:元|块)?",
            # "X元以内/以下/左右/上下/不超过/不高于/以上/至少"
            r"(\d+\.?\d*)\s*元\s*(?:以内|以下|左右|上下|不超过|不高于|以上|至少)",
            # "X以内/以下/之内"（无"元"字，如"100以内的充电宝"）
            r"(\d+\.?\d*)\s*(?:元|块)?\s*(?:以内|以下|之内)",
            # "不超过/不高于/少于/低于/大概/大约/约 X元"
            r"(?:不超过|不高于|少于|低于|大概|大约|约)\s*(\d+\.?\d*)\s*(?:元|块)",
            # "再X左右/上下"、"共X左右"（没有"元"字）
            r"[再共约]\s*(\d+\.?\d*)\s*(?:元|块)?\s*(?:左右|上下)",
            # 纯"X左右/上下"（无前缀）
            r"(\d+\.?\d*)\s*(?:元|块)?\s*(?:左右|上下)",
        ]
        matched_phrases = []
        total_price_cap = None  # "X以内/以下" 表示严格上限（不应用容差）
        for pat in total_patterns:
            m = re.search(pat, text)
            if m:
                constraints["total_price"] = float(m.group(1))
                matched_phrases.append(m.group(0))
                # "以内/以下/之内/不超过/不高于" → 严格上限
                if any(k in m.group(0) for k in ["以内", "以下", "之内", "不超过", "不高于"]):
                    total_price_cap = float(m.group(1))
                break

        # ---- 商品数量 ----

        # ---- 商品数量 ----
        # 支持"3个"、"三个"、"三件"、"三种"等，包含上下文避免误匹配
        cn_num_map = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5}
        qty_patterns = [
            # 优先匹配"包含/共/一共/合计 X个产品"这种明确上下文
            r"(?:共|一共|合计|包含|含)\s*(\d+)\s*(?:个|种|件|样|款)\s*(?:产品|商品|东西|礼品|礼盒)",
            r"(?:共|一共|合计|包含|含)\s*(\d+)\s*(?:个|种|件|样|款)",
            # 中文数字：同样需要明确上下文
            r"(?:共|一共|合计|包含|含)\s*([一二两三四五])\s*(?:个|种|件|样|款)\s*(?:产品|商品)",
            r"(?:共|一共|合计|包含|含)\s*([一二两三四五])\s*(?:个|种|件|样|款)",
            # 简单"X个"
            r"(\d+)\s*(?:个|种|件|样|款)\s*(?:产品|商品|东西|礼品|礼盒)",
            r"(\d+)\s*(?:个|种|件|样|款)",
            # 中文数字（如"三个产品"、"三件"），无上下文也可识别
            r"([一二两三四五])\s*(?:个|种|件|样|款)\s*(?:产品|商品|东西|礼品|礼盒)",
            r"([一二两三四五])\s*(?:个|种|件|样|款)",
        ]
        for pattern in qty_patterns:
            qty_match = re.search(pattern, text)
            if qty_match:
                val = qty_match.group(1)
                # 支持中文数字映射，否则转整数
                if val in cn_num_map:
                    constraints["total_quantity"] = cn_num_map[val]
                else:
                    try:
                        constraints["total_quantity"] = int(val)
                    except ValueError:
                        continue  # 忽略无法解析的匹配
                break

        # 提取最高折扣率（放松中间字词匹配，用 .*? 替代 [约为]?）
        dr_match = re.search(r"(?:折扣率|折扣).*?(?:低于|小于|不超过|不高于)\s*(\d+\.?\d*)\s*%?", text)
        if not dr_match:
            dr_match = re.search(r"(?:折扣率|折扣)[约为]?\s*(\d+\.?\d*)\s*%?", text)
        if dr_match:
            constraints["max_discount_rate"] = float(dr_match.group(1))

        # ---- 提取品类列表 ----
        qty = constraints.get("total_quantity", 3)
        cats: List[str] = []

        # 优先用"产品分别是/分别是"（更精确），其次才是"包含/包括"
        cat_section = re.search(r"(?:产品分别是|分别是)\s*(.+)", text)
        if not cat_section:
            # 排除"其中包含"这种非品类列举的"包含"
            cat_section = re.search(r"(?:包括|包含)\s*(.+)", text)

        if cat_section:
            cat_text = cat_section.group(1)
            # 移除末尾的条件描述（"其中..."、"，"、"。"等），保留品类名
            cat_text = re.sub(r"[，。].*$", "", cat_text)  # 句号/逗号开头意味着条件开始
            cat_text = re.sub(r"其中.*$", "", cat_text)    # "其中..."也是条件描述
            cats = re.split(r"[、，,]", cat_text)
            cats = [c.strip() for c in cats if c.strip()]

        # 如果找到了品类，为每个品类创建槽位
        if cats:
            for i, cat in enumerate(cats):
                slot: Dict[str, Any] = {}
                # "任意/随意/都可以/商品"等表示"任意商品"，不写入品类
                if not is_any_category(cat):
                    slot["category"] = cat
                # 为该品类查找紧密关联的价格约束
                # 只匹配"品类名(价值)不低于/不超过XXX"这种紧邻的约束，不会误读到其他品类的条件
                price_min_m = re.search(
                    rf"{re.escape(cat)}\s*(?:价值)?\s*(?:不低于|至少|不少于|≥)\s*(\d+)",
                    text
                )
                price_max_m = re.search(
                    rf"{re.escape(cat)}\s*(?:价值)?\s*(?:不超过|不高于|≤)\s*(\d+)",
                    text
                )
                if price_min_m:
                    slot["price_min"] = float(price_min_m.group(1))
                if price_max_m:
                    slot["price_max"] = float(price_max_m.group(1))
                constraints["items"].append(slot)
            # 如果品类数少于总数量，补齐空位
            while len(constraints["items"]) < qty:
                constraints["items"].append({})
        else:
            # 没找到明确品类
            is_simple_search = constraints.get("total_quantity", 1) <= 1
            if is_simple_search:
                # 未指定数量或只要求1个 → 简单商品搜索，按 1 个商品处理
                constraints["total_quantity"] = 1
                constraints["items"] = [{}]
                # 简单搜索：把未被识别为价格/数量条件的剩余文本作为搜索关键词
                remaining = text
                for phrase in matched_phrases:
                    remaining = remaining.replace(phrase, "")
                for key in ["brand", "category_level1", "category_level2", "category_level3",
                            "specification", "supply_status"]:
                    val = constraints.get(key)
                    if isinstance(val, str) and val:
                        remaining = remaining.replace(val, "")
                remaining = re.sub(r"[，。、！？：；\"\"''（）【】《》\s\d.%]+", " ", remaining)
                remaining = re.sub(r"[的是了在要给我一个件个种款大概大约左右以内以下不超过不高于]+", " ", remaining)
                keywords = []
                for kw in remaining.split():
                    kw = kw.strip()
                    if kw and len(kw) >= 2:
                        keywords.append(kw)
                if keywords:
                    constraints["keywords"] = keywords
            else:
                # 用户明确指定了多个数量，创建对应空位
                for _ in range(qty):
                    constraints["items"].append({})

        # "X以内/以下/不超过" → 严格总价上限（不应用 ±容差）
        if total_price_cap is not None:
            constraints["price_max"] = total_price_cap
            # 简单搜索（单个商品）时，同时应用到该槽位价格上限
            if len(constraints["items"]) == 1 and constraints["items"][0].get("price_max") is None:
                constraints["items"][0]["price_max"] = total_price_cap

        constraints["summary"] = text[:100]
        return constraints

    # ========== 结构化输入（多块输入） ==========

    def _build_structured_constraints(self, total_price: Optional[float], slots: list,
                                      max_discount_rate: Optional[float] = None,
                                      total_price_op: str = "",
                                      total_discount_op: str = "") -> Dict[str, Any]:
        """从结构化输入（总价 + 总折扣率 + 商品信息块列表）构建组合约束

        每个商品信息块：{category: 三级品类, quantity: 数量, price_op/price: 价格限制,
        discount_op/discount: 折扣率限制}
        总价/总折扣率支持 大于(gt)/小于(lt)/左右(around) 操作符
        数量 N 会展开为 N 个槽位（每个槽位匹配该品类），从而组合出不同商品
        """
        items: List[Dict[str, Any]] = []
        slot_descs = []
        for slot in slots:
            qty = max(1, int(getattr(slot, "quantity", 1) or 1))
            cat = (getattr(slot, "category", "") or "").strip()
            # "任意/随意/都可以/商品" 等表示"任意商品"，不应作为真实品类查询
            if is_any_category(cat):
                cat = ""
            price_min = getattr(slot, "price_min", None)
            price_max = getattr(slot, "price_max", None)
            price_op = (getattr(slot, "price_op", "") or "").strip()
            price_val = getattr(slot, "price", None)
            discount_op = (getattr(slot, "discount_op", "") or "").strip()
            discount_val = getattr(slot, "discount", None)
            discount_min = None
            discount_max = None

            # 根据操作符将价格限制转换为价格范围
            if price_op and price_val is not None:
                price_val = float(price_val)
                if price_op == "gt":          # 大于
                    price_min = price_val
                    price_max = None
                elif price_op == "lt":        # 小于
                    price_max = price_val
                    price_min = None
                elif price_op == "around":    # 左右（±15%）
                    price_min = round(price_val * 0.85, 2)
                    price_max = round(price_val * 1.15, 2)

            # 折扣率限制 → 折扣率范围（折扣率 = price/retail_price*100）
            if discount_op and discount_val is not None:
                discount_val = float(discount_val)
                if discount_op == "gt":          # 大于
                    discount_min = discount_val
                elif discount_op == "lt":        # 小于
                    discount_max = discount_val
                elif discount_op == "around":    # 左右（±15%）
                    discount_min = round(discount_val * 0.85, 2)
                    discount_max = round(discount_val * 1.15, 2)

            for _ in range(qty):
                item: Dict[str, Any] = {}
                if cat:
                    # 三级品类（精确匹配，前端从三级品类列表选择）
                    item["category_level3"] = cat
                if price_min is not None:
                    item["price_min"] = price_min
                if price_max is not None:
                    item["price_max"] = price_max
                if discount_min is not None:
                    item["discount_min"] = discount_min
                if discount_max is not None:
                    item["discount_max"] = discount_max
                items.append(item)

            # 生成摘要
            price_txt = ""
            if price_val is not None and price_op:
                if price_op == "gt":
                    price_txt = f"（＞{price_val}元）"
                elif price_op == "lt":
                    price_txt = f"（＜{price_val}元）"
                elif price_op == "around":
                    price_txt = f"（{price_val}元左右）"
            discount_txt = ""
            if discount_val is not None and discount_op:
                if discount_op == "gt":
                    discount_txt = f"（折扣率＞{discount_val}%）"
                elif discount_op == "lt":
                    discount_txt = f"（折扣率＜{discount_val}%）"
                elif discount_op == "around":
                    discount_txt = f"（折扣率{discount_val}%左右）"
            slot_name = cat or "任意商品"
            slot_descs.append(f"{slot_name}×{qty}{price_txt}{discount_txt}")

        constraints: Dict[str, Any] = {
            "total_price": float(total_price) if total_price else 0,
            "items": items,
        }
        # 总价操作符 → 总价上下界（兼容旧客户端：无操作符时默认"小于"=预算上限）
        if total_price:
            tv = float(total_price)
            op = total_price_op or "lt"
            if op == "lt":          # 小于 → 预算上限
                constraints["price_min"] = 0.0
                constraints["price_max"] = tv
            elif op == "gt":        # 大于 → 总价下限
                constraints["price_min"] = tv
            elif op == "around":    # 左右（±15%）
                constraints["price_min"] = round(tv * 0.85, 2)
                constraints["price_max"] = round(tv * 1.15, 2)
        # 总折扣率操作符 → 整体折扣率范围（兼容旧客户端：默认"小于"=上限）
        if max_discount_rate is not None:
            dv = float(max_discount_rate)
            op = total_discount_op or "lt"
            # 记录折扣率目标值（供排序时让方案总折扣率尽量靠近用户输入）
            constraints["discount_target"] = dv
            if op == "lt":          # 小于
                constraints["max_discount_rate"] = dv
            elif op == "gt":        # 大于
                constraints["min_discount_rate"] = dv
            elif op == "around":    # 左右（±15%）
                constraints["min_discount_rate"] = round(dv * 0.85, 2)
                constraints["max_discount_rate"] = round(dv * 1.15, 2)

        summary_parts = []
        if total_price:
            tv = float(total_price)
            op = total_price_op or "lt"
            if op == "lt":
                summary_parts.append(f"总价≤{tv}元")
            elif op == "gt":
                summary_parts.append(f"总价≥{tv}元")
            elif op == "around":
                summary_parts.append(f"总价{tv}元左右")
        if max_discount_rate is not None:
            dv = float(max_discount_rate)
            op = total_discount_op or "lt"
            if op == "lt":
                summary_parts.append(f"总折扣率≤{dv}%")
            elif op == "gt":
                summary_parts.append(f"总折扣率≥{dv}%")
            elif op == "around":
                summary_parts.append(f"总折扣率{dv}%左右")
        summary_parts.extend(slot_descs)
        constraints["summary"] = "，".join(summary_parts)
        return constraints

    # ========== 对外接口 ==========

    # ---- AI 模式"一键应用"辅助：把诊断改写为可直接覆盖用户输入的需求文本 ----

    def _build_requirement_text(self, constraints: Dict[str, Any]) -> str:
        """从结构化约束生成一段自然语言需求文本（供 AI 模式一键应用覆盖输入用）"""
        parts: List[str] = []

        if constraints.get("price_min") is not None and constraints.get("price_max") is not None \
                and constraints["price_min"] == constraints["price_max"]:
            parts.append(f"总价{constraints['price_min']}元左右")
        elif constraints.get("price_max") is not None and constraints["price_max"] != float('inf'):
            parts.append(f"总价不超过{constraints['price_max']}元")
        elif constraints.get("price_min") is not None:
            parts.append(f"总价不低于{constraints['price_min']}元")

        if constraints.get("min_discount_rate") is not None:
            parts.append(f"总折扣率不低于{constraints['min_discount_rate']}%")
        if constraints.get("max_discount_rate") is not None and constraints["max_discount_rate"] < 100:
            parts.append(f"总折扣率不超过{constraints['max_discount_rate']}%")

        for i, item in enumerate(constraints.get("items") or [], 1):
            cat = item.get("category_level3") or item.get("category") or "任意商品"
            desc = f"{i}.{cat}"
            if item.get("price_min") is not None:
                desc += f"（价格不低于{item['price_min']}元）"
            if item.get("price_max") is not None:
                desc += f"（价格不超过{item['price_max']}元）"
            if item.get("discount_min") is not None:
                desc += f"（折扣率不低于{item['discount_min']}%）"
            if item.get("discount_max") is not None:
                desc += f"（折扣率不超过{item['discount_max']}%）"
            parts.append(desc)

        if not parts:
            return ""
        return "，".join(parts) + "，请生成组合方案"

    def _apply_adjust_to_constraints(self, constraints: Dict[str, Any], adj: Dict[str, Any]) -> Dict[str, Any]:
        """把诊断调整应用到约束副本，返回修改后的新约束（不改动原始约束）"""
        import copy
        c = copy.deepcopy(constraints)
        field = adj.get("field")
        value = adj.get("value")
        op = adj.get("op")
        idx = adj.get("slot_index")
        items = c.setdefault("items", [])

        if field == "total_discount":
            if op == "lt":
                c["max_discount_rate"] = value
                c.pop("min_discount_rate", None)
            elif op == "gt":
                c["min_discount_rate"] = value
                c.pop("max_discount_rate", None)
        elif field == "total_price":
            if op == "lt":
                c["price_max"] = value
                c.pop("price_min", None)
            elif op == "gt":
                c["price_min"] = value
                c.pop("price_max", None)
        elif field == "price" and idx is not None and 0 <= idx < len(items):
            if op == "lt":
                items[idx]["price_max"] = value
                items[idx].pop("price_min", None)
            elif op == "gt":
                items[idx]["price_min"] = value
                items[idx].pop("price_max", None)
        elif field == "discount" and idx is not None and 0 <= idx < len(items):
            if op == "lt":
                items[idx]["discount_max"] = value
                items[idx].pop("discount_min", None)
            elif op == "gt":
                items[idx]["discount_min"] = value
                items[idx].pop("discount_max", None)
        elif field == "quantity" and idx is not None and 0 <= idx < len(items):
            try:
                target = max(1, int(value))
            except (TypeError, ValueError):
                target = 1
            def _it_sig(it):
                return (it.get("category_level3"), it.get("category"), it.get("brand"), it.get("specification"),
                        it.get("price_min"), it.get("price_max"), it.get("discount_min"), it.get("discount_max"))
            base_sig = _it_sig(items[idx])
            end = idx
            while end + 1 < len(items) and _it_sig(items[end + 1]) == base_sig:
                end += 1
            group_size = end - idx + 1
            if group_size > target:
                # 同一商品信息块按数量展开为多个相同槽位，减少数量 = 删除该组末尾多余的槽位
                del items[idx + target:end + 1]
        elif field == "remove_last_slot" and len(items) > 1:
            items.pop()
        return c

    def _attach_requirement_adjust(self, result: Dict[str, Any], constraints: Dict[str, Any]) -> None:
        """AI 模式：把每条诊断的一键应用改为"直接覆盖用户输入的需求文本"。

        非 AI 模式是结构化输入（总价/折扣率/商品块输入框），沿用原 adjust（改对应输入框）；
        AI 模式输入是自然语言文本、没有这些输入框，因此把 adjust 改写为
        {"field": "requirement", "value": "修改后的完整需求文本"}，前端一键应用时直接覆盖文本输入。
        对无具体数值的诊断（如"空槽位-换品类"）不附加，避免覆盖成无意义的文本。
        """
        original_text = self._build_requirement_text(constraints)
        for d in result.get("diagnosis") or []:
            adj = d.get("adjust")
            if not adj:
                continue
            revised = self._build_requirement_text(self._apply_adjust_to_constraints(constraints, adj))
            if revised and revised != original_text:
                d["adjust"] = {"field": "requirement", "value": revised}

    async def analyze(self, requirement: str = "", use_ai: bool = False,
                      company_id: Optional[int] = None, user_id: Optional[int] = None,
                      max_solutions: int = 50, total_price: Optional[float] = None,
                      slots: Optional[list] = None, max_discount_rate: Optional[float] = None,
                      total_price_op: str = "", total_discount_op: str = "") -> Dict[str, Any]:
        """分析组合需求，调用组合引擎生成所有可行方案（v2.0）

        支持两种输入：
        - 结构化输入：total_price + max_discount_rate + slots（多块输入，前端主用）
        - 文本输入：requirement（自然语言/AI）
        """
        constraints = {}
        tokens_used = 0
        ai_summary = ""

        if slots:
            # 结构化输入（多块输入）
            constraints = self._build_structured_constraints(
                total_price, slots, max_discount_rate=max_discount_rate,
                total_price_op=total_price_op, total_discount_op=total_discount_op,
            )
        elif use_ai:
            reference_data = self._get_reference_data(company_id=company_id or 0)
            ai_result, tokens_used = await self._parse_by_ai(requirement, reference_data, company_id=company_id or 0, user_id=user_id or 0)
            if ai_result:
                # AI 结果转结构化约束（复用多块输入逻辑，与前端结构完全一致）
                from types import SimpleNamespace
                ai_items = [SimpleNamespace(**it) for it in (ai_result.get("items") or [])]
                constraints = self._build_structured_constraints(
                    ai_result.get("total_price"), ai_items,
                    max_discount_rate=ai_result.get("max_discount_rate"),
                    total_price_op=ai_result.get("total_price_op") or "lt",
                    total_discount_op=ai_result.get("max_discount_op") or "",
                )
                if not constraints.get("items"):
                    # AI 未解析出商品信息（如简单商品搜索）→ 退回规则引擎
                    constraints = self._parse_combination_by_rules(requirement)
                    ai_summary = ""
                else:
                    ai_summary = ai_result.get("summary", "") or constraints.get("summary", "")
            else:
                constraints = self._parse_combination_by_rules(requirement)
                ai_summary = ""
        else:
            constraints = self._parse_combination_by_rules(requirement)
            ai_summary = ""

        # 调用组合方案生成引擎
        from app.services.combination_engine import combination_engine
        result = combination_engine.generate(constraints, company_id=company_id, max_solutions=max_solutions)

        # AI 模式：输入是自然语言文本，把每条诊断的"一键应用"改写为"直接覆盖用户输入的需求文本"
        if use_ai:
            self._attach_requirement_adjust(result, constraints)

        # 附加解析摘要
        result["parsed_constraints"] = constraints
        result["ai_interpretation"] = ai_summary if use_ai else ""
        result["tokens_used"] = tokens_used

        return result

    def generate_recommended_solutions(
        self,
        requirement: str,
        company_id: int,
        role: str,
        user_id: int = 0,
        max_solutions: int = 50,
    ) -> Dict[str, Any]:
        """为低权限用户生成高权限公司的推荐方案（基于邀请链）

        沿着邀请链向上查找：
        - 同公司不推荐
        - 只有角色更高才推荐
        """
        # 1. 解析需求（规则引擎，不同步调用 AI）
        constraints = self._parse_combination_by_rules(requirement)
        if not constraints.get("items"):
            return {"solutions": [], "total_solutions": 0, "message": "未解析出商品组合条件"}

        # 最高级管理员无推荐
        if role == "super_admin":
            return {"solutions": [], "total_solutions": 0, "message": "最高级管理员无推荐方案"}

        if not company_id:
            return {"solutions": [], "total_solutions": 0, "message": "请先完善公司信息"}

        # 2. 沿着邀请链向上查找来源公司
        source_companies = []  # [(company_id, company_name)]
        visited_user_ids = {user_id} if user_id else set()
        current_user_id = user_id

        while current_user_id:
            with sync_engine.connect() as conn:
                # 查找当前用户使用的邀请码
                invite_row = conn.execute(
                    text("SELECT created_by FROM invite_codes WHERE used_by = :uid AND is_used = 1"),
                    {'uid': current_user_id}
                ).fetchone()
                if not invite_row:
                    break

                creator_id = invite_row[0]
                if creator_id in visited_user_ids:
                    break
                visited_user_ids.add(creator_id)

                # 查询创建者信息
                creator_row = conn.execute(
                    text("SELECT role, company_id, company_name FROM users WHERE id = :uid AND is_active = 1"),
                    {'uid': creator_id}
                ).fetchone()
                if not creator_row:
                    break

                creator_role = creator_row[0]
                creator_company_id = creator_row[1] or 0
                creator_company_name = creator_row[2] or ""

                # 同公司不推荐
                if creator_company_id == company_id or not creator_company_id:
                    current_user_id = creator_id
                    continue

                # 只有角色更高才推荐
                role_hierarchy = {"super_admin": 3, "admin": 2, "user": 1}
                current_level = role_hierarchy.get(role, 0)
                creator_level = role_hierarchy.get(creator_role, 0)
                if creator_level > current_level and creator_company_id not in [c[0] for c in source_companies]:
                    source_companies.append((creator_company_id, creator_company_name))

                # 继续向上
                current_user_id = creator_id

        if not source_companies:
            return {"solutions": [], "total_solutions": 0, "message": "暂无推荐方案"}

        # 3. 为每个来源公司生成方案
        from app.services.combination_engine import combination_engine
        all_solutions = []
        seen_signatures = set()

        for src_company_id, src_company_name in source_companies:
            result = combination_engine.generate(
                constraints,
                company_id=src_company_id,
                max_solutions=max_solutions,
            )
            for sol in result.get("solutions", []):
                # 查询该公司的用户角色（取第一个作为来源角色）
                with sync_engine.connect() as conn:
                    role_row = conn.execute(
                        text("SELECT role FROM users WHERE company_id = :c AND is_active = 1 LIMIT 1"),
                        {'c': src_company_id}
                    ).fetchone()
                src_role = role_row[0] if role_row else ""

                sol["source_company_name"] = src_company_name
                sol["source_role"] = src_role

                # 基于产品 quick_model 集合去重
                sig = tuple(
                    sorted(item.get("quick_model", "") for item in sol.get("items", []))
                )
                if sig and sig not in seen_signatures:
                    seen_signatures.add(sig)
                    all_solutions.append(sol)

        # 按总价升序
        all_solutions.sort(key=lambda s: s.get("total_price", 0))

        return {
            "solutions": all_solutions,
            "total_solutions": len(all_solutions),
            "message": f"找到 {len(all_solutions)} 个推荐方案（来自 {len(source_companies)} 家公司）" if all_solutions else "暂无推荐方案",
        }

    def save_plan(self, name: str, requirement: str, ai_enabled: bool, items: list, remark: str = "", company_id: int = 0, company_name: str = "", owner_id: int = 0) -> Dict[str, Any]:
        """保存方案到数据库（绑定 company_id 用于隔离，company_name 用于展示）"""
        total_amount = 0.0
        now_str = datetime.now(timezone(timedelta(hours=8))).isoformat()

        with sync_engine.connect() as conn:
            # 插入方案主表（带 company_id / company_name 和 owner_id）
            result = conn.execute(
                text("""INSERT INTO solution_plans (name, requirement, ai_enabled, total_amount, status, remark, company_name, company_id, owner_id, created_at, updated_at)
                        VALUES (:name, :requirement, :ai_enabled, 0, 'draft', :remark, :company_name, :company_id, :owner_id, :now, :now)"""),
                {"name": name, "requirement": requirement, "ai_enabled": 1 if ai_enabled else 0, "remark": remark, "company_name": company_name, "company_id": company_id, "owner_id": owner_id, "now": now_str}
            )
            plan_id = result.lastrowid

            # 插入明细
            for item in items:
                product_id = item.get("product_id")
                quantity = int(item.get("quantity", 1))
                if quantity < 1:
                    quantity = 1

                # 从数据库查询商品信息（需校验数据隔离：只允许使用本公司产品）
                row = conn.execute(
                    text("SELECT quick_model, product_model, product_name, brand, specification, price, retail_price, category_level1, category_level2, image FROM products WHERE id=:id AND company_id=:company_id"),
                    {"id": product_id, "company_id": company_id}
                ).fetchone()

                if not row:
                    continue

                price = float(row[5]) if row[5] else 0
                retail_price = float(row[6]) if row[6] else 0
                cat1 = row[7] or ""
                cat2 = row[8] or ""
                subtotal = round(price * quantity, 2)
                total_amount += subtotal

                conn.execute(
                    text("""INSERT INTO solution_items
                            (plan_id, product_id, quick_model, product_model, product_name, brand, category_level1, category_level2, specification, price, retail_price, image, quantity, subtotal, created_at)
                            VALUES (:plan_id, :product_id, :qm, :pm, :pn, :brand, :cat1, :cat2, :spec, :price, :retail_price, :image, :qty, :subtotal, :now)"""),
                    {
                        "plan_id": plan_id,
                        "product_id": product_id,
                        "qm": row[0] or "",
                        "pm": row[1] or "",
                        "pn": row[2] or "",
                        "brand": row[3] or "",
                        "cat1": cat1,
                        "cat2": cat2,
                        "spec": row[4] or "",
                        "price": price,
                        "retail_price": retail_price,
                        "image": row[9] or "",
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

    def list_plans(self, company_id: int = 0) -> list:
        """获取当前公司的历史方案列表（含商品数量）"""
        with sync_engine.connect() as conn:
            rows = conn.execute(
                text("""SELECT p.id, p.name, p.requirement, p.total_amount, p.status, p.created_at,
                               (SELECT COUNT(*) FROM solution_items WHERE plan_id = p.id) as items_count
                        FROM solution_plans p WHERE p.company_id=:company_id ORDER BY p.created_at DESC"""),
                {"company_id": company_id}
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "name": r[1] or "",
                    "requirement": (r[2] or "")[:100],
                    "total_amount": r[3] or 0,
                    "status": r[4] or "draft",
                    "created_at": (str(r[5])[:19].replace('T', ' ')) if r[5] else "",
                    "items_count": r[6] or 0,
                }
                for r in rows
            ]

    def get_plan_detail(self, plan_id: int, company_id: int = 0) -> dict:
        """获取方案详情（含明细，数据隔离：按公司ID）"""
        with sync_engine.connect() as conn:
            query = "SELECT * FROM solution_plans WHERE id=:id"
            params: Dict[str, Any] = {"id": plan_id}
            if company_id:
                query += " AND company_id=:company_id"
                params["company_id"] = company_id
            plan = conn.execute(text(query), params).fetchone()
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

    def delete_plan(self, plan_id: int, company_id: int = 0) -> bool:
        """删除方案及其明细（校验 company_id）"""
        with sync_engine.connect() as conn:
            # 先校验数据归属
            query = "SELECT id FROM solution_plans WHERE id=:id"
            params: Dict[str, Any] = {"id": plan_id}
            if company_id:
                query += " AND company_id=:company_id"
                params["company_id"] = company_id
            plan = conn.execute(text(query), params).fetchone()
            if not plan:
                raise ValueError("方案不存在")
            conn.execute(text("DELETE FROM solution_items WHERE plan_id=:pid"), {"pid": plan_id})
            conn.execute(text("DELETE FROM solution_plans WHERE id=:id"), {"id": plan_id})
            conn.commit()
        return True

    def export_excel(self, plan_id: int, company_id: int = 0) -> Tuple[bytes, str]:
        """导出方案为 Excel 表格（v2.0）
        
        返回: (excel_bytes, filename)
        - 表格包含产品库中所有字段的列
        - 最后一列为「备注」列
        - 文件名为方案名称.xlsx
        """
        import io
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from openpyxl.utils import get_column_letter

        with sync_engine.connect() as conn:
            # 查询方案信息
            plan_row = conn.execute(
                text("SELECT id, name FROM solution_plans WHERE id=:id AND company_id=:company_id"),
                {"id": plan_id, "company_id": company_id}
            ).fetchone()
            if not plan_row:
                raise ValueError("方案不存在")
            plan_name = plan_row[1] or f"方案_{plan_id}"

            # 查询方案明细
            items = conn.execute(
                text("SELECT product_id, quantity, remark FROM solution_items WHERE plan_id=:pid ORDER BY id"),
                {"pid": plan_id}
            ).fetchall()

            if not items:
                raise ValueError("方案中没有商品")

            # 查询产品的完整数据（校验数据隔离）
            product_ids = [item[0] for item in items]
            placeholders = ", ".join([f":pid{i}" for i in range(len(product_ids))])
            params = {f"pid{i}": pid for i, pid in enumerate(product_ids)}
            params["company_id"] = company_id
            products = conn.execute(
                text(f"SELECT * FROM products WHERE id IN ({placeholders}) AND company_id=:company_id"),
                params
            ).fetchall()
            prod_cols = [col[1] for col in conn.execute(text("PRAGMA table_info(products)")).fetchall()]
            qty_map = {item[0]: item[1] for item in items}
            remark_map = {item[0]: (item[2] or "") for item in items}

            # 写入 Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            assert ws is not None
            # Excel 工作簿名称不允许: \ / ? * [ ] : 等字符
            safe_name = re.sub(r'[\\/?*\[\]:]', '_', plan_name) if plan_name else "方案"
            ws.title = safe_name[:31]  # Excel sheet name max 31 chars

            header_font = Font(bold=True, color="FFFFFF", size=11)
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            thin_border = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin"),
            )

            # 表头：产品库所有字段 + 数量 + 备注（最后一列）
            display_fields = [
                ("序号", 6), ("快查型号", 18), ("型号", 18),
                ("产品名称", 20), ("品牌", 14), ("一级品类", 14),
                ("二级品类", 14), ("三级品类", 14), ("备货商谈价(元)", 14), ("报价更新", 14),
                ("上次进货价(元)", 14), ("进货价(元)", 12), ("零售价(元)", 12),
                ("折扣率(%)", 10), ("新活动价(元)", 14), ("链接", 30), ("投标价(元)", 12),
                ("集采价/项目(元)", 14), ("代发价(元)", 12), ("毛重(kg)", 10),
                ("箱规", 12), ("合作等级", 12), ("供货状态", 12),
                ("规格", 20), ("备注(产品)", 20), ("代发运费(元)", 14),
                ("69码", 16), ("销量", 10), ("推荐理由", 20),
                ("参数", 20), ("3C", 16), ("图片", 15),
                ("数量", 10), ("备注", 20),  # 最后两列是数量和备注
            ]

            for col_idx, (header_text, width) in enumerate(display_fields, 1):
                cell = ws.cell(row=1, column=col_idx, value=header_text)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
                ws.column_dimensions[get_column_letter(col_idx)].width = width

            # 数据行
            price_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
            for row_idx, prod in enumerate(products, 2):
                p = dict(zip(prod_cols, prod))
                pid = p["id"]
                qty = qty_map.get(pid, 1)
                remark = remark_map.get(pid, "")

                values = [
                    row_idx - 1, p.get("quick_model", ""), p.get("product_model", ""),
                    p.get("product_name", ""), p.get("brand", ""), p.get("category_level1", ""),
                    p.get("category_level2", ""), p.get("category_level3", ""), p.get("negotiation_price") or 0, normalize_datetime_string(p.get("price_update", "")),
                    p.get("last_purchase_price") or 0, p.get("purchase_price") or 0, p.get("retail_price") or 0,
                    p.get("discount_rate") or 0, p.get("new_event_price") or 0, p.get("shop_url", ""), p.get("bid_price") or 0,
                    p.get("group_purchase_price") or 0, p.get("price") or 0, p.get("gross_weight") or 0,
                    p.get("box_spec", ""), p.get("cooperation_level", ""), p.get("supply_status", ""),
                    p.get("specification", ""), p.get("remark", ""), p.get("shipping_fee") or 0,
                    p.get("barcode_69", ""), p.get("sales_volume") or 0, p.get("recommendation", ""),
                    p.get("parameters", ""), p.get("cert_3c", ""),
                    "",  # 图片占位（后面单独处理）
                    qty, remark,  # 数量和备注
                ]
                for col_idx, val in enumerate(values, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=val)
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical="center")
                    if col_idx == 19:
                        cell.fill = price_fill
                        cell.number_format = '#,##0.00'
                    elif col_idx in (9, 11, 12, 13, 15, 16, 17, 18, 24, 26):
                        cell.number_format = '#,##0.00'

                # ---- 图片列：以 TwoCellAnchor 嵌入单元格（随单元格移动/缩放）----
                if not add_image_embedded_in_cell(
                    ws, row_idx, 32, p.get("image") or "", col_width=15, row_height=40
                ):
                    # 无图或图片解析失败时写入占位文本（openpyxl 类型桩误报为 MergedCell）
                    ws.cell(row=row_idx, column=32).value = "[图片]"  # type: ignore[union-attr, assignment]

            ws.freeze_panes = "A2"
            ws.auto_filter.ref = f"A1:{get_column_letter(len(display_fields))}{len(products) + 1}"

            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)

        return buf.getvalue(), f"{plan_name}.xlsx"


solution_service = SolutionService()
