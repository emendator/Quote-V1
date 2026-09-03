import type { ReactNode } from 'react';
import { Button } from 'antd';
import { SunOutlined, MoonOutlined } from '@ant-design/icons';
import InteractiveBackground from './InteractiveBackground';
import { useTheme } from '../store/ThemeContext';

interface HeroPoint {
    num: string;
    title: string;
    desc: string;
}

const DEFAULT_POINTS: HeroPoint[] = [
    {
        num: '01',
        title: '智能查询',
        desc: '像聊天一样找到商品：自然语言、价格区间、批量快查，随问随答。',
    },
    {
        num: '02',
        title: '智能方案',
        desc: '告诉系统预算与需求，自动组合出最贴近目标的最优报价方案。',
    },
    {
        num: '03',
        title: '数据管理',
        desc: 'Excel 一键导入、集中管理，报价数据从此井井有条。',
    },
];

interface AuthShellProps {
    children: ReactNode;
    points?: HeroPoint[];
}

/** 编辑部式分栏外壳：左侧交互式品牌叙事，右侧表单面板 */
export default function AuthShell({ children, points = DEFAULT_POINTS }: AuthShellProps) {
    const { mode, toggleTheme } = useTheme();
    return (
        <div className="auth-page">
            <Button
                type="text"
                className="dd-theme-toggle dd-theme-toggle-fixed"
                aria-label={mode === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
                title={mode === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
                icon={mode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
                onClick={toggleTheme}
            />
            <div className="auth-hero">
                <InteractiveBackground className="dd-interactive-bg" />
                <div className="auth-aurora" />
                <div className="auth-hero-grid" />
                <div className="auth-sweep" />
                <div className="auth-hero-inner">
                    <span className="eyebrow dd-fade-up">Smart Quotation Studio</span>
                    <h1 className="auth-hero-title">
                        让每一次报价，
                        <br />
                        都恰到好处。
                    </h1>
                    <p className="auth-hero-sub dd-fade-up" style={{ animationDelay: '0.16s' }}>
                        商品管理 · 智能查询 · 组合方案 —— 一个内敛而高效的报价工作台。
                        少一些操作，多一些从容。
                    </p>
                    <div className="auth-hero-points dd-stagger">
                        {points.map((p) => (
                            <div key={p.num} className="auth-hero-point" data-tilt>
                                <span className="auth-hero-point-num">{p.num}</span>
                                <div>
                                    <div className="auth-hero-point-title">{p.title}</div>
                                    <div className="auth-hero-point-desc">{p.desc}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* 左侧底部：编辑部式收尾（细线 + 微文案 + 页码），打破纯色底部的单调 */}
                <div className="auth-hero-foot" aria-hidden="true">
                    <div className="auth-hero-foot-rule" />
                    <div className="auth-hero-foot-row">
                        <span className="auth-hero-foot-caption">让报价，成为一门手艺</span>
                        <span className="auth-hero-foot-page">01 / 03</span>
                    </div>
                </div>
            </div>
            <div className="auth-panel">
                {/* 右侧最内层纯色背景：加上缓缓流动的渐变网格 + 纸面颗粒，告别单调（detail.design） */}
                <div className="auth-panel-bg" aria-hidden="true" />
                {children}

                {/* 右侧底部：编辑部式收尾（细线 + 微文案 + 页码），同样打破纯色底部 */}
                <div className="auth-panel-foot" aria-hidden="true">
                    <div className="auth-panel-foot-rule" />
                    <div className="auth-panel-foot-row">
                        <span className="auth-panel-foot-caption">安全 · 内敛 · 高效</span>
                        <span className="auth-panel-foot-page">02 / 03</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
