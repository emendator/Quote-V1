import { Table, Card, Tag, Empty, Typography, Space, Button } from 'antd';
import { DownOutlined, RightOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Product, ParsedQuery, SmartQueryResult } from '../types';
import { useState } from 'react';

const { Text, Title } = Typography;

const columns: ColumnsType<Product> = [
    { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 140, ellipsis: true, render: (v) => v || '-' },
    { title: '产品名称', dataIndex: 'product_name', key: 'product_name', width: 130, ellipsis: true, render: (v) => v || '-' },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 65, render: (v) => v || '-' },
    { title: '一级品类', dataIndex: 'category_level1', key: 'category_level1', width: 75, render: (v) => v || '-' },
    { title: '二级品类', dataIndex: 'category_level2', key: 'category_level2', width: 75, render: (v) => v || '-' },
    { title: '备货商谈价', dataIndex: 'negotiation_price', key: 'negotiation_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '代发价', dataIndex: 'price', key: 'price', width: 75, render: (v) => (v ? <span className="price-highlight">¥{v.toFixed(2)}</span> : '-') },
    { title: '进货价', dataIndex: 'purchase_price', key: 'purchase_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '零售价', dataIndex: 'retail_price', key: 'retail_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 65, render: (v) => (v ? `${v}%` : '-') },
    { title: '新活动价', dataIndex: 'new_event_price', key: 'new_event_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '投标价', dataIndex: 'bid_price', key: 'bid_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '集采价', dataIndex: 'group_purchase_price', key: 'group_purchase_price', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '链接', dataIndex: 'shop_url', key: 'shop_url', width: 150, ellipsis: true, render: (v) => v || '-' },
    { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 140, render: (v) => v || '-' },
    { title: '规格', dataIndex: 'specification', key: 'specification', width: 110, ellipsis: true, render: (v) => v || '-' },
    { title: '箱规', dataIndex: 'box_spec', key: 'box_spec', width: 110, render: (v) => v || '-' },
    { title: '合作等级', dataIndex: 'cooperation_level', key: 'cooperation_level', width: 65, render: (v) => v || '-' },
    { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 65, render: (v) => v || '-' },
    { title: '毛重(kg)', dataIndex: 'gross_weight', key: 'gross_weight', width: 65, render: (v) => (v ? v.toFixed(2) : '-') },
    { title: '代发运费', dataIndex: 'shipping_fee', key: 'shipping_fee', width: 75, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '销量', dataIndex: 'sales_volume', key: 'sales_volume', width: 55 },
    { title: '推荐理由', dataIndex: 'recommendation', key: 'recommendation', width: 130, ellipsis: true, render: (v) => v || '-' },
    { title: '参数', dataIndex: 'parameters', key: 'parameters', width: 100, ellipsis: true, render: (v) => v || '-' },
    { title: '3C', dataIndex: 'cert_3c', key: 'cert_3c', width: 65, render: (v) => v || '-' },
    { title: '备注', dataIndex: 'remark', key: 'remark', width: 140, ellipsis: true, render: (v) => v || '-' },
];

interface Props {
    result: SmartQueryResult | null;
}

export default function QueryResult({ result }: Props) {
    const [expanded, setExpanded] = useState<Set<number>>(new Set());

    const toggleCard = (idx: number) => {
        setExpanded((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });
    };
    if (!result) {
        return (
            <Empty
                description="输入查询条件后点击「智能查询」获取报价"
                style={{ marginTop: 60 }}
            />
        );
    }

    // AI 分析解读
    const aiBanner = result.ai_interpretation ? (
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
                <Text strong>{result.ai_interpretation}</Text>
            </Space>
        </Card>
    ) : null;

    // 联合查询（多条件 AND）
    if (result.query_intent === 'combined' && result.parsed_queries?.length > 0) {
        return (
            <div className="result-section">
                {aiBanner}
                <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
                    联合 {result.parsed_queries.length} 个条件，共 {result.result_count} 条结果
                </Text>
                <Card
                    className="result-card"
                    title={
                        <Space>
                            <Tag color="green">联合查询</Tag>
                            <Text>{result.message}</Text>
                        </Space>
                    }
                >
                    {result.results.length > 0 ? (
                        <Table
                            columns={columns}
                            dataSource={result.results}
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
    if (result.query_intent === 'mixed' && result.parsed_queries?.length > 0) {
        return (
            <div className="result-section">
                {aiBanner}
                <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
                    共识别到 {result.parsed_queries.length} 个查询条件，共 {result.result_count} 条结果
                </Text>
                {result.parsed_queries.map((pq: ParsedQuery, idx: number) => {
                    const isExpanded = expanded.has(idx);
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
                        <Tag color="green">{result.query_intent}</Tag>
                        <Text>{result.message}</Text>
                        <Tag>共 {result.result_count} 条</Tag>
                    </Space>
                }
            >
                {result.results.length > 0 ? (
                    <Table
                        columns={columns}
                        dataSource={result.results}
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
