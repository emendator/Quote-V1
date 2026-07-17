import { Table, Button, Space, Popconfirm, Tag, Input, Image, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined, CameraOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Product } from '../types';

interface Props {
    dataSource: Product[];
    loading: boolean;
    total: number;
    page: number;
    pageSize: number;
    selectedRowKeys: number[];
    zoom?: number;
    sortBy?: string;
    sortOrder?: string;
    onPageChange: (page: number, pageSize: number) => void;
    onSortChange?: (sortBy: string, sortOrder: string) => void;
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
    zoom = 100,
    sortBy,
    sortOrder,
    onPageChange,
    onSortChange,
    onEdit,
    onDelete,
    onBatchDelete,
    onSelectChange,
}: Props) {
    // 长文本渲染：显示省略号 + 悬停 Tooltip 可查看完整内容
    const renderEllipsis = (text: string) => {
        if (!text) return '-';
        return (
            <Tooltip title={text} overlayStyle={{ maxWidth: 500 }}>
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>
                    {text}
                </span>
            </Tooltip>
        );
    };

    const columns: ColumnsType<Product> = [
        { title: '序号', key: 'index', width: 56, render: (_, __, index) => (page - 1) * pageSize + index + 1 },
        { title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 160, ellipsis: true, render: (v) => renderEllipsis(v) },
        { title: '型号', dataIndex: 'product_model', key: 'product_model', width: 130, ellipsis: true, render: (v) => renderEllipsis(v) },
        {
            title: '图片',
            dataIndex: 'image',
            key: 'image',
            width: 80,
            render: (v: string) => {
                if (!v || v === '') {
                    return <span style={{ color: '#ccc', fontSize: 12 }}>无图</span>;
                }
                // 判断是否为 base64 图片数据
                if (v.startsWith('data:image')) {
                    return (
                        <Image
                            src={v}
                            alt="产品图片"
                            width={50}
                            height={50}
                            style={{ objectFit: 'cover', borderRadius: 4, cursor: 'pointer' }}
                            preview={{
                                mask: <CameraOutlined />,
                            }}
                            fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iMjUiIHk9IjMwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjOTk5IiBmb250LXNpemU9IjEyIj7lm77niYc8L3RleHQ+PC9zdmc+"
                        />
                    );
                }
                // 可能是 URL 链接
                return (
                    <Image
                        src={v}
                        alt="产品图片"
                        width={50}
                        height={50}
                        style={{ objectFit: 'cover', borderRadius: 4, cursor: 'pointer' }}
                        preview={{
                            mask: <CameraOutlined />,
                        }}
                        fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iMjUiIHk9IjMwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjOTk5IiBmb250LXNpemU9IjEyIj7lm77niYc8L3RleHQ+PC9zdmc+"
                    />
                );
            },
        },
        { title: '产品名称', dataIndex: 'product_name', key: 'product_name', width: 160, ellipsis: true, render: (v) => renderEllipsis(v) },
        { title: '品牌', dataIndex: 'brand', key: 'brand', width: 70, render: (v) => v || '-' },
        { title: '一级品类', dataIndex: 'category_level1', key: 'category_level1', width: 80, render: (v) => v || '-' },
        { title: '二级品类', dataIndex: 'category_level2', key: 'category_level2', width: 80, render: (v) => v || '-' },
        { title: '三级品类', dataIndex: 'category_level3', key: 'category_level3', width: 80, render: (v) => v || '-' },
        { title: '备货商谈价', dataIndex: 'negotiation_price', key: 'negotiation_price', width: 80, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
        { title: '报价更新', dataIndex: 'price_update', key: 'price_update', width: 80, render: (v) => v || '-' },
        { title: '上次进货价', dataIndex: 'last_purchase_price', key: 'last_purchase_price', width: 80, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
        { title: '进货价', dataIndex: 'purchase_price', key: 'purchase_price', width: 80, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
        { title: '零售价', dataIndex: 'retail_price', key: 'retail_price', width: 80, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
        { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 70, sorter: true, render: (v) => (v ? `${v}%` : '-') },
        { title: '新活动价', dataIndex: 'new_event_price', key: 'new_event_price', width: 80, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
        { title: '链接', dataIndex: 'shop_url', key: 'shop_url', width: 180, ellipsis: true, render: (v) => renderEllipsis(v) },
        { title: '投标价', dataIndex: 'bid_price', key: 'bid_price', width: 80, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
        { title: '集采价/项目', dataIndex: 'group_purchase_price', key: 'group_purchase_price', width: 80, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
        { title: '代发价', dataIndex: 'price', key: 'price', width: 80, sorter: true, render: (v) => (v ? <span className="price-highlight">¥{v.toFixed(2)}</span> : '-') },
        { title: '毛重(kg)', dataIndex: 'gross_weight', key: 'gross_weight', width: 70, render: (v) => (v ? v.toFixed(2) : '-') },
        { title: '箱规', dataIndex: 'box_spec', key: 'box_spec', width: 120, render: (v) => v || '-' },
        { title: '合作等级', dataIndex: 'cooperation_level', key: 'cooperation_level', width: 70, render: (v) => v || '-' },
        { title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 70, render: (v) => v || '-' },
        { title: '规格', dataIndex: 'specification', key: 'specification', width: 130, ellipsis: true, render: (v) => renderEllipsis(v) },
        { title: '备注', dataIndex: 'remark', key: 'remark', width: 150, ellipsis: true, render: (v) => renderEllipsis(v) },
        { title: '代发运费', dataIndex: 'shipping_fee', key: 'shipping_fee', width: 80, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
        { title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 150, render: (v) => v || '-' },
        { title: '销量', dataIndex: 'sales_volume', key: 'sales_volume', width: 60 },
        { title: '推荐理由', dataIndex: 'recommendation', key: 'recommendation', width: 150, ellipsis: true, render: (v) => renderEllipsis(v) },
        { title: '参数', dataIndex: 'parameters', key: 'parameters', width: 100, ellipsis: true, render: (v) => renderEllipsis(v) },
        { title: '3C', dataIndex: 'cert_3c', key: 'cert_3c', width: 70, render: (v) => v || '-' },
        {
            title: '导入时间', dataIndex: 'created_at', key: 'created_at', width: 160, sorter: true,
            render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-',
            defaultSortOrder: sortBy === 'created_at' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : undefined,
        },
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
            <div style={{ overflow: 'auto', zoom: `${zoom}%` }}>
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
                        pageSizeOptions: ['10', '20', '50', '100', '200', '500', '1000'],
                    }}
                    onChange={(_pagination, _filters, sorter) => {
                        if (onSortChange && !Array.isArray(sorter)) {
                            const field = (sorter.field as string) || '';
                            const order = sorter.order === 'ascend' ? 'asc' : sorter.order === 'descend' ? 'desc' : '';
                            // 仅在排序列或排序方向确实变化时才触发，避免翻页时误重置 page=1
                            if (field !== (sortBy || '') || order !== (sortOrder || '')) {
                                onSortChange(field || 'created_at', order || 'desc');
                            }
                        }
                    }}
                    scroll={{ x: 2400 }}
                    size="middle"
                />
            </div>
        </div>
    );
}
