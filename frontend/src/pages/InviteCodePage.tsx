import React, { useState, useEffect, useCallback } from 'react';
import { Table, Button, Card, Tag, Modal, Form, Select, Input, DatePicker, message, Space, Typography, Tooltip, Alert } from 'antd';
import { PlusOutlined, CopyOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, DeleteOutlined, WarningOutlined, ReloadOutlined } from '@ant-design/icons';
import { useAuth } from '../store/AuthContext';
import { getInviteCodes, createInviteCode, deleteInviteCode, renewInviteCode } from '../services/api';
import type { InviteCode } from '../types';

const { Text } = Typography;

/** 复制文本到剪贴板：优先 Clipboard API，回退到 execCommand（兼容 http 等非安全上下文） */
async function copyText(text: string): Promise<boolean> {
    // 1) 优先使用 Clipboard API（仅在 https / localhost 等安全上下文可用）
    if (window.isSecureContext && navigator.clipboard?.writeText) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch {
            // 被拒绝或失败时继续走回退方案
        }
    }
    // 2) 回退：临时 textarea + execCommand('copy')，http 环境下同样可用
    try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'fixed';
        textarea.style.top = '-9999px';
        textarea.style.left = '-9999px';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        textarea.setSelectionRange(0, text.length);
        const ok = document.execCommand('copy');
        document.body.removeChild(textarea);
        return ok;
    } catch {
        return false;
    }
}

const InviteCodePage: React.FC = () => {
    const { isSuperAdmin } = useAuth();
    const [data, setData] = useState<InviteCode[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);
    const [createLoading, setCreateLoading] = useState(false);
    const [form] = Form.useForm();

    // 续期弹窗
    const [renewModalOpen, setRenewModalOpen] = useState(false);
    const [renewTarget, setRenewTarget] = useState<InviteCode | null>(null);
    const [renewLoading, setRenewLoading] = useState(false);
    const [renewForm] = Form.useForm();

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

    const handleCreate = async (values: { code_type: string; expires_at: any }) => {
        setCreateLoading(true);
        try {
            // 将 moment 对象格式化为 YYYY-MM-DD HH:mm
            const expiresAtStr = values.expires_at.format('YYYY-MM-DD HH:mm');
            const result = await createInviteCode({
                code_type: values.code_type,
                expires_at: expiresAtStr,
                company_name: '',
            });
            message.success('邀请码创建成功');
            setModalOpen(false);
            form.resetFields();
            // 复制到剪贴板（兼容 http 等非安全上下文）
            if (await copyText(result.code)) {
                message.success('邀请码已复制到剪贴板');
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
    const handleRenew = async (values: { expires_at: any }) => {
        if (!renewTarget) return;
        setRenewLoading(true);
        try {
            const expiresAtStr = values.expires_at.format('YYYY-MM-DD HH:mm');
            await renewInviteCode(renewTarget.id, expiresAtStr);
            message.success(`账号已续期至 ${expiresAtStr}`);
            setRenewModalOpen(false);
            renewForm.resetFields();
            fetchData();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '续期失败';
            message.error(msg);
        } finally {
            setRenewLoading(false);
        }
    };

    const openRenewModal = (record: InviteCode) => {
        setRenewTarget(record);
        setRenewModalOpen(true);
    };
    const copyToClipboard = async (code: string) => {
        if (await copyText(code)) {
            message.success('已复制到剪贴板');
        } else {
            message.error('复制失败，请手动复制');
        }
    };

    const getStatusTag = (record: InviteCode) => {
        const now = new Date();
        const expires = new Date(record.expires_at);
        if (record.is_used) {
            if (expires < now) {
                return <Tag icon={<CloseCircleOutlined />} color="error">已过期</Tag>;
            }
            return <Tag icon={<CheckCircleOutlined />} color="success">有效</Tag>;
        }
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
            width: 180,
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
            width: 60,
            render: (type: string) => type === 'admin' ? <Tag color="blue">管理员</Tag> : <Tag color="green">用户</Tag>,
        },
        {
            title: '备注',
            dataIndex: 'company_name',
            key: 'company_name',
            width: 200,
            render: (v: string) => v || <span style={{ color: '#ccc' }}>-</span>,
        },
        {
            title: '状态',
            key: 'status',
            width: 60,
            render: (_: any, record: InviteCode) => getStatusTag(record),
        },
        {
            title: '使用者',
            key: 'used_user',
            width: 120,
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
            width: 130,
            render: (v: string | null) => formatTime(v),
        },
        {
            title: '过期时间',
            dataIndex: 'expires_at',
            key: 'expires_at',
            width: 130,
            render: (v: string) => formatTime(v),
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 130,
            render: (v: string) => formatTime(v),
        },
        {
            title: '操作',
            key: 'action',
            width: 120,
            render: (_: unknown, record: InviteCode) => {
                const isExpired = record.is_used && record.expires_at && new Date(record.expires_at) < new Date();
                return (
                    <Space>
                        {isExpired && (
                            <Button
                                type="link"
                                size="small"
                                icon={<ReloadOutlined />}
                                onClick={() => openRenewModal(record)}
                            >
                                续期
                            </Button>
                        )}
                        <Button
                            type="link"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => handleDelete(record)}
                        />
                    </Space>
                );
            },
        },
    ];

    // 如果是用户角色，不显示此页面内容
    if (!isSuperAdmin) {
        // 管理员也能看到页面
    }

    return (
        <div className="dd-module dd-d1">
            <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <span className="eyebrow">Invite & Members</span>
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
                    initialValues={{ code_type: 'user' }}
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
                        name="expires_at"
                        label="过期时间"
                        rules={[{ required: true, message: '请选择过期时间' }]}
                        extra="账号在此时间之前有效，过期后禁止登录"
                    >
                        <DatePicker
                            showTime={{ format: 'HH:mm' }}
                            format="YYYY-MM-DD HH:mm"
                            style={{ width: '100%' }}
                        />
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

            {/* 续期弹窗 */}
            <Modal
                title={`续期 - ${renewTarget?.used_by_username || ''}`}
                open={renewModalOpen}
                onCancel={() => setRenewModalOpen(false)}
                footer={null}
                destroyOnClose
            >
                <Form
                    form={renewForm}
                    layout="vertical"
                    onFinish={handleRenew}
                >
                    <Form.Item
                        name="expires_at"
                        label="新的过期时间"
                        rules={[{ required: true, message: '请选择新的过期时间' }]}
                        extra="设置后该账号可继续使用至此时间"
                    >
                        <DatePicker
                            showTime={{ format: 'HH:mm' }}
                            format="YYYY-MM-DD HH:mm"
                            style={{ width: '100%' }}
                        />
                    </Form.Item>

                    <Form.Item>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setRenewModalOpen(false)}>取消</Button>
                            <Button type="primary" htmlType="submit" loading={renewLoading}>
                                确认续期
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default InviteCodePage;
