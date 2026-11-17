"""Explicit selected-revision and selected-capture comparisons. No supersession."""

from datetime import timedelta

from nightdesk.gates import capture_comparison_gate
from nightdesk.model import ChangeSet, FieldDiff, Revision, PathLeg
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


def compare_captures(bundle, old_capture, new_capture, *, reader=None) -> ChangeSet:
    from nightdesk.store import ReadSession
    reader = reader or ReadSession(bundle)
    context = dict(old_capture=old_capture.capture_id, new_capture=new_capture.capture_id, basis="selected_captures")
    gate = capture_comparison_gate(old_capture, new_capture)
    if not gate.passed or old_capture.bundle != bundle.name:
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
    for key in sorted(a.keys() & b.keys()):
        compared = compare_revisions(a[key], b[key])
        diffs.extend(d.model_copy(update={"field": "/".join(key) + ":" + d.field}) for d in compared.field_diffs)
        days.update(compared.affected_dates)
    added = [b[k].revision_id for k in sorted(b.keys() - a.keys())]
    removed = [a[k].revision_id for k in sorted(a.keys() - b.keys())]
    for identifier in added + removed:
        days.update(affected_dates(load_revision(bundle, identifier, reader=reader)))
    return ChangeSet(**context, input_refs=refs, status="compared", field_diffs=diffs,
                     added=added, removed=removed, affected_dates=sorted(days))
