import { readFileSync } from "node:fs";
import path from "node:path";
import { Dashboard } from "@/components/Dashboard";
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
  return <Dashboard state={state} history={history} />;
}
