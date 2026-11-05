"use client";

import type { HistoryPoint, LatestState } from "@/lib/types";
import { LangProvider, useLang } from "@/lib/i18n";
import { Header } from "./Header";
import { HeroGauge } from "./HeroGauge";
import { Watchlist } from "./Watchlist";
import { Pillars } from "./Pillars";
import { LocalNotes } from "./LocalNotes";
import { DataFreshness } from "./DataFreshness";

const SOURCES = "Yahoo Finance, FRED, GDELT, BBC, Al Jazeera, Reuters, USGS, GDACS, WHO, CISA";

function Body({ state, history }: { state: LatestState | null; history: HistoryPoint[] }) {
  const { lang, t } = useLang();

  if (!state) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-24 text-center text-zinc-600">
        {t("noData")} <code className="text-zinc-800">python scripts/update_index.py</code> {t("noDataAfter")}
      </main>
    );
  }

  const s = state.summary;
  const warnings = (lang === "en" && s.early_warnings_en?.length ? s.early_warnings_en : s.early_warnings_th) ?? [];
  const notes = (lang === "en" && s.local_notes_en ? s.local_notes_en : s.local_notes_th) ?? [];

  return (
    <>
      <Header state={state} />
      <main className="mx-auto max-w-5xl space-y-10 px-4 pb-16 pt-6 sm:space-y-12">
        <HeroGauge state={state} history={history} />
        <Watchlist warnings={warnings} source={s.source} />
        <Pillars state={state} />
        <LocalNotes events={state.local_events} notes={notes} localCap={state.config.local_cap} />
        <DataFreshness sources={state.data_status.sources} />
      </main>
      <footer className="border-t border-zinc-200 py-6 text-center text-xs text-zinc-500">
        Global Crisis Index · {t("dataFrom")} {SOURCES} · {t("notAdvice")}
        <div className="mt-1">
          © 2026 dizconnectz · {t("licenseNote")}{" "}
          <a
            href={`https://creativecommons.org/licenses/by/4.0/${lang === "th" ? "deed.th" : ""}`}
            className="underline hover:text-zinc-700"
            target="_blank"
            rel="noopener noreferrer"
          >
            CC BY 4.0
          </a>{" "}
          — {t("creditNote")}
        </div>
      </footer>
    </>
  );
}

export function Dashboard(props: { state: LatestState | null; history: HistoryPoint[] }) {
  return (
    <LangProvider>
      <Body {...props} />
    </LangProvider>
  );
}
