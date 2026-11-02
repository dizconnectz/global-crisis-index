"use client";

import { useMemo, useRef, useState } from "react";
import type { HistoryPoint } from "@/lib/types";
import { BAND_HEX, bandOf, fmtDate } from "@/lib/format";
import { useLang } from "@/lib/i18n";

const W = 320;
const H = 88;
const PAD = { t: 6, b: 6, l: 2, r: 2 };

export function Sparkline({ history }: { history: HistoryPoint[] }) {
  const { lang, t } = useLang();
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
    return <div className="text-xs text-zinc-500">{t("noHistory")}</div>;
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
        <span>{t("trend")}</span>
        {pts.length > 1 && (
          <span className="num text-zinc-600">
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
          aria-label={t("chartAria", { n: history.length, s: last.h.score })}
        >
          {[20, 45, 70].map((t) => (
            <line key={t} x1={0} x2={W} y1={yOf(t)} y2={yOf(t)} stroke="#e4e4e7" strokeDasharray="2 4" strokeWidth={1} />
          ))}
          {pts.length > 1 && (
            <path d={d} fill="none" stroke="#3f3f46" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          )}
          {active && <line x1={active.x} x2={active.x} y1={0} y2={H} stroke="#a1a1aa" strokeWidth={1} vectorEffect="non-scaling-stroke" />}
          {(active ? [active] : [last]).map((p) => {
            const b = bandOf(p.h.score);
            return (
              <circle key="dot" cx={p.x} cy={p.y} r={4.5} fill={b ? BAND_HEX[b.key] : "#a1a1aa"} stroke="#ffffff" strokeWidth={2} />
            );
          })}
        </svg>
        {active && (
          <div
            className="pointer-events-none absolute -top-2 z-10 -translate-y-full whitespace-nowrap rounded-md border border-zinc-300 bg-white px-2.5 py-1.5 text-xs shadow-md"
            style={{ left: `${(active.x / W) * 100}%`, transform: `translate(${active.x > W * 0.6 ? "-100%" : active.x < W * 0.2 ? "0" : "-50%"}, -100%)` }}
          >
            <div className="num text-sm font-bold text-zinc-900">{active.h.score}</div>
            <div className="text-zinc-600">{fmtDate(active.h.t, lang)}</div>
          </div>
        )}
      </div>
      {pts.length < 3 && <div className="mt-1 text-[11px] text-zinc-500">{t("accumulating")}</div>}
    </figure>
  );
}
