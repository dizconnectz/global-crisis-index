"""Bilingual (Thai/English) narrative layer. Gemini writes words only — never numbers.

Order of preference:
  1. Gatekeeper: nothing new + econ moved < threshold  -> reuse previous AI text (0 tokens)
  2. One Gemini request per run (JSON mode), both languages in the same call
  3. Rule-based Thai + English template (no key, quota exhausted, bad response, anything)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime

from .geo_utils import countries_en, countries_th
from .models import Event, iso

log = logging.getLogger("gci.ai")

SIGNALS = ("สูง", "ปานกลาง", "เฝ้าระวัง")
PILLAR_TH = {
    "econ": "เศรษฐกิจ การเงิน และพลังงาน",
    "geo": "ความขัดแย้งและภูมิรัฐศาสตร์",
    "nat": "ภัยธรรมชาติต่อจุดยุทธศาสตร์",
    "bio_infra": "สุขภาพและโครงสร้างพื้นฐาน",
}
PILLAR_EN = {
    "econ": "Economy, finance & energy",
    "geo": "Conflict & geopolitics",
    "nat": "Natural hazards at strategic hubs",
    "bio_infra": "Health & critical infrastructure",
}
WATCH_TIMEFRAME = {
    "mobilization": "1-4 สัปดาห์", "chokepoint": "1-4 สัปดาห์", "energy_infra": "1-4 สัปดาห์",
    "great_power": "1-4 สัปดาห์", "nuclear": "1-4 สัปดาห์", "invasion": "1-4 สัปดาห์",
    "sanctions": "1-3 เดือน", "novel_pathogen": "1-3 เดือน", "high_consequence": "1-3 เดือน",
    "pheic": "1-4 สัปดาห์", "global_outage": "1-4 สัปดาห์", "cyber_incident": "1-3 เดือน",
}
TIMEFRAME_EN = {"1-4 สัปดาห์": "1-4 weeks", "1-3 เดือน": "1-3 months"}


# ---------------------------------------------------------------- template (always available)

def _signal(ev: Event) -> str:
    n = len(ev.sources)
    if ev.score >= 60 and n >= 3:
        return "สูง"
    if ev.score >= 40:
        return "ปานกลาง"
    return "เฝ้าระวัง"


def _watch_events(events: list[Event]) -> list[Event]:
    out, seen = [], set()
    for ev in events:
        if ev.category not in WATCH_TIMEFRAME or ev.is_local or ev.category in seen or ev.title in seen:
            continue
        seen.update({ev.category, ev.title})
        out.append(ev)
        if len(out) == 3:
            break
    return out


def template_summary(ctx: dict) -> dict:
    score, band_th, band_en = ctx["global_score"], ctx["band_label_th"], ctx["band_label_en"]
    drivers = ctx["top_drivers"]
    events: list[Event] = ctx["events"]
    top = next((e for e in events if not e.is_local), None)

    if score is None:
        exec_th = ("ขณะนี้ยังคำนวณดัชนีรวมไม่ได้เพราะแหล่งข้อมูลหลักขาดหาย "
                   "ระบบจะไม่แสดงค่าแทนที่เป็นศูนย์เพื่อไม่ให้โลกดูปลอดภัยเกินจริง")
        exec_en = ("The global index cannot be computed right now because key data sources are missing. "
                   "The system will not substitute zero, which would make the world look safer than it is.")
    else:
        drv_th = " และ".join(f"หมวด{PILLAR_TH[d['pillar']]} ({d['score']:.0f}/100)" for d in drivers[:2])
        drv_en = " and ".join(f"{PILLAR_EN[d['pillar']].lower()} ({d['score']:.0f}/100)" for d in drivers[:2])
        s1_th = f"ดัชนีวิกฤตโลกอยู่ที่ {score}/100 ระดับ “{band_th}” โดยแรงกดดันหลักมาจาก{drv_th}"
        s1_en = f"The Global Crisis Index stands at {score}/100 (“{band_en}”), driven mainly by {drv_en}."
        if top:
            s2_th = (f"เหตุการณ์ที่มีน้ำหนักสูงสุดคือ{top.category_th}เกี่ยวกับ{countries_th(top.countries)} "
                     f"(ยืนยันจาก {len(top.sources)} แหล่ง)")
            s2_en = (f"The heaviest-weighted event is {top.category_en.lower() or top.category}"
                     f" involving {countries_en(top.countries)} (confirmed by {len(top.sources)} "
                     f"source{'s' if len(top.sources) != 1 else ''})")
        else:
            s2_th = "ไม่พบเหตุการณ์ระดับโลกที่มีน้ำหนักโดดเด่นในรอบนี้"
            s2_en = "No dominant global-scale event was detected in this run"
        if ctx["cross_confirmed"]:
            s2_th += f" และวิกฤตเริ่มลุกลามข้ามหมวด ทำให้ตัวเร่งเชิงระบบเพิ่มคะแนน +{ctx['boost']:.0f}"
            s2_en += f", and the crisis is spreading across pillars, adding a systemic boost of +{ctx['boost']:.0f}"
        exec_th = f"{s1_th} {s2_th}"
        exec_en = f"{s1_en} {s2_en}."

    warn_th, warn_en = [], []
    for ev in _watch_events(events):
        tf = WATCH_TIMEFRAME[ev.category]
        sig = _signal(ev)
        warn_th.append({
            "title": f"{ev.category_th}: {countries_th(ev.countries)}", "signal_strength": sig, "timeframe": tf,
            "evidence_summary": f"พบรายงาน {ev.article_count} ชิ้นจาก {len(ev.sources)} แหล่งข่าว เช่น “{ev.title[:140]}”",
        })
        warn_en.append({
            "title": f"{ev.category_en or ev.category_th}: {countries_en(ev.countries)}", "signal_strength": sig,
            "timeframe": TIMEFRAME_EN[tf],
            "evidence_summary": f"{ev.article_count} report(s) from {len(ev.sources)} outlet(s), e.g. “{ev.title[:140]}”",
        })
    brent = next((i for i in ctx["econ_indicators"] if i["key"] == "brent"), None)
    if len(warn_th) < 3 and brent and brent.get("change_pct") is not None and abs(brent["change_pct"]) >= 8:
        sig = "ปานกลาง" if abs(brent["change_pct"]) < 15 else "สูง"
        warn_th.append({"title": "ความผันผวนราคาพลังงาน", "signal_strength": sig, "timeframe": "1-3 เดือน",
                        "evidence_summary": f"ราคาน้ำมัน Brent เปลี่ยนแปลง {brent['change_pct']:+.1f}% ใน 5 วันทำการ (ล่าสุด {brent['value']:.1f} USD)"})
        warn_en.append({"title": "Energy price volatility", "signal_strength": sig, "timeframe": "1-3 months",
                        "evidence_summary": f"Brent crude moved {brent['change_pct']:+.1f}% over 5 trading days (last {brent['value']:.1f} USD)"})

    notes_th, notes_en = [], []
    for ev in ctx["local_events"][:4]:
        notes_th.append(f"{ev.category_th} — {ev.location or countries_th(ev.countries)}: {ev.title[:120]} "
                        f"(น้ำหนักในดัชนีโลกถูกจำกัดไว้ที่ {ev.score:.0f} คะแนนในหมวด)")
        notes_en.append(f"{ev.category_en or ev.category_th} — {ev.location_en or countries_en(ev.countries)}: {ev.title[:120]} "
                        f"(weight in the global index capped at {ev.score:.0f} points in its pillar)")

    return {"executive_summary_th": exec_th, "early_warnings_th": warn_th, "local_notes_th": notes_th,
            "executive_summary_en": exec_en, "early_warnings_en": warn_en, "local_notes_en": notes_en}


# ---------------------------------------------------------------- Gemini

PROMPT = """You are a systemic-risk analyst. Reply with JSON only, in BOTH Thai and English.
Never create or change any score. Use only the numbers and news provided below. Do not guess probabilities.

