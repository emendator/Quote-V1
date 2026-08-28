import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography, Badge, Dropdown, Avatar, Space, Modal, Form, Input, Button, Tag, message, Alert, Card, Descriptions } from 'antd';
import {
    SearchOutlined,
    DatabaseOutlined,
    BulbOutlined,
    KeyOutlined,
    UserOutlined,
    LogoutOutlined,
    LockOutlined,
    SettingOutlined,
    ApiOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    ThunderboltOutlined,
    SafetyOutlined,
    DownOutlined,
    SunOutlined,
    MoonOutlined,
} from '@ant-design/icons';
import { useAuth } from '../store/AuthContext';
import { useTheme } from '../store/ThemeContext';
import { changePassword, updateApiKey, changeCompanyPassword } from '../services/api';

const { Header, Sider, Content } = Layout;
const { Text, Paragraph } = Typography;

// 计算购物车中的商品数量
function getCartCount(): number {
    try {
        const raw = localStorage.getItem('solution_cart');
        if (!raw) return 0;
        return JSON.parse(raw).length;
    } catch { return 0; }
}

// 页面标题 + 眉标（编辑部式：英文眉标 + 衬线标题）
const PAGE_META: Record<string, { eyebrow: string; title: string }> = {
    '/': { eyebrow: 'Smart Query', title: '智能查询' },
    '/data': { eyebrow: 'Product Library', title: '商品管理' },
    '/solutions': { eyebrow: 'Solution Studio', title: '智能方案' },
    '/invite-codes': { eyebrow: 'Access Control', title: '用户管理' },
};

