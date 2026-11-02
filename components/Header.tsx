"use client";

import { useEffect, useState } from "react";
import { Activity, CalendarOff, CircleCheck, Clock, TriangleAlert } from "lucide-react";
import type { LatestState } from "@/lib/types";
import { fmtThaiDate, relativeThai } from "@/lib/format";

// Pipeline runs every 6h; allow one missed run before calling data late.
const FRESH_H = 7;
const LATE_H = 13;

export function Header({ state }: { state: LatestState }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const ageH = now === null ? null : (now - new Date(state.generated_at).getTime()) / 3_600_000;
  const fresh =
    ageH === null
      ? { cls: "text-zinc-400 border-zinc-700", label: fmtThaiDate(state.generated_at) }
      : ageH <= FRESH_H
        ? { cls: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10", label: `อัปเดต ${relativeThai(state.generated_at, now!)}` }
        : ageH <= LATE_H
          ? { cls: "text-amber-300 border-amber-500/30 bg-amber-500/10", label: `ล่าช้า · ${relativeThai(state.generated_at, now!)}` }
          : { cls: "text-red-300 border-red-500/30 bg-red-500/10", label: `ข้อมูลเก่า · ${relativeThai(state.generated_at, now!)}` };

  const ds = state.data_status;
  const srcBadge =
    ds.key === "ok"
      ? { Icon: CircleCheck, cls: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10" }
      : ds.key === "market_closed"
        ? { Icon: CalendarOff, cls: "text-sky-300 border-sky-500/30 bg-sky-500/10" }
        : { Icon: TriangleAlert, cls: "text-amber-300 border-amber-500/30 bg-amber-500/10" };
  const failed = ds.sources.filter((s) => s.status !== "ok");

  return (
    <header className="sticky top-0 z-20 border-b border-zinc-800/80 bg-zinc-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
        <div className="flex items-center gap-2.5">
          <Activity className="h-5 w-5 text-zinc-300" aria-hidden />
          <h1 className="text-[15px] font-bold tracking-[0.18em] text-zinc-100 sm:text-base">GLOBAL CRISIS INDEX</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${fresh.cls}`}
            title={`สร้างข้อมูลเมื่อ ${fmtThaiDate(state.generated_at)} (เวลาไทย)`}
          >
            <Clock className="h-3.5 w-3.5" aria-hidden />
            <span suppressHydrationWarning>{fresh.label}</span>
          </span>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${srcBadge.cls}`}
            title={failed.length ? `แหล่งที่ไม่ตอบสนอง: ${failed.map((f) => f.name).join(", ")}` : "ทุกแหล่งข้อมูลตอบสนองปกติ"}
          >
            <srcBadge.Icon className="h-3.5 w-3.5" aria-hidden />
            แหล่งข้อมูล: {ds.label_th}
          </span>
        </div>
      </div>
    </header>
  );
}
