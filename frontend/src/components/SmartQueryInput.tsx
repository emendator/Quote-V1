import { Input, Button, Space, Switch, Tooltip } from 'antd';
import { SearchOutlined, ThunderboltOutlined, UnorderedListOutlined } from '@ant-design/icons';

const { TextArea } = Input;

interface Props {
    value?: string;
    aiMode?: boolean;
    batchMode?: boolean;
    onValueChange?: (text: string, ai: boolean, batch?: boolean) => void;
    onQuery: (text: string, useAI: boolean, useBatch?: boolean) => void;
    loading: boolean;
}

export default function SmartQueryInput({ value, aiMode, batchMode, onValueChange, onQuery, loading }: Props) {
    const isControlled = value !== undefined;

    const handleSearch = () => {
        if (isControlled && value?.trim()) {
            onQuery(value.trim(), aiMode ?? false, batchMode ?? false);
        }
    };

    return (
        <div className="query-input-wrapper" style={{ maxWidth: 960, margin: '0 auto' }}>
            <TextArea
                className="query-textarea"
                value={isControlled ? value : undefined}
                onChange={(e) => onValueChange?.(e.target.value, aiMode ?? false, batchMode ?? false)}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        if (!e.shiftKey && isControlled && value?.trim()) {
                            e.preventDefault();
                            onQuery(value.trim(), aiMode ?? false, batchMode ?? false);
                        }
                    }
                }}
                placeholder={batchMode
                    ? '批量快查型号查询：用空格分隔多个快查型号（支持模糊匹配）\n例如：K1 pro-追觅 AF10 Lite-追觅 AP10-追觅 PM NEO-追觅'
                    : '请输入查询内容，支持：69码查询、快查型号、品牌、品类、价格区间、合作等级、供货状态…\n也支持直接粘贴微信群客户询价消息，系统会自动识别其中的商品信息'}
                rows={batchMode ? 4 : 2}
                style={{ fontSize: 14 }}
            />
            <div style={{ marginTop: 8, textAlign: 'right' }}>
                <Space>
                    <Tooltip title={batchMode ? '批量模式：每行一个快查型号，分别查询代发价' : '普通查询模式'}>
                        <span>
                            <UnorderedListOutlined style={{ color: batchMode ? '#52c41a' : '#d9d9d9' }} />
                            <Switch
                                size="small"
                                checked={batchMode ?? false}
                                onChange={(v) => onValueChange?.(value ?? '', aiMode ?? false, v)}
                                style={{ marginLeft: 4 }}
                            />
                            <span style={{ marginLeft: 4, fontSize: 12, color: batchMode ? '#52c41a' : '#999' }}>
                                批量
                            </span>
                        </span>
                    </Tooltip>
                    <Tooltip title={aiMode ? 'AI 模式：使用 DeepSeek 分析自然语言' : '普通模式：使用正则规则匹配'}>
                        <span>
                            <ThunderboltOutlined style={{ color: aiMode ? '#faad14' : '#d9d9d9' }} />
                            <Switch
                                size="small"
                                checked={aiMode ?? false}
                                onChange={(v) => onValueChange?.(value ?? '', v, batchMode ?? false)}
                                style={{ marginLeft: 4 }}
                            />
                            <span style={{ marginLeft: 4, fontSize: 12, color: aiMode ? '#faad14' : '#999' }}>
                                AI
                            </span>
                        </span>
                    </Tooltip>
                    <Button
                        type="primary"
                        icon={<SearchOutlined />}
                        onClick={handleSearch}
                        loading={loading}
                        size="large"
                    >
                        {batchMode ? '批量查询' : aiMode ? 'AI 智能查询' : '智能查询'}
                    </Button>
                </Space>
            </div>
            <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                {batchMode
                    ? '提示：用空格分隔多个快查型号，系统会分别查询每个型号的代发价 | 支持模糊匹配'
                    : '提示：按 Enter 快速查询 | Shift+Enter 换行 | 筛选项变动后自动查询'}
            </div>
        </div>
    );
}
