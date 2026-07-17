import { useState, useEffect, useRef, useCallback } from 'react';
import { Select, Row, Col, Divider, message } from 'antd';
import SmartQueryInput from '../components/SmartQueryInput';
import QueryResult from '../components/QueryResult';
import { smartQuery, aiSmartQuery, batchModelQuery, fetchCategories, fetchBrands, fetchCategoryLevel2, fetchCategoryLevel3 } from '../services/api';
import type { SmartQueryResult, BatchModelQueryResult } from '../types';
import { usePageState } from '../store/PageStateContext';

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
    const [loading, setLoading] = useState(false);

    // ====== 持久化状态：切换页面后保留 ======
    const [pageState, setPageState] = usePageState('home', {
        queryText: '',
        useAI: false,
        batchMode: false,
        result: null as SmartQueryResult | BatchModelQueryResult | null,
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

    const { queryText, useAI, batchMode, result } = pageState;
    const { filterCat1, filterBrand, filterCat2, filterCat3, filterPrice, filterNego, filterPurchase, filterRetail, filterDiscount } = pageState;

    const updateState = useCallback((patch: Partial<typeof pageState>) => {
        setPageState({ ...pageState, ...patch });
    }, [pageState, setPageState]);

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

    // 首次挂载时，如果恢复的页面有查询文本或筛选条件，自动触发查询
    useEffect(() => {
        if (!hasRestoredState.current) {
            hasRestoredState.current = true;
            if (queryText.trim() || filterCat1 || filterBrand || filterCat2 || filterCat3 || filterPrice || filterNego || filterPurchase || filterRetail || filterDiscount) {
                // 延迟执行，确保 DOM 已更新
                setTimeout(() => doQuery(), 100);
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // 筛选项变动时自动触发查询（排除首次）
    useEffect(() => {
        if (isFirstRender.current) {
            isFirstRender.current = false;
            return;
        }
        doQuery();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filterCat1, filterBrand, filterCat2, filterCat3, filterPrice, filterNego, filterPurchase, filterRetail, filterDiscount]);

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
                // 批量快查型号查询：按空格拆分
                const items = finalText.split(/\s+/)
                    .map(s => s.trim())
                    .filter(s => s.length > 0);
                if (items.length === 0) {
                    message.warning('请输入要查询的快查型号，用空格分隔');
                    setLoading(false);
                    return;
                }
                const data = await batchModelQuery({ queries: items, fuzzy: true });
                updateState({ result: data });
                if (data.total_results > 0) {
                    message.success(`批量查询完成，共找到 ${data.total_results} 条结果`);
                } else {
                    message.info('未找到匹配的商品');
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
                updateState({ result: data });
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
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
            <SmartQueryInput
                value={queryText}
                aiMode={useAI}
                batchMode={batchMode}
                onValueChange={handleValueChange}
                onQuery={handleQuery}
                loading={loading}
            />

            <Divider style={{ margin: '8px 0 12px' }} />

            {!batchMode && (
                <>
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
                </>
            )}

            <QueryResult result={result} batchMode={batchMode} />
        </div>
    );
}
