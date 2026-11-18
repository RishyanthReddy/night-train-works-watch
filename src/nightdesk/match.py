"""Conservative works exposure on one selected dated run. Never a delay estimate."""

from nightdesk.model import Exposure, GateResult, GenericRow, Revision, TrainRun, WorkNotice
from nightdesk.gates import typed_record
from nightdesk.runs import segments
from nightdesk.timeutil import pass_window, work_windows, overlap


MATCH_RULE_VERSION = "match-v4"


def match_work(revision: Revision, run: TrainRun, *, resolver=None) -> Exposure | None:
    """None is verified no overlap. Unknowns always carry a reason.

    Unlocated results are global unresolved work rows, not evidence of exposure
    for this train. Callers must show them separately from A/B train exposures.
    """
    if not isinstance(revision.payload, WorkNotice):
        raise ValueError("match_requires_work_revision")
    work = revision.payload
    _, gates = typed_record(GenericRow(source=revision.source, fields=work.model_dump(mode="json", exclude={"extra", "unresolved"}),
                                       extra=work.extra, unresolved=work.unresolved), "WorkNotice", work.timezone)
    if any(not g.passed for g in gates):
        raise ValueError("work_record_failed_gates")
    refs = [revision.source] + run.input_refs
    resolved_places = {}
    changes = {}
    if resolver is not None:
        if resolver.bundle != revision.source.bundle:
            raise ValueError("cross_bundle_aliases")
        for side in ("from", "to"):
            if getattr(work, side + "_point_id") is None and getattr(work, side + "_place"):
                result = resolver.resolve(getattr(work, side + "_place"))
                resolved_places[side] = result.as_dict()
                refs.extend(result.input_refs)
                if result.point_id:
                    changes[side + "_point_id"] = result.point_id
        if changes:
            work = work.model_copy(update=changes)

    if any(ref.bundle != revision.source.bundle for ref in refs):
        raise ValueError("cross_bundle_match")
    common = dict(service_date=run.service_date, train_no=run.train_no, work_revision=revision.revision_id,
                  input_refs=refs, gate_results=gates, rule_version=MATCH_RULE_VERSION, place_resolution=resolved_places)
    def unknown(reason):
        return Exposure(**common, outcome="time_unknown", reasons=[reason])
    if revision.identity != "certain":
        return unknown("identity_uncertain")
    if work.recurrence == "unknown":
        return unknown("recurrence_unknown")
    if run.unresolved.get("point_order"):
        return unknown("no_pass_window")
    if len(run.points) < 2:
        return unknown("no_pass_window")
    locations = {}
    for i, point in enumerate(run.points):
        locations.setdefault(point.point_id, []).append(i)
    endpoint_ids = [work.from_point_id, work.to_point_id]
    on_path = [p for p in endpoint_ids if p in locations]
    if any(len(locations[p]) > 1 for p in on_path):
        return unknown("ambiguous_pass_window")
    if len(on_path) == 2:
        lo, hi = sorted(locations[p][0] for p in on_path)
        if lo == hi:
            return unknown("no_pass_window")
    elif len(on_path) == 1:
        i = locations[on_path[0]][0]
        lo, hi = max(0, i - 1), min(len(run.points) - 1, i + 1)
    else:
        lo, hi = 0, len(run.points) - 1
    selected_segments = segments(run)[lo:hi]
    lines = [segment.line for segment in selected_segments]
    line_only = bool(work.line and not on_path)
    uncertain_spans = []
    if line_only:
        spans = [pass_window(s.a, s.b) for s in selected_segments if s.line == work.line]
        uncertain_spans = [pass_window(s.a, s.b) for s in selected_segments if s.line is None]
    else:
        spans = [pass_window(run.points[lo], run.points[hi])]
    overlapping, assumptions = [], set()
    for span in spans:
        if span.reason:
            return unknown("no_pass_window")
        windows = work_windows(date_start=work.date_start, date_end=work.date_end,
                               clock_from=work.clock_from, clock_to=work.clock_to,
                               weekdays=work.weekdays, recurrence=work.recurrence,
                               zone=work.timezone, during=span.intervals[0])
        if windows.reason:
            return unknown(windows.reason)
        assumptions.update(windows.assumptions)
        overlapping.extend(w for window in windows.intervals if (w := overlap(window, span.intervals[0])) is not None)
    if not overlapping:
        # An unknown/station-area hop cannot positively stand in for a named
        # line. If its time might overlap, the line's pass window is unknown.
        for span in uncertain_spans:
            if span.reason:
                return unknown("no_pass_window")
            windows = work_windows(date_start=work.date_start, date_end=work.date_end,
                clock_from=work.clock_from, clock_to=work.clock_to, weekdays=work.weekdays,
                recurrence=work.recurrence, zone=work.timezone, during=span.intervals[0])
            if windows.reason:
                return unknown(windows.reason)
            if any(overlap(w, span.intervals[0]) is not None for w in windows.intervals):
                return unknown("line_unknown_for_pass_window")
        return None
    overlapping.sort()
    reasons = sorted(assumptions)
    reasons.extend(side + "_" + evidence["reason"] for side, evidence in resolved_places.items() if evidence["reason"])
    if changes:
        reasons.append("reviewed_alias_resolution")
    if len(overlapping) > 1:
        reasons.append("first_of_multiple_overlap_windows_shown")
    resolved = all(endpoint_ids)
    ordered = len(on_path) == 2
    common["gate_results"] = gates + [
        GateResult(gate="W4", passed=resolved, reason_code=None if resolved else "unresolved_endpoints"),
        GateResult(gate="W5", passed=ordered, reason_code=None if ordered else "not_on_ordered_path")]
    if not any(endpoint_ids) and not work.line:
        outcome = "unlocated"
        reasons.append("no_endpoint; not_attached_to_train")
    else:
        if len(on_path) == 1:
            reasons.append("one_endpoint")
        elif not ordered:
            reasons.append("not_on_ordered_path")
        line_known = bool(work.line and lines and all(lines) and work.line in lines)
        if work.line and lines and all(line is not None and line != work.line for line in lines):
            reasons.append("line_mismatch")
        elif not line_known:
            reasons.append("line_unknown")
        if run.path_unresolved:
            reasons.append("path_unresolved")
        outcome = "A" if resolved and ordered and not run.path_unresolved else "B"
    return Exposure(**common, outcome=outcome, reasons=reasons,
                    overlap_window=list(overlapping[0]))


def check_works(revisions: list[Revision], run: TrainRun, *, resolver=None):
    exposures, no_match = [], 0
    for revision in revisions:
        result = match_work(revision, run, resolver=resolver)
        if result is None:
            no_match += 1
        else:
            exposures.append(result)
    return {"exposures": exposures, "no_match_checked_pairs": no_match, "checked_pairs": len(revisions)}
