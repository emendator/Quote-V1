"""智能查询引擎 —— 将解析后的查询意图转化为数据库查询"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from app.models import Product
from app.services.message_parser import message_parser


class QueryEngine:
    """智能查询引擎"""

    async def execute_smart_query(self, db: AsyncSession, query_text: str, company_id: Optional[int] = None) -> Dict[str, Any]:
        """执行智能查询（支持数据隔离：按公司ID，company_id 显式传入每个子查询）"""
        # 1. 解析消息
        parsed = message_parser.parse(query_text)
        raw_queries = parsed.get("queries", [])
        sort_order = parsed.get("sort_order")

        if not raw_queries:
            return {
                "query_intent": "unknown",
                "parsed_params": {},
                "results": [],
                "result_count": 0,
                "message": "未能识别查询意图，请尝试输入69码、快查型号、品牌、型号、品类、规格或价格区间等信息",
                "unrecognized_text": query_text,
            }

        # 2. 分离排序意图和实际查询
        specific_queries = [q for q in raw_queries if q["type"] not in ("sort_order", "all_products")]
        sort_q = next((q for q in raw_queries if q["type"] == "sort_order"), None)
        all_q = next((q for q in raw_queries if q["type"] == "all_products"), None)

        effective_sort = sort_order or (sort_q["value"] if sort_q else None)

        # 3. 如果有具体的查询条件，优先处理它们
        if specific_queries:
            data_queries = specific_queries
        elif all_q:
            products, total = await self._query_all(db, effective_sort, company_id=company_id)
            return {
                "query_intent": "all_products",
                "parsed_params": {},
                "results": [p.to_dict() for p in products],
                "result_count": total,
                "message": f"共找到 {total} 个商品",
            }
        else:
            data_queries = []

        # 4. 处理单个查询
        if len(data_queries) == 1:
            return await self._execute_single_query(db, data_queries[0], effective_sort, company_id=company_id)

        # 5. 处理多个查询 —— AND 联合（取交集）
        all_product_sets = []
        parsed_queries = []
        for q in data_queries:
            result = await self._execute_single_query(db, q, effective_sort, return_raw=True, company_id=company_id)
            parsed_queries.append(result)
            if result.get("results"):
                all_product_sets.append({p["id"] for p in result["results"]})

        if all_product_sets:
            common_ids = all_product_sets[0]
            for s in all_product_sets[1:]:
                common_ids = common_ids & s
        else:
            common_ids = set()

        if common_ids:
            # 从第一个结果中取出交集商品（保证字段完整）
            first_results = {p["id"]: p for p in parsed_queries[0].get("results", [])}
            merged = [first_results[pid] for pid in common_ids if pid in first_results]
        else:
            merged = []

        # 排序
        if effective_sort == "asc":
            merged.sort(key=lambda p: p.get("price", 0))
        elif effective_sort == "desc":
            merged.sort(key=lambda p: p.get("price", 0), reverse=True)

        return {
            "query_intent": "combined",
            "parsed_queries": parsed_queries,
            "results": merged,
            "result_count": len(merged),
            "message": f"{len(data_queries)} 个条件联合查询，共找到 {len(merged)} 个商品",
        }

    async def _execute_single_query(
        self, db: AsyncSession, query: Dict[str, Any], sort_order: Optional[str] = None,
        return_raw: bool = False, company_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行单个查询（支持数据隔离：按公司ID）"""
        qtype = query["type"]
        value = query.get("value", "")

        products = []
        total = 0
        intent = qtype
        params = {}
        msg = ""

        try:
            if qtype == "exact_barcode":
                products, total = await self._query_by_barcode(db, query["value"], sort_order, company_id)
                params = {"barcode_69": query["value"]}
                msg = f"已为您找到69码为 {query['value']} 的商品报价" if total > 0 else f"未找到69码为 {query['value']} 的商品"

            elif qtype == "model_search":
                products, total = await self._query_by_model(db, query["value"], sort_order, company_id)
                params = {"product_model": query["value"]}
                msg = f"型号包含「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到型号包含「{query['value']}」的商品"

            elif qtype == "brand_search":
                products, total = await self._query_by_brand(db, query["value"], sort_order, company_id)
                params = {"brand": query["value"]}
                msg = f"品牌为「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到品牌「{query['value']}」的商品"

            elif qtype == "product_name_search":
                products, total = await self._query_by_product_name(db, query["value"], sort_order, company_id)
                params = {"product_name": query["value"]}
                msg = f"产品名称包含「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到产品名称包含「{query['value']}」的商品"

            elif qtype == "category_level1_search":
                products, total = await self._query_by_category_level1(db, query["value"], sort_order, company_id)
                params = {"category_level1": query["value"]}
                msg = f"一级品类为「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到一级品类「{query['value']}」的商品"

            elif qtype == "category_level2_search":
                products, total = await self._query_by_category_level2(db, query["value"], sort_order, company_id)
                params = {"category_level2": query["value"]}
                msg = f"二级品类为「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到二级品类「{query['value']}」的商品"

            elif qtype == "category_level3_search":
                products, total = await self._query_by_category_level3(db, query["value"], sort_order, company_id)
                params = {"category_level3": query["value"]}
                msg = f"三级品类为「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到三级品类「{query['value']}」的商品"

            elif qtype == "category_search":
                products, total = await self._query_by_category(db, query["value"], sort_order, company_id)
                params = {"category": query["value"]}
                msg = f"品类包含「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到品类「{query['value']}」的商品"

            elif qtype == "cooperation_level_search":
                products, total = await self._query_by_cooperation_level(db, query["value"], sort_order, company_id)
                params = {"cooperation_level": query["value"]}
                msg = f"合作等级为「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到合作等级「{query['value']}」的商品"

            elif qtype == "supply_status_search":
                products, total = await self._query_by_supply_status(db, query["value"], sort_order, company_id)
                params = {"supply_status": query["value"]}
                msg = f"供货状态为「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到供货状态「{query['value']}」的商品"

            elif qtype == "box_spec_search":
                products, total = await self._query_by_box_spec(db, query["value"], sort_order, company_id)
                params = {"box_spec": query["value"]}
                msg = f"箱规包含「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到箱规「{query['value']}」的商品"

            elif qtype == "cert_3c_search":
                products, total = await self._query_by_cert_3c(db, query["value"], sort_order, company_id)
                params = {"cert_3c": query["value"]}
                msg = f"3C包含「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到3C「{query['value']}」的商品"

            elif qtype == "recommendation_search":
                products, total = await self._query_by_recommendation(db, query["value"], sort_order, company_id)
                params = {"recommendation": query["value"]}
                msg = f"推荐理由包含「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到推荐理由包含「{query['value']}」的商品"

            elif qtype == "price_update_search":
                products, total = await self._query_by_price_update(db, query["value"], sort_order, company_id)
                params = {"price_update": query["value"]}
                msg = f"报价更新包含「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到报价更新「{query['value']}」的商品"

            elif qtype == "price_range":
                products, total = await self._query_by_price_range(
                    db, query["price_min"], query["price_max"], sort_order, company_id
                )
                params = {"price_min": query["price_min"], "price_max": query["price_max"]}
                msg = f"代发价在 {query['price_min']} ~ {query['price_max']} 元之间的商品共 {total} 个"

            elif qtype == "purchase_price_range":
                products, total = await self._query_by_purchase_price_range(
                    db, query["purchase_price_min"], query["purchase_price_max"], sort_order, company_id
                )
                params = {"purchase_price_min": query["purchase_price_min"], "purchase_price_max": query["purchase_price_max"]}
                msg = f"进货价在 {query['purchase_price_min']} ~ {query['purchase_price_max']} 元之间的商品共 {total} 个"

            elif qtype == "retail_price_range":
                products, total = await self._query_by_retail_price_range(
                    db, query["retail_price_min"], query["retail_price_max"], sort_order, company_id
                )
                params = {"retail_price_min": query["retail_price_min"], "retail_price_max": query["retail_price_max"]}
                msg = f"零售价在 {query['retail_price_min']} ~ {query['retail_price_max']} 元之间的商品共 {total} 个"

            elif qtype == "bid_price_range":
                products, total = await self._query_by_bid_price_range(
                    db, query["bid_price_min"], query["bid_price_max"], sort_order, company_id
                )
                params = {"bid_price_min": query["bid_price_min"], "bid_price_max": query["bid_price_max"]}
                msg = f"投标价在 {query['bid_price_min']} ~ {query['bid_price_max']} 元之间的商品共 {total} 个"

            elif qtype == "group_purchase_price_range":
                products, total = await self._query_by_group_purchase_price_range(
                    db, query["group_purchase_price_min"], query["group_purchase_price_max"], sort_order, company_id
                )
                params = {"group_purchase_price_min": query["group_purchase_price_min"], "group_purchase_price_max": query["group_purchase_price_max"]}
                msg = f"集采价在 {query['group_purchase_price_min']} ~ {query['group_purchase_price_max']} 元之间的商品共 {total} 个"

            elif qtype == "new_event_price_range":
                products, total = await self._query_by_new_event_price_range(
                    db, query["new_event_price_min"], query["new_event_price_max"], sort_order, company_id
                )
                params = {"new_event_price_min": query["new_event_price_min"], "new_event_price_max": query["new_event_price_max"]}
                msg = f"新活动价在 {query['new_event_price_min']} ~ {query['new_event_price_max']} 元之间的商品共 {total} 个"

            elif qtype == "negotiation_price_range":
                products, total = await self._query_by_negotiation_price_range(
                    db, query["negotiation_price_min"], query["negotiation_price_max"], sort_order, company_id
                )
                params = {"negotiation_price_min": query["negotiation_price_min"], "negotiation_price_max": query["negotiation_price_max"]}
                msg = f"备货商谈价在 {query['negotiation_price_min']} ~ {query['negotiation_price_max']} 元之间的商品共 {total} 个"

            elif qtype == "shipping_fee_range":
                products, total = await self._query_by_shipping_fee_range(
                    db, query["shipping_fee_min"], query["shipping_fee_max"], sort_order, company_id
                )
                params = {"shipping_fee_min": query["shipping_fee_min"], "shipping_fee_max": query["shipping_fee_max"]}
                msg = f"代发运费在 {query['shipping_fee_min']} ~ {query['shipping_fee_max']} 元之间的商品共 {total} 个"

            elif qtype == "gross_weight_range":
                products, total = await self._query_by_gross_weight_range(
                    db, query["gross_weight_min"], query["gross_weight_max"], sort_order, company_id
                )
                params = {"gross_weight_min": query["gross_weight_min"], "gross_weight_max": query["gross_weight_max"]}
                msg = f"毛重在 {query['gross_weight_min']} ~ {query['gross_weight_max']} kg之间的商品共 {total} 个"

            elif qtype == "sales_volume_search":
                products, total = await self._query_by_sales_volume(db, query["value"], sort_order, company_id)
                params = {"sales_volume": query["value"]}
                msg = f"销量不低于 {query['value']} 的商品共 {total} 个"

            elif qtype == "barcode_range":
                products, total = await self._query_by_barcode_range(
                    db, query["barcode_min"], query["barcode_max"], sort_order, company_id
                )
                params = {"barcode_min": query["barcode_min"], "barcode_max": query["barcode_max"]}
                msg = f"69码在 {query['barcode_min']} ~ {query['barcode_max']} 之间的商品共 {total} 个"

            elif qtype == "spec_keyword":
                products, total = await self._query_by_spec(db, query["value"], sort_order, company_id)
                params = {"spec_keyword": query["value"]}
                msg = f"规格包含「{query['value']}」的商品共 {total} 个"

            elif qtype == "discount_rate_range":
                products, total = await self._query_by_discount_rate(
                    db, query.get("discount_rate_min", 0), query.get("discount_rate_max", 100), sort_order, company_id
                )
                params = {"discount_rate_min": query.get("discount_rate_min", 0), "discount_rate_max": query.get("discount_rate_max", 100)}
                msg = f"折扣率在 {query.get('discount_rate_min', 0)}% ~ {query.get('discount_rate_max', 100)}% 之间的商品共 {total} 个"

            elif qtype == "fuzzy_search":
                products, total = await self._query_fuzzy(db, query["value"], sort_order, company_id)
                params = {"keyword": query["value"]}
                msg = f"模糊搜索「{query['value']}」的商品共 {total} 个"

            else:
                msg = f"暂不支持的查询类型: {qtype}"

        except Exception as e:
            msg = f"查询出错: {str(e)}"

        if return_raw:
            return {
                "type": qtype,
                "value": value,
                "results": [p.to_dict() for p in products],
                "count": total,
                "message": msg,
            }

        return {
            "query_intent": intent,
            "parsed_params": params,
            "results": [p.to_dict() for p in products],
            "result_count": total,
            "message": msg,
        }

    async def _apply_sort(self, query, model, sort_order: Optional[str]):
        """应用排序"""
        if sort_order == "asc":
            return query.order_by(model.price.asc())
        elif sort_order == "desc":
            return query.order_by(model.price.desc())
        return query.order_by(model.id.desc())

    async def _execute_and_fetch(self, db: AsyncSession, query, company_id: Optional[int] = None) -> tuple:
        """执行查询并返回结果（支持数据隔离：按公司ID，company_id 显式传入，避免并发串号）"""
        if company_id:
            query = query.where(Product.company_id == company_id)
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, len(items)

    # ========== 精确/模糊字段查询 ==========

    async def _query_by_barcode(self, db, barcode: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.barcode_69 == barcode)
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_model(self, db, model: str, sort_order=None, company_id=None):
        q = select(Product).where(
            or_(Product.product_model.ilike(f"%{model}%"), Product.quick_model.ilike(f"%{model}%"))
        )
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_quick_model(self, db, model: str, sort_order=None, fuzzy: bool = True, company_id=None):
        """按快查型号查询（支持模糊匹配，数据隔离）

        库内格式如 "TAA1708 - 启骏"（型号与品牌带空格），用户输入可能为 "TAA1708-启骏"、
        "TAH3220 -启骏" 等空格不一的写法；直接 ILIKE 会漏匹配。因此模糊匹配时
        对查询词与库内值同时去除普通空格/全角空格后再比较。
        """
        model = (model or "").strip()
        if fuzzy:
            like_model = model.replace(" ", "").replace("\u3000", "")
            if not like_model:
                return [], 0
            q = select(Product).where(
                func.replace(func.replace(Product.quick_model, " ", ""), "\u3000", "").ilike(f"%{like_model}%")
            )
        else:
            q = select(Product).where(Product.quick_model == model)
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def execute_batch_model_query(
        self, db: AsyncSession, queries: list, fuzzy: bool = True, company_id: Optional[int] = None
    ) -> dict:
        """批量快查型号查询：每个查询独立执行，返回分组结果（数据隔离）"""
        items = []
        for q_text in queries:
            q_text = q_text.strip()
            if not q_text:
                continue
            products, total = await self._query_by_quick_model(db, q_text, fuzzy=fuzzy, company_id=company_id)
            items.append({
                "query": q_text,
                "results": [p.to_dict() for p in products],
                "count": total,
                "message": f"快查型号包含「{q_text}」的商品共 {total} 个" if total > 0 else f"未找到快查型号包含「{q_text}」的商品",
            })

        total_results = sum(item["count"] for item in items)
        return {
            "total_queries": len(items),
            "total_results": total_results,
            "items": items,
        }

    async def _query_by_brand(self, db, brand: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.brand.ilike(f"%{brand}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_product_name(self, db, name: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.product_name.ilike(f"%{name}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_category_level1(self, db, cat: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.category_level1.ilike(f"%{cat}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_category_level2(self, db, cat: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.category_level2.ilike(f"%{cat}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_category_level3(self, db, cat: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.category_level3.ilike(f"%{cat}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_category(self, db, cat: str, sort_order=None, company_id=None):
        q = select(Product).where(or_(
            Product.category_level1.ilike(f"%{cat}%"),
            Product.category_level2.ilike(f"%{cat}%"),
            Product.category_level3.ilike(f"%{cat}%"),
        ))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_cooperation_level(self, db, level: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.cooperation_level.ilike(f"%{level}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_supply_status(self, db, status: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.supply_status.ilike(f"%{status}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_box_spec(self, db, spec: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.box_spec.ilike(f"%{spec}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_cert_3c(self, db, cert: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.cert_3c.ilike(f"%{cert}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_recommendation(self, db, rec: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.recommendation.ilike(f"%{rec}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_price_update(self, db, pu: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.price_update.ilike(f"%{pu}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    # ========== 价格区间查询 ==========

    async def _query_by_price_range(self, db, pmin: float, pmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.price >= pmin, Product.price <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.price.asc())
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_purchase_price_range(self, db, pmin: float, pmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.purchase_price >= pmin, Product.purchase_price <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.purchase_price.asc())
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_retail_price_range(self, db, pmin: float, pmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.retail_price >= pmin, Product.retail_price <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.retail_price.asc())
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_bid_price_range(self, db, pmin: float, pmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.bid_price >= pmin, Product.bid_price <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.bid_price.asc())
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_group_purchase_price_range(self, db, pmin: float, pmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.group_purchase_price >= pmin, Product.group_purchase_price <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.group_purchase_price.asc())
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_new_event_price_range(self, db, pmin: float, pmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.new_event_price >= pmin, Product.new_event_price <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.new_event_price.asc())
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_negotiation_price_range(self, db, pmin: float, pmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.negotiation_price >= pmin, Product.negotiation_price <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.negotiation_price.asc())
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_shipping_fee_range(self, db, pmin: float, pmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.shipping_fee >= pmin, Product.shipping_fee <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.shipping_fee.asc())
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_gross_weight_range(self, db, wmin: float, wmax: float, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.gross_weight >= wmin, Product.gross_weight <= wmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.gross_weight.asc())
        return await self._execute_and_fetch(db, q, company_id)

    # ========== 数值阈值查询 ==========

    async def _query_by_sales_volume(self, db, sales: int, sort_order=None, company_id=None):
        q = select(Product).where(Product.sales_volume >= sales)
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    # ========== 折扣率查询 ==========

    async def _query_by_discount_rate(self, db, rate_min: float, rate_max: float, sort_order=None, company_id=None):
        """折扣率 = 代发价/零售价，需先查询再在 Python 层过滤（数据隔离：按公司ID）"""
        q = select(Product)
        if company_id:
            q = q.where(Product.company_id == company_id)
        result = await db.execute(q)
        items = list(result.scalars().all())
        filtered = [p for p in items if rate_min <= p.discount_rate <= rate_max]
        if sort_order == "asc":
            filtered.sort(key=lambda p: p.discount_rate)
        elif sort_order == "desc":
            filtered.sort(key=lambda p: p.discount_rate, reverse=True)
        else:
            filtered.sort(key=lambda p: p.discount_rate)
        return filtered, len(filtered)

    # ========== 通用查询 ==========

    async def _query_fuzzy(self, db, keyword: str, sort_order=None, company_id=None):
        """通用模糊搜索：在快查型号/型号/产品名称/品牌/品类/规格/69码/推荐理由/参数中等匹配"""
        q = select(Product).where(or_(
            Product.quick_model.ilike(f"%{keyword}%"),
            Product.product_model.ilike(f"%{keyword}%"),
            Product.product_name.ilike(f"%{keyword}%"),
            Product.brand.ilike(f"%{keyword}%"),
            Product.category_level1.ilike(f"%{keyword}%"),
            Product.category_level2.ilike(f"%{keyword}%"),
            Product.category_level3.ilike(f"%{keyword}%"),
            Product.specification.ilike(f"%{keyword}%"),
            Product.barcode_69.ilike(f"%{keyword}%"),
            Product.recommendation.ilike(f"%{keyword}%"),
            Product.parameters.ilike(f"%{keyword}%"),
            Product.cert_3c.ilike(f"%{keyword}%"),
            Product.remark.ilike(f"%{keyword}%"),
        ))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_barcode_range(self, db, bc_min: str, bc_max: str, sort_order=None, company_id=None):
        q = select(Product).where(and_(Product.barcode_69 >= bc_min, Product.barcode_69 <= bc_max))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_by_spec(self, db, keyword: str, sort_order=None, company_id=None):
        q = select(Product).where(Product.specification.ilike(f"%{keyword}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)

    async def _query_all(self, db, sort_order=None, company_id=None):
        q = select(Product)
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q, company_id)


query_engine = QueryEngine()
