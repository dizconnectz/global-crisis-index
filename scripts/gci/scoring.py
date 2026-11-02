"""Deterministic scoring. Every number on the site is produced here — never by AI.

Rule of thumb throughout: missing data is `None`, never 0.
"""

from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timedelta
from functools import lru_cache

from .geo_utils import countries_en, countries_th, find_countries, haversine_km, normalize, title_tokens
from .models import Article, Event, iso, parse_iso


# ---------------------------------------------------------------- primitives

def piecewise(x: float, points: list[list[float]]) -> float:
    """Piecewise-linear map. Points are (x, score), sorted by x; ends are clamped."""
    pts = sorted(points, key=lambda p: p[0])
    if x <= pts[0][0]:
        return float(pts[0][1])
    if x >= pts[-1][0]:
        return float(pts[-1][1])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return float(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
    return float(pts[-1][1])  # unreachable


def aggregate(scores: list[float], tail_weight: float = 0.5) -> float:
    """Combine event scores: the largest counts fully, each further event fills a
    geometrically shrinking share of the remaining headroom. Bounded to [0, 100]
    so piling on many small events can never fake a crisis."""
    total = 0.0
    for i, s in enumerate(sorted((max(0.0, min(100.0, s)) for s in scores), reverse=True)):
        total += (100.0 - total) * (s / 100.0) * (1.0 if i == 0 else tail_weight ** i)
    return min(100.0, total)


def decay(score: float, days: float, rate: float) -> float:
    return score * (1.0 - rate) ** max(0.0, days)


# ---------------------------------------------------------------- econ pillar

def market_metrics(rows: list[tuple[str, float]], window: int = 5) -> dict:
    closes = [c for _, c in rows]
    last = closes[-1]
    prev = closes[-1 - window] if len(closes) > window else closes[0]
    peak = max(closes[-252:])
    return {
        "last": last,
        "last_date": rows[-1][0],
        "change_pct": (last / prev - 1.0) * 100.0,
        "drawdown_pct": (last / peak - 1.0) * 100.0,
    }


def score_indicator(ind_cfg: dict, m: dict) -> float:
    parts = []
    if "change_points" in ind_cfg:
        ch = abs(m["change_pct"]) if ind_cfg.get("change_abs") else m["change_pct"]
        parts.append(piecewise(ch, ind_cfg["change_points"]))
    if ind_cfg.get("combine") != "change_only":
        if "level_points" in ind_cfg:
            parts.append(piecewise(m["last"], ind_cfg["level_points"]))
        if "drawdown_points" in ind_cfg:
            parts.append(piecewise(m["drawdown_pct"], ind_cfg["drawdown_points"]))
    return max(parts)


def market_freshness(last_bar: str, now: datetime) -> str:
    """ok | market_closed | stale | expired, judged from the last daily bar."""
    age = (now.date() - datetime.strptime(last_bar, "%Y-%m-%d").date()).days
    if now.weekday() >= 5 and age <= 3:
        return "market_closed"
    if age <= 4:
        return "ok"
    if age <= 10:
        return "stale"
    return "expired"


def score_econ(market_data: dict | None, cfg: dict, cached_indicators: dict, now: datetime) -> dict:
    """Weighted average over indicators that have a valid value.

    A failed indicator falls back to its last known value (status `stale`) if that
    value is younger than `market_max_age_hours`; otherwise it is dropped and the
    remaining weights are renormalised. It is never replaced with 0.
    """
    econ = cfg["econ"]
    max_age = timedelta(hours=cfg["freshness"]["market_max_age_hours"])
    indicators = []
    for key, ind in econ["indicators"].items():
        entry = (market_data or {}).get(key)
        rec = None
        if entry and entry.get("rows"):
            m = market_metrics(entry["rows"], econ["trading_days_window"])
            status = market_freshness(m["last_date"], now)
            if status != "expired":
                rec = {**m, "status": status, "provider": entry.get("provider"), "as_of": iso(now)}
        if rec is None:
            prev = cached_indicators.get(key)
            prev_at = parse_iso(prev.get("as_of")) if prev else None
            if prev and prev.get("last") is not None and prev_at and now - prev_at <= max_age:
                rec = {**prev, "status": "stale"}
        if rec is None:
            indicators.append({"key": key, "label_th": ind["label_th"], "label_en": ind["label_en"],
                               "unit": ind["unit"], "unit_en": ind.get("unit_en", ""),
                               "ticker": ind["ticker"], "weight": ind["weight"],
                               "value": None, "change_pct": None, "drawdown_pct": None,
                               "score": None, "status": "missing", "last_date": None})
            continue
        indicators.append({
            "key": key, "label_th": ind["label_th"], "label_en": ind["label_en"], "unit": ind["unit"],
            "unit_en": ind.get("unit_en", ""), "ticker": ind["ticker"],
            "weight": ind["weight"], "value": round(rec["last"], 2),
            "change_pct": round(rec["change_pct"], 2), "drawdown_pct": round(rec["drawdown_pct"], 2),
            "score": round(score_indicator(ind, rec), 1), "status": rec["status"],
            "last_date": rec["last_date"], "provider": rec.get("provider"),
            # raw fields kept for the cache
            "last": rec["last"], "as_of": rec.get("as_of"),
        })

    valid = [i for i in indicators if i["score"] is not None]
    wsum = sum(i["weight"] for i in valid)
    score = sum(i["score"] * i["weight"] for i in valid) / wsum if valid else None
    statuses = {i["status"] for i in indicators}
    if score is None:
        status = "degraded"
    elif "missing" in statuses or "stale" in statuses:
        status = "partial"
    elif statuses == {"market_closed"} or ("market_closed" in statuses and statuses <= {"market_closed", "ok"}):
        status = "market_closed"
    else:
        status = "ok"
    return {"score": None if score is None else round(score, 1), "status": status,
            "coverage": round(wsum, 2), "indicators": indicators}


# ---------------------------------------------------------------- text classification

@lru_cache(maxsize=2048)
def _term_re(term: str) -> re.Pattern:
    tail = r"(?:s|es|ed|ing)?(?![a-z])" if term[-1].isalpha() else ""
    return re.compile(r"(?<![a-z])" + re.escape(term) + tail)


def _has(text: str, term: str) -> bool:
    return _term_re(term).search(text) is not None


def classify(text: str, categories: list[dict], great_powers: list[str] | None = None,
             countries: list[str] | None = None, min_severity: float = 0) -> dict | None:
    """Highest-severity category whose keyword rule matches the normalised text."""
    best = None
    for cat in categories:
        if cat["severity"] < min_severity:
            continue
        hit = any(_has(text, t) for t in cat.get("any", []))
        if not hit and cat.get("or_all"):
            hit = any(all(_has(text, t) for t in group) for group in cat["or_all"])
        if hit and cat.get("powers_min"):
            powers = {c for c in (countries or []) if c in (great_powers or [])}
            hit = len(powers) >= cat["powers_min"]
        if hit and (best is None or cat["severity"] > best["severity"]):
            best = cat
    return best


def _event_id(pillar: str, category: str, countries: list[str], tokens: set[str]) -> str:
    key = "|".join(sorted(countries[:2])) if countries else " ".join(sorted(tokens)[:4])
    return f"{pillar}:{category}:" + hashlib.sha1(key.encode()).hexdigest()[:10]


def group_articles(articles: list[Article], categories: list[dict], pillar: str, cfg_events: dict,
                   now: datetime, *, max_age_hours: float = 48, great_powers: list[str] | None = None,
                   min_severity: float = 0, trusted_sources: set[str] | None = None) -> list[Event]:
    """Deduplicate articles into events.

    Articles join an existing cluster when they share the category and either a
    country or most of their headline words. The event score depends on its
    category severity and on the number of *distinct outlets* — never on the raw
    article count, so 50 copies of one story weigh the same as one.
    """
    corroboration = {int(k): v for k, v in cfg_events["corroboration"].items()}
    max_c = max(corroboration)
    headline_only = cfg_events.get("headline_only_min_severity", 101)
    clusters: list[dict] = []
    for art in articles:
        if art.published and (now - art.published).total_seconds() > max_age_hours * 3600:
            continue
        title = normalize(art.title)
        text = normalize(f"{art.title} {art.summary[:400]}")
        countries = find_countries(text)
        # Severe categories must be stated in the headline itself; a passing mention
        # in the body ("fake warnings of nuclear threats") must not trigger them.
        cat = classify(title, categories, great_powers, countries, min_severity)
        body_cats = [c for c in categories if c["severity"] < headline_only]
        body_cat = classify(text, body_cats, great_powers, countries, min_severity)
        if body_cat and (cat is None or body_cat["severity"] > cat["severity"]):
            cat = body_cat
        if cat is None:
            continue
        toks = title_tokens(title)
        target = None
        for cl in clusters:
            if cl["cat"]["id"] != cat["id"]:
                continue
            shared = set(countries[:2]) & set(cl["countries"][:2])
            union = toks | cl["tokens"]
            jacc = len(toks & cl["tokens"]) / len(union) if union else 0
            if shared or jacc >= 0.5:
                target = cl
                break
        if target is None:
            clusters.append({"cat": cat, "countries": countries, "tokens": toks, "title": art.title,
                             "sources": {art.source}, "links": [art.link] if art.link else [],
                             "link_sources": [art.source] if art.link else [],
                             "count": 1, "text": text})
        else:
            target["sources"].add(art.source)
            target["count"] += 1
            if art.link and art.source not in target["link_sources"] and len(target["links"]) < 5:
                target["links"].append(art.link)
                target["link_sources"].append(art.source)
            for c in countries:
                if c not in target["countries"]:
                    target["countries"].append(c)

    events = []
    for cl in clusters:
        n_src = len(cl["sources"])
        factor = corroboration[min(n_src, max_c)]
        if trusted_sources and cl["sources"] & trusted_sources:
            factor = 1.0
        sev = float(cl["cat"]["severity"])
        events.append(Event(
            id=_event_id(pillar, cl["cat"]["id"], cl["countries"], cl["tokens"]),
            pillar=pillar, category=cl["cat"]["id"], category_th=cl["cat"]["label_th"],
            category_en=cl["cat"].get("label_en", cl["cat"]["label_th"]),
            title=cl["title"], severity=sev, score=sev * factor,
            countries=cl["countries"][:5], sources=sorted(cl["sources"])[:8],
            article_count=cl["count"], links=cl["links"], link_sources=cl["link_sources"],
        ))
        events[-1]._text = cl["text"]  # type: ignore[attr-defined]  # used by bio multi-country check
    # Two clusters can collapse onto the same id (same category + same lead countries)
    merged: dict[str, Event] = {}
    for ev in events:
        if ev.id in merged:
            m = merged[ev.id]
            m.article_count += ev.article_count
            m.sources = sorted(set(m.sources) | set(ev.sources))[:8]
            m.score = max(m.score, ev.score)
        else:
            merged[ev.id] = ev
    return list(merged.values())


# ---------------------------------------------------------------- active-event state (decay)

def merge_active(new_events: list[Event], active: dict[str, dict], cfg_events: dict,
                 now: datetime) -> tuple[list[Event], dict[str, dict]]:
    """Fold this run's events into persisted state so ongoing crises do not vanish
    after 24h, and decay those that stop appearing.

    Returns (effective events for scoring, new state dict). State stores the score
    at `last_seen`; the effective score decays from there.
    """
    rate = cfg_events["decay_per_day"]
    out_state: dict[str, dict] = {}
    effective: list[Event] = []
    seen_ids = set()
    for ev in new_events:
        prev = active.get(ev.id)
        if prev:
            pe = Event.from_dict(prev)
            days = (now - (parse_iso(pe.last_seen) or now)).total_seconds() / 86400
            ev.score = max(ev.score, decay(pe.score, days, rate))
            ev.first_seen = pe.first_seen
            ev.sources = sorted(set(ev.sources) | set(pe.sources))[:8]
        else:
            ev.first_seen = iso(now)
            ev.is_new = ev.score >= cfg_events["new_event_min_score"]
        ev.last_seen = iso(now)
        seen_ids.add(ev.id)
        out_state[ev.id] = ev.to_dict()
        effective.append(ev)
    for eid, d in active.items():
        if eid in seen_ids:
            continue
        ev = Event.from_dict(d)
        last = parse_iso(ev.last_seen) or now
        days = (now - last).total_seconds() / 86400
        eff = decay(ev.score, days, rate)
        if eff < cfg_events["drop_below"] or days > cfg_events["max_age_days"]:
            continue
        out_state[eid] = d                      # keep undecayed anchor in state
        ev.score = eff
        if ev.raw_score is not None:
            ev.raw_score = decay(ev.raw_score, days, rate)
        effective.append(ev)
    effective.sort(key=lambda e: e.score, reverse=True)
    return effective, out_state


# ---------------------------------------------------------------- geo pillar

def score_geo(articles: list[Article] | None, cfg: dict, active: dict, now: datetime) -> dict:
    geo, ev_cfg = cfg["geo"], cfg["events"]
    new_events = []
    if articles is not None:
        new_events = group_articles(articles, geo["categories"], "geo", ev_cfg, now,
                                    max_age_hours=geo["max_article_age_hours"],
                                    great_powers=geo["great_powers"])
    events, state = merge_active(new_events, active, ev_cfg, now)
    score = aggregate([e.score for e in events], ev_cfg["aggregate_tail_weight"]) if events else 0.0
    return {"score": round(score, 1), "events": events, "state": state,
            "articles": len(articles or []), "clusters": len(new_events)}


# ---------------------------------------------------------------- nat pillar

def nearest_hub(lat: float | None, lon: float | None, hubs: list[dict]) -> tuple[dict | None, float | None]:
    if lat is None or lon is None:
        return None, None
    best = min(hubs, key=lambda h: haversine_km(lat, lon, h["lat"], h["lon"]))
    return best, haversine_km(lat, lon, best["lat"], best["lon"])


def hazard_events(hazards: list[dict], cfg: dict, now: datetime) -> list[Event]:
    """2-stage impact filter: severity first, then is it near a global chokepoint?"""
    nat, rate = cfg["nat"], cfg["events"]["decay_per_day"]
    quakes = [h for h in hazards if h["source"] == "USGS"]
    events = []
    for h in hazards:
        t = h.get("time") or now
        age_days = (now - t).total_seconds() / 86400
        if age_days > nat["event_window_days"]:
            continue
        if h["source"] == "GDACS" and h["type"] == "EQ" and h["lat"] is not None and any(
                haversine_km(h["lat"], h["lon"], q["lat"], q["lon"]) < 150
                and abs((q["time"] - t).total_seconds()) < 2 * 86400 for q in quakes):
            continue  # same quake already counted from USGS
        alert = h.get("alert")
        multi_country = len(h.get("countries") or []) >= 2
        if h["source"] == "USGS":
            raw = piecewise(h["mag"], nat["magnitude_points"])
            if alert in nat["pager_floor"]:
                raw = max(raw, nat["pager_floor"][alert])
            category, cat_th, cat_en = "earthquake", nat["gdacs_type_th"]["EQ"], nat["gdacs_type_en"]["EQ"]
        else:
            raw = float(nat["gdacs_alert_points"].get(alert or "green", 10))
            if alert == "red" and multi_country:
                raw = max(raw, nat["gdacs_red_multicountry"])
            category = f"gdacs_{h['type'].lower() or 'other'}"
            cat_th = nat["gdacs_type_th"].get(h["type"], "ภัยธรรมชาติ")
            cat_en = nat["gdacs_type_en"].get(h["type"], "Natural hazard")
        raw = decay(raw, age_days, rate)

        hub, dist = nearest_hub(h.get("lat"), h.get("lon"), nat["strategic_hubs"])
        near_hub = dist is not None and dist <= nat["hub_radius_km"]
        cross_tsunami = h.get("tsunami") and (h.get("mag") or 0) >= nat["tsunami_cross_region_min_mag"]
        red_multi = h["source"] == "GDACS" and alert == "red" and multi_country
        is_global = near_hub or cross_tsunami or red_multi
        location = location_en = h.get("place") or ""
        if near_hub:
            location = f"{location} (ห่าง{hub['name_th']} ~{dist:.0f} กม.)"
            location_en = f"{location_en} (~{dist:.0f} km from {hub['name_en']})"
        events.append(Event(
            id=h["id"], pillar="nat", category=category, category_th=cat_th, category_en=cat_en, title=h["title"],
            severity=raw, score=raw if is_global else min(raw, nat["local_cap"]),
            countries=h.get("countries") or [], sources=[h["source"]], links=[h["link"]] if h.get("link") else [],
            link_sources=[h["source"]] if h.get("link") else [],
            first_seen=iso(t), last_seen=iso(t), is_local=not is_global, location=location.strip(),
            location_en=location_en.strip(),
            raw_score=raw,
        ))
    events.sort(key=lambda e: e.score, reverse=True)
    return events


def score_nat(hazards: list[dict] | None, cfg: dict, now: datetime) -> dict:
    events = hazard_events(hazards or [], cfg, now)
    tail = cfg["events"]["aggregate_tail_weight"]
    global_scores = [e.score for e in events if not e.is_local]
    local_scores = [e.score for e in events if e.is_local]
    # all local events together are worth at most `local_cap`
    if local_scores:
        global_scores.append(min(cfg["nat"]["local_cap"], aggregate(local_scores, tail)))
    score = aggregate(global_scores, tail) if global_scores else 0.0
    return {"score": round(score, 1), "events": events}


# ---------------------------------------------------------------- bio / infra pillar

def score_bio_infra(official: list[Article] | None, news: list[Article] | None, cfg: dict,
                    active: dict, now: datetime) -> dict:
    bio, ev_cfg = cfg["bio_infra"], cfg["events"]
    trusted = {"WHO DON", "WHO", "CISA"}
    window_h = bio["window_days"] * 24
    events = []
    if official:
        events += group_articles(official, bio["categories"], "bio_infra", ev_cfg, now,
                                 max_age_hours=window_h, trusted_sources=trusted)
    if news:
        # general news only counts for serious categories (outbreaks of note, real incidents)
        events += group_articles(news, bio["categories"], "bio_infra", ev_cfg, now,
                                 max_age_hours=48, min_severity=40)
    cats = {c["id"]: c for c in bio["categories"]}
    for ev in events:
        text = getattr(ev, "_text", "")
        multi = (cats[ev.category].get("multi_country")
                 or any(m in text for m in bio["multi_country_markers"])
                 or len(ev.countries) >= 2)
        if not multi and ev.score > bio["single_country_cap"]:
            ev.raw_score = ev.score
            ev.score = float(bio["single_country_cap"])
            ev.is_local = True
            ev.location = countries_th(ev.countries, 1) if ev.countries else None
            ev.location_en = countries_en(ev.countries, 1) if ev.countries else None
    # same id may come from both official and news lists
    uniq: dict[str, Event] = {}
    for ev in events:
        if ev.id not in uniq or ev.score > uniq[ev.id].score:
            uniq[ev.id] = ev
    effective, state = merge_active(list(uniq.values()), active, ev_cfg, now)
    score = aggregate([e.score for e in effective], ev_cfg["aggregate_tail_weight"]) if effective else 0.0
    return {"score": round(score, 1), "events": effective, "state": state}


# ---------------------------------------------------------------- master formula

def compose(pillars: dict[str, float | None], cfg: dict) -> dict:
    """Cross-Confirmed Master Formula.

    S_base = Σ w_i·S_i over pillars with data (weights renormalised if one is missing)
    Boost  = (100 − S_base)·0.65·((S_max1 − 70)/30)^1.3   when S_max1 > 70 and S_max2 > 45
           = same, capped at 15                           otherwise
    Global = min(100, round(S_base + Boost))
    """
    w, b = cfg["weights"], cfg["booster"]
    avail = {k: v for k, v in pillars.items() if v is not None}
    if not avail:
        return {"global_score": None, "base": None, "boost": None, "cross_confirmed": False,
                "effective_weights": {}, "max1": None, "max2": None, "max1_pillar": None}
    wsum = sum(w[k] for k in avail)
    eff_w = {k: w[k] / wsum for k in avail}
    base = sum(eff_w[k] * v for k, v in avail.items())
    ranked = sorted(avail.items(), key=lambda kv: kv[1], reverse=True)
    max1 = ranked[0][1]
    max2 = ranked[1][1] if len(ranked) > 1 else 0.0
    excess = max(0.0, (max1 - b["max1_threshold"]) / (100 - b["max1_threshold"]))
    raw = (100.0 - base) * b["factor"] * excess ** b["exponent"]
    cross = max1 > b["max1_threshold"] and max2 > b["max2_threshold"]
    boost = raw if cross else min(raw, b["isolated_cap"])
    return {
        "global_score": int(min(100, round(base + boost))),
        "base": round(base, 2), "boost": round(boost, 2), "cross_confirmed": cross,
        "effective_weights": {k: round(v, 4) for k, v in eff_w.items()},
        "max1": round(max1, 1), "max2": round(max2, 1), "max1_pillar": ranked[0][0],
    }


def band_for(score: int | None, cfg: dict) -> dict | None:
    if score is None:
        return None
    for band in cfg["bands"]:
        if band["min"] <= score <= band["max"]:
            return band
    return cfg["bands"][-1]
