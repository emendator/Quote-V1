import { useState, useEffect } from 'react';
import { Form, Input, Button, Typography, message, Row, Col } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, KeyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { verifyInviteCode } from '../services/api';

const { Text } = Typography;

interface Props {
    /** 初始展示面：login=正面登录，register=背面注册 */
    initialSide?: 'login' | 'register';
}

/** 3D 翻转卡：正面登录 / 背面注册，点击「立即注册 / 前往登录」翻转 */
export default function AuthFlipCard({ initialSide = 'login' }: Props) {
    const [flipped, setFlipped] = useState(initialSide === 'register');
    const [loginForm] = Form.useForm();
    const [regForm] = Form.useForm();

    const [loginLoading, setLoginLoading] = useState(false);
    const [guestLoading, setGuestLoading] = useState(false);
    const [regLoading, setRegLoading] = useState(false);
    const [checkingInvite, setCheckingInvite] = useState(false);
    const [inviteValid, setInviteValid] = useState<{ valid: boolean; type?: string | null; message: string; company_name?: string } | null>(null);

    const { login, guestLogin, register, user } = useAuth();
    const navigate = useNavigate();

    // 如果已登录，跳转首页
    useEffect(() => {
        if (user) {
            navigate('/', { replace: true });
        }
    }, [user, navigate]);

    /* ---------- 登录 ---------- */
    const onLoginFinish = async (values: { username: string; password: string }) => {
        setLoginLoading(true);
        try {
            await login(values);
            message.success('登录成功');
            navigate('/', { replace: true });
        } catch (err: any) {
            message.error(err.message || '登录失败');
        } finally {
            setLoginLoading(false);
        }
    };

    /* ---------- 游客登录 ---------- */
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

    /* ---------- 邀请码验证 ---------- */
    const handleCheckInvite = async () => {
        const code = regForm.getFieldValue('invite_code');
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

    /* ---------- 注册 ---------- */
    const onRegisterFinish = async (values: any) => {
        setRegLoading(true);
        try {
            await register({
                username: values.username,
                password: values.password,
                email: values.email,
                invite_code: values.invite_code,
            });
            message.success('注册成功，请先完善公司信息');
            // 邀请码仅决定角色，公司归属需在「完善公司信息」页填写并绑定
            navigate('/company-info', { replace: true });
        } catch (err: any) {
            message.error(err.message || '注册失败');
        } finally {
            setRegLoading(false);
        }
    };

    return (
        <div className="dd-flip-card dd-blur-reveal">
            <div className={`dd-flip-inner ${flipped ? 'is-flipped' : ''}`}>
                {/* ============ 正面：登录 ============ */}
                <div className="dd-flip-face auth-card">
                    <div className="auth-card-logo">
                        <div className="dd-brand-mark">¥</div>
                        <div className="auth-card-title">欢迎回来</div>
                        <div className="auth-card-sub">登录你的报价工作台</div>
                    </div>

                    <Form
                        form={loginForm}
                        layout="vertical"
                        onFinish={onLoginFinish}
                        autoComplete="off"
                        style={{ marginTop: 24 }}
                        size="large"
                    >
                        <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                            <Input prefix={<UserOutlined style={{ color: 'var(--ink-400)' }} />} placeholder="用户名" />
                        </Form.Item>
                        <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                            <Input.Password prefix={<LockOutlined style={{ color: 'var(--ink-400)' }} />} placeholder="密码" />
                        </Form.Item>

                        <Form.Item style={{ marginBottom: 12 }}>
                            <Button type="primary" htmlType="submit" loading={loginLoading} block className="dd-shimmer" data-magnetic>
                                登录
                            </Button>
                        </Form.Item>

                        {/* 游客登录：可体验核心功能，退出后数据自动清除 */}
                        <Form.Item style={{ marginBottom: 4 }}>
                            <Button block loading={guestLoading} onClick={onGuestLogin} className="auth-guest-btn" data-magnetic>
                                游客登录（体验模式）
                            </Button>
                        </Form.Item>
                        <div style={{ textAlign: 'center', marginBottom: 14 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                游客可体验智能查询、商品管理、智能方案；所有数据均为临时数据，退出后自动清除
                            </Text>
                        </div>

                        <div className="auth-card-footer">
                            <Text type="secondary">
                                没有账号？
                                <Button type="link" size="small" style={{ padding: 0, fontSize: 13 }} onClick={() => setFlipped(true)}>
                                    立即注册
                                </Button>
                            </Text>
                        </div>
                    </Form>
                </div>

                {/* ============ 背面：注册（2×2 栅格） ============ */}
                <div className="dd-flip-face dd-flip-face-back auth-card">
                    <div className="auth-card-logo">
                        <div className="dd-brand-mark">¥</div>
                        <div className="auth-card-title">创建账号</div>
                        <div className="auth-card-sub">凭邀请码加入你的公司工作台</div>
                    </div>

                    <Form
                        form={regForm}
                        layout="vertical"
                        onFinish={onRegisterFinish}
                        autoComplete="off"
                        style={{ marginTop: 20 }}
                        size="large"
                    >
                        <Row gutter={14} className="dd-reg-grid">
                            <Col xs={24} sm={12}>
                                <Form.Item
                                    name="username"
                                    rules={[
                                        { required: true, message: '请输入用户名' },
                                        { min: 3, message: '用户名至少3个字符' },
                                        { max: 20, message: '用户名最多20个字符' },
                                        { pattern: /^[a-zA-Z0-9_]+$/, message: '仅支持字母、数字、下划线' },
                                    ]}
                                >
                                    <Input prefix={<UserOutlined style={{ color: 'var(--ink-400)' }} />} placeholder="用户名" />
                                </Form.Item>
                            </Col>
                            <Col xs={24} sm={12}>
                                <Form.Item
                                    name="email"
                                    rules={[
                                        { required: true, message: '请输入邮箱' },
                                        { type: 'email', message: '请输入有效的邮箱地址' },
                                    ]}
                                >
                                    <Input prefix={<MailOutlined style={{ color: 'var(--ink-400)' }} />} placeholder="邮箱" />
                                </Form.Item>
                            </Col>
                            <Col xs={24} sm={12}>
                                <Form.Item
                                    name="password"
                                    rules={[
                                        { required: true, message: '请输入密码' },
                                        { min: 6, message: '密码至少6个字符' },
                                    ]}
                                >
                                    <Input.Password prefix={<LockOutlined style={{ color: 'var(--ink-400)' }} />} placeholder="密码" />
                                </Form.Item>
                            </Col>
                            <Col xs={24} sm={12}>
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
                                    <Input.Password prefix={<LockOutlined style={{ color: 'var(--ink-400)' }} />} placeholder="确认密码" />
                                </Form.Item>
                            </Col>
                        </Row>

                        <Form.Item
                            name="invite_code"
                            rules={[{ required: true, message: '请输入邀请码' }]}
                            extra={
                                inviteValid && (
                                    <Text type={inviteValid.valid ? 'success' : 'danger'}>
                                        {inviteValid.message}
                                    </Text>
                                )
                            }
                        >
                            <Input
                                prefix={<KeyOutlined style={{ color: 'var(--ink-400)' }} />}
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
                            <Button type="primary" htmlType="submit" loading={regLoading} block className="dd-shimmer" data-magnetic>
                                注册
                            </Button>
                        </Form.Item>

                        <div className="auth-card-footer">
                            <Text type="secondary">
                                已有账号？
                                <Button type="link" size="small" style={{ padding: 0, fontSize: 13 }} onClick={() => setFlipped(false)}>
                                    前往登录
                                </Button>
                            </Text>
                        </div>
                    </Form>
                </div>
            </div>
        </div>
    );
}
