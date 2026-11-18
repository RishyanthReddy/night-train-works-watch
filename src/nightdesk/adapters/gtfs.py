"""Local GTFS schedule adapter. No observed times, line inference or booked path."""
import csv
from datetime import date, datetime, time, timedelta
import hashlib
import io
from pathlib import Path
import re
import zlib
import lzma
from zipfile import ZipFile, BadZipFile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from nightdesk.audit import append_event, append_once, canonical_json
from nightdesk.config import MAX_GTFS_BYTES, MAX_GTFS_HOURS, MAX_GTFS_SERVICE_DAYS, MAX_GTFS_ROWS, PUBLIC_DEMO_BUNDLE
from nightdesk.intake.mapping import check_input, write_private, confirm_mapping, ingest
from nightdesk.timeutil import utc, localize

RULE_VERSION = 'gtfs-scheduled-v1'
ENCODED_POINT_RULE_VERSION = 'gtfs-scheduled-v2'
SPEC_URL = 'https://gtfs.org/documentation/schedule/reference/'


def gtfs_instant(day, raw, zone):
    if not raw:
        return None
    match = re.fullmatch(r'(\d{1,4}):([0-5]\d):([0-5]\d)', raw)
    if not match:
        raise ValueError('invalid_gtfs_time')
    hours, minutes, seconds = map(int, match.groups())
    if hours > MAX_GTFS_HOURS:
        raise ValueError('gtfs_time_exceeds_technical_limit')
    # GTFS Time is elapsed from service-day local noon minus twelve hours,
    # not a guessed wall-clock fold. stop_timezone does not change this basis.
    noon = localize(datetime.combine(day, time(12)), zone)
    if noon.at is None:
        raise ValueError('gtfs_service_noon_unresolved')
    return utc(noon.at) - timedelta(hours=12) + timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _table(archive, name, required=True):
    if name not in archive.namelist():
        if required:
            raise ValueError('gtfs_missing_table:' + name)
        return []
    values = list(csv.reader(io.StringIO(archive.read(name).decode('utf-8-sig'))))
    if not values or not values[0] or any(not c.strip() for c in values[0]) or len(set(values[0])) != len(values[0]):
        raise ValueError('gtfs_invalid_header:' + name)
    if any(len(row) != len(values[0]) for row in values[1:] if row):
        raise ValueError('gtfs_invalid_row_width:' + name)
    return [dict(zip(values[0], row)) for row in values[1:] if row]


def _unique(rows, key):
    result = {}
    for row in rows:
        identifier = row.get(key)
        if not identifier or identifier in result:
            raise ValueError('gtfs_missing_or_duplicate_id:' + key)
        result[identifier] = row
    return result


def _day(raw):
    try:
        if not isinstance(raw,str) or not re.fullmatch(r'\d{8}',raw): raise ValueError
        return datetime.strptime(raw, '%Y%m%d').date()
    except (ValueError, TypeError):
        raise ValueError('invalid_gtfs_service_date') from None


def service_dates(calendar, exceptions, requested=None):
    dates = {}
    names = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    for service, row in _unique(calendar, 'service_id').items():
        lo, hi = _day(row.get('start_date')), _day(row.get('end_date'))
        if hi < lo or (hi - lo).days > MAX_GTFS_SERVICE_DAYS:
            raise ValueError('gtfs_invalid_or_oversized_calendar')
        if any(row.get(name) not in {'0', '1'} for name in names):
            raise ValueError('gtfs_invalid_weekday')
        dates[service] = set()
        for offset in range((hi - lo).days + 1):
            day = lo + timedelta(days=offset)
            if row[names[day.weekday()]] == '1':
                dates[service].add(day)
    seen = set()
    for row in exceptions:
        service, day, action = row.get('service_id'), _day(row.get('date')), row.get('exception_type')
        if not service or action not in {'1', '2'} or (service, day) in seen:
            raise ValueError('gtfs_invalid_or_duplicate_calendar_exception')
        seen.add((service, day))
        dates.setdefault(service, set())
        if action == '1':
            dates[service].add(day)
        else:
            dates[service].discard(day)
    if sum(map(len, dates.values())) > MAX_GTFS_SERVICE_DAYS:
        raise ValueError('gtfs_service_dates_exceed_technical_limit')
    if requested is not None:
        dates = {service: days & requested for service, days in dates.items()}
    return dates


