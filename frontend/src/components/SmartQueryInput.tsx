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
            <div className="query-shell">
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
                        ? '每行输入一个快查型号（支持模糊匹配），例如：\nK1 pro-追觅\nAF10 Lite-追觅\nAP10-追觅\nPM NEO-追觅'
                        : '输入 69码、快查型号、品牌、品类、价格区间等条件；\n也可直接粘贴微信群客户询价消息，系统会自动识别商品信息'}
                    rows={batchMode ? 10 : 4}
                    style={{ fontSize: 15 }}
                />
                <div className="query-actions">
                    <div className="query-mode-switches">
                        <Tooltip title={batchMode ? '批量模式：每行一个快查型号，分别查询代发价' : '普通查询模式'}>
                            <span className={`query-mode-item ${batchMode ? 'active' : ''}`}>
                                <UnorderedListOutlined />
                                <Switch
                                    size="small"
                                    checked={batchMode ?? false}
                                    onChange={(v) => onValueChange?.(value ?? '', false, v)}
                                />
                                批量
                            </span>
                        </Tooltip>
                        {/* 批量查询为纯规则匹配，不需要 AI 开关，批量模式下隐藏 */}
                        {!batchMode && (
                            <Tooltip title={!hasApiKey ? '使用 AI 模式需先配置 API Key：请点击右上角用户菜单中的「API Key 配置」' : aiMode ? 'AI 模式：使用 DeepSeek 分析自然语言' : '普通模式：使用正则规则匹配'}>
                                <span className={`query-mode-item ${aiMode ? 'active' : ''}`}>
                                    <ThunderboltOutlined />
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
                                    />
                                    AI
                                </span>
                            </Tooltip>
                        )}
                        {tokensUsed ? (
                            <span className="query-tokens">
                                <ThunderboltOutlined /> 本次消耗 <strong>{tokensUsed}</strong> tokens
                            </span>
                        ) : null}
                    </div>
                    <Button
                        type="primary"
                        icon={<SearchOutlined />}
                        onClick={handleSearch}
                        loading={loading}
                        size="large"
                        className="dd-shimmer"
                    >
                        {batchMode ? '批量查询' : aiMode ? 'AI 智能查询' : '智能查询'}
                    </Button>
                </div>
            </div>
            <div className="query-hint">
                {batchMode
                    ? '提示：每行一个快查型号，分别查询各型号代发价；支持模糊匹配'
                    : '提示：按 Enter 快速查询 | Shift+Enter 换行 | 筛选项变动后自动查询'}
            </div>
        </div>
    );
}
