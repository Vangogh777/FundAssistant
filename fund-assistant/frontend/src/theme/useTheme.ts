import { useState, useCallback, useEffect } from 'react';
import type { ThemeConfig } from 'antd';
import { darkTheme, lightTheme } from './theme';

type ThemeMode = 'light' | 'dark';

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('fund-theme');
    return (saved as ThemeMode) || 'dark';
  });

  useEffect(() => {
    localStorage.setItem('fund-theme', mode);
    document.documentElement.setAttribute('data-theme', mode);
  }, [mode]);

  const toggleTheme = useCallback(() => {
    setMode(prev => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const theme: ThemeConfig = mode === 'dark' ? darkTheme : lightTheme;

  return { mode, theme, toggleTheme };
}
