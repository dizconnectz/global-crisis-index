import { readFileSync } from "node:fs";
import path from "node:path";
import { Header } from "@/components/Header";
import { HeroGauge } from "@/components/HeroGauge";
import { Watchlist } from "@/components/Watchlist";
import { Pillars } from "@/components/Pillars";
import { LocalNotes } from "@/components/LocalNotes";
import { Methodology } from "@/components/Methodology";
import type { HistoryPoint, LatestState } from "@/lib/types";

// Data is baked in at build time; the workflow rebuilds after every update.
function load<T>(file: string, fallback: T): T {
  try {
    return JSON.parse(readFileSync(path.join(process.cwd(), "public", "data", file), "utf-8")) as T;
  } catch {
    return fallback;
  }
}

export default function Home() {
  const state = load<LatestState | null>("latest_state.json", null);
  const history = load<HistoryPoint[]>("history.json", []);

  if (!state) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-24 text-center text-zinc-400">
        ยังไม่มีข้อมูล — รัน <code className="text-zinc-200">python scripts/update_index.py</code> ก่อน
      </main>
    );
  }

  return (
    <>
      <Header state={state} />
      <main className="mx-auto max-w-5xl space-y-10 px-4 pb-16 pt-6 sm:space-y-12">
        <HeroGauge state={state} history={history} />
        <Watchlist warnings={state.summary.early_warnings_th} source={state.summary.source} />
        <Pillars state={state} />
        <LocalNotes events={state.local_events} notes={state.summary.local_notes_th} localCap={state.config.local_cap} />
        <Methodology state={state} />
      </main>
      <footer className="border-t border-zinc-800/80 py-6 text-center text-xs text-zinc-500">
        Global Crisis Index · ข้อมูลจาก Yahoo Finance, FRED, GDELT, BBC, Al Jazeera, Reuters, USGS, GDACS, WHO, CISA ·
        ไม่ใช่คำแนะนำการลงทุน
      </footer>
    </>
  );
}
