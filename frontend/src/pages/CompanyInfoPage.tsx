import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, message, Descriptions, Radio, Alert } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';

const { Title, Text } = Typography;

const CompanyInfoPage: React.FC = () => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState<'create' | 'join'>('join');
    const { user, updateCompanyInfo, bindCompany, isSuperAdmin, isAdmin } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const isEdit = searchParams.get('edit') === '1';

    const isBound = !!user?.company_id;
    const canCreate = isSuperAdmin || isAdmin;

    const onFinish = async (values: any) => {
        setLoading(true);
        try {
            if (isBound) {
                // 已绑定公司：仅更新联系方式（公司归属不可更改）
                await updateCompanyInfo({
                    contact_person: values.contact_person || '',
                    contact_phone: values.contact_phone || '',
                    company_address: values.company_address || '',
                });
                message.success('公司信息已保存');
            } else {
                // 未绑定：绑定公司（公司名称 + 公司数据库密码）
                await bindCompany({
                    mode,
                    company_name: values.company_name,
                    company_password: values.company_password,
                    contact_person: values.contact_person || '',
                    contact_phone: values.contact_phone || '',
                    company_address: values.company_address || '',
                });
                message.success('公司绑定成功');
            }
            if (isEdit) {
                navigate(-1);
            } else {
                navigate('/', { replace: true });
            }
        } catch (err: any) {
            message.error(err.message || '保存失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <Card style={styles.card} bordered={false}>
                <div style={styles.logoArea}>
                    <Title level={3} style={{ margin: '0 0 4px' }}>
                        {isBound ? (isEdit ? '修改公司信息' : '公司信息') : '完善公司信息'}
                    </Title>
                    <Text type="secondary">
                        {isBound
                            ? '公司归属已绑定，仅可修改联系方式'
                            : '请填写公司名称与公司数据库密码，加入或创建公司'}
                    </Text>
                </div>

                {isBound ? (
                    <Descriptions style={{ marginTop: 24 }} column={1} size="small">
                        <Descriptions.Item label="公司名称">
                            <Text strong>{user?.company_name}</Text>
                            <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                                （绑定后不可修改）
                            </Text>
                        </Descriptions.Item>
                    </Descriptions>
                ) : (
                    <>
                        {canCreate ? (
                            <>
                                <Alert
                                    style={{ marginTop: 20 }}
                                    type="info"
                                    showIcon
                                    message="选择公司类型"
                                    description="管理员可选择「新注册公司」（为公司创建数据库密码）或「加入已有公司」（输入已有公司的名称与数据库密码）。"
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
                                style={{ marginTop: 20 }}
                                type="info"
                                showIcon
                                message="加入公司"
                                description="您只能凭「公司名称 + 公司数据库密码」加入已有公司，不能创建新公司。如有疑问请联系公司管理员。"
                            />
                        )}

                        {mode === 'create' && (
                            <Alert
                                style={{ marginTop: 16 }}
                                type="warning"
                                showIcon
                                message="公司名称填写后不可修改"
                                description="新注册公司后，公司名称将永久固定，请确认无误后再提交。"
                            />
                        )}
                    </>
                )}

                <Form
                    form={form}
                    layout="vertical"
                    onFinish={onFinish}
                    initialValues={{
                        contact_person: user?.contact_person || '',
                        contact_phone: user?.contact_phone || '',
                        company_address: user?.company_address || '',
                    }}
                    style={{ marginTop: 16 }}
                    size="large"
                >
                    {!isBound && (
                        <>
                            <Form.Item
                                name="company_name"
                                label="公司名称"
                                rules={[{ required: true, message: '请输入公司名称' }]}
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
                                extra={mode === 'create' ? '用于该公司成员的访问校验，请妥善保管' : '由公司管理员提供'}
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
                            >
                                <Input.Password placeholder="请再次输入公司数据库密码" />
                            </Form.Item>
                        </>
                    )}

                    <Form.Item name="contact_person" label="联系人">
                        <Input placeholder="请输入联系人（选填）" />
                    </Form.Item>

                    <Form.Item name="contact_phone" label="联系电话">
                        <Input placeholder="请输入联系电话（选填）" />
                    </Form.Item>

                    <Form.Item name="company_address" label="公司地址">
                        <Input.TextArea rows={2} placeholder="请输入公司地址（选填）" />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" loading={loading} block style={styles.saveBtn}>
                            {isBound ? (isEdit ? '保存修改' : '保存') : '绑定并进入系统'}
                        </Button>
                    </Form.Item>
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
        background: '#f0f2f5',
        padding: 24,
    },
    card: {
        width: 520,
        maxWidth: '100%',
        borderRadius: 12,
        boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
        padding: '24px 32px',
    },
    logoArea: {
        textAlign: 'center' as const,
    },
    saveBtn: {
        height: 44,
        borderRadius: 8,
        fontSize: 16,
    },
};

export default CompanyInfoPage;
