// Mirrors the JSON written by scripts/gci/pipeline.py

export type PillarKey = "econ" | "geo" | "nat" | "bio_infra";
export type Status = "ok" | "partial" | "market_closed" | "stale" | "degraded";
export type Signal = "สูง" | "ปานกลาง" | "เฝ้าระวัง";

export interface Band {
  key: "low" | "watch" | "high" | "critical";
  min: number;
  max: number;
  label_th: string;
  label_en?: string;
  short_th?: string;
  short_en?: string;
  color: string;
}

export interface EventItem {
  id: string;
  pillar: PillarKey;
  category: string;
  category_th: string;
  category_en?: string;
  title: string;
  severity: number;
  score: number;
  countries: string[];
  sources: string[];
  article_count: number;
  links: string[];
  first_seen: string | null;
  last_seen: string | null;
  is_local: boolean;
  location: string | null;
  location_en?: string | null;
  raw_score: number | null;
}

export interface Metric {
  key?: string;
  label_th: string;
  label_en?: string;
  value: number | string | null;
  unit: string;
  unit_en?: string;
  hint: string | null;
  hint_en?: string | null;
}

export interface Indicator {
  key: string;
  label_th: string;
  label_en?: string;
  unit: string;
  unit_en?: string;
  ticker: string;
  weight: number;
  value: number | null;
  change_pct: number | null;
  drawdown_pct: number | null;
  score: number | null;
  status: string;
  last_date: string | null;
  provider?: string;
}

export interface Pillar {
  label_th: string;
  label_en?: string;
  score: number | null;
  weight: number;
  effective_weight: number | null;
  status: Status;
  status_th: string;
  status_en?: string;
  note: string | null;
  top_events: EventItem[];
  metrics: Metric[];
  indicators?: Indicator[];
}

export interface SourceRef {
  url: string;
  source: string;
}

export interface Warning {
  title: string;
  signal_strength: Signal;
  timeframe: string;
  evidence_summary: string;
  refs?: SourceRef[];
}

export interface SourceStatus {
  name: string;
  pillar: PillarKey;
  status: "ok" | "error";
  fetched_at: string;
  /** Newest underlying data point: ISO time, or a bare YYYY-MM-DD for daily market closes. */
  data_as_of?: string | null;
  items: number | null;
  error: string | null;
  note: string | null;
}

export interface LatestState {
  schema_version: number;
  generated_at: string;
  global_score: number | null;
  band: Band | null;
  formula: {
    base: number | null;
    boost: number | null;
    cross_confirmed: boolean;
    max1: number | null;
    max2: number | null;
    max1_pillar: PillarKey | null;
  };
  pillars: Record<PillarKey, Pillar>;
  top_drivers: {
    pillar: PillarKey;
    label_th: string;
    label_en?: string;
    score: number;
    contribution: number;
    headline: string | null;
    headline_en?: string | null;
  }[];
  summary: {
    executive_summary_th: string;
    early_warnings_th: Warning[];
    local_notes_th: string[];
    executive_summary_en?: string;
    early_warnings_en?: Warning[];
    local_notes_en?: string[];
    source: "gemini" | "gemini_cached" | "template";
    model: string | null;
    generated_at: string | null;
  };
  local_events: EventItem[];
  data_status: { key: "ok" | "market_closed" | "degraded"; label_th: string; label_en?: string; sources: SourceStatus[] };
  config: {
    weights: Record<PillarKey, number>;
    booster: { max1_threshold: number; max2_threshold: number; factor: number; exponent: number; isolated_cap: number };
    bands: Band[];
    local_cap: number;
    single_country_cap: number;
    hub_radius_km: number;
    strategic_hubs: string[];
    strategic_hubs_en?: string[];
    decay_per_day: number;
  };
}

export interface HistoryPoint {
  t: string;
  score: number;
  econ: number | null;
  geo: number | null;
  nat: number | null;
  bio_infra: number | null;
}
