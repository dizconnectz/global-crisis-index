"use client";

import { MapPin } from "lucide-react";
import type { EventItem } from "@/lib/types";
import { useLang } from "@/lib/i18n";

export function LocalNotes({ events, notes, localCap }: { events: EventItem[]; notes: string[]; localCap: number }) {
  const { t, pick } = useLang();
  return (
    <section aria-labelledby="local-title">
      <h2 id="local-title" className="flex items-center gap-2 text-lg font-semibold text-zinc-900">
        <MapPin className="h-5 w-5 text-zinc-600" aria-hidden />
        {t("localTitle")}
      </h2>
      <p className="mb-4 text-sm text-zinc-500">{t("localSub", { cap: localCap })}</p>

      {events.length === 0 && notes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500">{t("noLocal")}</div>
      ) : (
        <div className="space-y-3">
          {notes.length > 0 && (
            <ul className="space-y-2 rounded-xl border border-zinc-200 bg-white p-4 text-sm text-zinc-700 shadow-sm">
              {notes.map((n, i) => (
                <li key={i} className="flex gap-2">
                  <span className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-zinc-400" />
                  {n}
                </li>
              ))}
            </ul>
          )}
          {events.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white">
              <table className="w-full min-w-[520px] text-sm">
                <thead className="bg-zinc-50 text-left text-[11px] text-zinc-500">
                  <tr>
                    <th className="px-3 py-2 font-normal">{t("colEvent")}</th>
                    <th className="px-3 py-2 font-normal">{t("colType")}</th>
                    <th className="px-3 py-2 text-right font-normal">{t("colActual")}</th>
                    <th className="px-3 py-2 text-right font-normal">{t("colCounted")}</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.id} className="border-t border-zinc-200">
                      <td className="px-3 py-2 text-zinc-700">
                        {e.links[0] ? (
                          <a href={e.links[0]} target="_blank" rel="noopener noreferrer" className="hover:underline">
                            {e.title}
                          </a>
                        ) : (
                          e.title
                        )}
                        {e.location && <div className="text-[11px] text-zinc-500">{pick(e, "location")}</div>}
                      </td>
                      <td className="px-3 py-2 text-zinc-600">{pick(e, "category")}</td>
                      <td className="num px-3 py-2 text-right text-zinc-700">{e.raw_score === null ? "—" : Math.round(e.raw_score)}</td>
                      <td className="num px-3 py-2 text-right text-zinc-600">{Math.round(e.score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
