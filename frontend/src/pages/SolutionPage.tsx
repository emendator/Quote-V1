import { useState, useEffect, useCallback, useRef } from 'react';
import { Input, Button, Select, Row, Col, Divider, message, Table, Space, Switch, Tooltip, Modal, InputNumber, Typography, Alert, Card, Tag } from 'antd';
import { SearchOutlined, ThunderboltOutlined, ThunderboltFilled, DeleteOutlined, DownloadOutlined, SaveOutlined, ShoppingCartOutlined, FileTextOutlined, HistoryOutlined, ShopOutlined, WarningOutlined } from '@ant-design/icons';
import { analyzeSolution, saveSolution, exportSolution, listSolutions, getSolutionDetail, deleteSolution, fetchProductsByIds, fetchCategories, fetchBrands, fetchCategoryLevel2, fetchCategoryLevel3 } from '../services/api';
import type { Product, SolutionCandidate, SolutionAnalyzeResult, SolutionItemData } from '../types';
import { usePageState } from '../store/PageStateContext';

const { TextArea } = Input;
const { Text, Title } = Typography;

// 价格档位选项（与智能查询页一致）
const PRICE_RANGES = [
    { label: '全部', query: '' },
    { label: '≤ 50', query: '价格在0到50' },
    { label: '50 - 100', query: '价格在50到100' },
    { label: '100 - 200', query: '价格在100到200' },
    { label: '200 - 300', query: '价格在200到300' },
    { label: '300 - 400', query: '价格在300到400' },
    { label: '400 - 500', query: '价格在400到500' },
    { label: '500 - 600', query: '价格在500到600' },
    { label: '600 - 700', query: '价格在600到700' },
    { label: '700 - 800', query: '价格在700到800' },
    { label: '800 - 900', query: '价格在800到900' },
    { label: '900 - 1000', query: '价格在900到1000' },
    { label: '≥ 1000', query: '价格在1000到999999' },
];

