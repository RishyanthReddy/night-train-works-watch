import csv
from datetime import date
import gzip
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from nightdesk.adapters.gtfs import import_gtfs
from nightdesk.adapters.rijden_archive import FIELDS, stage_month
from nightdesk.audit import verify
from nightdesk.config import ES_ROUTE, INFRABEL_MAPPING_HASHES, get_bundle
from nightdesk.desk import run_evidence, run_options
from nightdesk.es_runs import compare_runs
from nightdesk.export import export_es_run_comparison, export_run_evidence
from nightdesk.intake.mapping import confirm_mapping, ingest

REPO = Path(__file__).resolve().parents[1]


def test_dutch_archive_preserves_reported_delay_and_cancellation(tmp_path):
    bundle = get_bundle("test-rijden", tmp_path / "out")
    raw = tmp_path / "services.csv.gz"
    values = {name: "" for name in FIELDS}
    values.update({
        "Service:RDT-ID": "synthetic-service", "Service:Date": "2026-10-30",
        "Service:Type": "European Sleeper", "Service:Train number": "453",
        "Service:Partly cancelled": "true", "Stop:RDT-ID": "synthetic-stop",
        "Stop:Station code": "SYN", "Stop:Station name": "Synthetic station",
        "Stop:Departure time": "2026-10-31T01:10:00+01:00",
        "Stop:Arrival delay": "1.5", "Stop:Departure delay": "+8", "Stop:Departure cancelled": "true",
    })
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, sorted(FIELDS))
    writer.writeheader()
    writer.writerow({**values, "Stop:RDT-ID": "clockless-stop", "Stop:Station code": "EARLY",
                     "Stop:Station name": "Clockless station", "Stop:Departure time": ""})
    writer.writerow(values)
    writer.writerow({**values, "Service:Type": "Other service"})
    raw.write_bytes(gzip.compress(buffer.getvalue().encode()))
    with pytest.raises(ValueError, match="no_matching_services"):
        stage_month(bundle, raw, "2026-09")
    staged = stage_month(bundle, raw, "2026-10")
    mapping = REPO / "mappings/rijden_archive.yaml"
    confirm_mapping(mapping, bundle, "Test reviewer")
    result = ingest(staged["capture"], mapping, bundle)
    assert (result["accepted"], result["rejected"]) == (2, 0)
    capture = result["capture_id"]
    selection = next(iter(run_options(bundle, [capture])))
    report = run_evidence(bundle, capture, selection)
    run = report["run"]
    first, point = run["points"]
    assert first["name"] == "Clockless station" and first["planned_dep"] is None
    assert run["unresolved"]["point_order"]["reason"] == "missing_planned_time"
    assert run["unresolved"]["pass_window"]["reason"] == "rijden_archive_source_order_only"
    assert run["kind"] == "archived_report" and run["trip_id"] == "synthetic-service"
    assert run["service_date"] == "2026-10-30" and point["planned_dep"].startswith("2026-10-31")
    assert point["real_dep"] is None and point["published_dep"] is None
    assert point["extra"]["rdt_departure_delay_min"] == 8
    assert point["extra"]["rdt_arrival_delay_min"] is None
    assert point["extra"]["Stop:Arrival delay"] == "1.5"
    assert point["extra"]["rdt_delay_warnings"] == {"Arrival": "Expected whole minutes"}
    assert point["extra"]["Stop:Departure cancelled"] == "true"
    md, _ = export_run_evidence(bundle, capture, selection)
    assert "Rijden de Treinen" in md.read_text()
    assert verify(bundle)["valid"]
    writer.writerow({**values, "Stop:RDT-ID": "duplicate-station"})
    raw.write_bytes(gzip.compress(buffer.getvalue().encode()))
    with pytest.raises(ValueError, match="station_repeated_in_service"):
        stage_month(bundle, raw, "2026-10")


def test_reviewed_infrabel_mapping_versions_follow_shipped_files():
    for dataset, expected in INFRABEL_MAPPING_HASHES.items():
        actual = hashlib.sha256((REPO / "mappings" / f"{dataset}.yaml").read_bytes()).hexdigest()
        assert actual == expected, f"Review {dataset} before updating the approved mapping hash"
    assert all(ES_ROUTE.fullmatch(f"ES-{train}") for train in ("454", "455"))


