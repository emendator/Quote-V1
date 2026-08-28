import { useState, useEffect, useCallback, useMemo, useRef, type PointerEvent as ReactPointerEvent } from 'react';
import { Input, InputNumber, Row, Col, Divider, message, Table, Space, Tooltip, Modal, Typography, Alert, Card, Tag, Button, Select } from 'antd';
import { PlusOutlined, MinusCircleOutlined, DownloadOutlined, SaveOutlined, ShoppingCartOutlined, FileTextOutlined, HistoryOutlined, CheckCircleOutlined, SearchOutlined, DeleteOutlined, ColumnHeightOutlined, ShopOutlined, CloseCircleOutlined, ThunderboltFilled, DownOutlined, RightOutlined, RobotOutlined, BulbOutlined, RocketOutlined } from '@ant-design/icons';
import { analyzeSolution, saveSolution, exportSolution, listSolutions, getSolutionDetail, deleteSolution, getColumnDisplayConfig, getRecommendedProducts, getRecommendedSolutions, fetchCategoryLevel3 } from '../services/api';
import type { SolutionAnalyzeResult, SolutionItemData, SolutionCombination, SolutionSlotItem, SolutionSlotInput, SolutionDiagnosis, ColumnConfigItem, RecommendedProduct } from '../types';
import { usePageState } from '../store/PageStateContext';
import { useAuth } from '../store/AuthContext';
import ColumnDisplayConfig from '../components/ColumnDisplayConfig';
import { CountUpMoney } from '../hooks/useCountUp';

const { Text } = Typography;

/** 从结构化输入生成需求摘要文本（用于推荐/保存） */
function buildRequirementSummary(
    total: number | null | undefined,
    totalDiscount: number | null | undefined,
    slotList: SolutionSlotInput[],
    totalOp: 'gt' | 'lt' | 'around' | '' = 'lt',
    totalDiscountOp: 'gt' | 'lt' | 'around' | '' = 'lt',
): string {
    const parts: string[] = [];
    if (total && total > 0) {
        const op = totalOp || 'lt';
        parts.push(op === 'gt' ? `总价≥${total}元` : op === 'around' ? `总价${total}元左右` : `总价≤${total}元`);
    }
    if (totalDiscount != null && totalDiscount > 0 && totalDiscountOp) {
        const op = totalDiscountOp;
        parts.push(op === 'gt' ? `总折扣率≥${totalDiscount}%` : op === 'around' ? `总折扣率${totalDiscount}%左右` : `总折扣率≤${totalDiscount}%`);
    }
    slotList.forEach(s => {
        const cat = s.category?.trim();
        const qty = Math.max(1, s.quantity || 1);
        let priceTxt = '';
        const val = s.price;
        const op = s.price_op || '';
        if (val != null && op) {
            if (op === 'gt') priceTxt = `（＞${val}元）`;
            else if (op === 'lt') priceTxt = `（＜${val}元）`;
            else if (op === 'around') priceTxt = `（${val}元左右）`;
        }
        let discountTxt = '';
        const dval = s.discount;
        const dop = s.discount_op || '';
        if (dval != null && dop) {
            if (dop === 'gt') discountTxt = `（折扣率＞${dval}%）`;
            else if (dop === 'lt') discountTxt = `（折扣率＜${dval}%）`;
            else if (dop === 'around') discountTxt = `（折扣率${dval}%左右）`;
        }
        parts.push(`${cat || '任意商品'}×${qty}${priceTxt}${discountTxt}`);
    });
    return parts.join('，');
}

/** 两档胶囊滑块：左=多块输入，右=AI 智能（点击/拖动切换） */
function ModeSlider({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [dragging, setDragging] = useState(false);

    const handlePointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
        e.preventDefault();
        const setByX = (clientX: number) => {
            const rect = containerRef.current?.getBoundingClientRect();
            if (!rect || rect.width <= 0) return;
            onChange((clientX - rect.left) / rect.width >= 0.5);
        };
        setByX(e.clientX);
        setDragging(true);
        const move = (ev: PointerEvent) => setByX(ev.clientX);
        const up = () => {
            setDragging(false);
            window.removeEventListener('pointermove', move);
            window.removeEventListener('pointerup', up);
        };
        window.addEventListener('pointermove', move);
        window.addEventListener('pointerup', up);
    };

    return (
        // 容器（圆角背景条）
        <div
            ref={containerRef}
            onPointerDown={handlePointerDown}
            title={value ? 'AI 智能（右滑）' : '多块输入（左滑）'}
            className="dd-mode-slider"
            style={{
                position: 'relative', display: 'flex', width: 240, height: 34,
                background: 'var(--slider-track)', borderRadius: 17, overflow: 'hidden',
                userSelect: 'none', touchAction: 'none', cursor: 'pointer', flexShrink: 0,
            }}
        >
            {/* 滑块高亮：按 value 计算 left 位置，宽度占 1/2 */}
            <div style={{
                position: 'absolute', top: 3, bottom: 3,
                left: `${value ? 50 : 0}%`,
                width: 'calc(100% / 2)',
                background: 'var(--slider-thumb)',
                borderRadius: 14,
                transition: dragging ? 'none' : 'left 0.25s',
            }} />
            {/* 左档：多块输入 */}
            <div style={{
                flex: 1, position: 'relative', zIndex: 1, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                color: value ? 'var(--ink-400)' : '#fff', fontWeight: 600, fontSize: 13,
            }}>多块输入</div>
            {/* 右档：AI 智能 */}
            <div style={{
                flex: 1, position: 'relative', zIndex: 1, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                color: value ? '#fff' : 'var(--ink-400)', fontWeight: 600, fontSize: 13,
            }}>AI 智能</div>
        </div>
    );
}

