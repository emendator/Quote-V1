import React from 'react';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
    const [form] = Form.useForm();
    const [loading, setLoading] = React.useState(false);
    const [guestLoading, setGuestLoading] = React.useState(false);
    const { login, guestLogin, user } = useAuth();
    const navigate = useNavigate();

    // 如果已登录，跳转首页
    React.useEffect(() => {
        if (user) {
            navigate('/', { replace: true });
        }
    }, [user, navigate]);

    const onFinish = async (values: { username: string; password: string }) => {
        setLoading(true);
        try {
            await login(values);
            message.success('登录成功');
            navigate('/', { replace: true });
        } catch (err: any) {
            message.error(err.message || '登录失败');
        } finally {
            setLoading(false);
        }
    };

    const onGuestLogin = async () => {
        setGuestLoading(true);
        try {
            await guestLogin();
            message.success('游客登录成功');
            navigate('/', { replace: true });
        } catch (err: any) {
            message.error(err.message || '游客登录失败');
        } finally {
            setGuestLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.background} />
            <Card style={styles.card} bordered={false}>
                <div style={styles.logoArea}>
                    <div style={styles.logoIcon}>💡</div>
                    <Title level={3} style={{ margin: '8px 0 4px', color: '#1a1a2e' }}>
                        智能报价系统
                    </Title>
                    <Text type="secondary" style={{ fontSize: 14 }}>
                        请登录您的账号
                    </Text>
                </div>

                <Form
                    form={form}
                    layout="vertical"
                    onFinish={onFinish}
                    autoComplete="off"
                    style={{ marginTop: 32 }}
                    size="large"
                >
                    <Form.Item
                        name="username"
                        rules={[{ required: true, message: '请输入用户名' }]}
                    >
                        <Input
                            prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
                            placeholder="用户名"
                        />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: '请输入密码' }]}
                    >
                        <Input.Password
                            prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                            placeholder="密码"
                        />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 12 }}>
                        <Button type="primary" htmlType="submit" loading={loading} block style={styles.loginBtn}>
                            登 录
                        </Button>
                    </Form.Item>

                    {/* 游客登录：可体验核心功能，退出后数据自动清除 */}
                    <Form.Item style={{ marginBottom: 4 }}>
                        <Button block loading={guestLoading} onClick={onGuestLogin} style={styles.guestBtn}>
                            游客登录（体验模式）
                        </Button>
                    </Form.Item>
                    <div style={{ textAlign: 'center', marginBottom: 16 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                            游客可体验智能查询/数据管理/智能方案，不保留任何数据，退出登录后自动清除全部使用痕迹
                        </Text>
                    </div>

                    <div style={{ textAlign: 'center' }}>
                        <Text type="secondary">
                            没有账号？
                            <Link to="/register" style={{ marginLeft: 4 }}>立即注册</Link>
                        </Text>
                    </div>
                </Form>
            </Card>
        </div>
    );
};

const styles: Record<string, React.CSSProperties> = {
    container: {
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        position: 'relative',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: 24,
    },
    background: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
        opacity: 0.5,
    },
    card: {
        width: 420,
        maxWidth: '100%',
        borderRadius: 16,
        boxShadow: '0 8px 40px rgba(0,0,0,0.15)',
        position: 'relative',
        zIndex: 1,
        padding: '32px 24px',
    },
    logoArea: {
        textAlign: 'center' as const,
        marginBottom: 8,
    },
    logoIcon: {
        fontSize: 48,
        lineHeight: 1,
    },
    loginBtn: {
        height: 44,
        borderRadius: 8,
        fontSize: 16,
    },
    guestBtn: {
        height: 44,
        borderRadius: 8,
        fontSize: 15,
        borderStyle: 'dashed',
        color: '#764ba2',
        borderColor: '#764ba2',
    },
};

export default LoginPage;
