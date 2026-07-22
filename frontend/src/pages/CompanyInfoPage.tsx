import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';

const { Title, Text } = Typography;

const CompanyInfoPage: React.FC = () => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const { user, updateCompanyInfo } = useAuth();
    const navigate = useNavigate();

    // 如果已填写公司信息，跳转首页
    React.useEffect(() => {
        if (user?.company_name) {
            navigate('/', { replace: true });
        }
    }, [user, navigate]);

    const onFinish = async (values: { company_name: string; contact_person?: string; contact_phone?: string; company_address?: string }) => {
        setLoading(true);
        try {
            await updateCompanyInfo(values);
            message.success('公司信息已保存');
            navigate('/', { replace: true });
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
                        完善公司信息
                    </Title>
                    <Text type="secondary">
                        请填写您的公司信息以完成注册
                    </Text>
                </div>

                <Form
                    form={form}
                    layout="vertical"
                    onFinish={onFinish}
                    initialValues={{ company_name: '' }}
                    style={{ marginTop: 24 }}
                    size="large"
                >
                    <Form.Item
                        name="company_name"
                        label="公司名称"
                        rules={[{ required: true, message: '请输入公司名称' }]}
                    >
                        <Input placeholder="请输入公司名称" />
                    </Form.Item>

                    <Form.Item
                        name="contact_person"
                        label="联系人"
                    >
                        <Input placeholder="请输入联系人（选填）" />
                    </Form.Item>

                    <Form.Item
                        name="contact_phone"
                        label="联系电话"
                    >
                        <Input placeholder="请输入联系电话（选填）" />
                    </Form.Item>

                    <Form.Item
                        name="company_address"
                        label="公司地址"
                    >
                        <Input.TextArea rows={2} placeholder="请输入公司地址（选填）" />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" loading={loading} block style={styles.saveBtn}>
                            保存并进入系统
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
        width: 480,
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
