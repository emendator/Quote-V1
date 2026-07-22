import { useState, useEffect, useCallback } from 'react';
import {
    Table, Button, Space, Modal, Form, Input, Select, Switch, message, Popconfirm, Tag, Tooltip, Collapse, Typography, Steps, Alert,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined, LinkOutlined, SettingOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
    fetchPlatforms, createPlatform, updatePlatform, deletePlatform, testPlatformConnection, analyzePlatformDoc,
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

    // AI 智能添加状态
    const [aiModalOpen, setAiModalOpen] = useState(false);
    const [aiStep, setAiStep] = useState(0);
    const [aiUrl, setAiUrl] = useState('');
    const [aiAnalyzing, setAiAnalyzing] = useState(false);
    const [aiResult, setAiResult] = useState<Record<string, any> | null>(null);
    const [aiForm] = Form.useForm();

    const openAiModal = () => {
        setAiStep(0);
        setAiUrl('');
        setAiResult(null);
        aiForm.resetFields();
        setAiModalOpen(true);
    };

    const handleAiAnalyze = async () => {
        const url = aiUrl.trim();
        if (!url) { message.warning('请输入API文档网址'); return; }
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            message.warning('请输入有效的网址（以 http:// 或 https:// 开头）');
            return;
        }
        setAiAnalyzing(true);
        try {
            const result = await analyzePlatformDoc(url);
            setAiResult(result);
            setAiStep(1);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '分析失败';
            message.error(msg);
        } finally {
            setAiAnalyzing(false);
        }
    };

    const handleAiCreate = async () => {
        try {
            const values = await aiForm.validateFields();
            const fields: Record<string, any> = {};
            const extraFields: Record<string, any> = {};
            // 将动态字段拆分到主字段和 extra_config
            if (aiResult?.fields) {
                for (const f of aiResult.fields as any[]) {
                    const val = values[f.key];
                    if (val !== undefined && val !== '') {
                        if (['api_key', 'api_secret', 'shop_id', 'api_base_url', 'callback_url', 'auth_code'].includes(f.key)) {
                            fields[f.key] = val;
                        } else {
                            extraFields[f.key] = val;
                        }
                    }
                }
            }
            if (aiResult?.extra_fields) {
                for (const f of aiResult.extra_fields as any[]) {
                    const val = values[f.key];
                    if (val !== undefined && val !== '') {
                        extraFields[f.key] = val;
                    }
                }
            }
            const payload: PlatformConfigCreate = {
                name: values.name || aiResult?.platform_name || '新平台',
                platform_type: values.platform_type || aiResult?.platform_type || 'other',
                api_base_url: fields.api_base_url || aiResult?.api_endpoint || '',
                api_key: fields.api_key || '',
                api_secret: fields.api_secret || '',
                shop_id: fields.shop_id || '',
                extra_config: extraFields,
                is_active: true,
            };
            await createPlatform(payload);
            message.success('平台配置创建成功');
            setAiModalOpen(false);
            loadData();
        } catch (err: unknown) {
            if (err instanceof Error) {
                message.error(err.message);
            }
        }
    };

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
                <Button style={{ marginLeft: 8 }} icon={<ThunderboltOutlined />} onClick={openAiModal}>
                    AI 智能添加
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

            {/* AI 智能添加平台 */}
            <Modal
                title={
                    <Space>
                        <ThunderboltOutlined style={{ color: '#faad14' }} />
                        <span>AI 智能添加平台</span>
                    </Space>
                }
                open={aiModalOpen}
                onCancel={() => setAiModalOpen(false)}
                footer={null}
                width={680}
                destroyOnClose
            >
                <Steps
                    current={aiStep}
                    size="small"
                    items={[
                        { title: '输入网址' },
                        { title: 'AI 分析结果' },
                        { title: '确认创建' },
                    ]}
                    style={{ marginBottom: 24 }}
                />

                {aiStep === 0 && (
                    <div>
                        <Alert
                            type="info"
                            showIcon
                            message="输入电商平台开放平台的 API 文档网址"
                            description="例如：https://open.taobao.com/docs/api_list.htm、https://jos.jd.com/apilist 等"
                            style={{ marginBottom: 16 }}
                        />
                        <Input
                            prefix={<LinkOutlined />}
                            placeholder="请输入 API 文档网址，如 https://open.taobao.com/..."
                            value={aiUrl}
                            onChange={e => setAiUrl(e.target.value)}
                            onPressEnter={handleAiAnalyze}
                            size="large"
                        />
                        <div style={{ marginTop: 16, textAlign: 'right' }}>
                            <Button type="primary" onClick={handleAiAnalyze} loading={aiAnalyzing} icon={<ThunderboltOutlined />} size="large">
                                {aiAnalyzing ? 'AI 分析中...' : '开始 AI 分析'}
                            </Button>
                        </div>
                    </div>
                )}

                {aiStep === 1 && aiResult && (
                    <div>
                        <Alert
                            type="success"
                            showIcon
                            message={`识别到平台：${aiResult.platform_name || '未知'}`}
                            description={aiResult.notes || `API 网关: ${aiResult.api_endpoint || '未识别'}`}
                            style={{ marginBottom: 16 }}
                        />
                        <Form
                            form={aiForm}
                            layout="vertical"
                            style={{ maxHeight: 400, overflow: 'auto' }}
                        >
                            <Form.Item name="name" label="平台名称" rules={[{ required: true, message: '请输入平台名称' }]}>
                                <Input placeholder={aiResult.platform_name || '例如：淘宝旗舰店'} />
                            </Form.Item>
                            <Form.Item name="platform_type" label="平台类型" rules={[{ required: true, message: '请选择平台类型' }]}>
                                <Select placeholder="请选择平台类型">
                                    {[
                                        { value: 'taobao', label: '淘宝/天猫' },
                                        { value: 'jd', label: '京东' },
                                        { value: 'pinduoduo', label: '拼多多' },
                                        { value: 'douyin', label: '抖音' },
                                        { value: 'kuaishou', label: '快手' },
                                        { value: 'weixin', label: '微信小店' },
                                        { value: 'other', label: '其他' },
                                    ].map(t => (
                                        <Select.Option key={t.value} value={t.value}>{t.label}</Select.Option>
                                    ))}
                                </Select>
                            </Form.Item>
                            {/* AI 动态生成的字段 */}
                            {(aiResult.fields as any[] || []).map((f: any) => (
                                <Form.Item
                                    key={f.key}
                                    name={f.key}
                                    label={f.label}
                                    rules={f.required ? [{ required: true, message: `请输入${f.label}` }] : []}
                                    extra={f.description}
                                >
                                    {f.type === 'password' ? (
                                        <Input.Password placeholder={f.placeholder || `请输入${f.label}`} />
                                    ) : f.type === 'select' && f.options ? (
                                        <Select placeholder={f.placeholder || `请选择${f.label}`}>
                                            {(f.options as string[]).map((opt: string) => (
                                                <Select.Option key={opt} value={opt}>{opt}</Select.Option>
                                            ))}
                                        </Select>
                                    ) : (
                                        <Input placeholder={f.placeholder || `请输入${f.label}`} />
                                    )}
                                </Form.Item>
                            ))}
                            {/* AI 动态生成的额外字段 */}
                            {(aiResult.extra_fields as any[] || []).map((f: any) => (
                                <Form.Item
                                    key={f.key}
                                    name={f.key}
                                    label={f.label}
                                    rules={f.required ? [{ required: true, message: `请输入${f.label}` }] : []}
                                    extra={f.description}
                                >
                                    {f.type === 'password' ? (
                                        <Input.Password placeholder={f.placeholder || `请输入${f.label}`} />
                                    ) : (
                                        <Input placeholder={f.placeholder || `请输入${f.label}`} />
                                    )}
                                </Form.Item>
                            ))}
                        </Form>
                        <div style={{ marginTop: 16, textAlign: 'right' }}>
                            <Space>
                                <Button onClick={() => setAiStep(0)}>返回修改网址</Button>
                                <Button type="primary" onClick={handleAiCreate} icon={<PlusOutlined />}>
                                    创建平台配置
                                </Button>
                            </Space>
                        </div>
                    </div>
                )}
            </Modal>
        </div>
    );
}
