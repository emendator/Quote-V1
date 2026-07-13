import { Table, Card, Tag, Empty, Typography, Space, Popover } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Product, ParsedQuery, SmartQueryResult } from '../types';

const { Text, Title } = Typography;

const columns: ColumnsType<Product> = [
    {
        title: '图片',
        dataIndex: 'product_image',
        key: 'product_image',
        width: 60,
        render: (v: string) =>
            v ? (
                <Popover content={<img src={v} alt="商品图片" style={{ maxWidth: 200, maxHeight: 200 }} />} trigger="hover">
                    <img src={v} alt="商品图片" style={{ width: 36, height: 36, objectFit: 'cover', borderRadius: 4, cursor: 'pointer', border: '1px solid #f0f0f0' }} />
                </Popover>
            ) : null,
    },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 100, render: (v) => v || '-' },
    { title: '商品型号', dataIndex: 'product_model', key: 'product_model', width: 130, ellipsis: true, render: (v) => v || '-' },
    { title: '规格', dataIndex: 'specification', key: 'specification', width: 180, ellipsis: true, render: (v) => v || '-' },
    {
        title: '代发价(元)',
        dataIndex: 'price',
        key: 'price',
        width: 120,
        sorter: (a, b) => a.price - b.price,
        render: (v) => <span className="price-highlight">¥{v?.toFixed(2) ?? '0.00'}</span>,
    },
    { title: '京东划线价(元)', dataIndex: 'jd_price', key: 'jd_price', width: 110, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '成本价(元)', dataIndex: 'cost_price', key: 'cost_price', width: 100, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
    { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 140, render: (v) => v || '-' },
    { title: '类别', dataIndex: 'category', key: 'category', width: 90, render: (v) => v || '-' },
    { title: '供应商', dataIndex: 'supplier', key: 'supplier', width: 100, render: (v) => v || '-' },
    { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 80, render: (v) => (v ? `${v}%` : '-') },
    { title: '库存', dataIndex: 'stock', key: 'stock', width: 60 },
];

interface Props {
    result: SmartQueryResult | null;
}

export default function QueryResult({ result }: Props) {
    if (!result) {
        return (
            <Empty
                description="输入查询条件后点击「智能查询」获取报价"
                style={{ marginTop: 60 }}
            />
        );
    }

    // 混合查询（多个独立查询，如微信群消息）
    if (result.query_intent === 'mixed' && result.parsed_queries?.length > 0) {
        return (
            <div className="result-section">
                <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
                    共识别到 {result.parsed_queries.length} 个查询条件，共 {result.result_count} 条结果
                </Text>
                {result.parsed_queries.map((pq: ParsedQuery, idx: number) => (
                    <Card
                        key={idx}
                        className="result-card"
                        size="small"
                        title={
                            <Space>
                                <Tag color="blue">{pq.type === 'exact_barcode' ? '69码' : pq.type === 'exact_sku' ? 'SKU' : pq.type}</Tag>
                                <Text>{pq.value}</Text>
                                <Tag>{pq.count} 条结果</Tag>
                            </Space>
                        }
                    >
                        {pq.results.length > 0 ? (
                            <Table
                                columns={columns}
                                dataSource={pq.results}
                                rowKey="id"
                                size="small"
                                pagination={false}
                                scroll={{ x: 1000 }}
                            />
                        ) : (
                            <Empty description={pq.message} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        )}
                    </Card>
                ))}
            </div>
        );
    }

    // 单一查询结果
    return (
        <div className="result-section">
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
                        pagination={result.results.length > 20 ? { pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` } : false}
                        scroll={{ x: 1000 }}
                    />
                ) : (
                    <Empty description="未找到匹配的商品" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
            </Card>
        </div>
    );
}
