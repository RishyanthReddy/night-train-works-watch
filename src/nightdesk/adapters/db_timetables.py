"""One Deutsche Bahn station's schedule and published changes."""

from datetime import date, datetime, timezone
from collections import defaultdict
import hashlib
import re
from urllib.parse import quote

from nightdesk.adapters.source_http import credential, parse_xml, read_one
from nightdesk.adapters.staging import stage_capture
from nightdesk.intake.mapping import CaptureOrigin

HOST = "apis.deutschebahn.com"
BASE = f"https://{HOST}/db-api-marketplace/apis/timetables/v1"
MAX_XML_BYTES = 16 * 1024 * 1024


def endpoints(eva, day, hour):
    if not re.fullmatch(r"[0-9]{7}", eva) or not 0 <= hour <= 23:
        raise ValueError("db_station_or_hour_invalid")
    return {"plan": f"{BASE}/plan/{eva}/{day:%y%m%d}/{hour:02d}", "fchg": f"{BASE}/fchg/{eva}"}


def _stops(raw, eva):
    root = parse_xml(raw)
    if root.tag != "timetable" or (root.get("eva") and root.get("eva") != eva):
        raise ValueError("db_timetable_station_mismatch")
    result = {}
    for stop in root.findall("s"):
        identifier = stop.get("id")
        if not identifier or identifier in result or (stop.get("eva") and stop.get("eva") != eva):
            raise ValueError("db_timetable_stop_invalid_or_duplicate")
        result[identifier] = stop
    return root.get("station"), result


def _attributes(stop, tag):
    child = stop.find(tag) if stop is not None else None
    return dict(child.attrib) if child is not None else {}


def normalize(plan, changes, eva):
    planned_name, planned = _stops(plan, eva)
    changed_name, changed = _stops(changes, eva)
    if planned_name and changed_name and planned_name != changed_name:
        raise ValueError("db_timetable_station_mismatch")
    rows = []
    labels_by_trip = defaultdict(set)
    published_trips = set()
    for identifier in sorted(planned.keys() | changed.keys()):
        parts = identifier.rsplit("-", 2)
        trip, departure, sequence = parts if len(parts) == 3 else ("", "", "")
        service_date = None
        if trip and re.fullmatch(r"[0-9]{10}", departure) and re.fullmatch(r"[0-9]+", sequence):
            try:
                service_date = datetime.strptime(departure, "%y%m%d%H%M").date().isoformat()
            except ValueError:
                pass
        left, right = planned.get(identifier), changed.get(identifier)
        left_label, right_label = _attributes(left, "tl"), _attributes(right, "tl")
        label = right_label or left_label
        trip_id = f"{trip}-{departure}" if service_date is not None else None
        if trip_id:
            for member_label in (left_label, right_label):
                if member_label.get("n"):
                    text = f"{member_label.get('o', '')}/{member_label.get('c', '')}/{member_label['n']}"
                    labels_by_trip[trip_id].add("de-db:" + quote(text, safe=""))
            if right is not None:
                published_trips.add(trip_id)
        ar, dp = _attributes(left, "ar"), _attributes(left, "dp")
        ar_new, dp_new = _attributes(right, "ar"), _attributes(right, "dp")
        rows.append({
            "service_date": service_date, "point_id": eva, "trip_id": trip_id,
            "name": planned_name or changed_name or "",
            "planned_arr": ar.get("pt") or ar_new.get("pt"), "planned_dep": dp.get("pt") or dp_new.get("pt"),
            "published_arr": ar_new.get("ct"), "published_dep": dp_new.get("ct"),
            "db_stop_id": identifier, "db_stop_sequence": sequence, "db_trip_label": label,
            "db_planned_trip_label": left_label, "db_changed_trip_label": right_label,
            "db_planned_arrival": ar, "db_planned_departure": dp,
            "db_changed_arrival": ar_new, "db_changed_departure": dp_new,
            "db_in_plan": left is not None, "db_in_full_changes": right is not None,
            "db_change_messages": [dict(node.attrib) for node in right.findall("m")] if right is not None else [],
        })
    for row in rows:
        trip_id = row["trip_id"]
        labels = labels_by_trip.get(trip_id, set())
        row["train_no"] = next(iter(labels)) if len(labels) == 1 else (
            "de-db-trip:" + quote(trip_id, safe="") if trip_id else None)
        row["kind"] = "published" if trip_id in published_trips else "scheduled"
        row["db_trip_label_conflict"] = len(labels) > 1
    return rows


def stage_timetables(bundle, eva, day, hour, captures):
    paths = endpoints(eva, day, hour)
    evidence = {kind: {"source_url": paths[kind], "source_file": kind + ".xml",
                       "source_sha256": hashlib.sha256(body).hexdigest(), "fetched_at": fetched.isoformat()}
                for kind, (body, fetched) in captures.items()}
    origin = CaptureOrigin(captured_at=max(fetched for _, fetched in captures.values()),
                           filter={"eva": eva, "plan_date": day.isoformat(), "plan_hour": hour,
                                   "changes_scope": "full_station"},
                           evidence={**evidence, "licence": "UNKNOWN",
                                     "coverage": "The plan covers one station and hour. Published changes can include other hours or days."})
    rows = normalize(captures["plan"][0], captures["fchg"][0], eva)
    return stage_capture(bundle, "db-timetables", rows, origin=origin,
                         raw_files=[(kind + ".xml", body) for kind, (body, _) in captures.items()])


def fetch_timetables(bundle, eva, day: date, hour: int):
    if bundle.nda:
        raise ValueError("provider_capture_requires_practice_bundle")
    paths = endpoints(eva, day, hour)
    headers = {"DB-Client-Id": credential("DB_CLIENT_ID"), "DB-Api-Key": credential("DB_API_KEY"),
               "Accept": "application/xml"}
    captures = {}
    for kind, url in paths.items():
        raw, _ = read_one(url, {HOST}, headers=headers, limit=MAX_XML_BYTES)
        captures[kind] = raw, datetime.now(timezone.utc)
    return stage_timetables(bundle, eva, day, hour, captures)
