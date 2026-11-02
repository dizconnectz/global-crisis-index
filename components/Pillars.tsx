"use client";

import { Biohazard, CalendarOff, ChartLine, ChevronDown, CircleCheck, CircleSlash, Clock, Swords, Tornado, TriangleAlert } from "lucide-react";
import type { LatestState, Pillar, PillarKey, Status } from "@/lib/types";
import { BAND_HEX, bandOf, fmtNumber, fmtPct } from "@/lib/format";
import { useLang } from "@/lib/i18n";

const ORDER: PillarKey[] = ["econ", "geo", "nat", "bio_infra"];
const ICON = { econ: ChartLine, geo: Swords, nat: Tornado, bio_infra: Biohazard } as const;

const STATUS: Record<Status, { Icon: typeof CircleCheck; cls: string }> = {
  ok: { Icon: CircleCheck, cls: "text-emerald-700" },
  market_closed: { Icon: CalendarOff, cls: "text-sky-700" },
  partial: { Icon: TriangleAlert, cls: "text-amber-700" },
  stale: { Icon: Clock, cls: "text-amber-700" },
  degraded: { Icon: CircleSlash, cls: "text-red-700" },
};

function ScoreBar({ score }: { score: number | null }) {
  const b = bandOf(score);
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-200">
      {score !== null && (
        <div className="h-full rounded-full" style={{ width: `${Math.max(1.5, score)}%`, background: b ? BAND_HEX[b.key] : "#71717a" }} />
      )}
    </div>
  );
}

function EconTable({ p }: { p: Pillar }) {
  const { lang, t, pick } = useLang();
  const tag = (s: string) =>
    s === "stale" ? t("indStale") : s === "missing" ? t("indMissing") : s === "market_closed" ? t("indClosed") : "";
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">{pick(p, "label")}</caption>
      <thead>
        <tr className="text-left text-[11px] text-zinc-500">
          <th className="pb-1 font-normal">{t("colIndicator")}</th>
          <th className="pb-1 text-right font-normal">{t("colLatest")}</th>
          <th className="pb-1 text-right font-normal">{t("col5d")}</th>
          <th className="pb-1 text-right font-normal">{t("colScore")}</th>
        </tr>
      </thead>
      <tbody>
        {p.indicators!.map((i) => (
          <tr key={i.key} className="border-t border-zinc-200">
            <td className="py-1.5 pr-2 text-zinc-700">
              {pick(i, "label")}
              {i.status !== "ok" && <span className="ml-1 text-[10px] text-amber-700">{tag(i.status)}</span>}
            </td>
            <td className="num py-1.5 text-right text-zinc-800">{fmtNumber(i.value, lang)}</td>
            <td className="num py-1.5 text-right text-zinc-600">{fmtPct(i.change_pct)}</td>
            <td className="num py-1.5 text-right text-zinc-600">{i.score === null ? "—" : Math.round(i.score)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PillarCard({ k, p }: { k: PillarKey; p: Pillar }) {
  const { lang, t, pick } = useLang();
  const Icon = ICON[k];
  const st = STATUS[p.status];
  return (
    <article className="flex flex-col rounded-xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Icon className="h-5 w-5 shrink-0 text-zinc-600" aria-hidden />
          <div>
            <h3 className="font-semibold leading-tight text-zinc-900">{pick(p, "label")}</h3>
            <div className="num text-[11px] text-zinc-500">
              {t("weight")} {Math.round(p.weight * 100)}%
              {p.effective_weight !== null && Math.abs(p.effective_weight - p.weight) > 0.001 && ` → ${Math.round(p.effective_weight * 100)}%`}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="num text-3xl font-bold leading-none text-zinc-900">{p.score === null ? "—" : Math.round(p.score)}</div>
          <div className={`mt-1 inline-flex items-center gap-1 text-[11px] ${st.cls}`} title={p.note ?? undefined}>
            <st.Icon className="h-3 w-3" aria-hidden />
            {pick(p, "status")}
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
              <div key={m.key ?? m.label_th}>
                <dt className="text-[11px] text-zinc-500">{pick(m, "label")}</dt>
                <dd className="text-zinc-800">
                  <span className="num font-medium">{fmtNumber(m.value, lang)}</span>{" "}
                  <span className="text-xs text-zinc-500">{pick(m, "unit")}</span>
                  {m.hint && <div className="text-[11px] text-zinc-500">{pick(m, "hint")}</div>}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      {p.top_events.length > 0 && (
        <details className="group mt-4 border-t border-zinc-200 pt-3">
          <summary className="flex cursor-pointer items-center justify-between text-xs text-zinc-600 hover:text-zinc-900">
            {t("topEvents")} ({p.top_events.length})
            <ChevronDown className="chev h-4 w-4 transition-transform" aria-hidden />
          </summary>
          <ul className="mt-3 space-y-3">
            {p.top_events.map((e) => (
              <li key={e.id} className="text-sm">
                <div className="flex items-center justify-between gap-2 text-[11px] text-zinc-500">
                  <span>{pick(e, "category")}</span>
                  <span className="num">
                    {t("evMeta", { s: Math.round(e.score), n: e.sources.length })}
                    {e.article_count > 1 && t("evArticles", { n: e.article_count })}
                  </span>
                </div>
                {e.links[0] ? (
                  <a href={e.links[0]} target="_blank" rel="noopener noreferrer" className="break-words text-zinc-700 underline-offset-2 hover:underline">
                    {e.title}
                  </a>
                ) : (
                  <span className="break-words text-zinc-700">{e.title}</span>
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
  const { t } = useLang();
  return (
    <section aria-labelledby="pillars-title">
      <h2 id="pillars-title" className="text-lg font-semibold text-zinc-900">
        {t("pillarsTitle")}
      </h2>
      <p className="mb-4 text-sm text-zinc-500">{t("pillarsSub")}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {ORDER.map((k) => (
          <PillarCard key={k} k={k} p={state.pillars[k]} />
        ))}
      </div>
    </section>
  );
}
