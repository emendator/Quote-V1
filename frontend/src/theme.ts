import type { ThemeConfig } from 'antd';

/**
 * 智能报价 · 设计主题
 *
 * 设计语言参考 detail.design（编辑部式极简主义）：
 * - 近白纸感画布 + 发丝级描边，克制的阴影
 * - 墨色（ink）作为主操作色，靛蓝作为链接/信息色
 * - 琥珀色作为强调色（AI / 推荐 / 徽标），仅少量点缀
 * - 圆角 8–16px，中文正文 + 英文数字衬线展示
 */
const theme: ThemeConfig = {
    token: {
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

        // —— 阴影：柔和、克制 ——
        boxShadow: '0 1px 2px rgba(24,24,27,0.04), 0 4px 16px rgba(24,24,27,0.05)',
        boxShadowSecondary: '0 8px 40px rgba(24,24,27,0.10)',
    },
    components: {
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
        Card: {
            headerBg: 'transparent',
            headerFontSize: 15,
            bodyPadding: 20,
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
        Tag: {
            borderRadiusSM: 4,
        },
        Alert: {
            borderRadiusLG: 10,
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
        List: {
            headerBg: 'transparent',
        },
        Upload: {
            colorPrimary: '#1f1f24',
        },
        Result: {
            titleFontSize: 20,
        },
        Statistic: {
            titleFontSize: 13,
        },
        Progress: {
            defaultColor: '#1f1f24',
        },
    },
};

export default theme;
