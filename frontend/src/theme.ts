import { theme as antdTheme, type ThemeConfig } from 'antd';

/**
 * 智能报价 · 设计主题
 *
 * 设计语言参考 detail.design（编辑部式极简主义）：
 * - 近白纸感画布 + 发丝级描边，克制的阴影
 * - 墨色（ink）作为主操作色，靛蓝作为链接/信息色
 * - 琥珀色作为强调色（AI / 推荐 / 徽标），仅少量点缀
 * - 圆角 8–16px，中文正文 + 英文数字衬线展示
 *
 * 支持 浅色（light，默认）/ 深色（dark）两种外观，
 * 由 src/store/ThemeContext.tsx 统一切换并持久化到 localStorage。
 */

const SHARED_TOKENS = {
    // —— 圆角 ——
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    borderRadiusXS: 4,

    // —— 字体 ——
    fontFamily:
        "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans SC', sans-serif",
    fontSize: 14,

    // —— 尺寸 ——
    controlHeight: 36,
    controlHeightLG: 44,

    // —— 动效（物理弹簧缓动）——
    motionDurationFast: '0.12s',
    motionDurationMid: '0.2s',
    motionDurationSlow: '0.32s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    motionEaseOut: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    motionEaseInBack: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    motionEaseOutBack: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
} as const;

const SHARED_COMPONENTS = {
    Card: {
        headerBg: 'transparent',
        headerFontSize: 15,
        bodyPadding: 20,
    },
    Tag: {
        borderRadiusSM: 4,
    },
    Alert: {
        borderRadiusLG: 10,
    },
    Tooltip: {
        borderRadius: 8,
    },
    Dropdown: {
        borderRadiusLG: 12,
    },
    Popover: {
        borderRadiusLG: 12,
    },
    Steps: {
        iconSize: 30,
    },
    Result: {
        titleFontSize: 20,
    },
    Statistic: {
        titleFontSize: 13,
    },
    List: {
        headerBg: 'transparent',
    },
} as const;

/**
 * 浅色主题（默认，编辑部式近白画布）
 */
export const lightTheme: ThemeConfig = {
    token: {
        ...SHARED_TOKENS,

        // —— 色彩 ——
        colorPrimary: '#1f1f24',
        colorInfo: '#4f46e5',
        colorLink: '#4f46e5',
        colorSuccess: '#16a34a',
        colorWarning: '#d97706',
        colorError: '#dc2626',
        colorTextBase: '#18181b',
        colorBgLayout: '#fafaf9',
        colorBgContainer: '#ffffff',
        colorBgElevated: '#ffffff',
        colorBorder: '#e7e5e4',
        colorBorderSecondary: '#efefec',
        colorText: '#18181b',
        colorTextSecondary: '#6b6b72',
        colorTextTertiary: '#a1a1aa',
        colorTextQuaternary: '#d4d4d8',
        colorFillSecondary: '#f4f4f2',
        colorSplit: '#efefec',

        // —— 阴影：柔和、克制 ——
        boxShadow: '0 1px 2px rgba(24,24,27,0.04), 0 4px 16px rgba(24,24,27,0.05)',
        boxShadowSecondary: '0 8px 40px rgba(24,24,27,0.10)',
    },
    components: {
        ...SHARED_COMPONENTS,
        Layout: {
            headerBg: '#ffffff',
            siderBg: '#ffffff',
            bodyBg: '#fafaf9',
            headerHeight: 64,
            headerPadding: '0 28px',
        },
        Menu: {
            itemBg: 'transparent',
            itemHeight: 42,
            itemMarginBlock: 4,
            itemBorderRadius: 8,
            itemColor: '#55555c',
            itemHoverColor: '#18181b',
            itemHoverBg: '#f7f7f5',
            itemSelectedColor: '#1f1f24',
            itemSelectedBg: '#f1f1ee',
            activeBarBorderWidth: 0,
            iconSize: 16,
            subMenuItemBg: 'transparent',
        },
        Table: {
            headerBg: '#f6f6f4',
            headerColor: '#52525b',
            headerSplitColor: 'transparent',
            rowHoverBg: '#f7f7f5',
            borderColor: '#efefec',
            cellPaddingBlock: 12,
            cellPaddingBlockSM: 8,
            cellPaddingInline: 12,
        },
        Button: {
            fontWeight: 500,
            primaryShadow: '0 1px 2px rgba(24,24,27,0.12), 0 2px 8px rgba(24,24,27,0.08)',
            defaultShadow: '0 1px 1px rgba(24,24,27,0.04)',
            contentFontSizeLG: 15,
        },
        Modal: {
            borderRadiusLG: 16,
            titleFontSize: 16,
            headerBg: '#ffffff',
            contentBg: '#ffffff',
        },
        Input: {
            activeShadow: '0 0 0 3px rgba(79,70,229,0.10)',
            hoverBorderColor: '#c9c9c6',
            activeBorderColor: '#1f1f24',
            paddingInline: 12,
        },
        Select: {
            optionSelectedBg: '#f1f1ee',
            optionSelectedColor: '#1f1f24',
        },
        Pagination: {
            itemActiveBg: '#1f1f24',
        },
        Switch: {
            colorPrimary: '#1f1f24',
            colorPrimaryHover: '#3a3a41',
        },
        Segmented: {
            itemSelectedBg: '#ffffff',
            trackBg: '#f1f1ee',
        },
        Badge: {
            colorError: '#dc2626',
        },
        Tabs: {
            inkBarColor: '#1f1f24',
            itemSelectedColor: '#18181b',
            itemHoverColor: '#1f1f24',
        },
        Radio: {
            buttonSolidCheckedBg: '#1f1f24',
            buttonSolidCheckedActiveBg: '#1f1f24',
            buttonSolidCheckedHoverBg: '#3a3a41',
        },
        Checkbox: {
            colorPrimary: '#1f1f24',
        },
        DatePicker: {
            activeShadow: '0 0 0 3px rgba(79,70,229,0.10)',
        },
        InputNumber: {
            activeShadow: '0 0 0 3px rgba(79,70,229,0.10)',
            hoverBorderColor: '#c9c9c6',
            activeBorderColor: '#1f1f24',
        },
        Form: {
            labelColor: '#52525b',
            verticalLabelPadding: '0 0 6px',
        },
        Upload: {
            colorPrimary: '#1f1f24',
        },
        Progress: {
            defaultColor: '#1f1f24',
        },
    },
};

