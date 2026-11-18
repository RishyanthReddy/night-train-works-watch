"""Explicit selected-revision and selected-capture comparisons. No supersession."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from nightdesk.gates import capture_comparison_gate
from nightdesk.model import ChangeSet, FieldDiff, Revision, PathLeg, WorkNotice
from nightdesk.store import load_revision, same_subject


def field_diffs(old, new, prefix="") -> list[FieldDiff]:
    if isinstance(old, dict) and isinstance(new, dict):
        out = []
        for key in sorted(old.keys() | new.keys()):
            name = prefix + "." + key if prefix else key
            if key not in old or key not in new:
                out.append(FieldDiff(field=name, old=old.get(key), new=new.get(key),
                                     old_present=key in old, new_present=key in new))
            else:
                out.extend(field_diffs(old[key], new[key], name))
        return out
    if type(old) is not type(new) or old != new:
        return [FieldDiff(field=prefix, old=old, new=new)]
    return []


def affected_dates(revision: Revision):
    payload = revision.payload
    if isinstance(payload, PathLeg):
        return set(payload.operating_dates)
    return {payload.date_start + timedelta(days=i) for i in range((payload.date_end - payload.date_start).days + 1)}


def compare_revisions(old: Revision, new: Revision) -> ChangeSet:
    context = dict(old_revision=old.revision_id, new_revision=new.revision_id, basis="selected_revisions",
                   input_refs=[old.source, new.source])
    if old.source.bundle != new.source.bundle:
        return ChangeSet(**context, status="comparison_unavailable", reason="bundle_mismatch")
    if old.identity == "uncertain" or new.identity == "uncertain":
        return ChangeSet(**context, status="identity_uncertain", reason="identity_uncertain")
    if not same_subject(old, new):
        return ChangeSet(**context, status="comparison_unavailable", reason="different_subject")
    changes = field_diffs(old.payload.model_dump(mode="json"), new.payload.model_dump(mode="json"))
    if old.source_status != new.source_status and not any(d.field == "source_status" for d in changes):
        changes.append(FieldDiff(field="source_status", old=old.source_status, new=new.source_status))
    return ChangeSet(**context, status="compared", field_diffs=changes,
                     affected_dates=sorted(affected_dates(old) | affected_dates(new)) if changes else [])


def _validity_bounds(work):
    """All stated ranges matter. Never hide a later validity behind an envelope.

    The German raw fields are retained in extra, not imported as a new adapter.
    Missing or malformed individual bounds prevent a window exclusion.
    Canonical dates are inclusive, so their end is the following midnight.
    """
    if work.timezone:
        ZoneInfo(work.timezone)  # validate the declared zone, never infer one
    def bound(value, end=False):
        if not isinstance(value, str):
            raise ValueError("validity_bound_missing")
        if len(value) == 10:
            day = date.fromisoformat(value) + timedelta(days=int(end))
            parsed = datetime.combine(day, time())
        else:
            parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            if work.timezone is None:
                raise ValueError("validity_timezone_unknown")
            # Refuse folds/gaps rather than guessing a source instant.
            from nightdesk.timeutil import localize
            parsed = localize(parsed, work.timezone).at
            if parsed is None:
                raise ValueError("validity_time_unresolved")
        return parsed
    extra = work.extra
    if "zeitraum" not in extra and "gueltigkeiten" not in extra:
        return [(bound(work.date_start.isoformat()), bound(work.date_end.isoformat(), True))]
    envelope, periods = extra.get("zeitraum"), extra.get("gueltigkeiten")
    if not isinstance(envelope, dict) or not isinstance(periods, list) or not periods:
        raise ValueError("validity_bound_missing")
    result = [(bound(envelope.get("beginn")), bound(envelope.get("ende"), True))]
    for period in periods:
        if not isinstance(period, dict):
            raise ValueError("validity_bound_missing")
        # bisDatum is inclusive. Without an unambiguous clock, keep that day.
        def period_bound(day, clock, end=False):
            if not isinstance(day, str):
                raise ValueError("validity_bound_missing")
            return bound(day + "T" + clock) if isinstance(clock, str) and clock else bound(day, end)
        result.append((period_bound(period.get("vonDatum"), period.get("vonUhrzeit")),
                       period_bound(period.get("bisDatum"), period.get("bisUhrzeit"), True)))
    if any(a.tzinfo is None or b.tzinfo is None or a >= b for a, b in result):
        raise ValueError("validity_timezone_or_range_unknown")
    return result


def _validity_conflicts(work, bounds):
    """Raw clocks may refine canonical dates, never contradict them."""
    if "zeitraum" not in work.extra:
        return False
    zone = ZoneInfo(work.timezone) if work.timezone else None
    def projected(value, instant):
        if len(value) == 10:
            return date.fromisoformat(value)  # inclusive raw date, before +1 day
        return instant.astimezone(zone).date() if zone else instant.date()
    envelope = work.extra["zeitraum"]
    if (projected(envelope["beginn"], bounds[0][0]) != work.date_start or
            projected(envelope["ende"], bounds[0][1]) != work.date_end):
        return True
    return any(date.fromisoformat(p["vonDatum"]) < work.date_start or
               date.fromisoformat(p["bisDatum"]) > work.date_end
               for p in work.extra["gueltigkeiten"])


def _window_declarations(capture):
    policy = capture.filter or {}
    found = [policy["zeitraum"]] if "zeitraum" in policy else []
    if isinstance(policy.get("roles"), dict):
        found.extend(f["zeitraum"] for f in policy["roles"].values()
                     if isinstance(f, dict) and "zeitraum" in f)
    return found


def window_membership(revision, old_capture, new_capture, side, *, rolling_window_hours=None, allow_entering=True):
    """One-sided works are observations, never proof of publication/cancellation."""
    if not isinstance(revision.payload, WorkNotice):
        return None
    work = revision.payload
    evidence = {"revision_id": revision.revision_id, "side": side,
                "source": revision.source.model_dump(mode="json"),
                "canonical_validity": {"start": work.date_start.isoformat(), "end": work.date_end.isoformat()},
                "evaluated_at": new_capture.captured_at.isoformat()}
    try:
        bounds = _validity_bounds(work)
        conflict = _validity_conflicts(work, bounds)
    except (ValueError, TypeError, KeyError, OverflowError):
        return {**evidence, "classification": "membership_unknown", "reason": "validity_bounds_unresolved"}
    # Date-only canonical evidence without a declared zone cannot prove expiry.
    if any(a.tzinfo is None or b.tzinfo is None for a, b in bounds):
        return {**evidence, "classification": "membership_unknown", "reason": "validity_bounds_unresolved"}
    evidence["validity_bounds"] = [[a.isoformat(), b.isoformat()] for a, b in bounds]
    if conflict:
        return {**evidence, "classification": "membership_unknown", "reason": "canonical_raw_validity_conflict"}
    if side == "old" and all(end < new_capture.captured_at for _, end in bounds):
        return {**evidence, "classification": "expired_out_of_window", "reason": "all_validity_ended_before_capture"}
    if side == "old":
        return None
    old_windows, new_windows = _window_declarations(old_capture), _window_declarations(new_capture)
    declarations = old_windows + new_windows
    evidence["declared_windows"] = {"old": old_windows, "new": new_windows}
    if rolling_window_hours is not None:
        evidence["selected_window_hours"] = (rolling_window_hours if type(rolling_window_hours) in (int, float)
            and 0 < rolling_window_hours <= 24 * 3660 else "invalid")
    window = old_windows[0] if old_windows else {}
    if declarations and any(w != declarations[0] for w in declarations):
        return {**evidence, "classification": "membership_unknown", "reason": "rolling_window_conflict"}
    if rolling_window_hours is not None:
        chosen = {"type": "ROLLIEREND", "stunden": rolling_window_hours}
        # A selection fills missing policy. It cannot replace retained evidence.
        if declarations and (not isinstance(declarations[0], dict) or
                declarations[0].get("type") != "ROLLIEREND" or
                type(declarations[0].get("stunden")) not in (int, float) or
                type(rolling_window_hours) not in (int, float) or
                declarations[0]["stunden"] != rolling_window_hours):
            return {**evidence, "classification": "membership_unknown", "reason": "rolling_window_conflict"}
        if not declarations:
            window = chosen
    evidence["window_basis"] = "capture_filter" if old_windows else "explicit_comparison_selection" if rolling_window_hours is not None else "none"
    if not allow_entering:
        return {**evidence, "classification": "membership_unknown", "reason": "filter_mismatch"}
    if side == "new" and isinstance(window, dict) and window.get("type") == "ROLLIEREND":
        hours = window.get("stunden")
        if type(hours) not in (int, float) or not 0 < hours <= 24 * 3660:
            return {**evidence, "classification": "membership_unknown", "reason": "rolling_window_unresolved"}
        if new_capture.captured_at <= old_capture.captured_at:
            return {**evidence, "classification": "membership_unknown", "reason": "rolling_window_not_advancing"}
        try:
            edge = old_capture.captured_at.astimezone(timezone.utc) + timedelta(hours=hours)
        except OverflowError:
            return {**evidence, "classification": "membership_unknown", "reason": "rolling_window_unresolved"}
        evidence["previous_window_edge"] = edge.isoformat()
        if all(start >= edge for start, _ in bounds):
            return {**evidence, "classification": "entering_window", "reason": "all_validity_starts_at_previous_window_edge"}
    return None


def compare_captures(bundle, old_capture, new_capture, *, reader=None, rolling_window_hours=None) -> ChangeSet:
    from nightdesk.store import ReadSession
    reader = reader or ReadSession(bundle)
    context = dict(old_capture=old_capture.capture_id, new_capture=new_capture.capture_id, basis="selected_captures")
    gate = capture_comparison_gate(old_capture, new_capture)
    if (not gate.passed and gate.reason_code not in {"incomplete_capture", "filter_mismatch"}) or old_capture.bundle != bundle.name:
        return ChangeSet(**context, status="comparison_unavailable", reason=gate.reason_code or "bundle_mismatch")
    old = [load_revision(bundle, key, reader=reader) for key in old_capture.revision_ids]
    new = [load_revision(bundle, key, reader=reader) for key in new_capture.revision_ids]
    refs = [r.source for r in old + new]
    if any(r.identity == "uncertain" for r in old + new):
        return ChangeSet(**context, input_refs=refs, status="identity_uncertain", reason="identity_uncertain")
    if any(r.source.dataset != old_capture.dataset for r in old + new):
        return ChangeSet(**context, input_refs=refs, status="comparison_unavailable", reason="dataset_mismatch")
    index = lambda rows: {(r.subject_type, r.subject_key): r for r in rows}
    a, b = index(old), index(new)
    if len(a) != len(old) or len(b) != len(new):
        return ChangeSet(**context, input_refs=refs, status="identity_uncertain", reason="duplicate_subject")
    diffs, days = [], set()
    for key in sorted(a.keys() & b.keys()) if gate.passed else ():
        compared = compare_revisions(a[key], b[key])
        diffs.extend(d.model_copy(update={"field": "/".join(key) + ":" + d.field}) for d in compared.field_diffs)
        days.update(compared.affected_dates)
    membership = []
    added, removed = [], []
    for side, rows, keys, output in (("old", a, a.keys() - b.keys(), removed),
                                      ("new", b, b.keys() - a.keys(), added)):
        for key in sorted(keys):
            # Expiry can be described across differing/unknown filters; a newly
            # observed row cannot then be attributed to the forward window.
            item = window_membership(rows[key], old_capture, new_capture, side,
                    rolling_window_hours=rolling_window_hours, allow_entering=gate.reason_code != "filter_mismatch")
            if item is None and isinstance(rows[key].payload, WorkNotice):
                item = {"revision_id": rows[key].revision_id, "side": side,
                        "source": rows[key].source.model_dump(mode="json"),
                        "classification": "only_in_selected_" + side if gate.passed else "membership_unknown",
                        "reason": "source_membership_only_not_publication_or_cancellation" if gate.passed else gate.reason_code}
            if item:
                membership.append(item)
            if gate.passed and (item is None or item["classification"] not in {"expired_out_of_window", "entering_window"}):
                output.append(rows[key].revision_id)
    if membership:
        from nightdesk.audit import append_once
        append_once(bundle, "capture_membership_checked", {**context, "rule_version": "changes-v2",
                    "status": "compared" if gate.passed else "comparison_unavailable",
                    "reason": gate.reason_code, "membership_changes": membership,
                    "limits": "Selected export membership only; no publication or cancellation inferred."})
    if not gate.passed:
        return ChangeSet(**context, input_refs=refs, status="comparison_unavailable", reason=gate.reason_code,
                         membership_changes=membership)
    for identifier in added + removed:
        days.update(affected_dates(load_revision(bundle, identifier, reader=reader)))
    return ChangeSet(**context, input_refs=refs, status="compared", field_diffs=diffs,
                     added=added, removed=removed, membership_changes=membership, affected_dates=sorted(days))
