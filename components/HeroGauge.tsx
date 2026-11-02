import { Zap } from "lucide-react";
import type { HistoryPoint, LatestState } from "@/lib/types";
import { BAND_HEX, BANDS, bandOf } from "@/lib/format";
import { BandIcon } from "./BandIcon";
import { Sparkline } from "./Sparkline";

export function HeroGauge({ state, history }: { state: LatestState; history: HistoryPoint[] }) {
  const score = state.global_score;
  const band = bandOf(score);
  const hex = band ? BAND_HEX[band.key] : "#71717a";
  const f = state.formula;

  return (
    <section aria-labelledby="hero-title" className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 sm:p-8">
      <h2 id="hero-title" className="sr-only">
        ดัชนีวิกฤตโลกปัจจุบัน
      </h2>

      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-sm font-medium text-zinc-400">ระดับผลกระทบเชิงระบบต่อโลก</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="num text-7xl font-bold leading-none text-zinc-50 sm:text-8xl">{score ?? "—"}</span>
            <span className="num text-xl text-zinc-500">/100</span>
          </div>
          {band ? (
            <div
              className="mt-3 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium text-zinc-100"
              style={{ borderColor: `${hex}66`, background: `${hex}1f` }}
            >
              <BandIcon band={band.key} className="h-4 w-4" />
              <span style={{ color: hex }}>●</span>
              {band.label_th}
            </div>
          ) : (
            <div className="mt-3 text-sm text-zinc-400">ข้อมูลไม่พอสำหรับคำนวณ (ไม่แสดงเป็น 0)</div>
          )}
        </div>
        <div className="w-full md:w-80">
          <Sparkline history={history} />
        </div>
      </div>

      {/* segmented gauge */}
      <div className="mt-8">
        <div className="relative">
          <div className="flex h-3 gap-[2px] overflow-hidden rounded-full">
            {BANDS.map((b) => {
              const active = band?.key === b.key;
              return (
                <div
                  key={b.key}
                  className="h-full transition-opacity"
                  style={{
                    width: `${((b.max - (b.min === 0 ? 0 : b.min - 1)) / 100) * 100}%`,
                    background: BAND_HEX[b.key],
                    opacity: active ? 1 : 0.28,
                  }}
                />
              );
            })}
          </div>
          {score !== null && (
            <div
              className="absolute -top-1.5 h-6 w-1.5 -translate-x-1/2 rounded-full bg-zinc-50 ring-2 ring-zinc-950"
              style={{ left: `${score}%` }}
              aria-hidden
            />
          )}
        </div>
        <div className="num relative mt-2 h-4 text-[11px] text-zinc-500">
          {[0, 20, 45, 70, 100].map((t) => (
            <span
              key={t}
              className="absolute"
              style={{ left: `${t}%`, transform: t === 0 ? "none" : t === 100 ? "translateX(-100%)" : "translateX(-50%)" }}
            >
              {t}
            </span>
          ))}
        </div>
        <div className="mt-3 hidden grid-cols-4 gap-2 text-[11px] leading-snug text-zinc-500 sm:grid">
          {BANDS.map((b) => (
            <div key={b.key} className={band?.key === b.key ? "text-zinc-200" : ""}>
              <span className="num">
                {b.min}-{b.max}
              </span>{" "}
              {b.label_th}
            </div>
          ))}
        </div>
      </div>

      <p className="mt-7 max-w-3xl text-[15px] text-zinc-300 sm:text-base">{state.summary.executive_summary_th}</p>

      {state.top_drivers.length > 0 && (
        <div className="mt-5">
          <div className="mb-2 text-xs font-medium text-zinc-500">ปัจจัยขับเคลื่อนหลัก</div>
          <ul className="flex flex-wrap gap-2">
            {state.top_drivers.map((d) => {
              const b = bandOf(d.score);
              return (
                <li
                  key={d.pillar}
                  className="inline-flex max-w-full items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-1.5 text-sm"
                  title={d.headline ?? undefined}
                >
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: b ? BAND_HEX[b.key] : "#71717a" }} />
                  <span className="truncate text-zinc-200">{d.label_th}</span>
                  <span className="num text-xs text-zinc-500">+{d.contribution.toFixed(1)}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500">
        <span className="num">
          คะแนนฐาน {f.base?.toFixed(1) ?? "—"} + ตัวเร่ง {f.boost?.toFixed(1) ?? "—"}
        </span>
        <span className="inline-flex items-center gap-1">
          <Zap className={`h-3.5 w-3.5 ${f.cross_confirmed ? "text-orange-400" : "text-zinc-600"}`} aria-hidden />
          {f.cross_confirmed ? "วิกฤตยืนยันข้ามหมวด — ตัวเร่งเชิงระบบทำงาน" : "ยังไม่มีการยืนยันข้ามหมวด (ตัวเร่งจำกัด ≤ 15)"}
        </span>
        <span>
          ข้อความสรุปโดย{" "}
          {state.summary.source === "template" ? "เทมเพลตอัตโนมัติ" : `Gemini${state.summary.source === "gemini_cached" ? " (รอบก่อน)" : ""}`}
          {" "}· ตัวเลขทั้งหมดคำนวณด้วยสูตรตายตัว
        </span>
      </div>
    </section>
  );
}
