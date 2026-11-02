import type { Band } from "./types";

export const BANDS: Band[] = [
  { key: "low", min: 0, max: 20, label_th: "ผลกระทบเชิงระบบระดับต่ำ", color: "green" },
  { key: "watch", min: 21, max: 45, label_th: "เฝ้าระวัง / ผันผวนระดับภูมิภาค", color: "yellow" },
  { key: "high", min: 46, max: 70, label_th: "ตึงเครียดสูง / กระทบห่วงโซ่โลก", color: "orange" },
  { key: "critical", min: 71, max: 100, label_th: "วิกฤตเชิงระบบระดับโลก", color: "red" },
];

// One hex per band, used for marks only — text stays in neutral ink.
export const BAND_HEX: Record<Band["key"], string> = {
  low: "#22c55e",
  watch: "#eab308",
  high: "#f97316",
  critical: "#ef4444",
};

export function bandOf(score: number | null | undefined): Band | null {
  if (score === null || score === undefined) return null;
  const s = Math.round(score);
  return BANDS.find((b) => s >= b.min && s <= b.max) ?? BANDS[BANDS.length - 1];
}

export function fmtNumber(v: number | string | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  return v.toLocaleString("th-TH", { maximumFractionDigits: digits });
}

export function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export function fmtThaiDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("th-TH", {
    day: "numeric",
    month: "short",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Bangkok",
  });
}

export function relativeThai(fromIso: string, now: number): string {
  const mins = Math.max(0, Math.round((now - new Date(fromIso).getTime()) / 60000));
  if (mins < 1) return "เมื่อสักครู่";
  if (mins < 60) return `${mins} นาทีที่แล้ว`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 48) return `${hrs} ชั่วโมงที่แล้ว`;
  return `${Math.floor(hrs / 24)} วันที่แล้ว`;
}
