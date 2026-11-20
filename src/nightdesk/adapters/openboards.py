"""One Deutsche Bahn station's current departure and arrival boards (OpenBoards).

OpenBoards replaces the retired Timetables API. It answers a small POST per
board and returns JSON: each stop carries a scheduled time and, when the
operator has a live figure, a real time beside it. Nothing here decides what a
difference means; the two timestamps are kept side by side and labelled.
"""

from datetime import datetime, timezone
import hashlib
import json
import re

from nightdesk.adapters.source_http import credential, read_one_post
from nightdesk.adapters.staging import stage_capture
from nightdesk.intake.mapping import CaptureOrigin

HOST = "apis.deutschebahn.com"
BASE = f"https://{HOST}/db-api-marketplace/apis/open-boards/v1"
BOARDS = ("departures", "arrivals")
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_RESULTS = 500


def board_url(kind):
    if kind not in BOARDS:
        raise ValueError("db_board_kind_invalid")
    return f"{BASE}/{kind}"


def request_body(eva, limit, planned_time=None):
    """The request the board accepts: one station, a start instant, a page size per train type.

    `limit` is the board's own per-transport-type cap, so one pull returns at most
    `limit` times the number of train types running there.
    """
    if not re.fullmatch(r"[0-9]{7}", eva):
        raise ValueError("db_station_invalid")
    if not 1 <= limit <= MAX_RESULTS:
        raise ValueError("db_board_limit_invalid")
    start = planned_time or datetime.now().astimezone()
    return json.dumps({
        "stopPlaceOrStation": {"evaNumbers": [eva]},
        "timeWindow": {"timeStart": start.isoformat(timespec="seconds")},
        "maxViaStops": 2,
        "maxEntriesPerTransportType": limit,
        "languages": ["deu"],
    }).encode("utf-8")


def _allowed_stops(payload, eva):
    """The station asked for, plus the sub-stops the response says belong to it.

    A large station answers with platform-level eva numbers rather than its own
    (Berlin Hbf reports 8089021 and 8098160). Those are listed in the response,
    so a stop outside that set is a real mismatch and inside it is expected.
    """
    allowed = {eva}
    meta = payload.get("meta") or {}
    for place in meta.get("consideredStopPlaces") or []:
        if isinstance(place, str):
            allowed.add(place)
    for place in payload.get("stopPlaces") or []:
        if isinstance(place, dict) and place.get("evaNumber"):
            allowed.add(place["evaNumber"])
    return allowed


def _board(raw, kind, eva):
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("db_board_json_invalid") from None
    if not isinstance(payload, dict):
        raise ValueError("db_board_json_invalid")
    stops = payload.get(kind)
    if not isinstance(stops, list):
        raise ValueError("db_board_json_invalid")
    allowed = _allowed_stops(payload, eva)
    rows, seen = [], set()
    for stop in stops:
        if not isinstance(stop, dict):
            raise ValueError("db_board_json_invalid")
        if stop.get("evaNumber") and stop["evaNumber"] not in allowed:
            raise ValueError("db_board_station_mismatch")
        journey = (stop.get("journeyInfo") or {}).get("headerJourneyNumber")
        transport = stop.get("transport") or {}
        schedule = stop.get("timeSchedule")
        real = stop.get("time") if stop.get("timeType") == "REAL" else None
        row = {
            "kind": "observed" if real else "scheduled",
            "service_date": schedule[:10] if isinstance(schedule, str) and len(schedule) >= 10 else None,
            "point_id": eva,
            "trip_id": stop.get("journeyId"),
            "train_no": (f"de-db:{transport.get('administrationId', '')}/"
                         f"{transport.get('category', '')}/{transport.get('journeyNumber') or journey}"
                         if transport else None),
            "name": _station_name(payload),
            "planned_time": schedule,
            "observed_time": real,
            "planned_platform": (stop.get("platformSchedule") or {}).get("name"),
            "observed_platform": (stop.get("platform") or {}).get("name"),
            "db_board_kind": kind,
            "db_departure_id": stop.get("departureId"),
            "db_stop_place": stop.get("evaNumber"),
            "db_time_type": stop.get("timeType"),
            "db_messages": stop.get("messages") or [],
        }
        fingerprint = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        rows.append(row)
    return rows


def _station_name(payload):
    stations = payload.get("stations") or []
    first = stations[0] if stations and isinstance(stations[0], dict) else {}
    names = first.get("localizedNames") or []
    for name in names:
        if isinstance(name, dict) and name.get("name"):
            return name["name"]
    return ""


def normalize(raw_by_kind, eva):
    rows = []
    for kind in BOARDS:
        if kind in raw_by_kind:
            rows.extend(_board(raw_by_kind[kind], kind, eva))
    return rows


def stage_boards(bundle, eva, limit, captures):
    evidence = {kind: {"source_url": board_url(kind), "source_file": kind + ".json",
                       "source_sha256": hashlib.sha256(body).hexdigest(),
                       "fetched_at": fetched.isoformat()}
                for kind, (body, fetched) in captures.items()}
    origin = CaptureOrigin(
        captured_at=max(fetched for _, fetched in captures.values()),
        filter={"eva": eva, "max_results": limit},
        evidence={**evidence, "licence": "UNKNOWN",
                  "coverage": "A board is a short window of stops at one station, not a timetable. "
                              "A train absent from it has not been shown to be cancelled."})
    rows = normalize({kind: body for kind, (body, _) in captures.items()}, eva)
    return stage_capture(bundle, "db-openboards", rows, origin=origin,
                         raw_files=[(kind + ".json", body) for kind, (body, _) in captures.items()])


def fetch_boards(bundle, eva, limit: int, planned_time: datetime | None = None):
    if bundle.nda:
        raise ValueError("provider_capture_requires_practice_bundle")
    headers = {"DB-Client-Id": credential("DB_CLIENT_ID"), "DB-Api-Key": credential("DB_API_KEY"),
               "Content-Type": "application/json", "Accept": "application/json"}
    body = request_body(eva, limit, planned_time)
    captures = {}
    for kind in BOARDS:
        raw = read_one_post(board_url(kind), {HOST}, headers=headers, body=body, limit=MAX_JSON_BYTES)
        captures[kind] = raw, datetime.now(timezone.utc)
    return stage_boards(bundle, eva, limit, captures)
