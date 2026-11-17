"""One narrow consistency rule on adjacent explicitly linked path legs."""

from datetime import date

from nightdesk.gates import capture_comparison_gate
from nightdesk.links import covers
from nightdesk.model import Capture, ConsistencyFinding, JourneyLink, PathLeg, Revision
from nightdesk.timeutil import utc


def check_boundary(left: Revision, right: Revision, service_date: date, *,
                   link: JourneyLink | None = None, reviewed_points: set[str] | None = None,
                   left_capture: Capture | None = None, right_capture: Capture | None = None) -> ConsistencyFinding:
    refs = [left.source, right.source]
    if link:
        refs.extend(member.source for member in link.members)
    context = dict(rule="adjacent_same_boundary_event", rule_version="border-v1", input_refs=refs)
    def result(outcome="unknown", reason=None, **detail):
        return ConsistencyFinding(**context, result=outcome, reason=reason, detail={"service_date": service_date.isoformat(), **detail})
    if len({ref.bundle for ref in refs}) != 1:
        return result(reason="bundle_mismatch")
    if not isinstance(left.payload, PathLeg) or not isinstance(right.payload, PathLeg):
        return result(reason="path_legs_required")
    a, b = left.payload, right.payload
    if left.identity != "certain" or right.identity != "certain":
        return result(reason="identity_uncertain")
    if link is None:
        return result(reason="unlinked")
    linked = [covers(link, leg, service_date) for leg in (a, b)]
    if not all(ok for ok, _ in linked):
        return result(reason=next(reason for ok, reason in linked if not ok))
    if a.sequence is None or b.sequence != a.sequence + 1:
        return result(reason="not_adjacent_legs")
    if a.network == b.network:
        return result(reason="same_network")
    if left_capture is not None or right_capture is not None:
        if left_capture is None or right_capture is None:
            return result(reason="capture_completeness_unknown")
        if not left_capture.complete or not right_capture.complete:
            return result(reason="incomplete_capture")
        if left.revision_id not in left_capture.revision_ids or right.revision_id not in right_capture.revision_ids:
            return result(reason="capture_revision_mismatch")
        if (left_capture.bundle != left.source.bundle or right_capture.bundle != right.source.bundle
                or left_capture.dataset != left.source.dataset or right_capture.dataset != right.source.dataset):
            return result(reason="capture_source_mismatch")
    if set(a.operating_dates) != set(b.operating_dates):
        if left_capture is None or right_capture is None:
            return result(reason="capture_completeness_unknown")
        gate = capture_comparison_gate(left_capture, right_capture)
        if not gate.passed:
            return result(reason=gate.reason_code)
        if left.revision_id not in left_capture.revision_ids or right.revision_id not in right_capture.revision_ids:
            return result(reason="capture_revision_mismatch")
        if (left_capture.bundle != left.source.bundle or right_capture.bundle != right.source.bundle
                or left_capture.dataset != left.source.dataset or right_capture.dataset != right.source.dataset):
            return result(reason="capture_source_mismatch")
        return result("mismatch", "operating_dates_differ", left_dates=sorted(d.isoformat() for d in set(a.operating_dates)),
                      right_dates=sorted(d.isoformat() for d in set(b.operating_dates)))
    if service_date not in a.operating_dates or service_date not in b.operating_dates:
        return result(reason="service_date_not_operating")
    end, start = a.exit, b.entry
    if end is None or start is None:
        return result(reason="boundary_event_missing")
    if end.point_id is None or start.point_id is None:
        return result(reason="boundary_point_unresolved")
    if end.point_id != start.point_id:
        return result(reason="different_boundary_points")
    if end.point_id not in (reviewed_points or set()):
        return result(reason="boundary_point_not_reviewed")
    if end.kind == "unknown" or start.kind == "unknown":
        return result(reason="event_kind_unknown")
    if end.kind != start.kind:
        return result(reason="different_event_kinds")
    if end.at is None or start.at is None:
        return result(reason=end.unresolved_reason or start.unresolved_reason or "missing_time")
    if not end.timezone or not start.timezone:
        return result(reason="timezone_unknown")
    if left_capture is None or right_capture is None:
        return result(reason="capture_completeness_unknown")
    detail = dict(point_id=end.point_id, kind=end.kind, left_at=utc(end.at).isoformat(), right_at=utc(start.at).isoformat(),
                  limits="Only this same event at this reviewed point was checked; not whole-journey feasibility or national approval.")
    if utc(end.at) != utc(start.at):
        return result("mismatch", "boundary_instants_differ", **detail)
    return result("agrees_on_checked_fields", **detail)
