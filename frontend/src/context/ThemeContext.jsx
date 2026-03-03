import { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

/* ═══════════════════════════════════════════════════════════
   Theme Definitions — each theme provides dark-mode surfaces
   ═══════════════════════════════════════════════════════════ */
export const themes = {
  sunset: {
    name: 'Safari',
    primary: '#c85a17',
    secondary: '#d97706',
    accent: '#ea580c',
    bg: '#0f0a07',
    bgSecondary: '#1a1410',
    surface1: '#1f170f',
    surface2: '#281e14',
    text: '#f5f5f5',
    gradient: 'from-amber-700 via-orange-600 to-amber-600',
    glow: 'shadow-orange-900/20',
  },
  ocean: {
    name: 'Ocean',
    primary: '#0EA5E9',
    secondary: '#06B6D4',
    accent: '#3B82F6',
    bg: '#020617',
    bgSecondary: '#0f172a',
    surface1: '#131d33',
    surface2: '#1a253d',
    text: '#FFFFFF',
    gradient: 'from-blue-600 via-cyan-500 to-teal-400',
    glow: 'shadow-blue-500/50',
  },
  forest: {
    name: 'Forest',
    primary: '#10B981',
    secondary: '#059669',
    accent: '#34D399',
    bg: '#0a1410',
    bgSecondary: '#14241a',
    surface1: '#182e22',
    surface2: '#1f3a2b',
    text: '#FFFFFF',
    gradient: 'from-green-600 via-emerald-500 to-teal-500',
    glow: 'shadow-green-500/50',
  },
  lavender: {
    name: 'Lavender',
    primary: '#A855F7',
    secondary: '#C084FC',
    accent: '#E879F9',
    bg: '#100a1e',
    bgSecondary: '#1a1230',
    surface1: '#201840',
    surface2: '#28204d',
    text: '#FFFFFF',
    gradient: 'from-purple-600 via-violet-500 to-fuchsia-500',
    glow: 'shadow-purple-500/50',
  },
  rose: {
    name: 'Rose Gold',
    primary: '#EC4899',
    secondary: '#F472B6',
    accent: '#F9A8D4',
    bg: '#140810',
    bgSecondary: '#221020',
    surface1: '#2d1628',
    surface2: '#381e32',
    text: '#FFFFFF',
    gradient: 'from-pink-600 via-rose-500 to-red-400',
    glow: 'shadow-pink-500/50',
  },
  midnight: {
    name: 'Midnight',
    primary: '#6366f1',
    secondary: '#818cf8',
    accent: '#a5b4fc',
    bg: '#0a0a0f',
    bgSecondary: '#14141f',
    surface1: '#1a1a28',
    surface2: '#222233',
    text: '#f5f5f5',
    gradient: 'from-indigo-700 via-indigo-600 to-purple-600',
    glow: 'shadow-indigo-900/20',
  },
};

export function ThemeProvider({ children }) {
  const [currentTheme, setCurrentTheme] = useState(() => {
    const saved = localStorage.getItem('wildtrack-theme');
    return saved || 'sunset';
  });

  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('wildtrack-dark-mode');
    return saved ? saved === 'true' : true;
  });

  useEffect(() => {
    localStorage.setItem('wildtrack-theme', currentTheme);
    localStorage.setItem('wildtrack-dark-mode', String(dark));

    const t = themes[currentTheme];
    const r = document.documentElement;

    /* ── Accent colours (always from theme) ── */
    r.style.setProperty('--color-primary', t.primary);
    r.style.setProperty('--color-secondary', t.secondary);
    r.style.setProperty('--color-accent', t.accent);
    r.style.setProperty('--theme-primary', t.primary);
    r.style.setProperty('--theme-secondary', t.secondary);
    r.style.setProperty('--theme-accent', t.accent);

    if (dark) {
      /* ── Dark mode surfaces ── */
      r.style.setProperty('--bg-primary', t.bg);
      r.style.setProperty('--bg-secondary', t.bgSecondary);
      r.style.setProperty('--bg-surface-1', t.surface1);
      r.style.setProperty('--bg-surface-2', t.surface2);
      r.style.setProperty('--bg-card', t.surface1);
      r.style.setProperty('--bg-hover', 'rgba(255,255,255,0.04)');
      r.style.setProperty('--text-primary', '#FFFFFF');
      r.style.setProperty('--text-secondary', '#9CA3AF');
      r.style.setProperty('--text-tertiary', '#6B7280');
      r.style.setProperty('--text-dim', '#4B5563');
      r.style.setProperty('--border-primary', 'rgba(255,255,255,0.08)');
      r.style.setProperty('--border-subtle', 'rgba(255,255,255,0.05)');
      r.style.setProperty('--shadow-card', '0 1px 3px rgba(0,0,0,0.4)');
      r.style.setProperty('--grid-color', 'rgba(255,255,255,0.04)');
      /* legacy aliases */
      r.style.setProperty('--theme-bg', t.bg);
      r.style.setProperty('--theme-bg-secondary', t.bgSecondary);
      r.style.setProperty('--theme-text', '#FFFFFF');
      r.style.setProperty('--theme-text-secondary', '#9CA3AF');
      r.style.setProperty('--theme-border', 'rgba(255,255,255,0.08)');
      r.style.setProperty('--theme-card-bg', t.surface1);
      r.classList.add('dark');
    } else {
      /* ── Light mode surfaces ── */
      r.style.setProperty('--bg-primary', '#f8f9fb');
      r.style.setProperty('--bg-secondary', '#ffffff');
      r.style.setProperty('--bg-surface-1', '#ffffff');
      r.style.setProperty('--bg-surface-2', '#f1f3f5');
      r.style.setProperty('--bg-card', '#ffffff');
      r.style.setProperty('--bg-hover', 'rgba(0,0,0,0.03)');
      r.style.setProperty('--text-primary', '#111827');
      r.style.setProperty('--text-secondary', '#6B7280');
      r.style.setProperty('--text-tertiary', '#9CA3AF');
      r.style.setProperty('--text-dim', '#D1D5DB');
      r.style.setProperty('--border-primary', 'rgba(0,0,0,0.08)');
      r.style.setProperty('--border-subtle', 'rgba(0,0,0,0.04)');
      r.style.setProperty('--shadow-card', '0 1px 3px rgba(0,0,0,0.06)');
      r.style.setProperty('--grid-color', 'rgba(0,0,0,0.05)');
      /* legacy aliases */
      r.style.setProperty('--theme-bg', '#f8f9fb');
      r.style.setProperty('--theme-bg-secondary', '#ffffff');
      r.style.setProperty('--theme-text', '#111827');
      r.style.setProperty('--theme-text-secondary', '#6B7280');
      r.style.setProperty('--theme-border', 'rgba(0,0,0,0.08)');
      r.style.setProperty('--theme-card-bg', '#ffffff');
      r.classList.remove('dark');
    }
  }, [currentTheme, dark]);

  const changeTheme = (themeName) => setCurrentTheme(themeName);
  const toggleDarkMode = () => setDark(prev => !prev);

  return (
    <ThemeContext.Provider value={{
      dark,
      toggle: toggleDarkMode,
      currentTheme,
      theme: themes[currentTheme],
      changeTheme,
      themes
    }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
