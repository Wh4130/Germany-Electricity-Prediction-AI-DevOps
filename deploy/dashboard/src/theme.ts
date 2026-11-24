// Chart colors come from the CSS tokens (styles.css), so light and dark mode swap in one place.
import { useEffect, useState } from "react";

// a model keeps its color whatever else is shown (fixed slots, never by position)
// (slot 3, green, is left out: in dark mode it cannot be told from the pink of TabICL with green-blind vision;
//  slot 4, yellow, is left out: next to the orange of the tree model it is hard to tell apart.
//  The hybrid model has the cyan, slot 6.)
const MODEL_SLOT: Record<string, number> = { sarimax: 1, tree: 2, hybrid: 6, tabicl: 5, timesfm: 7, foundation: 5 };

// Width of the line of a model: the hybrid is drawn thicker than the models it is made of
export const lineWidth = (id: string): number => (id === "hybrid" ? 3 : 2);

export function modelSlot(id: string, index: number): number {
  return MODEL_SLOT[id] ?? Math.min(6 + index, 8); // any other model: the slots that are still free
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