def normalized_rows(path, bundle, *, namespace, licence, dates=None, trip_ids=None):
    check_input(path, bundle)
    if not re.fullmatch(r'[^\s:]+', namespace):
        raise ValueError('gtfs_namespace_required')
    if not licence.strip():
        raise ValueError('gtfs_declared_licence_required')
    if Path(path).stat().st_size > MAX_GTFS_BYTES:
        raise ValueError("gtfs_archive_exceeds_technical_limit")
    raw = Path(path).read_bytes()
    if len(raw) > MAX_GTFS_BYTES:
        raise ValueError('gtfs_archive_exceeds_technical_limit')
    try:
        archive = ZipFile(io.BytesIO(raw))
        if len(set(archive.namelist())) != len(archive.namelist()) or sum(i.file_size for i in archive.infolist()) > MAX_GTFS_BYTES:
            raise ValueError('gtfs_expanded_archive_exceeds_technical_limit')
        with archive:
            if 'frequencies.txt' in archive.namelist():
                raise ValueError('gtfs_frequency_service_not_supported')
            agency = _table(archive, 'agency.txt')
            stops = _unique(_table(archive, 'stops.txt'), 'stop_id')
            routes = _unique(_table(archive, 'routes.txt'), 'route_id')
            trips = _unique(_table(archive, 'trips.txt'), 'trip_id')
            times = _table(archive, 'stop_times.txt')
            calendar = _table(archive, 'calendar.txt', False)
            exceptions = _table(archive, 'calendar_dates.txt', False)
    except (BadZipFile, KeyError, UnicodeError, csv.Error, RuntimeError, NotImplementedError, zlib.error, EOFError, lzma.LZMAError):
        raise ValueError('gtfs_unreadable_archive') from None
    if not calendar and not exceptions:
        raise ValueError('gtfs_service_calendar_required')
    zones = {row.get('agency_timezone') for row in agency}
    if len(zones) != 1 or not next(iter(zones), None):
        raise ValueError('gtfs_agency_timezone_ambiguous')
    zone = next(iter(zones))
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('gtfs_agency_timezone_invalid') from None
    for stop in stops.values():
        if stop.get('stop_timezone'):
            try:
                ZoneInfo(stop['stop_timezone'])
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError('gtfs_stop_timezone_invalid') from None
    services = service_dates(calendar, exceptions, set(dates) if dates is not None else None)
    if trip_ids is not None and not set(trip_ids) <= trips.keys():
        raise ValueError('gtfs_selected_trip_not_found')
    by_trip, sequence_keys = {}, set()
    for index, row in enumerate(times, 2):
        try:
            sequence = int(row.get('stop_sequence', ''))
        except ValueError:
            raise ValueError('gtfs_invalid_stop_sequence') from None
        trip_id = row.get('trip_id')
        if sequence < 0 or trip_id not in trips or (trip_id, sequence) in sequence_keys or row.get('stop_id') not in stops:
            raise ValueError('gtfs_invalid_stop_reference_or_sequence')
        sequence_keys.add((trip_id, sequence))
        by_trip.setdefault(trip_id, []).append((sequence, index, row))
    # Index evidence once; no per-stop scan or repeated date parsing.
    calendar_by_service = {r['service_id']: [r] for r in calendar}
    exceptions_by_day = {(r['service_id'], _day(r['date'])): [r] for r in exceptions}
    projected = sum(len(services.get(t.get('service_id'),())) * len(by_trip.get(i,()))
                    for i,t in trips.items() if trip_ids is None or i in trip_ids)
    if projected > MAX_GTFS_ROWS:
        raise ValueError('gtfs_output_exceeds_technical_limit_select_dates_or_trips')
    source_sha = hashlib.sha256(raw).hexdigest()
    output = []
    for trip_id, trip in sorted(trips.items()):
        if trip_ids is not None and trip_id not in trip_ids:
            continue
        if trip.get('route_id') not in routes or trip.get('service_id') not in services:
            raise ValueError('gtfs_trip_reference_missing')
        if services[trip['service_id']] and not by_trip.get(trip_id):
            raise ValueError('gtfs_trip_has_no_stop_times')
        for day in sorted(services[trip['service_id']]):
            prior = None
            for sequence, index, stop_time in sorted(by_trip.get(trip_id, [])):
                stop = stops[stop_time['stop_id']]
                arrival = gtfs_instant(day, stop_time.get('arrival_time', ''), zone)
                departure = gtfs_instant(day, stop_time.get('departure_time', ''), zone)
                if (arrival and departure and departure < arrival) or (prior and (arrival or departure) and (arrival or departure) < prior):
                    raise ValueError('gtfs_reversed_stop_times')
                prior = departure or arrival or prior
                stop_key = re.sub(r"[%:\s]", lambda match: "".join(f"%{byte:02X}" for byte in match[0].encode()),
                                  stop_time['stop_id'])
                output.append(dict(service_date=day.isoformat(), train_no=namespace + ':' + trip['route_id'],
                    point_id=namespace + ':' + stop_key, name=stop.get('stop_name', ''), trip_id=trip_id,
                    kind='scheduled', planned_arr=arrival.isoformat() if arrival else None,
                    planned_dep=departure.isoformat() if departure else None,
                    gtfs_evidence=dict(rule_version=ENCODED_POINT_RULE_VERSION if stop_key != stop_time['stop_id'] else RULE_VERSION,
                        spec=SPEC_URL, source_path=str(Path(path).resolve()),
                        source_sha256=source_sha, licence=licence, service_date=day.isoformat(),
                        agency=agency, calendar=calendar_by_service.get(trip['service_id'], []),
                        calendar_exception=exceptions_by_day.get((trip['service_id'],day), []),
                        stop_times_row=index, stop_time=stop_time, trip=trip, route=routes[trip['route_id']], stop=stop,
                        agency_timezone=zone, scheduled_only=True, path_unresolved=True,
                        time_basis='agency_timezone local noon minus 12 elapsed hours; HH:MM:SS may exceed 24')))
    return output, source_sha


