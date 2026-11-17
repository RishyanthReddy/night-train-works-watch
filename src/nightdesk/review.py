"""Revision-bound local decisions and questions, with append-only history."""

from datetime import datetime, timezone
from uuid import uuid4

from nightdesk.audit import append_event, read_events
from nightdesk.model import ReviewDecision, FollowUp, SourceRef
from nightdesk.store import load_revision, ReadSession


def _text(value: str, name: str) -> str:
    if not value.strip():
        raise ValueError(name + "_required")
    return value


def record_decision(bundle, revision_id: str, actor: str, disposition: str, reason: str,
                    evidence: list[SourceRef] | None = None) -> ReviewDecision:
    revision = load_revision(bundle, revision_id)
    evidence = evidence or [revision.source]
    if any(ref.bundle != bundle.name for ref in evidence):
        raise ValueError("cross_bundle_evidence")
    decision = ReviewDecision(revision_id=revision_id, actor=_text(actor, "actor"), disposition=disposition,
                              reason=_text(reason, "reason"), evidence=evidence, at=datetime.now(timezone.utc))
    data = decision.model_dump(mode="json")
    data["evidence"] = [ref.model_dump(mode="json", exclude={"field_evidence"}) for ref in evidence]
    append_event(bundle, "review_recorded", {"decision": data})
    return decisions(bundle)[-1]


def follow_up(bundle, revision_id: str, owner: str, question: str, *,
              depends_on: str | None = None, deadline=None, deadline_source: SourceRef | None = None) -> FollowUp:
    load_revision(bundle, revision_id)
    if deadline_source is not None and deadline_source.bundle != bundle.name:
        raise ValueError("cross_bundle_deadline_source")
    item = FollowUp(follow_up_id=uuid4().hex, revision_id=revision_id, owner=_text(owner, "owner"),
                    question=_text(question, "question"), depends_on=depends_on,
                    deadline=deadline, deadline_source=deadline_source)
    data = item.model_dump(mode="json")
    if deadline_source:
        data["deadline_source"] = deadline_source.model_dump(mode="json", exclude={"field_evidence"})
    append_event(bundle, "follow_up_created", {"follow_up": data})
    return item


def answer_follow_up(bundle, identifier: str, actor: str, answer: str):
    if not any(f.follow_up_id == identifier for f in follow_ups(bundle)):
        raise ValueError("follow_up_not_in_bundle")
    append_event(bundle, "follow_up_answered", {"follow_up_id": identifier,
                                              "actor": _text(actor, "actor"), "answer": _text(answer, "answer")})


def _observations(bundle, events, reader):
    """Accepted capture observations, including a return to existing content."""
    out = []
    for event in events:
        ids = event.payload.get("revision_ids", [])
        if event.kind == "revision_created":
            ids = [event.payload["revision_id"]]
        elif event.kind == "ingested" and "revision_ids" not in event.payload:
            from nightdesk.intake.mapping import load_capture
            ids = load_capture(bundle.root / "captures" / event.payload["capture_id"], bundle, reader=reader)["capture"].revision_ids
        elif event.kind == "batch_imported" and "revision_ids" not in event.payload:
            from nightdesk.intake.batch import load_batch
            ids = load_batch(bundle, event.payload["capture_id"], reader=reader)["capture"].revision_ids
        if event.kind in {"revision_created", "ingested", "batch_imported"}:
            out.extend((event.seq, identifier) for identifier in ids)
    return out


def _observation_index(bundle, events, reader):
    observed = _observations(bundle, events, reader)
    subjects, by_subject, by_revision = {}, {}, {}
    for _, identifier in observed:
        if identifier not in subjects:
            revision = load_revision(bundle, identifier, reader=reader)
            subjects[identifier] = (revision.source.dataset, revision.subject_type, revision.subject_key)
    for seq, identifier in observed:
        by_subject.setdefault(subjects[identifier], []).append((seq, identifier))
        by_revision.setdefault(identifier, []).append(seq)
    return subjects, by_subject, by_revision


def _changes_after_basis(identifier, created_seq, index):
    subjects, by_subject, by_revision = index
    basis = max((seq for seq in by_revision.get(identifier, []) if seq <= created_seq), default=None)
    if basis is None:
        return [created_seq]
    return [seq for seq, other in by_subject[subjects[identifier]] if seq > basis and other != identifier]


def decisions(bundle, *, reader=None) -> list[ReviewDecision]:
    reader = reader or ReadSession(bundle)
    reader.check_bundle(bundle)
    events = reader.events
    selected = [e for e in events if e.kind == "review_recorded"]
    if not selected:
        return []
    observed = _observation_index(bundle, events, reader)
    out = []
    for event in selected:
        d = ReviewDecision.model_validate(event.payload["decision"])
        load_revision(bundle, d.revision_id, reader=reader)
        if any(ref.bundle != bundle.name for ref in d.evidence):
            raise ValueError("cross_bundle_review_evidence")
        out.append(d.model_copy(update={"stale": bool(_changes_after_basis(d.revision_id, event.seq, observed))}))
    return out


def follow_ups(bundle, *, reader=None) -> list[FollowUp]:
    reader = reader or ReadSession(bundle)
    reader.check_bundle(bundle)
    events = reader.events
    if not any(e.kind == "follow_up_created" for e in events):
        return []
    observed = _observation_index(bundle, events, reader)
    out, created, answered = {}, {}, {}
    for event in events:
        if event.kind == "follow_up_created":
            f = FollowUp.model_validate(event.payload["follow_up"])
            load_revision(bundle, f.revision_id, reader=reader)
            out[f.follow_up_id], created[f.follow_up_id] = f, event.seq
        elif event.kind == "follow_up_answered" and event.payload["follow_up_id"] in out:
            answered[event.payload["follow_up_id"]] = event.seq
    result = []
    for identifier, f in out.items():
        changes = _changes_after_basis(f.revision_id, created[identifier], observed)
        latest_change = max(changes, default=-1)
        answer_seq = answered.get(identifier, -1)
        status = "reopened" if latest_change > answer_seq else "answered" if answer_seq >= 0 else "open"
        result.append(f.model_copy(update={"status": status}))
    return result
