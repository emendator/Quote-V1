import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography } from 'antd';
import {
    SearchOutlined,
    DatabaseOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
    { key: '/', icon: <SearchOutlined />, label: '智能查询' },
    { key: '/data', icon: <DatabaseOutlined />, label: '数据管理' },
];

export default function AppLayout() {
    const navigate = useNavigate();
    const location = useLocation();

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider
                width={200}
                style={{ background: '#fff' }}
                breakpoint="lg"
                collapsedWidth="60"
            >
                <div style={{ padding: '20px 16px', textAlign: 'center' }}>
                    <Title level={5} style={{ margin: 0, color: '#1677ff' }}>
                        💰 智能报价
                    </Title>
                </div>
                <Menu
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    items={menuItems}
                    onClick={({ key }) => navigate(key)}
                    style={{ borderRight: 0 }}
                />
            </Sider>
            <Layout>
                <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
                    <Title level={4} style={{ margin: '16px 0', lineHeight: '32px' }}>
                        {location.pathname === '/' ? '🔍 智能报价查询' : '📋 商品数据管理'}
                    </Title>
                </Header>
                <Content style={{ padding: 24, overflow: 'auto' }}>
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    );
}
