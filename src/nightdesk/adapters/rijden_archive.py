"""Stage a saved Rijden de Treinen monthly archive for offline intake."""

import csv
from datetime import date, datetime, timezone
import gzip
import hashlib
from io import BytesIO
from pathlib import Path
import re
from urllib.parse import quote
import zlib

from nightdesk.adapters.staging import stage_capture
from nightdesk.intake.mapping import CaptureOrigin, check_input

SOURCE = "https://www.rijdendetreinen.nl/en/open-data/train-archive"
ATTRIBUTION = "Rijden de Treinen, Open data about train services (CC BY 4.0)"
TRAINS = {"452", "453"}
MAX_GZIP_BYTES = 64 * 1024 * 1024
MAX_CSV_BYTES = 768 * 1024 * 1024
MAX_LINE_BYTES = 128 * 1024
MAX_ES_ROWS = 20000
FIELDS = {
    "Service:RDT-ID", "Service:Date", "Service:Type", "Service:Train number",
    "Service:Completely cancelled", "Service:Partly cancelled", "Stop:RDT-ID",
    "Stop:Station code", "Stop:Station name", "Stop:Arrival time", "Stop:Departure time",
    "Stop:Arrival delay", "Stop:Departure delay", "Stop:Arrival cancelled", "Stop:Departure cancelled",
}


def _lines(compressed):
    size = 0
    with gzip.GzipFile(fileobj=BytesIO(compressed)) as stream:
        while line := stream.readline(MAX_LINE_BYTES + 1):
            size += len(line)
            if size > MAX_CSV_BYTES or len(line) > MAX_LINE_BYTES:
                raise ValueError("rijden_archive_csv_size_limit")
            yield line.decode("utf-8-sig" if size == len(line) else "utf-8")


def _minutes(value):
    if not re.fullmatch(r"[+-]?[0-9]{1,8}", value):
        return None
    return int(value)


def normalize(compressed, month):
    if not re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", month) or month.startswith("0000"):
        raise ValueError("rijden_archive_month_invalid")
    rows, stop_ids, service_keys, service_stations = [], set(), {}, set()
    try:
        reader = csv.DictReader(_lines(compressed), strict=True)
        fields = reader.fieldnames
        if not fields or len(set(fields)) != len(fields) or not FIELDS <= set(fields):
            raise ValueError("rijden_archive_header_invalid")
        for row in reader:
            if None in row or None in row.values():
                raise ValueError("rijden_archive_row_invalid")
            train = row["Service:Train number"]
            if row["Service:Type"] != "European Sleeper" or train not in TRAINS:
                continue
            day = date.fromisoformat(row["Service:Date"])
            if day.isoformat() != row["Service:Date"]:
                raise ValueError("rijden_archive_service_date_invalid")
            if day.isoformat()[:7] != month:
                continue
            service, stop, station = (row[name].strip() for name in
                                      ("Service:RDT-ID", "Stop:RDT-ID", "Stop:Station code"))
            if not all((service, stop, station)) or stop in stop_ids:
                raise ValueError("rijden_archive_stop_identity_invalid")
            key = (train, day)
            if service_keys.setdefault(service, key) != key:
                raise ValueError("rijden_archive_service_identity_conflict")
            if (service, station) in service_stations:
                raise ValueError("rijden_archive_station_repeated_in_service")
            service_stations.add((service, station))
            stop_ids.add(stop)
            arrival_delay = _minutes(row["Stop:Arrival delay"])
            departure_delay = _minutes(row["Stop:Departure delay"])
            rows.append({
                **row,
                "nd_train": f"nl-rdt:{train}",
                "nd_point": f"nl-rdt-stop:{quote(station, safe='')}",
                "nd_kind": "archived_report",
                "rdt_arrival_delay_min": arrival_delay,
                "rdt_departure_delay_min": departure_delay,
                "rdt_delay_warnings": {
                    side: "Expected whole minutes"
                    for side, value in (("Arrival", arrival_delay), ("Departure", departure_delay))
                    if value is None and row[f"Stop:{side} delay"]
                },
            })
            if len(rows) > MAX_ES_ROWS:
                raise ValueError("rijden_archive_selected_rows_limit")
    except (UnicodeError, csv.Error, EOFError, gzip.BadGzipFile, zlib.error):
        raise ValueError("rijden_archive_csv_unreadable") from None
    if not rows:
        raise ValueError("rijden_archive_no_matching_services")
    return rows


def stage_month(bundle, path, month):
    if bundle.nda:
        raise ValueError("provider_capture_requires_practice_bundle")
    check_input(path, bundle)
    with Path(path).open("rb") as source:
        raw = source.read(MAX_GZIP_BYTES + 1)
    if len(raw) > MAX_GZIP_BYTES:
        raise ValueError("rijden_archive_gzip_size_limit")
    rows = normalize(raw, month)
    origin = CaptureOrigin(
        captured_at=datetime.now(timezone.utc),
        filter={"service_month": month, "train_numbers": sorted(TRAINS)},
        evidence={
            "source_url": SOURCE,
            "source_file": "services.csv.gz",
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "licence": "CC BY 4.0",
            "attribution": ATTRIBUTION,
            "licence_url": "https://creativecommons.org/licenses/by/4.0/",
            "coverage": "Selected archive services. Times are scheduled; delays and cancellations are provider reports.",
        },
    )
    return stage_capture(bundle, "rijden-archive", rows, origin=origin,
                         raw_files=[("services.csv.gz", raw)])
