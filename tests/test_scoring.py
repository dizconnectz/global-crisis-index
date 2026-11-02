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
        assert set(w) == {"title", "signal_strength", "timeframe", "evidence_summary"}
        assert w["signal_strength"] in ("สูง", "ปานกลาง", "เฝ้าระวัง")
    assert isinstance(s["local_notes_th"], list) and len(s["local_notes_th"]) <= 4

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
        return {"executive_summary_th": "สรุป", "early_warnings_th": [], "local_notes_th": []}
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