/**
 * 深色主题（深墨画布，低亮度、高对比文字）
 */
export const darkTheme: ThemeConfig = {
    algorithm: antdTheme.darkAlgorithm,
    token: {
        ...SHARED_TOKENS,

        // —— 色彩 ——
        colorPrimary: '#d6d6de',
        colorInfo: '#818cf8',
        colorLink: '#818cf8',
        colorSuccess: '#4ade80',
        colorWarning: '#fbbf24',
        colorError: '#f87171',
        colorTextBase: '#ececf1',
        colorBgBase: '#141417',
        colorBgLayout: '#141417',
        colorBgContainer: '#1c1c21',
        colorBgElevated: '#24242b',
        colorBorder: '#2e2e36',
        colorBorderSecondary: '#28282f',
        colorText: '#ececf1',
        colorTextSecondary: '#a1a1aa',
        colorTextTertiary: '#7d7d87',
        colorTextQuaternary: '#56565f',
        colorFillSecondary: '#26262d',
        colorSplit: '#2c2c33',
        // 主操作色（浅墨）上的文字 → 深色，保证对比
        colorTextLightSolid: '#18181b',

        // —— 阴影：深色下更重、更收 ——
        boxShadow: '0 1px 2px rgba(0,0,0,0.35), 0 4px 16px rgba(0,0,0,0.30)',
        boxShadowSecondary: '0 8px 40px rgba(0,0,0,0.45)',
    },
    components: {
        ...SHARED_COMPONENTS,
        Layout: {
            headerBg: '#1c1c21',
            siderBg: '#1c1c21',
            bodyBg: '#141417',
            headerHeight: 64,
            headerPadding: '0 28px',
        },
        Menu: {
            itemBg: 'transparent',
            itemHeight: 42,
            itemMarginBlock: 4,
            itemBorderRadius: 8,
            itemColor: '#a1a1aa',
            itemHoverColor: '#ececf1',
            itemHoverBg: '#26262d',
            itemSelectedColor: '#ececf1',
            itemSelectedBg: '#30303a',
            activeBarBorderWidth: 0,
            iconSize: 16,
            subMenuItemBg: 'transparent',
        },
        Table: {
            headerBg: '#232329',
            headerColor: '#a1a1aa',
            headerSplitColor: 'transparent',
            rowHoverBg: '#26262d',
            borderColor: '#2c2c33',
            cellPaddingBlock: 12,
            cellPaddingBlockSM: 8,
            cellPaddingInline: 12,
        },
        Button: {
            fontWeight: 500,
            primaryShadow: '0 1px 2px rgba(0,0,0,0.40), 0 2px 8px rgba(0,0,0,0.30)',
            defaultShadow: '0 1px 1px rgba(0,0,0,0.25)',
            contentFontSizeLG: 15,
        },
        Modal: {
            borderRadiusLG: 16,
            titleFontSize: 16,
            headerBg: '#24242b',
            contentBg: '#24242b',
        },
        Input: {
            activeShadow: '0 0 0 3px rgba(129,140,248,0.18)',
            hoverBorderColor: '#4a4a54',
            activeBorderColor: '#d6d6de',
            paddingInline: 12,
        },
        Select: {
            optionSelectedBg: '#30303a',
            optionSelectedColor: '#ececf1',
        },
        Pagination: {
            itemActiveBg: '#d6d6de',
        },
        Switch: {
            colorPrimary: '#d6d6de',
            colorPrimaryHover: '#e4e4ea',
        },
        Segmented: {
            itemSelectedBg: '#30303a',
            trackBg: '#26262d',
        },
        Badge: {
            colorError: '#f87171',
        },
        Tabs: {
            inkBarColor: '#ececf1',
            itemSelectedColor: '#ececf1',
            itemHoverColor: '#d6d6de',
        },
        Radio: {
            buttonSolidCheckedBg: '#d6d6de',
            buttonSolidCheckedActiveBg: '#d6d6de',
            buttonSolidCheckedHoverBg: '#e4e4ea',
        },
        Checkbox: {
            colorPrimary: '#d6d6de',
        },
        DatePicker: {
            activeShadow: '0 0 0 3px rgba(129,140,248,0.18)',
        },
        InputNumber: {
            activeShadow: '0 0 0 3px rgba(129,140,248,0.18)',
            hoverBorderColor: '#4a4a54',
            activeBorderColor: '#d6d6de',
        },
        Form: {
            labelColor: '#a1a1aa',
            verticalLabelPadding: '0 0 6px',
        },
        Upload: {
            colorPrimary: '#d6d6de',
        },
        Progress: {
            defaultColor: '#d6d6de',
        },
    },
};

export default lightTheme;
