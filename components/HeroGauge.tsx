"use client";

import { Zap } from "lucide-react";
import type { HistoryPoint, LatestState } from "@/lib/types";
import { BAND_HEX, BANDS, bandOf } from "@/lib/format";
import { useLang } from "@/lib/i18n";
import { BandIcon } from "./BandIcon";
import { Sparkline } from "./Sparkline";

export function HeroGauge({ state, history }: { state: LatestState; history: HistoryPoint[] }) {
  const { t, pick } = useLang();
  const score = state.global_score;
  const band = bandOf(score);
  const hex = band ? BAND_HEX[band.key] : "#71717a";
  const f = state.formula;
  const src = state.summary.source;

  return (
    <section aria-labelledby="hero-title" className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-8">
      <h2 id="hero-title" className="sr-only">
        {t("heroSr")}
      </h2>

      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-sm font-medium text-zinc-600">{t("heroLabel")}</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="num text-7xl font-bold leading-none text-zinc-900 sm:text-8xl">{score ?? "—"}</span>
            <span className="num text-xl text-zinc-500">/100</span>
          </div>
          {band ? (
            <div
              className="mt-3 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium text-zinc-900"
              style={{ borderColor: `${hex}66`, background: `${hex}14` }}
            >
              <BandIcon band={band.key} className="h-4 w-4" />
              <span style={{ color: hex }}>●</span>
              {pick(band, "label")}
            </div>
          ) : (
            <div className="mt-3 text-sm text-zinc-600">{t("noScore")}</div>
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
                    width: `${b.max - (b.min === 0 ? 0 : b.min - 1)}%`,
                    background: BAND_HEX[b.key],
                    opacity: active ? 1 : 0.25,
                  }}
                />
              );
            })}
          </div>
          {score !== null && (
            <div
              className="absolute -top-1.5 h-6 w-1.5 -translate-x-1/2 rounded-full bg-zinc-900 ring-2 ring-white"
              style={{ left: `${score}%` }}
              aria-hidden
            />
          )}
        </div>
        <div className="num relative mt-2 h-4 text-[11px] text-zinc-500">
          {[0, 20, 45, 70, 100].map((v) => (
            <span
              key={v}
              className="absolute"
              style={{ left: `${v}%`, transform: v === 0 ? "none" : v === 100 ? "translateX(-100%)" : "translateX(-50%)" }}
            >
              {v}
            </span>
          ))}
        </div>
        <div className="mt-3 hidden grid-cols-4 gap-2 text-[11px] leading-snug text-zinc-500 sm:grid">
          {BANDS.map((b) => (
            <div key={b.key} className={band?.key === b.key ? "font-medium text-zinc-900" : ""}>
              <span className="num">
                {b.min}-{b.max}
              </span>{" "}
              {pick(b, "label")}
            </div>
          ))}
        </div>
      </div>

      <p className="mt-7 max-w-3xl text-[15px] text-zinc-700 sm:text-base">{pick(state.summary, "executive_summary")}</p>

      {state.top_drivers.length > 0 && (
        <div className="mt-5">
          <div className="mb-2 text-xs font-medium text-zinc-500">{t("drivers")}</div>
          <ul className="flex flex-wrap gap-2">
            {state.top_drivers.map((d) => {
              const b = bandOf(d.score);
              return (
                <li
                  key={d.pillar}
                  className="inline-flex max-w-full items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-sm"
                  title={pick(d, "headline") || undefined}
                >
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: b ? BAND_HEX[b.key] : "#71717a" }} />
                  <span className="truncate text-zinc-800">{pick(d, "label")}</span>
                  <span className="num text-xs text-zinc-500">+{d.contribution.toFixed(1)}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500">
        <span className="num">{t("baseBoost", { b: f.base?.toFixed(1) ?? "—", x: f.boost?.toFixed(1) ?? "—" })}</span>
        <span className="inline-flex items-center gap-1">
          <Zap className={`h-3.5 w-3.5 ${f.cross_confirmed ? "text-orange-500" : "text-zinc-400"}`} aria-hidden />
          {f.cross_confirmed ? t("crossOn") : t("crossOff")}
        </span>
        <span>
          {t("summaryBy")} {src === "template" ? t("byTemplate") : `Gemini${src === "gemini_cached" ? t("prevRun") : ""}`} ·{" "}
          {t("deterministic")}
        </span>
      </div>
    </section>
  );
}
