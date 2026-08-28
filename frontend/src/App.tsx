import { Routes, Route } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { lightTheme, darkTheme } from './theme';
import AppLayout from './components/Layout';
import HomePage from './pages/HomePage';
import DataManagePage from './pages/DataManagePage';
import SolutionPage from './pages/SolutionPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import CompanyInfoPage from './pages/CompanyInfoPage';
import InviteCodePage from './pages/InviteCodePage';
import NotFoundPage from './pages/NotFoundPage';
import RequireAuth from './components/RequireAuth';
import { PageStateProvider } from './store/PageStateContext';
import { AuthProvider } from './store/AuthContext';
import { ThemeProvider, useTheme } from './store/ThemeContext';

function ThemedApp() {
    const { mode } = useTheme();

    return (
        <ConfigProvider locale={zhCN} theme={mode === 'dark' ? darkTheme : lightTheme}>
            <AntApp>
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
                                <Route path="/solutions" element={<SolutionPage />} />
                                <Route path="/invite-codes" element={
                                    <RequireAuth roles={['super_admin', 'admin']}><InviteCodePage /></RequireAuth>
                                } />
                            </Route>

                            {/* 未匹配路由 → 交互式 404（未登录时进入登录页，已登录时展示 404） */}
                            <Route path="*" element={<NotFoundPage />} />
                        </Routes>
                    </AuthProvider>
                </PageStateProvider>
            </AntApp>
        </ConfigProvider>
    );
}

function App() {
    return (
        <ThemeProvider>
            <ThemedApp />
        </ThemeProvider>
    );
}

export default App;
