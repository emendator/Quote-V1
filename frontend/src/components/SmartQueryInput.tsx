import { useState } from 'react';
import { Input, Button, Tag, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';

const { TextArea } = Input;

const EXAMPLES = [
    '69码为6901234567890的报价',
    '规格为一箱的所有商品报价',
    '价格在200到300间的商品',
    '69码在123456到567890的商品',
    '查询所有商品，按价格从低到高',
];

interface Props {
    onQuery: (text: string) => void;
    loading: boolean;
}

export default function SmartQueryInput({ onQuery, loading }: Props) {
    const [text, setText] = useState('');

    const handleSearch = () => {
        if (text.trim()) {
            onQuery(text.trim());
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            handleSearch();
        }
    };

    return (
        <div className="query-input-wrapper">
            <TextArea
                className="query-textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="请输入查询内容，支持：69码查询、SKU查询、规格查询、价格区间查询…
也支持直接粘贴微信群客户询价消息，系统会自动识别其中的商品信息"
                rows={4}
                style={{ fontSize: 15 }}
            />
            <Space style={{ marginTop: 12, width: '100%', justifyContent: 'space-between' }}>
                <div className="query-examples">
                    {EXAMPLES.map((ex) => (
                        <Tag
                            key={ex}
                            className="query-example-tag"
                            color="blue"
                            onClick={() => {
                                setText(ex);
                                onQuery(ex);
                            }}
                        >
                            {ex}
                        </Tag>
                    ))}
                </div>
                <Button
                    type="primary"
                    icon={<SearchOutlined />}
                    onClick={handleSearch}
                    loading={loading}
                    size="large"
                >
                    智能查询
                </Button>
            </Space>
            <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                提示：按 Ctrl+Enter 快速查询 | 可直接粘贴微信群聊天记录
            </div>
        </div>
    );
}
