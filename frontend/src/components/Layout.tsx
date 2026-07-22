import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography, Badge, Dropdown, Avatar, Space, Modal, Form, Input, Button, Tag, message } from 'antd';
import {
    SearchOutlined,
    DatabaseOutlined,
    CloudServerOutlined,
    FileTextOutlined,
    BulbOutlined,
    KeyOutlined,
    UserOutlined,
    LogoutOutlined,
    LockOutlined,
    SettingOutlined,
} from '@ant-design/icons';
import { useAuth } from '../store/AuthContext';
import { changePassword } from '../services/api';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

// 计算购物车中的商品数量
function getCartCount(): number {
    try {
        const raw = localStorage.getItem('solution_cart');
        if (!raw) return 0;
        return JSON.parse(raw).length;
    } catch { return 0; }
}

export default function AppLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, logout, isSuperAdmin, isAdmin } = useAuth();
    const [cartCount, setCartCount] = useState(getCartCount);
    const [pwdModalOpen, setPwdModalOpen] = useState(false);
    const [pwdForm] = Form.useForm();
    const [pwdLoading, setPwdLoading] = useState(false);

    useEffect(() => {
        const handler = () => setCartCount(getCartCount());
        window.addEventListener('solutionCartChange', handler);
        return () => window.removeEventListener('solutionCartChange', handler);
    }, []);

    // 检查管理员是否需完善公司信息
    useEffect(() => {
        if (user?.role === 'admin' && !user.company_name) {
            navigate('/company-info', { replace: true });
        }
    }, [user, navigate]);

    const handleLogout = () => {
        logout();
        navigate('/login', { replace: true });
    };

    const handleChangePassword = async (values: { old_password: string; new_password: string }) => {
        setPwdLoading(true);
        try {
            await changePassword(values);
            message.success('密码修改成功');
            setPwdModalOpen(false);
            pwdForm.resetFields();
        } catch (err: any) {
            message.error(err.message || '修改失败');
        } finally {
            setPwdLoading(false);
        }
    };

    const roleLabel = isSuperAdmin ? '最高级管理员' : isAdmin ? '管理员' : '用户';
    const roleColor = isSuperAdmin ? 'red' : isAdmin ? 'blue' : 'green';

    const userMenuItems = [
        {
            key: 'userinfo',
            label: (
                <div style={{ padding: '4px 0' }}>
                    <div><Text strong>{user?.username}</Text></div>
                    <div><Text type="secondary" style={{ fontSize: 12 }}>{user?.company_name || roleLabel}</Text></div>
                </div>
            ),
            disabled: true,
        },
        { type: 'divider' as const },
        {
            key: 'password',
            icon: <LockOutlined />,
            label: '修改密码',
            onClick: () => setPwdModalOpen(true),
        },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '退出登录',
            onClick: handleLogout,
        },
    ];

    const menuItems = [
        { key: '/', icon: <SearchOutlined />, label: '智能查询' },
        { key: '/data', icon: <DatabaseOutlined />, label: '数据管理' },
        { key: '/platforms', icon: <CloudServerOutlined />, label: '平台管理' },
        { key: '/listing-logs', icon: <FileTextOutlined />, label: '上架日志' },
        {
            key: '/solutions', icon: <BulbOutlined />,
            label: cartCount > 0 ? <span>智能方案 <Badge count={cartCount} size="small" style={{ marginLeft: 4 }} /></span> : '智能方案',
        },
        ...(isSuperAdmin || isAdmin ? [
            { key: '/invite-codes', icon: <KeyOutlined />, label: '邀请码管理' },
        ] : []),
    ];

    const pageTitles: Record<string, string> = {
        '/': '🔍 智能报价查询',
        '/data': '📋 商品数据管理',
        '/platforms': '☁️ 平台配置管理',
        '/listing-logs': '📄 上架日志',
        '/solutions': '💡 智能方案',
        '/invite-codes': '🔑 邀请码管理',
    };

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider
                width={200}
                style={{ background: '#fff' }}
                breakpoint="lg"
                collapsedWidth="60"
            >
                <div style={{ padding: '20px 16px', textAlign: 'center' }}>
                    <Title level={5} style={{ margin: 0, color: '#1677ff' }}>
                        💰 智能报价
                    </Title>
                </div>
                <Menu
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    items={menuItems}
                    onClick={({ key }) => navigate(key)}
                    style={{ borderRight: 0 }}
                />
            </Sider>
            <Layout>
                <Header style={{
                    background: '#fff',
                    padding: '0 24px',
                    borderBottom: '1px solid #f0f0f0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    height: 64,
                }}>
                    <Title level={4} style={{ margin: 0, lineHeight: '64px' }}>
                        {pageTitles[location.pathname] || '智能报价系统'}
                    </Title>
                    <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                        <Space style={{ cursor: 'pointer' }}>
                            <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1677ff' }} />
                            <span>{user?.username}</span>
                            <Tag color={roleColor} style={{ fontSize: 11, lineHeight: '18px', padding: '0 6px', margin: 0 }}>{roleLabel}</Tag>
                        </Space>
                    </Dropdown>
                </Header>
                <Content style={{ padding: 24, overflow: 'auto' }}>
                    <Outlet />
                </Content>
            </Layout>

            {/* 修改密码弹窗 */}
            <Modal
                title="修改密码"
                open={pwdModalOpen}
                onCancel={() => setPwdModalOpen(false)}
                footer={null}
                destroyOnClose
            >
                <Form
                    form={pwdForm}
                    layout="vertical"
                    onFinish={handleChangePassword}
                >
                    <Form.Item
                        name="old_password"
                        label="当前密码"
                        rules={[{ required: true, message: '请输入当前密码' }]}
                    >
                        <Input.Password placeholder="请输入当前密码" />
                    </Form.Item>
                    <Form.Item
                        name="new_password"
                        label="新密码"
                        rules={[
                            { required: true, message: '请输入新密码' },
                            { min: 6, message: '密码至少6个字符' },
                        ]}
                    >
                        <Input.Password placeholder="请输入新密码" />
                    </Form.Item>
                    <Form.Item
                        name="confirm_password"
                        label="确认新密码"
                        dependencies={['new_password']}
                        rules={[
                            { required: true, message: '请确认新密码' },
                            ({ getFieldValue }) => ({
                                validator(_, value) {
                                    if (!value || getFieldValue('new_password') === value) {
                                        return Promise.resolve();
                                    }
                                    return Promise.reject(new Error('两次输入的密码不一致'));
                                },
                            }),
                        ]}
                    >
                        <Input.Password placeholder="请确认新密码" />
                    </Form.Item>
                    <Form.Item>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                            <Button onClick={() => setPwdModalOpen(false)}>取消</Button>
                            <Button type="primary" htmlType="submit" loading={pwdLoading}>确认修改</Button>
                        </div>
                    </Form.Item>
                </Form>
            </Modal>
        </Layout>
    );
}
