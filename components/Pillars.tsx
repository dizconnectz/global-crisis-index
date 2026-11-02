import { Biohazard, CalendarOff, ChartLine, ChevronDown, CircleCheck, CircleSlash, Clock, Swords, Tornado, TriangleAlert } from "lucide-react";
import type { LatestState, Pillar, PillarKey, Status } from "@/lib/types";
import { BAND_HEX, bandOf, fmtNumber, fmtPct } from "@/lib/format";

const ORDER: PillarKey[] = ["econ", "geo", "nat", "bio_infra"];
const ICON = { econ: ChartLine, geo: Swords, nat: Tornado, bio_infra: Biohazard } as const;

const STATUS: Record<Status, { Icon: typeof CircleCheck; cls: string }> = {
  ok: { Icon: CircleCheck, cls: "text-emerald-300" },
  market_closed: { Icon: CalendarOff, cls: "text-sky-300" },
  partial: { Icon: TriangleAlert, cls: "text-amber-300" },
  stale: { Icon: Clock, cls: "text-amber-300" },
  degraded: { Icon: CircleSlash, cls: "text-red-300" },
};

function ScoreBar({ score }: { score: number | null }) {
  const b = bandOf(score);
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
      {score !== null && (
        <div className="h-full rounded-full" style={{ width: `${Math.max(1.5, score)}%`, background: b ? BAND_HEX[b.key] : "#71717a" }} />
      )}
    </div>
  );
}

function EconTable({ p }: { p: Pillar }) {
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">ตัวชี้วัดเศรษฐกิจ</caption>
      <thead>
        <tr className="text-left text-[11px] text-zinc-500">
          <th className="pb-1 font-normal">ตัวชี้วัด</th>
          <th className="pb-1 text-right font-normal">ล่าสุด</th>
          <th className="pb-1 text-right font-normal">5 วันทำการ</th>
          <th className="pb-1 text-right font-normal">คะแนน</th>
        </tr>
      </thead>
      <tbody>
        {p.indicators!.map((i) => (
          <tr key={i.key} className="border-t border-zinc-800/70">
            <td className="py-1.5 pr-2 text-zinc-300">
              {i.label_th}
              {i.status !== "ok" && (
                <span className="ml-1 text-[10px] text-amber-400/90">
                  {i.status === "stale" ? "(ค่าเดิม)" : i.status === "missing" ? "(ขาดหาย)" : i.status === "market_closed" ? "(ปิดตลาด)" : ""}
                </span>
              )}
            </td>
            <td className="num py-1.5 text-right text-zinc-200">{fmtNumber(i.value)}</td>
            <td className="num py-1.5 text-right text-zinc-400">{fmtPct(i.change_pct)}</td>
            <td className="num py-1.5 text-right text-zinc-400">{i.score === null ? "—" : Math.round(i.score)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PillarCard({ k, p }: { k: PillarKey; p: Pillar }) {
  const Icon = ICON[k];
  const st = STATUS[p.status];
  return (
    <article className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Icon className="h-5 w-5 shrink-0 text-zinc-400" aria-hidden />
          <div>
            <h3 className="font-semibold leading-tight text-zinc-100">{p.label_th}</h3>
            <div className="num text-[11px] text-zinc-500">
              น้ำหนัก {Math.round(p.weight * 100)}%
              {p.effective_weight !== null && Math.abs(p.effective_weight - p.weight) > 0.001 && ` → ${Math.round(p.effective_weight * 100)}%`}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="num text-3xl font-bold leading-none text-zinc-50">{p.score === null ? "—" : Math.round(p.score)}</div>
          <div className={`mt-1 inline-flex items-center gap-1 text-[11px] ${st.cls}`} title={p.note ?? undefined}>
            <st.Icon className="h-3 w-3" aria-hidden />
            {p.status_th}
          </div>
        </div>
      </div>

      <div className="mt-3">
        <ScoreBar score={p.score} />
      </div>

      <div className="mt-4 flex-1">
        {k === "econ" && p.indicators ? (
          <EconTable p={p} />
        ) : (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-sm">
            {p.metrics.map((m) => (
              <div key={m.label_th}>
                <dt className="text-[11px] text-zinc-500">{m.label_th}</dt>
                <dd className="text-zinc-200">
                  <span className="num font-medium">{fmtNumber(m.value)}</span> <span className="text-xs text-zinc-500">{m.unit}</span>
                  {m.hint && <div className="text-[11px] text-zinc-500">{m.hint}</div>}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      {p.top_events.length > 0 && (
        <details className="group mt-4 border-t border-zinc-800 pt-3">
          <summary className="flex cursor-pointer items-center justify-between text-xs text-zinc-400 hover:text-zinc-200">
            เหตุการณ์ที่มีน้ำหนักสูงสุด ({p.top_events.length})
            <ChevronDown className="chev h-4 w-4 transition-transform" aria-hidden />
          </summary>
          <ul className="mt-3 space-y-3">
            {p.top_events.map((e) => (
              <li key={e.id} className="text-sm">
                <div className="flex items-center justify-between gap-2 text-[11px] text-zinc-500">
                  <span>{e.category_th}</span>
                  <span className="num">
                    {Math.round(e.score)} คะแนน · {e.sources.length} แหล่ง
                    {e.article_count > 1 && ` · ${e.article_count} ข่าว`}
                  </span>
                </div>
                {e.links[0] ? (
                  <a href={e.links[0]} target="_blank" rel="noopener noreferrer" className="break-words text-zinc-300 underline-offset-2 hover:underline">
                    {e.title}
                  </a>
                ) : (
                  <span className="break-words text-zinc-300">{e.title}</span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

export function Pillars({ state }: { state: LatestState }) {
  return (
    <section aria-labelledby="pillars-title">
      <h2 id="pillars-title" className="text-lg font-semibold text-zinc-100">
        4 เสาหลักของดัชนี
      </h2>
      <p className="mb-4 text-sm text-zinc-500">คะแนนย่อย 0-100 ต่อหมวด พร้อมค่าตัวชี้วัดจริงที่ใช้คำนวณ</p>
      <div className="grid gap-3 md:grid-cols-2">
        {ORDER.map((k) => (
          <PillarCard key={k} k={k} p={state.pillars[k]} />
        ))}
      </div>
    </section>
  );
}
