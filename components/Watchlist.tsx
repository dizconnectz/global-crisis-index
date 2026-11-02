import { Binoculars, CalendarRange, FileSearch, SignalHigh, SignalLow, SignalMedium } from "lucide-react";
import type { Signal, Warning } from "@/lib/types";

const SIGNAL: Record<Signal, { Icon: typeof SignalHigh; cls: string }> = {
  สูง: { Icon: SignalHigh, cls: "border-red-500/40 bg-red-500/10 text-red-300" },
  ปานกลาง: { Icon: SignalMedium, cls: "border-amber-500/40 bg-amber-500/10 text-amber-300" },
  เฝ้าระวัง: { Icon: SignalLow, cls: "border-zinc-600 bg-zinc-800/60 text-zinc-300" },
};

export function Watchlist({ warnings, source }: { warnings: Warning[]; source: string }) {
  return (
    <section aria-labelledby="watch-title">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="watch-title" className="flex items-center gap-2 text-lg font-semibold text-zinc-100">
            <Binoculars className="h-5 w-5 text-zinc-400" aria-hidden />
            สัญญาณเตือนล่วงหน้า
          </h2>
          <p className="text-sm text-zinc-500">สิ่งที่ควรจับตาใน 1-3 เดือนข้างหน้า — แยกจากคะแนนปัจจุบัน ไม่ถูกนำไปคำนวณดัชนี</p>
        </div>
        <span className="text-xs text-zinc-600">{source === "template" ? "สกัดด้วยกฎอัตโนมัติ" : "สกัดโดย AI จากข่าวที่ระบบส่งให้"}</span>
      </div>

      {warnings.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-800 p-6 text-center text-sm text-zinc-500">
          ไม่พบสัญญาณเตือนที่มีหลักฐานเพียงพอในรอบนี้
        </div>
      ) : (
        <ul className="grid gap-3 md:grid-cols-3">
          {warnings.map((w, i) => {
            const s = SIGNAL[w.signal_strength] ?? SIGNAL["เฝ้าระวัง"];
            return (
              <li key={i} className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${s.cls}`}>
                    <s.Icon className="h-3.5 w-3.5" aria-hidden />
                    สัญญาณ{w.signal_strength}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs text-zinc-500">
                    <CalendarRange className="h-3.5 w-3.5" aria-hidden />
                    {w.timeframe}
                  </span>
                </div>
                <h3 className="mt-3 font-semibold leading-snug text-zinc-100">{w.title}</h3>
                <p className="mt-2 flex gap-2 text-sm text-zinc-400">
                  <FileSearch className="mt-1 h-3.5 w-3.5 shrink-0 text-zinc-600" aria-hidden />
                  <span className="break-words">{w.evidence_summary}</span>
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
