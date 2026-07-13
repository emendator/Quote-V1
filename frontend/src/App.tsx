import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/Layout';
import HomePage from './pages/HomePage';
import DataManagePage from './pages/DataManagePage';

function App() {
    return (
        <Routes>
            <Route element={<AppLayout />}>
                <Route path="/" element={<HomePage />} />
                <Route path="/data" element={<DataManagePage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
        </Routes>
    );
}

export default App;
