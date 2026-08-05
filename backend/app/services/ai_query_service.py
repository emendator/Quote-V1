"""AI 智能查询服务 —— 调用 DeepSeek API 分析自然语言，提取结构化查询条件"""
import json
import logging
from typing import Any, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.api_key_service import call_deepseek_with_user_key
from app.services.query_engine import query_engine
from app.services.query_engine import Product
from sqlalchemy import select, func, or_

logger = logging.getLogger("ai_query")

# DeepSeek API 重试配置
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # 基础等待秒数，采用指数退避
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# 系统提示词：引导 DeepSeek 从用户输入中提取商品查询条件
SYSTEM_PROMPT = """你是一个智能报价系统的查询助手。用户的商品数据库有以下字段（括号内是常见同义/别称，用户在提问时可能使用任意一种）：
- quick_model (快查型号 / 快查 / 快查码)
- product_model (型号 / 商品型号 / 货号)
- product_name (产品名称 / 商品名称 / 品名)
- brand (品牌 / 品牌名 / 牌子)
- category_level1 (一级品类 / 大类 / 一级分类)
- category_level2 (二级品类 / 小类 / 二级分类)
- category_level3 (三级品类 / 三级分类 / 细分类)
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

注意语义匹配：快查型号=quick_model, 进价/成本价=purchase_price, 品类/分类=category_level1+category_level2+category_level3, 链接=shop_url, 活动价=new_event_price, 集采价=group_purchase_price, 运费=shipping_fee

请从用户的查询中提取结构化条件，以 JSON 格式返回。

可用条件字段（数值字段支持 _min / _max 后缀表示范围）：
- brand (品牌)
- category_level1 (一级品类)
- category_level2 (二级品类)
- category_level3 (三级品类)
- price_min / price_max (代发价范围)
- purchase_price_min / purchase_price_max (进货价范围)
- retail_price_min / retail_price_max (零售价范围)
- negotiation_price_min / negotiation_price_max (备货商谈价范围)
- bid_price_min / bid_price_max (投标价范围)
- group_purchase_price_min / group_purchase_price_max (集采价范围)
- new_event_price_min / new_event_price_max (新活动价范围)
- shipping_fee_min / shipping_fee_max (代发运费范围)
- gross_weight_min / gross_weight_max (毛重范围)
- discount_rate_min / discount_rate_max (折扣率范围)
- sales_volume_min (最低销量)
- supply_status (供货状态)
- specification (规格关键词)
- barcode_69 (69码，精确匹配)
- quick_model (快查型号)
- product_model (商品型号)
- keywords (其他关键词数组)
- sort_by (排序字段: price/purchase_price/retail_price/discount_rate/bid_price/group_purchase_price/new_event_price/negotiation_price/shipping_fee/gross_weight/sales_volume)
- sort_order (排序方向: asc=升序/desc=降序)
- summary (查询摘要，简短描述)

返回格式示例：
{"brand": "飞利浦", "category_level2": "插线板", "price_max": 200, "keywords": [], "summary": "200元以下的飞利浦插线板"}
{"brand": "华为", "category_level1": "3C数码", "purchase_price_max": 100, "sort_by": "price", "sort_order": "asc", "summary": "华为商品进货价100以内按代发价升序"}
{"barcode_69": "6901234567890", "summary": "查询69码6901234567890的商品"}
{"keywords": ["充电宝"], "sort_by": "price", "sort_order": "asc", "summary": "充电宝按代发价升序"}

注意事项：
- 品牌/品类等务必参考下方的数据库参考数据进行精准匹配
- 价格字段注意区分代发价(price)、进货价(purchase_price)、零售价(retail_price)等
- "xx以下/不超过/低于/以内" → 对应字段的 _max
- "xx以上/超过/高于" → 对应字段的 _min
- 用户说"进价"→purchase_price，"报价/价格"→price
- 品类/分类等通用词应同时搜索 category_level1、category_level2、category_level3
- 无法识别的关键词放到 keywords 数组
- 没有明确排序时不要输出 sort_by/sort_order
- 只返回 JSON，不要额外解释
- 无法提取任何条件时返回 {"keywords": [], "summary": "用户输入"}
"""


