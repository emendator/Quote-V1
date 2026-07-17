import { useState, useEffect } from 'react';
import {
    Modal, Checkbox, Button, message, Table, Tag, Space, Typography, Alert,
} from 'antd';
import { ShoppingCartOutlined } from '@ant-design/icons';
import { fetchPlatforms, submitListing } from '../services/api';
import type { PlatformConfig, ListingResultItem } from '../types';

const { Text } = Typography;

interface Props {
    open: boolean;
    selectedProductIds: number[];
    onClose: () => void;
    onSuccess?: () => void;
}

export default function ListingDialog({ open, selectedProductIds, onClose, onSuccess }: Props) {
    const [platforms, setPlatforms] = useState<PlatformConfig[]>([]);
    const [selectedPlatformIds, setSelectedPlatformIds] = useState<number[]>([]);
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [results, setResults] = useState<ListingResultItem[]>([]);
    const [submitted, setSubmitted] = useState(false);

    useEffect(() => {
        if (open) {
            loadPlatforms();
            setSelectedPlatformIds([]);
            setResults([]);
            setSubmitted(false);
        }
    }, [open]);

    const loadPlatforms = async () => {
        setLoading(true);
        try {
            const data = await fetchPlatforms();
            // 只显示已启用的平台
            setPlatforms(data.filter((p) => p.is_active));
            if (data.filter((p) => p.is_active).length > 0) {
                setSelectedPlatformIds([data.filter((p) => p.is_active)[0].id]);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '加载平台列表失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async () => {
        if (selectedPlatformIds.length === 0) {
            message.warning('请选择至少一个目标平台');
            return;
        }
        setSubmitting(true);
        try {
            const data = await submitListing({
                product_ids: selectedProductIds,
                platform_ids: selectedPlatformIds,
            });
            setResults(data.results);
            setSubmitted(true);
            if (data.failed === 0) {
                message.success(`全部上架成功！共 ${data.success} 条`);
                onSuccess?.();
            } else if (data.success > 0) {
                message.warning(`部分上架成功：成功 ${data.success} 个，失败 ${data.failed} 个`);
                onSuccess?.();
            } else {
                message.error(`全部上架失败：${data.failed} 个`);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '上架失败';
            message.error(msg);
        } finally {
            setSubmitting(false);
        }
    };

    const successCount = results.filter((r) => r.status === 'success').length;
    const failedCount = results.filter((r) => r.status === 'failed').length;

    return (
        <Modal
            title={
                <span>
                    <ShoppingCartOutlined style={{ marginRight: 8 }} />
                    一键上架 ({selectedProductIds.length} 个商品)
                </span>
            }
            open={open}
            onCancel={onClose}
            footer={
                !submitted ? (
                    <Space>
                        <Button onClick={onClose}>取消</Button>
                        <Button
                            type="primary"
                            loading={submitting}
                            onClick={handleSubmit}
                            disabled={selectedPlatformIds.length === 0}
                        >
                            提交上架
                        </Button>
                    </Space>
                ) : (
                    <Button type="primary" onClick={onClose}>
                        完成
                    </Button>
                )
            }
            width={640}
            destroyOnClose
        >
            {!submitted ? (
                <div>
                    <div style={{ marginBottom: 12 }}>
                        <Text strong>选择目标平台：</Text>
                        <Text type="secondary" style={{ marginLeft: 8 }}>
                            (可多选，仅显示已启用的平台)
                        </Text>
                    </div>
                    <Checkbox.Group
                        value={selectedPlatformIds}
                        onChange={(values) => setSelectedPlatformIds(values as number[])}
                        style={{ width: '100%' }}
                    >
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                            {platforms.map((p) => (
                                <Checkbox key={p.id} value={p.id} style={{ lineHeight: '32px' }}>
                                    <Tag color={
                                        p.platform_type === 'taobao' ? 'orange' :
                                            p.platform_type === 'jd' ? 'red' : 'blue'
                                    }>
                                        {p.name}
                                    </Tag>
                                </Checkbox>
                            ))}
                        </div>
                    </Checkbox.Group>
                    {platforms.length === 0 && !loading && (
                        <Alert
                            type="warning"
                            message={'暂无已启用的平台配置，请先在「平台管理」中添加并启用平台'}
                            style={{ marginTop: 12 }}
                        />
                    )}

                    <div style={{ marginTop: 16 }}>
                        <Text strong>待上架商品：</Text>
                        <Text type="secondary" style={{ marginLeft: 8 }}>
                            {selectedProductIds.length} 个
                        </Text>
                        <div style={{ marginTop: 8 }}>
                            <Text code style={{ fontSize: 12 }}>
                                ID: {selectedProductIds.join(', ')}
                            </Text>
                        </div>
                    </div>
                </div>
            ) : (
                <div>
                    <Alert
                        type={failedCount === 0 ? 'success' : successCount > 0 ? 'warning' : 'error'}
                        message={
                            failedCount === 0
                                ? `全部上架成功！共 ${successCount} 条`
                                : `上架完成：成功 ${successCount} 个，失败 ${failedCount} 个`
                        }
                        showIcon
                        style={{ marginBottom: 16 }}
                    />
                    <Table
                        rowKey={(r) => `${r.product_id}-${r.platform_id}`}
                        dataSource={results}
                        pagination={false}
                        size="small"
                        columns={[
                            {
                                title: '商品ID',
                                dataIndex: 'product_id',
                                width: 80,
                            },
                            {
                                title: '平台ID',
                                dataIndex: 'platform_id',
                                width: 80,
                            },
                            {
                                title: '状态',
                                dataIndex: 'status',
                                width: 80,
                                render: (v: string) => (
                                    <Tag color={v === 'success' ? 'success' : 'error'}>
                                        {v === 'success' ? '成功' : '失败'}
                                    </Tag>
                                ),
                            },
                            {
                                title: '平台商品ID',
                                dataIndex: 'platform_product_id',
                                width: 160,
                                render: (v: string) => v || '-',
                            },
                            {
                                title: '错误信息',
                                dataIndex: 'error_message',
                                render: (v: string) => v || '-',
                            },
                        ]}
                    />
                </div>
            )}
        </Modal>
    );
}
