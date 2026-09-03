"""组合方案生成引擎 —— 枚举所有满足约束条件的产品组合方案"""
import logging
import itertools
import difflib
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from app.database import sync_engine

logger = logging.getLogger("combination_engine")

# 表示"任意/不限"的商品品类关键词（用于正确识别"任意商品/随意/都可以"等，不应作为真实品类查询）
ARBITRARY_CATEGORY_KEYWORDS = ("任意", "随意", "随便", "都可以", "不限", "任何", "什么都", "全品类",
                             "任意商品", "任意产品", "任何商品", "任何产品", "商品", "全部")


def is_any_category(cat: Optional[str]) -> bool:
    """判断某个品类字符串是否表示"任意/不限"（不是真实品类）。"""
    if not cat:
        return True
    s = cat.strip().replace(" ", "").replace("\u3000", "")
    if not s:
        return True
    if s in ("商品", "全部", "全品类", "不限", "不限品类", "任意", "任意商品", "任意产品",
             "随意", "随便", "都可以", "任何", "任何商品", "任何产品"):
        return True
    if s in ARBITRARY_CATEGORY_KEYWORDS:
        return True
    return any(kw in s for kw in ("任意", "随意", "随便", "都可以", "不限", "任何", "什么都", "全品类"))


# ========== 约束解析结果结构 ==========
# {
#   "total_price": 500,           # 目标总价（约数）
#   "total_quantity": 3,          # 商品数量
#   "max_discount_rate": 70,      # 最大整体折扣率(%)
#   "items": [                    # 每个位置的约束
#     {"category": "电子产品", "price_min": 300, "price_max": null, "brand": null, "specification": null},
#     {"category": "商品", "price_min": null, "price_max": null, "brand": null, "specification": null},
#     {"category": "小家电", "price_min": null, "price_max": null, "brand": null, "specification": null}
#   ]
# }


