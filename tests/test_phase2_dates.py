"""Identity and dated evidence must not silently become a checked fact."""
from datetime import date
import pytest
from nightdesk.border import check_boundary
from nightdesk.model import Capture
from nightdesk.timeutil import parse_datetime, overlap
from nightdesk.match import match_work
from test_border import setup, source, DAY
from test_match import work, run


def complete(left, right):
    return Capture(capture_id='synthetic-dated', bundle='practice', dataset='synthetic',
                   captured_at=source().captured_at, declared_complete=True, complete=True,
                   revision_ids=[left.revision_id, right.revision_id])


def test_uncertain_work_identity_never_reaches_exposure_grade():
    revision = work(work_id=None)
    assert revision.identity == 'uncertain'
    exposure = match_work(revision, run())
    assert exposure.outcome == 'time_unknown' and exposure.reasons == ['identity_uncertain']


def test_repeated_operating_dates_do_not_reuse_one_absolute_event_instant():
    left, right, link = setup()
    dates = [DAY, date(2026, 11, 18)]
    left = left.model_copy(update={'payload': left.payload.model_copy(update={'operating_dates': dates})})
    right = right.model_copy(update={'payload': right.payload.model_copy(update={'operating_dates': dates})})
    capture = complete(left, right)
    for day in dates:
        result = check_boundary(left, right, day, link=link, reviewed_points={'syn:border'},
                                left_capture=capture, right_capture=capture)
        assert result.result == 'unknown' and result.reason == 'boundary_service_date_binding_unknown'


def test_single_service_day_may_have_boundary_on_next_calendar_day():
    from nightdesk.model import BoundaryEvent
    left, right, link = setup()
    event = BoundaryEvent(point_id='syn:border', kind='pass', at='2026-11-18T00:20+01:00', timezone='Europe/Brussels')
    left = left.model_copy(update={'payload': left.payload.model_copy(update={'exit': event})})
    right = right.model_copy(update={'payload': right.payload.model_copy(update={'entry': event})})
    capture = complete(left, right)
    result = check_boundary(left, right, DAY, link=link, reviewed_points={'syn:border'},
                            left_capture=capture, right_capture=capture)
    assert result.result == 'agrees_on_checked_fields'
    assert result.detail['left_at'].startswith('2026-11-17T23:20')


@pytest.mark.parametrize('raw', ['2026-03-29 02:30', '2026-10-25 02:30'])
def test_clock_change_gap_and_fold_stay_unknown_without_offset(raw):
    parsed = parse_datetime(raw, '%Y-%m-%d %H:%M', 'Europe/Brussels')
    assert parsed.at is None and parsed.reason == 'ambiguous_local_time'


def test_offset_resolves_fold_and_touching_utc_windows_do_not_overlap():
    first = parse_datetime('2026-10-25T02:30+0200', '%Y-%m-%dT%H:%M%z', 'Europe/Brussels').at
    second = parse_datetime('2026-10-25T02:30+0100', '%Y-%m-%dT%H:%M%z', 'Europe/Brussels').at
    end = parse_datetime('2026-10-25T03:30+0100', '%Y-%m-%dT%H:%M%z', 'Europe/Brussels').at
    assert overlap((first, second), (second, end)) is None
