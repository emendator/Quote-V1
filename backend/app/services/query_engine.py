"""智能查询引擎 —— 将解析后的查询意图转化为数据库查询"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.models import Product
from app.services.message_parser import message_parser


class QueryEngine:
    """智能查询引擎"""

    async def execute_smart_query(self, db: AsyncSession, query_text: str) -> Dict[str, Any]:
        """执行智能查询"""
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
                "message": "未能识别查询意图，请尝试输入69码、SKU、规格或价格区间等信息",
                "unrecognized_text": query_text,
            }

        # 2. 分离排序意图和实际查询
        # 将 all_products 视为低优先级查询——只有在没有其他特定查询时才使用
        specific_queries = [q for q in raw_queries if q["type"] not in ("sort_order", "all_products")]
        sort_q = next((q for q in raw_queries if q["type"] == "sort_order"), None)
        all_q = next((q for q in raw_queries if q["type"] == "all_products"), None)

        effective_sort = sort_order or (sort_q["value"] if sort_q else None)

        # 3. 如果有具体的查询条件，优先处理它们
        if specific_queries:
            data_queries = specific_queries
        elif all_q:
            # 只有全量查询时，执行全量查询
            products, total = await self._query_all(db, effective_sort)
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
            return await self._execute_single_query(db, data_queries[0], effective_sort)

        # 5. 处理多个查询（微信群消息场景）
        parsed_queries = []
        all_results = []
        for q in data_queries:
            result = await self._execute_single_query(db, q, effective_sort, return_raw=True)
            parsed_queries.append(result)

        return {
            "query_intent": "mixed",
            "parsed_queries": parsed_queries,
            "results": [],
            "result_count": sum(pq.get("count", 0) for pq in parsed_queries),
            "message": f"识别到 {len(data_queries)} 个查询条件",
        }

    async def _execute_single_query(
        self, db: AsyncSession, query: Dict[str, Any], sort_order: Optional[str] = None, return_raw: bool = False
    ) -> Dict[str, Any]:
        """执行单个查询"""
        qtype = query["type"]
        value = query.get("value", "")

        products = []
        total = 0
        intent = qtype
        params = {}
        msg = ""

        try:
            if qtype == "exact_barcode":
                products, total = await self._query_by_barcode(db, query["value"], sort_order)
                params = {"barcode_69": query["value"]}
                msg = f"已为您找到69码为 {query['value']} 的商品报价" if total > 0 else f"未找到69码为 {query['value']} 的商品"

            elif qtype == "exact_sku":
                products, total = await self._query_by_model(db, query["value"], sort_order)
                params = {"product_model": query["value"]}
                msg = f"已为您找到型号为 {query['value']} 的商品报价" if total > 0 else f"未找到型号为 {query['value']} 的商品"

            elif qtype == "price_range":
                products, total = await self._query_by_price_range(
                    db, query["price_min"], query["price_max"], sort_order
                )
                params = {"price_min": query["price_min"], "price_max": query["price_max"]}
                msg = f"代发价在 {query['price_min']} ~ {query['price_max']} 元之间的商品共 {total} 个"

            elif qtype == "barcode_range":
                products, total = await self._query_by_barcode_range(
                    db, query["barcode_min"], query["barcode_max"], sort_order
                )
                params = {"barcode_min": query["barcode_min"], "barcode_max": query["barcode_max"]}
                msg = f"69码在 {query['barcode_min']} ~ {query['barcode_max']} 之间的商品共 {total} 个"

            elif qtype == "spec_keyword":
                products, total = await self._query_by_spec(db, query["value"], sort_order)
                params = {"spec_keyword": query["value"]}
                msg = f"规格包含「{query['value']}」的商品共 {total} 个"

            elif qtype == "name_search":
                products, total = await self._query_by_model(db, query["value"], sort_order)
                params = {"product_model": query["value"]}
                msg = f"型号匹配「{query['value']}」的商品共 {total} 个" if total > 0 else f"未找到型号包含「{query['value']}」的商品"

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

    async def _execute_and_fetch(self, db: AsyncSession, query) -> tuple:
        """执行查询并返回结果"""
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, len(items)

    async def _query_by_barcode(self, db, barcode: str, sort_order=None):
        q = select(Product).where(Product.barcode_69 == barcode)
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q)

    async def _query_by_model(self, db, model: str, sort_order=None):
        q = select(Product).where(Product.product_model.ilike(f"%{model}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q)

    async def _query_by_price_range(self, db, pmin: float, pmax: float, sort_order=None):
        q = select(Product).where(and_(Product.price >= pmin, Product.price <= pmax))
        if sort_order:
            q = await self._apply_sort(q, Product, sort_order)
        else:
            q = q.order_by(Product.price.asc())
        return await self._execute_and_fetch(db, q)

    async def _query_by_barcode_range(self, db, bc_min: str, bc_max: str, sort_order=None):
        q = select(Product).where(and_(Product.barcode_69 >= bc_min, Product.barcode_69 <= bc_max))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q)

    async def _query_by_spec(self, db, keyword: str, sort_order=None):
        q = select(Product).where(Product.specification.ilike(f"%{keyword}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q)

    async def _query_by_model(self, db, keyword: str, sort_order=None):
        q = select(Product).where(Product.name.ilike(f"%{keyword}%"))
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q)

    async def _query_all(self, db, sort_order=None):
        q = select(Product)
        q = await self._apply_sort(q, Product, sort_order)
        return await self._execute_and_fetch(db, q)


query_engine = QueryEngine()
