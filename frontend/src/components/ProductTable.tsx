import { Table, Button, Space, Popconfirm, Tag, Input, Popover } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Product } from '../types';

interface Props {
    dataSource: Product[];
    loading: boolean;
    total: number;
    page: number;
    pageSize: number;
    selectedRowKeys: number[];
    onPageChange: (page: number, pageSize: number) => void;
    onEdit: (record: Product) => void;
    onDelete: (id: number) => void;
    onBatchDelete: () => void;
    onSelectChange: (keys: number[]) => void;
}

export default function ProductTable({
    dataSource,
    loading,
    total,
    page,
    pageSize,
    selectedRowKeys,
    onPageChange,
    onEdit,
    onDelete,
    onBatchDelete,
    onSelectChange,
}: Props) {
    const columns: ColumnsType<Product> = [
        { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
        {
            title: '图片',
            dataIndex: 'product_image',
            key: 'product_image',
            width: 70,
            render: (v: string) =>
                v ? (
                    <Popover content={<img src={v} alt="商品图片" style={{ maxWidth: 300, maxHeight: 300 }} />} trigger="hover">
                        <img src={v} alt="商品图片" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 4, cursor: 'pointer', border: '1px solid #f0f0f0' }} />
                    </Popover>
                ) : (
                    <span style={{ color: '#ccc' }}>无</span>
                ),
        },
        { title: '品牌', dataIndex: 'brand', key: 'brand', width: 100, render: (v) => v || '-' },
        { title: '类别', dataIndex: 'category', key: 'category', width: 90, render: (v) => v || '-' },
        { title: '商品型号', dataIndex: 'product_model', key: 'product_model', width: 130, ellipsis: true, render: (v) => v || '-' },
        { title: '规格', dataIndex: 'specification', key: 'specification', width: 160, ellipsis: true, render: (v) => v || '-' },
        {
            title: '京东划线价(元)',
            dataIndex: 'jd_price',
            key: 'jd_price',
            width: 110,
            render: (v) => (v ? `¥${v.toFixed(2)}` : '-'),
        },
        {
            title: '成本价(元)',
            dataIndex: 'cost_price',
            key: 'cost_price',
            width: 100,
            render: (v) => (v ? `¥${v.toFixed(2)}` : '-'),
        },
        {
            title: '代发价(元)',
            dataIndex: 'price',
            key: 'price',
            width: 110,
            sorter: true,
            render: (v) => <span className="price-highlight">¥{v?.toFixed(2) ?? '0.00'}</span>,
        },
        { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 140, render: (v) => v || '-' },
        { title: '供应商', dataIndex: 'supplier', key: 'supplier', width: 100, render: (v) => v || '-' },
        {
            title: '折扣率',
            dataIndex: 'discount_rate',
            key: 'discount_rate',
            width: 80,
            render: (v) => (v ? `${v}%` : '-'),
        },
        { title: '库存', dataIndex: 'stock', key: 'stock', width: 60 },
        {
            title: '操作',
            key: 'action',
            width: 120,
            fixed: 'right',
            render: (_, record) => (
                <Space size="small">
                    <Button type="link" size="small" icon={<EditOutlined />} onClick={() => onEdit(record)}>
                        编辑
                    </Button>
                    <Popconfirm title="确认删除此商品？" onConfirm={() => onDelete(record.id)} okText="确认" cancelText="取消">
                        <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div>
            {selectedRowKeys.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                    <Popconfirm
                        title={`确认删除选中的 ${selectedRowKeys.length} 个商品？`}
                        onConfirm={onBatchDelete}
                        okText="确认"
                        cancelText="取消"
                    >
                        <Button danger>批量删除 ({selectedRowKeys.length})</Button>
                    </Popconfirm>
                </div>
            )}
            <Table
                rowKey="id"
                columns={columns}
                dataSource={dataSource}
                loading={loading}
                rowSelection={{
                    selectedRowKeys,
                    onChange: (keys) => onSelectChange(keys as number[]),
                }}
                pagination={{
                    current: page,
                    pageSize,
                    total,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (t) => `共 ${t} 条`,
                    onChange: onPageChange,
                    pageSizeOptions: ['10', '20', '50', '100'],
                }}
                scroll={{ x: 1200 }}
                size="middle"
            />
        </div>
    );
}
