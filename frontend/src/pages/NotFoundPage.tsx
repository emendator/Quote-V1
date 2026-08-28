import { useNavigate } from 'react-router-dom';
import { Button, Space } from 'antd';
import { HomeOutlined, SearchOutlined } from '@ant-design/icons';

/** 交互式 404 页面（Interactive 404 / Error Page）—— 把死路变成小惊喜 */
export default function NotFoundPage() {
    const navigate = useNavigate();
    return (
        <div className="dd-empty" style={{ minHeight: '70vh', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div className="dd-404-digits" data-tilt aria-hidden="true">
                <span>4</span>
                <span className="dd-404-coin">¥</span>
                <span>4</span>
            </div>
            <div className="dd-empty-title" style={{ marginTop: 8 }}>这里没有报价</div>
            <div className="dd-empty-desc" style={{ marginTop: 4 }}>
                页面不存在或已被移除 —— 也许你想回到工作台继续报价？
            </div>
            <Space size={12} style={{ marginTop: 24, justifyContent: 'center' }}>
                <Button type="primary" size="large" icon={<HomeOutlined />} onClick={() => navigate('/', { replace: true })} className="dd-shimmer" data-magnetic>
                    返回智能查询
                </Button>
                <Button size="large" icon={<SearchOutlined />} onClick={() => navigate('/data', { replace: true })}>
                    去商品管理
                </Button>
            </Space>
        </div>
    );
}
