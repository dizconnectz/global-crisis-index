"""Thai narrative layer. Gemini writes words only — never numbers.

Order of preference:
  1. Gatekeeper: nothing new + econ moved < threshold  -> reuse previous AI text (0 tokens)
  2. One Gemini request per run (JSON mode)
  3. Rule-based Thai template (no key, quota exhausted, bad response, anything)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime

from .geo_utils import countries_th
from .models import Event, iso

log = logging.getLogger("gci.ai")

SIGNALS = ("สูง", "ปานกลาง", "เฝ้าระวัง")
PILLAR_TH = {
    "econ": "เศรษฐกิจ การเงิน และพลังงาน",
    "geo": "ความขัดแย้งและภูมิรัฐศาสตร์",
    "nat": "ภัยธรรมชาติต่อจุดยุทธศาสตร์",
    "bio_infra": "สุขภาพและโครงสร้างพื้นฐาน",
}
WATCH_TIMEFRAME = {
    "mobilization": "1-4 สัปดาห์", "chokepoint": "1-4 สัปดาห์", "energy_infra": "1-4 สัปดาห์",
    "great_power": "1-4 สัปดาห์", "nuclear": "1-4 สัปดาห์", "invasion": "1-4 สัปดาห์",
    "sanctions": "1-3 เดือน", "novel_pathogen": "1-3 เดือน", "high_consequence": "1-3 เดือน",
    "pheic": "1-4 สัปดาห์", "global_outage": "1-4 สัปดาห์", "cyber_incident": "1-3 เดือน",
}


# ---------------------------------------------------------------- template (always available)

def _signal(ev: Event) -> str:
    n = len(ev.sources)
    if ev.score >= 60 and n >= 3:
        return "สูง"
    if ev.score >= 40:
        return "ปานกลาง"
    return "เฝ้าระวัง"


def template_summary(ctx: dict) -> dict:
    score, band = ctx["global_score"], ctx["band_label_th"]
    drivers = ctx["top_drivers"]
    events: list[Event] = ctx["events"]
    if score is None:
        exec_th = ("ขณะนี้ยังคำนวณดัชนีรวมไม่ได้เพราะแหล่งข้อมูลหลักขาดหาย "
                   "ระบบจะไม่แสดงค่าแทนที่เป็นศูนย์เพื่อไม่ให้โลกดูปลอดภัยเกินจริง")
    else:
        drv = " และ".join(f"หมวด{PILLAR_TH[d['pillar']]} ({d['score']:.0f}/100)" for d in drivers[:2])
        s1 = f"ดัชนีวิกฤตโลกอยู่ที่ {score}/100 ระดับ “{band}” โดยแรงกดดันหลักมาจาก{drv}"
        top = next((e for e in events if not e.is_local), None)
        if top:
            s2 = (f"เหตุการณ์ที่มีน้ำหนักสูงสุดคือ{top.category_th}เกี่ยวกับ{countries_th(top.countries)} "
                  f"(ยืนยันจาก {len(top.sources)} แหล่ง)")
        else:
            s2 = "ไม่พบเหตุการณ์ระดับโลกที่มีน้ำหนักโดดเด่นในรอบนี้"
        if ctx["cross_confirmed"]:
            s2 += f" และวิกฤตเริ่มลุกลามข้ามหมวด ทำให้ตัวเร่งเชิงระบบเพิ่มคะแนน +{ctx['boost']:.0f}"
        exec_th = f"{s1} {s2}"

    warnings = []
    seen = set()
    for ev in events:
        if ev.category not in WATCH_TIMEFRAME or ev.is_local or ev.category in seen or ev.title in seen:
            continue
        seen.update({ev.category, ev.title})
        warnings.append({
            "title": f"{ev.category_th}: {countries_th(ev.countries)}",
            "signal_strength": _signal(ev),
            "timeframe": WATCH_TIMEFRAME[ev.category],
            "evidence_summary": f"พบรายงาน {ev.article_count} ชิ้นจาก {len(ev.sources)} แหล่งข่าว เช่น “{ev.title[:140]}”",
        })
        if len(warnings) == 3:
            break
    brent = next((i for i in ctx["econ_indicators"] if i["key"] == "brent"), None)
    if len(warnings) < 3 and brent and brent.get("change_pct") is not None and abs(brent["change_pct"]) >= 8:
        warnings.append({
            "title": "ความผันผวนราคาพลังงาน",
            "signal_strength": "ปานกลาง" if abs(brent["change_pct"]) < 15 else "สูง",
            "timeframe": "1-3 เดือน",
            "evidence_summary": f"ราคาน้ำมัน Brent เปลี่ยนแปลง {brent['change_pct']:+.1f}% ใน 5 วันทำการ (ล่าสุด {brent['value']:.1f} USD)",
        })

    notes = []
    for ev in ctx["local_events"][:4]:
        cap_note = f"น้ำหนักในดัชนีโลกถูกจำกัดไว้ที่ {ev.score:.0f} คะแนนในหมวด"
        where = ev.location or countries_th(ev.countries)
        notes.append(f"{ev.category_th} — {where}: {ev.title[:120]} ({cap_note})")

    return {"executive_summary_th": exec_th, "early_warnings_th": warnings, "local_notes_th": notes}


# ---------------------------------------------------------------- Gemini

PROMPT = """คุณเป็นนักวิเคราะห์ความเสี่ยงเชิงระบบ ตอบเป็น JSON เท่านั้น ภาษาไทย
ห้ามสร้างหรือแก้ไขตัวเลขคะแนนใดๆ ให้อ้างอิงเฉพาะตัวเลขและข่าวในข้อมูลด้านล่างเท่านั้น ห้ามเดาเปอร์เซ็นต์ความน่าจะเป็น

