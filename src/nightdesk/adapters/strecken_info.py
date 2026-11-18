"""Offline intake of saved strecken-info.de construction records."""

from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from nightdesk.adapters.staging import stage_capture
from nightdesk.intake.mapping import CaptureOrigin, check_input

WORKS_URL = "https://strecken-info.de/api/baustellen"
MAX_WORKS_BYTES = 96 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
ZONE = ZoneInfo("Europe/Berlin")


def _read(path, limit):
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError("strecken_info_snapshot_too_large")
    return data


def _code(value):
    return quote(value.strip(), safe="") if isinstance(value, str) and value.strip() else None


def _day(value):
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value).isoformat()
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() is not None:
            parsed = parsed.astimezone(ZONE)
        return parsed.date().isoformat()
    except ValueError:
        return None


def stage_works(bundle, manifest_path):
    """Verify the supplied raw file, retaining its original time and filter."""
    if bundle.nda:
        raise ValueError("provider_capture_requires_practice_bundle")
    manifest_path = Path(manifest_path)
    check_input(manifest_path, bundle)
    manifest_bytes = _read(manifest_path, MAX_MANIFEST_BYTES)
    manifest = json.loads(manifest_bytes)
    if (not isinstance(manifest, dict) or manifest.get("source") != "strecken-info.de"
            or manifest.get("complete") is not False or not isinstance(manifest.get("filter"), dict)
            or not isinstance(manifest.get("files"), list)):
        raise ValueError("strecken_info_manifest_invalid")
    works = [item for item in manifest["files"]
             if isinstance(item, dict) and item.get("file") == "baustellen.json"]
    if len(works) != 1 or works[0].get("url") != WORKS_URL or works[0].get("status") != 200:
        raise ValueError("strecken_info_works_evidence_missing")
    source = works[0]
    raw_path = manifest_path.parent / "baustellen.json"
    check_input(raw_path, bundle)
    raw = _read(raw_path, MAX_WORKS_BYTES)
    sha = hashlib.sha256(raw).hexdigest()
    if (sha, len(raw)) != (source.get("sha256"), source.get("bytes")):
        raise ValueError("strecken_info_works_hash_or_length_mismatch")
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != source.get("records") or not all(isinstance(r, dict) for r in rows):
        raise ValueError("strecken_info_works_record_count_mismatch")
    revision = manifest.get("revision")
    origin = CaptureOrigin(captured_at=source.get("fetched_at"), filter=manifest["filter"], evidence={
        "source_url": WORKS_URL, "source_file": "baustellen.json", "source_sha256": sha,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "works_data_as_of": revision.get("baustellenDatenstand") if isinstance(revision, dict) else None,
        "coverage": "partial", "licence": "UNKNOWN",
    })
    normalized = []
    for row in rows:
        validity = row.get("zeitraum")
        lines = row.get("streckennummern")
        # Keep all source periods. A multi-period work cannot be faithfully
        # represented by one canonical clock or a single recurrence rule.
        normalized.append({**row, "nd_country": "DE",
                           "nd_start": _day(validity.get("beginn")) if isinstance(validity, dict) else None,
                           "nd_end": _day(validity.get("ende")) if isinstance(validity, dict) else None,
                           "nd_line": _code(str(lines[0])) if isinstance(lines, list) and len(lines) == 1
                                      and isinstance(lines[0], (str, int)) else None,
                           "nd_from": _code(row.get("ril100Von")), "nd_to": _code(row.get("ril100Bis"))})
    return stage_capture(bundle, "strecken-info", normalized, origin=origin,
                         raw_files=[("manifest.json", manifest_bytes), ("baustellen.json", raw)])
