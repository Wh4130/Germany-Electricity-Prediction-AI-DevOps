import { useEffect, useMemo, useRef, useState } from "react";
import {
  type AppConfig, type Features, type ForecastRow, type Prediction,
  getFeatures, getForecast, isLive, loadConfig, predict,
} from "./api";
import { Chart, type ChartModel } from "./Chart";
import { Sidebar } from "./Sidebar";
import { modelSlot, useTheme } from "./theme";

const DEBOUNCE_MS = 150;
const gwh = (mwh: number) =>
  `${(mwh / 1000).toLocaleString("en-US", { maximumFractionDigits: 1, minimumFractionDigits: 1 })} GWh`;
const signed = (mwh: number) => `${mwh >= 0 ? "+" : "−"}${gwh(Math.abs(mwh))}`;
// forecast − actual, as in the shared evaluation (positive = overestimate)
const errorText = (forecast: number, actual: number) =>
  `${signed(forecast - actual)} (${forecast >= actual ? "+" : "−"}${(Math.abs(forecast - actual) / actual * 100).toFixed(1)}%)`;

export function App() {
  const theme = useTheme();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [forecasts, setForecasts] = useState<Record<string, ForecastRow[]>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [date, setDate] = useState<string | null>(null);
  const [features, setFeatures] = useState<Features | null>(null);
  const [x, setX] = useState<Record<string, number>>({});
  const [predictions, setPredictions] = useState<Record<string, Prediction | undefined>>({});
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const requestId = useRef(0);

  const setError = (key: string, message?: string) =>
    setErrors((e) => {
      const next = { ...e };
      if (message) next[key] = message;
      else delete next[key];
      return next;
    });

  // config, then the 2024 forecasts of every model
  useEffect(() => {
    loadConfig()
      .then((c) => {
        setConfig(c);
        for (const model of c.models) {
          getForecast(model)
            .then((rows) => {
              setForecasts((f) => ({ ...f, [model.id]: rows }));
              if (model.id === c.featureSource && rows.length) setDate((d) => d ?? rows[0].date);
            })
            .catch((e) => setError(model.id, `${model.label}: ${e.message}`));
        }
      })
      .catch((e) => setError("config", `config.json: ${e.message}`));
  }, []);

  const models: ChartModel[] = useMemo(
    () => (config?.models ?? []).map((m, i) => ({ ...m, color: theme.series(modelSlot(m.id, i)) })),
    [config, theme],
  );
  const visible = models.filter((m) => !hidden.has(m.id));
  // the 80% interval only when one model is visible (several intervals on top of each other are unreadable)
  const showIntervals = visible.length === 1;
  const source = config?.models.find((m) => m.id === config.featureSource);
  const liveSource = source && isLive(source) ? source : undefined;

  // the X of the selected day
  useEffect(() => {
    if (!liveSource || !date) return;
    getFeatures(liveSource, date)
      .then((f) => {
        setFeatures(f);
        setX(Object.fromEntries(Object.entries(f.sliders).map(([k, s]) => [k, s.value])));
        setError("features");
      })
      .catch((e) => setError("features", e.message));
  }, [liveSource, date]); // liveSource is the object of `config`, so it only changes with the config

  // what-if forecasts of the live models (only the changed X are sent; the others keep the actual value)
  useEffect(() => {
    if (!config || !features) return;
    const id = ++requestId.current;
    const changed = Object.fromEntries(
      Object.entries(x).filter(([k, v]) => features.sliders[k] && v !== features.sliders[k].value),
    );
    const timer = setTimeout(() => {
      for (const model of config.models) {
        if (!isLive(model)) continue;
        predict(model, features.date, changed)
          .then((p) => {
            if (id !== requestId.current) return; // an older request
            setPredictions((all) => ({ ...all, [model.id]: p }));
            setError(`predict-${model.id}`);
          })
          .catch((e) => setError(`predict-${model.id}`, `${model.label}: ${e.message}`));
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [config, features, x]);

  const selectDate = (d: string) => {
    setPredictions({});
    setDate(d);
  };
  const toggle = (id: string) =>
    setHidden((h) => {
      const next = new Set(h);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const reference = source ? forecasts[source.id] : undefined;
  const forecastOf = (id: string, day: string) => forecasts[id]?.find((r) => r.date === day);
  const changedCount = features
    ? Object.entries(features.sliders).filter(([k, s]) => x[k] !== undefined && x[k] !== s.value).length
    : 0;

  return (
    <div className="app">
      <Sidebar
        date={date}
        minDate={reference?.[0]?.date}
        maxDate={reference?.[reference.length - 1]?.date}
        features={features}
        x={x}
        error={errors.features}
        onDate={selectDate}
        onChange={(name, value) => setX((cur) => ({ ...cur, [name]: value }))}
        onReset={() =>
          features && setX(Object.fromEntries(Object.entries(features.sliders).map(([k, s]) => [k, s.value])))
        }
      />

      <main className="main">
        <section className="panel">
          <div className="chart-head">
            <h2>2024: actual load and one-day-ahead forecasts</h2>
            <div className="legend" role="group" aria-label="Models shown">
              <span className="legend-item static">
                <span className="swatch" style={{ background: theme.ink }} />
                Actual
              </span>
              {models.map((m) => {
                const on = !hidden.has(m.id);
                return (
                  <button
                    key={m.id}
                    className={`legend-item${on ? "" : " off"}`}
                    aria-pressed={on}
                    title={on ? `Hide ${m.label}` : `Show ${m.label}`}
                    onClick={() => toggle(m.id)}
                  >
                    <span className="swatch" style={{ background: m.color }} />
                    {m.label}
                    {!isLive(m) && <span className="tag">no what-if</span>}
                  </button>
                );
              })}
            </div>
          </div>
          {Object.entries(errors)
            .filter(([k]) => k !== "features")
            .map(([k, message]) => (
              <p className="error" key={k}>{message}</p>
            ))}
          <Chart
            models={visible}
            showIntervals={showIntervals}
            actual={reference ?? models.map((m) => forecasts[m.id]).find((rows) => rows?.length)}
            forecasts={forecasts}
            predictions={predictions}
            selectedDate={date}
            theme={theme}
            onSelectDate={selectDate}
          />
          <p className="hint">
            Click a day to select it. Diamonds: the forecasts of that day with the X on the left. Click a model above
            to hide or show it; the 80% interval is drawn when only one model is shown.
          </p>
        </section>

        {features && (
          <section className="panel">
            <h2>
              {new Date(features.date).toLocaleDateString("en-GB", {
                weekday: "long", day: "numeric", month: "long", year: "numeric",
              })}
            </h2>
            <div className="actual-line">
              <span className="name">Actual</span>
              <span className="big">{gwh(features.y_true)}</span>
            </div>
            <div className="model-rows">
              {visible.map((m) => {
                // the forecast with the actual X: from the forecast file, so it never moves with the sliders
                const row = forecastOf(m.id, features.date);
                const p = isLive(m) ? predictions[m.id] : undefined;
                const interval = (q?: { "q0.1"?: number; "q0.9"?: number }) =>
                  q && q["q0.1"] !== undefined && q["q0.9"] !== undefined
                    ? <div className="detail">80% interval {gwh(q["q0.1"])} – {gwh(q["q0.9"])}</div>
                    : null;
                return (
                  <div className="model-row" key={m.id} style={{ ["--swatch" as string]: m.color }}>
                    <div className="model-name">
                      <span className="swatch" />
                      {m.label}
                    </div>

                    <div className="card">
                      <div className="name">Forecast (actual X)</div>
                      <div className="big">{row ? gwh(row.y_pred) : "–"}</div>
                      {row && <div className="mid">error {errorText(row.y_pred, features.y_true)}</div>}
                      {interval(row)}
                    </div>

                    <div className="card">
                      <div className="name">What-if (changed X)</div>
                      {!isLive(m) ? (
                        <div className="detail">no what-if: this model is a forecast file only</div>
                      ) : !p ? (
                        <div className="big">…</div>
                      ) : (
                        <>
                          <div className="big">{gwh(p.y_pred)}</div>
                          {changedCount === 0 ? (
                            <div className="mid muted">No X changed</div>
                          ) : (
                            <div className="mid">
                              vs forecast {errorText(p.y_pred, p.y_pred_baseline)}
                            </div>
                          )}
                          {interval(p)}
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
