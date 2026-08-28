import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

/**
 * 页面外观（主题）上下文
 *
 * - 支持 浅色 / 深色 两种外观，默认浅色（与原有设计一致）
 * - 选择持久化到 localStorage（key: app_theme），刷新后保持
 * - 通过 <html data-theme="dark"> 驱动 App.css 中的深色 CSS 变量，
 *   同时为 antd ConfigProvider 提供对应主题配置
 */

export type ThemeMode = 'light' | 'dark';

const STORAGE_KEY = 'app_theme';
const THEME_COLORS: Record<ThemeMode, string> = {
    light: '#fafaf9',
    dark: '#141417',
};

interface ThemeContextValue {
    mode: ThemeMode;
    toggleTheme: () => void;
    setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
    mode: 'light',
    toggleTheme: () => {},
    setMode: () => {},
});

function getInitialMode(): ThemeMode {
    if (typeof window === 'undefined') return 'light';
    try {
        const saved = window.localStorage.getItem(STORAGE_KEY);
        return saved === 'dark' ? 'dark' : 'light';
    } catch {
        return 'light';
    }
}

function applyModeToDocument(mode: ThemeMode) {
    if (typeof document === 'undefined') return;
    document.documentElement.setAttribute('data-theme', mode);
    document.documentElement.style.colorScheme = mode;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', THEME_COLORS[mode]);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [mode, setModeState] = useState<ThemeMode>(getInitialMode);

    useEffect(() => {
        applyModeToDocument(mode);
        try {
            window.localStorage.setItem(STORAGE_KEY, mode);
        } catch {
            // 忽略隐私模式等场景下的存储异常
        }
    }, [mode]);

    const setMode = useCallback((next: ThemeMode) => setModeState(next), []);
    const toggleTheme = useCallback(
        () => setModeState((prev) => (prev === 'dark' ? 'light' : 'dark')),
        []
    );

    const value = useMemo(
        () => ({ mode, toggleTheme, setMode }),
        [mode, toggleTheme, setMode]
    );

    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
    return useContext(ThemeContext);
}
