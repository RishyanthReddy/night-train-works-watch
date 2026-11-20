"""The OpenBoards German board adapter: request shape, parsing and staging."""

import json
from datetime import datetime, timezone

import pytest

from nightdesk.adapters import openboards
from nightdesk.adapters.openboards import (board_url, normalize, request_body, stage_boards)
from nightdesk.config import get_bundle


def board(*stops, eva="8011160", name="Berlin Hauptbahnhof"):
    return json.dumps({"stations": [{"localizedNames": [{"language": "deu", "name": name}]}],
                       "stopPlaces": [{"evaNumber": eva}],
                       "departures": list(stops), "arrivals": list(stops)}).encode("utf-8")


def stop(**overrides):
    base = {"departureId": "8011160_D_1", "evaNumber": "8011160",
            "journeyId": "20261120-a3f1bd7d", "timeSchedule": "2026-11-20T23:00:00+01:00",
            "time": "2026-11-20T23:01:00+01:00", "timeType": "REAL",
            "platform": {"name": "12"}, "platformSchedule": {"name": "12"},
            "transport": {"administrationId": "80", "category": "ICE", "journeyNumber": 452}}
    base.update(overrides)
    return base


def test_board_url_only_accepts_the_two_boards():
    assert board_url("departures").endswith("/open-boards/v1/departures")
    assert board_url("arrivals").endswith("/open-boards/v1/arrivals")
    with pytest.raises(ValueError):
        board_url("timetable")


def test_request_body_is_one_station_with_a_page_size_per_train_type():
    when = datetime(2026, 11, 20, 22, 0, tzinfo=timezone.utc)
    body = json.loads(request_body("8011160", 50, when))
    assert body["stopPlaceOrStation"] == {"evaNumbers": ["8011160"]}
    assert body["maxEntriesPerTransportType"] == 50
    assert body["timeWindow"]["timeStart"] == when.isoformat(timespec="seconds")
    assert body["languages"] == ["deu"]


def test_request_body_defaults_the_start_instant_to_now():
    body = json.loads(request_body("8011160", 10))
    assert body["timeWindow"]["timeStart"]
    assert "T" in body["timeWindow"]["timeStart"]


def test_request_body_refuses_a_bad_station_or_limit():
    for eva in ("801116", "80111600", "abcdefg", "8011160 "):
        with pytest.raises(ValueError):
            request_body(eva, 50)
    for limit in (0, -1, 501):
        with pytest.raises(ValueError):
            request_body("8011160", limit)


def test_a_real_time_is_observed_and_a_bare_schedule_is_not():
    rows = normalize({"departures": board(stop(), stop(time=None, timeType="SCHEDULED"))}, "8011160")
    assert [row["kind"] for row in rows[:2]] == ["observed", "scheduled"]
    assert rows[0]["planned_time"] == "2026-11-20T23:00:00+01:00"
    assert rows[0]["observed_time"] == "2026-11-20T23:01:00+01:00"
    assert rows[1]["observed_time"] is None


def test_platform_change_is_kept_as_two_labelled_values():
    row = normalize({"departures": board(stop(platform={"name": "14"}))}, "8011160")[0]
    assert row["planned_platform"] == "12"
    assert row["observed_platform"] == "14"


def test_station_name_service_date_and_train_number_are_read():
    row = normalize({"departures": board(stop())}, "8011160")[0]
    assert row["name"] == "Berlin Hauptbahnhof"
    assert row["service_date"] == "2026-11-20"
    assert row["trip_id"] == "20261120-a3f1bd7d"
    assert row["train_no"] == "de-db:80/ICE/452"


def test_both_boards_are_kept_apart():
    rows = normalize({"departures": board(stop(departureId="D1")),
                      "arrivals": board(stop(departureId="A1"))}, "8011160")
    assert [row["db_board_kind"] for row in rows] == ["departures", "arrivals"]


def test_a_stop_from_another_station_is_refused():
    with pytest.raises(ValueError, match="db_board_station_mismatch"):
        normalize({"departures": board(stop(evaNumber="8000001"))}, "8011160")


@pytest.mark.parametrize("raw", [b"not json", b"[]", b'{"departures": 3}', b'{"departures": [1]}'])
def test_broken_boards_are_refused(raw):
    with pytest.raises(ValueError, match="db_board_json_invalid"):
        normalize({"departures": raw}, "8011160")


def test_a_capture_records_both_files_and_their_hashes(tmp_path):
    bundle = get_bundle("test-openboards", out_root=tmp_path)
    now = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
    result = stage_boards(bundle, "8011160", 10, {"departures": (board(stop()), now),
                                                  "arrivals": (board(stop()), now)})
    folder = bundle.root / "source-captures"
    staged = list(folder.iterdir())
    assert len(staged) == 1 and staged[0].name.startswith("db-openboards-")
    assert (staged[0] / "departures.json").is_file()
    assert (staged[0] / "arrivals.json").is_file()
    capture = json.loads((staged[0] / "capture.json").read_text(encoding="utf-8"))
    origin = capture["_capture"]
    assert origin["evidence"]["departures"]["source_url"] == board_url("departures")
    assert len(origin["evidence"]["departures"]["source_sha256"]) == 64
    assert origin["evidence"]["licence"] == "UNKNOWN"
    assert "not been shown to be cancelled" in origin["evidence"]["coverage"]
    assert result["rows"] == 2


def test_the_public_demo_bundle_cannot_hold_a_provider_capture(tmp_path):
    bundle = get_bundle("demo", out_root=tmp_path)
    now = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="provider_capture_requires_practice_bundle"):
        stage_boards(bundle, "8011160", 10, {"departures": (board(stop()), now)})


def test_fetch_refuses_an_nda_bundle_before_any_request(tmp_path):
    bundle = get_bundle("es", out_root=tmp_path)
    with pytest.raises(ValueError, match="provider_capture_requires_practice_bundle"):
        openboards.fetch_boards(bundle, "8011160", 10)


def test_a_platform_level_sub_stop_listed_by_the_response_is_accepted():
    raw = json.dumps({"meta": {"consideredStopPlaces": ["8011160", "8089021"]},
                      "stopPlaces": [{"evaNumber": "8089021", "localizedNames": [{"name": "Berlin Hbf (S-Bahn)"}]}],
                      "stations": [{"localizedNames": [{"language": "deu", "name": "Berlin Hauptbahnhof"}]}],
                      "departures": [stop(evaNumber="8089021")]}).encode("utf-8")
    row = normalize({"departures": raw}, "8011160")[0]
    assert row["point_id"] == "8011160"
    assert row["db_stop_place"] == "8089021"
    assert row["name"] == "Berlin Hauptbahnhof"


def test_identical_stop_rows_are_kept_once():
    repeated = stop()
    rows = normalize({"departures": board(repeated, repeated)}, "8011160")
    assert len(rows) == 1
