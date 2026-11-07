"use client";

import { useEffect, useState } from "react";
import { Activity, CalendarOff, CircleCheck, Clock, TriangleAlert } from "lucide-react";
import type { LatestState } from "@/lib/types";
import { fmtDate, relativeParts } from "@/lib/format";
import { useLang, type Lang } from "@/lib/i18n";

// The workflow is scheduled every 6h, but GitHub throttles scheduled runs and in
// practice they land roughly every 11-13h. "Fresh" covers that real cadence;
// "late" allows one more missed run before the data is called stale.
const FRESH_H = 14;
const LATE_H = 26;

function LangToggle() {
  const { lang, setLang, t } = useLang();
  const opts: { v: Lang; label: string }[] = [
    { v: "th", label: "ไทย" },
    { v: "en", label: "EN" },
  ];
  return (
    <div role="group" aria-label={t("langLabel")} className="inline-flex rounded-full border border-zinc-300 bg-white p-0.5 text-xs">
      {opts.map((o) => (
        <button
          key={o.v}
          type="button"
          onClick={() => setLang(o.v)}
          aria-pressed={lang === o.v}
          className={`rounded-full px-2.5 py-0.5 font-medium transition-colors ${
            lang === o.v ? "bg-zinc-900 text-white" : "text-zinc-600 hover:text-zinc-900"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Header({ state }: { state: LatestState }) {
  const { lang, t, pick } = useLang();
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const rel = now === null ? null : relativeParts(state.generated_at, now);
  const relText = rel ? t(rel.key, { n: rel.n }) : "";
  const ageH = now === null ? null : (now - new Date(state.generated_at).getTime()) / 3_600_000;
  const fresh =
    ageH === null
      ? { cls: "text-zinc-600 border-zinc-300", label: fmtDate(state.generated_at, lang) }
      : ageH <= FRESH_H
        ? { cls: "text-emerald-700 border-emerald-500/30 bg-emerald-500/10", label: `${t("updated")} ${relText}` }
        : ageH <= LATE_H
          ? { cls: "text-amber-700 border-amber-500/30 bg-amber-500/10", label: `${t("delayed")} · ${relText}` }
          : { cls: "text-red-700 border-red-500/30 bg-red-500/10", label: `${t("staleData")} · ${relText}` };

  const ds = state.data_status;
  const srcBadge =
    ds.key === "ok"
      ? { Icon: CircleCheck, cls: "text-emerald-700 border-emerald-500/30 bg-emerald-500/10" }
      : ds.key === "market_closed"
        ? { Icon: CalendarOff, cls: "text-sky-700 border-sky-500/30 bg-sky-500/10" }
        : { Icon: TriangleAlert, cls: "text-amber-700 border-amber-500/30 bg-amber-500/10" };
  const failed = ds.sources.filter((s) => s.status !== "ok");

  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/85 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
        <div className="flex items-center gap-2.5">
          <Activity className="h-5 w-5 text-zinc-700" aria-hidden />
          <h1 className="text-[15px] font-bold tracking-[0.18em] text-zinc-900 sm:text-base">GLOBAL CRISIS INDEX</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${fresh.cls}`}
            title={`${t("generatedAt")} ${fmtDate(state.generated_at, lang)} ${t("localTime")}`}
          >
            <Clock className="h-3.5 w-3.5" aria-hidden />
            <span suppressHydrationWarning>{fresh.label}</span>
          </span>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${srcBadge.cls}`}
            title={failed.length ? `${t("failedSources")}: ${failed.map((f) => f.name).join(", ")}` : t("allSourcesOk")}
          >
            <srcBadge.Icon className="h-3.5 w-3.5" aria-hidden />
            {t("sources")}: {pick(ds, "label")}
          </span>
          <LangToggle />
        </div>
      </div>
    </header>
  );
}
