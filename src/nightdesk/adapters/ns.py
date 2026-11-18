"""Capture NS maintenance with source-scoped station identifiers."""

from datetime import datetime, timezone
import hashlib
import json
from urllib.parse import quote
from zoneinfo import ZoneInfo

from nightdesk.adapters.source_http import credential, read_one
from nightdesk.adapters.staging import stage_capture
from nightdesk.intake.mapping import CaptureOrigin

HOST = "gateway.apiportal.ns.nl"
URL = f"https://{HOST}/disruptions/v3?type=maintenance&isActive=false"
ZONE = ZoneInfo("Europe/Amsterdam")


def _date(raw):
    if not isinstance(raw, str):
        return None
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return value.astimezone(ZONE).date().isoformat() if value.utcoffset() is not None else None


def normalize(raw):
    data = json.loads(raw)
    if not isinstance(data, list) or any(not isinstance(row, dict) or row.get("type") != "MAINTENANCE" for row in data):
        raise ValueError("ns_maintenance_response_invalid")
    rows = []
    for row in data:
        sections = row.get("publicationSections")
        section = sections[0] if isinstance(sections, list) and len(sections) == 1 else None
        section = section.get("section") if isinstance(section, dict) else None
        stations = section.get("stations") if isinstance(section, dict) else None
        start, end = None, None
        if isinstance(stations, list) and len(stations) >= 2:
            start, end = stations[0], stations[-1]
        def station(value):
            if not isinstance(value, dict):
                return None, ""
            code = value.get("stationCode")
            label = value.get("name")
            return (quote(code, safe="") if isinstance(code, str) and code.strip() else None,
                    label if isinstance(label, str) else "")
        from_point, from_name = station(start)
        to_point, to_name = station(end)
        rows.append({**row, "nd_country": "NL", "nd_start": _date(row.get("start")), "nd_end": _date(row.get("end")),
                     "nd_from": from_point, "nd_to": to_point, "nd_from_name": from_name, "nd_to_name": to_name})
    return rows


def stage_maintenance(bundle, raw, captured_at):
    origin = CaptureOrigin(captured_at=captured_at, filter={"type": "maintenance", "isActive": False},
                           evidence={"source_url": URL, "source_file": "maintenance.json",
                                     "source_sha256": hashlib.sha256(raw).hexdigest(),
                                     "coverage": "Selected NS maintenance query; activity status retained per record.",
                                     "licence": "UNKNOWN"})
    return stage_capture(bundle, "ns-maintenance", normalize(raw), origin=origin,
                         raw_files=[("maintenance.json", raw)])


def fetch_maintenance(bundle):
    if bundle.nda:
        raise ValueError("provider_capture_requires_practice_bundle")
    body, _ = read_one(URL, {HOST}, headers={"Ocp-Apim-Subscription-Key": credential("NS_API_KEY"),
                                           "Accept": "application/json"}, limit=16 * 1024 * 1024)
    return stage_maintenance(bundle, body, datetime.now(timezone.utc))