def test_reviewed_overnight_observation_and_gtfs_identity(tmp_path):
    bundle = get_bundle("test-es", tmp_path / "out")
    gtfs = tmp_path / "synthetic.zip"
    tables = {
        "agency.txt": "agency_id,agency_name,agency_timezone\nes,Synthetic,Europe/Brussels\n",
        "routes.txt": "route_id,route_type\nES-475,2\n",
        "trips.txt": "route_id,service_id,trip_id\nES-475,day,synthetic-trip\n",
        "calendar_dates.txt": "service_id,date,exception_type\nday,20261117,1\n",
        "stops.txt": "stop_id,stop_name\nA B,Synthetic A\nA%20B,Synthetic B\n",
        "stop_times.txt": "trip_id,stop_id,stop_sequence,arrival_time,departure_time\n"
                          "synthetic-trip,A B,1,25:09:00,25:10:00\nsynthetic-trip,A%20B,2,26:00:00,26:01:00\n",
    }
    with ZipFile(gtfs, "w") as archive:
        for name, data in tables.items():
            archive.writestr(name, data)
    scheduled = import_gtfs(gtfs, bundle, actor="Test reviewer", namespace="syn-es", licence="synthetic",
                            dates=[date(2026, 11, 17)])
    assert (scheduled["accepted"], scheduled["rejected"]) == (2, 0)

    observation = tmp_path / "infrabel.csv"
    observation.write_text(
        "DATDEP,TRAIN_NO,TRAIN_SERV,PTCAR_NO,PTCAR_LG_NM_NL,LINE_NO_DEP,LINE_NO_ARR,"
        "PLANNED_DATE_ARR,PLANNED_TIME_ARR,PLANNED_DATE_DEP,PLANNED_TIME_DEP,"
        "REAL_DATE_ARR,REAL_TIME_ARR,REAL_DATE_DEP,REAL_TIME_DEP,DELAY_ARR,DELAY_DEP\n"
        "18Nov2026,475,EURSLEEPER,1,Synthetic A,1,1,18Nov2026,01:09:00,18Nov2026,01:10:00,"
        "18Nov2026,01:11:00,18Nov2026,01:12:00,120,120\n"
    )
    mapping = REPO / "mappings/infrabel_punctuality.yaml"
    confirm_mapping(mapping, bundle, "Test reviewer")
    observed = ingest(observation, mapping, bundle)
    assert (observed["accepted"], observed["rejected"]) == (1, 0)
    review = bundle.root / "review.json"
    choices = {"reviewed_by": "Test reviewer", "stations": [
        {"scheduled_point": "syn-es:A%20B", "observed_point": "be-ptcar:1"},
    ]}
    for side, imported in (("scheduled", scheduled), ("observed", observed)):
        capture = imported["capture_id"]
        choices[side] = {"capture": capture, "selection": next(iter(run_options(bundle, [capture])))}
    review.write_text(json.dumps(choices))
    comparison = compare_runs(bundle, review)
    assert comparison["stations"][0]["departure"] == {
        "scheduled": "2026-11-18T00:10:00Z", "infrabel_planned": "2026-11-18T01:10:00+01:00",
        "observed": "2026-11-18T01:12:00+01:00", "schedule_agrees": True,
    }
    points = comparison["scheduled"]["run"]["points"]
    assert [point["point_id"] for point in points] == ["syn-es:A%20B", "syn-es:A%2520B"]
    assert points[0]["extra"]["gtfs_evidence"]["stop"]["stop_id"] == "A B"
    _, exported = export_es_run_comparison(bundle, review)
    assert json.loads(exported.read_text()) == comparison and verify(bundle)["valid"]
    assert "Partial Infrabel capture: not_declared_complete" in comparison["limits"]
    assert comparison["stations"][0]["scheduled_native_stop_id"] == "A B"
    assert comparison["unreviewed_points"] == {"scheduled": 1, "observed": 0}

    unofficial = tmp_path / "unofficial.yaml"
    unofficial.write_text(mapping.read_text() + "\n# A different mapping version\n")
    confirm_mapping(unofficial, bundle, "Test reviewer")
    other_capture = ingest(observation, unofficial, bundle)["capture_id"]
    original_observed = choices["observed"]
    choices["observed"] = {"capture": other_capture, "selection": next(iter(run_options(bundle, [other_capture])))}
    review.write_text(json.dumps(choices))
    with pytest.raises(ValueError, match="infrabel_mapping_unverified"):
        compare_runs(bundle, review)
    choices["observed"] = original_observed

    normalized = next((bundle.root / "adapters/gtfs").glob("*/rows.json"))
    copied = tmp_path / "copied.json"
    copied.write_bytes(normalized.read_bytes())
    other_capture = ingest(copied, normalized.with_name("mapping.yaml"), bundle)["capture_id"]
    original_scheduled = choices["scheduled"]
    choices["scheduled"] = {"capture": other_capture, "selection": next(iter(run_options(bundle, [other_capture])))}
    review.write_text(json.dumps(choices))
    with pytest.raises(ValueError, match="gtfs_import_receipt_required"):
        compare_runs(bundle, review)
    choices["scheduled"] = original_scheduled

    choices["stations"][0]["scheduled_point"] = "syn-es:A%2520B"
    review.write_text(json.dumps(choices))
    with pytest.raises(ValueError, match="no_matching_planned_instant"):
        compare_runs(bundle, review)
    with pytest.raises(ValueError):
        compare_runs(get_bundle("test-other", tmp_path / "out"), review)
