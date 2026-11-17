from datetime import datetime, timezone

import pytest

from nightdesk.config import get_bundle
from nightdesk.match import check_works, match_work
from nightdesk.model import RunPoint, SourceRef, TrainRun, WorkNotice
from nightdesk.store import make_revision


def source():
    return SourceRef(bundle="practice", dataset="synthetic", record_id="syn-1", capture_id="c",
                     content_sha256="a" * 64, captured_at=datetime(2026, 11, 17, tzinfo=timezone.utc),
                     url_or_path="synthetic", licence="synthetic")


def work(**changes):
    w = WorkNotice(**(dict(work_id="syn-w", country="zz", line="zz:1", from_point_id="syn:a", to_point_id="syn:c",
                          date_start="2026-11-16", date_end="2026-11-18", clock_from="23:00", clock_to="04:55",
                          recurrence="periodical", weekdays=[1, 2, 3, 4, 5], timezone="Europe/Brussels") | changes))
    return make_revision(get_bundle("practice"), source(), w)[0]


def run(**changes):
    points = [RunPoint(point_id="syn:" + name, planned_arr=when, planned_dep=when,
                       line_dep="zz:1", line_arr="zz:1", source=source())
              for name, when in [("a", "2026-11-17T23:10+01:00"), ("b", "2026-11-17T23:20+01:00"), ("c", "2026-11-17T23:30+01:00")]]
    return TrainRun(**(dict(service_date="2026-11-17", train_no="zz:1", kind="observed", points=points,
                           input_refs=[source()]) | changes))


def test_a_needs_both_endpoints_and_known_line_time():
    result = match_work(work(), run())
    assert result.outcome == "A" and result.overlap_window
    assert len(result.input_refs) == 2 and result.rule_version == "match-v3"
    assert all(g.passed for g in result.gate_results)


def test_one_endpoint_and_unresolved_path_never_a_but_exact_endpoints_need_no_work_line():
    assert match_work(work(from_point_id=None), run()).outcome == "B"
    assert "one_endpoint" in match_work(work(from_point_id=None), run()).reasons
    assert match_work(work(line=None), run()).outcome == "A"
    scheduled = run(kind="scheduled", path_unresolved=True)
    assert match_work(work(), scheduled).outcome == "B"
    assert "path_unresolved" in match_work(work(), scheduled).reasons


def test_no_place_unlocated_and_no_match_counts_scoped():
    result = match_work(work(from_point_id=None, to_point_id=None, line=None), run())
    assert result.outcome == "unlocated" and any("not_attached" in reason for reason in result.reasons)
    report = check_works([work(clock_from="01:00", clock_to="02:00"), work()], run())
    assert report["checked_pairs"] == 2 and report["no_match_checked_pairs"] == 1


@pytest.mark.parametrize("changes,reason", [({"recurrence": "unknown"}, "recurrence_unknown"),
    ({"clock_from": None}, "missing_work_clock"), ({"weekdays": None}, "weekdays_unknown"),
    ({"timezone": None}, "timezone_unknown")])
def test_time_unknown_never_a_b_or_no_match(changes, reason):
    result = match_work(work(**changes), run())
    assert result.outcome == "time_unknown" and reason in result.reasons


def test_absolute_dates_not_service_date_used_for_overlap_and_midnight():
    points = [p.model_copy(update={"planned_arr": datetime.fromisoformat(t), "planned_dep": datetime.fromisoformat(t)})
              for p, t in zip(run().points, ["2026-11-18T02:00+01:00", "2026-11-18T02:10+01:00", "2026-11-18T02:20+01:00"])]
    result = match_work(work(), run(points=points))
    assert result.outcome == "A" and result.service_date.isoformat() == "2026-11-17"
    assert match_work(work(date_start="2026-11-17", date_end="2026-11-17"), run(points=points)) is None


def test_wrong_clock_window_touching_or_verified_line_mismatch_no_match():
    assert match_work(work(clock_from="01:00", clock_to="02:00"), run()) is None
    assert match_work(work(clock_from="23:30", clock_to="23:40"), run()) is None
    line_warning = match_work(work(line="zz:other"), run())
    assert line_warning.outcome == "A" and "line_mismatch" in line_warning.reasons
    assert match_work(work(date_start="2026-11-18"), run()) is None


def test_missing_pass_and_ambiguous_window_stay_unknown():
    points = run().points
    points[0] = points[0].model_copy(update={"planned_arr": None, "planned_dep": None})
    assert match_work(work(), run(points=points)).outcome == "time_unknown"
    points = [p.model_copy(update={"planned_arr": datetime.fromisoformat(t), "planned_dep": datetime.fromisoformat(t)})
              for p, t in zip(run().points, ["2026-10-25T00:00Z", "2026-10-25T01:00Z", "2026-10-25T03:00Z"])]
    result = match_work(work(date_start="2026-10-25", date_end="2026-10-25", weekdays=[7], clock_from="02:30", clock_to="04:00"), run(points=points))
    assert result.outcome == "time_unknown" and result.reasons == ["ambiguous_local_time"]