export default function SolutionPage() {
    const [loading, setLoading] = useState(false);

    // ====== 持久化状态：切换页面后保留 ======
    const [pageState, setPageState] = usePageState('solution', {
        requirement: '',
        useAI: false,
        result: null as SolutionAnalyzeResult | null,
        filterCat1: undefined as string | undefined,
        filterBrand: undefined as string | undefined,
        filterCat2: undefined as string | undefined,
        filterCat3: undefined as string | undefined,
        filterPrice: '',
        filterNego: '',
        filterPurchase: '',
        filterRetail: '',
        filterDiscount: '',
        solutionName: '',
        solutionRemark: '',
        savedPlanId: null as number | null,
    });

    const { requirement, useAI, result } = pageState;
    const { filterCat1, filterBrand, filterCat2, filterCat3, filterPrice, filterNego, filterPurchase, filterRetail, filterDiscount } = pageState;
    const { solutionName, solutionRemark, savedPlanId } = pageState;

    const updateState = useCallback((patch: Partial<typeof pageState>) => {
        setPageState({ ...pageState, ...patch });
    }, [pageState, setPageState]);

    // 筛选器数据（非持久化）
    const [categories, setCategories] = useState<string[]>([]);
    const [brands, setBrands] = useState<string[]>([]);
    const [categoryLevel2, setCategoryLevel2] = useState<string[]>([]);
    const [categoryLevel3, setCategoryLevel3] = useState<string[]>([]);

    // 方案：已选商品 { product_id: quantity }
    const [selectedItems, setSelectedItems] = useState<Map<number, number>>(() => {
        try {
            const raw = localStorage.getItem('solution_cart');
            if (raw) return new Map<number, number>(JSON.parse(raw));
        } catch { /* ignore */ }
        return new Map<number, number>();
    });
    // 购物车商品详情（从 localStorage 加载后自动获取）
    const [cartProducts, setCartProducts] = useState<Product[]>([]);

    // 推荐产品
    // 购买提示弹窗
    const [purchaseModalOpen, setPurchaseModalOpen] = useState(false);
    const [purchaseItems, setPurchaseItems] = useState<SolutionCandidate[]>([]);

    // 历史方案
    const [historyOpen, setHistoryOpen] = useState(false);
    const [historyList, setHistoryList] = useState<any[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);

    useEffect(() => {
        fetchCategories().then(setCategories).catch(() => { });
        fetchBrands().then(setBrands).catch(() => { });
        fetchCategoryLevel2().then(setCategoryLevel2).catch(() => { });
        fetchCategoryLevel3().then(setCategoryLevel3).catch(() => { });
    }, []);

    const isFirstRender = useRef(true);

    // 加载购物车商品详情
    useEffect(() => {
        if (selectedItems.size > 0) {
            const ids = Array.from(selectedItems.keys());
            fetchProductsByIds(ids).then(products => {
                setCartProducts(products);
            }).catch(() => { });
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // 筛选项变动时自动触发分析（排除首次）
    useEffect(() => {
        if (isFirstRender.current) {
            isFirstRender.current = false;
            return;
        }
        // 每次筛选条件变化自动分析（防抖 500ms）
        const timer = setTimeout(() => handleAnalyzeWithRecommend(), 500);
        return () => clearTimeout(timer);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filterCat1, filterBrand, filterCat2, filterCat3, filterPrice, filterNego, filterPurchase, filterRetail, filterDiscount]);

    // 同步 selectedItems 到 localStorage，并通知其他组件
    useEffect(() => {
        localStorage.setItem('solution_cart', JSON.stringify([...selectedItems.entries()]));
        window.dispatchEvent(new CustomEvent('solutionCartChange', { detail: selectedItems.size }));
    }, [selectedItems]);

    const buildFilters = () => {
        const filters: Record<string, unknown> = {};
        if (filterCat1) filters.category_level1 = filterCat1;
        if (filterBrand) filters.brand = filterBrand;
        if (filterCat2) filters.category_level2 = filterCat2;
        if (filterCat3) filters.category_level3 = filterCat3;
        // 价格筛选（解析 PRICE_RANGES 的 query 字符串）
        if (filterPrice) {
            const m = filterPrice.match(/价格在(\d+)到(\d+)/);
            if (m) { filters.price_min = parseFloat(m[1]); filters.price_max = parseFloat(m[2]); }
        }
        if (filterNego) {
            const m = filterNego.match(/价格在(\d+)到(\d+)/);
            if (m) { filters.negotiation_price_min = parseFloat(m[1]); filters.negotiation_price_max = parseFloat(m[2]); }
        }
        if (filterPurchase) {
            const m = filterPurchase.match(/价格在(\d+)到(\d+)/);
            if (m) { filters.purchase_price_min = parseFloat(m[1]); filters.purchase_price_max = parseFloat(m[2]); }
        }
        if (filterRetail) {
            const m = filterRetail.match(/价格在(\d+)到(\d+)/);
            if (m) { filters.retail_price_min = parseFloat(m[1]); filters.retail_price_max = parseFloat(m[2]); }
        }
        if (filterDiscount) {
            const m = filterDiscount.match(/折扣率在(\d+)到(\d+)/);
            if (m) { filters.discount_rate_min = parseFloat(m[1]); filters.discount_rate_max = parseFloat(m[2]); }
        }
        return filters;
    };

    const handleAnalyze = async () => {
        if (!requirement.trim() && !filterCat1 && !filterBrand && !filterCat2 && !filterCat3) {
            message.warning('请输入客户需求或选择筛选条件');
            return;
        }
        setLoading(true);
        try {
            const data = await analyzeSolution({
                requirement: requirement.trim(),
                use_ai: useAI,
                filters: buildFilters(),
            });
            updateState({ result: data, savedPlanId: null });
            if (data.total_candidates > 0) {
                message.success(`找到 ${data.total_candidates} 个候选商品`);
            } else {
                message.info(data.message || '未找到匹配的商品');
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '分析失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    // 处理选品
    const toggleItem = (productId: number) => {
        setSelectedItems(prev => {
            const next = new Map(prev);
            if (next.has(productId)) {
                next.delete(productId);
            } else {
                next.set(productId, 1);
            }
            return next;
        });
    };

    const updateQuantity = (productId: number, qty: number) => {
        setSelectedItems(prev => {
            const next = new Map(prev);
            if (qty <= 0) {
                next.delete(productId);
            } else {
                next.set(productId, qty);
            }
            return next;
        });
    };

    const clearSelected = () => setSelectedItems(new Map());

    // 分析需求（推荐产品会由后端直接返回在 candidates 中）
    const handleAnalyzeWithRecommend = async () => {
        await handleAnalyze();
    };

    // 保存方案
    const handleSave = async () => {
        if (selectedItems.size === 0) {
            message.warning('请至少选择一个商品');
            return;
        }

        // 检查购物车中是否包含推荐产品（从 analyze 结果中查找 is_recommended 标记）
        const selectedCandidates = (result?.candidates ?? []).filter(c => selectedItems.has(c.id));
        const cartRecommended = selectedCandidates.filter(c => c.is_recommended);

        if (cartRecommended.length > 0) {
            // 有推荐产品，弹出购买提示弹窗
            setPurchaseItems(cartRecommended);
            setPurchaseModalOpen(true);
            return;
        }

        // 无推荐产品，正常保存
        await doSave();
    };

    const doSave = async () => {
        const items: SolutionItemData[] = [];
        selectedItems.forEach((qty, productId) => {
            items.push({ product_id: productId, quantity: qty });
        });
        const name = solutionName.trim() || `方案_${new Date().toLocaleDateString('zh-CN')}`;
        try {
            const res = await saveSolution({
                name,
                requirement: requirement || '（无需求文本）',
                remark: solutionRemark,
                ai_enabled: useAI,
                items,
            });
            updateState({ savedPlanId: res.plan_id });
            message.success(`方案已保存，共 ${res.items_count} 个商品，总金额 ¥${res.total_amount}。如需清空购物车请点击"清空"按钮`);
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

    // 图片列渲染（与智能查询保持一致）
    const renderImage = (_: unknown, record: any) => {
        const v = record.image;
        if (!v || v === '') return <span style={{ color: '#ccc', fontSize: 12 }}>无图</span>;
        const src = v.startsWith('data:') ? v : `data:image/png;base64,${v}`;
        return (
            <Tooltip title={<img src={src} style={{ maxWidth: 300, maxHeight: 300 }} alt="预览" />}>
                <img src={src} alt="" style={{ width: 50, height: 50, objectFit: 'cover', borderRadius: 4, border: '1px solid #f0f0f0', cursor: 'pointer' }} />
            </Tooltip>
        );
    };

    // 操作列渲染
    const renderAction = (_: unknown, record: SolutionCandidate) => {
        const selected = selectedItems.has(record.id);
        return (
            <Button size="small" type={selected ? 'primary' : 'default'} onClick={() => toggleItem(record.id)}>
                {selected ? '已选' : '添加'}
            </Button>
        );
    };

    // 候选商品表格列（不含来源列，操作列在最前面）
    const candidateColumns: any[] = [
        { title: '操作', key: 'action', width: 80, render: renderAction },
        { title: '图片', key: 'image', width: 60, render: renderImage },
        { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 150, ellipsis: true, render: (v: string) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
        { title: '产品名称', dataIndex: 'product_name', key: 'product_name', width: 160, ellipsis: true, render: (v: string) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
        { title: '品牌', dataIndex: 'brand', key: 'brand', width: 70 },
        { title: '一级品类', dataIndex: 'category_level1', key: 'category_level1', width: 80 },
        { title: '二级品类', dataIndex: 'category_level2', key: 'category_level2', width: 80 },
        { title: '代发价', dataIndex: 'price', key: 'price', width: 80, render: (v: number) => (v !== null && v !== undefined ? <Text strong style={{ color: '#cf1322' }}>¥{Number(v).toFixed(2)}</Text> : '-') },
        { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 70 },
    ];

    // 推荐产品表格列（含来源列，操作列在最前面）
    const recommendedColumns: any[] = [
        { title: '操作', key: 'action', width: 80, render: renderAction },
        { title: '图片', key: 'image', width: 60, render: renderImage },
        { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 150, ellipsis: true, render: (v: string) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
        { title: '产品名称', dataIndex: 'product_name', key: 'product_name', width: 160, ellipsis: true, render: (v: string) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
        { title: '品牌', dataIndex: 'brand', key: 'brand', width: 70 },
        { title: '一级品类', dataIndex: 'category_level1', key: 'category_level1', width: 80 },
        { title: '二级品类', dataIndex: 'category_level2', key: 'category_level2', width: 80 },
        { title: '代发价', dataIndex: 'price', key: 'price', width: 80, render: (v: number) => (v !== null && v !== undefined ? <Text strong style={{ color: '#cf1322' }}>¥{Number(v).toFixed(2)}</Text> : '-') },
        { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 70 },
        {
            title: '来源', key: 'source', width: 90,
            render: (_: unknown, record: any) => (
                <Tag color={record.source_role === 'super_admin' ? 'red' : 'blue'}>{record.source_company_name || record.source_role}</Tag>
            ),
        },
    ];

    // 已选商品列表：优先用分析结果中的信息，回退到独立加载的购物车详情
    const selectedFromResult = result?.candidates.filter(c => selectedItems.has(c.id)) ?? [];
    const selectedFromCart = cartProducts.filter(c => selectedItems.has(c.id) && !selectedFromResult.find(r => r.id === c.id));
    const selectedDisplay = [...selectedFromResult, ...selectedFromCart.map(c => ({
        id: c.id, quick_model: c.quick_model, product_model: c.product_model,
        product_name: c.product_name, brand: c.brand, category_level1: c.category_level1,
        category_level2: c.category_level2, specification: c.specification,
        price: c.price, supply_status: c.supply_status,
    } as SolutionCandidate))];
    const totalAmount = selectedDisplay.reduce((sum, c) => sum + c.price * (selectedItems.get(c.id) ?? 0), 0);
    const totalQty = selectedDisplay.reduce((sum, c) => sum + (selectedItems.get(c.id) ?? 0), 0);

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
            const items = (detail.items as any[]) || [];
            const newMap = new Map<number, number>();
            for (const item of items) {
                newMap.set(item.product_id, item.quantity || 1);
            }
            setSelectedItems(newMap);
            updateState({
                solutionName: detail.name as string || '',
                solutionRemark: detail.remark as string || '',
                requirement: detail.requirement as string || '',
            });
            setHistoryOpen(false);
            message.success('已加载历史方案，请点击「分析需求」更新候选商品');
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

    // 渲染预览卡片内容
    const renderPreviewCard = () => {
        // 有可展示的选品（来自分析结果或购物车加载）
        if (selectedDisplay.length > 0) {
            return (
                <>
                    <div style={{ marginBottom: 8 }}>
                        <Input placeholder="方案名称（可选）" value={solutionName}
                            onChange={e => updateState({ solutionName: e.target.value })} size="small" />
                    </div>
                    <div style={{ marginBottom: 8 }}>
                        <Input.TextArea placeholder="备注说明（可选，会出现在导出的文档中）" value={solutionRemark}
                            onChange={e => updateState({ solutionRemark: e.target.value })} rows={2} size="small" />
                    </div>
                    <div style={{ maxHeight: 360, overflow: 'auto' }}>
                        {selectedDisplay.map(c => {
                            const qty = selectedItems.get(c.id) ?? 1;
                            const isRecommended = (c as any).is_recommended === true;
                            return (
                                <div key={c.id} style={{
                                    padding: '6px 0', borderBottom: '1px solid #f0f0f0',
                                    display: 'flex', alignItems: 'center', gap: 8,
                                    background: isRecommended ? '#fffbe6' : 'transparent',
                                }}>
                                    <div style={{ flex: 1, overflow: 'hidden' }}>
                                        <Tooltip title={c.product_name || c.quick_model}>
                                            <div style={{ fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {c.product_name || c.quick_model}
                                                {isRecommended && <Tag color="warning" style={{ marginLeft: 4, fontSize: 11 }}>推荐</Tag>}
                                            </div>
                                        </Tooltip>
                                        <div style={{ fontSize: 12, color: '#999' }}>
                                            {c.brand} | ¥{c.price.toFixed(2)}
                                            {isRecommended && (
                                                <span style={{ marginLeft: 8, color: '#faad14' }}>
                                                    {(c as any).source_company_name || '外部推荐'}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <InputNumber min={1} max={99999} value={qty}
                                        onChange={v => updateQuantity(c.id, v ?? 1)}
                                        size="small" style={{ width: 65 }} />
                                    <Text style={{ width: 70, textAlign: 'right', fontSize: 13, color: '#cf1322' }}>
                                        ¥{(c.price * qty).toFixed(2)}
                                    </Text>
                                    <Button type="text" size="small" danger icon={<DeleteOutlined />}
                                        onClick={() => toggleItem(c.id)} />
                                </div>
                            );
                        })}
                    </div>
                    <Divider style={{ margin: '8px 0' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>共 <strong>{selectedItems.size}</strong> 种 / <strong>{totalQty}</strong> 件</Text>
                        <Text strong style={{ fontSize: 16, color: '#cf1322' }}>¥{totalAmount.toFixed(2)}</Text>
                    </div>
                    {savedPlanId && (
                        <Alert type="success" showIcon message={`已保存（ID: ${savedPlanId}）`} style={{ marginTop: 8 }} />
                    )}
                </>
            );
        }
        // 有购物车但还没加载完或没分析
        if (selectedItems.size > 0 && selectedDisplay.length === 0) {
            return (
                <div style={{ color: '#999', textAlign: 'center', padding: '20px 0' }}>
                    购物车中有 <strong>{selectedItems.size}</strong> 个商品，<br />
                    正在加载商品信息...
                </div>
            );
        }
        // 空状态
        return (
            <div style={{ color: '#999', textAlign: 'center', padding: '20px 0' }}>
                请在智能查询页加入商品，<br />
                或从左侧搜索后「添加」选择商品
            </div>
        );
    };

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            {/* 需求输入区 */}
            <Card size="small" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                    <Col span={16}>
                        <TextArea
                            value={requirement}
                            onChange={e => updateState({ requirement: e.target.value })}
                            placeholder="请输入客户项目需求，例如：&#10;需要一批价格在50-100元的充电宝，品牌飞利浦，用于投标项目"
                            rows={3}
                            style={{ fontSize: 14 }}
                        />
                    </Col>
                    <Col span={8}>
                        <div style={{ marginBottom: 8 }}>
                            <Space>
                                <Tooltip title={useAI ? 'AI 模式：调用大模型分析需求' : '普通模式：使用规则匹配'}>
                                    <span>
                                        {useAI ? <ThunderboltFilled style={{ color: '#faad14' }} /> : <ThunderboltOutlined style={{ color: '#d9d9d9' }} />}
                                        <Switch size="small" checked={useAI} onChange={v => updateState({ useAI: v })} style={{ marginLeft: 4 }} />
                                        <span style={{ marginLeft: 4, fontSize: 12, color: useAI ? '#faad14' : '#999' }}>AI</span>
                                    </span>
                                </Tooltip>
                                <Button type="primary" icon={<SearchOutlined />} onClick={handleAnalyzeWithRecommend} loading={loading} size="large">
                                    分析需求
                                </Button>
                                <Button icon={<FileTextOutlined />} onClick={openHistory} size="large">
                                    历史方案
                                </Button>
                            </Space>
                        </div>
                        <div style={{ color: '#999', fontSize: 12 }}>
                            提示：输入需求后点击「分析需求」，系统将自动筛选匹配的商品
                        </div>
                    </Col>
                </Row>
            </Card>

            {/* 筛选条件 */}
            <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
                <Col span={6}>
                    <Select placeholder="一级品类" allowClear showSearch value={filterCat1} onChange={v => updateState({ filterCat1: v })}
                        style={{ width: '100%' }} options={categories.map(c => ({ value: c, label: c }))} />
                </Col>
                <Col span={6}>
                    <Select placeholder="品牌" allowClear showSearch value={filterBrand} onChange={v => updateState({ filterBrand: v })}
                        style={{ width: '100%' }} options={brands.map(b => ({ value: b, label: b }))} />
                </Col>
                <Col span={6}>
                    <Select placeholder="二级品类" allowClear showSearch value={filterCat2} onChange={v => updateState({ filterCat2: v })}
                        style={{ width: '100%' }} options={categoryLevel2.map(c => ({ value: c, label: c }))} />
                </Col>
                <Col span={6}>
                    <Select placeholder="三级品类" allowClear showSearch value={filterCat3} onChange={v => updateState({ filterCat3: v })}
                        style={{ width: '100%' }} options={categoryLevel3.map(c => ({ value: c, label: c }))} />
                </Col>
            </Row>

            {/* 第二行：价格 / 折扣率筛选 */}
            <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
                <Col span={4}>
                    <Select placeholder="代发价" allowClear value={filterPrice || undefined}
                        onChange={(v) => updateState({ filterPrice: v || '' })} style={{ width: '100%' }}
                        options={PRICE_RANGES.map(r => ({ value: r.query, label: r.label }))} />
                </Col>
                <Col span={5}>
                    <Select placeholder="备货商谈价" allowClear value={filterNego || undefined}
                        onChange={(v) => updateState({ filterNego: v || '' })} style={{ width: '100%' }}
                        options={PRICE_RANGES.map(r => ({ value: r.query, label: r.label }))} />
                </Col>
                <Col span={4}>
                    <Select placeholder="进货价" allowClear value={filterPurchase || undefined}
                        onChange={(v) => updateState({ filterPurchase: v || '' })} style={{ width: '100%' }}
                        options={PRICE_RANGES.map(r => ({ value: r.query, label: r.label }))} />
                </Col>
                <Col span={4}>
                    <Select placeholder="零售价" allowClear value={filterRetail || undefined}
                        onChange={(v) => updateState({ filterRetail: v || '' })} style={{ width: '100%' }}
                        options={PRICE_RANGES.map(r => ({ value: r.query, label: r.label }))} />
                </Col>
                <Col span={4}>
                    <Select placeholder="折扣率" allowClear value={filterDiscount || undefined}
                        onChange={(v) => updateState({ filterDiscount: v || '' })} style={{ width: '100%' }}
                        options={[
                            { value: '', label: '全部' },
                            { value: '折扣率在0到30', label: '≤ 30%' },
                            { value: '折扣率在30到50', label: '30% - 50%' },
                            { value: '折扣率在50到70', label: '50% - 70%' },
                            { value: '折扣率在70到90', label: '70% - 90%' },
                            { value: '折扣率在90到100', label: '≥ 90%' },
                        ]} />
                </Col>
            </Row>

            <Divider style={{ margin: '8px 0' }} />

            <Row gutter={16}>
                {/* 左侧：候选商品 / 提示 */}
                <Col span={result?.total_candidates != null ? (result.total_candidates > 0 ? 16 : 24) : 16}>
                    {/* 分析结果 */}
                    {result && (
                        <>
                            {result.ai_interpretation && (
                                <Alert type="success" showIcon icon={<ThunderboltFilled />}
                                    message={<Text strong>{result.ai_interpretation}</Text>}
                                    style={{ marginBottom: 12, background: '#fffbe6', border: '1px solid #ffe58f' }} />
                            )}
                            <Alert type="info" showIcon message={result.message} style={{ marginBottom: 12 }} />

                            {result.candidates?.filter(c => !c.is_recommended).length > 0 && (
                                <Card
                                    title={
                                        <Space>
                                            <span>候选商品</span>
                                            <span style={{ fontSize: 12, color: '#999', fontWeight: 'normal' }}>
                                                （共 {result.candidates.filter(c => !c.is_recommended).length} 个）
                                            </span>
                                        </Space>
                                    }
                                    size="small"
                                >
                                    <Table
                                        dataSource={result.candidates.filter(c => !c.is_recommended)}
                                        columns={candidateColumns}
                                        rowKey="id"
                                        size="small"
                                        pagination={result.total_candidates > 20 ? { pageSize: 20 } : false}
                                        scroll={{ x: 900 }}
                                    />
                                </Card>
                            )}

                            {/* 推荐产品：单独分区展示 */}
                            {result.candidates?.filter(c => c.is_recommended).length > 0 && (
                                <Card
                                    title={
                                        <Space>
                                            <ShopOutlined style={{ color: '#faad14' }} />
                                            <span>推荐产品（来自关联公司）</span>
                                        </Space>
                                    }
                                    size="small"
                                    style={{ marginTop: 12, background: '#fffbe6', border: '1px solid #ffe58f' }}
                                >
                                    <Table
                                        dataSource={result.candidates.filter(c => c.is_recommended)}
                                        columns={recommendedColumns}
                                        rowKey="id"
                                        size="small"
                                        pagination={false}
                                        scroll={{ x: 900 }}
                                    />
                                    <Alert
                                        type="warning"
                                        showIcon
                                        message="推荐产品来自其他公司，如需购买请联系对应公司"
                                        style={{ marginTop: 8, fontSize: 12 }}
                                    />
                                </Card>
                            )}

                        </>
                    )}

                    {/* 无结果时显示提示 */}
                    {!result && (
                        <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
                            <ShoppingCartOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                            <p style={{ marginTop: 16 }}>输入客户需求或选择筛选条件后，点击「分析需求」开始匹配商品</p>
                        </div>
                    )}
                </Col>

                {/* 右侧：方案预览（始终显示） */}
                <Col span={8}>
                    <Card title="📋 方案预览" size="small"
                        extra={
                            <Space size="small">
                                <Button size="small" onClick={clearSelected} disabled={selectedItems.size === 0}>清空</Button>
                                <Button size="small" type="primary" icon={<SaveOutlined />} onClick={handleSave} disabled={selectedItems.size === 0}>保存</Button>
                                <Button size="small" icon={<DownloadOutlined />} onClick={handleExport} disabled={!savedPlanId}>导出</Button>
                            </Space>
                        }>
                        {renderPreviewCard()}
                    </Card>
                </Col>
            </Row>

            {/* 推荐产品购买提示弹窗 */}
            <Modal
                title={
                    <Space>
                        <WarningOutlined style={{ color: '#faad14' }} />
                        <span>以下推荐商品需要联系购买</span>
                    </Space>
                }
                open={purchaseModalOpen}
                onCancel={() => setPurchaseModalOpen(false)}
                footer={
                    <Button type="primary" onClick={() => setPurchaseModalOpen(false)}>
                        我知道了
                    </Button>
                }
                width={620}
            >
                <div style={{ marginBottom: 16 }}>
                    <Typography.Text type="secondary">
                        方案中包含来自其他公司的推荐商品，不能直接保存。请分别联系对应公司购买以下商品：
                    </Typography.Text>
                </div>
                {purchaseItems.map((item, idx) => (
                    <div key={item.id} style={{
                        padding: '8px 0', borderBottom: idx < purchaseItems.length - 1 ? '1px solid #f0f0f0' : 'none',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
                    }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <Tooltip title={item.product_name || item.quick_model}>
                                <div style={{ fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.product_name || item.quick_model}</div>
                            </Tooltip>
                            <div style={{ fontSize: 12, color: '#999' }}>
                                {item.brand} | 来源：<Tag color={item.source_role === 'super_admin' ? 'red' : 'blue'}>{item.source_company_name || item.source_role}</Tag>
                            </div>
                        </div>
                        <Text strong style={{ color: '#cf1322', fontSize: 16, whiteSpace: 'nowrap' }}>¥{item.price.toFixed(2)}</Text>
                    </div>
                ))}
                <div style={{ marginTop: 16, padding: 12, background: '#fff7e6', borderRadius: 6 }}>
                    <Typography.Text type="warning">
                        💡 提示：请将推荐商品从购物车中移除后再保存方案，或直接联系对应公司采购。
                    </Typography.Text>
                </div>
            </Modal>

            {/* 历史方案对话框 */}
            <Modal title="📂 历史方案" open={historyOpen} onCancel={() => setHistoryOpen(false)} footer={null} width={680} destroyOnHidden>
                {historyLoading ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
                ) : historyList.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无历史方案</div>
                ) : (
                    <Table
                        dataSource={historyList}
                        rowKey="id"
                        size="small"
                        pagination={false}
                        scroll={{ x: 640 }}
                        columns={[
                            { title: '方案名称', dataIndex: 'name', key: 'name', width: 130, ellipsis: true, render: (v) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
                            { title: '需求摘要', dataIndex: 'requirement', key: 'requirement', width: 180, ellipsis: true, render: (v) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
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
