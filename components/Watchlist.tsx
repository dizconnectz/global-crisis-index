"use client";

import { Binoculars, CalendarRange, ExternalLink, FileSearch, SignalHigh, SignalLow, SignalMedium } from "lucide-react";
import type { Signal, Warning } from "@/lib/types";
import { useLang } from "@/lib/i18n";

const SIGNAL: Record<Signal, { Icon: typeof SignalHigh; cls: string }> = {
  สูง: { Icon: SignalHigh, cls: "border-red-500/40 bg-red-500/10 text-red-700" },
  ปานกลาง: { Icon: SignalMedium, cls: "border-amber-500/40 bg-amber-500/10 text-amber-700" },
  เฝ้าระวัง: { Icon: SignalLow, cls: "border-zinc-300 bg-zinc-100 text-zinc-700" },
};

export function Watchlist({ warnings, source }: { warnings: Warning[]; source: string }) {
  const { t } = useLang();
  return (
    <section aria-labelledby="watch-title">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="watch-title" className="flex items-center gap-2 text-lg font-semibold text-zinc-900">
            <Binoculars className="h-5 w-5 text-zinc-600" aria-hidden />
            {t("watchTitle")}
          </h2>
          <p className="text-sm text-zinc-500">{t("watchSub")}</p>
        </div>
        <span className="text-xs text-zinc-500">{source === "template" ? t("byRules") : t("byAI")}</span>
      </div>

      {warnings.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500">{t("noWarnings")}</div>
      ) : (
        <ul className="grid gap-3 md:grid-cols-3">
          {warnings.map((w, i) => {
            const sig: Signal = w.signal_strength in SIGNAL ? w.signal_strength : "เฝ้าระวัง";
            const s = SIGNAL[sig];
            return (
              <li key={i} className="flex flex-col rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${s.cls}`}>
                    <s.Icon className="h-3.5 w-3.5" aria-hidden />
                    {t(`sig_${sig}`)}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs text-zinc-500">
                    <CalendarRange className="h-3.5 w-3.5" aria-hidden />
                    {w.timeframe}
                  </span>
                </div>
                <h3 className="mt-3 font-semibold leading-snug text-zinc-900">{w.title}</h3>
                <p className="mt-2 flex gap-2 text-sm text-zinc-600">
                  <FileSearch className="mt-1 h-3.5 w-3.5 shrink-0 text-zinc-400" aria-hidden />
                  <span className="break-words">{w.evidence_summary}</span>
                </p>
                {(() => {
                  // URLs are filtered in the pipeline too; re-check so only web links render
                  const refs = (w.refs ?? []).filter((r) => /^https?:\/\//i.test(r.url));
                  return refs.length > 0 ? (
                    <div className="mt-auto pt-3">
                      <div className="mb-1 text-[11px] text-zinc-500">{t("readSources")}</div>
                      <ul className="flex flex-wrap gap-1.5">
                        {refs.map((r) => (
                          <li key={r.url}>
                            <a
                              href={r.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-md border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-xs text-zinc-700 hover:border-zinc-400 hover:text-zinc-900"
                            >
                              {r.source}
                              <ExternalLink className="h-3 w-3" aria-hidden />
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null;
                })()}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
