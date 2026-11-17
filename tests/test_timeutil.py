from datetime import date, datetime, time, timezone
from types import SimpleNamespace

import pytest

from nightdesk.timeutil import localize, overlap, parse_clock, parse_date, parse_datetime, pass_window, work_windows


def dt(text):
    return datetime.fromisoformat(text)


def work(day, **changes):
    args = dict(date_start=date(2026, 11, 1), date_end=date(2026, 11, 30),
                clock_from=time(23), clock_to=time(4, 55), weekdays=[1, 2, 3, 4, 5],
                recurrence="periodical", zone="Europe/Brussels",
                during=(dt(day + "T02:00+01:00"), dt(day + "T02:10+01:00")))
    return work_windows(**(args | changes))


@pytest.mark.parametrize("day,covered", [("2026-11-17", True), ("2026-11-21", True),
                                           ("2026-11-16", False), ("2026-11-22", False)])
def test_midnight_weekday_is_start_day(day, covered):
    result = work(day)
    assert bool(result.intervals) == covered and result.reason is None
    assert result.assumptions


def test_inclusive_final_date_clips_overnight_window():
    assert work("2026-11-21", date_end=date(2026, 11, 20)).intervals == ()
    result = work("2026-11-20", date_end=date(2026, 11, 20),
                  during=(dt("2026-11-20T23:55+01:00"), dt("2026-11-21T00:05+01:00")))
    assert result.intervals[0][1] == dt("2026-11-20T23:00+00:00")


def test_continuous_is_not_a_daily_repeat():
    # A multi-day continuous interval covers noon even with night-like endpoints.
    result = work("2026-11-17", recurrence="continuous", date_start=date(2026, 11, 16), date_end=date(2026, 11, 18),
                  during=(dt("2026-11-17T12:00+01:00"), dt("2026-11-17T12:10+01:00")))
    assert len(result.intervals) == 1
    assert result.intervals[0] == (dt("2026-11-16T22:00Z"), dt("2026-11-18T03:55Z"))


@pytest.mark.parametrize("changes,reason", [({"recurrence": "unknown"}, "recurrence_unknown"),
    ({"zone": None}, "timezone_unknown"), ({"clock_from": None}, "missing_work_clock"),
    ({"weekdays": None}, "weekdays_unknown")])
def test_unknown_inputs_never_produce_a_no_match(changes, reason):
    result = work("2026-11-17", **changes)
    assert result.reason == reason and result.intervals == ()


@pytest.mark.parametrize("raw", ["2026-10-25 02:30", "2026-03-29 02:30"])
def test_clock_change_not_guessed(raw):
    result = parse_datetime(raw, "%Y-%m-%d %H:%M", "Europe/Brussels")
    assert result.at is None and result.reason == "ambiguous_local_time" and result.raw == raw


def test_explicit_offset_resolves_clock_change_and_utc_overlap():
    a = parse_datetime("2026-10-25 02:30+0200", "%Y-%m-%d %H:%M%z", "Europe/Brussels")
    b = parse_datetime("2026-10-25 02:30+0100", "%Y-%m-%d %H:%M%z", "Europe/Brussels")
    assert a.reason is None and b.reason is None
    assert a.at.timestamp() + 3600 == b.at.timestamp()
    assert overlap((a.at, b.at), (dt("2026-10-25T01:00Z"), dt("2026-10-25T01:15Z")))


def test_half_open_no_touching_and_equal_window_empty():
    a, b, c = map(dt, ["2026-11-17T00:00Z", "2026-11-17T01:00Z", "2026-11-17T02:00Z"])
    assert overlap((a, b), (b, c)) is None
    assert overlap((a, a), (a, c)) is None
    result = work("2026-11-17", clock_from=time(2), clock_to=time(2))
    assert result.intervals == ()


def point(arr=None, dep=None):
    return SimpleNamespace(planned_arr=arr, planned_dep=dep)


def test_pass_prefers_departure_at_start_arrival_at_end_and_absolute_dates():
    a = point(dt("2026-11-17T23:50Z"), dt("2026-11-17T23:55Z"))
    b = point(dt("2026-11-18T00:10Z"), dt("2026-11-18T00:15Z"))
    assert pass_window(a, b).intervals == ((a.planned_dep, b.planned_arr),)
    assert pass_window(point(arr=a.planned_arr), point(dep=b.planned_dep)).intervals == ((a.planned_arr, b.planned_dep),)


@pytest.mark.parametrize("a,b", [(point(), point()),
    (point(dep=dt("2026-11-17T12:00Z")), point(arr=dt("2026-11-17T11:00Z"))),
    (point(dep=dt("2026-11-17T12:00Z")), point(arr=dt("2026-11-17T12:00Z"))),
    (point(dep=dt("2026-11-17T12:00")), point(arr=dt("2026-11-17T13:00")))])
def test_missing_reversed_equal_or_naive_pass_stays_unknown(a, b):
    assert pass_window(a, b).reason == "no_pass_window"


def test_spring_day_duration_and_work_boundary_ambiguity():
    result = work_windows(date_start=date(2026, 3, 29), date_end=date(2026, 3, 29), clock_from=time(0), clock_to=time(4),
                          weekdays=None, recurrence="continuous", zone="Europe/Brussels",
                          during=(dt("2026-03-28T23:00Z"), dt("2026-03-29T03:00Z")))
    assert (result.intervals[0][1] - result.intervals[0][0]).total_seconds() == 3 * 3600
    ambiguous = work_windows(date_start=date(2026, 10, 25), date_end=date(2026, 10, 25), clock_from=time(2, 30), clock_to=time(4),
                             weekdays=[7], recurrence="periodical", zone="Europe/Brussels",
                             during=(dt("2026-10-25T00:00Z"), dt("2026-10-25T04:00Z")))
    assert ambiguous.reason == "ambiguous_local_time"


def test_parsing_missing_and_malformed_are_distinct():
    assert parse_datetime("", "%Y", "Europe/Brussels").reason == "missing_time"
    assert localize(dt("2026-11-17T00:00"), None).reason == "timezone_unknown"
    assert parse_date("17NOV2026", "%d%b%Y") == date(2026, 11, 17)
    assert parse_clock("9:02:03", "%H:%M:%S") == time(9, 2, 3)
    for func, args in [(parse_date, ("bad", "%Y")), (parse_clock, ("25:99",)),
                        (parse_datetime, ("bad", "%Y", "Europe/Brussels"))]:
        with pytest.raises(ValueError):
            func(*args)