export default function SolutionPage() {
    const { user } = useAuth();
    const [loading, setLoading] = useState(false);
    // 方案排序：'smart' 智能（贴近用户输入，默认）| 'asc' 升序 | 'desc' 降序
    const [sortOrder, setSortOrder] = useState<'smart' | 'asc' | 'desc'>('smart');

    // ====== 持久化状态 ======
    const [pageState, setPageState] = usePageState('solution', {
        requirement: '',            // 需求摘要（由结构化输入生成）
        useAI: false,               // AI 模式开关
        aiMode: false,              // 输入方式：false=多块输入, true=AI 智能输入
        aiText: '',                 // AI 模式的自然语言需求
        totalPrice: null as number | null,        // 总价（必填）
        totalPriceOp: 'lt' as 'gt' | 'lt' | 'around',   // 总价限制方式（默认小于）
        totalDiscount: null as number | null,     // 总折扣率（可选）
        totalDiscountOp: 'lt' as '' | 'gt' | 'lt' | 'around', // 总折扣率限制方式（默认小于，可选不限）
        slotsOpen: true,                          // 商品信息整个区块是否展开
        previewItemsOpen: true,                   // 方案预览中的商品明细下拉是否展开
        slots: [{ category: '', quantity: 1, price_op: '', price: null, discount_op: '', discount: null, price_min: null, price_max: null }] as SolutionSlotInput[],
        result: null as SolutionAnalyzeResult | null,
        solutionName: '',
        savedPlanId: null as number | null,
        selectedSolutionIdx: null as number | null,  // 当前选中的组合方案索引
    });

    const { requirement, useAI, aiMode, aiText, totalPrice, totalPriceOp, totalDiscount, totalDiscountOp, slotsOpen, previewItemsOpen, slots, result, solutionName, savedPlanId, selectedSolutionIdx } = pageState;
    const updateState = useCallback((patch: Partial<typeof pageState>) => {
        // 函数式更新：始终基于最新状态合并，避免异步回调用旧闭包覆盖新状态
        setPageState(prev => ({ ...prev, ...patch }));
    }, [setPageState]);

    // ====== 结构化输入：商品信息块操作 ======

    const updateSlot = useCallback((idx: number, patch: Partial<SolutionSlotInput>) => {
        const next = slots.map((s, i) => (i === idx ? { ...s, ...patch } : s));
        updateState({ slots: next });
    }, [slots, updateState]);

    const addSlot = useCallback(() => {
        updateState({ slots: [...slots, { category: '', quantity: 1, price_op: '', price: null, discount_op: '', discount: null, price_min: null, price_max: null }] });
    }, [slots, updateState]);

    const removeSlot = useCallback((idx: number) => {
        if (slots.length <= 1) {
            message.warning('至少保留一个商品信息');
            return;
        }
        updateState({ slots: slots.filter((_, i) => i !== idx) });
    }, [slots, updateState]);

    // ====== 智能诊断：一键应用建议 ======

    // 后端按 quantity 展开槽位，需映射回前端商品块索引（同一商品块对应多个后端槽位）
    const backendToFrontSlotIndex = useCallback((backendIdx: number) => {
        let acc = 0;
        for (let i = 0; i < slots.length; i++) {
            acc += Math.max(1, slots[i].quantity || 1);
            if (backendIdx < acc) return i;
        }
        return slots.length - 1;
    }, [slots]);

    // 高亮定位到指定输入框（滚动到视野 + 紫色边框闪烁）
    const flashHighlight = useCallback((id: string, shouldScroll = true, duration = 3000) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (shouldScroll) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // antd InputNumber 的边框在外层容器 .ant-input-number 上，高亮容器更明显
        const box = el.closest('.ant-input-number') as HTMLElement | null;
        const target = box || el;
        target.style.transition = 'border-color 0.3s, box-shadow 0.3s';
        target.style.borderColor = 'var(--accent-purple)';
        target.style.borderWidth = '2px';
        target.style.boxShadow = '0 0 0 3px rgba(124,58,237,0.3)';
        target.style.borderRadius = '6px';
        setTimeout(() => {
            target.style.borderColor = '';
            target.style.borderWidth = '';
            target.style.boxShadow = '';
            target.style.transition = '';
        }, duration);
    }, []);

    // 无方案时：自动高亮诊断涉及的输入框（紫色边框 + 发光闪烁），让用户知道该改哪里
    const autoHighlightDiagnosis = useCallback((diag: SolutionDiagnosis[]) => {
        if (!diag?.length) return;
        let needsSlotOpen = false;
        const targets: { id: string; scroll: boolean }[] = [];
        diag.forEach((d, idx) => {
            const adj = d.adjust;
            if (!adj) return;
            let id: string | null = null;
            if (adj.field === 'total_price') {
                id = 'sol-total-price';
            } else if (adj.field === 'total_discount') {
                id = 'sol-total-discount';
            } else if (adj.field === 'price' && adj.slot_index != null) {
                needsSlotOpen = true;
                id = `sol-price-${backendToFrontSlotIndex(adj.slot_index)}`;
            } else if (adj.field === 'discount' && adj.slot_index != null) {
                needsSlotOpen = true;
                id = `sol-discount-${backendToFrontSlotIndex(adj.slot_index)}`;
            } else if (adj.field === 'category' && adj.slot_index != null) {
                needsSlotOpen = true;
                id = `sol-cat-${backendToFrontSlotIndex(adj.slot_index)}`;
            }
            if (id) targets.push({ id, scroll: idx === 0 });
        });
        if (!targets.length) return;
        const doHighlight = () => {
            // 第一条滚动定位，其余仅高亮避免页面跳动
            targets.forEach((t) => flashHighlight(t.id, t.scroll, 5000));
        };
        if (needsSlotOpen && !slotsOpen) {
            updateState({ slotsOpen: true });
            setTimeout(doHighlight, 120);
        } else {
            doHighlight();
        }
    }, [backendToFrontSlotIndex, flashHighlight, slotsOpen, updateState]);

    const applyAdjust = useCallback((d: SolutionDiagnosis) => {
        const adj = d?.adjust;
        if (!adj) return;
        // AI 模式：后端已把调整改写为"直接覆盖需求文本"，此处直接覆盖用户输入（不照搬非 AI 的改输入框逻辑）
        if (adj.field === 'requirement') {
            const revised = (adj.value as string) || '';
            updateState({ aiText: revised, requirement: revised });
            flashHighlight('sol-ai-text');
            message.success('✅ 已按诊断自动改写需求文本（已覆盖输入框），请点击「生成方案」重新生成');
            return;
        }
        const { field, slot_index, op } = adj;
        // 结构化（非 AI）调整：value 必为数值（requirement 分支已提前 return）
        const value = (adj.value as number | null);
        const priceOp = (op as 'gt' | 'lt' | 'around' | '') || 'lt';
        const discOp = (op as 'gt' | 'lt' | 'around' | '') || 'lt';

        if (field === 'total_price') {
            updateState({ totalPrice: value ?? null, totalPriceOp: priceOp });
            flashHighlight('sol-total-price');
            message.success(`✅ 已自动把总价${priceOp === 'gt' ? '下限' : priceOp === 'around' ? '限制' : '上限'}填入 ${value} 元（输入框已高亮），请点击「生成方案」`);
        } else if (field === 'total_discount') {
            updateState({ totalDiscount: value ?? null, totalDiscountOp: discOp });
            flashHighlight('sol-total-discount');
            message.success(`✅ 已自动把总折扣率${discOp === 'gt' ? '下限' : '上限'}填入 ${value}%（输入框已高亮），请点击「生成方案」`);
        } else if (field === 'price' && slot_index != null) {
            const fi = backendToFrontSlotIndex(slot_index);
            if (!slotsOpen) updateState({ slotsOpen: true });
            updateSlot(fi, { price_op: priceOp, price: value ?? null });
            flashHighlight(`sol-price-${fi}`);
            message.success(`✅ 已自动把第 ${fi + 1} 个商品「${slots[fi]?.category || ''}」的价格限制填入 ${value} 元（价格输入框已高亮），请点击「生成方案」`);
        } else if (field === 'discount' && slot_index != null) {
            const fi = backendToFrontSlotIndex(slot_index);
            if (!slotsOpen) updateState({ slotsOpen: true });
            updateSlot(fi, { discount_op: discOp, discount: value ?? null });
            flashHighlight(`sol-discount-${fi}`);
            message.success(`✅ 已自动把第 ${fi + 1} 个商品「${slots[fi]?.category || ''}」的折扣率限制填入 ${value}%（折扣率输入框已高亮），请点击「生成方案」`);
        } else if (field === 'remove_last_slot') {
            if (slots.length > 1) {
                updateState({ slots: slots.slice(0, slots.length - 1) });
                message.success('✅ 已移除最后一个商品，请点击「生成方案」重新生成');
            } else {
                message.warning('至少保留一个商品信息');
            }
        }
    }, [updateState, updateSlot, slots, slotsOpen, flashHighlight, backendToFrontSlotIndex]);

    // 三级品类列表（用于产品品类自动补全）
    const [level3Categories, setLevel3Categories] = useState<string[]>([]);
    const [categoriesLoading, setCategoriesLoading] = useState(false);

    useEffect(() => {
        setCategoriesLoading(true);
        fetchCategoryLevel3()
            .then(setLevel3Categories)
            .catch(() => setLevel3Categories([]))
            .finally(() => setCategoriesLoading(false));
    }, []);

    // 历史方案
    const [historyOpen, setHistoryOpen] = useState(false);
    const [historyList, setHistoryList] = useState<any[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);

    // 列显示配置
    const [columnConfigOpen, setColumnConfigOpen] = useState(false);
    const [solutionColumnConfig, setSolutionColumnConfig] = useState<ColumnConfigItem[] | undefined>(undefined);
    const pageTypeForConfig = 'solution_items';

    // 推荐产品
    const [recommendedProducts, setRecommendedProducts] = useState<RecommendedProduct[]>([]);
    const [recommendedLoading, setRecommendedLoading] = useState(false);

    // 推荐方案
    const [recommendedSolutions, setRecommendedSolutions] = useState<any[]>([]);
    const [recommendedSolutionsLoading, setRecommendedSolutionsLoading] = useState(false);

    const loadSolutionColumnConfig = useCallback(async () => {
        try {
            const data = await getColumnDisplayConfig(pageTypeForConfig);
            setSolutionColumnConfig(data.columns || []);
        } catch {
            setSolutionColumnConfig(undefined);
        }
    }, [pageTypeForConfig]);

    // 当 result 变化时（分析完成或页面状态恢复），加载列配置和推荐内容
    useEffect(() => {
        if (result?.solutions) {
            loadSolutionColumnConfig();
            if (recommendedProducts.length === 0 && recommendedSolutions.length === 0) {
                fetchRecommendations(requirement);
            }
        }
    }, [result]);

    // ========== 获取推荐产品 & 推荐方案 ==========

    const fetchRecommendations = async (requirementText: string) => {
        setRecommendedLoading(true);
        setRecommendedSolutionsLoading(true);
        try {
            // 获取推荐产品
            const prodRes = await getRecommendedProducts({ filters: {}, page: 1, page_size: 20 });
            setRecommendedProducts(prodRes.items || []);
        } catch {
            setRecommendedProducts([]);
        } finally {
            setRecommendedLoading(false);
        }

        // 获取推荐方案（使用解析后的需求文本）
        if (requirementText.trim()) {
            try {
                const solRes = await getRecommendedSolutions({
                    requirement: requirementText.trim(),
                    max_solutions: 50,
                });
                setRecommendedSolutions(solRes.solutions || []);
            } catch {
                setRecommendedSolutions([]);
            } finally {
                setRecommendedSolutionsLoading(false);
            }
        } else {
            setRecommendedSolutionsLoading(false);
        }
    };

    // ========== 组合方案处理 ==========

    // 方案结果后处理：去重 + 默认智能排序
    const postProcess = (data: SolutionAnalyzeResult): SolutionAnalyzeResult => {
        if (data.solutions) {
            const seen = new Set<string>();
            data.solutions = data.solutions.filter((sol: SolutionCombination) => {
                const qms = sol.items.map((item: SolutionSlotItem) => item.quick_model).sort().join(',');
                if (seen.has(qms)) return false;
                seen.add(qms);
                return true;
            });
            data.total_solutions = data.solutions.length;
        }
        setSortOrder('smart');
        return data;
    };

    const handleAnalyze = async () => {
        // ===== AI 智能输入模式：直接解析自然语言 =====
        if (aiMode) {
            if (!aiText?.trim()) {
                message.warning('请输入客户需求描述');
                return;
            }
            if (!user?.has_api_key) {
                message.warning('使用 AI 智能输入需先配置 API Key：请点击右上角用户菜单中的「API Key 配置」');
                return;
            }
            setLoading(true);
            setRecommendedProducts([]);
            setRecommendedSolutions([]);
            try {
                const data = await analyzeSolution({
                    requirement: aiText.trim(),
                    use_ai: true,
                    max_solutions: 200,
                });
                const processed = postProcess(data);
                updateState({ result: processed, requirement: aiText.trim(), savedPlanId: null, selectedSolutionIdx: null });
                if (processed.total_solutions > 0) {
                    message.success(`找到 ${processed.total_solutions} 个符合条件的组合方案`);
                } else if (processed.diagnosis?.length) {
                    message.warning('未生成合适方案，已标出需要调整的输入框，请按下方诊断建议修改后重试');
                    autoHighlightDiagnosis(processed.diagnosis);
                } else {
                    message.info(processed.message || '未找到符合条件的组合方案，试试放宽价格或折扣率限制');
                }
            } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : '分析失败';
                message.error(msg);
            } finally {
                setLoading(false);
            }
            return;
        }

        // 汇总所有缺失的必填项，一次性提醒用户
        const missing: string[] = [];

        // 总价必填
        if (!totalPrice && totalPrice !== 0) {
            missing.push('总价');
        } else if (totalPrice !== null && totalPrice !== undefined && totalPrice <= 0) {
            missing.push('总价（需大于 0）');
        }

        // 每个商品的品类必填
        if (slots.length === 0) {
            missing.push('至少一个商品');
        } else {
            slots.forEach((s, i) => {
                if (!s.category?.trim()) {
                    missing.push(`第 ${i + 1} 个商品的品类`);
                }
            });
        }

        if (missing.length > 0) {
            message.warning(`请完善以下必填项：${missing.join('；')}`);
            return;
        }

        // 必填项已全部填写
        const validSlots = slots.filter(s => s.category?.trim());
        const summary = buildRequirementSummary(totalPrice, totalDiscount, validSlots, totalPriceOp, totalDiscountOp);
        setLoading(true);
        setRecommendedProducts([]);
        setRecommendedSolutions([]);
        try {
            const data = await analyzeSolution({
                requirement: summary,
                use_ai: false,
                total_price: totalPrice,
                total_price_op: totalPriceOp,
                // 选择"不限"时总折扣率不生效
                max_discount_rate: totalDiscountOp === '' ? null : totalDiscount,
                max_discount_op: totalDiscountOp,
                slots: validSlots.map(s => {
                    // 优先使用新的操作符 + 价格值；兼容旧数据（仅 price_max → 小于）
                    let op: '' | 'gt' | 'lt' | 'around' = s.price_op || '';
                    let val = s.price;
                    if (!op && s.price_max != null) {
                        op = 'lt';
                        val = s.price_max;
                    }
                    return {
                        category: s.category?.trim() || '',
                        quantity: Math.max(1, s.quantity || 1),
                        price_op: op,
                        price: val ?? null,
                        discount_op: s.discount_op || '',
                        discount: s.discount ?? null,
                        price_min: null,
                        price_max: null,
                    };
                }),
                max_solutions: 200,
            });
            const processed = postProcess(data);
            updateState({ result: processed, requirement: summary, savedPlanId: null, selectedSolutionIdx: null });
            if (processed.total_solutions > 0) {
                message.success(`找到 ${processed.total_solutions} 个符合条件的组合方案`);
            } else if (processed.diagnosis?.length) {
                message.warning('未生成合适方案，已标出需要调整的输入框，请按下方诊断建议修改后重试');
                autoHighlightDiagnosis(processed.diagnosis);
            } else {
                message.info(processed.message || '未找到符合条件的组合方案，试试放宽价格或折扣率限制');
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '分析失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    // 选中某个组合方案
    const selectSolution = (idx: number) => {
        updateState({ selectedSolutionIdx: idx });
    };

    // 保存选中的方案
    const handleSave = async () => {
        if (selectedSolutionIdx === null || !result?.solutions[selectedSolutionIdx]) {
            message.warning('请先选择一个组合方案');
            return;
        }

        const selected = result.solutions[selectedSolutionIdx];
        const items: SolutionItemData[] = selected.items.map((item: SolutionSlotItem) => ({
            product_id: item.product_id,
            quantity: item.quantity,
        }));

        const name = solutionName.trim() || `组合方案_${new Date().toLocaleDateString('zh-CN')}`;
        try {
            const res = await saveSolution({
                name,
                requirement: requirement || '（无需求文本）',
                remark: '',
                ai_enabled: useAI,
                items,
            });
            updateState({ savedPlanId: res.plan_id });
            message.success(`方案已保存，共 ${res.items_count} 个商品，总金额 ¥${res.total_amount}`);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '保存失败';
            message.error(msg);
        }
    };

    // 导出方案
    const handleExport = async () => {
        if (!savedPlanId) {
            message.warning('请先保存方案');
            return;
        }
        try {
            await exportSolution(savedPlanId);
            message.success('导出成功');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '导出失败';
            message.error(msg);
        }
    };

    // 已选方案的商品数量总计
    const selectedSolutionTotal = selectedSolutionIdx !== null && result?.solutions[selectedSolutionIdx]
        ? result.solutions[selectedSolutionIdx].total_quantity : 0;

    // 历史方案
    const openHistory = async () => {
        setHistoryLoading(true);
        setHistoryOpen(true);
        try {
            const list = await listSolutions();
            setHistoryList(list);
        } catch { setHistoryList([]); }
        setHistoryLoading(false);
    };

    const handleReusePlan = async (planId: number) => {
        try {
            const detail = await getSolutionDetail(planId);
            const items_list = (detail.items || []) as any[];
            // 构建一个和 analyze 返回格式一致的 solution 对象
            const planItems = items_list.map((item: any) => ({
                product_id: item.product_id,
                quick_model: item.quick_model || '',
                product_model: item.product_model || '',
                product_name: item.product_name || '',
                brand: item.brand || '',
                category_level1: item.category_level1 || '',
                category_level2: item.category_level2 || '',
                specification: item.specification || '',
                price: item.price || 0,
                retail_price: item.retail_price || 0,
                discount_rate: item.discount_rate || 0,
                quantity: item.quantity || 1,
                subtotal: item.subtotal || (item.price || 0) * (item.quantity || 1),
            }));
            const totalPrice = planItems.reduce((sum: number, i: any) => sum + (i.subtotal || 0), 0);
            const totalDiscount = planItems.reduce((sum: number, i: any) => {
                if (i.retail_price && i.retail_price > 0) {
                    return sum + (i.price / i.retail_price * 100);
                }
                return sum;
            }, 0) / (planItems.length || 1);

            const reuseSolution: SolutionCombination = {
                total_price: totalPrice,
                total_quantity: planItems.length,
                total_discount_rate: parseFloat(totalDiscount.toFixed(2)),
                items: planItems,
            };

            const reuseResult: SolutionAnalyzeResult = {
                solutions: [reuseSolution],
                total_solutions: 1,
                message: `已加载历史方案「${detail.name || ''}」`,
                ai_interpretation: '',
                parsed_constraints: {},
            };

            updateState({
                result: reuseResult,
                savedPlanId: planId,
                selectedSolutionIdx: 0,
                solutionName: detail.name as string || '',
                requirement: detail.requirement as string || '',
            });
            setHistoryOpen(false);
            message.success(`已加载历史方案，共 ${planItems.length} 个商品`);
        } catch (err: unknown) {
            message.error('加载方案失败');
        }
    };

    const handleDeletePlan = async (planId: number) => {
        try {
            await deleteSolution(planId);
            setHistoryList(prev => prev.filter(p => p.id !== planId));
            message.success('已删除');
        } catch { message.error('删除失败'); }
    };

    // 清除当前选中的方案（不清除结果列表）
    const handleClear = () => {
        updateState({
            savedPlanId: null,
            selectedSolutionIdx: null,
            solutionName: '',
        });
    };

    // 组合方案表格列定义
    const renderImage = (v: string) => {
        if (!v || v === '') return <span style={{ color: 'var(--ink-300)', fontSize: 12 }}>无图</span>;
        const src = v.startsWith('data:') ? v : `data:image/png;base64,${v}`;
        return (
            <Tooltip title={<img src={src} style={{ maxWidth: 300, maxHeight: 300 }} alt="预览" />}>
                <img src={src} alt="" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 4, border: '1px solid var(--ink-100)', cursor: 'pointer' }} />
            </Tooltip>
        );
    };

    const solutionItemColumns = useMemo(() => {
        const baseColumns = [
            {
                title: '图片', dataIndex: 'image', key: 'image', width: 55,
                render: (v: string) => renderImage(v),
            },
            { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 130, ellipsis: true },
            { title: '型号', dataIndex: 'product_model', key: 'product_model', width: 110, ellipsis: true },
            {
                title: '商品名称', dataIndex: 'product_name', key: 'product_name', width: 160,
                ellipsis: { showTitle: false },
                render: (v: string, record: SolutionSlotItem) => (
                    <Tooltip title={`${v || record.quick_model} (${record.brand})`}>
                        <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {v || record.quick_model}
                        </span>
                    </Tooltip>
                )
            },
            { title: '品牌', dataIndex: 'brand', key: 'brand', width: 60 },
            { title: '一级品类', dataIndex: 'category_level1', key: 'category_level1', width: 70 },
            { title: '二级品类', dataIndex: 'category_level2', key: 'category_level2', width: 70 },
            { title: '三级品类', dataIndex: 'category_level3', key: 'category_level3', width: 70 },
            { title: '备货商谈价', dataIndex: 'negotiation_price', key: 'negotiation_price', width: 75, render: (v: number) => v ? `¥${v.toFixed(2)}` : '-' },
            { title: '报价更新', dataIndex: 'price_update', key: 'price_update', width: 95, ellipsis: true },
            { title: '上次进货价', dataIndex: 'last_purchase_price', key: 'last_purchase_price', width: 75, render: (v: number) => v ? `¥${v.toFixed(2)}` : '-' },
            { title: '进货价', dataIndex: 'purchase_price', key: 'purchase_price', width: 75, render: (v: number) => v ? `¥${v.toFixed(2)}` : '-' },
            { title: '新活动价', dataIndex: 'new_event_price', key: 'new_event_price', width: 75, render: (v: number) => v ? `¥${v.toFixed(2)}` : '-' },
            { title: '集采价', dataIndex: 'group_purchase_price', key: 'group_purchase_price', width: 75, render: (v: number) => v ? `¥${v.toFixed(2)}` : '-' },
            { title: '投标价', dataIndex: 'bid_price', key: 'bid_price', width: 75, render: (v: number) => v ? `¥${v.toFixed(2)}` : '-' },
            { title: '规格', dataIndex: 'specification', key: 'specification', width: 110, ellipsis: true },
            {
                title: '代发价', dataIndex: 'price', key: 'price', width: 70,
                render: (v: number) => <Text strong style={{ color: 'var(--accent-red)' }}>¥{v.toFixed(2)}</Text>
            },
            { title: '零售价', dataIndex: 'retail_price', key: 'retail_price', width: 70, render: (v: number) => v ? `¥${v.toFixed(2)}` : '-' },
            { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 60, render: (v: number) => v ? `${v.toFixed(1)}%` : '-' },
            {
                title: '链接', dataIndex: 'shop_url', key: 'shop_url', width: 150,
                ellipsis: { showTitle: false },
                render: (v: string) => v ? (
                    <a href={v} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}
                        style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {v}
                    </a>
                ) : '-',
            },
            { title: '毛重(kg)', dataIndex: 'gross_weight', key: 'gross_weight', width: 65, render: (v: number) => v ? v : '-' },
            { title: '箱规', dataIndex: 'box_spec', key: 'box_spec', width: 110, ellipsis: true },
            { title: '合作等级', dataIndex: 'cooperation_level', key: 'cooperation_level', width: 65 },
            { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 65 },
            { title: '备注', dataIndex: 'remark', key: 'remark', width: 140, ellipsis: true },
            { title: '代发运费', dataIndex: 'shipping_fee', key: 'shipping_fee', width: 75, render: (v: number) => v ? `¥${v.toFixed(2)}` : '-' },
            { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 130, ellipsis: true },
            { title: '销量', dataIndex: 'sales_volume', key: 'sales_volume', width: 55 },
            { title: '推荐理由', dataIndex: 'recommendation', key: 'recommendation', width: 130, ellipsis: true },
            { title: '参数', dataIndex: 'parameters', key: 'parameters', width: 100, ellipsis: true },
            { title: '3C', dataIndex: 'cert_3c', key: 'cert_3c', width: 65, ellipsis: true },
            { title: '导入时间', dataIndex: 'created_at', key: 'created_at', width: 150, ellipsis: true },
            { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 60 },
            {
                title: '小计', dataIndex: 'subtotal', key: 'subtotal', width: 80,
                render: (v: number) => <Text strong>¥{v.toFixed(2)}</Text>
            },
        ];

        if (solutionColumnConfig && solutionColumnConfig.length > 0) {
            const configMap = new Map(solutionColumnConfig.map(c => [c.key, c]));
            return baseColumns
                .filter(col => {
                    const key = String((col as any).key ?? '');
                    const cfg = configMap.get(key);
                    return cfg ? cfg.visible : true;
                })
                .map(col => {
                    const key = String((col as any).key ?? '');
                    const cfg = configMap.get(key);
                    if (cfg) {
                        return {
                            ...col,
                            title: cfg.label || col.title,
                            // 如果配置中指定了列宽则使用，否则不设宽度让列自适应
                            width: cfg.width || undefined,
                        };
                    }
                    return col;
                })
                .sort((a, b) => {
                    const keyA = String((a as any).key ?? '');
                    const keyB = String((b as any).key ?? '');
                    const orderMap = new Map(solutionColumnConfig.map((c, i) => [c.key, i]));
                    const ai = orderMap.get(keyA) ?? 999;
                    const bi = orderMap.get(keyB) ?? 999;
                    return ai - bi;
                });
        }
        return baseColumns;
    }, [solutionColumnConfig]);

    // 选中组合方案的商品明细
    const selectedSolution = selectedSolutionIdx !== null && result?.solutions[selectedSolutionIdx]
        ? result.solutions[selectedSolutionIdx] : null;

    return (
        <div style={{ margin: '0 auto', padding: '0 8px' }}>
            {/* 顶部行：需求输入区 + 方案预览并列（6 : 4） */}
            <Row gutter={16} align="stretch">
                <Col xs={24} md={{ flex: '60%' }} className="dd-module dd-d1">
                    {/* 需求输入区 */}
                    <Card size="small" style={{ marginBottom: 16, height: '100%' }}>
                        {aiMode ? (
                            <div>
                                <Input.TextArea
                                    id="sol-ai-text"
                                    rows={4}
                                    value={aiText}
                                    onChange={e => updateState({ aiText: e.target.value })}
                                    onKeyDown={(e) => {
                                        // 中文输入法守卫：Enter 在拼音组合中不触发（Handle CJK Input Method Differently）
                                        if (e.key === 'Enter' && !e.nativeEvent.isComposing && !e.shiftKey) {
                                            e.preventDefault();
                                            handleAnalyze();
                                        }
                                    }}
                                    placeholder="例如：我要一个价值500的礼盒，包含三个产品，整体折扣率低于70%，产品分别是移动电源、自拍杆、数据线，其中移动电源价值不低于300"
                                />
                                {/* 示例需求预填（Pre-filled Example Content） */}
                                <div className="query-examples" style={{ marginTop: 8 }}>
                                    {[
                                        '我要一个价值500的礼盒，包含三个产品，整体折扣率低于70%，产品分别是移动电源、自拍杆、数据线，其中移动电源价值不低于300',
                                        '价值800左右的开业礼篮：吹风机、剃须刀、保温杯各一件，折扣率越低越好',
                                    ].map((ex) => (
                                        <Button
                                            key={ex}
                                            type="dashed"
                                            size="small"
                                            className="query-example-tag"
                                            onClick={() => updateState({ aiText: ex })}
                                        >
                                            试试示例：{ex.slice(0, 22)}…
                                        </Button>
                                    ))}
                                </div>
                                <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
                                    点击「生成组合方案」后，AI 将自动解析总价、三级品类、价格/折扣率限制并生成方案（需在右上角用户菜单配置 API Key）
                                </Text>
                            </div>
                        ) : (
                            <>
                                {/* 总价 + 总折扣率（均支持 大于/小于/左右） */}
                                <div style={{ marginBottom: 12, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
                                    <span style={{ whiteSpace: 'nowrap' }}>
                                        <Text type="secondary" style={{ marginRight: 8 }}>总价（必填）：</Text>
                                        <Select
                                            value={totalPriceOp}
                                            onChange={v => updateState({ totalPriceOp: (v || 'lt') as 'gt' | 'lt' | 'around' })}
                                            options={[
                                                { value: 'lt', label: '小于' },
                                                { value: 'gt', label: '大于' },
                                                { value: 'around', label: '左右' },
                                            ]}
                                            style={{ width: 76 }}
                                        />
                                        <InputNumber
                                            id="sol-total-price"
                                            value={totalPrice}
                                            onChange={v => updateState({ totalPrice: v })}
                                            placeholder="如 500"
                                            min={0}
                                            precision={2}
                                            addonAfter="元"
                                            style={{ width: 140 }}
                                        />
                                    </span>
                                    <span style={{ whiteSpace: 'nowrap' }}>
                                        <Text type="secondary" style={{ marginRight: 8 }}>总折扣率（可选）：</Text>
                                        <Select
                                            value={totalDiscountOp}
                                            onChange={v => updateState({ totalDiscountOp: (v || '') as '' | 'gt' | 'lt' | 'around' })}
                                            options={[
                                                { value: '', label: '不限' },
                                                { value: 'lt', label: '小于' },
                                                { value: 'gt', label: '大于' },
                                                { value: 'around', label: '左右' },
                                            ]}
                                            style={{ width: 76 }}
                                        />
                                        <InputNumber
                                            id="sol-total-discount"
                                            value={totalDiscount}
                                            onChange={v => updateState({ totalDiscount: v })}
                                            placeholder="如 70"
                                            min={0}
                                            max={100}
                                            precision={1}
                                            addonAfter="%"
                                            disabled={!totalDiscountOp}
                                            style={{ width: 120 }}
                                        />
                                    </span>
                                </div>

                                {/* 商品信息整个区块做成下拉列表（点击标题整体展开/收起，平滑手风琴） */}
                                <div className="dd-collapse-block" style={{ marginBottom: 12 }}>
                                    <div
                                        onClick={() => updateState({ slotsOpen: !slotsOpen })}
                                        style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', cursor: 'pointer', userSelect: 'none' }}
                                    >
                                        <span style={{ color: '#999', display: 'inline-flex' }}>
                                            {slotsOpen ? <DownOutlined /> : <RightOutlined />}
                                        </span>
                                        <Text strong>商品信息</Text>
                                        <Tag color="blue" style={{ marginInlineEnd: 0 }}>{slots.length} 个商品</Tag>
                                        <Text type="secondary" style={{ fontSize: 12 }}>（点击{slotsOpen ? '收起' : '展开'}）</Text>
                                        <div style={{ flex: 1 }} />
                                    </div>
                                    {/* grid-rows 技巧：0fr → 1fr 平滑展开/收起 */}
                                    <div style={{
                                        display: 'grid',
                                        gridTemplateRows: slotsOpen ? '1fr' : '0fr',
                                        transition: 'grid-template-rows 0.32s cubic-bezier(0.4, 0, 0.2, 1)',
                                    }}>
                                        <div style={{ overflow: 'hidden', minHeight: 0 }}>
                                            <div style={{ padding: '0 10px 10px', borderTop: '1px solid var(--ink-100)' }}>
                                            {slots.map((slot, idx) => (
                                                <div key={idx} style={{
                                                    border: '1px solid var(--ink-100)',
                                                    borderRadius: 6,
                                                    marginTop: 8,
                                                    padding: '8px 10px',
                                                    background: 'var(--surface)',
                                                }}>
                                                    {/* 单行：产品品类 + 数量 + 价格 + 折扣率 + 删除（窄屏自动换行） */}
                                                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                                                        <Select
                                                            id={`sol-cat-${idx}`}
                                                            showSearch
                                                            loading={categoriesLoading}
                                                            value={slot.category || undefined}
                                                            placeholder="三级品类（必填）"
                                                            onChange={v => updateSlot(idx, { category: v })}
                                                            options={level3Categories.map(c => ({ value: c, label: c }))}
                                                            filterOption={(input, option) =>
                                                                (option?.label as string ?? '').toLowerCase().includes(input.toLowerCase())
                                                            }
                                                            notFoundContent="未找到匹配的三级品类，试试其他关键词"
                                                            style={{ width: 120 }}
                                                        />
                                                        <InputNumber
                                                            placeholder="数量"
                                                            value={slot.quantity}
                                                            onChange={v => updateSlot(idx, { quantity: v ?? 1 })}
                                                            min={1}
                                                            style={{ width: 58 }}
                                                        />
                                                        <Text type="secondary" style={{ fontSize: 12 }}>价格</Text>
                                                        <Select
                                                            value={slot.price_op || ''}
                                                            onChange={v => updateSlot(idx, { price_op: (v || '') as '' | 'gt' | 'lt' | 'around' })}
                                                            options={[
                                                                { value: '', label: '不限' },
                                                                { value: 'lt', label: '小于' },
                                                                { value: 'gt', label: '大于' },
                                                                { value: 'around', label: '左右' },
                                                            ]}
                                                            style={{ width: 76 }}
                                                        />
                                                        <InputNumber
                                                            id={`sol-price-${idx}`}
                                                            placeholder="可选"
                                                            value={slot.price}
                                                            onChange={v => updateSlot(idx, { price: v })}
                                                            min={0}
                                                            precision={2}
                                                            addonAfter="元"
                                                            disabled={!slot.price_op}
                                                            style={{ width: 100 }}
                                                        />
                                                        <Text type="secondary" style={{ fontSize: 12 }}>折扣率</Text>
                                                        <Select
                                                            value={slot.discount_op || ''}
                                                            onChange={v => updateSlot(idx, { discount_op: (v || '') as '' | 'gt' | 'lt' | 'around' })}
                                                            options={[
                                                                { value: '', label: '不限' },
                                                                { value: 'lt', label: '小于' },
                                                                { value: 'gt', label: '大于' },
                                                                { value: 'around', label: '左右' },
                                                            ]}
                                                            style={{ width: 76 }}
                                                        />
                                                        <InputNumber
                                                            id={`sol-discount-${idx}`}
                                                            placeholder="可选"
                                                            value={slot.discount}
                                                            onChange={v => updateSlot(idx, { discount: v })}
                                                            min={0}
                                                            max={100}
                                                            precision={1}
                                                            addonAfter="%"
                                                            disabled={!slot.discount_op}
                                                            style={{ width: 100 }}
                                                        />
                                                        <Button type="text" danger icon={<MinusCircleOutlined />} onClick={() => removeSlot(idx)} />
                                                    </div>
                                                </div>
                                            ))}
                                            <Button type="dashed" block icon={<PlusOutlined />} onClick={addSlot} style={{ marginTop: 8 }}>
                                                添加商品
                                            </Button>
                                        </div>
                                    </div>
                                    </div>
                                </div>
                            </>
                        )}

                        <Space wrap size={[8, 8]}>
                            <Button type="primary" icon={<SearchOutlined />} onClick={handleAnalyze} loading={loading} className="dd-shimmer">
                                生成组合方案
                            </Button>
                            <Button icon={<FileTextOutlined />} onClick={openHistory}>
                                历史方案
                            </Button>
                            <Button icon={<ColumnHeightOutlined />} onClick={() => setColumnConfigOpen(true)}>
                                列配置
                            </Button>
                            <Divider type="vertical" />
                            <span style={{ whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                                <Text type="secondary" style={{ fontSize: 12 }}>输入方式</Text>
                                <ModeSlider
                                    value={aiMode}
                                    onChange={v => updateState({ aiMode: v })}
                                />
                            </span>
                        </Space>
                        <div style={{ color: 'var(--ink-400)', fontSize: 12, marginTop: 8 }}>
                            {aiMode
                                ? '提示：输入自然语言需求即可，例如「总价500左右，含移动电源、自拍杆各一个，整体折扣率低于70%」'
                                : '提示：总价必填；三级品类与数量必填；价格、折扣率限制可选。点击「添加商品」可添加更多商品'}
                        </div>
                        {result?.tokens_used ? (
                            <div style={{ marginTop: 4, color: 'var(--accent-purple)', fontSize: 12 }}>
                                本次分析消耗 <strong>{result.tokens_used}</strong> tokens
                            </div>
                        ) : null}
                    </Card>
                </Col>

                <Col xs={24} md={{ flex: '40%' }} className="dd-module dd-d2">
                    {/* 右侧：方案预览 */}
                    <Card
                        size="small"
                        title={
                            <Space>
                                <ShoppingCartOutlined />
                                <span>方案预览</span>
                            </Space>
                        }
                        styles={{ body: { padding: '12px' } }}
                    >
                        {selectedSolution ? (
                            <>
                                <div style={{ marginBottom: 8 }}>
                                    <Input placeholder="方案名称（可选）" value={solutionName}
                                        onChange={e => {
                                            updateState({ solutionName: e.target.value });
                                            // 同步编辑内容到标题（Sync Editing Content to Title）
                                            document.title = e.target.value.trim()
                                                ? `方案：${e.target.value.trim()} · 智能报价`
                                                : '智能报价 · 让每一次报价恰到好处';
                                        }}
                                        size="small" />
                                </div>
                                <Divider style={{ margin: '8px 0' }} />
                                <div style={{ marginBottom: 8 }}>
                                    <Space direction="vertical" style={{ width: '100%' }}>
                                        <div><Text type="secondary">商品数：</Text><Text strong>{selectedSolution.total_quantity} 件</Text></div>
                                        <div><Text type="secondary">总金额：</Text><CountUpMoney value={selectedSolution.total_price} fontSize={20} strong /></div>
                                        <div><Text type="secondary">平均折扣率：</Text><Text strong>{selectedSolution.total_discount_rate.toFixed(1)}%</Text></div>
                                    </Space>
                                </div>
                                <Divider style={{ margin: '8px 0' }} />
                                {/* 商品明细下拉列表（可收起，无滑动条） */}
                                <div className="dd-collapse-block" style={{ marginBottom: 8 }}>
                                    <div
                                        onClick={() => updateState({ previewItemsOpen: !previewItemsOpen })}
                                        style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', cursor: 'pointer', userSelect: 'none' }}
                                    >
                                        <span style={{ color: '#999', display: 'inline-flex' }}>
                                            {previewItemsOpen ? <DownOutlined /> : <RightOutlined />}
                                        </span>
                                        <Text strong style={{ fontSize: 13 }}>商品明细</Text>
                                        <Tag color="blue" style={{ marginInlineEnd: 0 }}>{selectedSolution.items.length} 件</Tag>
                                        <Text type="secondary" style={{ fontSize: 12 }}>（点击{previewItemsOpen ? '收起' : '展开'}）</Text>
                                        <div style={{ flex: 1 }} />
                                    </div>
                                    {/* grid-rows 技巧：0fr → 1fr 平滑展开/收起 */}
                                    <div style={{
                                        display: 'grid',
                                        gridTemplateRows: previewItemsOpen ? '1fr' : '0fr',
                                        transition: 'grid-template-rows 0.32s cubic-bezier(0.4, 0, 0.2, 1)',
                                    }}>
                                        <div style={{ overflow: 'hidden', minHeight: 0 }}>
                                            <div style={{ padding: '0 10px', background: 'var(--surface)', borderTop: '1px solid var(--ink-100)' }}>
                                                {selectedSolution.items.map((item, idx) => (
                                                    <div key={idx} style={{
                                                        padding: '6px 0', borderBottom: idx < selectedSolution.items.length - 1 ? '1px solid var(--ink-100)' : 'none',
                                                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                                    }}>
                                                        <div style={{ flex: 1, overflow: 'hidden' }}>
                                                            <Tooltip title={item.product_name || item.quick_model}>
                                                                <div style={{ fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                                    {item.product_name || item.quick_model}
                                                                </div>
                                                            </Tooltip>
                                                            <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                                                                {item.quick_model} | {item.brand} | {item.category_level1} | ¥{item.price.toFixed(2)}
                                                            </div>
                                                        </div>
                                                        <div style={{ textAlign: 'right', minWidth: 80 }}>
                                                            <div className="dd-amount" style={{ fontSize: 13 }}>¥{item.subtotal.toFixed(2)}</div>
                                                            <div style={{ fontSize: 11, color: 'var(--ink-400)' }}>×{item.quantity}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <Divider style={{ margin: '8px 0' }} />
                                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                    <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} disabled={!selectedSolution}>
                                        保存方案
                                    </Button>
                                    <Button icon={<DownloadOutlined />} onClick={handleExport} disabled={!savedPlanId}>
                                        导出Excel
                                    </Button>
                                    {selectedSolution && (
                                        <Button icon={<CloseCircleOutlined />} onClick={handleClear} danger size="small">
                                            清除
                                        </Button>
                                    )}
                                </Space>
                                {savedPlanId && (
                                    <Alert type="success" showIcon className="dd-fade-in"
                                        message={<span>已保存（ID: {savedPlanId}），可导出 Excel 表格</span>}
                                        style={{ marginTop: 8 }} />
                                )}
                            </>
                        ) : (
                            <div style={{ color: 'var(--ink-400)', textAlign: 'center', padding: '40px 0' }}>
                                <ShoppingCartOutlined style={{ fontSize: 48, color: 'var(--ink-300)', display: 'block', marginBottom: 16 }} />
                                <Text type="secondary">请先生成方案，然后选择一个方案查看详情</Text>
                            </div>
                        )}
                    </Card>
                </Col>
            </Row>

            {/* 组合方案列表区域 - 全宽 */}
            {result && (
                <div style={{ marginTop: 16 }}>
                    {result.ai_interpretation && (
                        <Alert type="success" showIcon icon={<ThunderboltFilled />}
                            message={<Text strong>{result.ai_interpretation}</Text>}
                            style={{ marginBottom: 12, background: 'var(--accent-amber-bg)', border: '1px solid #f3e3b2' }} />
                    )}
                    {result.total_solutions === 0 && result.diagnosis?.length ? (
                        <Card
                            size="small"
                            className="dd-diagnosis-card dd-fade-up"
                            style={{
                                marginBottom: 12,
                                border: '1px solid var(--accent-purple-border)',
                                background: 'linear-gradient(135deg, var(--accent-purple-bg) 0%, var(--accent-indigo-bg) 100%)',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
                                <div style={{
                                    width: 36, height: 36, borderRadius: '50%',
                                    background: '#7c3aed', color: '#fff',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    marginRight: 10, fontSize: 18, flexShrink: 0,
                                    boxShadow: '0 2px 8px rgba(124,58,237,0.35)',
                                }}>
                                    <RobotOutlined />
                                </div>
                                <div>
                                    <Text strong style={{ fontSize: 15, color: 'var(--accent-purple)', display: 'block' }}>
                                        🤖 智能方案诊断
                                    </Text>
                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                        系统已自动分析无法生成方案的原因，逐项给出调整建议
                                    </Text>
                                </div>
                            </div>
                            <div className="dd-stagger">
                                {(result.diagnosis as SolutionDiagnosis[]).map((d, idx) => {
                                    const adj = d.adjust;
                                    const isCategoryPick = adj?.field === 'category';
                                    const hasApplyBtn = !!adj && !isCategoryPick;
                                    return (
                                        <div key={idx} style={{
                                            padding: '8px 12px', marginBottom: 8,
                                            background: 'var(--surface)', borderRadius: 10,
                                            borderLeft: '3px solid var(--accent-purple)',
                                            boxShadow: '0 1px 3px rgba(124,58,237,0.08)',
                                        }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
                                                <Tag color="purple" style={{ marginRight: 6 }}>诊断 {idx + 1}</Tag>
                                                <Text strong style={{ color: 'var(--accent-purple)' }}>{d.title}</Text>
                                            </div>
                                            {hasApplyBtn && (
                                                <Button
                                                    size="small"
                                                    icon={<RocketOutlined />}
                                                    onClick={() => applyAdjust(d)}
                                                    style={{
                                                        flexShrink: 0,
                                                        marginLeft: 8,
                                                        background: 'linear-gradient(135deg, var(--accent-purple) 0%, #8b5cf6 100%)',
                                                        border: 'none',
                                                        color: '#fff',
                                                        fontWeight: 600,
                                                        boxShadow: '0 2px 6px rgba(124,58,237,0.35)',
                                                    }}
                                                >
                                                    一键应用建议
                                                </Button>
                                            )}
                                        </div>
                                        <div style={{ color: 'var(--ink-500)', marginBottom: 4 }}>{d.detail}</div>
                                        <div>
                                            <BulbOutlined style={{ color: 'var(--accent-amber)', marginRight: 6 }} />
                                            <Text strong style={{ color: 'var(--accent-green)' }}>建议：</Text>
                                            <Text style={{ color: 'var(--accent-green)' }}>{d.suggestion}</Text>
                                        </div>
                                        {isCategoryPick && adj?.slot_index != null && (
                                            <div style={{ marginTop: 6, display: 'flex', alignItems: 'center' }}>
                                                <Text style={{ marginRight: 8, color: 'var(--accent-purple)', flexShrink: 0 }}>更换为：</Text>
                                                <Select
                                                    showSearch
                                                    size="small"
                                                    placeholder="选择其他三级品类"
                                                    style={{ width: 220 }}
                                                    options={level3Categories.map((c) => ({ value: c, label: c }))}
                                                    onChange={(v) => {
                                                        if (adj.slot_index != null) {
                                                            const fi = backendToFrontSlotIndex(adj.slot_index);
                                                            if (!slotsOpen) updateState({ slotsOpen: true });
                                                            updateSlot(fi, { category: v });
                                                            flashHighlight(`sol-cat-${fi}`);
                                                            message.success('✅ 已更换品类（品类选择框已高亮），请点击「生成方案」重新生成');
                                                        }
                                                    }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                );
                                })}
                            </div>
                        </Card>
                    ) : (
                        <Alert
                            type={result.total_solutions > 0 ? 'info' : 'warning'}
                            showIcon
                            message={result.message}
                            style={{ marginBottom: 12 }}
                        />
                    )}

                    {result.solutions?.length > 0 && (
                        <>
                            <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Text type="secondary">共 {result.total_solutions} 个方案</Text>
                                <Button
                                    size="small"
                                    icon={sortOrder === 'asc' ? <span>↑</span> : sortOrder === 'desc' ? <span>↓</span> : <span>★</span>}
                                    onClick={() => {
                                        // 三态循环：智能（贴近用户输入）→ 升序 → 降序
                                        const cycle: ('smart' | 'asc' | 'desc')[] = ['smart', 'asc', 'desc'];
                                        const newOrder = cycle[(cycle.indexOf(sortOrder) + 1) % cycle.length];
                                        setSortOrder(newOrder);
                                        let sorted = [...(result?.solutions || [])];
                                        if (newOrder === 'asc') {
                                            sorted.sort((a, b) => a.total_price - b.total_price);
                                        } else if (newOrder === 'desc') {
                                            sorted.sort((a, b) => b.total_price - a.total_price);
                                        }
                                        // 'smart' 不排序，保留后端"最接近用户输入"的顺序
                                        updateState({
                                            result: result ? { ...result, solutions: sorted } : null
                                        });
                                    }}
                                >
                                    按价格 {sortOrder === 'asc' ? '升序' : sortOrder === 'desc' ? '降序' : '智能'}
                                </Button>
                            </div>
                            <div className="dd-fade-up dd-stagger dd-fade-edge" style={{ maxHeight: 600, overflowY: 'auto' }}>
                                {result.solutions.map((sol: SolutionCombination, idx: number) => (
                                    <Card
                                        key={idx}
                                        size="small"
                                        className={`dd-solution-card ${selectedSolutionIdx === idx ? 'ant-card-selected' : ''}`}
                                        style={{
                                            marginBottom: 12,
                                            cursor: 'pointer',
                                            background: selectedSolutionIdx === idx ? 'var(--ink-50)' : 'var(--surface)',
                                        }}
                                        onClick={() => selectSolution(idx)}
                                        title={
                                            <Space size={6}>
                                                <span className="dd-solution-number">{(idx + 1).toString().padStart(2, '0')}</span>
                                                <Text strong>方案</Text>
                                                <Tag color="default" style={{ borderRadius: 999 }}>¥{sol.total_price.toFixed(2)}</Tag>
                                                <Tag color="default" style={{ borderRadius: 999 }}>{sol.total_quantity} 件</Tag>
                                                <Tag color="default" style={{ borderRadius: 999 }}>{sol.total_discount_rate.toFixed(1)}%</Tag>
                                            </Space>
                                        }
                                        extra={
                                            selectedSolutionIdx === idx
                                                ? <Tag color="success" icon={<CheckCircleOutlined />} style={{ borderRadius: 999 }}>已选</Tag>
                                                : null
                                        }
                                    >
                                        <Table
                                            dataSource={sol.items}
                                            columns={solutionItemColumns}
                                            rowKey="product_id"
                                            size="small"
                                            pagination={false}
                                            summary={() => (
                                                <Table.Summary.Row>
                                                    <Table.Summary.Cell index={0} colSpan={5}>
                                                        <Text strong style={{ float: 'right' }}>合计：</Text>
                                                    </Table.Summary.Cell>
                                                    <Table.Summary.Cell index={1}>
                                                        <Text strong style={{ color: 'var(--accent-red)' }}>¥{sol.total_price.toFixed(2)}</Text>
                                                    </Table.Summary.Cell>
                                                </Table.Summary.Row>
                                            )}
                                        />
                                    </Card>
                                ))}
                            </div>
                        </>
                    )}
                    {!result.solutions?.length && !result.ai_interpretation && (
                        <div className="dd-empty" style={{ padding: '56px 0 48px' }}>
                            <div className="dd-empty-mark">✦</div>
                            <div className="dd-empty-title">输入需求，生成最优搭配</div>
                            <div className="dd-empty-desc">
                                例如：我需要一个价值 500 元的礼盒，包含三个产品…
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* 无结果时的默认提示 */}
            {!result && (
                <div className="dd-empty" style={{ padding: '72px 0 64px' }}>
                    <div className="dd-empty-mark">✦</div>
                    <div className="dd-empty-title">输入需求，生成最优搭配</div>
                    <div className="dd-empty-desc">
                        例如：我需要一个价值 500 元的礼盒，包含三个产品，整体折扣率低于 70%…
                    </div>
                </div>
            )}

            {/* 推荐方案区域 */}
            {recommendedSolutions.length > 0 && (
                <>
                    <Divider style={{ margin: '16px 0 8px' }} />
                    <Card
                        size="small"
                        className="dd-recommend-card dd-fade-up"
                        title={
                            <Space>
                                <ShopOutlined style={{ color: 'var(--accent-green)' }} />
                                <span style={{ fontWeight: 600 }}>推荐方案</span>
                                <Tag color="success" style={{ borderRadius: 999 }}>来自其他公司</Tag>
                                <Typography.Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
                                    以下为使用其他公司商品生成的推荐方案，可供参考
                                </Typography.Text>
                            </Space>
                        }
                        style={{ background: 'linear-gradient(135deg, var(--accent-green-bg) 0%, var(--surface) 100%)', border: '1px solid var(--accent-green-border)', marginTop: 8 }}
                    >
                        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                            {recommendedSolutions.map((sol: any, idx: number) => (
                                <Card
                                    key={idx}
                                    size="small"
                                    style={{ marginBottom: 8, border: '1px solid var(--accent-green-border)' }}
                                    title={
                                        <Space>
                                            <Text strong>推荐方案 {idx + 1}</Text>
                                            <Tag color="blue">¥{sol.total_price?.toFixed(2)}</Tag>
                                            <Tag color="green">{sol.total_quantity} 件</Tag>
                                            {sol.source_company_name && (
                                                <Tag color={sol.source_role === 'super_admin' ? 'red' : 'blue'}>
                                                    {sol.source_company_name}
                                                </Tag>
                                            )}
                                        </Space>
                                    }
                                >
                                    <Table
                                        dataSource={sol.items || []}
                                        columns={[
                                            { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 120, ellipsis: true },
                                            { title: '商品名称', dataIndex: 'product_name', key: 'product_name', width: 140, ellipsis: true },
                                            { title: '品牌', dataIndex: 'brand', key: 'brand', width: 70 },
                                            { title: '单价', dataIndex: 'price', key: 'price', width: 80, render: (v: number) => `¥${v?.toFixed(2) || '0.00'}` },
                                            { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 50 },
                                            { title: '小计', dataIndex: 'subtotal', key: 'subtotal', width: 80, render: (v: number) => <span style={{ color: 'var(--accent-red)' }}>¥{v?.toFixed(2) || '0.00'}</span> },
                                        ]}
                                        rowKey="product_id"
                                        size="small"
                                        pagination={false}
                                    />
                                </Card>
                            ))}
                        </div>
                    </Card>
                </>
            )}

            {/* 推荐产品区域 */}
            {recommendedProducts.length > 0 && (
                <>
                    <Divider style={{ margin: '16px 0 8px' }} />
                    <Card
                        size="small"
                        className="dd-recommend-card dd-fade-up"
                        title={
                            <Space>
                                <ShopOutlined style={{ color: 'var(--accent-amber)' }} />
                                <span style={{ fontWeight: 600 }}>推荐商品</span>
                                <Tag color="warning" style={{ borderRadius: 999 }}>来自其他公司</Tag>
                                <Typography.Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
                                    来自其他公司的推荐商品，可加入方案，保存时需联系对应公司购买
                                </Typography.Text>
                            </Space>
                        }
                        style={{ background: 'linear-gradient(135deg, var(--accent-amber-bg) 0%, var(--surface) 100%)', border: '1px solid var(--accent-amber-border)', marginTop: 8 }}
                    >
                        <Table
                            dataSource={recommendedProducts}
                            rowKey="id"
                            size="small"
                            pagination={false}
                            scroll={{ x: 800 }}
                            columns={[
                                { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 130, ellipsis: { showTitle: false }, render: (v: string) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
                                { title: '商品名称', dataIndex: 'product_name', key: 'product_name', width: 150, ellipsis: { showTitle: false }, render: (v: string) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
                                { title: '品牌', dataIndex: 'brand', key: 'brand', width: 70 },
                                {
                                    title: '图片', key: 'image', width: 65,
                                    render: (_: unknown, r: RecommendedProduct) => {
                                        if (!r.image) return <span style={{ color: '#ccc', fontSize: 12 }}>无图</span>;
                                        const src = r.image.startsWith('data:') ? r.image : `data:image/png;base64,${r.image}`;
                                        return (
                                            <Tooltip title={<img src={src} style={{ maxWidth: 300, maxHeight: 300 }} alt="预览" />}>
                                                <img src={src} alt="" style={{ width: 50, height: 50, objectFit: 'cover', borderRadius: 4, border: '1px solid var(--ink-100)', cursor: 'pointer' }} />
                                            </Tooltip>
                                        );
                                    },
                                },
                                { title: '代发价', dataIndex: 'price', key: 'price', width: 80, render: (v: number) => <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>¥{Number(v).toFixed(2)}</span> },
                                {
                                    title: '来源公司', dataIndex: 'source_company_name', key: 'source_company_name', width: 120,
                                    render: (v: string, r: RecommendedProduct) => (
                                        <Tag color={r.source_role === 'super_admin' ? 'red' : 'blue'}>{v || r.source_role}</Tag>
                                    ),
                                },
                            ]}
                        />
                        <div style={{ textAlign: 'center', marginTop: 8, color: '#999', fontSize: 12 }}>
                            如需购买推荐商品，请联系对应公司
                        </div>
                    </Card>
                </>
            )}

            {/* 列显示配置对话框 */}
            <ColumnDisplayConfig
                open={columnConfigOpen}
                pageType={pageTypeForConfig}
                title="方案商品列显示配置"
                onClose={() => setColumnConfigOpen(false)}
                onSaved={() => loadSolutionColumnConfig()}
            />

            {/* 历史方案对话框 */}
            <Modal title="📂 历史方案" open={historyOpen} onCancel={() => setHistoryOpen(false)} footer={null} width={680} destroyOnHidden>
                {historyLoading ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>正在加载历史方案...</div>
                ) : historyList.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>还没有保存过方案，生成方案后可在这里查看和复用</div>
                ) : (
                    <Table
                        dataSource={historyList}
                        rowKey="id"
                        size="small"
                        pagination={false}
                        scroll={{ x: 640 }}
                        columns={[
                            { title: '方案名称', dataIndex: 'name', key: 'name', width: 130, ellipsis: { showTitle: false }, render: (v) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
                            { title: '需求摘要', dataIndex: 'requirement', key: 'requirement', width: 160, ellipsis: { showTitle: false }, render: (v) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
                            { title: '商品数', dataIndex: 'items_count', key: 'items_count', width: 55, render: (v: number) => v ?? '-' },
                            { title: '金额', dataIndex: 'total_amount', key: 'total_amount', width: 70, render: (v: number) => `¥${(v || 0).toFixed(2)}` },
                            { title: '状态', dataIndex: 'status', key: 'status', width: 50, render: (v: string) => v === 'draft' ? '草稿' : v },
                            { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 130 },
                            {
                                title: '操作', key: 'action', width: 100,
                                render: (_: unknown, record: any) => (
                                    <Space size="small">
                                        <Button size="small" type="primary" ghost icon={<HistoryOutlined />}
                                            onClick={() => handleReusePlan(record.id)}>复用</Button>
                                        <Button size="small" danger icon={<DeleteOutlined />}
                                            onClick={() => handleDeletePlan(record.id)}>删除</Button>
                                    </Space>
                                ),
                            },
                        ]}
                    />
                )}
            </Modal>
        </div>
    );
}
