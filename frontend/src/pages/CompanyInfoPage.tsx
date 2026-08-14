import React, { useState } from 'react';
import { Form, Input, Button, Typography, message, Descriptions, Radio, Alert } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import AuthShell from '../components/AuthShell';

const { Text } = Typography;

const CompanyInfoPage: React.FC = () => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState<'create' | 'join'>('join');
    const { user, bindCompany, isSuperAdmin, isAdmin } = useAuth();
    const navigate = useNavigate();

    const isBound = !!user?.company_id;
    const canCreate = isSuperAdmin || isAdmin;

    const onFinish = async (values: any) => {
        setLoading(true);
        try {
            // 绑定公司（公司名称 + 公司数据库密码）
            await bindCompany({
                mode,
                company_name: values.company_name,
                company_password: values.company_password,
            });
            message.success('公司绑定成功');
            navigate('/', { replace: true });
        } catch (err: any) {
            message.error(err.message || '绑定失败');
        } finally {
            setLoading(false);
        }
    };

    // 已绑定公司：只读展示（公司归属不可更改）
    if (isBound) {
        return (
            <AuthShell>
                <div className="auth-card dd-company-card dd-blur-reveal" style={{ width: 460 }}>
                    <div className="auth-card-logo">
                        <div className="dd-brand-mark">¥</div>
                        <div className="auth-card-title">公司信息</div>
                        <div className="auth-card-sub">你的公司归属已绑定</div>
                    </div>

                    <Descriptions style={{ marginTop: 14 }} column={1} size="middle" colon={false}>
                        <Descriptions.Item label="公司名称">
                            <Text strong style={{ fontSize: 16 }}>{user?.company_name}</Text>
                        </Descriptions.Item>
                    </Descriptions>

                    <Alert
                        style={{ marginTop: 12 }}
                        type="info"
                        showIcon
                        message="公司归属已绑定，不可修改"
                        description="如需更换公司，请联系最高级管理员处理。"
                    />

                    <div style={{ marginTop: 16 }}>
                        <Button type="primary" block size="large" onClick={() => navigate('/', { replace: true })} className="dd-shimmer" data-magnetic>
                            返回工作台
                        </Button>
                    </div>
                </div>
            </AuthShell>
        );
    }

    return (
        <AuthShell>
            <div className="auth-card dd-company-card dd-blur-reveal" style={{ width: 460 }}>
                <div className="auth-card-logo">
                    <div className="dd-brand-mark">¥</div>
                    <div className="auth-card-title">完善公司信息</div>
                    <div className="auth-card-sub">填写公司名称和公司数据库密码，加入或创建公司</div>
                </div>

                <Form
                    form={form}
                    layout="vertical"
                    onFinish={onFinish}
                    className="dd-company-form"
                    style={{ marginTop: 8 }}
                    size="large"
                >
                    {canCreate ? (
                        <>
                            <Alert
                                style={{ marginTop: 16 }}
                                type="info"
                                showIcon
                                message="选择公司类型"
                                description="管理员可创建新公司（设置公司数据库密码），或加入已有公司（输入公司名称与密码）。"
                            />
                            <Radio.Group
                                style={{ marginTop: 16 }}
                                value={mode}
                                onChange={(e) => setMode(e.target.value)}
                                optionType="button"
                                buttonStyle="solid"
                            >
                                <Radio.Button value="create">新注册公司</Radio.Button>
                                <Radio.Button value="join">加入已有公司</Radio.Button>
                            </Radio.Group>
                        </>
                    ) : (
                        <Alert
                            style={{ marginTop: 16 }}
                            type="info"
                            showIcon
                            message="加入公司"
                            description="只能凭「公司名称 + 公司数据库密码」加入已有公司；如有疑问，请联系公司管理员。"
                        />
                    )}

                    {mode === 'create' && (
                        <Alert
                            style={{ marginTop: 12 }}
                            type="warning"
                            showIcon
                            message="公司名称填写后不可修改"
                            description="创建后公司名称将无法修改，请确认无误后再提交。"
                        />
                    )}

                    <Form.Item
                        name="company_name"
                        label="公司名称"
                        rules={[{ required: true, message: '请输入公司名称' }]}
                        style={{ marginTop: 10, marginBottom: 10 }}
                    >
                        <Input placeholder={mode === 'create' ? '请输入新公司名称（创建后不可修改）' : '请输入公司名称'} />
                    </Form.Item>

                    <Form.Item
                        name="company_password"
                        label="公司数据库密码"
                        rules={[
                            { required: true, message: '请输入公司数据库密码' },
                            { min: 6, message: '公司数据库密码至少6个字符' },
                        ]}
                        extra={mode === 'create' ? '用于公司成员访问校验，请妥善保管' : '由公司管理员提供'}
                        style={{ marginBottom: 10 }}
                    >
                        <Input.Password placeholder="请输入公司数据库密码" />
                    </Form.Item>

                    <Form.Item
                        name="confirm_password"
                        label="确认公司数据库密码"
                        dependencies={['company_password']}
                        rules={[
                            { required: true, message: '请再次输入公司数据库密码' },
                            ({ getFieldValue }) => ({
                                validator(_, value) {
                                    if (!value || getFieldValue('company_password') === value) {
                                        return Promise.resolve();
                                    }
                                    return Promise.reject(new Error('两次输入的公司数据库密码不一致'));
                                },
                            }),
                        ]}
                        style={{ marginBottom: 16 }}
                    >
                        <Input.Password placeholder="请再次输入公司数据库密码" />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 0 }}>
                        <Button type="primary" htmlType="submit" loading={loading} block className="dd-shimmer" data-magnetic>
                            绑定并进入系统
                        </Button>
                    </Form.Item>
                </Form>
            </div>
        </AuthShell>
    );
};

export default CompanyInfoPage;
