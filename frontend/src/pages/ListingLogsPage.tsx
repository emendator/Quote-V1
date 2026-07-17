import { useState, useEffect, useCallback } from 'react';
import {
    Table, Tag, Space, Button, Select, message, Modal, Descriptions, Tooltip,
} from 'antd';
import { EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { fetchListingLogs, fetchListingLogDetail, fetchPlatforms } from '../services/api';
import type { ListingLog, ListingLogDetail, PlatformConfig } from '../types';
import { usePageState } from '../store/PageStateContext';

const STATUS_MAP: Record<string, { color: string; text: string }> = {
    pending: { color: 'processing', text: '处理中' },
    success: { color: 'success', text: '成功' },
    failed: { color: 'error', text: '失败' },
};

export default function ListingLogsPage() {
    const [logs, setLogs] = useState<ListingLog[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [platforms, setPlatforms] = useState<PlatformConfig[]>([]);

    // 持久化状态
    const [pageState, setPageState] = usePageState('listingLogs', {
        page: 1,
        pageSize: 20,
        statusFilter: undefined as string | undefined,
        platformFilter: undefined as number | undefined,
    });
    const { page, pageSize, statusFilter, platformFilter } = pageState;
    const updateState = useCallback((patch: Partial<typeof pageState>) => {
        setPageState({ ...pageState, ...patch });
    }, [pageState, setPageState]);

    // 详情弹窗
    const [detailOpen, setDetailOpen] = useState(false);
    const [detail, setDetail] = useState<ListingLogDetail | null>(null);
    const [detailLoading, setDetailLoading] = useState(false);

    const loadLogs = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchListingLogs({
                page,
                page_size: pageSize,
                status: statusFilter,
                platform_id: platformFilter,
            });
            setLogs(data.items);
            setTotal(data.total);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '加载失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    }, [page, pageSize, statusFilter, platformFilter]);

    const loadPlatforms = async () => {
        try {
            const data = await fetchPlatforms();
            setPlatforms(data);
        } catch {
            // ignore
        }
    };

    useEffect(() => {
        loadLogs();
        loadPlatforms();
    }, [loadLogs]);

    const handleViewDetail = async (id: number) => {
        setDetailLoading(true);
        setDetailOpen(true);
        try {
            const data = await fetchListingLogDetail(id);
            setDetail(data);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '加载详情失败';
            message.error(msg);
            setDetailOpen(false);
        } finally {
            setDetailLoading(false);
        }
    };

    const columns: ColumnsType<ListingLog> = [
        {
            title: '序号',
            key: 'index',
            width: 56,
            render: (_, __, index) => (page - 1) * pageSize + index + 1,
        },
        {
            title: '商品信息',
            key: 'product',
            width: 220,
            render: (_, record) => (
                <div>
                    <div style={{ fontWeight: 500 }}>{record.product_name || '-'}</div>
                    <div style={{ color: '#999', fontSize: 12 }}>型号: {record.product_model || '-'}</div>
                </div>
            ),
        },
        {
            title: '目标平台',
            dataIndex: 'platform_name',
            key: 'platform_name',
            width: 140,
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            width: 90,
            render: (v: string) => {
                const info = STATUS_MAP[v] || { color: 'default', text: v };
                return <Tag color={info.color}>{info.text}</Tag>;
            },
        },
        {
            title: '平台商品ID',
            dataIndex: 'platform_product_id',
            key: 'platform_product_id',
            width: 160,
            render: (v: string) => v || '-',
        },
        {
            title: '错误信息',
            dataIndex: 'error_message',
            key: 'error_message',
            width: 200,
            ellipsis: true,
            render: (v: string) => {
                if (!v) return '-';
                return (
                    <Tooltip title={v}>
                        <span style={{ color: '#ff4d4f' }}>{v}</span>
                    </Tooltip>
                );
            },
        },
        {
            title: '上架时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 170,
            render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
        },
        {
            title: '操作',
            key: 'action',
            width: 80,
            render: (_, record) => (
                <Button
                    type="link"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => handleViewDetail(record.id)}
                >
                    详情
                </Button>
            ),
        },
    ];

    return (
        <div>
            <div className="toolbar">
                <Select
                    placeholder="筛选状态"
                    allowClear
                    style={{ width: 140 }}
                    value={statusFilter}
                    onChange={(val) => {
                        updateState({ statusFilter: val, page: 1 });
                    }}
                    options={[
                        { value: 'pending', label: '处理中' },
                        { value: 'success', label: '成功' },
                        { value: 'failed', label: '失败' },
                    ]}
                />
                <Select
                    placeholder="筛选平台"
                    allowClear
                    style={{ width: 180 }}
                    value={platformFilter}
                    onChange={(val) => {
                        updateState({ platformFilter: val, page: 1 });
                    }}
                    options={platforms.map((p) => ({ value: p.id, label: p.name }))}
                />
                <div style={{ flex: 1 }} />
                <Button icon={<ReloadOutlined />} onClick={loadLogs}>
                    刷新
                </Button>
            </div>

            <Table
                rowKey="id"
                columns={columns}
                dataSource={logs}
                loading={loading}
                pagination={{
                    current: page,
                    pageSize,
                    total,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (t) => `共 ${t} 条`,
                    onChange: (p, ps) => {
                        updateState({ page: p, pageSize: ps });
                    },
                    pageSizeOptions: ['10', '20', '50', '100'],
                }}
                scroll={{ x: 1000 }}
                size="middle"
            />

            <Modal
                title="上架日志详情"
                open={detailOpen}
                onCancel={() => setDetailOpen(false)}
                footer={null}
                width={800}
                loading={detailLoading}
            >
                {detail && (
                    <Descriptions column={2} bordered size="small">
                        <Descriptions.Item label="商品ID">{detail.product_id}</Descriptions.Item>
                        <Descriptions.Item label="商品型号">{detail.product_model || '-'}</Descriptions.Item>
                        <Descriptions.Item label="商品名称" span={2}>{detail.product_name || '-'}</Descriptions.Item>
                        <Descriptions.Item label="目标平台">{detail.platform_name}</Descriptions.Item>
                        <Descriptions.Item label="状态">
                            <Tag color={STATUS_MAP[detail.status]?.color || 'default'}>
                                {STATUS_MAP[detail.status]?.text || detail.status}
                            </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="平台商品ID">{detail.platform_product_id || '-'}</Descriptions.Item>
                        <Descriptions.Item label="错误信息">
                            {detail.error_message || '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="上架时间" span={2}>
                            {detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '-'}
                        </Descriptions.Item>
                        {detail.request_data && Object.keys(detail.request_data).length > 0 && (
                            <Descriptions.Item label="请求数据" span={2}>
                                <pre style={{
                                    background: '#f5f5f5',
                                    padding: 8,
                                    borderRadius: 4,
                                    fontSize: 12,
                                    maxHeight: 300,
                                    overflow: 'auto',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-all',
                                }}>
                                    {JSON.stringify(detail.request_data, null, 2)}
                                </pre>
                            </Descriptions.Item>
                        )}
                        {detail.response_data && Object.keys(detail.response_data).length > 0 && (
                            <Descriptions.Item label="响应数据" span={2}>
                                <pre style={{
                                    background: '#f5f5f5',
                                    padding: 8,
                                    borderRadius: 4,
                                    fontSize: 12,
                                    maxHeight: 300,
                                    overflow: 'auto',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-all',
                                }}>
                                    {JSON.stringify(detail.response_data, null, 2)}
                                </pre>
                            </Descriptions.Item>
                        )}
                    </Descriptions>
                )}
            </Modal>
        </div>
    );
}
