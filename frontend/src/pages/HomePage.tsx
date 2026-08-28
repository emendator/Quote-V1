import { useState, useEffect, useRef, useCallback } from 'react';
import { Select, Row, Col, Divider, message, Button, Space, Tooltip, Typography, Tag, Card, Table } from 'antd';
import { DownloadOutlined, ShopOutlined, ColumnHeightOutlined } from '@ant-design/icons';
import SmartQueryInput from '../components/SmartQueryInput';
import QueryResult from '../components/QueryResult';
import ColumnDisplayConfig from '../components/ColumnDisplayConfig';
import { smartQuery, aiSmartQuery, batchModelQuery, fetchCategories, fetchBrands, fetchCategoryLevel2, fetchCategoryLevel3, getRecommendedProducts, exportQueryResults } from '../services/api';
import type { SmartQueryResult, BatchModelQueryResult, Product, RecommendedProduct } from '../types';
import { usePageState } from '../store/PageStateContext';
import { useAuth } from '../store/AuthContext';

// 价格档位选项
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

export default function HomePage() {
    const { user, refreshUser } = useAuth();
    const [loading, setLoading] = useState(false);

    // ====== 持久化状态：切换页面后保留 ======
    const [pageState, setPageState] = usePageState('home', {
        queryText: '',
        useAI: false,
        batchMode: false,
        result: null as SmartQueryResult | BatchModelQueryResult | null,
        tokensUsed: 0,
        filterCat1: undefined as string | undefined,
        filterBrand: undefined as string | undefined,
        filterCat2: undefined as string | undefined,
        filterCat3: undefined as string | undefined,
        filterPrice: '',
        filterNego: '',
        filterPurchase: '',
        filterRetail: '',
        filterDiscount: '',
    });

    const { queryText, useAI, batchMode, result, tokensUsed } = pageState;
    const { filterCat1, filterBrand, filterCat2, filterCat3, filterPrice, filterNego, filterPurchase, filterRetail, filterDiscount } = pageState;

    const updateState = useCallback((patch: Partial<typeof pageState>) => {
        // 函数式更新：始终基于最新状态合并，避免异步回调用旧闭包覆盖新状态
        setPageState(prev => ({ ...prev, ...patch }));
    }, [setPageState]);

    // 推荐产品
    const [recommendedProducts, setRecommendedProducts] = useState<RecommendedProduct[]>([]);
    const [recommendedLoading, setRecommendedLoading] = useState(false);

    // 勾选导出的行
    const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);

    // 列显示配置弹窗
    const [columnConfigOpen, setColumnConfigOpen] = useState(false);
    const [columnConfigPageType, setColumnConfigPageType] = useState<'query_result' | 'batch_query'>('query_result');
    const [columnConfigVersion, setColumnConfigVersion] = useState(0);

    // 当查询结果变更时，清空勾选
    useEffect(() => {
        setSelectedRowKeys([]);
    }, [result]);

    // 筛选选项数据（非持久化）
    const [categories, setCategories] = useState<string[]>([]);
    const [brands, setBrands] = useState<string[]>([]);
    const [categoryLevel2, setCategoryLevel2] = useState<string[]>([]);
    const [categoryLevel3, setCategoryLevel3] = useState<string[]>([]);

    const isFirstRender = useRef(true);
    const hasRestoredState = useRef(false);

    useEffect(() => {
        fetchCategories().then(setCategories).catch(() => { });
        fetchBrands().then(setBrands).catch(() => { });
        fetchCategoryLevel2().then(setCategoryLevel2).catch(() => { });
        fetchCategoryLevel3().then(setCategoryLevel3).catch(() => { });
    }, []);

    // 首次挂载时，始终直接显示缓存数据，不自动触发任何查询
    useEffect(() => {
        hasRestoredState.current = true;
    }, []);

    // 筛选项变动时自动触发查询（排除首次，AI 模式时不触发）
    useEffect(() => {
        if (isFirstRender.current) {
            isFirstRender.current = false;
            return;
        }
        if (useAI) return;
        doQuery();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filterCat1, filterBrand, filterCat2, filterCat3, filterPrice, filterNego, filterPurchase, filterRetail, filterDiscount, useAI]);

    const buildQueryText = (text: string): string => {
        const parts: string[] = [];
        if (text.trim()) parts.push(text.trim());
        if (filterCat1) parts.push(`一级品类为${filterCat1}`);
        if (filterBrand) parts.push(`品牌为${filterBrand}`);
        if (filterCat2) parts.push(`二级品类为${filterCat2}`);
        if (filterCat3) parts.push(`三级品类为${filterCat3}`);

        const priceFieldMap: Record<string, string> = {
            price: '代发价',
            negotiation_price: '备货商谈价',
            purchase_price: '进货价',
            retail_price: '零售价',
        };
        const priceFilters = [
            { field: 'price', value: filterPrice },
            { field: 'negotiation_price', value: filterNego },
            { field: 'purchase_price', value: filterPurchase },
            { field: 'retail_price', value: filterRetail },
        ];
        for (const pf of priceFilters) {
            if (pf.value) {
                const fieldName = priceFieldMap[pf.field];
                parts.push(pf.value.replace(/^价格/, fieldName));
            }
        }

        if (filterDiscount) {
            parts.push(filterDiscount.replace(/^价格/, '折扣率'));
        }

        return parts.join('。');
    };

    const doQuery = async (textOverride?: string, aiOverride?: boolean, batchOverride?: boolean) => {
        const finalText = textOverride !== undefined ? textOverride : queryText;
        const finalAI = aiOverride !== undefined ? aiOverride : useAI;
        const finalBatch = batchOverride !== undefined ? batchOverride : batchMode;

        setLoading(true);
        try {
            if (finalBatch) {
                // 批量快查型号查询：按换行拆分
                const items = finalText.split(/[\r\n]+/)
                    .map(s => s.trim())
                    .filter(s => s.length > 0);
                if (items.length === 0) {
                    message.warning('请输入要查询的快查型号，每行一个');
                    setLoading(false);
                    return;
                }
                const data = await batchModelQuery({ queries: items, fuzzy: true });
                updateState({ result: data });
                if (data.total_results > 0) {
                    message.success(`批量查询完成，共找到 ${data.total_results} 条结果`);
                } else {
                    message.info('未找到匹配的商品，请检查快查型号是否正确');
                }
            } else {
                const queryText_ = buildQueryText(finalText);
                if (!queryText_.trim()) {
                    setLoading(false);
                    return;
                }
                const data = finalAI
                    ? await aiSmartQuery({ query_text: queryText_ })
                    : await smartQuery({ query_text: queryText_ });
                updateState({ result: data, tokensUsed: finalAI ? (data as SmartQueryResult).tokens_used ?? 0 : 0 });
                if (finalAI) refreshUser();
                if (data.result_count === 0 && data.query_intent !== 'mixed') {
                    message.info(data.message || '未找到匹配的商品');
                } else if (data.result_count > 0) {
                    message.success(`找到 ${data.result_count} 条结果`);
                }
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '查询失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }

        // 查询完成后获取推荐产品
        await fetchRecommendedProducts();
    };

    // 构建推荐产品查询条件
    const buildRecommendFilters = () => {
        const filters: Record<string, unknown> = {};
        if (filterCat1) filters.category_level1 = filterCat1;
        if (filterBrand) filters.brand = filterBrand;
        if (filterCat2) filters.category_level2 = filterCat2;
        if (filterCat3) filters.category_level3 = filterCat3;
        // 解析价格区间
        const priceRanges = [
            { key: 'price', value: filterPrice },
            { key: 'negotiation_price', value: filterNego },
            { key: 'purchase_price', value: filterPurchase },
            { key: 'retail_price', value: filterRetail },
        ];
        for (const pr of priceRanges) {
            if (pr.value) {
                const m = pr.value.match(/价格在(\d+)到(\d+)/);
                if (m) {
                    filters[`${pr.key}_min`] = parseFloat(m[1]);
                    filters[`${pr.key}_max`] = parseFloat(m[2]);
                }
            }
        }
        // 非批量模式：把查询文本作为关键词传递
        // 批量模式：不传关键词（因为批量查的是具体型号，高权限库不一定有相同型号）
        if (!batchMode && queryText.trim()) {
            filters.keyword = queryText.trim();
        }
        return filters;
    };

    // 获取推荐产品（传递当前查询条件）
    const fetchRecommendedProducts = async () => {
        try {
            const filters = buildRecommendFilters();
            const res = await getRecommendedProducts({ filters, page: 1, page_size: 20 });
            setRecommendedProducts(res.items || []);
        } catch {
            setRecommendedProducts([]);
        }
    };

    const handleQuery = (text: string, aiMode: boolean, useBatch?: boolean) => {
        const finalBatch = useBatch !== undefined ? useBatch : batchMode;
        const patch: Partial<typeof pageState> = { queryText: text, useAI: aiMode, batchMode: finalBatch };
        // 如果模式变了，清空结果避免类型不匹配白屏
        if (finalBatch !== batchMode || (result && 'total_queries' in result) !== finalBatch) {
            patch.result = null;
        }
        updateState(patch);
        doQuery(text, aiMode, useBatch);
    };

    const handleValueChange = (text: string, ai: boolean, batch?: boolean) => {
        const patch: Partial<typeof pageState> = { queryText: text, useAI: ai };
        if (batch !== undefined) {
            patch.batchMode = batch;
            // 切换批量模式时清空结果，避免类型不匹配导致白屏
            patch.result = null;
        }
        updateState(patch);
    };

    // 导出查询结果到 Excel（调用后端 API 以正确嵌入图片）
    const handleExport = useCallback(async () => {
        if (!result) {
            message.warning('当前没有可导出的商品，请先完成查询');
            return;
        }

        // 收集所有商品 ID
        let allProducts: Product[] = [];

        if ('total_queries' in result) {
            const batchResult = result as BatchModelQueryResult;
            batchResult.items.forEach(item => {
                if (item.results) allProducts.push(...item.results);
            });
        } else {
            const smartResult = result as SmartQueryResult;
            if (smartResult.results) allProducts = smartResult.results;
        }

        // 根据勾选情况决定导出哪些
        let products: Product[];
        if (selectedRowKeys.length > 0) {
            const selectedSet = new Set(selectedRowKeys);
            products = allProducts.filter(p => selectedSet.has(p.id));
            if (products.length === 0) {
                message.warning('勾选的商品中没有可导出的数据，请重新勾选');
                return;
            }
        } else {
            message.warning('请先勾选要导出的商品（点击表格左侧复选框）');
            return;
        }

        try {
            const ids = products.map(p => p.id);
            await exportQueryResults(ids);
            message.success(`已导出 ${products.length} 条数据（含图片）`);
        } catch {
            message.error('导出失败，请检查网络或稍后重试');
        }
    }, [result, selectedRowKeys]);

    // 价格筛选器通用组件
    const renderPriceSelect = (
        label: string,
        value: string,
        onChange: (v: string) => void,
    ) => (
        <Select
            placeholder={label}
            allowClear
            value={value || undefined}
            onChange={(v) => onChange(v || '')}
            style={{ width: 140 }}
            options={PRICE_RANGES.map((r) => ({ value: r.query, label: r.label }))}
        />
    );

    return (
        <div style={{ margin: '0 auto', padding: '0 8px' }}>
            <div className="dd-module dd-d1">
                <SmartQueryInput
                    value={queryText}
                    aiMode={useAI}
                    batchMode={batchMode}
                    hasApiKey={user?.has_api_key}
                    tokensUsed={tokensUsed}
                    onValueChange={handleValueChange}
                    onQuery={handleQuery}
                    loading={loading}
                />
            </div>

            <div className="dd-module dd-d2" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10, alignItems: 'center', gap: 8 }}>
                <Space size={8}>
                    <Tooltip title="配置查询结果表格的列显示和表头名称">
                        <Button
                            size="small"
                            icon={<ColumnHeightOutlined />}
                            onClick={() => {
                                setColumnConfigPageType(batchMode ? 'batch_query' : 'query_result');
                                setColumnConfigOpen(true);
                            }}
                        >
                            列配置
                        </Button>
                    </Tooltip>
                    {result && (
                        <>
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                                {selectedRowKeys.length > 0 ? `已选 ${selectedRowKeys.length} 项` : '从表格勾选商品'}
                            </Typography.Text>
                            <Button size="small" onClick={() => {
                                const ids: number[] = [];
                                if ('total_queries' in result) {
                                    const br = result as BatchModelQueryResult;
                                    br.items.forEach(item => { if (item.results) item.results.forEach(p => ids.push(p.id)); });
                                } else {
                                    const sr = result as SmartQueryResult;
                                    if (sr.results) sr.results.forEach(p => ids.push(p.id));
                                }
                                setSelectedRowKeys(ids);
                            }}>全选</Button>
                            <Button size="small" onClick={() => setSelectedRowKeys([])}>取消全选</Button>
                            <Tooltip title="导出当前勾选的商品">
                                <Button
                                    icon={<DownloadOutlined />}
                                    onClick={handleExport}
                                    size="small"
                                    disabled={selectedRowKeys.length === 0}
                                >
                                    导出选中 ({selectedRowKeys.length})
                                </Button>
                            </Tooltip>
                        </>
                    )}
                </Space>
            </div>

            {!batchMode && (
                <div className="filter-bar dd-module dd-d3">
                    {/* 第一行：品类 / 品牌 筛选 */}
                    <Row gutter={[8, 8]} style={{ marginBottom: 8 }}>
                        <Col span={6}>
                            <Select
                                placeholder="一级品类"
                                allowClear
                                showSearch
                                value={filterCat1}
                                onChange={(v) => updateState({ filterCat1: v })}
                                style={{ width: '100%' }}
                                options={categories.map((c) => ({ value: c, label: c }))}
                            />
                        </Col>
                        <Col span={6}>
                            <Select
                                placeholder="品牌"
                                allowClear
                                showSearch
                                value={filterBrand}
                                onChange={(v) => updateState({ filterBrand: v })}
                                style={{ width: '100%' }}
                                options={brands.map((b) => ({ value: b, label: b }))}
                            />
                        </Col>
                        <Col span={6}>
                            <Select
                                placeholder="二级品类"
                                allowClear
                                showSearch
                                value={filterCat2}
                                onChange={(v) => updateState({ filterCat2: v })}
                                style={{ width: '100%' }}
                                options={categoryLevel2.map((c) => ({ value: c, label: c }))}
                            />
                        </Col>
                        <Col span={6}>
                            <Select
                                placeholder="三级品类"
                                allowClear
                                showSearch
                                value={filterCat3}
                                onChange={(v) => updateState({ filterCat3: v })}
                                style={{ width: '100%' }}
                                options={categoryLevel3.map((c) => ({ value: c, label: c }))}
                            />
                        </Col>
                    </Row>

                    {/* 第二行：价格 / 折扣率 */}
                    <Row gutter={[8, 8]} style={{ marginBottom: 0 }}>
                        <Col span={4}>{renderPriceSelect('代发价', filterPrice, (v) => updateState({ filterPrice: v }))}</Col>
                        <Col span={5}>{renderPriceSelect('备货商谈价', filterNego, (v) => updateState({ filterNego: v }))}</Col>
                        <Col span={4}>{renderPriceSelect('进货价', filterPurchase, (v) => updateState({ filterPurchase: v }))}</Col>
                        <Col span={4}>{renderPriceSelect('零售价', filterRetail, (v) => updateState({ filterRetail: v }))}</Col>
                        <Col span={4}>
                            <Select
                                placeholder="折扣率"
                                allowClear
                                value={filterDiscount || undefined}
                                onChange={(v) => updateState({ filterDiscount: v || '' })}
                                style={{ width: '100%' }}
                                options={[
                                    { value: '', label: '全部' },
                                    { value: '折扣率在0到30', label: '≤ 30%' },
                                    { value: '折扣率在30到50', label: '30% - 50%' },
                                    { value: '折扣率在50到70', label: '50% - 70%' },
                                    { value: '折扣率在70到90', label: '70% - 90%' },
                                    { value: '折扣率在90到100', label: '≥ 90%' },
                                ]}
                            />
                        </Col>
                    </Row>
                </div>
            )}

            <QueryResult
                result={result}
                batchMode={batchMode}
                selectedRowKeys={selectedRowKeys}
                onSelectionChange={setSelectedRowKeys}
                pageType={batchMode ? 'batch_query' : 'query_result'}
                configVersion={columnConfigVersion}
            />

            <ColumnDisplayConfig
                open={columnConfigOpen}
                pageType={columnConfigPageType}
                onClose={() => setColumnConfigOpen(false)}
                onSaved={() => {
                    setColumnConfigVersion(v => v + 1);
                    message.success('列配置已更新');
                }}
            />

            {/* 推荐产品区域 */}
            {recommendedProducts.length > 0 && (
                <>
                    <Divider style={{ margin: '16px 0 8px' }} />
                    <Card
                        size="small"
                        className="dd-recommend-card dd-module dd-d4"
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
                                { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 130, ellipsis: { showTitle: false }, render: (v) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
                                { title: '商品名称', dataIndex: 'product_name', key: 'product_name', width: 150, ellipsis: { showTitle: false }, render: (v) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-' },
                                { title: '品牌', dataIndex: 'brand', key: 'brand', width: 70 },
                                {
                                    title: '图片', key: 'image', width: 65,
                                    render: (_: unknown, r: RecommendedProduct) => {
                                        if (!r.image) return <span style={{ color: 'var(--ink-300)', fontSize: 12 }}>无图</span>;
                                        const src = r.image.startsWith('data:') ? r.image : `data:image/png;base64,${r.image}`;
                                        return (
                                            <Tooltip title={<img src={src} style={{ maxWidth: 300, maxHeight: 300 }} alt="预览" />}>
                                                <img src={src} alt="" style={{ width: 50, height: 50, objectFit: 'cover', borderRadius: 4, border: '1px solid var(--ink-100)', cursor: 'pointer' }} />
                                            </Tooltip>
                                        );
                                    },
                                },
                                { title: '代发价', dataIndex: 'price', key: 'price', width: 80, render: (v: number) => <span className="price-highlight" style={{ fontSize: 13 }}>¥{Number(v).toFixed(2)}</span> },
                                {
                                    title: '来源公司', dataIndex: 'source_company_name', key: 'source_company_name', width: 120,
                                    render: (v: string, r: RecommendedProduct) => (
                                        <Tag color={r.source_role === 'super_admin' ? 'red' : 'blue'}>{v || r.source_role}</Tag>
                                    ),
                                },
                            ]}
                        />
                        <div style={{ textAlign: 'center', marginTop: 8, color: 'var(--ink-400)', fontSize: 12 }}>
                            如需购买推荐商品，请加入方案后，在「智能方案」页保存时按提示联系对应公司
                        </div>
                    </Card>
                </>
            )}
        </div>
    );
}