def import_gtfs(path, bundle, *, actor, namespace, licence, dates=None, trip_ids=None):
    if bundle.name == PUBLIC_DEMO_BUNDLE:
        raise ValueError("demo_gtfs_import_requires_manifested_intake")
    if not actor.strip():
        raise ValueError('gtfs_actor_required')
    try:
        rows, sha = normalized_rows(path, bundle, namespace=namespace, licence=licence, dates=dates, trip_ids=trip_ids)
    except (ValueError, OSError):
        append_event(bundle, 'gtfs_import_refused', {'reason': 'invalid_or_unsupported_gtfs', 'actor': actor})
        raise
    rule_version = (ENCODED_POINT_RULE_VERSION
                    if any(row['gtfs_evidence']['rule_version'] == ENCODED_POINT_RULE_VERSION for row in rows)
                    else RULE_VERSION)
    scope = dict(source_sha256=sha, source_path=str(Path(path).resolve()), namespace=namespace, licence=licence,
                 dates=sorted(d.isoformat() for d in dates) if dates is not None else None,
                 trip_ids=sorted(trip_ids) if trip_ids is not None else None, rule_version=rule_version)
    selected_filter = canonical_json({'dates': scope['dates'], 'trip_ids': scope['trip_ids']})
    rows = [dict(row, adapter_selection=selected_filter) for row in rows]
    identifier = hashlib.sha256(canonical_json(scope).encode()).hexdigest()
    root = bundle.resolve(bundle.root / 'adapters' / 'gtfs' / identifier); root.mkdir(parents=True, exist_ok=True)
    normalized = root / 'rows.json'; mapping = root / 'mapping.yaml'
    fields = {name: {'column': name, 'parse': 'str'} for name in ('train_no', 'point_id', 'name', 'kind', 'trip_id')}
    fields['service_date'] = {'column': 'service_date', 'parse': 'date:%Y-%m-%d'}
    for name in ('planned_arr', 'planned_dep'):
        fields[name] = {'column': name, 'parse': 'datetime:%Y-%m-%dT%H:%M:%S%z'}
    spec = dict(version=1, dataset=namespace + '_gtfs', licence=licence, complete=True,
                external_processing_allowed=False, file={'type': 'json'}, timezone='UTC', record='RunRow',
                required=['service_date', 'train_no', 'point_id'], filter={'adapter_selection': selected_filter}, fields=fields)
    for target, text in ((normalized, canonical_json(rows) + '\n'), (mapping, canonical_json(spec) + '\n')):
        if target.exists():
            if target.read_text() != text:
                raise ValueError('gtfs_existing_normalization_differs')
        else:
            write_private(target, text)
    confirm_mapping(mapping, bundle, actor)
    result = ingest(normalized, mapping, bundle)
    append_once(bundle, "gtfs_schedule_imported", {
        "capture_id": result["capture_id"], "source_sha256": sha, "rule_version": rule_version,
    })
    return result
