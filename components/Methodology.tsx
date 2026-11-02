"use client";

import { BookOpen, ChevronDown } from "lucide-react";
import type { LatestState } from "@/lib/types";
import { fmtDate } from "@/lib/format";
import { useLang } from "@/lib/i18n";

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <h3 className="mb-2 font-semibold text-zinc-800">{title}</h3>
      <div className="space-y-2 text-sm text-zinc-600">{children}</div>
    </div>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return <pre className="num overflow-x-auto rounded-lg bg-zinc-50 p-3 text-[12px] leading-relaxed text-zinc-700 ring-1 ring-zinc-200">{children}</pre>;
}

export function Methodology({ state }: { state: LatestState }) {
  const { lang, t } = useLang();
  const c = state.config;
  const w = c.weights;
  const b = c.booster;
  const en = lang === "en";
  const decay = Math.round(c.decay_per_day * 100);
  const hubs = (en && c.strategic_hubs_en ? c.strategic_hubs_en : c.strategic_hubs).join(", ");
  const natCap = (c.local_cap * w.nat).toFixed(1);

  const formulaBase = `S_base = ${w.econ}·S_econ + ${w.geo}·S_geo\n       + ${w.nat}·S_nat + ${w.bio_infra}·S_bio_infra`;
  const formulaBoost = en
    ? `if S_max1 > ${b.max1_threshold} and S_max2 > ${b.max2_threshold}:\n  Boost = (100 − S_base)·${b.factor}·((S_max1 − ${b.max1_threshold})/${100 - b.max1_threshold})^${b.exponent}\notherwise: Boost ≤ ${b.isolated_cap}\nGlobal = min(100, round(S_base + Boost))`
    : `ถ้า S_max1 > ${b.max1_threshold} และ S_max2 > ${b.max2_threshold}:\n  Boost = (100 − S_base)·${b.factor}·((S_max1 − ${b.max1_threshold})/${100 - b.max1_threshold})^${b.exponent}\nไม่เช่นนั้น: Boost ≤ ${b.isolated_cap}\nGlobal = min(100, round(S_base + Boost))`;

  return (
    <section>
      <details className="rounded-xl border border-zinc-200 bg-white shadow-sm">
        <summary className="flex cursor-pointer items-center justify-between gap-3 p-4 sm:p-5">
          <span className="flex items-center gap-2 font-semibold text-zinc-800">
            <BookOpen className="h-5 w-5 text-zinc-600" aria-hidden />
            {t("methodTitle")}
          </span>
          <ChevronDown className="chev h-5 w-5 text-zinc-500 transition-transform" aria-hidden />
        </summary>

        <div className="grid gap-8 border-t border-zinc-200 p-4 sm:p-6 md:grid-cols-2">
          <Block title={en ? "1. Base score (weighted average)" : "1. คะแนนฐาน (ค่าเฉลี่ยถ่วงน้ำหนัก)"}>
            <Code>{formulaBase}</Code>
            <p>
              {en
                ? "If a pillar has no data it is dropped and the weights are renormalised — never replaced with 0, which would make the world look safer than it is."
                : "หากหมวดใดไม่มีข้อมูล จะถูกตัดออกและกระจายน้ำหนักใหม่ — ไม่แทนค่าด้วย 0 เพราะจะทำให้โลกดูปลอดภัยเกินจริง"}
            </p>
          </Block>

          <Block title={en ? "2. Cross-pillar systemic booster" : "2. ตัวเร่งเมื่อวิกฤตลุกลามข้ามหมวด"}>
            <Code>{formulaBoost}</Code>
            <p>
              {en
                ? "Prevents both “the average burying a major crisis” and “one faulty pillar dragging the world score to 100”."
                : "ป้องกันทั้งปัญหา “ค่าเฉลี่ยกดทับวิกฤตใหญ่” และ “ข้อมูลหมวดเดียวผิดพลาดแล้วดึงคะแนนโลกเป็น 100”"}
            </p>
            <p className="num text-xs text-zinc-500">
              {en ? "This run" : "รอบนี้"}: S_max1 = {state.formula.max1 ?? "—"}, S_max2 = {state.formula.max2 ?? "—"}, Boost = {state.formula.boost ?? "—"}
            </p>
          </Block>

          <Block title={en ? "Economy, finance & energy (35%)" : "เศรษฐกิจ การเงิน และพลังงาน (35%)"}>
            <p>
              {en
                ? "VIX, Brent crude, gold, the S&P 500 and SOXX from Yahoo Finance (FRED as fallback), mapped to scores with piecewise-linear curves on price level, 5-trading-day change and drawdown from the 52-week high."
                : "VIX, น้ำมัน Brent, ทองคำ, S&P 500 และ SOXX จาก Yahoo Finance (สำรองด้วย FRED) แปลงเป็นคะแนนด้วย Piecewise Linear Mapping จากระดับราคา การเปลี่ยนแปลง 5 วันทำการ และระยะห่างจากจุดสูงสุด 52 สัปดาห์"}
            </p>
            <p>
              {en
                ? "On weekends Friday's close is used as normal (status “market closed”, not a failure)."
                : "วันเสาร์-อาทิตย์ใช้ราคาปิดวันศุกร์ตามปกติ (สถานะ “ตลาดปิดสุดสัปดาห์” ไม่ถือว่าระบบล่ม)"}
            </p>
          </Block>

          <Block title={en ? "Conflict & geopolitics (35%)" : "ความขัดแย้งและภูมิรัฐศาสตร์ (35%)"}>
            <p>
              {en
                ? "News from GDELT, BBC World, Al Jazeera and Reuters is grouped into events by severity category and countries involved. The score depends on severity and on how many distinct outlets confirm it — not on article count, so 50 copies of one story weigh the same as one."
                : "ข่าวจาก GDELT, BBC World, Al Jazeera และ Reuters ถูกยุบรวมเป็น “เหตุการณ์” ตามหมวดความรุนแรงและประเทศที่เกี่ยวข้อง คะแนนขึ้นกับระดับความรุนแรงและจำนวนสำนักข่าวที่ยืนยัน — ไม่ใช่จำนวนบทความ ข่าวซ้ำ 50 ชิ้นจึงมีน้ำหนักเท่าข่าวเดียว"}
            </p>
            <p>
              {en
                ? `Severe categories (nuclear, chokepoints, etc.) must appear in the headline. Ongoing events are remembered across runs and lose ${decay}% weight per day without new reports.`
                : `หมวดรุนแรงสูง (นิวเคลียร์ ช่องแคบ ฯลฯ) ต้องปรากฏในพาดหัวข่าว เหตุการณ์ที่ยังไม่ยุติถูกจดจำข้ามรอบและลดน้ำหนักลง ${decay}% ต่อวันหากไม่มีรายงานใหม่`}
            </p>
          </Block>

          <Block title={en ? "Natural hazards (15%)" : "ภัยธรรมชาติ (15%)"}>
            <p>
              {en
                ? `USGS (M6.0+ earthquakes) and GDACS (green/orange/red alerts) pass a 2-stage filter: events more than ${c.hub_radius_km} km from a global strategic hub, with no cross-regional tsunami, are capped at ${c.local_cap}/100 (at most ${natCap} points on the world score).`
                : `USGS (แผ่นดินไหว M6.0+) และ GDACS (ระดับเตือนเขียว/ส้ม/แดง) ผ่านตัวกรอง 2 ขั้น: เหตุที่อยู่ห่างจุดยุทธศาสตร์โลกเกิน ${c.hub_radius_km} กม. และไม่มีสึนามิข้ามภูมิภาค ถูกจำกัดไว้ที่ ${c.local_cap}/100 (กระทบคะแนนโลกไม่เกิน ${natCap} แต้ม)`}
            </p>
            <p>
              {en ? "Strategic hubs" : "จุดยุทธศาสตร์"}: {hubs}
            </p>
          </Block>

          <Block title={en ? "Health & critical infrastructure (15%)" : "สุขภาพและโครงสร้างพื้นฐาน (15%)"}>
            <p>
              {en
                ? `WHO Disease Outbreak News and CISA alerts. Routine vulnerability advisories carry very little weight; real outbreaks and attacks count more. Events confined to one country are capped at ${c.single_country_cap}/100.`
                : `WHO Disease Outbreak News และ CISA Cybersecurity Alerts แยก “ประกาศช่องโหว่ทั่วไป” (น้ำหนักต่ำมาก) ออกจาก “การระบาด/การโจมตีที่เกิดขึ้นจริง” เหตุที่จำกัดอยู่ในประเทศเดียวมีเพดาน ${c.single_country_cap}/100`}
            </p>
          </Block>

          <Block title={en ? "Role of AI" : "บทบาทของ AI"}>
            <p>
              {en
                ? "Every number is computed deterministically in Python. Gemini only writes the summary text from the numbers and pre-filtered news, and is called only when something new happens (at most once per run). Without an API key the system falls back to rule-based templates."
                : "ตัวเลขทุกตัวคำนวณด้วย Python แบบ Deterministic — Gemini ใช้เพียงเขียนข้อความสรุปจากตัวเลขและข่าวที่ระบบคัดแล้ว และเรียกเฉพาะเมื่อมีเหตุการณ์ใหม่ (ไม่เกิน 1 ครั้งต่อรอบ) หากไม่มี API Key ระบบใช้เทมเพลตแทนได้ทันที"}
            </p>
          </Block>

          <Block title={en ? "Limitations" : "ข้อจำกัด"}>
            <ul className="list-disc space-y-1 pl-5">
              {(en
                ? [
                    "News is classified with English keywords and may miss or misclassify events phrased differently.",
                    "The index reflects systemic impact on the world, not the human toll in any one place.",
                    "Updated every 6 hours — not a real-time warning system, and not investment advice.",
                    "Early warnings summarise news; they are not probabilistic forecasts.",
                  ]
                : [
                    "การจัดหมวดข่าวใช้คำสำคัญภาษาอังกฤษ อาจจัดผิดหมวดหรือพลาดเหตุการณ์ที่ใช้ถ้อยคำต่างไป",
                    "ดัชนีสะท้อนผลกระทบเชิงระบบต่อโลก ไม่ใช่ความรุนแรงต่อชีวิตในพื้นที่ใดพื้นที่หนึ่ง",
                    "อัปเดตทุก 6 ชั่วโมง ไม่ใช่ระบบเตือนภัยแบบเรียลไทม์ และไม่ใช่คำแนะนำการลงทุน",
                    "สัญญาณเตือนล่วงหน้าเป็นการสรุปจากข่าว ไม่ใช่การพยากรณ์เชิงความน่าจะเป็น",
                  ]
              ).map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </Block>

          <div className="min-w-0 md:col-span-2">
            <h3 className="mb-2 font-semibold text-zinc-800">{t("sourceStatus")}</h3>
            <div className="overflow-x-auto rounded-lg border border-zinc-200">
              <table className="w-full min-w-[480px] text-sm">
                <thead className="bg-zinc-50 text-left text-[11px] text-zinc-500">
                  <tr>
                    <th className="px-3 py-2 font-normal">{t("colSource")}</th>
                    <th className="px-3 py-2 font-normal">{t("colStatus")}</th>
                    <th className="px-3 py-2 text-right font-normal">{t("colItems")}</th>
                    <th className="px-3 py-2 font-normal">{t("colTime")}</th>
                  </tr>
                </thead>
                <tbody>
                  {state.data_status.sources.map((s) => (
                    <tr key={s.name} className="border-t border-zinc-200">
                      <td className="px-3 py-1.5 text-zinc-700">{s.name}</td>
                      <td className={`px-3 py-1.5 ${s.status === "ok" ? "text-emerald-700" : "text-amber-700"}`} title={s.error ?? undefined}>
                        {s.status === "ok" ? t("srcOk") : t("srcErr")}
                      </td>
                      <td className="num px-3 py-1.5 text-right text-zinc-600">{s.items ?? "—"}</td>
                      <td className="num px-3 py-1.5 text-zinc-500">{fmtDate(s.fetched_at, lang)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </details>
    </section>
  );
}
