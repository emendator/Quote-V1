import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/Layout';
import HomePage from './pages/HomePage';
import DataManagePage from './pages/DataManagePage';
import PlatformManagePage from './pages/PlatformManagePage';
import ListingLogsPage from './pages/ListingLogsPage';
import { PageStateProvider } from './store/PageStateContext';

function App() {
    return (
        <PageStateProvider>
            <Routes>
                <Route element={<AppLayout />}>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/data" element={<DataManagePage />} />
                    <Route path="/platforms" element={<PlatformManagePage />} />
                    <Route path="/listing-logs" element={<ListingLogsPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
            </Routes>
        </PageStateProvider>
    );
}

export default App;
