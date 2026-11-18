"""Swiss planned SIRI-SX. Only situations explicitly scoped to rail enter intake."""

from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
from io import BytesIO
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

from nightdesk.adapters.source_http import check_xml, credential, read_one
from nightdesk.adapters.staging import stage_capture
from nightdesk.adapters.swiss_journeys import RAIL_TYPES, TERMS, dated_modes, read_reference
from nightdesk.intake.mapping import CaptureOrigin

HOST = "api.opentransportdata.swiss"
DOWNLOAD_HOST = "largeapi.opentransportdata.swiss"
URL = f"https://{HOST}/la/siri-sx"
MAX_XML_BYTES = 200 * 1024 * 1024
ZONE = ZoneInfo("Europe/Zurich")
REQUEST_HEADERS = {"Accept": "application/xml", "User-Agent": "Nightdesk/0.1"}


def _name(node):
    return node.tag.rsplit("}", 1)[-1]


def _text(node):
    return (node.text or "").strip()


def _field(node, name):
    return next((_text(child) for child in node if _name(child) == name and _text(child)), None)


def _day(value):
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed.astimezone(ZONE).date().isoformat() if parsed.utcoffset() is not None else None


def _declared_modes(item):
    evidence = [node for node in item.iter() if _name(node) == "Affects"]
    modes = {_text(child).casefold() for node in evidence for child in node.iter()
             if _name(child) in {"VehicleMode", "PtMode"} and _text(child)}
    explicit_rail_submode = any(_name(child) == "RailSubmode" and _text(child)
                                for node in evidence for child in node.iter())
    if not modes and explicit_rail_submode:
        modes.add("rail")
    return modes


def _journeys(item):
    references = set()
    for scope in item.iter():
        if _name(scope) != "Affects":
            continue
        for frame in scope.iter():
            if _name(frame) != "FramedVehicleJourneyRef":
                continue
            journey = _field(frame, "DatedVehicleJourneyRef")
            raw_day = _field(frame, "DataFrameRef")
            if journey and journey.startswith("ch:1:sjyid:") and raw_day and len(raw_day) == 10:
                try:
                    references.add((journey, date.fromisoformat(raw_day)))
                except ValueError:
                    continue
    return references


def _parse(raw, use_references):
    check_xml(raw)
    rows, counted = [], 0
    found_delivery = False
    try:
        for _, item in ElementTree.iterparse(BytesIO(raw), events=("end",)):
            name = _name(item)
            if name == "SituationExchangeDelivery":
                found_delivery = True
                if (_field(item, "Status") or "").casefold() in {"false", "0"}:
                    raise ValueError("swiss_siri_delivery_refused")
            if name != "PtSituationElement":
                continue
            counted += 1
            modes = _declared_modes(item)
            if (_field(item, "Planned") or "").casefold() in {"true", "1"}:
                periods = [{"start": _field(p, "StartTime"), "end": _field(p, "EndTime")}
                           for p in item if _name(p) == "ValidityPeriod"]
                starts = [_day(p["start"]) for p in periods]
                ends = [_day(p["end"]) for p in periods]
                participant, situation = _field(item, "ParticipantRef"), _field(item, "SituationNumber")
                row = {"id": situation if participant is None or situation is None else f"{participant}/{situation}",
                             "country": "CH", "start": min(starts) if starts and all(starts) else None,
                             "end": max(ends) if ends and all(ends) else None,
                             "description": _field(item, "Description") or _field(item, "Summary") or "",
                             "siri_situation_number": situation, "siri_participant_ref": participant,
                             "siri_validity_periods": periods, "siri_declared_modes": sorted(modes),
                             "siri_source_situation": counted}
                rows.append((row, _journeys(item) if use_references and not modes else set()))
            item.clear()
    except (ElementTree.ParseError, LookupError):
        raise ValueError("swiss_siri_invalid_xml") from None
    if not found_delivery:
        raise ValueError("swiss_siri_delivery_missing")
    return rows, counted


