import { useState, useEffect, useCallback } from 'react';
import {
    Table, Button, Space, Modal, Form, Input, Select, Switch, message, Popconfirm, Tag, Tooltip, Collapse, Typography,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined, LinkOutlined, SettingOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
    fetchPlatforms, createPlatform, updatePlatform, deletePlatform, testPlatformConnection,
} from '../services/api';
import type { PlatformConfig, PlatformConfigCreate, PlatformConfigUpdate } from '../types';

const { Text } = Typography;

const PLATFORM_TYPES: { value: string; label: string }[] = [
    { value: 'taobao', label: '淘宝/天猫' },
    { value: 'jd', label: '京东' },
    { value: 'pinduoduo', label: '拼多多' },
];

const PLATFORM_TYPE_MAP: Record<string, string> = {
    taobao: '淘宝/天猫',
    jd: '京东',
    pinduoduo: '拼多多',
};

export default function PlatformManagePage() {
    const [platforms, setPlatforms] = useState<PlatformConfig[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);
    const [editingPlatform, setEditingPlatform] = useState<PlatformConfig | null>(null);
    const [testingId, setTestingId] = useState<number | null>(null);
    const [form] = Form.useForm();

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchPlatforms();
            setPlatforms(data);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '加载失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleAdd = () => {
        setEditingPlatform(null);
        form.resetFields();
        form.setFieldsValue({ is_active: true, extra_config: {}, extra_config_json: '' });
        setModalOpen(true);
    };

    const handleEdit = (record: PlatformConfig) => {
        setEditingPlatform(record);
        const extraConfig = record.extra_config || {};
        form.setFieldsValue({
            name: record.name,
            platform_type: record.platform_type,
            api_base_url: record.api_base_url,
            api_key: record.api_key === '******' ? '' : record.api_key,
            api_secret: record.api_secret === '******' ? '' : record.api_secret,
            shop_id: record.shop_id,
            extra_config: extraConfig,
            extra_config_json: Object.keys(extraConfig).length > 0 ? JSON.stringify(extraConfig, null, 2) : '',
            is_active: record.is_active,
        });
        setModalOpen(true);
    };

    const handleDelete = async (id: number) => {
        try {
            await deletePlatform(id);
            message.success('删除成功');
            loadData();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '删除失败';
            message.error(msg);
        }
    };

    const handleTest = async (id: number) => {
        setTestingId(id);
        try {
            const result = await testPlatformConnection(id);
            if (result.success) {
                message.success(result.message);
            } else {
                message.warning(result.message);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '测试失败';
            message.error(msg);
        } finally {
            setTestingId(null);
        }
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();

            // 合并 extra_config
            const extraConfig: Record<string, unknown> = { ...(values.extra_config || {}) };
            if (values.extra_config_json) {
                try {
                    const parsed = JSON.parse(values.extra_config_json);
                    Object.assign(extraConfig, parsed);
                } catch {
                    message.warning('扩展配置 JSON 格式错误，已忽略');
                }
            }

            if (editingPlatform) {
                const updateData: PlatformConfigUpdate = {};
                if (values.name !== editingPlatform.name) updateData.name = values.name;
                if (values.platform_type !== editingPlatform.platform_type) updateData.platform_type = values.platform_type;
                if (values.api_base_url !== editingPlatform.api_base_url) updateData.api_base_url = values.api_base_url;
                if (values.api_key) updateData.api_key = values.api_key;
                if (values.api_secret) updateData.api_secret = values.api_secret;
                if (values.shop_id !== editingPlatform.shop_id) updateData.shop_id = values.shop_id;
                if (values.is_active !== editingPlatform.is_active) updateData.is_active = values.is_active;
                updateData.extra_config = extraConfig;
                await updatePlatform(editingPlatform.id, updateData);
                message.success('更新成功');
            } else {
                const createData: PlatformConfigCreate = {
                    name: values.name,
                    platform_type: values.platform_type,
                    api_base_url: values.api_base_url || '',
                    api_key: values.api_key || '',
                    api_secret: values.api_secret || '',
                    shop_id: values.shop_id || '',
                    extra_config: extraConfig,
                    is_active: values.is_active !== false,
                };
                await createPlatform(createData);
                message.success('新增成功');
            }
            setModalOpen(false);
            loadData();
        } catch (err: unknown) {
            if (err instanceof Error) {
                message.error(err.message);
            }
        }
    };

    const columns: ColumnsType<PlatformConfig> = [
        {
            title: '序号',
            key: 'index',
            width: 60,
            render: (_, __, index) => index + 1,
        },
        {
            title: '平台名称',
            dataIndex: 'name',
            key: 'name',
            width: 180,
        },
        {
            title: '平台类型',
            dataIndex: 'platform_type',
            key: 'platform_type',
            width: 120,
            render: (v: string) => {
                const label = PLATFORM_TYPE_MAP[v] || v;
                const colorMap: Record<string, string> = {
                    taobao: 'orange',
                    jd: 'red',
                    pinduoduo: 'blue',
                };
                return <Tag color={colorMap[v] || 'default'}>{label}</Tag>;
            },
        },
        {
            title: 'API地址',
            dataIndex: 'api_base_url',
            key: 'api_base_url',
            width: 280,
            ellipsis: true,
            render: (v: string) => (
                <Tooltip title={v}>
                    <span>{v || '-'}</span>
                </Tooltip>
            ),
        },
        {
            title: '店铺ID',
            dataIndex: 'shop_id',
            key: 'shop_id',
            width: 140,
            render: (v: string) => v || '-',
        },
        {
            title: '状态',
            dataIndex: 'is_active',
            key: 'is_active',
            width: 80,
            render: (v: boolean) => (
                <Tag color={v ? 'green' : 'default'}>{v ? '已启用' : '已禁用'}</Tag>
            ),
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 170,
            render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
        },
        {
            title: '操作',
            key: 'action',
            width: 180,
            fixed: 'right',
            render: (_, record) => (
                <Space size="small">
                    <Button
                        type="link"
                        size="small"
                        icon={<ApiOutlined />}
                        loading={testingId === record.id}
                        onClick={() => handleTest(record.id)}
                    >
                        测试
                    </Button>
                    <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        编辑
                    </Button>
                    <Popconfirm
                        title="确认删除此平台配置？"
                        onConfirm={() => handleDelete(record.id)}
                        okText="确认"
                        cancelText="取消"
                    >
                        <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div>
            <div style={{ marginBottom: 16 }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                    新增平台
                </Button>
                <span style={{ marginLeft: 12, color: '#999', fontSize: 13 }}>
                    配置第三方电商平台的API连接信息，支持淘宝/天猫、京东、拼多多等
                </span>
            </div>

            <Table
                rowKey="id"
                columns={columns}
                dataSource={platforms}
                loading={loading}
                pagination={false}
                scroll={{ x: 1000 }}
                size="middle"
            />

            <Modal
                title={editingPlatform ? '编辑平台配置' : '新增平台配置'}
                open={modalOpen}
                onOk={handleSubmit}
                onCancel={() => setModalOpen(false)}
                okText="确认"
                cancelText="取消"
                width={700}
                destroyOnClose
            >
                <Form
                    form={form}
                    layout="vertical"
                    style={{ marginTop: 16 }}
                >
                    <Form.Item
                        name="name"
                        label="平台名称"
                        rules={[{ required: true, message: '请输入平台名称' }]}
                    >
                        <Input placeholder="例如：淘宝旗舰店" />
                    </Form.Item>
                    <Form.Item
                        name="platform_type"
                        label="平台类型"
                        rules={[{ required: true, message: '请选择平台类型' }]}
                    >
                        <Select
                            placeholder="请选择平台类型"
                            onChange={() => {
                                // 切换平台类型时重置额外配置
                                form.setFieldsValue({ extra_config: {} });
                            }}
                        >
                            {PLATFORM_TYPES.map((t) => (
                                <Select.Option key={t.value} value={t.value}>
                                    {t.label}
                                </Select.Option>
                            ))}
                        </Select>
                    </Form.Item>
                    <Form.Item
                        name="api_base_url"
                        label="API网关地址"
                        extra="正式环境地址，留空则使用平台默认地址"
                    >
                        <Input placeholder="留空使用平台默认网关地址" />
                    </Form.Item>
                    <Form.Item
                        name="api_key"
                        label={
                            <span>
                                API密钥 (AppKey/ClientId)
                                <Text type="secondary" style={{ fontSize: 12, marginLeft: 4 }}>
                                    从开放平台应用详情获取
                                </Text>
                            </span>
                        }
                        rules={[{ required: true, message: '请输入API密钥' }]}
                    >
                        <Input.Password
                            placeholder={editingPlatform ? '留空则不修改' : '请输入API密钥'}
                        />
                    </Form.Item>
                    <Form.Item
                        name="api_secret"
                        label={
                            <span>
                                API密钥 (AppSecret/ClientSecret)
                                <Text type="secondary" style={{ fontSize: 12, marginLeft: 4 }}>
                                    用于请求签名，请妥善保管
                                </Text>
                            </span>
                        }
                        rules={[{ required: true, message: '请输入API密钥Secret' }]}
                    >
                        <Input.Password
                            placeholder={editingPlatform ? '留空则不修改' : '请输入API密钥Secret'}
                        />
                    </Form.Item>
                    <Form.Item
                        name="shop_id"
                        label="店铺ID"
                        extra="在平台店铺后台获取"
                    >
                        <Input placeholder="店铺ID（选填）" />
                    </Form.Item>
                    <Form.Item name="is_active" label="启用状态" valuePropName="checked">
                        <Switch checkedChildren="启用" unCheckedChildren="禁用" />
                    </Form.Item>

                    {/* 平台专属配置 */}
                    <Collapse
                        ghost
                        items={[
                            {
                                key: 'advanced',
                                label: (
                                    <span>
                                        <SettingOutlined style={{ marginRight: 4 }} />
                                        平台专属配置（类目ID、运费模板等）
                                    </span>
                                ),
                                children: (
                                    <div style={{ padding: '8px 0' }}>
                                        <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 13 }}>
                                            以下为可选配置，根据各平台 API 文档填写的类目 ID、运费模板等参数。
                                            可通过 <Tag>extra_config</Tag> 字段扩展更多参数。
                                        </Text>

                                        {/* 淘宝专属配置 */}
                                        <Form.Item noStyle shouldUpdate={(prev, cur) => prev.platform_type !== cur.platform_type}>
                                            {({ getFieldValue }) => {
                                                const type = getFieldValue('platform_type');
                                                if (type !== 'taobao') return null;
                                                return (
                                                    <div style={{ background: '#fff7e6', padding: 12, borderRadius: 6, marginBottom: 12 }}>
                                                        <Text strong style={{ color: '#d46b08' }}>🔸 淘宝/天猫 专属配置</Text>
                                                        <div style={{ marginTop: 8 }}>
                                                            <Form.Item name={['extra_config', 'taobao_cat_id']} label="商品类目ID(cat_id)" style={{ marginBottom: 12 }}>
                                                                <Input placeholder="例如：50008055，在淘宝开放平台查询类目" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'taobao_freight_id']} label="运费模板ID(freight_id)" style={{ marginBottom: 12 }}>
                                                                <Input placeholder="在淘宝店铺后台-物流管理获取" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'province']} label="所在地-省" style={{ marginBottom: 8 }}>
                                                                <Input placeholder="例如：浙江省" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'city']} label="所在地-市" style={{ marginBottom: 0 }}>
                                                                <Input placeholder="例如：杭州市" />
                                                            </Form.Item>
                                                        </div>
                                                    </div>
                                                );
                                            }}
                                        </Form.Item>

                                        {/* 京东专属配置 */}
                                        <Form.Item noStyle shouldUpdate={(prev, cur) => prev.platform_type !== cur.platform_type}>
                                            {({ getFieldValue }) => {
                                                const type = getFieldValue('platform_type');
                                                if (type !== 'jd') return null;
                                                return (
                                                    <div style={{ background: '#f0f5ff', padding: 12, borderRadius: 6, marginBottom: 12 }}>
                                                        <Text strong style={{ color: '#1677ff' }}>🔸 京东 专属配置</Text>
                                                        <div style={{ marginTop: 8 }}>
                                                            <Form.Item name={['extra_config', 'jd_category_id']} label="商品类目ID(cid)" style={{ marginBottom: 12 }}>
                                                                <Input placeholder="在京东开放平台查询类目ID" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'jd_shop_category']} label="店内分类(shop_category)" style={{ marginBottom: 12 }}>
                                                                <Input placeholder="店内分类名称" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'jd_freight_id']} label="运费模板ID(freight_id)" style={{ marginBottom: 8 }}>
                                                                <Input placeholder="在京东商家后台获取" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'warranty']} label="保修期" style={{ marginBottom: 0 }}>
                                                                <Input placeholder="例如：1年质保" />
                                                            </Form.Item>
                                                        </div>
                                                    </div>
                                                );
                                            }}
                                        </Form.Item>

                                        {/* 拼多多专属配置 */}
                                        <Form.Item noStyle shouldUpdate={(prev, cur) => prev.platform_type !== cur.platform_type}>
                                            {({ getFieldValue }) => {
                                                const type = getFieldValue('platform_type');
                                                if (type !== 'pinduoduo') return null;
                                                return (
                                                    <div style={{ background: '#f6ffed', padding: 12, borderRadius: 6, marginBottom: 12 }}>
                                                        <Text strong style={{ color: '#389e0d' }}>🔸 拼多多 专属配置</Text>
                                                        <div style={{ marginTop: 8 }}>
                                                            <Form.Item name={['extra_config', 'pdd_cat_id']} label="商品类目ID(cat_id)" style={{ marginBottom: 12 }}>
                                                                <Input placeholder="在拼多多开放平台查询类目ID" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'pdd_brand_id']} label="品牌ID(brand_id)" style={{ marginBottom: 12 }}>
                                                                <Input placeholder="在拼多多开放平台查询品牌ID" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'pdd_freight_id']} label="运费模板ID(freight_id)" style={{ marginBottom: 8 }}>
                                                                <Input placeholder="在拼多多商家后台获取" />
                                                            </Form.Item>
                                                            <Form.Item name={['extra_config', 'country_id']} label="国家ID" style={{ marginBottom: 0 }}>
                                                                <Input placeholder="默认0（中国）" />
                                                            </Form.Item>
                                                        </div>
                                                    </div>
                                                );
                                            }}
                                        </Form.Item>

                                        {/* 通用扩展配置 */}
                                        <Form.Item name="extra_config_json" label="扩展配置 (JSON)" extra="以上未覆盖的配置项可用 JSON 格式传入">
                                            <Input.TextArea
                                                rows={3}
                                                placeholder='例如：{"use_sandbox": true, "auth_code": "..."}'
                                            />
                                        </Form.Item>
                                    </div>
                                ),
                            },
                        ]}
                    />
                </Form>
            </Modal>
        </div>
    );
}
