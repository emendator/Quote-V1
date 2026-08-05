import { Input, Button, Space, Switch, Tooltip, message } from 'antd';
import { SearchOutlined, ThunderboltOutlined, UnorderedListOutlined } from '@ant-design/icons';

const { TextArea } = Input;

interface Props {
    value?: string;
    aiMode?: boolean;
    batchMode?: boolean;
    hasApiKey?: boolean;
    tokensUsed?: number;
    onValueChange?: (text: string, ai: boolean, batch?: boolean) => void;
    onQuery: (text: string, useAI: boolean, useBatch?: boolean) => void;
    loading: boolean;
}

export default function SmartQueryInput({ value, aiMode, batchMode, hasApiKey, tokensUsed, onValueChange, onQuery, loading }: Props) {
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
                    ? '批量快查型号查询：每行一个快查型号（支持模糊匹配）\n例如：\nK1 pro-追觅\nAF10 Lite-追觅\nAP10-追觅\nPM NEO-追觅'
                    : '请输入查询内容，支持：69码查询、快查型号、品牌、品类、价格区间、合作等级、供货状态…\n也支持直接粘贴微信群客户询价消息，系统会自动识别其中的商品信息'}
                rows={batchMode ? 10 : 4}
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
                                onChange={(v) => onValueChange?.(value ?? '', false, v)}
                                style={{ marginLeft: 4 }}
                            />
                            <span style={{ marginLeft: 4, fontSize: 12, color: batchMode ? '#52c41a' : '#999' }}>
                                批量
                            </span>
                        </span>
                    </Tooltip>
                    {/* 批量查询为纯规则匹配，不需要 AI 开关，批量模式下隐藏 */}
                    {!batchMode && (
                        <Tooltip title={!hasApiKey ? '未配置 API Key，无法使用 AI 模式。请在右上角用户菜单中配置。' : aiMode ? 'AI 模式：使用 DeepSeek 分析自然语言' : '普通模式：使用正则规则匹配'}>
                            <span>
                                <ThunderboltOutlined style={{ color: aiMode ? '#faad14' : '#d9d9d9' }} />
                                <Switch
                                    size="small"
                                    checked={aiMode ?? false}
                                    onChange={(v) => {
                                        if (!hasApiKey) {
                                            message.warning('未配置 API Key，无法使用 AI 模式。请在右上角用户菜单中配置。');
                                            return;
                                        }
                                        onValueChange?.(value ?? '', v, batchMode ?? false);
                                    }}
                                    style={{ marginLeft: 4 }}
                                />
                                <span style={{ marginLeft: 4, fontSize: 12, color: aiMode ? '#faad14' : '#999' }}>
                                    AI
                                </span>
                            </span>
                        </Tooltip>
                    )}
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
                    ? '提示：每行输入一个快查型号，系统会分别查询每个型号的代发价 | 支持模糊匹配'
                    : '提示：按 Enter 快速查询 | Shift+Enter 换行 | 筛选项变动后自动查询'}
            </div>
            {tokensUsed ? (
                <div style={{ marginTop: 4, color: '#722ed1', fontSize: 12 }}>
                    本次查询消耗 <strong>{tokensUsed}</strong> tokens
                </div>
            ) : null}
        </div>
    );
}
