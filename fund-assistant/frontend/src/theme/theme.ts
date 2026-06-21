import type { ThemeConfig } from 'antd';

// 🌙 深色主题 — 科技深蓝
export const darkTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1677ff',
    colorBgBase: '#0a1628',
    colorBgContainer: '#0f1f3d',
    colorBgElevated: '#162d50',
    colorBgLayout: '#070f1e',
    colorTextBase: '#e8edf5',
    colorTextSecondary: '#8ca3c4',
    colorBorder: '#1e3a5f',
    colorBorderSecondary: '#1a3255',
    borderRadius: 8,
    fontSize: 14,
  },
  components: {
    Layout: {
      headerBg: '#0a1628',
      bodyBg: '#070f1e',
      siderBg: '#0f1f3d',
    },
    Menu: {
      darkItemBg: '#0f1f3d',
      darkItemSelectedBg: '#1677ff22',
      darkItemSelectedColor: '#1677ff',
    },
    Card: {
      colorBgContainer: '#0f1f3d',
    },
    Table: {
      headerBg: '#0a1628',
      headerColor: '#8ca3c4',
      rowHoverBg: '#162d50',
    },
    Statistic: {
      contentFontSize: 28,
    },
  },
};

// ☀️ 浅色主题 — 简约大气
export const lightTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1677ff',
    colorBgBase: '#ffffff',
    colorBgContainer: '#ffffff',
    colorBgElevated: '#fafafa',
    colorBgLayout: '#f5f7fa',
    colorTextBase: '#1a2233',
    colorTextSecondary: '#5a6a7e',
    colorBorder: '#e8ecf1',
    colorBorderSecondary: '#f0f2f5',
    borderRadius: 8,
    fontSize: 14,
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      bodyBg: '#f5f7fa',
      siderBg: '#ffffff',
    },
    Menu: {
      itemBg: '#ffffff',
      itemSelectedBg: '#e6f4ff',
      itemSelectedColor: '#1677ff',
    },
    Card: {
      colorBgContainer: '#ffffff',
    },
    Table: {
      headerBg: '#fafafa',
      headerColor: '#5a6a7e',
      rowHoverBg: '#f5f7fa',
    },
  },
};
