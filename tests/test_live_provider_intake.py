from datetime import date, datetime, timezone
import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from streamlit.testing.v1 import AppTest

from nightdesk.adapters import db_timetables, infrabel, ns, source_http, swiss_siri, train_archive
from nightdesk.audit import read_events
from nightdesk.cli import main
from nightdesk.config import get_bundle
from nightdesk.desk import run_evidence, run_options, snapshot
from nightdesk.intake.mapping import confirm_mapping, ingest


MAPPINGS = Path(__file__).resolve().parents[1] / "mappings"
DAY = date(2026, 11, 17)
NOW = datetime(2026, 11, 18, 8, tzinfo=timezone.utc)


def import_staged(bundle, staged, name):
    mapping = MAPPINGS / f"{name}.yaml"
    confirm_mapping(mapping, bundle, "Test source reviewer")
    result = ingest(staged["capture"], mapping, bundle)
    selected = snapshot(bundle, result["capture_id"])
    assert selected["capture"].complete is False
    assert result["rejected"] == 0
    return selected


def test_infrabel_missing_place_and_deleted_rows(tmp_path, monkeypatch):
    bundle = get_bundle("test-tcr", tmp_path)
    source = {"id": 1, "line": "12", "ptcar_from": None, "ptcar_to": "123",
              "start_commercialname_dutch": None, "end_commercialname_dutch": "Example",
              "date_begin": "2026-11-07", "date_end": "2027-05-06",
              "time_begin": "23:00:00", "time_end": "05:00:00",
              "impact_description": None, "logically_deleted": "No"}
    data = [source, {**source, "id": 2, "logically_deleted": "Yes"}]
    monkeypatch.setattr(infrabel, "_read_page", lambda path, limit: json.dumps(data).encode())
    result = import_staged(bundle, infrabel.fetch_works(bundle), "infrabel_works")
    assert result["metadata"]["accepted"] == result["metadata"]["filtered"] == 1
    work, = result["typed_rows"]
    assert work.from_place == "" and work.to_point_id == "be-ptcar:123"
    changed_envelope = Path(infrabel.fetch_works(bundle)["capture"])
    payload = json.loads(changed_envelope.read_bytes())
    payload["_capture"]["filter"] = None
    changed_envelope.write_text(json.dumps(payload))
    result = import_staged(bundle, {"capture": str(changed_envelope)}, "infrabel_works")
    assert result["metadata"]["filtered"] == 1
    assert result["capture"].filter == {"provider_query": None, "row_filter": {"logically_deleted": "No"}}


def test_ns_active_status_and_sections_survive(tmp_path, monkeypatch):
    bundle = get_bundle("test-ns", tmp_path)
    monkeypatch.setenv("NS_API_KEY", "synthetic-key")
    section = {"section": {"stations": [{"stationCode": "A", "name": "A"},
                                       {"stationCode": "B", "name": "B"}]}}
    row = {"id": "one", "type": "MAINTENANCE", "title": "Synthetic work", "isActive": True,
           "start": "2026-11-17T23:45:00Z", "end": "2026-11-19T07:00:00+01:00",
           "publicationSections": [section]}

    def fetch(url, hosts, *, headers, limit):
        assert url == ns.URL and hosts == {ns.HOST}
        assert headers["Ocp-Apim-Subscription-Key"] == "synthetic-key"
        return json.dumps([row, {**row, "id": "two", "publicationSections": [section, section]}]).encode(), None

    monkeypatch.setattr(ns, "read_one", fetch)
    selected = import_staged(bundle, ns.fetch_maintenance(bundle), "ns_maintenance")
    first, second = selected["typed_rows"]
    assert first.date_start.isoformat() == "2026-11-18"
    assert first.from_point_id == "nl-ns:A"
    assert first.extra["isActive"] is True
    assert second.from_point_id is None and len(second.extra["publicationSections"]) == 2


