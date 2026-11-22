import { useEffect, useState } from "react";
import Plotly from "plotly.js-basic-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import type { Data, Layout, PlotMouseEvent, PlotRelayoutEvent } from "plotly.js";
import type { ForecastRow, ModelConfig, Prediction } from "./api";
import { type Theme, lineWidth, withAlpha } from "./theme";

const Plot = createPlotlyComponent(Plotly);
const GWH = (mwh: number) => mwh / 1000;
const DAY_MS = 86_400_000;

// Plotly gives dates as "2024-03-01" or "2024-03-01 12:34:56.789", without a time zone; read them all as UTC
const toMs = (date: string) =>
  Date.parse(date.length <= 10 ? `${date}T00:00:00Z` : `${date.replace(" ", "T").slice(0, 23)}Z`);
const fromMs = (ms: number) => new Date(ms).toISOString().replace("T", " ").slice(0, 19);

// zoom presets around the selected day (days shown)
const WINDOWS = [
  { label: "2w", days: 14 },
  { label: "1m", days: 31 },
  { label: "3m", days: 92 },
  { label: "All", days: 0 },
];

type Range = [number, number]; // ms, UTC

export interface ChartModel extends ModelConfig {
  color: string;
}

interface Props {
  models: ChartModel[]; // the visible models
  showIntervals: boolean; // the 80% intervals (App: only when one model is visible)
  actual?: ForecastRow[]; // the rows whose y_true is the actual load
  forecasts: Record<string, ForecastRow[]>;
  predictions: Record<string, Prediction | undefined>;
  selectedDate: string | null;
  theme: Theme;
  onSelectDate: (date: string) => void;
}

