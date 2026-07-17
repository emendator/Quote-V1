import { Table, Card, Tag, Empty, Typography, Space, Button, Alert, Tooltip } from 'antd';
import { DownOutlined, RightOutlined, OrderedListOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Product, ParsedQuery, SmartQueryResult, BatchModelQueryResult, BatchModelQueryItem } from '../types';
import { useState } from 'react';

const { Text, Title } = Typography;

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

// 批量查询专用精简列：聚焦代发价等关键报价信息
const batchColumns: ColumnsType<Product> = [
    { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 160, ellipsis: true, render: (v) => <Text strong>{v || '-'}</Text> },
    { title: '产品名称', dataIndex: 'product_name', key: 'product_name', width: 150, ellipsis: true, render: (v) => renderEllipsis(v) },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 80, render: (v) => v || '-' },
    { title: '型号', dataIndex: 'product_model', key: 'product_model', width: 130, ellipsis: true, render: (v) => renderEllipsis(v) },
    { title: '代发价', dataIndex: 'price', key: 'price', width: 90, render: (v) => (v ? <span className="price-highlight" style={{ fontWeight: 'bold', fontSize: 15 }}>¥{v.toFixed(2)}</span> : '-') },
    { title: '进货价', dataIndex: 'purchase_price', key: 'purchase_price', width: 85, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '零售价', dataIndex: 'retail_price', key: 'retail_price', width: 85, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 75, render: (v) => (v ? `${v}%` : '-') },
    { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 75, render: (v) => v || '-' },
    { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 140, render: (v) => v || '-' },
];

