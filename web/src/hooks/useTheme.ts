import { useEffect } from 'react';
import { useAppStore, type Theme } from '../store/appStore';

const themeClasses: Record<Theme, string> = {
  dark: 'dark theme-dark',
  light: 'light theme-light',
  midnight: 'dark theme-midnight',
  corporate: 'dark theme-corporate',
  emerald: 'dark theme-emerald',
};

export function useTheme() {
  const { theme, setTheme } = useAppStore();

  useEffect(() => {
    const root = document.documentElement;
    // Remove all theme classes
    Object.values(themeClasses).forEach((cls) => {
      cls.split(' ').forEach((c) => root.classList.remove(c));
    });
    // Add current theme
    themeClasses[theme].split(' ').forEach((c) => root.classList.add(c));
  }, [theme]);

  return { theme, setTheme };
}
