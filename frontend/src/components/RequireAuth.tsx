import React, { type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuth } from '../store/AuthContext';
import type { UserRole } from '../types';

interface RequireAuthProps {
    children: ReactNode;
    roles?: UserRole[];
}

const RequireAuth: React.FC<RequireAuthProps> = ({ children, roles }) => {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div style={{
                display: 'flex', justifyContent: 'center', alignItems: 'center',
                height: '100vh', background: 'var(--paper)', flexDirection: 'column', gap: 20,
            }}>
                <div className="dd-brand-mark dd-float" style={{ width: 46, height: 46, borderRadius: 14, fontSize: 22, marginBottom: 0 }}>¥</div>
                <Spin size="large" />
                <div style={{ color: 'var(--ink-400)', fontSize: 13, letterSpacing: '0.08em' }}>正在加载工作台…</div>
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (roles && !roles.includes(user.role)) {
        return <Navigate to="/" replace />;
    }

    return <>{children}</>;
};

export default RequireAuth;
