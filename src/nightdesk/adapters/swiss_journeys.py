"""Swiss SIRI mode evidence from exact dated journeys in official GTFS releases."""

from collections import defaultdict
import csv
import hashlib
from io import BytesIO, TextIOWrapper
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import zlib

from nightdesk.adapters.gtfs import _day, _table, _unique
from nightdesk.intake.mapping import check_input

MAX_ZIP = 350 * 1024 * 1024
TABLE_LIMITS = {"feed_info.txt": 4096, "routes.txt": 4 * 1024**2, "trips.txt": 400 * 1024**2,
                "calendar.txt": 12 * 1024**2, "calendar_dates.txt": 320 * 1024**2}
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
TERMS = "https://opentransportdata.swiss/en/terms-of-use/"
RAIL_TYPES = {"2", *(str(code) for code in range(100, 118))}


def read_reference(path, bundle):
    check_input(path, bundle)
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_ZIP + 1)
    if len(raw) > MAX_ZIP:
        raise ValueError("swiss_gtfs_reference_too_large")
    return raw


def _stream(archive, name, fields, *, required):
    if name not in archive.namelist():
        if required:
            raise ValueError("swiss_gtfs_reference_missing_table")
        return
    with TextIOWrapper(archive.open(name), encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle, strict=True)
        if not rows.fieldnames or not fields <= set(rows.fieldnames) or len(rows.fieldnames) != len(set(rows.fieldnames)):
            raise ValueError("swiss_gtfs_reference_bad_header")
        for row in rows:
            if None in row or None in row.values():
                raise ValueError("swiss_gtfs_reference_bad_row")
            yield row


def dated_modes(raw, wanted):
    """Return exact (SJYID, day) matches; calendars and exceptions must support the day."""
    try:
        with ZipFile(BytesIO(raw)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or any(info.file_size > TABLE_LIMITS[info.filename]
                    for info in archive.infolist() if info.filename in TABLE_LIMITS):
                raise ValueError("swiss_gtfs_reference_table_limit")
            feed, = _table(archive, "feed_info.txt")
            first, last = _day(feed["feed_start_date"]), _day(feed["feed_end_date"])
            if not feed["feed_version"] or not feed["feed_publisher_name"] or first > last:
                raise ValueError("swiss_gtfs_reference_invalid_feed_info")
            routes = _unique(_table(archive, "routes.txt"), "route_id")
            calendars = _unique(_table(archive, "calendar.txt", required=False), "service_id")
            relevant = defaultdict(set)
            for journey, day in wanted:
                if first <= day <= last:
                    relevant[journey].add(day)
            candidates = defaultdict(list)
            dates = {day.strftime("%Y%m%d"): day for days in relevant.values() for day in days}
            fields = {"original_trip_id", "route_id", "service_id", "trip_id"}
            for trip in _stream(archive, "trips.txt", fields, required=True):
                sjyid = trip["original_trip_id"]
                if sjyid in relevant:
                    route = routes[trip["route_id"]]
                    candidates[trip["service_id"]].append((sjyid, trip["trip_id"], route))
            exceptions = {}
            for row in _stream(archive, "calendar_dates.txt", {"service_id", "date", "exception_type"}, required=False):
                if row["service_id"] not in candidates or row["date"] not in dates:
                    continue
                key = (row["service_id"], dates[row["date"]])
                if key in exceptions or row["exception_type"] not in {"1", "2"}:
                    raise ValueError("swiss_gtfs_reference_invalid_exception")
                exceptions[key] = row["exception_type"] == "1"
            matches = defaultdict(set)
            for service, trips in candidates.items():
                calendar = calendars.get(service)
                start, end = (_day(calendar[key]) for key in ("start_date", "end_date")) if calendar else (None, None)
                for journey, trip_id, route in trips:
                    for day in relevant[journey]:
                        active = exceptions.get((service, day))
                        if active is None:
                            active = calendar and start <= day <= end and calendar[WEEKDAYS[day.weekday()]] == "1"
                        if active:
                            matches[journey, day].add((trip_id, route["route_id"], route["route_type"]))
    except (BadZipFile, UnicodeError, KeyError, csv.Error, RuntimeError, NotImplementedError, zlib.error):
        raise ValueError("swiss_gtfs_reference_invalid") from None
    return matches, {"sha256": hashlib.sha256(raw).hexdigest(), "publisher": feed["feed_publisher_name"],
                     "version": feed["feed_version"], "first_day": first.isoformat(), "last_day": last.isoformat(),
                     "terms": TERMS}
