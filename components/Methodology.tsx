import { BookOpen, ChevronDown } from "lucide-react";
import type { LatestState } from "@/lib/types";
import { fmtThaiDate } from "@/lib/format";

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <h3 className="mb-2 font-semibold text-zinc-200">{title}</h3>
      <div className="space-y-2 text-sm text-zinc-400">{children}</div>
    </div>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return <pre className="num overflow-x-auto rounded-lg bg-zinc-950 p-3 text-[12px] leading-relaxed text-zinc-300">{children}</pre>;
}

export function Methodology({ state }: { state: LatestState }) {
  const c = state.config;
  const w = c.weights;
  const b = c.booster;
  return (
    <section>
      <details className="rounded-xl border border-zinc-800 bg-zinc-900/30">
        <summary className="flex cursor-pointer items-center justify-between gap-3 p-4 sm:p-5">
          <span className="flex items-center gap-2 font-semibold text-zinc-200">
            <BookOpen className="h-5 w-5 text-zinc-400" aria-hidden />
            วิธีคำนวณ แหล่งข้อมูล และข้อจำกัด
          </span>
          <ChevronDown className="chev h-5 w-5 text-zinc-500 transition-transform" aria-hidden />
        </summary>

        <div className="grid gap-8 border-t border-zinc-800 p-4 sm:p-6 md:grid-cols-2">
          <Block title="1. คะแนนฐาน (ค่าเฉลี่ยถ่วงน้ำหนัก)">
            <Code>{`S_base = ${w.econ}·S_econ + ${w.geo}·S_geo\n       + ${w.nat}·S_nat + ${w.bio_infra}·S_bio_infra`}</Code>
            <p>หากหมวดใดไม่มีข้อมูล จะถูกตัดออกและกระจายน้ำหนักใหม่ — ไม่แทนค่าด้วย 0 เพราะจะทำให้โลกดูปลอดภัยเกินจริง</p>
          </Block>

          <Block title="2. ตัวเร่งเมื่อวิกฤตลุกลามข้ามหมวด">
            <Code>{`ถ้า S_max1 > ${b.max1_threshold} และ S_max2 > ${b.max2_threshold}:\n  Boost = (100 − S_base)·${b.factor}·((S_max1 − ${b.max1_threshold})/${100 - b.max1_threshold})^${b.exponent}\nไม่เช่นนั้น: Boost ≤ ${b.isolated_cap}\nGlobal = min(100, round(S_base + Boost))`}</Code>
            <p>ป้องกันทั้งปัญหา “ค่าเฉลี่ยกดทับวิกฤตใหญ่” และ “ข้อมูลหมวดเดียวผิดพลาดแล้วดึงคะแนนโลกเป็น 100”</p>
            <p className="num text-xs text-zinc-500">
              รอบนี้: S_max1 = {state.formula.max1 ?? "—"}, S_max2 = {state.formula.max2 ?? "—"}, Boost = {state.formula.boost ?? "—"}
            </p>
          </Block>

          <Block title="เศรษฐกิจ การเงิน และพลังงาน (35%)">
            <p>VIX, น้ำมัน Brent, ทองคำ, S&amp;P 500 และ SOXX จาก Yahoo Finance (สำรองด้วย FRED) แปลงเป็นคะแนนด้วย Piecewise Linear Mapping จากระดับราคา การเปลี่ยนแปลง 5 วันทำการ และระยะห่างจากจุดสูงสุด 52 สัปดาห์</p>
            <p>วันเสาร์-อาทิตย์ใช้ราคาปิดวันศุกร์ตามปกติ (สถานะ “ตลาดปิดสุดสัปดาห์” ไม่ถือว่าระบบล่ม)</p>
          </Block>

          <Block title="ความขัดแย้งและภูมิรัฐศาสตร์ (35%)">
            <p>ข่าวจาก GDELT, BBC World, Al Jazeera และ Reuters ถูกยุบรวมเป็น “เหตุการณ์” ตามหมวดความรุนแรงและประเทศที่เกี่ยวข้อง คะแนนขึ้นกับระดับความรุนแรงและจำนวนสำนักข่าวที่ยืนยัน — ไม่ใช่จำนวนบทความ ข่าวซ้ำ 50 ชิ้นจึงมีน้ำหนักเท่าข่าวเดียว</p>
            <p>หมวดรุนแรงสูง (นิวเคลียร์ ช่องแคบ ฯลฯ) ต้องปรากฏในพาดหัวข่าว เหตุการณ์ที่ยังไม่ยุติถูกจดจำข้ามรอบและลดน้ำหนักลง {Math.round(c.decay_per_day * 100)}% ต่อวันหากไม่มีรายงานใหม่</p>
          </Block>

          <Block title="ภัยธรรมชาติ (15%)">
            <p>USGS (แผ่นดินไหว M6.0+) และ GDACS (ระดับเตือนเขียว/ส้ม/แดง) ผ่านตัวกรอง 2 ขั้น: เหตุที่อยู่ห่างจุดยุทธศาสตร์โลกเกิน {c.hub_radius_km} กม. และไม่มีสึนามิข้ามภูมิภาค ถูกจำกัดไว้ที่ {c.local_cap}/100 (กระทบคะแนนโลกไม่เกิน {(c.local_cap * w.nat).toFixed(1)} แต้ม)</p>
            <p>จุดยุทธศาสตร์: {c.strategic_hubs.join(", ")}</p>
          </Block>

          <Block title="สุขภาพและโครงสร้างพื้นฐาน (15%)">
            <p>WHO Disease Outbreak News และ CISA Cybersecurity Alerts แยก “ประกาศช่องโหว่ทั่วไป” (น้ำหนักต่ำมาก) ออกจาก “การระบาด/การโจมตีที่เกิดขึ้นจริง” เหตุที่จำกัดอยู่ในประเทศเดียวมีเพดาน {c.single_country_cap}/100</p>
          </Block>

          <Block title="บทบาทของ AI">
            <p>ตัวเลขทุกตัวคำนวณด้วย Python แบบ Deterministic — Gemini ใช้เพียงเขียนข้อความสรุปภาษาไทยจากตัวเลขและข่าวที่ระบบคัดแล้ว และเรียกเฉพาะเมื่อมีเหตุการณ์ใหม่ (ไม่เกิน 1 ครั้งต่อรอบ) หากไม่มี API Key ระบบใช้เทมเพลตภาษาไทยแทนได้ทันที</p>
          </Block>

          <Block title="ข้อจำกัด">
            <ul className="list-disc space-y-1 pl-5">
              <li>การจัดหมวดข่าวใช้คำสำคัญภาษาอังกฤษ อาจจัดผิดหมวดหรือพลาดเหตุการณ์ที่ใช้ถ้อยคำต่างไป</li>
              <li>ดัชนีสะท้อนผลกระทบเชิงระบบต่อโลก ไม่ใช่ความรุนแรงต่อชีวิตในพื้นที่ใดพื้นที่หนึ่ง</li>
              <li>อัปเดตทุก 6 ชั่วโมง ไม่ใช่ระบบเตือนภัยแบบเรียลไทม์ และไม่ใช่คำแนะนำการลงทุน</li>
              <li>สัญญาณเตือนล่วงหน้าเป็นการสรุปจากข่าว ไม่ใช่การพยากรณ์เชิงความน่าจะเป็น</li>
            </ul>
          </Block>

          <div className="min-w-0 md:col-span-2">
            <h3 className="mb-2 font-semibold text-zinc-200">สถานะแหล่งข้อมูลรอบล่าสุด</h3>
            <div className="overflow-x-auto rounded-lg border border-zinc-800">
              <table className="w-full min-w-[480px] text-sm">
                <thead className="bg-zinc-900/60 text-left text-[11px] text-zinc-500">
                  <tr>
                    <th className="px-3 py-2 font-normal">แหล่ง</th>
                    <th className="px-3 py-2 font-normal">สถานะ</th>
                    <th className="px-3 py-2 text-right font-normal">รายการ</th>
                    <th className="px-3 py-2 font-normal">เวลา (ไทย)</th>
                  </tr>
                </thead>
                <tbody>
                  {state.data_status.sources.map((s) => (
                    <tr key={s.name} className="border-t border-zinc-800/70">
                      <td className="px-3 py-1.5 text-zinc-300">{s.name}</td>
                      <td className={`px-3 py-1.5 ${s.status === "ok" ? "text-emerald-300" : "text-amber-300"}`} title={s.error ?? undefined}>
                        {s.status === "ok" ? "✓ ปกติ" : "✕ ไม่ตอบสนอง"}
                      </td>
                      <td className="num px-3 py-1.5 text-right text-zinc-400">{s.items ?? "—"}</td>
                      <td className="num px-3 py-1.5 text-zinc-500">{fmtThaiDate(s.fetched_at)}</td>
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
