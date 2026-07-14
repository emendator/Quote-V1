import { Input, Button, Space, Switch, Tooltip } from 'antd';
import { SearchOutlined, ThunderboltOutlined } from '@ant-design/icons';

const { TextArea } = Input;

interface Props {
    value?: string;
    aiMode?: boolean;
    onValueChange?: (text: string, ai: boolean) => void;
    onQuery: (text: string, useAI: boolean) => void;
    loading: boolean;
}

export default function SmartQueryInput({ value, aiMode, onValueChange, onQuery, loading }: Props) {
    const isControlled = value !== undefined;

    const handleSearch = () => {
        if (isControlled && value?.trim()) {
            onQuery(value.trim(), aiMode ?? false);
        }
    };

    return (
        <div className="query-input-wrapper" style={{ maxWidth: 960, margin: '0 auto' }}>
            <TextArea
                className="query-textarea"
                value={isControlled ? value : undefined}
                onChange={(e) => onValueChange?.(e.target.value, aiMode ?? false)}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        if (!e.shiftKey && isControlled && value?.trim()) {
                            e.preventDefault();
                            onQuery(value.trim(), aiMode ?? false);
                        }
                    }
                }}
                placeholder="请输入查询内容，支持：69码查询、快查型号、品牌、品类、价格区间、合作等级、供货状态…
也支持直接粘贴微信群客户询价消息，系统会自动识别其中的商品信息"
                rows={2}
                style={{ fontSize: 14 }}
            />
            <div style={{ marginTop: 8, textAlign: 'right' }}>
                <Space>
                    <Tooltip title={aiMode ? 'AI 模式：使用 DeepSeek 分析自然语言' : '普通模式：使用正则规则匹配'}>
                        <span>
                            <ThunderboltOutlined style={{ color: aiMode ? '#faad14' : '#d9d9d9' }} />
                            <Switch
                                size="small"
                                checked={aiMode ?? false}
                                onChange={(v) => onValueChange?.(value ?? '', v)}
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
                        {aiMode ? 'AI 智能查询' : '智能查询'}
                    </Button>
                </Space>
            </div>
            <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                提示：按 Enter 快速查询 | Shift+Enter 换行 | 筛选项变动后自动查询
            </div>
        </div>
    );
}
