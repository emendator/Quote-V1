import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { message } from 'antd';
import type { User, LoginRequest, RegisterRequest, CompanyInfoUpdate, CompanyBindRequest } from '../types';
import * as api from '../services/api';
import { PageStateContext } from './PageStateContext';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    isSuperAdmin: boolean;
    isAdmin: boolean;
    isUser: boolean;
    login: (data: LoginRequest) => Promise<void>;
    register: (data: RegisterRequest) => Promise<void>;
    logout: () => void;
    updateCompanyInfo: (data: CompanyInfoUpdate) => Promise<void>;
    bindCompany: (data: CompanyBindRequest) => Promise<void>;
    refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const pageCtx = useContext(PageStateContext);

    // 从 localStorage 恢复登录态
    const restoreSession = useCallback(async () => {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            setLoading(false);
            return;
        }
        try {
            const userData = await api.getCurrentUser();
            setUser(userData);
        } catch {
            // Token 无效，清除
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        restoreSession();
    }, [restoreSession]);

    const login = async (data: LoginRequest) => {
        const result = await api.login(data);
        localStorage.setItem('auth_token', result.access_token);
        localStorage.setItem('auth_user', JSON.stringify(result.user));
        setUser(result.user);
        // 切换账号时清空上一个用户的页面操作痕迹
        pageCtx?.clearAllStates();
    };

    const register = async (data: RegisterRequest) => {
        const result = await api.register(data);
        localStorage.setItem('auth_token', result.access_token);
        localStorage.setItem('auth_user', JSON.stringify(result.user));
        setUser(result.user);
        pageCtx?.clearAllStates();
    };

    const logout = () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        setUser(null);
        pageCtx?.clearAllStates();
        message.success('已退出登录');
    };

    const updateCompanyInfo = async (data: CompanyInfoUpdate) => {
        const updatedUser = await api.updateCompanyInfo(data);
        setUser(updatedUser);
        localStorage.setItem('auth_user', JSON.stringify(updatedUser));
    };

    const bindCompany = async (data: CompanyBindRequest) => {
        const updatedUser = await api.bindCompany(data);
        setUser(updatedUser);
        localStorage.setItem('auth_user', JSON.stringify(updatedUser));
    };

    const refreshUser = async () => {
        try {
            const userData = await api.getCurrentUser();
            setUser(userData);
            localStorage.setItem('auth_user', JSON.stringify(userData));
        } catch {
            // ignore
        }
    };

    const isSuperAdmin = user?.role === 'super_admin';
    const isAdmin = user?.role === 'admin';
    const isUser = user?.role === 'user';

    return (
        <AuthContext.Provider value={{
            user,
            loading,
            isSuperAdmin,
            isAdmin,
            isUser,
            login,
            register,
            logout,
            updateCompanyInfo,
            bindCompany,
            refreshUser,
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