const columns: ColumnsType<Product> = [
    { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 140, ellipsis: true, render: (v) => renderEllipsis(v) },
    { title: '产品名称', dataIndex: 'product_name', key: 'product_name', width: 130, ellipsis: true, render: (v) => renderEllipsis(v) },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 65, render: (v) => v || '-' },
    { title: '一级品类', dataIndex: 'category_level1', key: 'category_level1', width: 75, render: (v) => v || '-' },
    { title: '二级品类', dataIndex: 'category_level2', key: 'category_level2', width: 75, render: (v) => v || '-' },
    { title: '三级品类', dataIndex: 'category_level3', key: 'category_level3', width: 75, render: (v) => v || '-' },
    { title: '备货商谈价', dataIndex: 'negotiation_price', key: 'negotiation_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '代发价', dataIndex: 'price', key: 'price', width: 75, render: (v) => (v ? <span className="price-highlight">¥{v.toFixed(2)}</span> : '-') },
    { title: '进货价', dataIndex: 'purchase_price', key: 'purchase_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '零售价', dataIndex: 'retail_price', key: 'retail_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 65, render: (v) => (v ? `${v}%` : '-') },
    { title: '新活动价', dataIndex: 'new_event_price', key: 'new_event_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '投标价', dataIndex: 'bid_price', key: 'bid_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '集采价', dataIndex: 'group_purchase_price', key: 'group_purchase_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '链接', dataIndex: 'shop_url', key: 'shop_url', width: 150, ellipsis: true, render: (v) => renderEllipsis(v) },
    { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 140, render: (v) => v || '-' },
    { title: '规格', dataIndex: 'specification', key: 'specification', width: 110, ellipsis: true, render: (v) => renderEllipsis(v) },
    { title: '箱规', dataIndex: 'box_spec', key: 'box_spec', width: 110, render: (v) => v || '-' },
    { title: '合作等级', dataIndex: 'cooperation_level', key: 'cooperation_level', width: 65, render: (v) => v || '-' },
    { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 65, render: (v) => v || '-' },
    { title: '毛重(kg)', dataIndex: 'gross_weight', key: 'gross_weight', width: 65, render: (v) => (v ? v.toFixed(2) : '-') },
    { title: '代发运费', dataIndex: 'shipping_fee', key: 'shipping_fee', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '销量', dataIndex: 'sales_volume', key: 'sales_volume', width: 55 },
    { title: '推荐理由', dataIndex: 'recommendation', key: 'recommendation', width: 130, ellipsis: true, render: (v) => renderEllipsis(v) },
    { title: '参数', dataIndex: 'parameters', key: 'parameters', width: 100, ellipsis: true, render: (v) => renderEllipsis(v) },
    { title: '3C', dataIndex: 'cert_3c', key: 'cert_3c', width: 65, render: (v) => v || '-' },
    { title: '备注', dataIndex: 'remark', key: 'remark', width: 140, ellipsis: true, render: (v) => renderEllipsis(v) },
];

interface Props {
    result: SmartQueryResult | BatchModelQueryResult | null;
    batchMode?: boolean;
}

export default function QueryResult({ result, batchMode }: Props) {
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

    // ========== 批量查询结果渲染 ==========
    if (batchMode && result && 'total_queries' in result) {
        const batchResult = result as BatchModelQueryResult;
        if (batchResult.total_queries === 0) {
            return (
                <Empty
                    description="未找到匹配的商品，请检查输入的快查型号"
                    style={{ marginTop: 60 }}
                />
            );
        }
        return (
            <div className="result-section">
                <Alert
                    type="success"
                    showIcon
                    icon={<OrderedListOutlined />}
                    message={
                        <Text>
                            批量查询完成：共查询 <Text strong>{batchResult.total_queries}</Text> 个快查型号，
                            找到 <Text strong>{batchResult.total_results}</Text> 条结果
                        </Text>
                    }
                    style={{ marginBottom: 16 }}
                />
                {batchResult.items.map((item: BatchModelQueryItem, idx: number) => {
                    const itemExpanded = isExpanded(idx);
                    const hasResults = item.count > 0;
                    return (
                        <Card
                            key={idx}
                            className="result-card"
                            size="small"
                            style={{ marginBottom: 12 }}
                            title={
                                <Space>
                                    <Button
                                        type="text"
                                        size="small"
                                        icon={itemExpanded ? <DownOutlined /> : <RightOutlined />}
                                        onClick={() => toggleCard(idx)}
                                    />
                                    <Tag color={hasResults ? 'blue' : 'default'}>快查型号</Tag>
                                    <Text strong style={{ fontSize: 14 }}>{item.query}</Text>
                                    <Tag color={hasResults ? 'success' : 'error'}>{item.count} 条结果</Tag>
                                </Space>
                            }
                            extra={
                                <Button size="small" type="link" onClick={() => toggleCard(idx)}>
                                    {itemExpanded ? '收起' : '展开'}
                                </Button>
                            }
                        >
                            {itemExpanded && (
                                hasResults ? (
                                    <Table
                                        columns={batchColumns}
                                        dataSource={item.results}
                                        rowKey="id"
                                        size="small"
                                        pagination={false}
                                        scroll={{ x: 1100 }}
                                    />
                                ) : (
                                    <Empty description={item.message} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                                )
                            )}
                        </Card>
                    );
                })}
            </div>
        );
    }

    // ========== 智能查询结果 ==========
    if (!result) {
        return (
            <Empty
                description="输入查询条件后点击「智能查询」获取报价"
                style={{ marginTop: 60 }}
            />
        );
    }

    const smartResult = result as SmartQueryResult;

    // AI 分析解读
    const aiBanner = smartResult.ai_interpretation ? (
        <Card
            size="small"
            style={{
                marginBottom: 16,
                background: '#fffbe6',
                border: '1px solid #ffe58f',
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
                    联合 {smartResult.parsed_queries.length} 个条件，共 {smartResult.result_count} 条结果
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
                            columns={columns}
                            dataSource={smartResult.results}
                            rowKey="id"
                            size="middle"
                            pagination={{
                                defaultPageSize: 20,
                                showSizeChanger: true,
                                pageSizeOptions: ['10', '20', '50', '100', '200', '500', '1000'],
                                showTotal: (t: number) => `共 ${t} 条`,
                            }}
                            scroll={{ x: 2400 }}
                        />
                    ) : (
                        <Empty description="未找到同时满足所有条件的商品" image={Empty.PRESENTED_IMAGE_SIMPLE} />
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
                    共识别到 {smartResult.parsed_queries.length} 个查询条件，共 {smartResult.result_count} 条结果
                </Text>
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
                                    columns={columns}
                                    dataSource={pq.results}
                                    rowKey="id"
                                    size="small"
                                    pagination={false}
                                    scroll={{ x: 2400 }}
                                />
                            ) : (
                                <Empty description={pq.message} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                            ))}
                        </Card>
                    );
                })}
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
                        <Tag>共 {smartResult.result_count} 条</Tag>
                    </Space>
                }
            >
                {smartResult.results.length > 0 ? (
                    <Table
                        columns={columns}
                        dataSource={smartResult.results}
                        rowKey="id"
                        size="middle"
                        pagination={{
                            defaultPageSize: 20,
                            showSizeChanger: true,
                            pageSizeOptions: ['10', '20', '50', '100', '200', '500', '1000'],
                            showTotal: (t) => `共 ${t} 条`,
                        }}
                        scroll={{ x: 2400 }}
                    />
                ) : (
                    <Empty description="未找到匹配的商品" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
            </Card>
        </div>
    );
}
