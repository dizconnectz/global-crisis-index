"use client";

import { useEffect, useState } from "react";
import type { SourceStatus } from "@/lib/types";
import { fmtAsOf, fmtDate, relativeParts } from "@/lib/format";
import { useLang } from "@/lib/i18n";

const DAY_ONLY = /^\d{4}-\d{2}-\d{2}$/;

export function DataFreshness({ sources }: { sources: SourceStatus[] }) {
  const { lang, t } = useLang();
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => setNow(Date.now()), []);

  const age = (iso: string) => {
    if (now === null) return "";
    const r = relativeParts(iso, now);
    return t(r.key, { n: r.n });
  };

  return (
    <section aria-labelledby="fresh-h">
      <h2 id="fresh-h" className="text-base font-semibold text-zinc-900">{t("freshTitle")}</h2>
      <p className="mt-1 text-xs text-zinc-500">{t("freshSub")}</p>
      <div className="mt-3 overflow-x-auto rounded-xl border border-zinc-200 bg-white shadow-sm">
        <table className="w-full min-w-[34rem] text-left text-sm">
          <thead className="text-xs text-zinc-500">
            <tr>
              <th className="px-3 py-2 font-medium">{t("freshSource")}</th>
              <th className="px-3 py-2 font-medium">{t("freshLatest")}</th>
              <th className="px-3 py-2 font-medium">{t("freshFetched")}</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.name} className="border-t border-zinc-200 align-top">
                <td className="px-3 py-2 text-zinc-900">{s.name}</td>
                <td className="px-3 py-2 text-zinc-700">
                  {s.status !== "ok" ? (
                    <span className="text-amber-700">{t("freshFailed")}</span>
                  ) : s.data_as_of ? (
                    <>
                      {fmtAsOf(s.data_as_of, lang)}
                      {DAY_ONLY.test(s.data_as_of) ? (
                        <span className="text-zinc-500"> ({t("freshDailyClose")})</span>
                      ) : (
                        <span className="text-zinc-500" suppressHydrationWarning> · {age(s.data_as_of)}</span>
                      )}
                    </>
                  ) : (
                    <span className="text-zinc-500">{t("freshUnknown")}</span>
                  )}
                </td>
                <td className="px-3 py-2 text-zinc-700">{fmtDate(s.fetched_at, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