export function Chart({
  models, showIntervals, actual, forecasts, predictions, selectedDate, theme, onSelectDate,
}: Props) {
  // the x range the user zoomed to (null: the whole year); kept across re-renders, so changing an X on the left
  // does not reset the zoom
  const [xRange, setXRange] = useState<Range | null>(null);
  // "load": the load in GWh; "error": forecast − actual, which pulls the models apart when their lines overlap
  const [view, setView] = useState<"load" | "error">("load");
  const err = view === "error";
  const val = (mwh: number, actual: number) => GWH(err ? mwh - actual : mwh);
  const hover = err ? "%{y:+,.1f} GWh" : "%{y:,.1f} GWh";

  // a day picked outside the zoomed window: move the window to it (same width)
  useEffect(() => {
    if (!selectedDate || !xRange) return;
    const day = toMs(selectedDate);
    if (day >= xRange[0] && day <= xRange[1]) return;
    const half = (xRange[1] - xRange[0]) / 2;
    setXRange([day - half, day + half]);
  }, [selectedDate]); // only when the day changes, not when the user zooms

  const zoomTo = (days: number) => {
    if (!days) return setXRange(null);
    const center = selectedDate ? toMs(selectedDate) : xRange ? (xRange[0] + xRange[1]) / 2 : Date.now();
    setXRange([center - (days / 2) * DAY_MS, center + (days / 2) * DAY_MS]);
  };

  const traces: Data[] = [];
  const whiskers: [string, number][] = []; // ends of the what-if intervals, for the y range

  // 80% intervals first, so the lines are drawn on top
  if (showIntervals) {
    for (const model of models) {
      const rows = forecasts[model.id] ?? [];
      if (!rows.length || rows[0]["q0.1"] === undefined) continue;
      const dates = rows.map((r) => r.date);
      traces.push(
        { x: dates, y: rows.map((r) => val(r["q0.9"]!, r.y_true)), type: "scatter", mode: "lines",
          line: { width: 0 }, hoverinfo: "skip", showlegend: false, legendgroup: model.id },
        { x: dates, y: rows.map((r) => val(r["q0.1"]!, r.y_true)), type: "scatter", mode: "lines",
          line: { width: 0 }, fill: "tonexty", fillcolor: withAlpha(model.color, 0.14),
          hoverinfo: "skip", showlegend: false, legendgroup: model.id },
      );
    }
  }

  // actual load: always shown (also when every model is hidden), except in the error view, where it is the zero line
  if (actual?.length && !err) {
    traces.push({
      x: actual.map((r) => r.date), y: actual.map((r) => GWH(r.y_true)),
      type: "scatter", mode: "lines", name: "Actual",
      line: { color: theme.ink, width: 2 },
      hovertemplate: "%{y:,.1f} GWh<extra>Actual</extra>",
    });
  }

  for (const model of models) {
    const rows = forecasts[model.id] ?? [];
    traces.push({
      x: rows.map((r) => r.date), y: rows.map((r) => val(r.y_pred, r.y_true)),
      type: "scatter", mode: "lines", name: model.label, legendgroup: model.id,
      line: { color: model.color, width: lineWidth(model.id) },
      hovertemplate: `${hover}<extra>${model.label}</extra>`,
    });
  }

  // what-if forecasts of the selected day, with their 80% interval
  for (const model of models) {
    const p = predictions[model.id];
    if (!p) continue;
    const hasInterval = showIntervals && p["q0.1"] !== undefined && p["q0.9"] !== undefined;
    if (hasInterval) whiskers.push([p.date, val(p["q0.1"]!, p.y_true)], [p.date, val(p["q0.9"]!, p.y_true)]);
    traces.push({
      x: [p.date], y: [val(p.y_pred, p.y_true)],
      type: "scatter", mode: "markers", name: `${model.label} what-if`, legendgroup: model.id,
      marker: { symbol: "diamond", size: 13, color: model.color, line: { color: theme.surface, width: 2 } },
      error_y: hasInterval
        ? { type: "data", symmetric: false, array: [GWH(p["q0.9"]! - p.y_pred)],
            arrayminus: [GWH(p.y_pred - p["q0.1"]!)], color: model.color, thickness: 2, width: 6 }
        : undefined,
      hovertemplate: `${hover}<extra>${model.label} what-if</extra>`,
    });
  }

  // y range: fitted to what is inside the zoomed window (Plotly's autorange uses the whole year)
  let yRange: [number, number] | undefined;
  if (xRange) {
    let low = Infinity;
    let high = -Infinity;
    const visit = (date: string, y: number) => {
      const t = toMs(date);
      if (t < xRange[0] || t > xRange[1] || !Number.isFinite(y)) return;
      low = Math.min(low, y);
      high = Math.max(high, y);
    };
    for (const trace of traces as { x?: string[]; y?: number[] }[]) {
      trace.x?.forEach((date, i) => visit(date, trace.y![i]));
    }
    whiskers.forEach(([date, y]) => visit(date, y));
    if (low <= high) {
      const pad = Math.max((high - low) * 0.08, 5);
      yRange = [low - pad, high + pad];
    }
  }

  const handleRelayout = (event: Readonly<PlotRelayoutEvent>) => {
    const e = event as Record<string, unknown>;
    if (e["xaxis.autorange"]) return setXRange(null);
    const range = (e["xaxis.range"] as string[] | undefined) ??
      (e["xaxis.range[0]"] !== undefined ? [e["xaxis.range[0]"], e["xaxis.range[1]"]] as string[] : undefined);
    if (range) setXRange([toMs(String(range[0])), toMs(String(range[1]))]);
  };

  const layout: Partial<Layout> = {
    autosize: true,
    height: 560,
    margin: { l: 64, r: 16, t: 8, b: 24 },
    // a new revision whenever the app sets the range, so Plotly applies it instead of keeping its own zoom
    uirevision: xRange ? xRange.join() : "all",
    dragmode: "zoom",
    paper_bgcolor: theme.surface,
    plot_bgcolor: theme.surface,
    font: { family: 'system-ui, -apple-system, "Segoe UI", sans-serif', color: theme.inkSecondary, size: 12 },
    hovermode: "x unified",
    hoverlabel: { bgcolor: theme.surface, bordercolor: theme.axis, font: { color: theme.ink } },
    showlegend: false, // the legend is the model toggles above the chart (App.tsx)
    xaxis: {
      showgrid: false, linecolor: theme.axis, tickcolor: theme.axis,
      ...(xRange ? { range: [fromMs(xRange[0]), fromMs(xRange[1])], autorange: false } : { autorange: true }),
      // month names for the whole year, days when zoomed in
      tickformatstops: [
        { dtickrange: [null, 7 * DAY_MS], value: "%d %b" },
        { dtickrange: [7 * DAY_MS, null], value: "%b" },
      ],
      hoverformat: "%a %d %b %Y", showspikes: true, spikecolor: theme.muted, spikethickness: 1,
      spikedash: "solid", spikemode: "across",
      rangeslider: { visible: true, thickness: 0.08, bgcolor: theme.surface, bordercolor: theme.axis,
                     borderwidth: 1 },
    },
    yaxis: {
      title: { text: err ? "Forecast − actual (GWh / day)" : "Load (GWh / day)" },
      gridcolor: theme.grid, zeroline: err, zerolinecolor: theme.ink, zerolinewidth: 2,
      tickformat: err ? "+,.0f" : ",.0f", linecolor: theme.axis,
      fixedrange: true, // zoom only along time; the y range follows the window
      ...(yRange ? { range: yRange, autorange: false } : { autorange: true }),
    },
    shapes: selectedDate
      ? [{ type: "line", xref: "x", yref: "paper", x0: selectedDate, x1: selectedDate, y0: 0, y1: 1,
           line: { color: theme.muted, width: 1, dash: "dot" } }]
      : [],
  };

  const handleClick = (event: PlotMouseEvent) => {
    const x = event.points[0]?.x;
    if (x !== undefined && x !== null) onSelectDate(String(x).slice(0, 10));
  };

  const windowDays = xRange ? Math.round((xRange[1] - xRange[0]) / DAY_MS) : 0;

  return (
    <>
      <div className="zoom" role="group" aria-label="View and zoom">
        {(["load", "error"] as const).map((v) => (
          <button key={v} className={view === v ? "active" : ""} aria-pressed={view === v} onClick={() => setView(v)}>
            {v === "load" ? "Load" : "Error"}
          </button>
        ))}
        <span className="hint" style={{ marginRight: 10 }}>
          {err ? "forecast − actual" : "the load in GWh"}
        </span>
        {WINDOWS.map((w) => (
          <button
            key={w.label}
            className={windowDays === w.days ? "active" : ""}
            aria-pressed={windowDays === w.days}
            onClick={() => zoomTo(w.days)}
          >
            {w.label}
          </button>
        ))}
        <span className="hint">around the selected day · drag in the chart to zoom, double-click for the year</span>
      </div>
      <Plot
        data={traces}
        layout={layout}
        config={{
          displaylogo: false, responsive: true, doubleClick: "autosize",
          modeBarButtonsToRemove: ["lasso2d", "select2d", "zoomIn2d", "zoomOut2d", "autoScale2d"],
        }}
        useResizeHandler
        style={{ width: "100%" }}
        onClick={handleClick}
        onRelayout={handleRelayout}
      />
    </>
  );
}
