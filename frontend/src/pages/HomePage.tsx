import { useState } from 'react';
import { message } from 'antd';
import SmartQueryInput from '../components/SmartQueryInput';
import QueryResult from '../components/QueryResult';
import { smartQuery } from '../services/api';
import type { SmartQueryResult } from '../types';

export default function HomePage() {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<SmartQueryResult | null>(null);

    const handleQuery = async (text: string) => {
        setLoading(true);
        try {
            const data = await smartQuery({ query_text: text });
            setResult(data);
            if (data.result_count === 0 && data.query_intent !== 'mixed') {
                message.info(data.message || '未找到匹配的商品');
            } else if (data.result_count > 0) {
                message.success(`找到 ${data.result_count} 条结果`);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '查询失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <SmartQueryInput onQuery={handleQuery} loading={loading} />
            <QueryResult result={result} />
        </div>
    );
}
