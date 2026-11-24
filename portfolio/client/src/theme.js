import { useCallback, useState } from 'react';

// The initial theme is set by an inline script in index.html (saved choice,
// otherwise the system preference), so we only read it here.
export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || 'light');

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try {
        localStorage.setItem('theme', next);
      } catch {
        /* storage can be blocked; the theme still changes for this visit */
      }
      return next;
    });
  }, []);

  return [theme, toggle];
}

export function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
