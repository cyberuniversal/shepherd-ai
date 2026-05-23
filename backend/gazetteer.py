import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


GAZETTEER_SCHEMA = "shepherd_gazetteer/1.0"
GAZETTEER_PATH_ENV = "SHEPHERD_GAZETTEER_PATH"
DEFAULT_GAZETTEER_PATH = Path(__file__).resolve().parents[1] / "data" / "gazetteer" / "riyadh_seed.jsonl"


@dataclass(frozen=True)
class GazetteerRecord:
    id: str
    name: str
    aliases: tuple[str, ...]
    lat: float
    lng: float
    source: str
    notes: str = ""

    @property
    def normalized_aliases(self) -> tuple[str, ...]:
        aliases = [self.name, *self.aliases]
        return tuple(dict.fromkeys(normalize_place_name(alias) for alias in aliases if normalize_place_name(alias)))


def normalize_place_name(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def get_gazetteer_path(path: str | Path | None = None) -> Path:
    configured = path or os.getenv(GAZETTEER_PATH_ENV) or DEFAULT_GAZETTEER_PATH
    return Path(configured).expanduser().resolve()


@lru_cache(maxsize=8)
def load_gazetteer(path: str | Path | None = None) -> tuple[GazetteerRecord, ...]:
    gazetteer_path = get_gazetteer_path(path)
    records: list[GazetteerRecord] = []
    with gazetteer_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            try:
                lat = float(payload["lat"])
                lng = float(payload["lng"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid gazetteer coordinates at {gazetteer_path}:{line_number}") from exc
            if not -90 <= lat <= 90 or not -180 <= lng <= 180:
                raise ValueError(f"Gazetteer coordinates out of range at {gazetteer_path}:{line_number}")
            aliases = tuple(str(alias) for alias in payload.get("aliases", []) if str(alias).strip())
            records.append(
                GazetteerRecord(
                    id=str(payload["id"]),
                    name=str(payload["name"]),
                    aliases=aliases,
                    lat=lat,
                    lng=lng,
                    source=str(payload.get("source") or "local_gazetteer"),
                    notes=str(payload.get("notes") or ""),
                )
            )
    return tuple(records)


def get_known_location_map(path: str | Path | None = None) -> dict[str, tuple[float, float]]:
    return {
        alias: (record.lat, record.lng)
        for record in load_gazetteer(path)
        for alias in record.normalized_aliases
    }


def resolve_place_name(query: str, path: str | Path | None = None) -> dict:
    normalized_query = normalize_place_name(query)
    if not normalized_query or normalized_query in {"unknown", "undefined", "none", "null"}:
        return _unresolved(query, reason="missing_target")

    records = load_gazetteer(path)
    alias_matches = []
    for record in records:
        if normalized_query in record.normalized_aliases:
            alias_matches.append((record, "exact_alias", normalized_query))

    if not alias_matches:
        alias_matches = list(_contained_alias_matches(normalized_query, records))

    if len(alias_matches) == 1:
        record, match_kind, matched_alias = alias_matches[0]
        return {
            "resolved": True,
            "schema": GAZETTEER_SCHEMA,
            "lat": record.lat,
            "lng": record.lng,
            "source": "local_gazetteer",
            "label": normalize_place_name(record.name),
            "display_name": record.name,
            "gazetteer_id": record.id,
            "query": query,
            "match": {"kind": match_kind, "alias": matched_alias},
        }

    if len(alias_matches) > 1:
        return _unresolved(
            query,
            reason="ambiguous_target",
            candidates=[_candidate(record, match_kind, matched_alias) for record, match_kind, matched_alias in alias_matches],
        )

    return _unresolved(query, reason="not_found")


def _contained_alias_matches(
    normalized_query: str,
    records: Iterable[GazetteerRecord],
) -> Iterable[tuple[GazetteerRecord, str, str]]:
    if len(normalized_query) < 4:
        return
    for record in records:
        for alias in record.normalized_aliases:
            if len(alias) < 4:
                continue
            if alias in normalized_query or normalized_query in alias:
                yield record, "contained_alias", alias
                break


def _candidate(record: GazetteerRecord, match_kind: str, matched_alias: str) -> dict:
    return {
        "gazetteer_id": record.id,
        "label": normalize_place_name(record.name),
        "display_name": record.name,
        "lat": record.lat,
        "lng": record.lng,
        "match": {"kind": match_kind, "alias": matched_alias},
    }


def _unresolved(query: str, *, reason: str, candidates: list[dict] | None = None) -> dict:
    return {
        "resolved": False,
        "schema": GAZETTEER_SCHEMA,
        "source": "local_gazetteer",
        "label": normalize_place_name(query) or "unknown",
        "query": query,
        "reason": reason,
        "candidates": candidates or [],
    }
