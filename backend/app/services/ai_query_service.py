"""AI 智能查询服务 —— 调用 DeepSeek API 分析自然语言，提取结构化查询条件"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from app.services.query_engine import query_engine
from app.services.query_engine import Product
from sqlalchemy import select, func

logger = logging.getLogger("ai_query")

# DeepSeek API 重试配置
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # 基础等待秒数，采用指数退避
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# 系统提示词：引导 DeepSeek 从用户输入中提取商品查询条件
SYSTEM_PROMPT = """你是一个智能报价系统的查询助手。用户的商品数据库有以下字段（括号内是常见同义/别称，用户在提问时可能使用任意一种）：
- quick_model (快查型号 / 快查 / 快查码) — 精确/模糊均可
- product_model (型号 / 商品型号 / 货号)
- product_name (产品名称 / 商品名称 / 品名)
- brand (品牌 / 品牌名 / 牌子)
- category_level1 (一级品类 / 大类 / 一级分类)
- category_level2 (二级品类 / 小类 / 二级分类)
- negotiation_price (备货商谈价 / 商谈价 / 备货价) — 数值
- price_update (报价更新 / 价格更新)
- last_purchase_price (上次进货价 / 上次进价) — 数值
- purchase_price (进货价 / 进价 / 采购价 / 成本价) — 数值
- retail_price (零售价 / 零售价格) — 数值
- discount_rate (折扣率 / 优惠度 / 折扣) — 自动计算 = 代发价/零售价 × 100%
- new_event_price (新活动价 / 活动价 / 促销价) — 数值
- shop_url (链接 / 店铺链接)
- bid_price (投标价 / 竞标价) — 数值
- group_purchase_price (集采价/项目 / 集采价 / 项目价 / 团购价) — 数值
- price (代发价 / 报价 / 价格 / 供货价) — 数值
- gross_weight (毛重 / 重量) — 数值
- box_spec (箱规 / 箱规格)
- cooperation_level (合作等级 / 合作级别)
- supply_status (供货状态 / 供应状态 / 在售状态)
- specification (规格 / 包装规格)
- remark (备注 / 说明)
- shipping_fee (代发运费 / 运费 / 快递费) — 数值
- barcode_69 (69码 / 条形码 / 条码) — 精确匹配
- sales_volume (销量 / 销售量) — 数值
- recommendation (推荐理由 / 推荐)
- parameters (参数 / 商品参数)
- cert_3c (3C / 3C认证 / CCC)

注意语义匹配：快查型号=quick_model, 进价/成本价=purchase_price, 品类/分类=category_level1+category_level2, 链接=shop_url, 活动价=new_event_price, 集采价=group_purchase_price, 运费=shipping_fee

请从用户的查询中提取结构化的查询条件，以 JSON 格式返回。
返回格式必须严格遵循以下模式之一或组合：
1. 精确匹配: {"type": "exact_barcode", "value": "6901234567890"}
2. 模糊搜索: {"type": "brand_search", "value": "飞利浦"}  (支持: brand_search, model_search, product_name_search, category_level1_search, category_level2_search, category_search, cooperation_level_search, supply_status_search, box_spec_search, cert_3c_search, recommendation_search, price_update_search, spec_keyword)
3. 范围查询: {"type": "price_range", "price_min": 100, "price_max": 200}  (支持: price_range, purchase_price_range, retail_price_range, bid_price_range, group_purchase_price_range, new_event_price_range, negotiation_price_range, shipping_fee_range, gross_weight_range, barcode_range)
4. 销量阈值: {"type": "sales_volume_search", "value": 10}
5. 全量+排序: {"type": "all_products", "sort_by": "price", "sort_order": "asc"}
6. 组合查询: {"type": "combined", "queries": [...多个上面的条件...], "sort_by": "price", "sort_order": "asc"}

排序说明：
- 用户提到"从小到大/从低到高/升序" → sort_order 为 "asc"
- 用户提到"从大到小/从高到低/降序" → sort_order 为 "desc"
- 用户提到"代发价升序/代发价从低到高" → sort_by 为 "price"
- 用户提到"进货价升序/进货价从低到高" → sort_by 为 "purchase_price"
- 用户提到"零售价升序/零售价从高到低" → sort_by 为 "retail_price"，sort_order 为 "desc"
- 用户提到"折扣率升序/折扣率从高到低" → sort_by 为 "discount_rate"
- sort_by 可选值: price(代发价), purchase_price(进货价), retail_price(零售价), discount_rate(折扣率), bid_price(投标价), group_purchase_price(集采价), new_event_price(新活动价), negotiation_price(备货商谈价), shipping_fee(代发运费), gross_weight(毛重), sales_volume(销量)
- 用户没有明确指定排序字段时，默认 sort_by 为 "price"
- 多条件用 combined 类型
- 品类/分类等通用词应同时搜索 category_level1 和 category_level2
- 只返回 JSON，不要额外解释
- 无法识别时返回 {"type": "unknown", "original_text": "用户输入"}