ข้อมูลดัชนี (คำนวณโดยระบบแล้ว):
{indices}

เหตุการณ์/พาดหัวข่าวที่ตัดซ้ำแล้ว (สูงสุด 20 รายการ):
{headlines}

เหตุการณ์ระดับท้องถิ่นที่ถูกจำกัดน้ำหนัก:
{local}

ตอบด้วย JSON รูปแบบ:
{{
  "executive_summary_th": "สรุปสาเหตุของระดับคะแนนปัจจุบัน 2 ประโยค",
  "early_warnings_th": [
    {{"title": "ชื่อความเสี่ยง", "signal_strength": "สูง|ปานกลาง|เฝ้าระวัง",
      "timeframe": "เช่น 1-4 สัปดาห์ หรือ 1-3 เดือน", "evidence_summary": "ข้อเท็จจริงจากข่าว 1 ประโยค"}}
  ],
  "local_notes_th": ["สรุปเหตุการณ์ท้องถิ่นสั้นๆ"]
}}
early_warnings_th ไม่เกิน 3 รายการ และต้องมีหลักฐานจากข่าวที่ให้ไว้เท่านั้น local_notes_th ไม่เกิน 4 รายการ"""


def _validate(data: dict) -> dict:
    exec_th = str(data.get("executive_summary_th", "")).strip()
    if not exec_th:
        raise ValueError("empty executive_summary_th")
    warnings = []
    for w in (data.get("early_warnings_th") or [])[:3]:
        if not isinstance(w, dict) or not w.get("title"):
            continue
        sig = str(w.get("signal_strength", "")).strip()
        warnings.append({
            "title": str(w["title"]).strip()[:120],
            "signal_strength": sig if sig in SIGNALS else "เฝ้าระวัง",
            "timeframe": str(w.get("timeframe") or "1-3 เดือน").strip()[:40],
            "evidence_summary": str(w.get("evidence_summary", "")).strip()[:300],
        })
    notes = [str(n).strip()[:240] for n in (data.get("local_notes_th") or []) if str(n).strip()][:4]
    return {"executive_summary_th": exec_th[:600], "early_warnings_th": warnings, "local_notes_th": notes}


def _call_gemini(ctx: dict, api_key: str, model: str) -> dict:
    from google import genai
    from google.genai import types

    indices = {
        "global_score": ctx["global_score"], "band": ctx["band_label_th"],
        "pillars": ctx["pillar_scores"], "boost": ctx["boost"], "cross_confirmed": ctx["cross_confirmed"],
        "econ_indicators": {i["key"]: {"value": i["value"], "change_5d_pct": i["change_pct"]}
                            for i in ctx["econ_indicators"]},
    }
    heads = [f"- [{e.pillar}/{e.category_th}] {e.title} (แหล่ง: {len(e.sources)}, คะแนน {e.score:.0f})"
             for e in ctx["events"] if not e.is_local][:ctx["max_headlines"]]
    local = [f"- {e.category_th}: {e.title} ({e.location or ''})" for e in ctx["local_events"][:6]]
    prompt = PROMPT.format(indices=json.dumps(indices, ensure_ascii=False),
                           headlines="\n".join(heads) or "- (ไม่มี)", local="\n".join(local) or "- (ไม่มี)")
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
    )
    return _validate(json.loads(resp.text))


def events_hash(events: list[Event]) -> tuple[str, list[str]]:
    ids = sorted(e.id for e in events if e.score >= 30)
    return hashlib.sha1("|".join(ids).encode()).hexdigest()[:16], ids


def build_narrative(ctx: dict, ai_cache: dict, now: datetime, ai_cfg: dict) -> tuple[dict, dict]:
    """Return (summary block for latest_state, updated ai cache)."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-2.5-flash"
    h, ids = events_hash(ctx["events"])
    econ = ctx["pillar_scores"].get("econ")

    if api_key:
        prev_ids = set(ai_cache.get("event_ids", []))
        new_ids = set(ids) - prev_ids
        prev_econ = ai_cache.get("econ_score")
        econ_delta = abs(econ - prev_econ) if econ is not None and prev_econ is not None else float("inf")
        if (ai_cache.get("source") == "gemini" and ai_cache.get("summary")
                and not new_ids and econ_delta < ai_cfg["econ_delta_threshold"]):
            log.info("AI gate: no new events, econ Δ=%.2f -> reuse previous text (0 tokens)", econ_delta)
            summary = {**ai_cache["summary"], "source": "gemini_cached", "model": ai_cache.get("model"),
                       "generated_at": ai_cache.get("generated_at")}
            return summary, ai_cache
        try:
            text = _call_gemini(ctx, api_key, model)
            log.info("Gemini summary generated with %s", model)
            new_cache = {"source": "gemini", "model": model, "events_hash": h, "event_ids": ids,
                         "econ_score": econ, "summary": text, "generated_at": iso(now)}
            return {**text, "source": "gemini", "model": model, "generated_at": iso(now)}, new_cache
        except Exception as exc:  # noqa: BLE001 - 429 quota, network, bad JSON… all fall back
            log.warning("Gemini unavailable (%s: %s) -> Thai template", type(exc).__name__, str(exc)[:160])

    text = template_summary(ctx)
    new_cache = {"source": "template", "model": None, "events_hash": h, "event_ids": ids,
                 "econ_score": econ, "summary": text, "generated_at": iso(now)}
    return {**text, "source": "template", "model": None, "generated_at": iso(now)}, new_cache
