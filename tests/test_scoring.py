"""Unit tests for the deterministic scoring core (no network)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gci import scoring  # noqa: E402
from gci.models import Article, SourceResult, iso  # noqa: E402
from gci.pipeline import build_state  # noqa: E402

CFG = json.loads((ROOT / "config" / "scoring_rules.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)  # a Wednesday


# ---------------------------------------------------------------- fixtures

def _rows(start: float, end: float, n: int = 30, last_day: datetime = NOW) -> list[tuple[str, float]]:
    days = [last_day - timedelta(days=i) for i in range(n)][::-1]
    step = (end - start) / (n - 1)
    return [(d.strftime("%Y-%m-%d"), start + step * i) for i, d in enumerate(days)]


def calm_markets() -> SourceResult:
    data = {
        "vix": {"rows": _rows(14, 14), "provider": "test"},
        "brent": {"rows": _rows(70, 70), "provider": "test"},
        "gold": {"rows": _rows(2400, 2400), "provider": "test"},
        "spx": {"rows": _rows(6000, 6000), "provider": "test"},
        "soxx": {"rows": _rows(250, 250), "provider": "test"},
    }
    return SourceResult("markets", "econ", True, data)


def ok(name: str, pillar: str, data) -> SourceResult:
    return SourceResult(name, pillar, True, data)


def fail(name: str, pillar: str) -> SourceResult:
    return SourceResult(name, pillar, False, None, error="simulated outage")


def base_inputs(**over) -> dict:
    inputs = {
        "markets": calm_markets(),
        "gdelt": ok("GDELT", "geo", []),
        "rss": [ok("BBC World", "geo", []), ok("Al Jazeera", "geo", [])],
        "usgs": ok("USGS", "nat", []),
        "gdacs": ok("GDACS", "nat", []),
        "who": ok("WHO", "bio_infra", []),
        "cisa": ok("CISA", "bio_infra", []),
    }
    inputs.update(over)
    return inputs


@pytest.fixture(autouse=True)
def no_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


# ---------------------------------------------------------------- primitives

def test_piecewise_interpolates_and_clamps():
    pts = [[10, 0], [20, 50], [30, 100]]
    assert scoring.piecewise(5, pts) == 0
    assert scoring.piecewise(15, pts) == 25
    assert scoring.piecewise(99, pts) == 100


def test_aggregate_is_bounded():
    assert scoring.aggregate([]) == 0
    assert scoring.aggregate([40]) == 40
    assert scoring.aggregate([100] * 50) == 100
    assert scoring.aggregate([30] * 50) < 50  # many small events cannot fake a crisis


def test_compose_formula_cross_confirmed():
    out = scoring.compose({"econ": 50, "geo": 85, "nat": 10, "bio_infra": 10}, CFG)
    base = 0.35 * 50 + 0.35 * 85 + 0.15 * 10 + 0.15 * 10
    boost = (100 - base) * 0.65 * ((85 - 70) / 30) ** 1.3
    assert out["cross_confirmed"] is True
    assert out["base"] == pytest.approx(base, abs=0.01)
    assert out["boost"] == pytest.approx(boost, abs=0.01)
    assert out["global_score"] == min(100, round(base + boost))


def test_compose_isolated_spike_boost_capped():
    out = scoring.compose({"econ": 5, "geo": 100, "nat": 5, "bio_infra": 5}, CFG)
    assert out["cross_confirmed"] is False
    assert out["boost"] <= CFG["booster"]["isolated_cap"]


def test_compose_no_boost_below_threshold():
    out = scoring.compose({"econ": 40, "geo": 60, "nat": 20, "bio_infra": 20}, CFG)
    assert out["boost"] == 0


# ---------------------------------------------------------------- case 1: None data

def test_missing_pillar_is_excluded_not_zero():
    out = scoring.compose({"econ": None, "geo": 60, "nat": 20, "bio_infra": 20}, CFG)
    # renormalised over 0.65 weight, not dragged down by a phantom 0
    expected = (0.35 * 60 + 0.15 * 20 + 0.15 * 20) / 0.65
    assert out["base"] == pytest.approx(expected, abs=0.01)
    assert "econ" not in out["effective_weights"]
    with_zero = scoring.compose({"econ": 0, "geo": 60, "nat": 20, "bio_infra": 20}, CFG)
    assert out["base"] > with_zero["base"]


def test_missing_market_indicator_dropped_not_zeroed():
    md = calm_markets().data
    md["vix"] = None
    md["spx"] = None
    econ = scoring.score_econ(md, CFG, {}, NOW)
    vix = next(i for i in econ["indicators"] if i["key"] == "vix")
    assert vix["value"] is None and vix["score"] is None and vix["status"] == "missing"
    assert econ["score"] is not None and econ["status"] == "partial"
    assert econ["coverage"] == pytest.approx(0.5)


def test_missing_indicator_uses_last_known_value_as_stale():
    md = calm_markets().data
    md["vix"] = None
    cached = {"vix": {"last": 32.0, "change_pct": 5.0, "drawdown_pct": 0.0, "last_date": "2026-11-03",
                      "as_of": iso(NOW - timedelta(hours=6)), "provider": "test"}}
    econ = scoring.score_econ(md, CFG, cached, NOW)
    vix = next(i for i in econ["indicators"] if i["key"] == "vix")
    assert vix["status"] == "stale" and vix["value"] == 32.0 and vix["score"] > 0


def test_all_apis_none_pipeline_does_not_crash_and_never_reports_zero():
    inputs = {
        "markets": fail("markets", "econ"), "gdelt": fail("GDELT", "geo"),
        "rss": [fail("BBC", "geo")], "usgs": fail("USGS", "nat"), "gdacs": fail("GDACS", "nat"),
        "who": fail("WHO", "bio_infra"), "cisa": fail("CISA", "bio_infra"),
    }
    latest, hist, cache = build_state(inputs, CFG, {}, [], NOW)
    assert latest["global_score"] is None        # null, never a fake 0
    assert hist == []
    for p in latest["pillars"].values():
        assert p["score"] is None and p["status"] == "degraded"
    assert latest["data_status"]["key"] == "degraded"
    assert latest["summary"]["executive_summary_th"]


def test_source_outage_falls_back_to_last_valid_value():
    cache = {"last_valid": {"nat": {"score": 42.0, "as_of": iso(NOW - timedelta(hours=6))}}}
    latest, _, _ = build_state(base_inputs(usgs=fail("USGS", "nat"), gdacs=fail("GDACS", "nat")),
                               CFG, cache, [], NOW)
    assert latest["pillars"]["nat"]["score"] == 42.0
    assert latest["pillars"]["nat"]["status"] == "stale"


def test_weekend_is_market_closed_not_failure():
    saturday = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    friday = saturday - timedelta(days=1)
    md = {k: {"rows": _rows(v["rows"][0][1], v["rows"][0][1], last_day=friday), "provider": "t"}
          for k, v in calm_markets().data.items()}
    econ = scoring.score_econ(md, CFG, {}, saturday)
    assert econ["status"] == "market_closed"
    assert econ["score"] is not None


# ---------------------------------------------------------------- case 2: local earthquake

def _quake(lat, lon, mag, alert="red", tsunami=False, place="Remote region"):
    return {"id": f"usgs:{lat}{lon}", "source": "USGS", "type": "EQ", "title": f"M {mag} - {place}",
            "place": place, "mag": mag, "lat": lat, "lon": lon, "alert": alert, "tsunami": tsunami,
            "time": NOW - timedelta(hours=2), "link": "", "countries": []}


def test_strong_quake_outside_hubs_is_capped_local():
    q = _quake(-15.0, -75.0, 8.2, alert="red", place="Southern Peru")  # far from every hub
    nat = scoring.score_nat([q], CFG, NOW)
    assert nat["score"] <= CFG["nat"]["local_cap"]
    ev = nat["events"][0]
    assert ev.is_local and ev.raw_score > CFG["nat"]["local_cap"]

    latest, _, _ = build_state(base_inputs(usgs=ok("USGS", "nat", [q])), CFG, {}, [], NOW)
    calm, _, _ = build_state(base_inputs(), CFG, {}, [], NOW)
    # contribution to the world score is at most 0.15 * 30 = 4.5 points
    assert latest["global_score"] - calm["global_score"] <= 5
    assert latest["local_events"], "local quake must be surfaced in Local Event Notes"
    assert latest["summary"]["local_notes_th"]


def test_many_local_quakes_still_capped():
    qs = [_quake(-15.0 - i, -75.0, 7.8, place=f"Peru {i}") for i in range(6)]
    nat = scoring.score_nat(qs, CFG, NOW)
    assert nat["score"] <= CFG["nat"]["local_cap"]


def test_quake_near_strategic_hub_counts_fully():
    q = _quake(24.2, 120.0, 8.0, alert="red", place="Taiwan Strait")
    nat = scoring.score_nat([q], CFG, NOW)
    assert not nat["events"][0].is_local
    assert nat["score"] > CFG["nat"]["local_cap"]


def test_cross_region_tsunami_counts_fully():
    q = _quake(-15.0, -75.0, 8.6, alert="orange", tsunami=True)
    nat = scoring.score_nat([q], CFG, NOW)
    assert not nat["events"][0].is_local


# ---------------------------------------------------------------- case 3: duplicate news

def test_twenty_duplicate_articles_collapse_into_one_event():
    arts = [Article(title=f"Missile strike hits Kyiv as Russia escalates attacks ({i})", source="BBC World",
                    published=NOW - timedelta(hours=1)) for i in range(20)]
    events = scoring.group_articles(arts, CFG["geo"]["categories"], "geo", CFG["events"], NOW,
                                    great_powers=CFG["geo"]["great_powers"])
    assert len(events) == 1
    ev = events[0]
    assert ev.article_count == 20
    assert ev.score <= ev.severity  # count never inflates beyond category severity
    single = scoring.group_articles(arts[:1], CFG["geo"]["categories"], "geo", CFG["events"], NOW,
                                    great_powers=CFG["geo"]["great_powers"])
    assert single[0].score == ev.score  # 20 copies == 1 copy


def test_duplicates_do_not_push_geo_over_category_ceiling():
    arts = [Article(title="Troops massing near border, military drills reported", source="Al Jazeera",
                    published=NOW) for _ in range(20)]
    geo = scoring.score_geo(arts, CFG, {}, NOW)
    sev = next(c["severity"] for c in CFG["geo"]["categories"] if c["id"] == "mobilization")
    assert geo["score"] <= sev


def test_active_event_persists_and_decays():
    arts = [Article(title="Iran missile attack on Israel", source=s, published=NOW) for s in ("BBC", "AJ", "Reuters")]
    first = scoring.score_geo(arts, CFG, {}, NOW)
    later = NOW + timedelta(days=2)
    second = scoring.score_geo([], CFG, first["state"], later)  # nothing new reported
    assert second["events"], "event must survive past 24h"
    assert second["score"] < first["score"]
    gone = scoring.score_geo([], CFG, first["state"], NOW + timedelta(days=40))
    assert not gone["events"]


def test_word_boundaries_avoid_false_positive():
    assert scoring.classify("software award ceremony", CFG["geo"]["categories"]) is None


# ---------------------------------------------------------------- case 4: no GEMINI_API_KEY

def test_runs_without_gemini_key_and_produces_complete_thai_json():
    arts = [Article(title="Russia deploys troops, military drills near Poland border", source=s, published=NOW)
            for s in ("BBC World", "Al Jazeera", "Reuters (Google News)")]
    inputs = base_inputs(rss=[ok("BBC World", "geo", arts)],
                         usgs=ok("USGS", "nat", [_quake(-15.0, -75.0, 7.6, place="Southern Peru")]))
    latest, hist, cache = build_state(inputs, CFG, {}, [], NOW)

    s = latest["summary"]
    assert s["source"] == "template"
    assert isinstance(s["executive_summary_th"], str) and len(s["executive_summary_th"]) > 20
    assert any("฀" <= ch <= "๿" for ch in s["executive_summary_th"])  # Thai script
    assert isinstance(s["early_warnings_th"], list) and len(s["early_warnings_th"]) <= 3
    for w in s["early_warnings_th"]:
        assert set(w) == {"title", "signal_strength", "timeframe", "evidence_summary", "refs"}
        assert w["signal_strength"] in ("สูง", "ปานกลาง", "เฝ้าระวัง")
    assert isinstance(s["local_notes_th"], list) and len(s["local_notes_th"]) <= 4

    # English twin of every generated text block
    # the score and level are shown above the summary, so it must not repeat them
    for text in (s["executive_summary_th"], s["executive_summary_en"]):
        assert "/100" not in text and latest["band"]["label_th"] not in text
    assert s["executive_summary_en"].startswith("Pressure comes mainly from")
    assert len(s["early_warnings_en"]) == len(s["early_warnings_th"])
    assert len(s["local_notes_en"]) == len(s["local_notes_th"])
    for p in latest["pillars"].values():
        assert p["label_en"] and p["status_en"]
        assert all(m["label_en"] for m in p["metrics"])

    assert isinstance(latest["global_score"], int)
    assert latest["band"]["label_th"]
    assert set(latest["pillars"]) == {"econ", "geo", "nat", "bio_infra"}
    assert len(hist) == 1
    json.dumps(latest, ensure_ascii=False)  # serialisable
    json.dumps(cache, ensure_ascii=False)


def test_gemini_429_falls_back_to_template(monkeypatch):
    from gci import ai_helper

    def boom(*a, **k):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(ai_helper, "_call_gemini", boom)
    latest, _, cache = build_state(base_inputs(), CFG, {}, [], NOW)
    assert latest["summary"]["source"] == "template"
    assert latest["summary"]["executive_summary_th"]


def test_gemini_gatekeeper_skips_call_when_nothing_changed(monkeypatch):
    from gci import ai_helper
    calls = []

    def fake(ctx, key, model):
        calls.append(1)
        return {"executive_summary_th": "สรุป", "early_warnings_th": [], "local_notes_th": [],
                "executive_summary_en": "Summary", "early_warnings_en": [], "local_notes_en": []}
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(ai_helper, "_call_gemini", fake)
    _, _, cache = build_state(base_inputs(), CFG, {}, [], NOW)
    latest, _, _ = build_state(base_inputs(), CFG, cache, [], NOW + timedelta(hours=6))
    assert len(calls) == 1
    assert latest["summary"]["source"] == "gemini_cached"


def test_severe_category_requires_headline_not_body_mention():
    art = Article(title="Air raid alert apps hit by cyberattacks after truce ends", source="AJ",
                  summary="Users receive fake warnings of nuclear threats.", published=NOW)
    events = scoring.group_articles([art], CFG["geo"]["categories"], "geo", CFG["events"], NOW,
                                    great_powers=CFG["geo"]["great_powers"])
    assert all(e.category != "nuclear" for e in events)


def test_hormuz_tanker_headline_is_chokepoint():
    art = Article(title="Iran war live: Tankers hit in Hormuz", source="AJ", published=NOW)
    events = scoring.group_articles([art], CFG["geo"]["categories"], "geo", CFG["events"], NOW,
                                    great_powers=CFG["geo"]["great_powers"])
    assert events[0].category == "chokepoint"


def test_many_green_gdacs_alerts_stay_minor():
    greens = [{"id": f"gdacs:FL{i}", "source": "GDACS", "type": "FL", "title": f"Green flood alert {i}",
               "place": "X", "mag": None, "lat": -30.0, "lon": -60.0 + i * 0.01, "alert": "green",
               "tsunami": False, "time": NOW, "link": "", "countries": ["Argentina"]} for i in range(150)]
    assert scoring.score_nat(greens, CFG, NOW)["score"] < 10


# ---------------------------------------------------------------- security / robustness

def test_only_web_links_reach_the_site():
    from gci.models import Event
    ev = Event(id="x", pillar="geo", category="conflict", category_th="", title="t", severity=1, score=1,
               links=["javascript:alert(1)", "data:text/html,x", "https://ok.example/a", "HTTP://ok.example/b"])
    assert ev.to_dict()["links"] == ["https://ok.example/a", "HTTP://ok.example/b"]


def test_permanent_4xx_is_not_retried(monkeypatch):
    import requests
    from gci import http

    calls = []

    class Resp:
        status_code = 403

        def raise_for_status(self):
            raise requests.HTTPError("403", response=self)

    monkeypatch.setattr(http.requests, "get", lambda *a, **k: calls.append(1) or Resp())
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    with pytest.raises(requests.HTTPError):
        http.get("https://example.test", retries=3)
    assert len(calls) == 1


def test_rss_parser_rejects_entity_expansion():
    from gci.http import parse_rss
    bomb = b'''<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;">]>
<rss><channel><item><title>&b;</title></item></channel></rss>'''
    with pytest.raises(Exception):
        parse_rss(bomb)


def test_optional_gdelt_outage_does_not_mark_geo_delayed():
    gdelt_down = SourceResult("GDELT", "geo", False, None, error="429", optional=True)
    latest, _, _ = build_state(base_inputs(gdelt=gdelt_down), CFG, {}, [], NOW)
    assert latest["pillars"]["geo"]["status"] == "ok"
    assert latest["data_status"]["key"] == "ok"


def test_gemini_output_rules_are_enforced_in_code(monkeypatch):
    from gci import ai_helper

    def chatty(ctx, key, model):
        return {"executive_summary_th": "ดัชนีอยู่ที่ 45/100", "executive_summary_en": "The index is 45/100.",
                "early_warnings_th": [], "early_warnings_en": [],
                "local_notes_th": ["ข่าวตลาดหุ้น"], "local_notes_en": ["stock market news"]}
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(ai_helper, "_call_gemini", chatty)
    latest, _, _ = build_state(base_inputs(), CFG, {}, [], NOW)
    s = latest["summary"]
    assert s["source"] == "gemini"
    assert "/100" not in s["executive_summary_th"] and "/100" not in s["executive_summary_en"]
    assert s["local_notes_th"] == [] and s["local_notes_en"] == []  # no local events this run


def test_prompt_version_change_invalidates_cached_ai_text(monkeypatch):
    from gci import ai_helper
    calls = []

    def fake(ctx, key, model):
        calls.append(1)
        return {"executive_summary_th": "สรุป", "early_warnings_th": [], "local_notes_th": [],
                "executive_summary_en": "Summary", "early_warnings_en": [], "local_notes_en": []}
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(ai_helper, "_call_gemini", fake)
    _, _, cache = build_state(base_inputs(), CFG, {}, [], NOW)
    cache["ai"]["prompt_version"] = ai_helper.PROMPT_VERSION - 1
    build_state(base_inputs(), CFG, cache, [], NOW + timedelta(hours=6))
    assert len(calls) == 2


# ---------------------------------------------------------------- warning source links

def test_template_warnings_carry_source_links():
    arts = [Article(title="Russia deploys troops, military drills near Poland border", source=s,
                    link=f"https://{s.lower().replace(' ', '')}.example/story", published=NOW)
            for s in ("BBC World", "Al Jazeera", "Reuters (Google News)")]
    latest, _, _ = build_state(base_inputs(rss=[ok("BBC World", "geo", arts)]), CFG, {}, [], NOW)
    w = latest["summary"]["early_warnings_th"][0]
    assert w["refs"] and all(r["url"].startswith("https://") and r["source"] for r in w["refs"])
    assert len({r["source"] for r in w["refs"]}) == len(w["refs"])  # one link per outlet
    assert latest["summary"]["early_warnings_en"][0]["refs"] == w["refs"]


def _ev(eid, score, sources, category="chokepoint"):
    from gci.models import Event
    return Event(id=eid, pillar="geo", category=category, category_th="", title=eid, severity=score, score=score,
                 sources=sources, links=[f"https://{s}.example/{eid}" for s in sources], link_sources=sources)


def test_gemini_refs_come_from_our_data_not_the_model():
    from gci.ai_helper import _validate
    events = {"E1": _ev("E1", 50, ["BBC World"])}
    data = {"executive_summary_th": "ก", "executive_summary_en": "a",
            "early_warnings": [{"title_th": "ก", "title_en": "a", "signal_strength": "สูง",
                                "event_ids": ["E1", "E99"], "url": "https://evil.example"}]}
    out = _validate(data, events)
    assert out["early_warnings_th"][0]["refs"] == [{"url": "https://BBC World.example/E1", "source": "BBC World"}]
    assert "evil" not in str(out)


def test_watchlist_signal_is_computed_in_code_not_by_the_model():
    from gci.ai_helper import _validate
    events = {"E1": _ev("E1", 70, ["BBC", "AJ", "Reuters"]), "E2": _ev("E2", 45, ["BBC"], "sanctions"),
              "E3": _ev("E3", 20, ["AJ"])}

    def run(model_says):
        data = {"executive_summary_th": "ก", "executive_summary_en": "a", "early_warnings": [
            {"title_th": "a", "title_en": "a", "signal_strength": model_says, "event_ids": ["E1"]},
            {"title_th": "b", "title_en": "b", "signal_strength": model_says, "event_ids": ["E2"]},
            {"title_th": "c", "title_en": "c", "signal_strength": model_says, "event_ids": ["E3"]},
        ]}
        return [(w["signal_strength"], w["timeframe"]) for w in _validate(data, events)["early_warnings_th"]]

    expected = [("สูง", "1-4 สัปดาห์"), ("ปานกลาง", "1-3 เดือน"), ("เฝ้าระวัง", "1-4 สัปดาห์")]
    assert run("สูง") == expected
    assert run("เฝ้าระวัง") == expected  # whatever the model says, the label is the same


# ---------------------------------------------------------------- data_as_of per source

def test_source_status_reports_newest_data_time():
    older, newer = NOW - timedelta(hours=9), NOW - timedelta(hours=2)
    arts = ok("BBC", "geo", [Article("a", "BBC", published=older), Article("b", "BBC", published=newer),
                              Article("c", "BBC", published=None)])
    quakes = ok("USGS", "nat", [{"time": older}, {"time": newer}])
    st = {s.name: s.to_status() for s in (arts, quakes)}
    assert st["BBC"]["data_as_of"] == iso(newer)
    assert st["USGS"]["data_as_of"] == iso(newer)


def test_market_data_as_of_is_a_bare_date_and_failures_have_none():
    assert calm_markets().to_status()["data_as_of"] == NOW.strftime("%Y-%m-%d")
    assert fail("X", "geo").to_status()["data_as_of"] is None
    assert ok("empty", "geo", []).to_status()["data_as_of"] is None
