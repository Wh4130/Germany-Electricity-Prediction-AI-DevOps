// Chart colors come from the CSS tokens (styles.css), so light and dark mode swap in one place.
import { useEffect, useState } from "react";

// a model keeps its color whatever else is shown (fixed slots, never by position)
const MODEL_SLOT: Record<string, number> = { sarimax: 1, tree: 2, hybrid: 3, foundation: 4 };

export function modelSlot(id: string, index: number): number {
  return MODEL_SLOT[id] ?? Math.min(4 + index, 8);
}

export interface Theme {
  surface: string;
  ink: string;
  inkSecondary: string;
  muted: string;
  grid: string;
  axis: string;
  series: (slot: number) => string;
}

function readTheme(): Theme {
  const style = getComputedStyle(document.documentElement);
  const get = (name: string) => style.getPropertyValue(name).trim();
  return {
    surface: get("--surface-1"),
    ink: get("--text-primary"),
    inkSecondary: get("--text-secondary"),
    muted: get("--text-muted"),
    grid: get("--grid"),
    axis: get("--axis"),
    series: (slot) => get(`--series-${slot}`),
  };
}

export function useTheme(): Theme {
  const [theme, setTheme] = useState(readTheme);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setTheme(readTheme());
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return theme;
}

export function withAlpha(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
