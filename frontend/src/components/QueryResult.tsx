import { Table, Card, Tag, Empty, Typography, Space, Button, Alert, Tooltip } from 'antd';
import { DownOutlined, RightOutlined, OrderedListOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Product, ParsedQuery, SmartQueryResult, BatchModelQueryResult, BatchModelQueryItem, ColumnConfigItem } from '../types';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { getColumnDisplayConfig } from '../services/api';
import { useCountUp } from '../hooks/useCountUp';

const { Text, Title } = Typography;

// 数字滚动文本
function CountUpText({ value }: { value: number }) {
    const v = useCountUp(value);
    return <>{Math.round(v)}</>;
}

// ========== 方案购物车（localStorage 持久化） ==========
const SOLUTION_CART_KEY = 'solution_cart';

// 编辑部式空状态
const renderEmpty = (title: string, desc?: string) => (
    <div className="dd-empty">
        <div className="dd-empty-mark">◇</div>
        <div className="dd-empty-title">{title}</div>
        {desc && <div className="dd-empty-desc">{desc}</div>}
    </div>
);

function getSolutionCart(): Map<number, number> {
    try {
        const raw = localStorage.getItem(SOLUTION_CART_KEY);
        if (!raw) return new Map();
        const arr = JSON.parse(raw);
        return new Map(arr);
    } catch { return new Map(); }
}

function saveSolutionCart(cart: Map<number, number>) {
    localStorage.setItem(SOLUTION_CART_KEY, JSON.stringify([...cart.entries()]));
}

function toggleSolutionCart(product: Product) {
    const cart = getSolutionCart();
    if (cart.has(product.id)) {
        cart.delete(product.id);
    } else {
        cart.set(product.id, 1);
    }
    saveSolutionCart(cart);
    // 强制重新渲染当前组件
    const evt = new CustomEvent('solutionCartChange', { detail: cart.size });
    window.dispatchEvent(evt);
}
// ================================================

// 长文本渲染：省略号 + 悬停 Tooltip 查看完整内容
const renderEllipsis = (text: string) => {
    if (!text) return '-';
    return (
        <Tooltip title={text} overlayStyle={{ maxWidth: 500 }}>
            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block', maxWidth: '100%' }}>
                {text}
            </span>
        </Tooltip>
    );
};

// 时间格式：去掉时分秒，仅保留日期
const fmtDate = (v: string | null | undefined) => {
    if (!v) return '-';
    const m = v.match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : v;
};

// 链接渲染：检测 URL 并显示为可点击的超链接
const renderUrl = (v: string | null | undefined) => {
    if (!v || v === '') return '-';
    const url = v.startsWith('http://') || v.startsWith('https://') ? v : `https://${v}`;
    return (
        <a href={url} target="_blank" rel="noopener noreferrer" style={{ wordBreak: 'break-all' }}>
            {v}
        </a>
    );
};

// 图片渲染：Base64 缩略图，点击放大
const renderImage = (v: string | null | undefined) => {
    if (!v || v === '') return '-';
    const src = v.startsWith('data:') ? v : `data:image/png;base64,${v}`;
    return (
        <Tooltip title={<img src={src} style={{ maxWidth: 300, maxHeight: 300 }} alt="预览" />}>
            <img src={src} style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 4, cursor: 'pointer' }} alt="缩略图" />
        </Tooltip>
    );
};

// 数值排序：null/undefined 排到最后，有效值按数字大小
const numSort = (a: number | null | undefined, b: number | null | undefined): number => {
    if (a == null && b == null) return 0;
    if (a == null) return 1;
    if (b == null) return -1;
    return Number(a) - Number(b);
};

// 日期排序：空值排到最后，有效值按时间先后
const dateSort = (a: string | null | undefined, b: string | null | undefined): number => {
    if (!a && !b) return 0;
    if (!a) return 1;
    if (!b) return -1;
    return new Date(a).getTime() - new Date(b).getTime();
};

