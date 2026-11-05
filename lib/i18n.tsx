"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Lang = "th" | "en";
const STORAGE_KEY = "gci-lang";

const DICT = {
  // header
  updated: { th: "อัปเดต", en: "Updated" },
  delayed: { th: "ล่าช้า", en: "Delayed" },
  staleData: { th: "ข้อมูลเก่า", en: "Stale data" },
  sources: { th: "แหล่งข้อมูล", en: "Sources" },
  generatedAt: { th: "สร้างข้อมูลเมื่อ", en: "Generated" },
  localTime: { th: "(เวลาไทย)", en: "(Bangkok time)" },
  failedSources: { th: "แหล่งที่ไม่ตอบสนอง", en: "Sources not responding" },
  allSourcesOk: { th: "ทุกแหล่งข้อมูลตอบสนองปกติ", en: "All sources responded normally" },
  freshTitle: { th: "ความสดของข้อมูลแต่ละแหล่ง", en: "How fresh is each source" },
  freshSub: {
    th: "“ข้อมูลล่าสุด” คือเวลาของรายการใหม่สุดที่แหล่งนั้นรายงาน ส่วน “ดึงเมื่อ” คือเวลาที่ระบบดึงข้อมูลรอบนี้ (เวลาไทย)",
    en: "“Latest data” is the time of the newest item the source reported; “Fetched” is when this run pulled it (Bangkok time)",
  },
  freshSource: { th: "แหล่งข้อมูล", en: "Source" },
  freshLatest: { th: "ข้อมูลล่าสุด", en: "Latest data" },
  freshFetched: { th: "ดึงเมื่อ", en: "Fetched" },
  freshDailyClose: { th: "ราคาปิดรายวัน", en: "daily close" },
  freshUnknown: { th: "ไม่ระบุ", en: "n/a" },
  freshFailed: { th: "ดึงไม่สำเร็จ", en: "fetch failed" },
  langLabel: { th: "ภาษา", en: "Language" },
  // relative time
  justNow: { th: "เมื่อสักครู่", en: "just now" },
  minAgo: { th: "{n} นาทีที่แล้ว", en: "{n} min ago" },
  hrAgo: { th: "{n} ชั่วโมงที่แล้ว", en: "{n} h ago" },
  dayAgo: { th: "{n} วันที่แล้ว", en: "{n} days ago" },
  // hero
  heroLabel: { th: "ระดับผลกระทบเชิงระบบต่อโลก", en: "Global systemic impact level" },
  heroSr: { th: "ดัชนีวิกฤตโลกปัจจุบัน", en: "Current global crisis index" },
  noScore: { th: "ข้อมูลไม่พอสำหรับคำนวณ (ไม่แสดงเป็น 0)", en: "Not enough data to compute (never shown as 0)" },
  drivers: { th: "ปัจจัยขับเคลื่อนหลัก", en: "Top drivers" },
  baseBoost: { th: "คะแนนฐาน {b} + ตัวเร่ง {x}", en: "Base {b} + boost {x}" },
  crossOn: { th: "วิกฤตยืนยันข้ามหมวด — ตัวเร่งเชิงระบบทำงาน", en: "Cross-pillar crisis confirmed — systemic booster active" },
  crossOff: { th: "ยังไม่มีการยืนยันข้ามหมวด (ตัวเร่งจำกัด ≤ 15)", en: "No cross-pillar confirmation (boost capped at ≤ 15)" },
  summaryBy: { th: "ข้อความสรุปโดย", en: "Summary by" },
  byTemplate: { th: "เทมเพลตอัตโนมัติ", en: "rule-based template" },
  prevRun: { th: " (รอบก่อน)", en: " (previous run)" },
  deterministic: { th: "ตัวเลขทั้งหมดคำนวณด้วยสูตรตายตัว", en: "all numbers come from a fixed formula" },
  // sparkline
  trend: { th: "แนวโน้มคะแนนย้อนหลัง (สูงสุด 90 วัน)", en: "Score trend (up to 90 days)" },
  noHistory: { th: "ยังไม่มีประวัติคะแนน", en: "No score history yet" },
  accumulating: {
    th: "กำลังสะสมข้อมูล — กราฟจะสมบูรณ์ขึ้นหลังอัปเดตหลายรอบ",
    en: "Collecting data — the chart fills in after a few updates",
  },
  chartAria: { th: "กราฟคะแนนย้อนหลัง {n} จุด ล่าสุด {s}", en: "Score history, {n} points, latest {s}" },
  // watchlist
  watchTitle: { th: "สัญญาณเตือนล่วงหน้า", en: "Early-warning watchlist" },
  watchSub: {
    th: "สิ่งที่ควรจับตาใน 1-3 เดือนข้างหน้า — แยกจากคะแนนปัจจุบัน ไม่ถูกนำไปคำนวณดัชนี",
    en: "What to watch over the next 1-3 months — separate from the current score and not part of the index",
  },
  byRules: { th: "สกัดด้วยกฎอัตโนมัติ", en: "Extracted by rules" },
  byAI: { th: "สกัดโดย AI จากข่าวที่ระบบส่งให้", en: "Extracted by AI from news supplied by the system" },
  noWarnings: { th: "ไม่พบสัญญาณเตือนที่มีหลักฐานเพียงพอในรอบนี้", en: "No sufficiently evidenced warning signals this run" },
  readSources: { th: "อ่านข่าวต้นทาง", en: "Read the source" },
  sig_สูง: { th: "สัญญาณสูง", en: "High signal" },
  sig_ปานกลาง: { th: "สัญญาณปานกลาง", en: "Medium signal" },
  sig_เฝ้าระวัง: { th: "สัญญาณเฝ้าระวัง", en: "Watch" },
  // pillars
  pillarsTitle: { th: "4 เสาหลักของดัชนี", en: "The 4 pillars" },
  pillarsSub: {
    th: "คะแนนย่อย 0-100 ต่อหมวด พร้อมค่าตัวชี้วัดจริงที่ใช้คำนวณ",
    en: "Sub-scores 0-100 per pillar, with the real indicator values behind them",
  },
  weight: { th: "น้ำหนัก", en: "Weight" },
  dataStatus: { th: "ข้อมูล", en: "Data" },
  colIndicator: { th: "ตัวชี้วัด", en: "Indicator" },
  colLatest: { th: "ล่าสุด", en: "Latest" },
  col5d: { th: "5 วันทำการ", en: "5 trading days" },
  colScore: { th: "คะแนน", en: "Score" },
  indStale: { th: "(ค่าเดิม)", en: "(last value)" },
  indMissing: { th: "(ขาดหาย)", en: "(missing)" },
  indClosed: { th: "(ปิดตลาด)", en: "(market closed)" },
  topEvents: { th: "เหตุการณ์ที่มีน้ำหนักสูงสุด", en: "Highest-weighted events" },
  evMeta: { th: "{s} คะแนน · {n} แหล่ง", en: "{s} pts · {n} source(s)" },
  evArticles: { th: " · {n} ข่าว", en: " · {n} articles" },
  // local notes
  localTitle: { th: "หมายเหตุเหตุการณ์ระดับท้องถิ่น", en: "Local event notes" },
  localSub: {
    th: "เหตุการณ์รุนแรงที่เกิดเฉพาะพื้นที่ (ห่างจากจุดยุทธศาสตร์ห่วงโซ่อุปทานโลก) ถูกจำกัดน้ำหนักไว้ไม่เกิน {cap} คะแนนในหมวด จึงไม่ดันคะแนนรวมของโลกให้สูงเกินจริง — แต่ยังสำคัญต่อผู้ได้รับผลกระทบ",
    en: "Severe events confined to one area (away from global supply-chain chokepoints) are capped at {cap} points in their pillar, so they don't inflate the world score — but they still matter to the people affected.",
  },
  noLocal: { th: "ไม่มีเหตุการณ์ท้องถิ่นที่มีนัยสำคัญในรอบนี้", en: "No significant local events this run" },
  colEvent: { th: "เหตุการณ์", en: "Event" },
  colType: { th: "ประเภท", en: "Type" },
  colActual: { th: "ความรุนแรงจริง", en: "Actual severity" },
  colCounted: { th: "นับในดัชนี", en: "Counted in index" },
  // footer
  dataFrom: { th: "ข้อมูลจาก", en: "Data from" },
  notAdvice: { th: "ไม่ใช่คำแนะนำการลงทุน", en: "Not investment advice" },
  licenseNote: { th: "ข้อมูลและเนื้อหาใช้สัญญาอนุญาต", en: "Data and content licensed under" },
  creditNote: { th: "นำไปใช้หรืออ้างอิงได้โดยต้องให้เครดิต", en: "free to use or cite with attribution" },
  noData: { th: "ยังไม่มีข้อมูล — รัน", en: "No data yet — run" },
  noDataAfter: { th: "ก่อน", en: "first" },
} as const;

export type DictKey = keyof typeof DICT;

interface LangCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: DictKey, vars?: Record<string, string | number>) => string;
  /** obj[`${field}_en`] in English (falling back to Thai), obj[`${field}_th`] or obj[field] in Thai. */
  pick: (obj: object | null | undefined, field: string) => string;
}

const Ctx = createContext<LangCtx | null>(null);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("th");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "en" || saved === "th") setLangState(saved);
    } catch {
      /* storage unavailable: stay on Thai */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* ignore */
    }
  }, []);

  const t = useCallback(
    (key: DictKey, vars?: Record<string, string | number>) => {
      let s: string = DICT[key][lang];
      if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
      return s;
    },
    [lang],
  );

  const pick = useCallback(
    (obj: object | null | undefined, field: string) => {
      if (!obj) return "";
      const o = obj as Record<string, unknown>;
      const th = (o[`${field}_th`] ?? o[field] ?? "") as string;
      if (lang === "th") return th;
      return ((o[`${field}_en`] as string | undefined) || th) ?? "";
    },
    [lang],
  );

  return <Ctx.Provider value={{ lang, setLang, t, pick }}>{children}</Ctx.Provider>;
}

export function useLang(): LangCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useLang must be used inside <LangProvider>");
  return c;
}