Index data (already computed by the system):
{indices}

Deduplicated events / headlines (max 20):
{headlines}

Local events whose weight was capped:
{local}

Reply with this JSON shape:
{{
  "executive_summary_th": "2 Thai sentences explaining why the score is at its current level",
  "executive_summary_en": "the same 2 sentences in English",
  "early_warnings": [
    {{"title_th": "...", "title_en": "...",
      "signal_strength": "สูง|ปานกลาง|เฝ้าระวัง",
      "timeframe_th": "e.g. 1-4 สัปดาห์ or 1-3 เดือน", "timeframe_en": "e.g. 1-4 weeks or 1-3 months",
      "evidence_th": "one Thai sentence of fact from the news", "evidence_en": "the same in English"}}
  ],
  "local_notes_th": ["short Thai note"],
  "local_notes_en": ["the same in English"]
}}
early_warnings: at most 3, each backed by the news above (1-3 month watchlist: troop movements, new sanctions,
energy trends, etc). local_notes: at most 4. signal_strength must be exactly one of the three Thai values."""


def _validate(data: dict) -> dict:
    exec_th = str(data.get("executive_summary_th", "")).strip()
    exec_en = str(data.get("executive_summary_en", "")).strip()
    if not exec_th or not exec_en:
        raise ValueError("missing executive summary")
    warn_th, warn_en = [], []
    for w in (data.get("early_warnings") or [])[:3]:
        if not isinstance(w, dict) or not w.get("title_th") or not w.get("title_en"):
            continue
        sig = str(w.get("signal_strength", "")).strip()
        sig = sig if sig in SIGNALS else "เฝ้าระวัง"
        warn_th.append({"title": str(w["title_th"]).strip()[:120], "signal_strength": sig,
                        "timeframe": str(w.get("timeframe_th") or "1-3 เดือน").strip()[:40],
                        "evidence_summary": str(w.get("evidence_th", "")).strip()[:300]})
        warn_en.append({"title": str(w["title_en"]).strip()[:120], "signal_strength": sig,
                        "timeframe": str(w.get("timeframe_en") or "1-3 months").strip()[:40],
                        "evidence_summary": str(w.get("evidence_en", "")).strip()[:300]})

    def notes(key: str) -> list[str]:
        return [str(n).strip()[:240] for n in (data.get(key) or []) if str(n).strip()][:4]

    return {"executive_summary_th": exec_th[:600], "early_warnings_th": warn_th, "local_notes_th": notes("local_notes_th"),
            "executive_summary_en": exec_en[:700], "early_warnings_en": warn_en, "local_notes_en": notes("local_notes_en")}


def _call_gemini(ctx: dict, api_key: str, model: str) -> dict:
    from google import genai
    from google.genai import types

    indices = {
        "global_score": ctx["global_score"], "band": ctx["band_label_en"],
        "pillars": ctx["pillar_scores"], "boost": ctx["boost"], "cross_confirmed": ctx["cross_confirmed"],
        "econ_indicators": {i["key"]: {"value": i["value"], "change_5d_pct": i["change_pct"]}
                            for i in ctx["econ_indicators"]},
    }
    heads = [f"- [{e.pillar}/{e.category_en or e.category}] {e.title} (sources: {len(e.sources)}, score {e.score:.0f})"
             for e in ctx["events"] if not e.is_local][:ctx["max_headlines"]]
    local = [f"- {e.category_en or e.category}: {e.title} ({e.location_en or ''})" for e in ctx["local_events"][:6]]
    prompt = PROMPT.format(indices=json.dumps(indices, ensure_ascii=False),
                           headlines="\n".join(heads) or "- (none)", local="\n".join(local) or "- (none)")
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
        cached = ai_cache.get("summary") or {}
        if (ai_cache.get("source") == "gemini" and cached.get("executive_summary_en")
                and not new_ids and econ_delta < ai_cfg["econ_delta_threshold"]):
            log.info("AI gate: no new events, econ Δ=%.2f -> reuse previous text (0 tokens)", econ_delta)
            summary = {**cached, "source": "gemini_cached", "model": ai_cache.get("model"),
                       "generated_at": ai_cache.get("generated_at")}
            return summary, ai_cache
        try:
            text = _call_gemini(ctx, api_key, model)
            log.info("Gemini summary generated with %s", model)
            new_cache = {"source": "gemini", "model": model, "events_hash": h, "event_ids": ids,
                         "econ_score": econ, "summary": text, "generated_at": iso(now)}
            return {**text, "source": "gemini", "model": model, "generated_at": iso(now)}, new_cache
        except Exception as exc:  # noqa: BLE001 - 429 quota, network, bad JSON… all fall back
            log.warning("Gemini unavailable (%s: %s) -> template", type(exc).__name__, str(exc)[:160])

    text = template_summary(ctx)
    new_cache = {"source": "template", "model": None, "events_hash": h, "event_ids": ids,
                 "econ_score": econ, "summary": text, "generated_at": iso(now)}
    return {**text, "source": "template", "model": None, "generated_at": iso(now)}, new_cache
