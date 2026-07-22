import React, { useState, useEffect, useCallback } from 'react';
import { Table, Button, Card, Tag, Modal, Form, Select, InputNumber, message, Space, Typography, Tooltip, Alert } from 'antd';
import { PlusOutlined, CopyOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, DeleteOutlined, WarningOutlined } from '@ant-design/icons';
import { useAuth } from '../store/AuthContext';
import { getInviteCodes, createInviteCode, deleteInviteCode } from '../services/api';
import type { InviteCode } from '../types';

const { Title, Text } = Typography;

const InviteCodePage: React.FC = () => {
    const { isSuperAdmin } = useAuth();
    const [data, setData] = useState<InviteCode[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);
    const [createLoading, setCreateLoading] = useState(false);
    const [form] = Form.useForm();

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const result = await getInviteCodes({ page, page_size: 20 });
            setData(result.items);
            setTotal(result.total);
        } catch {
            message.error('获取邀请码列表失败');
        } finally {
            setLoading(false);
        }
    }, [page]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleCreate = async (values: { code_type: string; expires_in_days: number }) => {
        setCreateLoading(true);
        try {
            const result = await createInviteCode(values);
            message.success('邀请码创建成功');
            setModalOpen(false);
            form.resetFields();
            // 复制到剪贴板
            try {
                await navigator.clipboard.writeText(result.code);
                message.success('邀请码已复制到剪贴板');
            } catch {
                // 部分浏览器可能不支持
            }
            fetchData();
        } catch (err: any) {
            message.error(err.message || '创建失败');
        } finally {
            setCreateLoading(false);
        }
    };

    const handleDelete = async (record: InviteCode) => {
        const usedInfo = record.is_used
            ? `\n\n⚠️ 该邀请码已被用户「${record.used_by_username || '未知'}」使用，删除将同时删除该账号及其所有数据（商品、方案等）。`
            : '';
        Modal.confirm({
            title: '确认删除此邀请码？',
            icon: <WarningOutlined style={{ color: '#faad14' }} />,
            content: (
                <div>
                    <p>邀请码：<Text code>{record.code}</Text></p>
                    <p>类型：{record.type === 'admin' ? '管理员' : '用户'}</p>
                    <p>状态：{record.is_used ? '已使用' : '未使用'}</p>
                    {record.is_used && (
                        <Alert
                            type="warning"
                            showIcon
                            message="此操作将级联删除关联账号及所有数据（商品、方案等），不可恢复！"
                            style={{ marginTop: 8 }}
                        />
                    )}
                </div>
            ),
            okText: '确认删除',
            okType: 'danger',
            cancelText: '取消',
            onOk: async () => {
                try {
                    await deleteInviteCode(record.id);
                    message.success('删除成功');
                    fetchData();
                } catch (err: unknown) {
                    const msg = err instanceof Error ? err.message : '删除失败';
                    message.error(msg);
                }
            },
        });
    };

    const copyToClipboard = async (code: string) => {
        try {
            await navigator.clipboard.writeText(code);
            message.success('已复制到剪贴板');
        } catch {
            message.error('复制失败，请手动复制');
        }
    };

    const getStatusTag = (record: InviteCode) => {
        if (record.is_used) {
            return <Tag icon={<CheckCircleOutlined />} color="default">已使用</Tag>;
        }
        const now = new Date();
        const expires = new Date(record.expires_at);
        if (expires < now) {
            return <Tag icon={<CloseCircleOutlined />} color="error">已过期</Tag>;
        }
        return <Tag icon={<ClockCircleOutlined />} color="processing">未使用</Tag>;
    };

    const formatTime = (v: string | null | undefined) => {
        if (!v) return '-';
        try {
            return new Date(v).toLocaleString('zh-CN');
        } catch {
            return '-';
        }
    };

    const columns = [
        {
            title: '邀请码',
            dataIndex: 'code',
            key: 'code',
            render: (code: string) => (
                <Space>
                    <span style={{ fontFamily: 'monospace', fontSize: 13 }}>{code}</span>
                    <Tooltip title="复制">
                        <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => copyToClipboard(code)} />
                    </Tooltip>
                </Space>
            ),
        },
        {
            title: '类型',
            dataIndex: 'type',
            key: 'type',
            width: 80,
            render: (type: string) => type === 'admin' ? <Tag color="blue">管理员</Tag> : <Tag color="green">用户</Tag>,
        },
        {
            title: '状态',
            key: 'status',
            width: 80,
            render: (_: any, record: InviteCode) => getStatusTag(record),
        },
        {
            title: '使用者',
            key: 'used_user',
            width: 150,
            render: (_: any, record: InviteCode) => {
                if (!record.is_used || !record.used_by_username) return <span style={{ color: '#999' }}>-</span>;
                return (
                    <div>
                        <div style={{ fontWeight: 500, fontSize: 13 }}>{record.used_by_username}</div>
                        {record.used_by_company && (
                            <div style={{ fontSize: 11, color: '#999' }}>{record.used_by_company}</div>
                        )}
                    </div>
                );
            },
        },
        {
            title: '最后登录',
            dataIndex: 'used_by_last_login',
            key: 'used_by_last_login',
            width: 160,
            render: (v: string | null) => formatTime(v),
        },
        {
            title: '使用时间',
            dataIndex: 'used_at',
            key: 'used_at',
            width: 160,
            render: (v: string | null) => formatTime(v),
        },
        {
            title: '过期时间',
            dataIndex: 'expires_at',
            key: 'expires_at',
            width: 160,
            render: (v: string) => formatTime(v),
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 160,
            render: (v: string) => formatTime(v),
        },
        {
            title: '操作',
            key: 'action',
            width: 70,
            render: (_: unknown, record: InviteCode) => (
                <Button
                    type="link"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDelete(record)}
                />
            ),
        },
    ];

    // 如果是用户角色，不显示此页面内容
    if (!isSuperAdmin) {
        // 管理员也能看到页面
    }

    return (
        <div style={{ padding: 24 }}>
            <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <Title level={4} style={{ margin: 0 }}>邀请码管理</Title>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                        创建邀请码
                    </Button>
                </div>

                <Table
                    dataSource={data}
                    columns={columns}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        current: page,
                        pageSize: 20,
                        total,
                        onChange: (p) => setPage(p),
                        showSizeChanger: false,
                    }}
                />
            </Card>

            <Modal
                title="创建邀请码"
                open={modalOpen}
                onCancel={() => setModalOpen(false)}
                footer={null}
                destroyOnClose
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleCreate}
                    initialValues={{ code_type: 'user', expires_in_days: 7 }}
                >
                    <Form.Item
                        name="code_type"
                        label="邀请码类型"
                        rules={[{ required: true, message: '请选择邀请码类型' }]}
                    >
                        <Select>
                            {isSuperAdmin && (
                                <Select.Option value="admin">一级邀请码（管理员）</Select.Option>
                            )}
                            <Select.Option value="user">二级邀请码（用户）</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="expires_in_days"
                        label="有效天数"
                        rules={[{ required: true, message: '请设置有效天数' }]}
                    >
                        <InputNumber min={1} max={30} style={{ width: '100%' }} />
                    </Form.Item>

                    <Form.Item>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setModalOpen(false)}>取消</Button>
                            <Button type="primary" htmlType="submit" loading={createLoading}>
                                创建
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default InviteCodePage;
