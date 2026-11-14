import type { Features } from "./api";

const CALENDAR_LABELS: Record<string, string> = {
  is_holiday: "Public holiday",
  is_holiday_weekday: "Holiday on a weekday",
  weighted_regional_holiday: "Regional holiday",
  weighted_school_holiday: "School holiday",
  is_bridge_day: "Bridge day",
  is_christmas_new_year: "Christmas / New Year",
  is_dst: "Summer time",
  is_dst_transition_day: "DST change",
};

const number = new Intl.NumberFormat("en-US", { maximumSignificantDigits: 4 });
export const formatValue = (v: number) => number.format(v);

interface Props {
  date: string | null;
  minDate?: string;
  maxDate?: string;
  features: Features | null;
  x: Record<string, number>;
  error?: string;
  onDate: (date: string) => void;
  onChange: (name: string, value: number) => void;
  onReset: () => void;
}

export function Sidebar({ date, minDate, maxDate, features, x, error, onDate, onChange, onReset }: Props) {
  const changed = features
    ? Object.keys(features.sliders).filter((c) => x[c] !== features.sliders[c].value)
    : [];

  return (
    <aside className="panel sidebar">
      <div>
        <h1>What-if load forecast</h1>
        <p className="subtitle">
          Daily load of Germany in 2024, forecast one day ahead. Pick a day in the chart, then change its
          weather, price or economic X to see how each model reacts.
        </p>
      </div>

      <label className="date">
        Day
        <input
          type="date"
          value={date ?? ""}
          min={minDate}
          max={maxDate}
          onChange={(e) => e.target.value && onDate(e.target.value)}
        />
      </label>

      {error && <p className="error">{error}</p>}

      {features && (
        <>
          <section>
            <h2>Calendar (fixed by the day)</h2>
            <div className="chips">
              <span className="chip on">{String(features.calendar.day_of_week)}</span>
              {Object.entries(CALENDAR_LABELS).map(([key, label]) => {
                const value = Number(features.calendar[key] ?? 0);
                if (value === 0) return null;
                const share = value < 1 ? ` ${Math.round(value * 100)}%` : "";
                return (
                  <span key={key} className="chip on">
                    {label}
                    {share}
                  </span>
                );
              })}
            </div>
          </section>

          <section>
            <div className="section-head">
              <h2>X of the day</h2>
              <button onClick={onReset} disabled={changed.length === 0}>
                Reset to actual{changed.length ? ` (${changed.length})` : ""}
              </button>
            </div>
            {Object.entries(features.sliders).map(([name, s]) => {
              const value = x[name] ?? s.value;
              const isChanged = value !== s.value;
              const tick = ((s.value - s.min) / (s.max - s.min)) * 100;
              return (
                <div className="slider" key={name}>
                  <div className="slider-head">
                    <span>
                      {s.label}
                      {s.past_only && <span className="tag" title="known only up to the day before">past-only</span>}
                    </span>
                    <span className={`value${isChanged ? " changed" : ""}`}>
                      {formatValue(value)} {s.unit}
                    </span>
                  </div>
                  {s.note && <div className="slider-note">{s.note}</div>}
                  <div className="slider-track">
                    <input
                      type="range"
                      aria-label={s.label}
                      min={s.min}
                      max={s.max}
                      step={s.step}
                      value={value}
                      onChange={(e) => onChange(name, Number(e.target.value))}
                      onDoubleClick={() => onChange(name, s.value)}
                    />
                    <span className="actual-tick" style={{ left: `${tick}%` }} title="actual value" />
                  </div>
                  <div className="slider-foot">
                    <span>{formatValue(s.min)}</span>
                    <span>actual {formatValue(s.value)}</span>
                    <span>{formatValue(s.max)}</span>
                  </div>
                </div>
              );
            })}
            <p className="hint">
              Range: actual ± 2 standard deviations of 2019–2023. Double-click a slider to reset it.
            </p>
          </section>
        </>
      )}
    </aside>
  );
}
