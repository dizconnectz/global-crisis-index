"""Shared data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z") if dt else None


def parse_iso(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class SourceResult:
    """Outcome of one fetcher. `data` is None when the source failed entirely."""
    name: str
    pillar: str
    ok: bool
    data: Any = None
    error: str | None = None
    fetched_at: datetime = field(default_factory=utcnow)
    note: str | None = None

    def to_status(self) -> dict:
        count = len(self.data) if isinstance(self.data, (list, dict)) else None
        return {
            "name": self.name,
            "pillar": self.pillar,
            "status": "ok" if self.ok else "error",
            "fetched_at": iso(self.fetched_at),
            "items": count,
            "error": self.error,
            "note": self.note,
        }


@dataclass
class Article:
    title: str
    source: str
    link: str = ""
    summary: str = ""
    published: datetime | None = None


@dataclass
class Event:
    """A deduplicated, scored event (one cluster of articles / one hazard)."""
    id: str
    pillar: str
    category: str
    category_th: str
    title: str
    severity: float          # raw category severity before corroboration
    score: float             # effective score (after corroboration, caps, decay)
    countries: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    article_count: int = 1
    links: list[str] = field(default_factory=list)
    first_seen: str | None = None
    last_seen: str | None = None
    is_local: bool = False
    location: str | None = None
    raw_score: float | None = None   # score before local cap
    is_new: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id, "pillar": self.pillar, "category": self.category,
            "category_th": self.category_th, "title": self.title,
            "severity": round(self.severity, 1), "score": round(self.score, 1),
            "countries": self.countries, "sources": self.sources,
            "article_count": self.article_count, "links": self.links[:3],
            "first_seen": self.first_seen, "last_seen": self.last_seen,
            "is_local": self.is_local, "location": self.location,
            "raw_score": None if self.raw_score is None else round(self.raw_score, 1),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(
            id=d["id"], pillar=d["pillar"], category=d["category"],
            category_th=d.get("category_th", ""), title=d.get("title", ""),
            severity=float(d.get("severity", 0)), score=float(d.get("score", 0)),
            countries=list(d.get("countries", [])), sources=list(d.get("sources", [])),
            article_count=int(d.get("article_count", 1)), links=list(d.get("links", [])),
            first_seen=d.get("first_seen"), last_seen=d.get("last_seen"),
            is_local=bool(d.get("is_local", False)), location=d.get("location"),
            raw_score=d.get("raw_score"),
        )
