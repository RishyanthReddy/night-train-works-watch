"""Selected daily Train Archive reports, retaining prediction and delay-source evidence."""

import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import re
from urllib.parse import quote, urljoin, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from nightdesk.adapters.source_http import credential, read_one
from nightdesk.adapters.staging import stage_capture
from nightdesk.intake.mapping import CaptureOrigin
from nightdesk.timeutil import localize

CATALOGUE_HOST = "www.train-archive.eu"
DATA_HOST = "data.train-archive.eu"
DOWNLOAD_HOST = "nbg1.your-objectstorage.com"
MAX_CSV_BYTES = 160 * 1024 * 1024
MAX_SELECTED_ROWS = 20000
REQUIRED = {"provider", "feed_id", "service_date", "route", "trip_id", "trip_start_time",
            "stop_id", "stop_sequence", "stop_name", "scheduled_arrival", "scheduled_departure",
            "predicted_arrival", "predicted_departure", "delay_source"}


def source_catalogue(provider):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", provider):
        raise ValueError("archive_provider_id_invalid")
    raw, _ = read_one(f"https://{CATALOGUE_HOST}/api/sources.json", {CATALOGUE_HOST}, limit=4 * 1024 * 1024)
    data = json.loads(raw)
    sources = data.get("sources") if isinstance(data, dict) else None
    found = [s for s in sources if isinstance(s, dict) and s.get("id") == provider] if isinstance(sources, list) else []
    if len(found) != 1 or not isinstance(found[0].get("services"), dict) or "TripUpdate" not in found[0]["services"]:
        raise ValueError("archive_provider_trip_updates_unavailable")
    return found[0]


def _instant(value, zone):
    if not value:
        return None, None
    try:
        if not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}", value):
            return None, "invalid_datetime"
        parsed = datetime.fromisoformat(value)
        if parsed.microsecond:
            return None, "subsecond_datetime_unresolved"
        result = localize(parsed, zone)
        return (result.at.isoformat(), None) if result.at is not None else (None, result.reason)
    except ValueError:
        return None, "invalid_datetime"


def normalize(raw, provider, day, zone, *, trip_id=None, route=None):
    if bool(trip_id) == bool(route) or (route and not route.strip()):
        raise ValueError("archive_select_exactly_one_trip_or_route")
    try:
        ZoneInfo(zone)
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise ValueError("archive_source_timezone_unknown") from None
    rows, selected_keys = [], {}
    try:
        reader = csv.DictReader(StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        if not reader.fieldnames or not REQUIRED <= set(reader.fieldnames) or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("archive_csv_header_invalid")
        for row in reader:
            if None in row or None in row.values() or row["provider"] != provider:
                raise ValueError("archive_csv_row_or_provider_invalid")
            if row["service_date"] != day.isoformat():
                continue
            if (trip_id and row["trip_id"] != trip_id) or (route and row["route"].strip() != route.strip()):
                continue
            key = tuple(row.values())
            if key in selected_keys:
                selected_keys[key]["archive_identical_duplicates"] += 1
                continue
            feed = "/".join(quote(part, safe="") for part in (provider, row["feed_id"]))
            token = "/".join(quote(part, safe="") for part in
                             (feed, row["trip_id"], row["trip_start_time"], row.get("timetable_version", "")))
            times = {name: _instant(row[name], zone) for name in (
                "scheduled_arrival", "scheduled_departure", "predicted_arrival", "predicted_departure")}
            normalized = {**row, "nd_train": f"archive-trip:{token}" if row["trip_id"].strip() else None,
                          "nd_trip": token if row["trip_id"].strip() else None, "nd_kind": "archived_report",
                          "nd_point": f"archive-stop:{feed}/{quote(row['stop_id'], safe='')}" if row["stop_id"].strip() else None,
                          "archive_identical_duplicates": 0,
                          "archive_time_warnings": {name: reason for name, (_, reason) in times.items() if reason},
                          **{f"nd_{name}": instant for name, (instant, _) in times.items()}}
            rows.append(normalized)
            selected_keys[key] = normalized
            if len(rows) > MAX_SELECTED_ROWS:
                raise ValueError("archive_selected_rows_limit")
    except (UnicodeError, csv.Error):
        raise ValueError("archive_csv_invalid") from None
    return rows


def stage_daily(bundle, raw, source, day, captured_at, *, trip_id=None, route=None, redirect_host=None):
    provider, zone = source["id"], source.get("timezone")
    url = f"https://{DATA_HOST}/daily/provider={provider}/service=TripUpdate/date={day.isoformat()}.csv.gz"
    rows = normalize(raw, provider, day, zone, trip_id=trip_id, route=route)
    origin = CaptureOrigin(captured_at=captured_at, filter={"provider": provider, "service_date": day.isoformat(),
                               "trip_id": trip_id, "route": route},
                           evidence={"source_url": url, "source_file": "trip-updates.csv",
                                     "source_sha256": hashlib.sha256(raw).hexdigest(), "redirect_host": redirect_host,
                                     "source_timezone": zone, "catalogue_licence": source.get("licence"),
                                     "licence": "UNKNOWN",
                                     "coverage": "Selected archive report. Predictions and carried-forward delay are source reports."})
    return stage_capture(bundle, "train-archive", rows, origin=origin, raw_files=[("trip-updates.csv", raw)])


def fetch_daily(bundle, provider, day, *, trip_id=None, route=None):
    if bundle.nda:
        raise ValueError("provider_capture_requires_practice_bundle")
    source = source_catalogue(provider)
    url = f"https://{DATA_HOST}/daily/provider={provider}/service=TripUpdate/date={day.isoformat()}.csv.gz"
    body, redirect = read_one(url, {DATA_HOST}, headers={"X-Api-Key": credential("TRAIN_ARCHIVE_TOKEN")},
                              limit=MAX_CSV_BYTES, allow_redirect=True)
    redirect_host = None
    if redirect:
        target = urljoin(url, redirect)
        redirect_host = urlsplit(target).netloc
        body, _ = read_one(target, {DATA_HOST, DOWNLOAD_HOST}, limit=MAX_CSV_BYTES)
    return stage_daily(bundle, body, source, day, datetime.now(timezone.utc),
                       trip_id=trip_id, route=route, redirect_host=redirect_host)
