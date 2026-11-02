"""Global Crisis Index (GCI) pipeline package."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "scoring_rules.json"
LATEST_PATH = ROOT / "public" / "data" / "latest_state.json"
HISTORY_PATH = ROOT / "public" / "data" / "history.json"
CACHE_PATH = ROOT / "data" / "state_cache.json"
