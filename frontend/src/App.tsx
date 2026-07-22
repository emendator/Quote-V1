import { Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/Layout';
import HomePage from './pages/HomePage';
import DataManagePage from './pages/DataManagePage';
import PlatformManagePage from './pages/PlatformManagePage';
import ListingLogsPage from './pages/ListingLogsPage';
import SolutionPage from './pages/SolutionPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import CompanyInfoPage from './pages/CompanyInfoPage';
import InviteCodePage from './pages/InviteCodePage';
import RequireAuth from './components/RequireAuth';
import { PageStateProvider } from './store/PageStateContext';
import { AuthProvider } from './store/AuthContext';

function App() {
    return (
        <ConfigProvider locale={zhCN}>
            <PageStateProvider>
                <AuthProvider>
                    <Routes>
                        {/* 公开路由 */}
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />

                        {/* 需登录 - 完善公司信息 */}
                        <Route path="/company-info" element={
                            <RequireAuth><CompanyInfoPage /></RequireAuth>
                        } />

                        {/* 需登录 - 主布局 */}
                        <Route element={
                            <RequireAuth><AppLayout /></RequireAuth>
                        }>
                            <Route path="/" element={<HomePage />} />
                            <Route path="/data" element={<DataManagePage />} />
                            <Route path="/platforms" element={<PlatformManagePage />} />
                            <Route path="/listing-logs" element={<ListingLogsPage />} />
                            <Route path="/solutions" element={<SolutionPage />} />
                            <Route path="/invite-codes" element={
                                <RequireAuth roles={['super_admin', 'admin']}><InviteCodePage /></RequireAuth>
                            } />
                        </Route>

                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </AuthProvider>
            </PageStateProvider>
        </ConfigProvider>
    );
}

export default App;