class CombinationEngine:
    """组合方案生成引擎"""

    MAX_CANDIDATES_PER_SLOT = 50   # 每品类最多候选数
    MAX_SOLUTIONS = 500            # 最大返回方案数
    PRICE_TOLERANCE = 0.20         # "左右"等模糊总价允许偏差 20%
    MAX_ENUMERABLE_COMBOS = 20000  # 允许枚举的最大组合数（超过则动态缩减候选）
    FUZZY_MAX_MATCH = 30           # 放宽变体在全库的匹配数上限，超过则视为过于宽泛不采用（数据驱动，无硬编码关键词）

    def generate(
        self,
        constraints: Dict[str, Any],
        company_id: Optional[int] = None,
        max_solutions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        根据约束条件生成所有可行组合方案

        商品名称匹配策略（完全基于用户输入推导，无硬编码）：
        1. 第一轮：完整关键词精确匹配（如"自拍杆"）
        2. 若精确匹配组合不出方案，自动放宽为渐进变体匹配后重试（如"自拍"可匹配"自拍神器"）

        Args:
            constraints: 约束条件（从 AI 或规则引擎解析）
            company_id: 数据隔离公司ID
            max_solutions: 最多返回方案数（默认用 self.MAX_SOLUTIONS）

        Returns:
            {"solutions": [...], "total_solutions": int, "message": str}
        """
        items_constraints = constraints.get("items", [])
        if not items_constraints:
            return {
                "solutions": [], "total_solutions": 0,
                "message": "未解析出商品组合条件", "diagnosis": [],
            }

        total_price_target = constraints.get("total_price", 0)
        min_discount_rate = constraints.get("min_discount_rate", 0)
        max_discount_rate = constraints.get("max_discount_rate", 100)
        discount_target = constraints.get("discount_target")
        max_solutions = max_solutions or self.MAX_SOLUTIONS
        keywords = constraints.get("keywords", [])
        strict_total_min = constraints.get("price_min")
        strict_total_max = constraints.get("price_max")

        # 计算总价上下界（由操作符决定：price_min/price_max 已由解析层设置）
        if strict_total_min is not None and strict_total_max is not None:
            price_min, price_max = strict_total_min, strict_total_max
        elif strict_total_max is not None:
            # "小于/以内"：仅上限（预算）
            price_min, price_max = 0.0, strict_total_max
        elif strict_total_min is not None:
            # "大于"：仅下限
            price_min, price_max = strict_total_min, float('inf')
        elif total_price_target > 0:
            # 旧逻辑：目标价 ± 容差
            price_min = total_price_target * (1 - self.PRICE_TOLERANCE)
            price_max = total_price_target * (1 + self.PRICE_TOLERANCE)
        else:
            price_min, price_max = 0.0, float('inf')

        def _query() -> List[List[Dict]]:
            """查询各槽位候选：完整关键词精确匹配优先 + 受控模糊补足（区分度守卫防污染）"""
            return [
                self._query_candidates_for_slot(slot, company_id, keywords=keywords, fuzzy=True)[:self.MAX_CANDIDATES_PER_SLOT]
                for slot in items_constraints
            ]

        # 查询各槽位候选并枚举组合
        slot_candidates = _query()
        solutions, was_capped, empty_slots = self._enumerate(
            items_constraints, slot_candidates, price_min, price_max,
            min_discount_rate, max_discount_rate, max_solutions,
            target_total=total_price_target, discount_target=discount_target,
        )

        # 空槽位：数据驱动诊断具体原因（品类无货 / 价格 / 折扣率约束过严）
        if empty_slots:
            diagnosis = self._diagnose_empty_slots(items_constraints, empty_slots, company_id)
            message = self._diagnosis_to_message(diagnosis)
            return {
                "solutions": [],
                "total_solutions": 0,
                "message": message,
                "diagnosis": diagnosis,
            }

        # 生成提示信息
        diagnosis: List[Dict[str, Any]] = []
        if solutions:
            if was_capped and len(solutions) >= max_solutions:
                message = f"候选组合较多，已展示前 {len(solutions)} 个方案供选择"
            else:
                message = f"共找到 {len(solutions)} 个符合条件的组合方案"
        else:
            # 数据驱动诊断无方案原因：逐步放松约束归因，定位是哪个条件导致失败并给出具体调整建议
            diagnosis = self._diagnose_no_solution(
                items_constraints, slot_candidates,
                price_min, price_max,
                min_discount_rate, max_discount_rate,
                company_id=company_id,
            )
            message = self._diagnosis_to_message(diagnosis)
            logger.info(f"组合方案生成无结果: {message}")

        return {
            "solutions": solutions,
            "total_solutions": len(solutions),
            "message": message,
            "diagnosis": diagnosis,
        }

    @staticmethod
    def _diagnosis_to_message(diagnosis: List[Dict[str, Any]]) -> str:
        """将结构化诊断条目列表转为人类可读的摘要文本（供 message 字段 / 日志使用）"""
        if not diagnosis:
            return "无合适方案"
        parts = []
        for d in diagnosis[:3]:
            title = d.get("title", "")
            suggestion = (d.get("suggestion") or "").strip().rstrip("。")
            parts.append(f"{title}：{suggestion}" if suggestion else title)
        return "无合适方案：" + "；".join(parts) + "。请按以上建议调整后重新生成。"

    def _enumerate(
        self,
        items_constraints: List[Dict[str, Any]],
        slot_candidates: List[List[Dict]],
        price_min: float,
        price_max: float,
        min_discount_rate: float,
        max_discount_rate: float,
        max_solutions: int,
        target_total: float = 0,
        discount_target: Optional[float] = None,
    ) -> Tuple[List[Dict], bool, List[int]]:
        """枚举所有组合，返回 (solutions, was_capped, empty_slots)"""
        # 检查是否有空位
        empty_slots = [i for i, cands in enumerate(slot_candidates) if not cands]
        if empty_slots:
            return [], False, empty_slots

        # 组合数过大时，动态缩减每槽候选数，保证能给出部分方案供选择
        total_combos = 1
        for cands in slot_candidates:
            total_combos *= len(cands)
        was_capped = False
        if total_combos > self.MAX_ENUMERABLE_COMBOS:
            slot_candidates, total_combos = self._cap_slot_candidates(slot_candidates, self.MAX_ENUMERABLE_COMBOS)
            was_capped = True

        # 使用 itertools.product 枚举所有组合
        solutions = []
        seen_signatures = set()  # 用于去重
        for combo in itertools.product(*slot_candidates):
            combo_list = list(combo)
            # 同一组合内商品不重复（数量代表"需几件不同商品"，同一商品不能重复使用）
            product_ids = [p.get("id") for p in combo_list]
            if len(set(product_ids)) != len(product_ids):
                continue
            combo_total_price = sum(p.get("price", 0) or 0 for p in combo_list)
            combo_total_qty = sum(p.get("quantity", 1) or 1 for p in combo_list)
            # 匹配度：精确匹配商品越多越靠前（用于排序）
            combo_relevance = sum(p.get("_match_score", 1.0) for p in combo_list)

            # 检查总价约束
            if combo_total_price < price_min or combo_total_price > price_max:
                continue

            # 检查各品类价格约束
            valid = True
            for i, slot in enumerate(items_constraints):
                if i < len(combo_list):
                    p = combo_list[i]
                    if slot.get("price_min") is not None and (p.get("price") or 0) < slot["price_min"]:
                        valid = False
                        break
                    if slot.get("price_max") is not None and (p.get("price") or 0) > slot["price_max"]:
                        valid = False
                        break
            if not valid:
                continue

            # 计算整体折扣率（price / retail_price 的平均值）
            total_discount = 0
            discount_count = 0
            for p in combo_list:
                retail = p.get("retail_price") or 0
                price = p.get("price") or 0
                if retail > 0:
                    total_discount += price / retail * 100
                    discount_count += 1
            avg_discount = round(total_discount / discount_count, 2) if discount_count > 0 else 0

            if avg_discount < min_discount_rate or avg_discount > max_discount_rate:
                continue

            # 去重：同一组商品（相同 quick_model 集合）只保留一个方案
            qms = sorted(p.get("quick_model", "") or "" for p in combo_list)
            sig = tuple(qms)
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)

            # 构建方案（包含产品库全部字段，供列显示配置使用）
            solution_items = []
            for p in combo_list:
                solution_items.append({
                    "product_id": p.get("id"),
                    "company_name": p.get("company_name", ""),
                    "quick_model": p.get("quick_model", ""),
                    "product_model": p.get("product_model", ""),
                    "product_name": p.get("product_name", ""),
                    "brand": p.get("brand", ""),
                    "category_level1": p.get("category_level1", ""),
                    "category_level2": p.get("category_level2", ""),
                    "category_level3": p.get("category_level3", ""),
                    "negotiation_price": p.get("negotiation_price", 0),
                    "price_update": p.get("price_update", ""),
                    "last_purchase_price": p.get("last_purchase_price", 0),
                    "purchase_price": p.get("purchase_price", 0),
                    "retail_price": p.get("retail_price", 0),
                    "new_event_price": p.get("new_event_price", 0),
                    "group_purchase_price": p.get("group_purchase_price", 0),
                    "bid_price": p.get("bid_price", 0),
                    "price": p.get("price", 0),
                    "gross_weight": p.get("gross_weight", 0),
                    "box_spec": p.get("box_spec", ""),
                    "cooperation_level": p.get("cooperation_level", ""),
                    "supply_status": p.get("supply_status", ""),
                    "specification": p.get("specification", ""),
                    "remark": p.get("remark", ""),
                    "shipping_fee": p.get("shipping_fee", 0),
                    "barcode_69": p.get("barcode_69", ""),
                    "sales_volume": p.get("sales_volume", 0),
                    "recommendation": p.get("recommendation", ""),
                    "parameters": p.get("parameters", ""),
                    "cert_3c": p.get("cert_3c", ""),
                    "discount_rate": p.get("discount_rate", 0),
                    "shop_url": p.get("shop_url", ""),
                    "image": p.get("image", ""),
                    "created_at": p.get("created_at", ""),
                    "quantity": 1,
                    "subtotal": p.get("price", 0),
                })

            solutions.append({
                "total_price": round(combo_total_price, 2),
                "total_quantity": combo_total_qty,
                "total_discount_rate": avg_discount,
                "items": solution_items,
                "_relevance": combo_relevance,
            })

            if len(solutions) >= max_solutions:
                break

        # 排序：优先展示总价最接近用户输入目标的方案（无论大于/小于/左右），
        # 总价相同时看总折扣率是否贴近用户输入，再比匹配度与总价
        target = float(target_total) if target_total else 0
        disc_target = float(discount_target) if discount_target is not None else None
        if target > 0 or disc_target is not None:
            solutions.sort(key=lambda s: (
                abs(s["total_price"] - target) if target > 0 else 0.0,
                abs(s["total_discount_rate"] - disc_target) if disc_target is not None else 0.0,
                -s.get("_relevance", 0),
                s["total_price"],
            ))
        else:
            solutions.sort(key=lambda s: (-s.get("_relevance", 0), s["total_price"]))
        # 移除内部字段
        for s in solutions:
            s.pop("_relevance", None)
        return solutions, was_capped, []

    def _stat_combos(
        self,
        slot_candidates: List[List[Dict]],
        price_min: float,
        price_max: float,
        min_discount_rate: float,
        max_discount_rate: float,
    ) -> Dict[str, Any]:
        """轻量统计：遍历候选组合，统计满足给定约束的组合的总价/折扣率范围。

        用于无方案时的数据驱动诊断：不构建完整方案对象，只统计
        count / min_total / max_total / min_discount / max_discount，
        从而根据实际商品数据给出可执行的调整建议。
        """
        stats: Dict[str, Any] = {
            "count": 0,
            "min_total": None, "max_total": None,
            "min_discount": None, "max_discount": None,
        }
        if not slot_candidates:
            return stats

        cands = slot_candidates
        total_combos = 1
        for c in cands:
            total_combos *= len(c)
        # 组合数过大时按与真实枚举相同的规则缩减候选，保证统计可完成（近似值用于建议）
        if total_combos > self.MAX_ENUMERABLE_COMBOS:
            cands, _ = self._cap_slot_candidates(cands, self.MAX_ENUMERABLE_COMBOS)

        for combo in itertools.product(*cands):
            combo_list = list(combo)
            # 与真实枚举一致：组合内商品必须互不相同
            product_ids = [p.get("id") for p in combo_list]
            if len(set(product_ids)) != len(product_ids):
                continue
            combo_total = sum(float(p.get("price") or 0) for p in combo_list)
            if combo_total < price_min or combo_total > price_max:
                continue
            total_discount = 0.0
            discount_count = 0
            for p in combo_list:
                retail = float(p.get("retail_price") or 0)
                price = float(p.get("price") or 0)
                if retail > 0:
                    total_discount += price / retail * 100
                    discount_count += 1
            avg_discount = round(total_discount / discount_count, 2) if discount_count > 0 else 0.0
            if avg_discount < min_discount_rate or avg_discount > max_discount_rate:
                continue

            stats["count"] += 1
            if stats["min_total"] is None or combo_total < stats["min_total"]:
                stats["min_total"] = round(combo_total, 2)
            if stats["max_total"] is None or combo_total > stats["max_total"]:
                stats["max_total"] = round(combo_total, 2)
            if stats["min_discount"] is None or avg_discount < stats["min_discount"]:
                stats["min_discount"] = avg_discount
            if stats["max_discount"] is None or avg_discount > stats["max_discount"]:
                stats["max_discount"] = avg_discount
        return stats

    @staticmethod
    def _has_distinct_assignment(candidate_sets: List[set]) -> bool:
        """判断是否能为每个槽位分配一个互不相同的商品（二分图最大匹配）。

        组合内商品必须互不相同：若无法为所有槽位找到一组互不相同的商品，
        则无论总价/总折扣率如何放宽，都不可能组合出方案。
        """
        match_to_slot: Dict[int, int] = {}

        def dfs(slot: int, visited: set) -> bool:
            for pid in candidate_sets[slot]:
                if pid in visited:
                    continue
                visited.add(pid)
                if pid not in match_to_slot or dfs(match_to_slot[pid], visited):
                    match_to_slot[pid] = slot
                    return True
            return False

        for i in range(len(candidate_sets)):
            if not dfs(i, set()):
                return False
        return True

    def _similar_categories(self, cat: str, company_id: Optional[int] = None, top: int = 3) -> List[str]:
        """模糊查找与给定品类最接近的数据库中已有三级品类，用于空槽位建议。

        完全基于商品库实际数据（无硬编码）：优先匹配包含关系，再用相似度排序。
        """
        if not cat or not cat.strip():
            return []
        try:
            sql = "SELECT DISTINCT category_level3 FROM products WHERE category_level3 IS NOT NULL AND TRIM(category_level3) != ''"
            params = {}
            if company_id:
                sql += " AND company_id = :company_id"
                params["company_id"] = company_id
            with sync_engine.connect() as conn:
                rows = conn.execute(text(sql), params).fetchall()
        except Exception:
            return []
        names = [r[0] for r in rows if r[0]]
        scored = []
        cat_key = cat.replace(" ", "").replace("　", "")
        for name in names:
            name_key = name.replace(" ", "").replace("　", "")
            if cat_key and (cat_key in name_key or name_key in cat_key):
                score = 1.0
            else:
                score = difflib.SequenceMatcher(None, cat, name).ratio()
            if score >= 0.3:
                scored.append((score, name))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [name for _, name in scored[:top]]

    def _diagnose_empty_slots(
        self,
        items_constraints: List[Dict[str, Any]],
        empty_slots: List[int],
        company_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """诊断空槽位原因：是品类本身无货，还是该品类的价格/折扣率限制过严。

        返回结构化诊断条目列表（{type, title, detail, suggestion}），供前端渲染智能诊断面板。
        数据驱动：对每个空槽位，去掉价格/折扣率约束重新查询候选，对比实际数据定位具体原因。
        """
        diagnosis: List[Dict[str, Any]] = []
        for i in empty_slots:
            slot = items_constraints[i]
            cat = slot.get("category_level3") or slot.get("category") or f"第 {i + 1} 个品类"
            # 只保留品类匹配条件（去掉价格/折扣率约束），看品类本身是否有货
            relaxed_slot = {k: v for k, v in slot.items()
                            if k not in ("price_min", "price_max", "discount_min", "discount_max")}
            base_cands = self._query_candidates_for_slot(relaxed_slot, company_id, fuzzy=True)

            if not base_cands:
                # 尝试仅保留品类条件，判断是品类无货，还是品牌/规格等附加限制导致
                cat_only_slot = {k: v for k, v in slot.items() if k in ("category_level3", "category")}
                cat_only_cands = self._query_candidates_for_slot(cat_only_slot, company_id, fuzzy=True) if cat_only_slot else []
                if cat_only_cands:
                    cond_names = []
                    if slot.get("brand"):
                        cond_names.append("品牌")
                    if slot.get("specification"):
                        cond_names.append("规格")
                    if slot.get("keyword"):
                        cond_names.append("商品名称关键词")
                    cond_txt = "、".join(cond_names) if cond_names else "品牌/规格/商品名称关键词"
                    diagnosis.append({
                        "type": "slot_attr",
                        "title": f"第 {i + 1} 个品类「{cat}」的{cond_txt}限制过严",
                        "detail": (
                            f"该品类本身有可用商品（{len(cat_only_cands)} 个），"
                            f"但在当前{cond_txt}条件下没有匹配商品。"
                        ),
                        "suggestion": f"请去掉或放宽{cond_txt}限制，或更换{cond_txt}。",
                    })
                    continue

                # 品类本身无匹配商品
                suggestion = "更换品类，或检查该品类的商品数据。"
                similar = self._similar_categories(cat, company_id)
                if similar:
                    suggestion = (
                        f"该品类在商品库中可能不存在或名称不一致；"
                        f"与目标最接近的三级品类有：{'、'.join(similar)}。"
                        f"可考虑更换为其中之一，或检查该品类的商品数据。"
                    )
                diagnosis.append({
                    "type": "empty_slot",
                    "title": f"第 {i + 1} 个品类「{cat}」暂无可用商品",
                    "detail": (
                        f"该品类在商品库中未找到匹配商品（可能是品类名称与商品库中的三级品类不完全一致，"
                        f"或该品类下暂未导入商品）。"
                    ),
                    "suggestion": suggestion,
                    "adjust": {"field": "category", "slot_index": i},
                })
                continue

            # 品类有货 → 进一步定位：仅价格约束 / 仅折扣率约束
            prices = [float(c.get("price") or 0) for c in base_cands]
            discount_rates = []
            for c in base_cands:
                retail = float(c.get("retail_price") or 0)
                price = float(c.get("price") or 0)
                if retail > 0:
                    discount_rates.append(round(price / retail * 100, 2))

            has_price_cond = slot.get("price_min") is not None or slot.get("price_max") is not None
            has_disc_cond = slot.get("discount_min") is not None or slot.get("discount_max") is not None

            price_cands = base_cands
            if has_price_cond:
                price_slot = dict(relaxed_slot)
                if slot.get("price_min") is not None:
                    price_slot["price_min"] = slot["price_min"]
                if slot.get("price_max") is not None:
                    price_slot["price_max"] = slot["price_max"]
                price_cands = self._query_candidates_for_slot(price_slot, company_id, fuzzy=True)

            disc_cands = base_cands
            if has_disc_cond:
                disc_slot = dict(relaxed_slot)
                if slot.get("discount_min") is not None:
                    disc_slot["discount_min"] = slot["discount_min"]
                if slot.get("discount_max") is not None:
                    disc_slot["discount_max"] = slot["discount_max"]
                disc_cands = self._query_candidates_for_slot(disc_slot, company_id, fuzzy=True)

            if has_price_cond and not price_cands and prices:
                lo_p, hi_p = min(prices), max(prices)
                diagnosis.append({
                    "type": "slot_price",
                    "title": f"第 {i + 1} 个品类「{cat}」价格限制过严",
                    "detail": f"您设置的价格限制与商品库不符：该品类商品价格在 {lo_p}~{hi_p} 元之间。",
                    "suggestion": f"将价格上限/下限调整到 {lo_p}~{hi_p} 元范围内。",
                    "adjust": {"field": "price", "slot_index": i, "value": hi_p, "op": "lt"},
                })
            if has_disc_cond and not disc_cands and discount_rates:
                lo_d, hi_d = min(discount_rates), max(discount_rates)
                diagnosis.append({
                    "type": "slot_discount",
                    "title": f"第 {i + 1} 个品类「{cat}」折扣率限制过严",
                    "detail": f"您设置的折扣率限制与商品库不符：该品类商品折扣率在 {lo_d}%~{hi_d}% 之间。",
                    "suggestion": f"将折扣率上限/下限调整到 {lo_d}%~{hi_d}% 范围内。",
                    "adjust": {"field": "discount", "slot_index": i, "value": hi_d, "op": "lt"},
                })
            if not diagnosis or not any(
                d.get("title", "").startswith(f"第 {i + 1} 个品类") for d in diagnosis
            ):
                # 约束单独都能匹配、但组合后仍为空——罕见情况，给出通用指引
                diagnosis.append({
                    "type": "empty_slot",
                    "title": f"第 {i + 1} 个品类「{cat}」未找到匹配商品",
                    "detail": "该品类在商品库中未找到满足条件的商品。",
                    "suggestion": "检查品类名称，或放宽限制。",
                })

        return diagnosis

    def _diagnose_no_solution(
        self,
        items_constraints: List[Dict[str, Any]],
        slot_candidates: List[List[Dict]],
        price_min: float,
        price_max: float,
        min_discount_rate: float,
        max_discount_rate: float,
        company_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """数据驱动诊断：定位导致"无合适方案"的约束条件，返回结构化诊断条目列表。

        完全基于实际候选商品数据（slot_candidates 来自数据库查询），无任何硬编码：
        1. 总折扣率归因：放松总折扣率后若有组合 → 说明是总折扣率限制过严，给出可调整到的折扣率值；
        2. 总价归因：放松总价后若有组合 → 说明是总价限制过严，给出可调整到的总价值；
        3. 槽位归因：逐槽位对比"限制值 vs 该品类商品实际价格/折扣率范围"，定位过严的商品级约束；
        4. 数量归因：同一三级品类按数量展开成多个槽位时，若该品类可选的不同商品数 < 需求件数，说明"数量要求过高"导致无法组合出互不相同的商品；
        5. 分配归因：对全部槽位做"互不相同商品"的最大匹配，若匹配无解，说明各槽位候选过小或相互重合，无法为每个槽位分配不同商品；
        6. 兜底：若仍无法定位到单一冲突，给出各品类可选商品数量/约束的汇总，并指出最可能"卡脖子"的品类及具体放宽方向。

        返回 [{type, title, detail, suggestion}, ...]，供前端渲染"智能诊断"面板。
        """
        diagnosis: List[Dict[str, Any]] = []

        # ---- 1. 总折扣率归因（先看全局折扣率限制）----
        if min_discount_rate > 0 or max_discount_rate < 100:
            relaxed = self._stat_combos(slot_candidates, price_min, price_max, 0.0, 100.0)
            if relaxed["count"] > 0:
                if relaxed["max_discount"] < min_discount_rate:
                    diagnosis.append({
                        "type": "total_discount",
                        "title": "总折扣率要求过高",
                        "detail": (
                            f"当前商品组合的总折扣率最高只能达到 {relaxed['max_discount']}%，"
                            f"未达到您要求的 {min_discount_rate}%。"
                        ),
                        "suggestion": (
                            f"将总折扣率要求调低到 {relaxed['max_discount']}% 或以下，"
                            f"或改选折扣率更高的商品。"
                        ),
                        "adjust": {"field": "total_discount", "value": relaxed["max_discount"], "op": "lt"},
                    })
                elif relaxed["min_discount"] > max_discount_rate:
                    diagnosis.append({
                        "type": "total_discount",
                        "title": "总折扣率要求过低",
                        "detail": (
                            f"当前商品组合的总折扣率最低也有 {relaxed['min_discount']}%，"
                            f"高于您要求的 {max_discount_rate}%。"
                        ),
                        "suggestion": (
                            f"将总折扣率要求调高到 {relaxed['min_discount']}% 或以上，"
                            f"或改选折扣率更低的商品。"
                        ),
                        "adjust": {"field": "total_discount", "value": relaxed["min_discount"], "op": "gt"},
                    })

        # ---- 2. 总价归因 ----
        if price_min > 0 or price_max != float('inf'):
            relaxed = self._stat_combos(slot_candidates, 0.0, float('inf'), min_discount_rate, max_discount_rate)
            if relaxed["count"] > 0:
                if relaxed["min_total"] > price_max:
                    diagnosis.append({
                        "type": "total_price",
                        "title": "总价预算过低",
                        "detail": (
                            f"当前条件下最低组合总价也要 {relaxed['min_total']} 元，"
                            f"超出总价上限 {price_max} 元。"
                        ),
                        "suggestion": (
                            f"将总价上限提高到 {relaxed['min_total']} 元，"
                            f"或放宽某个商品的价格限制。"
                        ),
                        "adjust": {"field": "total_price", "value": relaxed["min_total"], "op": "lt"},
                    })
                elif relaxed["max_total"] < price_min:
                    diagnosis.append({
                        "type": "total_price",
                        "title": "总价要求过高",
                        "detail": (
                            f"当前条件下最高组合总价也只有 {relaxed['max_total']} 元，"
                            f"未达到总价下限 {price_min} 元。"
                        ),
                        "suggestion": (
                            f"将总价下限调低到 {relaxed['max_total']} 元，"
                            f"或增加商品数量。"
                        ),
                        "adjust": {"field": "total_price", "value": relaxed["max_total"], "op": "gt"},
                    })

        # ---- 3. 槽位归因：定位过严的品类级价格/折扣率约束 ----
        for i, slot in enumerate(items_constraints):
            if i >= len(slot_candidates) or not slot_candidates[i]:
                continue  # 空槽位已在调用方单独处理
            cat = slot.get("category_level3") or slot.get("category") or f"第 {i + 1} 个品类"
            cands = slot_candidates[i]
            prices = [float(c.get("price") or 0) for c in cands]
            discount_rates = []
            for c in cands:
                retail = float(c.get("retail_price") or 0)
                price = float(c.get("price") or 0)
                if retail > 0:
                    discount_rates.append(round(price / retail * 100, 2))

            if slot.get("price_min") is not None and prices:
                actual_max = max(prices)
                if actual_max < float(slot["price_min"]):
                    diagnosis.append({
                        "type": "slot_price",
                        "title": f"第 {i + 1} 个品类「{cat}」价格下限过高",
                        "detail": (
                            f"您要求该品类价格不低于 {slot['price_min']} 元，"
                            f"但该品类商品最高价仅 {actual_max} 元。"
                        ),
                        "suggestion": f"将价格下限降到 {actual_max} 元或以下。",
                        "adjust": {"field": "price", "slot_index": i, "value": actual_max, "op": "lt"},
                    })
            if slot.get("price_max") is not None and prices:
                actual_min = min(prices)
                if actual_min > float(slot["price_max"]):
                    diagnosis.append({
                        "type": "slot_price",
                        "title": f"第 {i + 1} 个品类「{cat}」价格上限过低",
                        "detail": (
                            f"您要求该品类价格不超过 {slot['price_max']} 元，"
                            f"但该品类商品最低价也要 {actual_min} 元。"
                        ),
                        "suggestion": f"将价格上限提高到 {actual_min} 元或以上。",
                        "adjust": {"field": "price", "slot_index": i, "value": actual_min, "op": "gt"},
                    })
            if slot.get("discount_min") is not None and discount_rates:
                actual_max_dr = max(discount_rates)
                if actual_max_dr < float(slot["discount_min"]):
                    diagnosis.append({
                        "type": "slot_discount",
                        "title": f"第 {i + 1} 个品类「{cat}」折扣率下限过高",
                        "detail": (
                            f"您要求该品类折扣率不低于 {slot['discount_min']}%，"
                            f"但该品类商品最高折扣率仅 {actual_max_dr}%。"
                        ),
                        "suggestion": f"将折扣率下限降到 {actual_max_dr}% 或以下。",
                        "adjust": {"field": "discount", "slot_index": i, "value": actual_max_dr, "op": "lt"},
                    })
            if slot.get("discount_max") is not None and discount_rates:
                actual_min_dr = min(discount_rates)
                if actual_min_dr > float(slot["discount_max"]):
                    diagnosis.append({
                        "type": "slot_discount",
                        "title": f"第 {i + 1} 个品类「{cat}」折扣率上限过低",
                        "detail": (
                            f"您要求该品类折扣率不超过 {slot['discount_max']}%，"
                            f"但该品类商品最低折扣率也有 {actual_min_dr}%。"
                        ),
                        "suggestion": f"将折扣率上限提高到 {actual_min_dr}% 或以上。",
                        "adjust": {"field": "discount", "slot_index": i, "value": actual_min_dr, "op": "gt"},
                    })

        if diagnosis:
            return diagnosis

        # ---- 4. 同一三级品类按数量展开后可选商品不足归因 ----
        # 组合内商品必须互不相同：若某三级品类需要 N 件（数量展开成 N 个槽位），
        # 则该品类在当前价格/折扣率条件下必须至少有 N 个不同的可选商品，否则必然无解。
        cat_groups: Dict[str, List[int]] = {}
        for i, slot in enumerate(items_constraints):
            cat_key = slot.get("category_level3") or slot.get("category") or ""
            if not cat_key:
                continue
            cat_groups.setdefault(cat_key, []).append(i)

        group_diag: List[Dict[str, Any]] = []
        for cat, idxs in cat_groups.items():
            if len(idxs) < 2:
                continue
            need = len(idxs)
            distinct_ids: set = set()
            prices: set = set()
            for i in idxs:
                if i < len(slot_candidates):
                    for c in slot_candidates[i]:
                        distinct_ids.add(c.get("id"))
                        prices.add(float(c.get("price") or 0))
            if len(distinct_ids) >= need:
                continue
            available = len(distinct_ids)
            price_txt = f"价格 {min(prices)}~{max(prices)} 元" if prices else "价格不限"
            first_idx = min(idxs)
            group_diag.append({
                "type": "slot_quantity",
                "title": f"第 {idxs[0] + 1}-{idxs[-1] + 1} 个品类「{cat}」可选商品数量不足",
                "detail": (
                    f"您要求该三级品类共 {need} 件（数量 {need}），"
                    f"但在当前价格/折扣率条件下符合的商品只有 {available} 个不同商品"
                    f"（{price_txt}），同一商品不能重复使用，因此不足以组成 {need} 个互不相同的商品。"
                ),
                "suggestion": (
                    f"请将「{cat}」的数量调整为 {available} 件或更少；"
                    f"或放宽该品类的价格/折扣率限制，以增加可选商品数量；"
                    f"或更换为可选商品更多的三级品类。"
                ),
                "adjust": {"field": "quantity", "slot_index": first_idx, "value": available, "op": "lt"},
            })

        if group_diag:
            return group_diag

        # ---- 5. 全局"互不相同"分配冲突归因 ----
        # 即使每个品类单独看都有商品，多个槽位的候选集合也可能过小或相互重合，
        # 导致无法为所有槽位分配一组互不相同的商品（二分图匹配无解）。
        candidate_sets = [set(c.get("id") for c in cands) for cands in slot_candidates]
        if not self._has_distinct_assignment(candidate_sets):
            all_ids: set = set()
            for s in candidate_sets:
                all_ids |= s
            sizes = [len(s) for s in candidate_sets]
            min_size = min(sizes) if sizes else 0
            tight_idxs = [i for i, s in enumerate(candidate_sets) if len(s) == min_size]
            tight_names = []
            for i in tight_idxs:
                slot = items_constraints[i]
                name = slot.get("category_level3") or slot.get("category") or f"第 {i + 1} 个品类"
                tight_names.append(f"第 {i + 1} 个品类「{name}」")
            tight_desc = "、".join(tight_names[:3])
            if len(tight_names) > 3:
                tight_desc += " 等"
            detail = (
                f"当前各商品位可选的去重商品共 {len(all_ids)} 个，而需要组成 {len(items_constraints)} 个互不相同的商品；"
                f"且候选中存在过少或相互重合的商品位（可选商品最少为：{tight_desc}），"
                f"无法为每个商品位分配到互不相同的商品。"
            )
            suggestion = (
                f"请减少商品数量；或放宽这些商品位的价格/折扣率限制以增加可选商品；"
                f"或更换为可选商品更多的品类；若同一品类数量较大，可适当降低该品类数量。"
            )
            return [{
                "type": "assignment",
                "title": "可选商品无法分配到各商品位（互不相同）",
                "detail": detail,
                "suggestion": suggestion,
            }]

        # ---- 6. 兜底：给出具体、可执行的调整方向（而不是一句空泛的"放宽限制"） ----
        slot_desc_parts = []
        counts = []
        for i, slot in enumerate(items_constraints):
            cat = slot.get("category_level3") or slot.get("category") or f"第 {i + 1} 个品类"
            n = len(slot_candidates[i]) if i < len(slot_candidates) else 0
            counts.append(n)
            conds = []
            if slot.get("price_min") is not None:
                conds.append(f"价格≥{slot['price_min']}元")
            if slot.get("price_max") is not None:
                conds.append(f"价格≤{slot['price_max']}元")
            if slot.get("discount_min") is not None:
                conds.append(f"折扣率≥{slot['discount_min']}%")
            if slot.get("discount_max") is not None:
                conds.append(f"折扣率≤{slot['discount_max']}%")
            cond_txt = "，".join(conds) if conds else "无价格/折扣率限制"
            slot_desc_parts.append(f"{cat}（可选{n}个，{cond_txt}）")
        summary = "；".join(slot_desc_parts)

        total_req_parts = []
        if price_min > 0:
            total_req_parts.append(f"总价≥{price_min}元")
        if price_max != float('inf'):
            total_req_parts.append(f"总价≤{price_max}元")
        if min_discount_rate > 0:
            total_req_parts.append(f"总折扣率≥{min_discount_rate}%")
        if max_discount_rate < 100:
            total_req_parts.append(f"总折扣率≤{max_discount_rate}%")
        total_req_txt = "、".join(total_req_parts) if total_req_parts else "无总价/折扣率要求"

        # 定位可选商品最少的品类（最可能"卡脖子"），给出针对性的放宽方向
        tight_cat = None
        min_n = 0
        if counts:
            min_n = min(counts)
            tight_idx = counts.index(min_n)
            tight_slot = items_constraints[tight_idx]
            tight_cat = tight_slot.get("category_level3") or tight_slot.get("category") or f"第 {tight_idx + 1} 个品类"

        # 统计"在满足各品类约束下"可行的总价/折扣率范围，让兜底建议更具体
        feasible = self._stat_combos(slot_candidates, 0.0, float('inf'), 0.0, 100.0)
        feasible_parts = []
        if feasible.get("min_total") is not None:
            feasible_parts.append(f"总价 {feasible['min_total']}~{feasible['max_total']} 元")
        if feasible.get("min_discount") is not None:
            feasible_parts.append(f"总折扣率 {feasible['min_discount']}%~{feasible['max_discount']}%")
        feasible_txt = "；".join(feasible_parts) if feasible_parts else "无可行组合"

        detail = (
            f"各品类可选商品及约束如下：{summary}。"
            f"在满足上述各品类约束的前提下，当前可组合的总价/折扣率范围为「{feasible_txt}」，"
            f"而您要求「{total_req_txt}」，两者无法同时满足。"
        )
        if tight_cat:
            suggestion = (
                f"「{tight_cat}」当前仅可选 {min_n} 个商品，是导致无法组合的关键瓶颈："
                f"请放宽该品类的价格/折扣率限制（或更换为可选商品更多的品类），"
                f"或减少该品类的数量；同时请将总价/总折扣率调整到当前可行范围（{feasible_txt}）内，"
                f"或适当放宽总价（当前要求：{total_req_txt}）与总折扣率。"
            )
        else:
            suggestion = (
                f"请将总价/总折扣率调整到当前可行范围（{feasible_txt}）内；"
                f"当前总价要求为「{total_req_txt}」，若无法满足，请放宽总价或总折扣率，"
                f"并放宽可选商品最少品类的价格/折扣率限制。"
            )
        return [{
            "type": "general",
            "title": "组合条件相互冲突",
            "detail": detail,
            "suggestion": suggestion,
        }]

    def _cap_slot_candidates(
        self,
        slot_candidates: List[List[Dict]],
        max_combos: int,
    ) -> Tuple[List[List[Dict]], int]:
        """动态缩减每槽候选数，使组合总数不超过 max_combos，保证能枚举出部分方案"""
        n = len(slot_candidates)
        if n == 0:
            return slot_candidates, 0

        # 粗略目标：每槽候选数为 max_combos 的 n 次方根
        per_slot_target = max(1, int(max_combos ** (1.0 / n)))
        sizes = [min(len(c), per_slot_target) for c in slot_candidates]

        # 若仍超限，从最大的槽开始逐步减半
        while True:
            total = 1
            for s in sizes:
                total *= s
            if total <= max_combos or max(sizes) <= 1:
                break
            idx = sizes.index(max(sizes))
            sizes[idx] = max(1, sizes[idx] // 2)

        # 应用裁剪：分层采样（保留首尾 + 中间均匀抽样），避免只保留最便宜候选导致总价目标无法达成
        capped = [self._spread_sample(slot_candidates[i], sizes[i]) for i in range(n)]
        total = 1
        for s in sizes:
            total *= s
        return capped, total

    @staticmethod
    def _keyword_variants(kw: str) -> List[str]:
        """生成关键词渐进放宽变体：完整词 + 逐字去掉末尾（至少保留2字）

        例如 "自拍杆" → ["自拍杆", "自拍"]，可匹配到 "自拍神器" 等同义商品；
        完全根据用户输入推导，无任何硬编码关键词。
        """
        cur = kw.strip().replace(" ", "").replace("\u3000", "")
        variants = []
        while len(cur) >= 2:
            variants.append(cur)
            cur = cur[:-1]
        return variants

    def _variant_is_specific(self, variant: str, company_id: Optional[int] = None) -> bool:
        """判断放宽变体是否足够具体

        若该变体在全库匹配数超过 FUZZY_MAX_MATCH，说明过于宽泛（如"充电"匹配到大量充电器），
        此时不采用放宽匹配，避免把不相关商品混入候选。完全基于数据统计，无硬编码。
        """
        sql_cond, params = self._keyword_condition_sql("vs", [variant])
        where = sql_cond
        if company_id:
            where = "({}) AND company_id = :company_id".format(sql_cond)
            params["company_id"] = company_id
        sql = "SELECT COUNT(*) FROM products WHERE {}".format(where)
        try:
            with sync_engine.connect() as conn:
                cnt = conn.execute(text(sql), params).scalar() or 0
            return cnt <= self.FUZZY_MAX_MATCH
        except Exception as e:
            logger.warning(f"检查放宽变体区分度失败: {e}")
            return False

    @staticmethod
    def _keyword_condition_sql(param_prefix: str, variants: List[str]) -> tuple:
        """构建商品名称模糊匹配 SQL（忽略空格），返回 (sql, params)

        对名称/型号/品牌/规格各字段，只要命中任一变体即视为匹配
        """
        fields = ["product_name", "quick_model", "product_model", "brand", "specification"]
        field_parts = []
        params = {}
        for fi, f in enumerate(fields):
            v_parts = []
            for vi, v in enumerate(variants):
                p = "{}_{}_{}".format(param_prefix, fi, vi)
                v_parts.append(
                    "REPLACE(REPLACE({f}, ' ', ''), '\u3000', '') LIKE :{p}".format(f=f, p=p)
                )
                params[p] = "%{}%".format(v)
            field_parts.append("(" + " OR ".join(v_parts) + ")")
        return "(" + " OR ".join(field_parts) + ")", params

    @staticmethod
    def _spread_sample(items: List[Dict], k: int) -> List[Dict]:
        """对候选列表做分层采样：保留首尾各若干 + 中间均匀抽样，覆盖价位区间。

        用于"任意商品"槽位及候选数超限时的缩减，避免只保留最便宜的一批而导致
        较高总价目标无法达成。
        """
        n = len(items)
        if n <= k:
            return list(items)
        if k <= 3:
            return items[:k]
        head = max(1, k // 5)
        tail = max(1, k // 5)
        body_n = k - head - tail
        if body_n <= 0:
            return items[:k]
        body = items[head:n - tail]
        step = max(1, len(body) // body_n)
        return (items[:head] + body[::step][:body_n] + items[n - tail:])[:k]

    def _query_any_candidates(self, company_id: Optional[int] = None) -> List[Dict]:
        """查询"任意商品"槽位的候选：在全部有价格商品中做分层采样。

        覆盖低价/中价/高价，使"任意三个产品凑500元"这类需求能够选中合适商品。
        """
        sql = "SELECT * FROM products WHERE COALESCE(price, 0) > 0"
        params = {}
        if company_id:
            sql += " AND company_id = :company_id"
            params["company_id"] = company_id
        sql += " ORDER BY price ASC"
        try:
            with sync_engine.connect() as conn:
                rows = conn.execute(text(sql), params).fetchall()
                if not rows:
                    return []
                columns = [col[1] for col in conn.execute(text("PRAGMA table_info(products)")).fetchall()]
        except Exception as e:
            logger.warning(f"查询任意商品候选失败: {e}")
            return []
        products = [dict(zip(columns, row)) for row in rows]
        return self._spread_sample(products, self.MAX_CANDIDATES_PER_SLOT)

    def _query_candidates_for_slot(
        self,
        slot: Dict[str, Any],
        company_id: Optional[int] = None,
        keywords: Optional[List[str]] = None,
        fuzzy: bool = True,
    ) -> List[Dict]:
        """查询某个品类槽位的候选商品

        商品名称关键词策略（完全基于用户输入推导，无任何硬编码关键词）：
        - fuzzy=False：仅完整关键词精确匹配（如"自拍杆"）
        - fuzzy=True：精确匹配优先 + 渐进放宽变体补足（如"自拍"可匹配"自拍神器"）
        """
        conditions = []
        params = {}

        # 三级品类（前端从三级品类列表选择，精确匹配）
        # "任意/随意/都可以"等表示"任意商品"，不应作为真实品类查询
        if slot.get("category_level3") and not is_any_category(slot["category_level3"]):
            conditions.append("category_level3 = :cat3")
            params["cat3"] = slot["category_level3"]

        if slot.get("category") and not is_any_category(slot["category"]):
            cat = slot["category"]
            conditions.append(
                "(category_level1 LIKE :cat OR category_level2 LIKE :cat OR category_level3 LIKE :cat)"
            )
            params["cat"] = f"%{cat}%"

        if slot.get("brand"):
            conditions.append("brand LIKE :brand")
            params["brand"] = f"%{slot['brand']}%"

        if slot.get("specification"):
            conditions.append("specification LIKE :spec")
            params["spec"] = f"%{slot['specification']}%"

        if slot.get("price_min") is not None:
            conditions.append("price >= :pmin")
            params["pmin"] = slot["price_min"]

        if slot.get("price_max") is not None:
            conditions.append("price <= :pmax")
            params["pmax"] = slot["price_max"]

        # 折扣率（计算字段：price/retail_price*100，前端可选）
        if slot.get("discount_min") is not None:
            conditions.append("(price * 100.0 / NULLIF(retail_price, 0)) >= :dmin")
            params["dmin"] = slot["discount_min"]
        if slot.get("discount_max") is not None:
            conditions.append("(price * 100.0 / NULLIF(retail_price, 0)) <= :dmax")
            params["dmax"] = slot["discount_max"]

        # 全局关键词条件（多个关键词用 AND，同样忽略空格模糊匹配）
        if keywords:
            kw_conds = []
            for i, kw in enumerate(keywords):
                variants = self._keyword_variants(str(kw))
                if not variants:
                    continue
                # 严格模式只取完整词；模糊模式仅当放宽变体足够具体时才放宽
                use_variants = variants
                if not fuzzy or (len(use_variants) > 1 and not self._variant_is_specific(use_variants[1], company_id)):
                    use_variants = use_variants[:1]
                pname = "kw{}".format(i)
                kw_sql, kw_params = self._keyword_condition_sql(pname, use_variants)
                kw_conds.append(kw_sql)
                params.update(kw_params)
            if kw_conds:
                conditions.append("(" + " AND ".join(kw_conds) + ")")

        # 数据隔离
        pure_any = not conditions
        if company_id:
            conditions.append("company_id = :company_id")
            params["company_id"] = company_id

        def _run(extra_conds: list, extra_params: dict, limit: int) -> List[Dict]:
            """执行一次候选查询"""
            all_cond = list(conditions) + list(extra_conds)
            all_params = {**params, **extra_params}
            where_clause = " AND ".join(all_cond) if all_cond else "1=1"
            sql = f"SELECT * FROM products WHERE {where_clause} ORDER BY price ASC LIMIT {limit}"
            try:
                with sync_engine.connect() as conn:
                    rows = conn.execute(text(sql), all_params).fetchall()
                    if not rows:
                        return []
                    columns = [col[1] for col in conn.execute(text("PRAGMA table_info(products)")).fetchall()]
                    return [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                logger.warning(f"查询候选商品失败: {e}")
                return []

        # 单个槽位的商品名称关键词：精确匹配优先，模糊放宽补足
        kw = (slot.get("keyword") or "").strip()
        if kw:
            variants = self._keyword_variants(kw)
            if variants:
                # 第一优先级：完整关键词精确匹配
                exact_sql, exact_params = self._keyword_condition_sql("kwx", variants[:1])
                exact_rows = _run([exact_sql], exact_params, self.MAX_CANDIDATES_PER_SLOT)
                for r in exact_rows:
                    r["_match_score"] = 1.0
                exact_ids = {r["id"] for r in exact_rows}
                # 第二优先级（仅模糊模式）：放宽变体需足够具体，避免"充电"误配到大量充电器
                if fuzzy and len(variants) > 1 and self._variant_is_specific(variants[1], company_id):
                    fuzzy_sql, fuzzy_params = self._keyword_condition_sql("kwf", variants)
                    fuzzy_rows = _run([fuzzy_sql], fuzzy_params, self.MAX_CANDIDATES_PER_SLOT)
                    fuzzy_rows = [r for r in fuzzy_rows if r["id"] not in exact_ids]
                    for r in fuzzy_rows:
                        r["_match_score"] = 0.5
                else:
                    fuzzy_rows = []
                remaining = self.MAX_CANDIDATES_PER_SLOT - len(exact_rows)
                return exact_rows + fuzzy_rows[: max(0, remaining)]

        # 无商品名称关键词：
        # 若该槽位是"任意商品"（无任何品类/价格/折扣率/品牌/规格/关键词约束），
        # 用全库有价商品的分层样本，避免只取最便宜的一批导致较高总价目标无法达成。
        if pure_any:
            return self._query_any_candidates(company_id)
        return _run([], {}, self.MAX_CANDIDATES_PER_SLOT)


# 全局单例
combination_engine = CombinationEngine()