示例：
用户输入: "飞利浦品牌、代发价在400到500之间的商品"
返回: {"type": "combined", "queries": [{"type": "brand_search", "value": "飞利浦"}, {"type": "price_range", "price_min": 400, "price_max": 500}], "sort_by": "price", "sort_order": "asc"}

用户输入: "帮我查下69码6901234567890的价格"
返回: {"type": "exact_barcode", "value": "6901234567890"}

用户输入: "列出所有商品按代发价从低到高"
返回: {"type": "all_products", "sort_by": "price", "sort_order": "asc"}

用户输入: "进货价升序排列"
返回: {"type": "all_products", "sort_by": "purchase_price", "sort_order": "asc"}

用户输入: "折扣率降序排列"
返回: {"type": "all_products", "sort_by": "discount_rate", "sort_order": "desc"}

用户输入: "零售价从高到低"
返回: {"type": "all_products", "sort_by": "retail_price", "sort_order": "desc"}
"""


class AIQueryService:
    """AI 查询服务"""

    async def _call_deepseek(self, user_text: str) -> Optional[Dict[str, Any]]:
        """调用 DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.1,  # 低温度提高一致性
            "max_tokens": 1024,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                # 清理可能的 markdown 代码块标记
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                return json.loads(content)
        except httpx.TimeoutException:
            logger.error("DeepSeek API 请求超时")
            return None
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return None

    async def process_query(self, db: AsyncSession, query_text: str) -> Dict[str, Any]:
        """处理 AI 查询"""
        # 1. 调用 DeepSeek 提取结构化条件
        parsed = await self._call_deepseek(query_text)

        if not parsed:
            # API 调用失败，回退到正则引擎
            logger.info("DeepSeek API 不可用，回退到正则查询引擎")
            return await query_engine.execute_smart_query(db, query_text)

        # 2. 根据解析结果执行查询
        return await self._execute_parsed_query(db, parsed, query_text)

    def _apply_sort_by(self, query, sort_by: str, sort_order: Optional[str]):
        """按指定字段和方向排序"""
        sort_field_map = {
            "price": Product.price,
            "purchase_price": Product.purchase_price,
            "retail_price": Product.retail_price,
            "bid_price": Product.bid_price,
            "group_purchase_price": Product.group_purchase_price,
            "new_event_price": Product.new_event_price,
            "negotiation_price": Product.negotiation_price,
            "shipping_fee": Product.shipping_fee,
            "gross_weight": Product.gross_weight,
            "sales_volume": Product.sales_volume,
            "last_purchase_price": Product.last_purchase_price,
        }
        sort_col = sort_field_map.get(sort_by, Product.price)
        if sort_order == "asc":
            return query.order_by(sort_col.asc())
        elif sort_order == "desc":
            return query.order_by(sort_col.desc())
        return query.order_by(Product.id.desc())

    async def _execute_parsed_query(
        self, db: AsyncSession, parsed: Dict[str, Any], original_text: str
    ) -> Dict[str, Any]:
        """根据 AI 解析结果执行查询"""
        qtype = parsed.get("type", "unknown")

        # 未知查询
        if qtype == "unknown":
            return await query_engine.execute_smart_query(db, original_text)

        # 全量查询
        if qtype == "all_products":
            sort_order = parsed.get("sort_order")
            sort_by = parsed.get("sort_by", "price")
            q = select(Product)
            q = self._apply_sort_by(q, sort_by, sort_order)
            result = await db.execute(q)
            items = list(result.scalars().all())
            field_label = {"price": "代发价", "purchase_price": "进货价", "retail_price": "零售价",
                           "discount_rate": "折扣率", "bid_price": "投标价", "group_purchase_price": "集采价",
                           "new_event_price": "新活动价", "negotiation_price": "备货商谈价",
                           "shipping_fee": "代发运费", "gross_weight": "毛重", "sales_volume": "销量"}.get(sort_by, sort_by)
            order_label = "从低到高" if sort_order == "asc" else "从高到低"
            return {
                "query_intent": "all_products",
                "ai_interpretation": f"查询所有商品，按{field_label}{order_label}排序",
                "results": [p.to_dict() for p in items],
                "result_count": len(items),
                "message": f"共找到 {len(items)} 个商品",
            }

        # 组合查询（多条件）
        if qtype == "combined":
            queries = parsed.get("queries", [])
            sort_order = parsed.get("sort_order")
            sort_by = parsed.get("sort_by", "price")

            all_results = []
            all_items = []
            for sub_query in queries:
                result = await self._execute_single_condition(db, sub_query, sort_order)
                if result and result.get("results"):
                    items = result["results"]
                    all_items.extend(items)
                    all_results.append(result)

            # 去重（按 id）
            seen_ids = set()
            unique_items = []
            for item in all_items:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    unique_items.append(item)

            # 排序
            if sort_order:
                reverse = sort_order == "desc"
                sort_key_map = {
                    "price": lambda x: x.get("price", 0),
                    "purchase_price": lambda x: x.get("purchase_price", 0) or 0,
                    "retail_price": lambda x: x.get("retail_price", 0) or 0,
                    "discount_rate": lambda x: x.get("discount_rate", 0) or 0,
                    "bid_price": lambda x: x.get("bid_price", 0) or 0,
                    "group_purchase_price": lambda x: x.get("group_purchase_price", 0) or 0,
                    "new_event_price": lambda x: x.get("new_event_price", 0) or 0,
                    "negotiation_price": lambda x: x.get("negotiation_price", 0) or 0,
                    "shipping_fee": lambda x: x.get("shipping_fee", 0) or 0,
                    "gross_weight": lambda x: x.get("gross_weight", 0) or 0,
                    "sales_volume": lambda x: x.get("sales_volume", 0) or 0,
                }
                key_fn = sort_key_map.get(sort_by, lambda x: x.get("price", 0))
                unique_items.sort(key=key_fn, reverse=reverse)
            else:
                unique_items.sort(key=lambda x: x.get("price", 0))

            # 构建 AI 解释
            cond_desc = []
            for sq in queries:
                t = sq.get("type", "")
                v = sq.get("value", "")
                if t == "brand_search":
                    cond_desc.append(f"品牌={v}")
                elif t == "category_search":
                    cond_desc.append(f"品类={v}")
                elif t == "category_level1_search":
                    cond_desc.append(f"一级品类={v}")
                elif t == "category_level2_search":
                    cond_desc.append(f"二级品类={v}")
                elif t == "model_search":
                    cond_desc.append(f"型号={v}")
                elif t == "product_name_search":
                    cond_desc.append(f"产品名称={v}")
                elif t == "cooperation_level_search":
                    cond_desc.append(f"合作等级={v}")
                elif t == "supply_status_search":
                    cond_desc.append(f"供货状态={v}")
                elif t == "box_spec_search":
                    cond_desc.append(f"箱规={v}")
                elif t == "cert_3c_search":
                    cond_desc.append(f"3C={v}")
                elif t == "recommendation_search":
                    cond_desc.append(f"推荐理由={v}")
                elif t == "price_update_search":
                    cond_desc.append(f"报价更新={v}")
                elif t == "spec_keyword":
                    cond_desc.append(f"规格={v}")
                elif t == "price_range":
                    cond_desc.append(f"代发价{sq.get('price_min')}~{sq.get('price_max')}")
                elif t == "purchase_price_range":
                    cond_desc.append(f"进货价{sq.get('purchase_price_min')}~{sq.get('purchase_price_max')}")
                elif t == "retail_price_range":
                    cond_desc.append(f"零售价{sq.get('retail_price_min')}~{sq.get('retail_price_max')}")
                elif t == "bid_price_range":
                    cond_desc.append(f"投标价{sq.get('bid_price_min')}~{sq.get('bid_price_max')}")
                elif t == "group_purchase_price_range":
                    cond_desc.append(f"集采价{sq.get('group_purchase_price_min')}~{sq.get('group_purchase_price_max')}")
                elif t == "new_event_price_range":
                    cond_desc.append(f"新活动价{sq.get('new_event_price_min')}~{sq.get('new_event_price_max')}")
                elif t == "negotiation_price_range":
                    cond_desc.append(f"备货商谈价{sq.get('negotiation_price_min')}~{sq.get('negotiation_price_max')}")
                elif t == "shipping_fee_range":
                    cond_desc.append(f"代发运费{sq.get('shipping_fee_min')}~{sq.get('shipping_fee_max')}")
                elif t == "gross_weight_range":
                    cond_desc.append(f"毛重{sq.get('gross_weight_min')}~{sq.get('gross_weight_max')}")
                elif t == "exact_barcode":
                    cond_desc.append(f"69码={v}")
                elif t == "barcode_range":
                    cond_desc.append(f"69码区间{sq.get('barcode_min')}~{sq.get('barcode_max')}")
                elif t == "sales_volume_search":
                    cond_desc.append(f"销量≥{v}")
                elif t == "discount_rate_range":
                    cond_desc.append(f"折扣率{sq.get('discount_rate_min')}%~{sq.get('discount_rate_max')}%")
                elif t == "fuzzy_search":
                    cond_desc.append(f"模糊搜索={v}")

            ai_desc = " 且 ".join(cond_desc) if cond_desc else "多条件组合查询"

            return {
                "query_intent": "combined",
                "ai_interpretation": ai_desc,
                "results": unique_items,
                "result_count": len(unique_items),
                "message": f"AI 分析结果：{ai_desc}，共找到 {len(unique_items)} 个商品",
            }

        # 单个条件
        result = await self._execute_single_condition(db, parsed, parsed.get("sort_order"))
        if result:
            return result

        return {
            "query_intent": "unknown",
            "results": [],
            "result_count": 0,
            "message": "AI 未能解析查询条件，请重试",
        }

    async def _execute_single_condition(
        self, db: AsyncSession, condition: Dict[str, Any], sort_order: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """执行单个查询条件"""
        qtype = condition.get("type")
        if not qtype:
            return None

        try:
            if qtype == "exact_barcode":
                items, total = await query_engine._query_by_barcode(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "brand_search":
                items, total = await query_engine._query_by_brand(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "model_search":
                items, total = await query_engine._query_by_model(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "product_name_search":
                items, total = await query_engine._query_by_product_name(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "category_search":
                items, total = await query_engine._query_by_category(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "category_level1_search":
                items, total = await query_engine._query_by_category_level1(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "category_level2_search":
                items, total = await query_engine._query_by_category_level2(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "cooperation_level_search":
                items, total = await query_engine._query_by_cooperation_level(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "supply_status_search":
                items, total = await query_engine._query_by_supply_status(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "box_spec_search":
                items, total = await query_engine._query_by_box_spec(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "cert_3c_search":
                items, total = await query_engine._query_by_cert_3c(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "recommendation_search":
                items, total = await query_engine._query_by_recommendation(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "price_update_search":
                items, total = await query_engine._query_by_price_update(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "spec_keyword":
                items, total = await query_engine._query_by_spec(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "price_range":
                items, total = await query_engine._query_by_price_range(
                    db, condition["price_min"], condition["price_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "purchase_price_range":
                items, total = await query_engine._query_by_purchase_price_range(
                    db, condition["purchase_price_min"], condition["purchase_price_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "retail_price_range":
                items, total = await query_engine._query_by_retail_price_range(
                    db, condition["retail_price_min"], condition["retail_price_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "bid_price_range":
                items, total = await query_engine._query_by_bid_price_range(
                    db, condition["bid_price_min"], condition["bid_price_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "group_purchase_price_range":
                items, total = await query_engine._query_by_group_purchase_price_range(
                    db, condition["group_purchase_price_min"], condition["group_purchase_price_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "new_event_price_range":
                items, total = await query_engine._query_by_new_event_price_range(
                    db, condition["new_event_price_min"], condition["new_event_price_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "negotiation_price_range":
                items, total = await query_engine._query_by_negotiation_price_range(
                    db, condition["negotiation_price_min"], condition["negotiation_price_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "shipping_fee_range":
                items, total = await query_engine._query_by_shipping_fee_range(
                    db, condition["shipping_fee_min"], condition["shipping_fee_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "gross_weight_range":
                items, total = await query_engine._query_by_gross_weight_range(
                    db, condition["gross_weight_min"], condition["gross_weight_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "barcode_range":
                items, total = await query_engine._query_by_barcode_range(
                    db, condition["barcode_min"], condition["barcode_max"], sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "sales_volume_search":
                items, total = await query_engine._query_by_sales_volume(db, condition.get("value", 0), sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "discount_rate_range":
                items, total = await query_engine._query_by_discount_rate(
                    db, condition.get("discount_rate_min", 0), condition.get("discount_rate_max", 100), sort_order
                )
                return {"results": [p.to_dict() for p in items], "count": total}

            elif qtype == "fuzzy_search":
                items, total = await query_engine._query_fuzzy(db, condition["value"], sort_order)
                return {"results": [p.to_dict() for p in items], "count": total}

        except Exception as e:
            logger.error(f"执行条件查询失败 {qtype}: {e}")
            return None

        return None


ai_query_service = AIQueryService()
