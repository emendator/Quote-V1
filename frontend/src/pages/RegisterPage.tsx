import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, message, Steps } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, KeyOutlined } from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { verifyInviteCode } from '../services/api';

const { Title, Text } = Typography;

const RegisterPage: React.FC = () => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [inviteValid, setInviteValid] = useState<{ valid: boolean; type?: string | null; message: string } | null>(null);
    const [checkingInvite, setCheckingInvite] = useState(false);
    const { register, user } = useAuth();
    const navigate = useNavigate();

    React.useEffect(() => {
        if (user) {
            navigate('/', { replace: true });
        }
    }, [user, navigate]);

    const handleCheckInvite = async () => {
        const code = form.getFieldValue('invite_code');
        if (!code) {
            message.warning('请先输入邀请码');
            return;
        }
        setCheckingInvite(true);
        try {
            const result = await verifyInviteCode(code);
            setInviteValid(result);
            if (result.valid) {
                message.success(`邀请码有效，将注册为${result.type === 'admin' ? '管理员' : '用户'}角色`);
            } else {
                message.error(result.message);
            }
        } catch {
            message.error('验证邀请码失败');
        } finally {
            setCheckingInvite(false);
        }
    };

    const onFinish = async (values: any) => {
        setLoading(true);
        try {
            await register({
                username: values.username,
                password: values.password,
                email: values.email,
                invite_code: values.invite_code,
            });
            message.success('注册成功');
            // 所有注册用户都需要完善公司信息
            navigate('/company-info', { replace: true });
        } catch (err: any) {
            message.error(err.message || '注册失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.background} />
            <Card style={styles.card} bordered={false}>
                <div style={styles.logoArea}>
                    <Title level={3} style={{ margin: '0 0 4px', color: '#1a1a2e' }}>
                        创建账号
                    </Title>
                    <Text type="secondary">使用邀请码注册新账号</Text>
                </div>

                <Form
                    form={form}
                    layout="vertical"
                    onFinish={onFinish}
                    autoComplete="off"
                    style={{ marginTop: 24 }}
                    size="large"
                >
                    <Form.Item
                        name="username"
                        rules={[
                            { required: true, message: '请输入用户名' },
                            { min: 3, message: '用户名至少3个字符' },
                            { max: 20, message: '用户名最多20个字符' },
                            { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' },
                        ]}
                    >
                        <Input prefix={<UserOutlined style={{ color: '#bfbfbf' }} />} placeholder="用户名" />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[
                            { required: true, message: '请输入密码' },
                            { min: 6, message: '密码至少6个字符' },
                        ]}
                    >
                        <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="密码" />
                    </Form.Item>

                    <Form.Item
                        name="confirm_password"
                        dependencies={['password']}
                        rules={[
                            { required: true, message: '请确认密码' },
                            ({ getFieldValue }) => ({
                                validator(_, value) {
                                    if (!value || getFieldValue('password') === value) {
                                        return Promise.resolve();
                                    }
                                    return Promise.reject(new Error('两次输入的密码不一致'));
                                },
                            }),
                        ]}
                    >
                        <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="确认密码" />
                    </Form.Item>

                    <Form.Item
                        name="email"
                        rules={[
                            { required: true, message: '请输入邮箱' },
                            { type: 'email', message: '请输入有效的邮箱地址' },
                        ]}
                    >
                        <Input prefix={<MailOutlined style={{ color: '#bfbfbf' }} />} placeholder="邮箱" />
                    </Form.Item>

                    <Form.Item
                        name="invite_code"
                        rules={[
                            { required: true, message: '请输入邀请码' },
                        ]}
                        extra={
                            inviteValid && (
                                <Text type={inviteValid.valid ? 'success' : 'danger'}>
                                    {inviteValid.message}
                                </Text>
                            )
                        }
                    >
                        <Input
                            prefix={<KeyOutlined style={{ color: '#bfbfbf' }} />}
                            placeholder="邀请码"
                            onBlur={handleCheckInvite}
                            suffix={
                                <Button size="small" type="link" loading={checkingInvite} onClick={handleCheckInvite}>
                                    验证
                                </Button>
                            }
                        />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 12 }}>
                        <Button type="primary" htmlType="submit" loading={loading} block style={styles.registerBtn}>
                            注 册
                        </Button>
                    </Form.Item>

                    <div style={{ textAlign: 'center' }}>
                        <Text type="secondary">
                            已有账号？
                            <Link to="/login" style={{ marginLeft: 4 }}>返回登录</Link>
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
        top: 0, left: 0, right: 0, bottom: 0,
        background: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
        opacity: 0.5,
    },
    card: {
        width: 440,
        maxWidth: '100%',
        borderRadius: 16,
        boxShadow: '0 8px 40px rgba(0,0,0,0.15)',
        position: 'relative',
        zIndex: 1,
        padding: '28px 24px',
    },
    logoArea: {
        textAlign: 'center' as const,
    },
    registerBtn: {
        height: 44,
        borderRadius: 8,
        fontSize: 16,
    },
};

export default RegisterPage;