export default function AppLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, logout, isSuperAdmin, isAdmin, isGuest, refreshUser } = useAuth();
    const { mode, toggleTheme } = useTheme();
    const [cartCount, setCartCount] = useState(getCartCount);
    const [pwdModalOpen, setPwdModalOpen] = useState(false);

    // 侧边栏折叠状态（持久化到 localStorage）
    const [siderCollapsed, setSiderCollapsed] = useState(() => {
        return localStorage.getItem('sider_collapsed') === 'true';
    });
    const [pwdForm] = Form.useForm();
    const [pwdLoading, setPwdLoading] = useState(false);

    // API Key 弹窗
    const [apiKeyModalOpen, setApiKeyModalOpen] = useState(false);
    const [apiKeyForm] = Form.useForm();
    const [apiKeyLoading, setApiKeyLoading] = useState(false);

    // 公司数据库密码弹窗
    const [cpwdModalOpen, setCpwdModalOpen] = useState(false);
    const [cpwdForm] = Form.useForm();
    const [cpwdLoading, setCpwdLoading] = useState(false);

    // 账号过期提醒
    const expiresAt = user?.expires_at ? new Date(user.expires_at) : null;
    const daysLeft = expiresAt ? Math.ceil((expiresAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24)) : null;
    // 游客不显示账号过期告警（游客会话本身是临时的，随时可重新进入）
    const showExpiryWarning = !isGuest && daysLeft !== null && daysLeft >= 0 && daysLeft <= 7;
    const expiresAtString = expiresAt ? expiresAt.toLocaleString() : '';

    useEffect(() => {
        const handler = () => setCartCount(getCartCount());
        window.addEventListener('solutionCartChange', handler);
        return () => window.removeEventListener('solutionCartChange', handler);
    }, []);

    // 检查是否需完善公司信息（绑定公司名称 + 公司数据库密码）；游客拥有独立临时公司，无需绑定
    useEffect(() => {
        if (user && !user.company_id && !isGuest) {
            navigate('/company-info', { replace: true });
        }
    }, [user, navigate, isGuest]);

    const handleLogout = async () => {
        // 游客退出登录会自动清除服务端全部临时数据（不保留任何使用痕迹），先确认再执行
        if (isGuest) {
            Modal.confirm({
                title: '退出游客模式',
                content: '退出后，当前游客会话的数据将全部清除且无法恢复。确定退出吗？',
                okText: '确认退出',
                cancelText: '取消',
                onOk: async () => {
                    await logout();
                    navigate('/login', { replace: true });
                },
            });
            return;
        }
        await logout();
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

    const handleSaveApiKey = async (values: { api_key: string }) => {
        setApiKeyLoading(true);
        try {
            await updateApiKey(values.api_key);
            message.success('API Key 已保存（加密存储）');
            setApiKeyModalOpen(false);
            apiKeyForm.resetFields();
            refreshUser();
        } catch (err: any) {
            message.error(err.message || '保存失败');
        } finally {
            setApiKeyLoading(false);
        }
    };

    const handleChangeCompanyPassword = async (values: { old_password: string; new_password: string; company_name?: string }) => {
        setCpwdLoading(true);
        try {
            await changeCompanyPassword({
                old_password: values.old_password,
                new_password: values.new_password,
                company_name: values.company_name || '',
            });
            message.success('公司数据库密码修改成功');
            setCpwdModalOpen(false);
            cpwdForm.resetFields();
        } catch (err: any) {
            message.error(err.message || '修改失败');
        } finally {
            setCpwdLoading(false);
        }
    };

    const roleLabel = isSuperAdmin ? '最高级管理员' : isAdmin ? '管理员' : isGuest ? '游客' : '用户';
    const roleColor = isSuperAdmin ? 'red' : isAdmin ? 'blue' : isGuest ? 'purple' : 'green';

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
        ...(isGuest ? [] : [
            {
                key: 'company',
                icon: <SettingOutlined />,
                label: '公司信息',
                onClick: () => navigate('/company-info?edit=1'),
            },
        ]),
        {
            key: 'apikey',
            icon: <ApiOutlined />,
            label: (
                <span>
                    API Key 配置
                    {user?.has_api_key
                        ? <Tag color="success" style={{ marginLeft: 6, fontSize: 10 }}>已配置</Tag>
                        : <Tag color="warning" style={{ marginLeft: 6, fontSize: 10 }}>未配置</Tag>
                    }
                </span>
            ),
            onClick: () => setApiKeyModalOpen(true),
        },
        ...(isGuest ? [] : [
            {
                key: 'password',
                icon: <LockOutlined />,
                label: '修改密码',
                onClick: () => setPwdModalOpen(true),
            },
        ]),
        ...(isSuperAdmin || isAdmin ? [
            {
                key: 'company-pwd',
                icon: <SafetyOutlined />,
                label: '修改公司数据库密码',
                onClick: () => setCpwdModalOpen(true),
            },
        ] : []),
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '退出登录',
            onClick: handleLogout,
        },
    ];

    const menuItems = [
        { key: '/', icon: <SearchOutlined />, label: '智能查询' },
        { key: '/data', icon: <DatabaseOutlined />, label: '商品管理' },
        {
            key: '/solutions', icon: <BulbOutlined />,
            label: cartCount > 0
                ? <span>智能方案 <Badge key={cartCount} count={cartCount} size="small" className="dd-badge-pop" style={{ marginLeft: 4, backgroundColor: 'var(--accent-amber)' }} /></span>
                : '智能方案',
        },
        ...(isSuperAdmin || isAdmin ? [
            { key: '/invite-codes', icon: <KeyOutlined />, label: '用户管理' },
        ] : []),
    ];

    const pageMeta = PAGE_META[location.pathname] || { eyebrow: 'Workspace', title: '智能报价系统' };

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider
                width={216}
                className={siderCollapsed ? 'dd-sider dd-sider-collapsed' : 'dd-sider'}
                style={{ background: 'var(--surface)', borderRight: '1px solid var(--ink-100)' }}
                collapsible
                collapsed={siderCollapsed}
                onCollapse={(value) => {
                    setSiderCollapsed(value);
                    localStorage.setItem('sider_collapsed', String(value));
                }}
                collapsedWidth={64}
                trigger={null}
            >
                <div className="dd-brand">
                    <div className="dd-brand-mark dd-float">¥</div>
                    {!siderCollapsed && (
                        <>
                            <div className="dd-brand-name">智能报价</div>
                            <div className="dd-brand-tagline">Quotation Studio</div>
                        </>
                    )}
                </div>
                <Menu
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    items={menuItems}
                    onClick={({ key }) => navigate(key)}
                    inlineCollapsed={siderCollapsed}
                />
                {/* 折叠/展开按钮固定在底部 */}
                <div
                    onClick={() => {
                        const next = !siderCollapsed;
                        setSiderCollapsed(next);
                        localStorage.setItem('sider_collapsed', String(next));
                    }}
                    style={{
                        position: 'absolute',
                        bottom: 0,
                        width: '100%',
                        height: 48,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        borderTop: '1px solid var(--ink-100)',
                        color: 'var(--ink-400)',
                        fontSize: 15,
                        transition: 'all 0.2s',
                        background: 'var(--surface)',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--ink-900)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--ink-400)'; }}
                >
                    {siderCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                </div>
            </Sider>
            <Layout>
                <Header className="dd-header" style={{
                    padding: '0 28px',
                    borderBottom: '1px solid var(--ink-100)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    height: 64,
                }}>
                    <div key={location.pathname} className="dd-page-title">
                        <span className="eyebrow dd-title-stagger">{pageMeta.eyebrow}</span>
                        <h2 className="dd-title-stagger" style={{ animationDelay: '0.07s' }}>{pageMeta.title}</h2>
                    </div>
                    <Space size={12}>
                        <Button
                            type="text"
                            className="dd-theme-toggle"
                            aria-label={mode === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
                            title={mode === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
                            icon={mode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
                            onClick={toggleTheme}
                        />
                        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                            <Space className="dd-user-chip">
                                <Avatar icon={<UserOutlined />} size={30} style={{ backgroundColor: 'var(--ink-800)' }} />
                                <span style={{ fontWeight: 550, fontSize: 13.5, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {user?.username}
                                </span>
                                <Tag color={roleColor} style={{ fontSize: 11, lineHeight: '18px', padding: '0 7px', margin: 0, borderRadius: 999 }}>{roleLabel}</Tag>
                                <DownOutlined style={{ fontSize: 10, color: 'var(--ink-400)' }} />
                            </Space>
                        </Dropdown>
                    </Space>
                </Header>
                <Content key={location.pathname} className="dd-content" style={{ overflow: 'auto' }}>
                    {isGuest && (
                        <Alert
                            type="info"
                            showIcon
                            style={{ marginBottom: 16 }}
                            message={
                                <span>
                                    🧪 <Text strong>游客模式</Text>：所有数据均为临时体验数据，退出后自动清除；使用 AI 功能需先在个人菜单配置 API Key
                                </span>
                            }
                        />
                    )}
                    {showExpiryWarning && (
                        <Alert
                            type="warning"
                            showIcon
                            style={{ marginBottom: 16 }}
                            message={`您的账号将于 ${daysLeft === 0 ? '今天' : `${daysLeft} 天后`}过期（${expiresAtString}），过期后将被禁止登录，请联系管理员续期。`}
                        />
                    )}
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

            {/* API Key 配置弹窗 */}
            <Modal
                title={<span><ApiOutlined /> DeepSeek API Key 配置</span>}
                open={apiKeyModalOpen}
                onCancel={() => setApiKeyModalOpen(false)}
                footer={null}
                destroyOnClose
                width={560}
            >
                <Alert
                    message="需要 DeepSeek API Key"
                    description="AI 智能查询与智能方案需要 DeepSeek API Key。请前往 platform.deepseek.com 获取，Key 以 sk- 开头。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 20 }}
                />

                <Card size="small" title="当前状态" style={{ marginBottom: 20 }}>
                    <Descriptions column={1} size="small">
                        <Descriptions.Item label="API Key 状态">
                            {user?.has_api_key ? (
                                <Tag icon={<CheckCircleOutlined />} color="success">已配置</Tag>
                            ) : (
                                <Tag icon={<CloseCircleOutlined />} color="error">未配置</Tag>
                            )}
                        </Descriptions.Item>
                        <Descriptions.Item label="累计 Token 消耗">
                            <Text><ThunderboltOutlined /> <span className="mono">{(user?.total_tokens_used ?? 0).toLocaleString()}</span> Tokens</Text>
                        </Descriptions.Item>
                    </Descriptions>
                </Card>

                <Card size="small" title={user?.has_api_key ? "更新 API Key" : "设置 API Key"}>
                    <Form
                        form={apiKeyForm}
                        layout="vertical"
                        onFinish={handleSaveApiKey}
                    >
                        <Form.Item
                            name="api_key"
                            rules={[{ required: true, message: '请输入 API Key' }]}
                        >
                            <Input.Password
                                prefix={<KeyOutlined />}
                                placeholder={user?.has_api_key ? "输入新的 API Key 以替换现有 Key" : "粘贴您的 DeepSeek API Key（sk-...）"}
                                autoComplete="off"
                                size="large"
                            />
                        </Form.Item>
                        <Form.Item style={{ marginBottom: 0 }}>
                            <Button
                                type="primary"
                                htmlType="submit"
                                loading={apiKeyLoading}
                                block
                                size="large"
                            >
                                {user?.has_api_key ? '更新 API Key' : '保存 API Key'}
                            </Button>
                        </Form.Item>
                    </Form>
                    <Paragraph type="secondary" style={{ marginTop: 12, fontSize: 12, marginBottom: 0 }}>
                        API Key 将使用加密存储，不会以明文形式保存在数据库中。
                    </Paragraph>
                </Card>
            </Modal>

            {/* 修改公司数据库密码弹窗（仅管理员/最高级管理员） */}
            <Modal
                title={<span><SafetyOutlined /> 修改公司数据库密码</span>}
                open={cpwdModalOpen}
                onCancel={() => setCpwdModalOpen(false)}
                footer={null}
                destroyOnClose
            >
                <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 20 }}
                    message="公司数据库密码"
                    description={
                        isSuperAdmin
                            ? `最高级管理员可修改任意公司的数据库密码：填写下方「目标公司」即可（留空=当前公司「${user?.company_name || '-'}」）。修改后原密码立即失效，成员需用新密码重新加入/访问。`
                            : `当前公司：${user?.company_name || '-'}。仅可修改本公司数据库密码，修改后原密码立即失效，成员需用新密码重新加入/访问。`
                    }
                />
                <Form
                    form={cpwdForm}
                    layout="vertical"
                    onFinish={handleChangeCompanyPassword}
                >
                    {isSuperAdmin && (
                        <Form.Item
                            name="company_name"
                            label="目标公司"
                            extra="留空则修改当前公司；可填写任意公司名以修改其密码"
                        >
                            <Input placeholder="输入要修改密码的公司名称（默认当前公司）" />
                        </Form.Item>
                    )}
                    <Form.Item
                        name="old_password"
                        label="当前公司数据库密码"
                        rules={[{ required: true, message: '请输入当前公司数据库密码' }]}
                    >
                        <Input.Password placeholder="请输入当前公司数据库密码" />
                    </Form.Item>
                    <Form.Item
                        name="new_password"
                        label="新公司数据库密码"
                        rules={[
                            { required: true, message: '请输入新公司数据库密码' },
                            { min: 6, message: '密码至少6个字符' },
                        ]}
                    >
                        <Input.Password placeholder="请输入新公司数据库密码" />
                    </Form.Item>
                    <Form.Item
                        name="confirm_password"
                        label="确认新公司数据库密码"
                        dependencies={['new_password']}
                        rules={[
                            { required: true, message: '请确认新公司数据库密码' },
                            ({ getFieldValue }) => ({
                                validator(_, value) {
                                    if (!value || getFieldValue('new_password') === value) {
                                        return Promise.resolve();
                                    }
                                    return Promise.reject(new Error('两次输入不一致'));
                                },
                            }),
                        ]}
                    >
                        <Input.Password placeholder="请确认新公司数据库密码" />
                    </Form.Item>
                    <Form.Item>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                            <Button onClick={() => setCpwdModalOpen(false)}>取消</Button>
                            <Button type="primary" htmlType="submit" loading={cpwdLoading}>确认修改</Button>
                        </div>
                    </Form.Item>
                </Form>
            </Modal>
        </Layout>
    );
}
