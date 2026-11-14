// Clients for the model services (contract: docs/deploy/API.md)

// A live model has `url` (an API with what-if forecasts); a static model has `forecastCsv` (a forecast file in
// the shared format, only its step-1 rows are used) and no what-if.
export interface ModelConfig {
  id: string;
  label: string;
  url?: string;
  forecastCsv?: string;
}

export const isLive = (model: ModelConfig): model is ModelConfig & { url: string } => Boolean(model.url);

export interface AppConfig {
  models: ModelConfig[];
  featureSource: string; // the model whose /features fills the sliders
}

export type Quantiles = Partial<Record<"q0.1" | "q0.9", number>>;

export interface ForecastRow extends Quantiles {
  date: string;
  y_true: number;
  y_pred: number;
}

export interface Slider {
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  step: number;
  past_only: boolean;
  note?: string;
}

export interface Features {
  date: string;
  y_true: number;
  sliders: Record<string, Slider>;
  calendar: Record<string, number | string>;
}

export interface Prediction extends Quantiles {
  date: string;
  y_pred: number;
  y_pred_baseline: number;
  y_true: number;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      // not JSON
    }
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const loadConfig = () => request<AppConfig>(`${import.meta.env.BASE_URL}config.json`);

// a forecast file of the shared format (src/models/foundation/data.py): the step-1 rows, one per day
export function parseForecastCsv(text: string): ForecastRow[] {
  const [header, ...lines] = text.trim().split(/\r?\n/);
  const columns = header.split(",").map((c) => c.trim());
  const col = (name: string) => columns.indexOf(name);
  const [iTarget, iStep, iTrue, iPred, iLow, iHigh] =
    ["target_time", "step", "y_true", "y_pred", "q0.1", "q0.9"].map(col);
  if (iTarget < 0 || iPred < 0) throw new Error("not a forecast file (needs target_time and y_pred)");
  const rows: ForecastRow[] = [];
  for (const line of lines) {
    const cells = line.split(",");
    if (iStep >= 0 && Number(cells[iStep]) !== 1) continue;
    const row: ForecastRow = {
      date: cells[iTarget].slice(0, 10),
      y_true: iTrue >= 0 ? Number(cells[iTrue]) : NaN,
      y_pred: Number(cells[iPred]),
    };
    if (iLow >= 0 && iHigh >= 0 && cells[iLow] !== "" && cells[iHigh] !== "") {
      row["q0.1"] = Number(cells[iLow]);
      row["q0.9"] = Number(cells[iHigh]);
    }
    rows.push(row);
  }
  return rows.sort((a, b) => a.date.localeCompare(b.date));
}

export async function getForecast(model: ModelConfig): Promise<ForecastRow[]> {
  if (model.url) return request<ForecastRow[]>(`${model.url}/forecast`);
  if (model.forecastCsv) {
    const url = new URL(model.forecastCsv, window.location.href).toString();
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${response.status}: ${model.forecastCsv}`);
    return parseForecastCsv(await response.text());
  }
  throw new Error("the model needs a url or a forecastCsv");
}

export const getFeatures = (model: ModelConfig & { url: string }, date: string) =>
  request<Features>(`${model.url}/features?date=${encodeURIComponent(date)}`);

export const predict = (model: ModelConfig & { url: string }, date: string, x: Record<string, number>) =>
  request<Prediction>(`${model.url}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date, x }),
  });
