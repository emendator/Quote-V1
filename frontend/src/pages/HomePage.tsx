import { useState, useEffect, useRef } from 'react';
import { Select, Row, Col, Divider, message } from 'antd';
import SmartQueryInput from '../components/SmartQueryInput';
import QueryResult from '../components/QueryResult';
import { smartQuery, aiSmartQuery, fetchCategories, fetchBrands, fetchCategoryLevel2 } from '../services/api';
import type { SmartQueryResult } from '../types';

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
    const [result, setResult] = useState<SmartQueryResult | null>(null);

    // 筛选选项数据
    const [categories, setCategories] = useState<string[]>([]);
    const [brands, setBrands] = useState<string[]>([]);
    const [categoryLevel2, setCategoryLevel2] = useState<string[]>([]);

    // 筛选状态
    const [filterCat1, setFilterCat1] = useState<string | undefined>(undefined);
    const [filterBrand, setFilterBrand] = useState<string | undefined>(undefined);
    const [filterCat2, setFilterCat2] = useState<string | undefined>(undefined);
    const [filterPrice, setFilterPrice] = useState<string>('');
    const [filterNego, setFilterNego] = useState<string>('');
    const [filterPurchase, setFilterPurchase] = useState<string>('');
    const [filterRetail, setFilterRetail] = useState<string>('');
    const [filterDiscount, setFilterDiscount] = useState<string>('');

    // 输入框文本（由 SmartQueryInput 同步上来）
    const [queryText, setQueryText] = useState('');
    const [useAI, setUseAI] = useState(false);

    const isFirstRender = useRef(true);

    useEffect(() => {
        fetchCategories().then(setCategories).catch(() => { });
        fetchBrands().then(setBrands).catch(() => { });
        fetchCategoryLevel2().then(setCategoryLevel2).catch(() => { });
    }, []);

    // 筛选项变动时自动触发查询
    useEffect(() => {
        if (isFirstRender.current) {
            isFirstRender.current = false;
            return;
        }
        doQuery();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filterCat1, filterBrand, filterCat2, filterPrice, filterNego, filterPurchase, filterRetail, filterDiscount]);

    const buildQueryText = (text: string): string => {
        const parts: string[] = [];
        if (text.trim()) parts.push(text.trim());
        if (filterCat1) parts.push(`一级品类为${filterCat1}`);
        if (filterBrand) parts.push(`品牌为${filterBrand}`);
        if (filterCat2) parts.push(`二级品类为${filterCat2}`);

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

    const doQuery = async (textOverride?: string, aiOverride?: boolean) => {
        const finalText = textOverride !== undefined ? textOverride : queryText;
        const finalAI = aiOverride !== undefined ? aiOverride : useAI;
        const queryText_ = buildQueryText(finalText);
        if (!queryText_.trim()) return;

        if (finalAI === undefined) return;

        setLoading(true);
        try {
            const data = finalAI
                ? await aiSmartQuery({ query_text: queryText_ })
                : await smartQuery({ query_text: queryText_ });
            setResult(data);
            if (data.result_count === 0 && data.query_intent !== 'mixed') {
                message.info(data.message || '未找到匹配的商品');
            } else if (data.result_count > 0) {
                message.success(`找到 ${data.result_count} 条结果`);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '查询失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleQuery = (text: string, aiMode: boolean) => {
        setQueryText(text);
        setUseAI(aiMode);
        doQuery(text, aiMode);
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
                onValueChange={(text, ai) => { setQueryText(text); setUseAI(ai); }}
                onQuery={handleQuery}
                loading={loading}
            />

            <Divider style={{ margin: '8px 0 12px' }} />

            {/* 第一行：一级品类 / 品牌 / 二级品类 */}
            <Row gutter={[8, 8]} style={{ marginBottom: 8 }}>
                <Col span={8}>
                    <Select
                        placeholder="一级品类"
                        allowClear
                        showSearch
                        value={filterCat1}
                        onChange={setFilterCat1}
                        style={{ width: '100%' }}
                        options={categories.map((c) => ({ value: c, label: c }))}
                    />
                </Col>
                <Col span={8}>
                    <Select
                        placeholder="品牌"
                        allowClear
                        showSearch
                        value={filterBrand}
                        onChange={setFilterBrand}
                        style={{ width: '100%' }}
                        options={brands.map((b) => ({ value: b, label: b }))}
                    />
                </Col>
                <Col span={8}>
                    <Select
                        placeholder="二级品类"
                        allowClear
                        showSearch
                        value={filterCat2}
                        onChange={setFilterCat2}
                        style={{ width: '100%' }}
                        options={categoryLevel2.map((c) => ({ value: c, label: c }))}
                    />
                </Col>
            </Row>

            {/* 第二行：价格 / 折扣率 */}
            <Row gutter={[8, 8]} style={{ marginBottom: 0 }}>
                <Col span={4}>{renderPriceSelect('代发价', filterPrice, setFilterPrice)}</Col>
                <Col span={5}>{renderPriceSelect('备货商谈价', filterNego, setFilterNego)}</Col>
                <Col span={4}>{renderPriceSelect('进货价', filterPurchase, setFilterPurchase)}</Col>
                <Col span={4}>{renderPriceSelect('零售价', filterRetail, setFilterRetail)}</Col>
                <Col span={4}>
                    <Select
                        placeholder="折扣率"
                        allowClear
                        value={filterDiscount || undefined}
                        onChange={(v) => setFilterDiscount(v || '')}
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

            <QueryResult result={result} />
        </div>
    );
}