// 批量查询专用精简列：聚焦代发价等关键报价信息
const batchColumns: ColumnsType<Product> = [
    { title: '图片', dataIndex: 'image', key: 'image', width: 55, render: (v) => renderImage(v) },
    { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 130, ellipsis: true, render: (v) => <Text strong>{v || '-'}</Text> },
    { title: '商品名称', dataIndex: 'product_name', key: 'product_name', width: 140, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 55, render: (v) => v || '-' },
    { title: '型号', dataIndex: 'product_model', key: 'product_model', width: 110, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    { title: '报价更新', dataIndex: 'price_update', key: 'price_update', width: 95, sorter: (a, b) => dateSort(a.price_update, b.price_update), render: (v) => fmtDate(v) },
    { title: '代发价', dataIndex: 'price', key: 'price', width: 85, sorter: (a, b) => numSort(a.price, b.price), render: (v) => (v !== null && v !== undefined && v !== '' ? <span className="price-highlight" style={{ fontWeight: 'bold', fontSize: 15 }}>¥{Number(v).toFixed(2)}</span> : '-') },
    { title: '进货价', dataIndex: 'purchase_price', key: 'purchase_price', width: 80, sorter: (a, b) => numSort(a.purchase_price, b.purchase_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '零售价', dataIndex: 'retail_price', key: 'retail_price', width: 80, sorter: (a, b) => numSort(a.retail_price, b.retail_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '新活动价', dataIndex: 'new_event_price', key: 'new_event_price', width: 75, sorter: (a, b) => numSort(a.new_event_price, b.new_event_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '集采价', dataIndex: 'group_purchase_price', key: 'group_purchase_price', width: 75, sorter: (a, b) => numSort(a.group_purchase_price, b.group_purchase_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 70, sorter: (a, b) => numSort(a.discount_rate, b.discount_rate), render: (v) => (v ? `${v}%` : '-') },
    { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 70, render: (v) => v || '-' },
    { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 130, render: (v) => v || '-' },
    {
        title: '方案', key: 'solution', width: 60, fixed: 'right',
        render: (_: unknown, record: Product) => {
            const isInCart = getSolutionCart().has(record.id);
            return <Button key={isInCart ? 'in' : 'out'} size="small" type={isInCart ? 'primary' : 'default'} className={isInCart ? 'dd-state-pop' : undefined} onClick={() => toggleSolutionCart(record)}>{isInCart ? '已加' : '加入'}</Button>;
        },
    },
];

const columns: ColumnsType<Product> = [
    { title: '图片', dataIndex: 'image', key: 'image', width: 55, render: (v) => renderImage(v) },
    { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 115, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    { title: '商品名称', dataIndex: 'product_name', key: 'product_name', width: 125, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    { title: '型号', dataIndex: 'product_model', key: 'product_model', width: 110, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 55, render: (v) => v || '-' },
    { title: '一级品类', dataIndex: 'category_level1', key: 'category_level1', width: 75, render: (v) => v || '-' },
    { title: '二级品类', dataIndex: 'category_level2', key: 'category_level2', width: 75, render: (v) => v || '-' },
    { title: '三级品类', dataIndex: 'category_level3', key: 'category_level3', width: 75, render: (v) => v || '-' },
    { title: '报价更新', dataIndex: 'price_update', key: 'price_update', width: 95, sorter: (a, b) => dateSort(a.price_update, b.price_update), render: (v) => fmtDate(v) },
    { title: '备货商谈价', dataIndex: 'negotiation_price', key: 'negotiation_price', width: 75, sorter: (a, b) => numSort(a.negotiation_price, b.negotiation_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '代发价', dataIndex: 'price', key: 'price', width: 75, sorter: (a, b) => numSort(a.price, b.price), render: (v) => (v !== null && v !== undefined && v !== '' ? <span className="price-highlight">¥{Number(v).toFixed(2)}</span> : '-') },
    { title: '进货价', dataIndex: 'purchase_price', key: 'purchase_price', width: 75, sorter: (a, b) => numSort(a.purchase_price, b.purchase_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '零售价', dataIndex: 'retail_price', key: 'retail_price', width: 75, sorter: (a, b) => numSort(a.retail_price, b.retail_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '新活动价', dataIndex: 'new_event_price', key: 'new_event_price', width: 75, sorter: (a, b) => numSort(a.new_event_price, b.new_event_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '集采价', dataIndex: 'group_purchase_price', key: 'group_purchase_price', width: 75, sorter: (a, b) => numSort(a.group_purchase_price, b.group_purchase_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '投标价', dataIndex: 'bid_price', key: 'bid_price', width: 75, sorter: (a, b) => numSort(a.bid_price, b.bid_price), render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 65, sorter: (a, b) => numSort(a.discount_rate, b.discount_rate), render: (v) => (v ? `${v}%` : '-') },
    { title: '链接', dataIndex: 'shop_url', key: 'shop_url', width: 150, render: (v) => renderUrl(v) },
    { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 140, render: (v) => v || '-' },
    { title: '规格', dataIndex: 'specification', key: 'specification', width: 110, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    { title: '箱规', dataIndex: 'box_spec', key: 'box_spec', width: 110, render: (v) => v || '-' },
    { title: '合作等级', dataIndex: 'cooperation_level', key: 'cooperation_level', width: 65, render: (v) => v || '-' },
    { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 65, render: (v) => v || '-' },
    { title: '毛重(kg)', dataIndex: 'gross_weight', key: 'gross_weight', width: 65, render: (v) => (v ? v.toFixed(2) : '-') },
    { title: '代发运费', dataIndex: 'shipping_fee', key: 'shipping_fee', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '销量', dataIndex: 'sales_volume', key: 'sales_volume', width: 55 },
    { title: '推荐理由', dataIndex: 'recommendation', key: 'recommendation', width: 130, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    { title: '参数', dataIndex: 'parameters', key: 'parameters', width: 100, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    { title: '3C', dataIndex: 'cert_3c', key: 'cert_3c', width: 65, render: (v) => v || '-' },
    { title: '备注', dataIndex: 'remark', key: 'remark', width: 140, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) },
    {
        title: '方案', key: 'solution', width: 70, fixed: 'right',
        render: (_: unknown, record: Product) => {
            const isInCart = getSolutionCart().has(record.id);
            return (
                <Button
                    key={isInCart ? 'in' : 'out'}
                    size="small"
                    type={isInCart ? 'primary' : 'default'}
                    className={isInCart ? 'dd-state-pop' : undefined}
                    onClick={() => toggleSolutionCart(record)}
                >
                    {isInCart ? '已加' : '加入'}
                </Button>
            );
        },
    },
];

interface Props {
    result: SmartQueryResult | BatchModelQueryResult | null;
    batchMode?: boolean;
    selectedRowKeys?: number[];
    onSelectionChange?: (keys: number[]) => void;
    pageType?: 'query_result' | 'batch_query';
    configVersion?: number;
}

export default function QueryResult({ result, batchMode, selectedRowKeys, onSelectionChange, pageType, configVersion }: Props) {
    // 列配置
    const [columnConfig, setColumnConfig] = useState<ColumnConfigItem[] | null>(null);

    useEffect(() => {
        if (!pageType) {
            setColumnConfig(null);
            return;
        }
        getColumnDisplayConfig(pageType)
            .then(data => setColumnConfig(data.columns || null))
            .catch(() => setColumnConfig(null));
    }, [pageType, configVersion]);

    // 方案购物车版本号——每次加入/移除时 +1，强制重渲染让按钮状态更新
    const [, setCartVersion] = useState(0);

    useEffect(() => {
        const handler = () => setCartVersion(v => v + 1);
        window.addEventListener('solutionCartChange', handler);
        return () => window.removeEventListener('solutionCartChange', handler);
    }, []);

    // 根据列配置动态生成列定义
    const effectiveColumns = useMemo(() => {
        if (!columnConfig || columnConfig.length === 0) return columns;
        const configMap = new Map(columnConfig.map(c => [c.key, c]));
        // 过滤可见列 + 应用标题，移除固定宽度使列自适应
        let filtered = columns
            .filter(col => {
                const colKey = String(col.key ?? '');
                const cfg = configMap.get(colKey);
                return cfg ? cfg.visible : true;
            })
            .map(col => {
                const colKey = String(col.key ?? '');
                const cfg = configMap.get(colKey);
                if (!cfg) return { ...col, width: undefined, fixed: undefined };
                return {
                    ...col,
                    title: cfg.label || col.title,
                    // 如果配置中指定了列宽则使用，否则不设宽度让列自适应
                    width: cfg.width || undefined,
                    fixed: undefined,
                };
            });
        // 排序
        const orderMap = new Map(columnConfig.map((c, i) => [c.key, i]));
        filtered.sort((a, b) => {
            const ai = orderMap.get(String(a.key ?? '')) ?? 999;
            const bi = orderMap.get(String(b.key ?? '')) ?? 999;
            return ai - bi;
        });
        return filtered;
    }, [columnConfig]);

    // 行选择配置（导出使用）
    const rowSelection = selectedRowKeys !== undefined && onSelectionChange ? {
        selectedRowKeys,
        onChange: (keys: React.Key[]) => onSelectionChange(keys as number[]),
        preserveSelectedRowKeys: true,
    } : undefined;

    // 默认全部展开，点击收起
    const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

    const toggleCard = (idx: number) => {
        setCollapsed((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });
    };
    const isExpanded = (idx: number) => !collapsed.has(idx);

    // ========== 批量查询结果渲染（统一滑动条控制） ==========
    if (batchMode && result && 'total_queries' in result) {
        const batchResult = result as BatchModelQueryResult;
        if (batchResult.total_queries === 0) {
            return renderEmpty(
                '暂无匹配结果',
                '请检查快查型号是否输入正确，或换一个关键词试试'
            );
        }

        // 将所有子查询结果合并到一个扁平数组中，每行附加 source_query 字段标识来源
        const flatDataSource: (Product & { source_query: string })[] = [];
        batchResult.items.forEach((item: BatchModelQueryItem) => {
            if (item.results) {
                item.results.forEach(p => {
                    flatDataSource.push({ ...p, source_query: item.query });
                });
            }
        });

        // 统一列定义：在原来 batchColumns 最前面插入「查询来源」列
        // 类型用 any 绕过 batchColumns(ColumnsType<Product>) 与泛型不兼容的 TS 限制
        const baseBatchCols: any[] = batchColumns.map(col => {
            if (col.key === 'solution') return col;
            return { ...col, fixed: undefined };
        });

        // 根据列配置过滤/排序
        const unifiedColumns: any[] = (() => {
            let cols: any[] = [
                {
                    title: '查询来源',
                    dataIndex: 'source_query',
                    key: 'source_query',
                    width: 130,
                    fixed: 'left',
                    render: (v: string) => <Tag color="blue">{v}</Tag>,
                },
                ...baseBatchCols,
            ];
            if (columnConfig && columnConfig.length > 0) {
                const configMap = new Map(columnConfig.map(c => [c.key, c]));
                cols = cols.filter((col: any) => {
                    if (col.key === 'source_query') return true;
                    const cfg = configMap.get(col.key);
                    return cfg ? cfg.visible : true;
                }).map((col: any) => {
                    if (col.key === 'source_query') return col;
                    const cfg = configMap.get(col.key);
                    if (!cfg) return { ...col, width: undefined, fixed: undefined };
                    return {
                        ...col,
                        title: cfg.label || col.title,
                        // 如果配置中指定了列宽则使用，否则不设宽度让列自适应
                        width: cfg.width || undefined,
                        fixed: undefined,
                    };
                });
                // 按配置顺序排序
                const orderMap = new Map(columnConfig.map((c, i) => [c.key, i]));
                cols.sort((a: any, b: any) => {
                    if (a.key === 'source_query') return -1;
                    if (b.key === 'source_query') return 1;
                    const ai = orderMap.get(a.key) ?? 999;
                    const bi = orderMap.get(b.key) ?? 999;
                    return ai - bi;
                });
            }
            return cols;
        })();

        return (
            <div className="result-section">
                <Alert
                    type="success"
                    showIcon
                    icon={<OrderedListOutlined />}
                    message={
                        <Text>
                            批量查询完成：共查询 <Text strong><CountUpText value={batchResult.total_queries} /></Text> 个快查型号，
                            找到 <Text strong><CountUpText value={batchResult.total_results} /></Text> 条结果
                        </Text>
                    }
                    style={{ marginBottom: 16 }}
                />
                <Card
                    size="small"
                    title={
                        <Space>
                            <OrderedListOutlined />
                            <span>批量查询结果 — 统一展示（共 {flatDataSource.length} 行）</span>
                        </Space>
                    }
                >
                    <Table
                        columns={unifiedColumns}
                        dataSource={flatDataSource}
                        rowKey="id"
                        size="small"
                        pagination={{
                            defaultPageSize: 50,
                            showSizeChanger: true,
                            pageSizeOptions: ['20', '50', '100', '200', '500'],
                            showTotal: (t: number) => `共 ${t} 条`,
                        }}
                        scroll={{ x: columnConfig ? 800 : 1600, y: 600 }}
                        rowSelection={rowSelection}
                    />
                </Card>
            </div>
        );
    }

    // ========== 智能查询结果 ==========
    if (!result) {
        return renderEmpty(
            '开始一次智能查询',
            '输入查询条件后点击「智能查询」获取报价，例如：飞利浦充电宝 100 块以下'
        );
    }

    const smartResult = result as SmartQueryResult;

    // AI 分析解读
    const aiBanner = smartResult.ai_interpretation ? (
        <Card
            size="small"
            style={{
                marginBottom: 16,
                background: 'var(--accent-amber-bg)',
                border: '1px solid var(--accent-amber-border)',
                borderRadius: 8,
            }}
        >
            <Space>
                <Tag color="gold">AI 分析</Tag>
                <Text strong>{smartResult.ai_interpretation}</Text>
            </Space>
        </Card>
    ) : null;

    // 联合查询（多条件 AND）
    if (smartResult.query_intent === 'combined' && smartResult.parsed_queries?.length > 0) {
        return (
            <div className="result-section">
                {aiBanner}
                <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
                    联合 {smartResult.parsed_queries.length} 个条件，共 <CountUpText value={smartResult.result_count} /> 条结果
                </Text>
                <Card
                    className="result-card"
                    title={
                        <Space>
                            <Tag color="green">联合查询</Tag>
                            <Text>{smartResult.message}</Text>
                        </Space>
                    }
                >
                    {smartResult.results.length > 0 ? (
                        <Table
                            columns={effectiveColumns}
                            dataSource={smartResult.results}
                            rowKey="id"
                            size="middle"
                            pagination={{
                                defaultPageSize: 20,
                                showSizeChanger: true,
                                pageSizeOptions: ['10', '20', '50', '100', '200', '500', '1000'],
                                showTotal: (t: number) => `共 ${t} 条`,
                            }}
                            scroll={{ x: columnConfig ? 800 : 2400 }}
                            rowSelection={rowSelection}
                        />
                    ) : (
                        <Empty description="未找到同时满足所有条件的商品，试试减少筛选条件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                </Card>
            </div>
        );
    }

    // 混合查询（多个独立查询，如微信群消息）
    if (smartResult.query_intent === 'mixed' && smartResult.parsed_queries?.length > 0) {
        return (
            <div className="result-section">
                {aiBanner}
                <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
                    共识别到 <CountUpText value={smartResult.parsed_queries.length} /> 个查询条件，共 <CountUpText value={smartResult.result_count} /> 条结果
                </Text>
                <div className="dd-stagger">
                {smartResult.parsed_queries.map((pq: ParsedQuery, idx: number) => {
                    const isExpanded = !collapsed.has(idx);
                    return (
                        <Card
                            key={idx}
                            className="result-card"
                            size="small"
                            title={
                                <Space>
                                    <Button
                                        type="text"
                                        size="small"
                                        icon={isExpanded ? <DownOutlined /> : <RightOutlined />}
                                        onClick={() => toggleCard(idx)}
                                    />
                                    <Tag color="blue">{pq.type === 'exact_barcode' ? '69码' : pq.type === 'exact_sku' ? 'SKU' : pq.type}</Tag>
                                    <Text>{pq.value}</Text>
                                    <Tag>{pq.count} 条结果</Tag>
                                </Space>
                            }
                            extra={
                                <Button size="small" type="link" onClick={() => toggleCard(idx)}>
                                    {isExpanded ? '收起' : '展开'}
                                </Button>
                            }
                        >
                            {isExpanded && (pq.results.length > 0 ? (
                                <Table
                                    columns={effectiveColumns}
                                    dataSource={pq.results}
                                    rowKey="id"
                                    size="small"
                                    pagination={false}
                                    scroll={{ x: columnConfig ? 800 : 2400 }}
                                    rowSelection={rowSelection}
                                />
                            ) : (
                                <Empty description={pq.message} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                            ))}
                        </Card>
                    );
                })}
                </div>
            </div>
        );
    }

    // 单一查询结果
    return (
        <div className="result-section">
            {aiBanner}
            <Card
                className="result-card"
                title={
                    <Space>
                        <Tag color="green">{smartResult.query_intent}</Tag>
                        <Text>{smartResult.message}</Text>
                        <Tag>共 <CountUpText value={smartResult.result_count} /> 条</Tag>
                    </Space>
                }
            >
                {smartResult.results.length > 0 ? (
                    <Table
                        columns={effectiveColumns}
                        dataSource={smartResult.results}
                        rowKey="id"
                        size="middle"
                        pagination={{
                            defaultPageSize: 20,
                            showSizeChanger: true,
                            pageSizeOptions: ['10', '20', '50', '100', '200', '500', '1000'],
                            showTotal: (t) => `共 ${t} 条`,
                        }}
                        scroll={{ x: columnConfig ? 800 : 2400 }}
                        rowSelection={rowSelection}
                    />
                ) : (
                    <Empty description="未找到匹配的商品，试试简化关键词或调整筛选条件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
            </Card>
        </div>
    );
}
