import React, { createContext, useContext, useRef, useCallback, useState } from 'react';

/**
 * 页面状态保持上下文
 * 当用户切换页面时，保存各页面的状态，切回时自动恢复
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PageState = Record<string, any>;

interface PageStateContextValue {
    /** 获取某个页面的状态，如不存在返回默认值 */
    getState: <T>(pageKey: string, defaults: T) => T;
    /** 保存某个页面的状态 */
    setState: (pageKey: string, state: PageState) => void;
}

const PageStateContext = createContext<PageStateContextValue | null>(null);

export function PageStateProvider({ children }: { children: React.ReactNode }) {
    // 使用 ref 存储所有页面状态，页面切走再回来时恢复
    const statesRef = useRef<Record<string, PageState>>({});

    const getState = useCallback(<T,>(pageKey: string, defaults: T): T => {
        return (statesRef.current[pageKey] ?? defaults) as T;
    }, []);

    const setState = useCallback((pageKey: string, state: PageState) => {
        statesRef.current[pageKey] = state;
    }, []);

    return (
        <PageStateContext.Provider value={{ getState, setState }}>
            {children}
        </PageStateContext.Provider>
    );
}

export function usePageState<T>(pageKey: string, defaults: T): [T, (state: T) => void] {
    const ctx = useContext(PageStateContext);
    if (!ctx) {
        throw new Error('usePageState must be used within PageStateProvider');
    }

    // 用 useState 存储实际值，保证更新后触发重渲染
    const [state, setState] = useState<T>(() => ctx.getState(pageKey, defaults));

    const saveState = useCallback(
        (newState: T) => {
            // 同时更新 ref（跨页面持久）和本地 state（触发重渲染）
            ctx.setState(pageKey, newState as unknown as PageState);
            setState(newState);
        },
        [ctx, pageKey],
    );

    return [state, saveState];
}
