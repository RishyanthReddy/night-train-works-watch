from datetime import date, datetime, timezone

import pytest

from nightdesk.border import check_boundary
from nightdesk.config import get_bundle
from nightdesk.model import BoundaryEvent, Capture, JourneyLink, JourneyLinkMember, PathLeg, SourceRef
from nightdesk.store import make_revision

DAY = date(2026, 11, 17)


def source():
    return SourceRef(bundle="practice", dataset="synthetic", record_id="syn-1", capture_id="c",
                     content_sha256="a" * 64, captured_at=datetime(2026, 11, 17, tzinfo=timezone.utc),
                     url_or_path="synthetic", licence="synthetic")


def setup(**updates):
    event = BoundaryEvent(point_id="syn:border", kind="pass", at="2026-11-17T23:00+01:00", timezone="Europe/Brussels")
    a = PathLeg(request_id="syn-request", network="aa", train_no="aa:1", sequence=1,
                operating_dates=[DAY], exit=event)
    b = PathLeg(**(dict(request_id="syn-request", network="bb", train_no="bb:2", sequence=2,
                       operating_dates=[DAY], entry=event) | updates))
    left = make_revision(get_bundle("practice"), source(), a)[0]
    right = make_revision(get_bundle("practice"), source(), b)[0]
    members = [JourneyLinkMember(source=source(), journey_id="syn-j", network=leg.network,
                                 train_no=leg.train_no, service_date_rule="*") for leg in (a, b)]
    link = JourneyLink(journey_id="syn-j", basis="source", source=source(), members=members)
    return left, right, link


def check(left, right, link, **kwargs):
    if set(left.payload.operating_dates) == set(right.payload.operating_dates):
        complete = Capture(capture_id="synthetic-test-capture", bundle="practice", dataset="synthetic",
            captured_at=source().captured_at, declared_complete=True, complete=True,
            revision_ids=[left.revision_id, right.revision_id])
        kwargs.setdefault("left_capture", complete)
        kwargs.setdefault("right_capture", complete)
    return check_boundary(left, right, DAY, link=link, reviewed_points={"syn:border"}, **kwargs)


def test_exact_instant_agrees_different_offset_same_instant_no_tolerance():
    a, b, link = setup(entry=BoundaryEvent(point_id="syn:border", kind="pass", at="2026-11-17T22:00Z", timezone="UTC"))
    result = check(a, b, link)
    assert result.result == "agrees_on_checked_fields" and result.reason is None
    assert "Only this same event" in result.detail["limits"]
    changed = b.payload.entry.model_copy(update={"at": datetime.fromisoformat("2026-11-17T22:00:01Z")})
    a, b, link = setup(entry=changed)
    assert check(a, b, link).result == "mismatch"
    assert check(a, b, link).reason == "boundary_instants_differ"


@pytest.mark.parametrize("event,reason", [
    (BoundaryEvent(point_id="syn:other", kind="pass", at="2026-11-17T22:00Z", timezone="UTC"), "different_boundary_points"),
    (BoundaryEvent(point_id="syn:border", kind="arrival", at="2026-11-17T22:00Z", timezone="UTC"), "different_event_kinds"),
    (BoundaryEvent(point_id=None), "boundary_point_unresolved"),
    (BoundaryEvent(point_id="syn:border", kind="unknown"), "event_kind_unknown"),
    (BoundaryEvent(point_id="syn:border", kind="pass", raw_time="02:30", unresolved_reason="ambiguous_local_time"), "ambiguous_local_time"),
    (BoundaryEvent(point_id="syn:border", kind="pass", at="2026-11-17T22:00Z"), "timezone_unknown"),
])
def test_unknown_inputs_never_become_mismatch_or_agreement(event, reason):
    a, b, link = setup(entry=event)
    result = check(a, b, link)
    assert result.result == "unknown" and result.reason == reason


def test_unlinked_not_adjacent_or_unreviewed_stay_unknown():
    a, b, link = setup()
    assert check_boundary(a, b, DAY, reviewed_points={"syn:border"}).reason == "unlinked"
    assert check_boundary(a, b, DAY, link=link).reason == "boundary_point_not_reviewed"
    a, b, link = setup(sequence=3)
    assert check(a, b, link).reason == "not_adjacent_legs"


def test_date_set_mismatch_only_when_both_captures_effectively_complete():
    a, b, link = setup(operating_dates=[DAY, date(2026, 11, 18)])
    assert check(a, b, link).reason == "capture_completeness_unknown"
    common = dict(bundle="practice", dataset="synthetic", captured_at=source().captured_at, declared_complete=True,
                  complete=True, revision_ids=[a.revision_id, b.revision_id])
    ca, cb = Capture(capture_id="a", **common), Capture(capture_id="b", **common)
    assert check(a, b, link, left_capture=ca, right_capture=cb).reason == "operating_dates_differ"
    result = check(a, b, link, left_capture=ca, right_capture=cb.model_copy(update={"complete": False}))
    assert result.result == "unknown" and result.reason == "incomplete_capture"
    missing = cb.model_copy(update={"revision_ids": []})
    assert check(a, b, link, left_capture=ca, right_capture=missing).reason == "capture_revision_mismatch"


def test_uncertain_identity_and_cross_bundle_never_compare():
    a, b, link = setup(sequence=None)
    assert check(a, b, link).reason == "identity_uncertain"
    a, b, link = setup()
    b = b.model_copy(update={"source": b.source.model_copy(update={"bundle": "es"})})
    assert check(a, b, link).reason == "bundle_mismatch"
