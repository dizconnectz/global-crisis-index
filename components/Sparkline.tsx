"use client";

import { useMemo, useRef, useState } from "react";
import type { HistoryPoint } from "@/lib/types";
import { BAND_HEX, bandOf, fmtThaiDate } from "@/lib/format";

const W = 320;
const H = 88;
const PAD = { t: 6, b: 6, l: 2, r: 2 };

export function Sparkline({ history }: { history: HistoryPoint[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const pts = useMemo(() => {
    if (history.length === 0) return [];
    const t0 = new Date(history[0].t).getTime();
    const t1 = new Date(history[history.length - 1].t).getTime();
    const span = Math.max(1, t1 - t0);
    return history.map((h) => ({
      x: history.length === 1 ? W - PAD.r : PAD.l + ((new Date(h.t).getTime() - t0) / span) * (W - PAD.l - PAD.r),
      // fixed 0-100 domain: the line's height means the same thing every day
      y: PAD.t + (1 - h.score / 100) * (H - PAD.t - PAD.b),
      h,
    }));
  }, [history]);

  if (pts.length === 0) {
    return <div className="text-xs text-zinc-500">ยังไม่มีประวัติคะแนน</div>;
  }

  const last = pts[pts.length - 1];
  const d = pts.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const active = hover !== null ? pts[hover] : null;
  const yOf = (v: number) => PAD.t + (1 - v / 100) * (H - PAD.t - PAD.b);
  const first = history[0].score;
  const delta = last.h.score - first;

  function onMove(e: React.PointerEvent<SVGSVGElement>) {
    const rect = svgRef.current!.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0;
    for (let i = 1; i < pts.length; i++) if (Math.abs(pts[i].x - x) < Math.abs(pts[best].x - x)) best = i;
    setHover(best);
  }

  return (
    <figure>
      <figcaption className="mb-1.5 flex items-baseline justify-between text-xs text-zinc-500">
        <span>แนวโน้มคะแนนย้อนหลัง (สูงสุด 90 วัน)</span>
        {pts.length > 1 && (
          <span className="num text-zinc-400">
            {delta > 0 ? "▲" : delta < 0 ? "▼" : "■"} {delta > 0 ? "+" : ""}
            {delta}
          </span>
        )}
      </figcaption>
      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          className="h-[88px] w-full touch-none overflow-visible"
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
          role="img"
          aria-label={`กราฟคะแนนย้อนหลัง ${history.length} จุด ล่าสุด ${last.h.score}`}
        >
          {[20, 45, 70].map((t) => (
            <line key={t} x1={0} x2={W} y1={yOf(t)} y2={yOf(t)} stroke="#27272a" strokeDasharray="2 4" strokeWidth={1} />
          ))}
          {pts.length > 1 && (
            <path d={d} fill="none" stroke="#d4d4d8" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          )}
          {active && <line x1={active.x} x2={active.x} y1={0} y2={H} stroke="#52525b" strokeWidth={1} vectorEffect="non-scaling-stroke" />}
          {(active ? [active] : [last]).map((p) => {
            const b = bandOf(p.h.score);
            return (
              <circle key="dot" cx={p.x} cy={p.y} r={4.5} fill={b ? BAND_HEX[b.key] : "#a1a1aa"} stroke="#18181b" strokeWidth={2} />
            );
          })}
        </svg>
        {active && (
          <div
            className="pointer-events-none absolute -top-2 z-10 -translate-y-full whitespace-nowrap rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 text-xs shadow-lg"
            style={{ left: `${(active.x / W) * 100}%`, transform: `translate(${active.x > W * 0.6 ? "-100%" : active.x < W * 0.2 ? "0" : "-50%"}, -100%)` }}
          >
            <div className="num text-sm font-bold text-zinc-100">{active.h.score}</div>
            <div className="text-zinc-400">{fmtThaiDate(active.h.t)}</div>
          </div>
        )}
      </div>
      {pts.length < 3 && <div className="mt-1 text-[11px] text-zinc-500">กำลังสะสมข้อมูล — กราฟจะสมบูรณ์ขึ้นหลังอัปเดตหลายรอบ</div>}
    </figure>
  );
}