def _classify(raw, references):
    planned, counted = _parse(raw, bool(references))
    wanted = {ref for _, journeys in planned for ref in journeys}
    dated = defaultdict(set)
    sources = []
    for index, reference in enumerate(references, 1):
        matches, origin = dated_modes(reference, wanted)
        sources.append({**origin, "source_file": f"gtfs-reference-{index}.zip"})
        for key, rows in matches.items():
            dated[key].update((*row, origin["sha256"]) for row in rows)

    accepted = []
    unresolved = mixed = 0
    for row, journeys in planned:
        declared = row["siri_declared_modes"]
        if declared:
            if "rail" in declared:
                mixed += len(declared) > 1
                accepted.append(row)
            continue
        examples, resolved = {}, 0
        for journey, day in sorted(journeys):
            evidence = dated.get((journey, day), set())
            # Multiple reference releases may repeat the exact same trip.
            if len({(trip, route, kind) for trip, route, kind, _ in evidence}) != 1:
                continue
            trip, route, route_type, source_hash = min(evidence)
            if not route_type.isdecimal():
                continue
            mode = "rail" if route_type in RAIL_TYPES else "non_rail"
            resolved += 1
            examples.setdefault(mode, {"sjyid": journey, "service_date": day.isoformat(),
                                       "gtfs_trip_id": trip, "gtfs_route_id": route,
                                       "route_type": route_type, "source_sha256": source_hash})
        if not examples:
            unresolved += 1
        if "rail" in examples:
            row["siri_dated_mode_evidence"] = {"examples": examples, "journeys_resolved": resolved,
                                              "journeys_unresolved": len(journeys) - resolved}
            mixed += "non_rail" in examples
            accepted.append(row)
    return accepted, counted, sources, unresolved, mixed


def normalize(raw):
    rows, counted, *_ = _classify(raw, ())
    return rows, counted


def fetch_siri(bundle, *, gtfs_paths=()):
    if bundle.nda:
        raise ValueError("provider_capture_requires_practice_bundle")
    if len(gtfs_paths) > 2:
        raise ValueError("swiss_gtfs_reference_limit")
    references = [read_reference(path, bundle) for path in gtfs_paths]
    headers = {**REQUEST_HEADERS, "Authorization": "Bearer " + credential("SWISS_OTD_TOKEN")}
    raw, redirect = read_one(URL, {HOST}, headers=headers, limit=MAX_XML_BYTES, allow_redirect=True)
    redirect_host = None
    if redirect:
        target = urljoin(URL, redirect)
        redirect_host = urlsplit(target).netloc
        # The signed URL is used in memory only, with no gateway credentials.
        raw, _ = read_one(target, {DOWNLOAD_HOST}, headers=REQUEST_HEADERS, limit=MAX_XML_BYTES)
    when = datetime.now(timezone.utc)
    rows, counted, sources, unresolved, mixed = _classify(raw, references)
    if unresolved and not rows:
        raise ValueError("swiss_siri_rail_scope_unverified")
    origin = CaptureOrigin(captured_at=when, filter={"planned": True, "mode": "rail"},
                           evidence={"source_url": URL, "redirect_host": redirect_host,
                                     "source_file": "situations.xml", "source_sha256": hashlib.sha256(raw).hexdigest(),
                                     "source_situations": counted, "licence": "UNKNOWN", "provider_terms": TERMS,
                                     "excluded_situations": counted - len(rows),
                                     "mode_unresolved_situations": unresolved, "mixed_mode_situations": mixed,
                                     "gtfs_references": sources,
                                     "coverage": "Planned situations with explicit rail mode or an exact dated rail journey. Coverage is partial."})
    files = [("situations.xml", raw)] + [(source["source_file"], data) for source, data in zip(sources, references)]
    return stage_capture(bundle, "swiss-siri", rows, origin=origin, raw_files=files)