def test_db_plan_exact_stop_and_published_times(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NIGHTDESK_BUNDLE", "test-db")
    bundle = get_bundle("test-db")
    plan = b"""<timetable station="Synthetic">
                <s id="-42-2611172300-1"><dp pt="2611172330"/></s><s id="-42-2611172300-2">
                <tl c="ES" n="5" o="X"/><ar pt="2611180001"/><dp pt="2611180004"/>
                </s></timetable>"""
    changes = b"""<timetable station="Synthetic" eva="8123456"><s id="-42-2611172300-2">
                  <ar ct="2611180002"/><dp cs="c" ct="2611180007"/></s>
                  <s id="-42-2611172300-3"><dp ct="2611180015"/></s></timetable>"""
    monkeypatch.setenv("DB_CLIENT_ID", "synthetic-id")
    monkeypatch.setenv("DB_API_KEY", "synthetic-key")

    def fetch(url, hosts, *, headers, limit):
        assert hosts == {db_timetables.HOST}
        assert headers["DB-Client-Id"] == "synthetic-id"
        assert headers["DB-Api-Key"] == "synthetic-key"
        return plan if url.endswith("/plan/8123456/261117/23") else changes, None

    monkeypatch.setattr(db_timetables, "read_one", fetch)
    selected = import_staged(bundle, db_timetables.fetch_timetables(bundle, "8123456", DAY, 23), "db_timetables")
    plan_only, first, second = selected["typed_rows"]
    assert first.service_date == DAY and first.real_dep is None and first.delay_dep_s is None
    assert first.planned_dep.isoformat() == "2026-11-18T00:04:00+01:00"
    assert first.published_dep.isoformat() == "2026-11-18T00:07:00+01:00"
    assert second.planned_dep is None and second.extra["db_in_plan"] is False
    assert plan_only.train_no == first.train_no == second.train_no
    chosen, = run_options(bundle, [selected["capture"].capture_id])
    evidence = run_evidence(bundle, selected["capture"].capture_id, chosen)
    assert evidence["run"]["kind"] == "published"
    assert len(evidence["run"]["points"]) == 3
    assert evidence["run"]["unresolved"]["pass_window"]["reason"] == "station_capture_has_no_interstation_path"
    assert evidence["run"]["points"][0]["real_dep"] is None
    assert evidence["timetable_status"][1]["departure"] == "Cancelled"
    assert selected["capture"].filter["changes_scope"] == "full_station"
    app = AppTest.from_file(MAPPINGS.parent / "src/nightdesk/ui/app.py", default_timeout=30).run()
    capture_id = selected["capture"].capture_id
    app.selectbox(key="test-db:runs").set_value(capture_id)
    app.session_state["test-db:active_tab"] = "Run evidence"
    app.run()
    app.selectbox(key=f"test-db:source_run:{capture_id}").set_value(chosen).run()
    assert not app.exception
    assert app.tabs[3].dataframe[0].value.iloc[1]["Departure status"] == "Cancelled"
    assert any(first.train_no in element.value for element in app.tabs[3].text)
    assert all(first.train_no not in element.value for element in app.tabs[3].caption)


def test_swiss_planned_rail_and_redirect_without_credentials(tmp_path, monkeypatch):
    bundle = get_bundle("test-swiss", tmp_path)
    monkeypatch.setenv("SWISS_OTD_TOKEN", "synthetic-key")
    base = """<PtSituationElement><ParticipantRef>syn</ParticipantRef><SituationNumber>{0}</SituationNumber>
              <Planned>{1}</Planned><ValidityPeriod><StartTime>2026-11-17T23:59:00Z</StartTime>
              <EndTime>2026-11-18T10:00:00Z</EndTime></ValidityPeriod>
              <Affects><Networks><AffectedLine><VehicleMode>{2}</VehicleMode></AffectedLine></Networks></Affects>
              <Summary>Synthetic work</Summary></PtSituationElement>"""
    mixed = base.format("mixed", "true", "rail").replace("</AffectedLine>", "<VehicleMode>bus</VehicleMode></AffectedLine>")
    separated = base.format("a", "true", "rail").replace(
        "</ValidityPeriod>", "</ValidityPeriod><ValidityPeriod><StartTime>2027-03-01T22:00:00Z</StartTime>"
        "<EndTime>2027-03-02T04:00:00Z</EndTime></ValidityPeriod>")
    raw = ("<Siri xmlns='http://www.siri.org.uk/siri'><ServiceDelivery><SituationExchangeDelivery>"
           "<Situations>" + separated + base.format("b", "true", "bus") +
           base.format("c", "false", "rail") + mixed +
           "</Situations></SituationExchangeDelivery></ServiceDelivery></Siri>").encode()
    redirect = f"https://{swiss_siri.DOWNLOAD_HOST}/sample?Signature=mock-signature"

    def fetch(url, hosts, *, headers, limit, allow_redirect=False):
        assert headers["User-Agent"] == "Nightdesk/0.1"
        if allow_redirect:
            assert headers["Authorization"] == "Bearer synthetic-key" and hosts == {swiss_siri.HOST}
            return None, redirect
        assert url == redirect and hosts == {swiss_siri.DOWNLOAD_HOST}
        assert "Authorization" not in headers
        return raw, None

    monkeypatch.setattr(swiss_siri, "read_one", fetch)
    staged = swiss_siri.fetch_siri(bundle)
    assert b"mock-signature" not in Path(staged["capture"]).read_bytes()
    selected = import_staged(bundle, staged, "swiss_siri_works")
    work, second = selected["typed_rows"]
    assert work.work_id == "syn/a" and work.date_start.isoformat() == "2026-11-18"
    from nightdesk.changes import _validity_bounds
    from nightdesk.ui.app import _has_validity_date
    assert len(_validity_bounds(work)) == 2
    assert _has_validity_date(work.model_dump(mode="json"), date(2026, 11, 18))
    assert not _has_validity_date(work.model_dump(mode="json"), date(2026, 12, 1))
    assert second.extra["siri_declared_modes"] == ["bus", "rail"]
    evidence = selected["metadata"]["capture_origin"]["evidence"]
    assert (evidence["source_situations"], evidence["excluded_situations"], evidence["mixed_mode_situations"]) == (4, 2, 1)


def test_swiss_rail_mode_requires_exact_active_native_journey(tmp_path, monkeypatch):
    monkeypatch.setenv("SWISS_OTD_TOKEN", "synthetic-key")
    bundle = get_bundle("test-swiss-reference", tmp_path)
    reference = tmp_path / "swiss-reference.zip"
    with ZipFile(reference, "w") as archive:
        archive.writestr("feed_info.txt", "feed_publisher_name,feed_version,feed_start_date,feed_end_date\nSynthetic,sample,20261101,20261130\n")
        archive.writestr("routes.txt", "route_id,route_type\ntrain,102\nbus,700\n")
        archive.writestr("trips.txt", "original_trip_id,route_id,service_id,trip_id\n"
                         "ch:1:sjyid:test:rail,train,svc,rail-trip\nch:1:sjyid:test:bus,bus,svc,bus-trip\n")
        archive.writestr("calendar_dates.txt", "service_id,date,exception_type\nsvc,20261117,1\nsvc,20261118,2\n")

    def situation(identifier, day, *journeys):
        scope = "".join(f"<FramedVehicleJourneyRef><DataFrameRef>{day}</DataFrameRef>"
                        f"<DatedVehicleJourneyRef>ch:1:sjyid:test:{ref}</DatedVehicleJourneyRef>"
                        "</FramedVehicleJourneyRef>" for ref in journeys)
        return (f"<PtSituationElement><ParticipantRef>test</ParticipantRef><SituationNumber>{identifier}</SituationNumber>"
                "<Planned>true</Planned><ValidityPeriod><StartTime>2026-11-17T01:00:00Z</StartTime>"
                "<EndTime>2026-11-18T10:00:00Z</EndTime></ValidityPeriod>"
                f"<PublishingActions><PublishingAction><PublishAtScope><Affects>{scope}</Affects>"
                "</PublishAtScope></PublishingAction></PublishingActions></PtSituationElement>")

    raw = ("<Siri><SituationExchangeDelivery><Situations>" + situation("mixed", "2026-11-17", "rail", "bus", "unknown")
           + situation("removed", "2026-11-18", "rail") + situation("bus-only", "2026-11-17", "bus")
           + "</Situations></SituationExchangeDelivery></Siri>").encode()
    monkeypatch.setattr(swiss_siri, "read_one", lambda *_args, **_kwargs: (raw, None))
    with pytest.raises(ValueError, match="swiss_siri_rail_scope_unverified"):
        swiss_siri.fetch_siri(bundle)
    assert not (bundle.root / "source-captures").exists()
    staged = swiss_siri.fetch_siri(bundle, gtfs_paths=[reference])
    selected = import_staged(bundle, staged, "swiss_siri_works")
    work, = selected["typed_rows"]
    seam = work.extra["siri_dated_mode_evidence"]
    assert work.work_id == "test/mixed" and seam["journeys_resolved"] == 2 and seam["journeys_unresolved"] == 1
    assert seam["examples"]["rail"]["gtfs_trip_id"] == "rail-trip"
    origin = selected["metadata"]["capture_origin"]["evidence"]
    assert origin["mode_unresolved_situations"] == 1 and origin["mixed_mode_situations"] == 1
    gtfs, = origin["gtfs_references"]
    assert gtfs["sha256"] == seam["examples"]["rail"]["source_sha256"]
    assert Path(staged["capture"]).with_name(gtfs["source_file"]).read_bytes() == reference.read_bytes()


def test_archive_csv_preserves_estimates_and_filter(tmp_path):
    bundle = get_bundle("test-archive", tmp_path)
    rows = []
    for route, trip in (("ES", "synthetic-a"), ("IC", "synthetic-b")):
        rows.append({"provider": "ch-fake", "feed_id": "syn", "route": route, "service_date": str(DAY),
                     "trip_id": trip, "trip_start_time": "21:00:00", "stop_sequence": "1",
                     "stop_id": "aa", "stop_name": "Synthetic station", "scheduled_arrival": "2026-11-18 00:10:00",
                     "scheduled_departure": "", "predicted_arrival": "2026-11-18 00:15:00", "predicted_departure": "",
                     "delay_source": "propagated", "arrival_delay_min": "5"})
    raw = io.StringIO(newline="")
    csv_rows = csv.DictWriter(raw, fieldnames=list(rows[0]))
    csv_rows.writeheader()
    csv_rows.writerows(rows + [
        rows[0], {**rows[0], "stop_sequence": "2", "stop_id": "bb", "scheduled_arrival": "2026-11-17 23:50:00"},
    ])
    staged = train_archive.stage_daily(bundle, raw.getvalue().encode(), {"id": "ch-fake", "timezone": "Europe/Zurich"},
                                       DAY, NOW, route="ES")
    selected = import_staged(bundle, staged, "train_archive_reports")
    point, _ = selected["typed_rows"]
    assert point.kind == "archived_report" and point.train_no.startswith("archive-trip:")
    assert point.real_arr is None and point.delay_arr_s is None
    assert point.published_arr.isoformat() == "2026-11-18T00:15:00+01:00"
    assert point.extra["delay_source"] == "propagated" and point.extra["arrival_delay_min"] == "5"
    assert point.extra["archive_identical_duplicates"] == 1
    capture_id = selected["capture"].capture_id
    run_id, = run_options(bundle, [capture_id])
    report = run_evidence(bundle, capture_id, run_id)
    assert [p["extra"]["stop_sequence"] for p in report["run"]["points"]] == ["1", "2"]
    assert train_archive._instant("2026-10-25 02:30:00", "Europe/Zurich") == (None, "ambiguous_local_time")
    assert train_archive._instant("2026-11-18T00:10:00+01:00", "Europe/Zurich") == ("2026-11-18T00:10:00+01:00", None)


def test_xml_entity_declarations_are_refused():
    with pytest.raises(ValueError, match="provider_xml_declaration_not_allowed"):
        swiss_siri.normalize(b'<!DOCTYPE Siri [<!ENTITY x "X">]><Siri>&x;</Siri>')


def test_provider_missing_credential_audited_without_network(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NS_API_KEY", raising=False)
    assert main(["fetch-ns", "--bundle", "test-source-refusal"]) == 1
    assert "NS_API_KEY_missing_or_invalid" in capsys.readouterr().err
    event, = read_events(get_bundle("test-source-refusal"))
    assert event.kind == "source_capture_refused"
    assert event.payload == {"dataset": "ns_maintenance", "reason": "NS_API_KEY_missing_or_invalid"}


def test_transport_checks_host_and_bounds_decompressed_payload(monkeypatch):
    import gzip
    members = []

    class Response:
        status = 200

        def getheader(self, name):
            return "gzip" if name == "Content-Encoding" else None

        def read(self, limit):
            return gzip.compress(b"x" * 1000)[:limit]

    class Connection:
        def __init__(self, host, timeout):
            assert host == "synthetic.invalid"

        def request(self, method, path, headers):
            members.append(path)

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(source_http, "HTTPSConnection", Connection)
    with pytest.raises(ValueError, match="provider_url_not_allowed"):
        source_http.read_one("https://other.invalid/a", {"synthetic.invalid"}, limit=100)
    assert members == []
    with pytest.raises(ValueError, match="provider_response_too_large"):
        source_http.read_one("https://synthetic.invalid/a", {"synthetic.invalid"}, limit=100)
    assert members == ["/a"]
