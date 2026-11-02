import { MapPin } from "lucide-react";
import type { EventItem } from "@/lib/types";

export function LocalNotes({ events, notes, localCap }: { events: EventItem[]; notes: string[]; localCap: number }) {
  return (
    <section aria-labelledby="local-title">
      <h2 id="local-title" className="flex items-center gap-2 text-lg font-semibold text-zinc-100">
        <MapPin className="h-5 w-5 text-zinc-400" aria-hidden />
        หมายเหตุเหตุการณ์ระดับท้องถิ่น
      </h2>
      <p className="mb-4 text-sm text-zinc-500">
        เหตุการณ์รุนแรงที่เกิดเฉพาะพื้นที่ (ห่างจากจุดยุทธศาสตร์ห่วงโซ่อุปทานโลก) ถูกจำกัดน้ำหนักไว้ไม่เกิน {localCap} คะแนนในหมวด
        จึงไม่ดันคะแนนรวมของโลกให้สูงเกินจริง — แต่ยังสำคัญต่อผู้ได้รับผลกระทบ
      </p>

      {events.length === 0 && notes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-800 p-6 text-center text-sm text-zinc-500">
          ไม่มีเหตุการณ์ท้องถิ่นที่มีนัยสำคัญในรอบนี้
        </div>
      ) : (
        <div className="space-y-3">
          {notes.length > 0 && (
            <ul className="space-y-2 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 text-sm text-zinc-300">
              {notes.map((n, i) => (
                <li key={i} className="flex gap-2">
                  <span className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-zinc-500" />
                  {n}
                </li>
              ))}
            </ul>
          )}
          {events.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-zinc-800">
              <table className="w-full min-w-[520px] text-sm">
                <thead className="bg-zinc-900/60 text-left text-[11px] text-zinc-500">
                  <tr>
                    <th className="px-3 py-2 font-normal">เหตุการณ์</th>
                    <th className="px-3 py-2 font-normal">ประเภท</th>
                    <th className="px-3 py-2 text-right font-normal">ความรุนแรงจริง</th>
                    <th className="px-3 py-2 text-right font-normal">นับในดัชนี</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.id} className="border-t border-zinc-800/70">
                      <td className="px-3 py-2 text-zinc-300">
                        {e.links[0] ? (
                          <a href={e.links[0]} target="_blank" rel="noopener noreferrer" className="hover:underline">
                            {e.title}
                          </a>
                        ) : (
                          e.title
                        )}
                        {e.location && <div className="text-[11px] text-zinc-500">{e.location}</div>}
                      </td>
                      <td className="px-3 py-2 text-zinc-400">{e.category_th}</td>
                      <td className="num px-3 py-2 text-right text-zinc-300">{e.raw_score === null ? "—" : Math.round(e.raw_score)}</td>
                      <td className="num px-3 py-2 text-right text-zinc-400">{Math.round(e.score)}</td>
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