class AIQueryService:
    """AI 查询服务"""

    async def _get_reference_data(self, db: AsyncSession, company_id: Optional[int] = None) -> str:
        """从数据库采样参考数据，帮助 AI 理解实际存在的值（数据隔离：按公司ID）"""
        try:
            # 构建基础查询条件
            base_filter = True
            if company_id:
                base_filter = Product.company_id == company_id

            # 查询品牌列表（当前用户数据）
            brand_result = await db.execute(
                select(Product.brand).distinct().where(Product.brand.isnot(None)).where(Product.brand != '').where(base_filter).order_by(Product.brand).limit(200)
            )
            brands = [r[0] for r in brand_result.fetchall() if r[0]]

            # 查询一级品类（当前用户数据）
            cat1_result = await db.execute(
                select(Product.category_level1).distinct().where(Product.category_level1.isnot(None)).where(Product.category_level1 != '').where(base_filter).order_by(Product.category_level1).limit(200)
            )
            cat1_list = [r[0] for r in cat1_result.fetchall() if r[0]]

            # 查询二级品类（当前用户数据）
            cat2_result = await db.execute(
                select(Product.category_level2).distinct().where(Product.category_level2.isnot(None)).where(Product.category_level2 != '').where(base_filter).order_by(Product.category_level2).limit(200)
            )
            cat2_list = [r[0] for r in cat2_result.fetchall() if r[0]]

            # 查询三级品类（当前用户数据）
            cat3_result = await db.execute(
                select(Product.category_level3).distinct().where(Product.category_level3.isnot(None)).where(Product.category_level3 != '').where(base_filter).order_by(Product.category_level3).limit(200)
            )
            cat3_list = [r[0] for r in cat3_result.fetchall() if r[0]]

            # 查询供货状态（示例1个，数据隔离：按公司ID）
            status_result = await db.execute(
                select(Product.supply_status).distinct().where(Product.supply_status.isnot(None)).where(Product.supply_status != '').where(base_filter).limit(1)
            )
            status_val = status_result.scalar_one_or_none()

            lines = []
            lines.append("========== 数据库参考数据 ==========")
            lines.append("以下数据来自数据库，请据此匹配用户的输入。")
            lines.append("")
            if brands:
                lines.append(f"【品牌】全部值：{', '.join(brands)}")
            if cat1_list:
                lines.append(f"【一级品类】全部值：{', '.join(cat1_list)}")
            if cat2_list:
                lines.append(f"【二级品类】全部值：{', '.join(cat2_list)}")
            if cat3_list:
                lines.append(f"【三级品类】全部值：{', '.join(cat3_list)}")
            if status_val:
                lines.append(f"【供货状态】示例：{status_val}")
            lines.append("")
            lines.append("请将用户输入中的词汇与以上参考数据精准匹配。")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"获取参考数据失败: {e}")
            return ""

    async def _call_deepseek(self, user_text: str, reference_data: str = "",
                             user_id: int = 0) -> Tuple[Optional[Dict[str, Any]], int]:
        """调用 DeepSeek API，返回 (结果, 消耗token数)"""
        # 构建系统提示词：基础提示 + 参考数据
        system_content = SYSTEM_PROMPT
        if reference_data:
            system_content = system_content + "\n\n" + reference_data

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_text},
        ]

        data, tokens_used = await call_deepseek_with_user_key(
            user_id=user_id,
            messages=messages,
            max_tokens=1024,
            temperature=0.1,
        )
        if not data:
            return None, 0

        try:
            content = data["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            return json.loads(content), tokens_used
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return None, tokens_used

    async def process_query(self, db: AsyncSession, query_text: str, company_id: Optional[int] = None, user_id: int = 0) -> Dict[str, Any]:
        """处理 AI 查询（支持数据隔离：按公司ID）"""
        # 0. 查询参考数据，帮助 AI 理解数据库中的实际值
        reference_data = await self._get_reference_data(db, company_id=company_id)

        # 1. 调用 DeepSeek 提取结构化条件
        parsed, tokens_used = await self._call_deepseek(query_text, reference_data, user_id=user_id)

        if not parsed:
            # API 调用失败，回退到正则引擎
            logger.info("DeepSeek API 不可用，回退到正则查询引擎")
            result = await query_engine.execute_smart_query(db, query_text, company_id=company_id)
            result["tokens_used"] = 0
            return result

        # 2. 根据解析结果执行查询
        result = await self._execute_parsed_query(db, parsed, query_text, company_id=company_id)
        result["tokens_used"] = tokens_used
        return result

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
        self, db: AsyncSession, parsed: Dict[str, Any], original_text: str,
        company_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """根据 AI 解析结果执行查询（简化版：从 flat intent 构建 SQL，支持数据隔离）"""
        # 如果没有任何条件，回退到正则引擎
        has_any_condition = any(
            parsed.get(k) not in (None, "", [], {})
            for k in ["brand", "category_level1", "category_level2", "category_level3",
                       "price_min", "price_max", "purchase_price_min", "purchase_price_max",
                       "retail_price_min", "retail_price_max", "bid_price_min", "bid_price_max",
                       "group_purchase_price_min", "group_purchase_price_max",
                       "new_event_price_min", "new_event_price_max",
                       "negotiation_price_min", "negotiation_price_max",
                       "shipping_fee_min", "shipping_fee_max",
                       "gross_weight_min", "gross_weight_max",
                       "discount_rate_min", "discount_rate_max",
                       "sales_volume_min", "supply_status", "specification",
                       "barcode_69", "quick_model", "product_model", "keywords"]
        )
        if not has_any_condition:
            return await query_engine.execute_smart_query(db, original_text, company_id=company_id)

        # 构建查询（带数据隔离）
        q = select(Product)
        if company_id:
            q = q.where(Product.company_id == company_id)
        conditions_desc = []

        # --- 文本模糊匹配 ---
        if parsed.get("brand"):
            q = q.where(Product.brand.like(f"%{parsed['brand']}%"))
            conditions_desc.append(f"品牌={parsed['brand']}")

        if parsed.get("category_level1"):
            q = q.where(Product.category_level1.like(f"%{parsed['category_level1']}%"))
            conditions_desc.append(f"一级品类={parsed['category_level1']}")

        if parsed.get("category_level2"):
            q = q.where(Product.category_level2.like(f"%{parsed['category_level2']}%"))
            conditions_desc.append(f"二级品类={parsed['category_level2']}")

        if parsed.get("category_level3"):
            q = q.where(Product.category_level3.like(f"%{parsed['category_level3']}%"))
            conditions_desc.append(f"三级品类={parsed['category_level3']}")

        if parsed.get("supply_status"):
            q = q.where(Product.supply_status.like(f"%{parsed['supply_status']}%"))
            conditions_desc.append(f"供货状态={parsed['supply_status']}")

        if parsed.get("specification"):
            q = q.where(Product.specification.like(f"%{parsed['specification']}%"))
            conditions_desc.append(f"规格={parsed['specification']}")

        if parsed.get("barcode_69"):
            q = q.where(Product.barcode_69 == parsed["barcode_69"])
            conditions_desc.append(f"69码={parsed['barcode_69']}")

        if parsed.get("quick_model"):
            q = q.where(Product.quick_model.like(f"%{parsed['quick_model']}%"))
            conditions_desc.append(f"快查型号={parsed['quick_model']}")

        if parsed.get("product_model"):
            q = q.where(Product.product_model.like(f"%{parsed['product_model']}%"))
            conditions_desc.append(f"型号={parsed['product_model']}")

        # --- 关键词 ---
        keywords = parsed.get("keywords", [])
        if keywords and isinstance(keywords, list):
            kw_filters = []
            for kw in keywords:
                kw_str = str(kw)
                kw_filters.append(Product.product_name.like(f"%{kw_str}%"))
                kw_filters.append(Product.quick_model.like(f"%{kw_str}%"))
                kw_filters.append(Product.product_model.like(f"%{kw_str}%"))
                kw_filters.append(Product.specification.like(f"%{kw_str}%"))
                kw_filters.append(Product.brand.like(f"%{kw_str}%"))
                kw_filters.append(Product.remark.like(f"%{kw_str}%"))
            if kw_filters:
                q = q.where(or_(*kw_filters))
                conditions_desc.append(f"关键词={','.join(str(k) for k in keywords)}")

        # --- 价格/数值范围 ---
        price_field_map = {
            "price": Product.price,
            "purchase_price": Product.purchase_price,
            "retail_price": Product.retail_price,
            "bid_price": Product.bid_price,
            "group_purchase_price": Product.group_purchase_price,
            "new_event_price": Product.new_event_price,
            "negotiation_price": Product.negotiation_price,
            "shipping_fee": Product.shipping_fee,
            "gross_weight": Product.gross_weight,
        }
        price_labels = {
            "price": "代发价", "purchase_price": "进货价", "retail_price": "零售价",
            "bid_price": "投标价", "group_purchase_price": "集采价",
            "new_event_price": "新活动价", "negotiation_price": "备货商谈价",
            "shipping_fee": "代发运费", "gross_weight": "毛重", "discount_rate": "折扣率",
        }
        for field, column in price_field_map.items():
            min_val = parsed.get(f"{field}_min")
            max_val = parsed.get(f"{field}_max")
            if min_val is not None:
                q = q.where(column >= float(min_val))
            if max_val is not None:
                q = q.where(column <= float(max_val))
            if min_val is not None or max_val is not None:
                label = price_labels.get(field, field)
                if min_val is not None and max_val is not None:
                    conditions_desc.append(f"{label}{min_val}~{max_val}")
                elif min_val is not None:
                    conditions_desc.append(f"{label}≥{min_val}")
                else:
                    conditions_desc.append(f"{label}≤{max_val}")

        # discount_rate 是计算属性（price / retail_price * 100），不是数据库列，需用表达式
        dr_min = parsed.get("discount_rate_min")
        dr_max = parsed.get("discount_rate_max")
        if dr_min is not None:
            q = q.where((Product.price * 100.0 / func.nullif(Product.retail_price, 0)) >= float(dr_min))
            conditions_desc.append(f"折扣率≥{dr_min}")
        if dr_max is not None:
            q = q.where((Product.price * 100.0 / func.nullif(Product.retail_price, 0)) <= float(dr_max))
            conditions_desc.append(f"折扣率≤{dr_max}")

        # --- 最低销量 ---
        if parsed.get("sales_volume_min") is not None:
            q = q.where(Product.sales_volume >= int(parsed["sales_volume_min"]))
            conditions_desc.append(f"销量≥{parsed['sales_volume_min']}")

        # --- 排序 ---
        sort_by = parsed.get("sort_by")
        sort_order = parsed.get("sort_order")
        if sort_by and sort_by in price_field_map:
            sort_col = price_field_map[sort_by]
            if sort_order == "asc":
                q = q.order_by(sort_col.asc())
            elif sort_order == "desc":
                q = q.order_by(sort_col.desc())
            else:
                q = q.order_by(sort_col.asc())
        else:
            q = q.order_by(Product.price.asc())

        q = q.limit(500)

        result = await db.execute(q)
        items = list(result.scalars().all())
        ai_desc = " 且 ".join(conditions_desc) if conditions_desc else "全部商品"
        return {
            "query_intent": "parsed",
            "ai_interpretation": ai_desc,
            "results": [p.to_dict() for p in items],
            "result_count": len(items),
            "message": f"AI 分析结果：{ai_desc}，共找到 {len(items)} 个商品",
        }

ai_query_service = AIQueryService()
