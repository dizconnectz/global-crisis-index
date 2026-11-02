import type { Band } from "./types";

export const BANDS: Band[] = [
  { key: "low", min: 0, max: 20, label_th: "ผลกระทบเชิงระบบระดับต่ำ", label_en: "Low systemic impact", short_th: "ต่ำ", short_en: "Low", color: "green" },
  { key: "watch", min: 21, max: 45, label_th: "เฝ้าระวัง / ผันผวนระดับภูมิภาค", label_en: "Watch / regional volatility", short_th: "เฝ้าระวัง", short_en: "Watch", color: "yellow" },
  { key: "high", min: 46, max: 70, label_th: "ตึงเครียดสูง / กระทบห่วงโซ่โลก", label_en: "High tension / global supply-chain impact", short_th: "ตึงเครียดสูง", short_en: "High tension", color: "orange" },
  { key: "critical", min: 71, max: 100, label_th: "วิกฤตเชิงระบบระดับโลก", label_en: "Global systemic crisis", short_th: "วิกฤต", short_en: "Crisis", color: "red" },
];

// One hex per band, used for marks only — text stays in neutral ink.
export const BAND_HEX: Record<Band["key"], string> = {
  low: "#16a34a",
  watch: "#ca8a04",
  high: "#ea580c",
  critical: "#dc2626",
};

export function bandOf(score: number | null | undefined): Band | null {
  if (score === null || score === undefined) return null;
  const s = Math.round(score);
  return BANDS.find((b) => s >= b.min && s <= b.max) ?? BANDS[BANDS.length - 1];
}

export type Locale = "th" | "en";
const LOCALE = { th: "th-TH", en: "en-GB" } as const;

export function fmtNumber(v: number | string | null | undefined, lang: Locale = "th", digits = 2): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  return v.toLocaleString(LOCALE[lang], { maximumFractionDigits: digits });
}

export function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export function fmtDate(iso: string | null | undefined, lang: Locale = "th"): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(LOCALE[lang], {
    day: "numeric",
    month: "short",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Bangkok",
  });
}

/** Minutes/hours/days since `fromIso`, as a dictionary key + count. */
export function relativeParts(fromIso: string, now: number): { key: "justNow" | "minAgo" | "hrAgo" | "dayAgo"; n: number } {
  const mins = Math.max(0, Math.round((now - new Date(fromIso).getTime()) / 60000));
  if (mins < 1) return { key: "justNow", n: 0 };
  if (mins < 60) return { key: "minAgo", n: mins };
  const hrs = Math.floor(mins / 60);
  if (hrs < 48) return { key: "hrAgo", n: hrs };
  return { key: "dayAgo", n: Math.floor(hrs / 24) };
}
