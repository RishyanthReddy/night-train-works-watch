"""Bundle-scoped immutable revisions. Import order never implies supersession.

The identifier excludes capture time/path. Every load rechecks the canonical
content hash. First source stays attached to an existing revision forever.
"""

import hashlib
import re
from pathlib import Path

from nightdesk.audit import canonical_json, append_event
from nightdesk.config import Bundle
from nightdesk.model import SourceRef, Revision, WorkNotice, PathLeg


def hash_value(value) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def subject_key(payload: WorkNotice | PathLeg) -> tuple[str, str]:
    if isinstance(payload, WorkNotice):
        if payload.work_id and payload.work_id.strip():
            return payload.work_id, "certain"
    else:
        identity = payload.request_id or payload.journey_ref
        if identity and identity.strip() and payload.sequence is not None:
            return canonical_json([identity, payload.network, payload.sequence]), "certain"
    # No near-match guessing: this identifies this exact unkeyed input only.
    return "unresolved:" + hash_value(payload.model_dump(mode="json")), "uncertain"


def revision_hash(*, bundle: str, dataset: str, subject_type: str, subject_key: str,
                  source_status: str | None, payload: WorkNotice | PathLeg) -> str:
    return hash_value(dict(bundle=bundle, dataset=dataset, subject_type=subject_type,
                           subject_key=subject_key, source_status=source_status,
                           payload=payload.model_dump(mode="json")))


def same_subject(a: Revision, b: Revision) -> bool:
    return ((a.source.bundle, a.source.dataset, a.subject_type, a.subject_key) ==
            (b.source.bundle, b.source.dataset, b.subject_type, b.subject_key))


def revision_path(bundle: Bundle, revision_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{64}", revision_id):
        raise ValueError("invalid_revision_id")
    return bundle.resolve(bundle.root / "revisions" / (revision_id + ".json"))


class ReadSession:
    """One operation's verified audit, captures and revisions. Never shared globally."""
    def __init__(self, bundle, events=None):
        self.bundle = bundle
        self._events = None
        self.created, self.predecessors, self.imports, self.batch_imports = {}, {}, {}, {}
        self.capture_cache, self.batch_cache, self.raw_revisions, self.source_rows = {}, {}, {}, {}
        self.confirmed = {}
        self.pending_events = None  # an importer holds both writer locks before deferring
        if events is not None:
            self.set_events(events)

    def set_events(self, events):
        self._events = events
        self.created, self.predecessors, self.imports, self.batch_imports = {}, {}, {}, {}
        self.confirmed = {}
        for event in events:
            payload = event.payload
            if event.kind == "mapping_confirmed":
                self.confirmed.setdefault(payload["mapping_sha256"], []).append(payload["path"])
            elif event.kind == "revision_created":
                self.created.setdefault(payload["revision_id"], payload)
            elif event.kind == "predecessor_recorded":
                self.predecessors.setdefault(payload["revision_id"], (payload["predecessor"], payload["basis"]))
            elif event.kind == "ingested":
                self.imports[payload["capture_id"]] = payload
            elif event.kind == "batch_imported":
                self.batch_imports[payload["capture_id"]] = payload

    @property
    def events(self):
        if self._events is None:
            from nightdesk.audit import read_events
            self.set_events(read_events(self.bundle))
        return self._events

    def check_bundle(self, bundle):
        if bundle.name != self.bundle.name or bundle.real_root() != self.bundle.real_root():
            raise ValueError("cross_bundle_read_session")

    def capture(self, capture_id):
        from nightdesk.intake.mapping import load_capture
        return load_capture(self.bundle.root / "captures" / capture_id, self.bundle, reader=self)

    def get(self, revision_id):
        if revision_id not in self.raw_revisions:
            record = Revision.model_validate_json(revision_path(self.bundle, revision_id).read_text("utf-8"))
            if record.source.bundle != self.bundle.name or record.revision_id != revision_id:
                raise ValueError("revision_reference_mismatch")
            expected = revision_hash(bundle=self.bundle.name, dataset=record.source.dataset,
                subject_type=record.subject_type, subject_key=record.subject_key,
                source_status=record.source_status, payload=record.payload)
            if expected != revision_id:
                raise ValueError("revision_content_hash_mismatch")
            capture_id = record.source.capture_id
            if capture_id not in self.source_rows:
                folder = self.bundle.resolve(self.bundle.root / "captures" / capture_id)
                self.source_rows[capture_id] = ({row.source.record_id: row.source for row in self.capture(capture_id)["rows"]}
                                                if folder.exists() else None)
            rows = self.source_rows[capture_id]
            if rows is not None and rows.get(record.source.record_id) != record.source:
                raise ValueError("revision_source_mismatch")
            self.events
            committed = self.created.get(revision_id, {}).get("source_sha256")
            if committed is not None and committed != hash_value(record.source.model_dump(mode="json")):
                raise ValueError("revision_source_hash_mismatch")
            self.raw_revisions[revision_id] = record
        record = self.raw_revisions[revision_id]
        self.events
        if revision_id not in self.created and self.pending_events is None:
            raise ValueError("revision_import_evidence_missing")
        committed = self.created.get(revision_id, {}).get("source_sha256")
        if committed is not None and committed != hash_value(record.source.model_dump(mode="json")):
            raise ValueError("revision_source_hash_mismatch")
        relationship = self.predecessors.get(revision_id)
        if record.predecessor is not None and relationship != (record.predecessor, record.predecessor_basis):
            raise ValueError("revision_predecessor_metadata_mismatch")
        predecessor, basis = relationship or (None, None)
        return record.model_copy(deep=True, update={"predecessor": predecessor, "predecessor_basis": basis})


def load_revision(bundle: Bundle, revision_id: str, *, reader=None) -> Revision:
    reader = reader or ReadSession(bundle)
    reader.check_bundle(bundle)
    return reader.get(revision_id)


def revisions(bundle: Bundle) -> list[Revision]:
    folder = bundle.resolve(bundle.root / "revisions")
    if not folder.exists():
        return []
    reader = ReadSession(bundle)
    return [load_revision(bundle, p.stem, reader=reader) for p in sorted(folder.glob("*.json"))]


def make_revision(bundle: Bundle, source: SourceRef, payload: WorkNotice | PathLeg,
                  predecessor: str | None = None, predecessor_basis: str | None = None, *, reader=None):
    if source.bundle != bundle.name:
        raise ValueError("cross_bundle_source")
    subject_type = "work" if isinstance(payload, WorkNotice) else "path_leg"
    key, identity = subject_key(payload)
    status = payload.source_status if isinstance(payload, PathLeg) else None
    identifier = revision_hash(bundle=bundle.name, dataset=source.dataset, subject_type=subject_type,
                               subject_key=key, source_status=status, payload=payload)
    r = Revision(revision_id=identifier, subject_type=subject_type, subject_key=key, payload=payload, source=source,
                 source_status=status, identity=identity, import_status="unresolved" if payload.unresolved else "accepted")
    link_reason = None
    if predecessor:
        try:
            prior = load_revision(bundle, predecessor, reader=reader)
            if predecessor == identifier or not same_subject(prior, r) or predecessor_basis not in {"source_field", "human"}:
                raise ValueError("invalid_predecessor")
        except (ValueError, OSError):
            link_reason = "invalid_predecessor"
        else:
            r = r.model_copy(update={"predecessor": predecessor, "predecessor_basis": predecessor_basis})
    elif predecessor_basis is not None:
        link_reason = "invalid_predecessor"
    return r, link_reason


def save_revision(bundle: Bundle, revision: Revision, *, reader=None) -> tuple[Revision, bool]:
    from nightdesk.intake.mapping import write_private
    if revision.source.bundle != bundle.name:
        raise ValueError("cross_bundle_revision")
    expected = revision_hash(bundle=bundle.name, dataset=revision.source.dataset, subject_type=revision.subject_type,
                             subject_key=revision.subject_key, source_status=revision.source_status, payload=revision.payload)
    if expected != revision.revision_id:
        raise ValueError("revision_content_hash_mismatch")
    path = revision_path(bundle, revision.revision_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    # The content/source file stays immutable. Later explicit relationships are
    # append-only audit metadata, so idempotent content never drops a valid link.
    base = revision.model_copy(update={"predecessor": None, "predecessor_basis": None})
    created = True
    try:
        write_private(path, base.model_dump_json(indent=2) + "\n")
    except FileExistsError:
        created = False
    reader = reader or ReadSession(bundle)
    reader.check_bundle(bundle)
    if created:
        reader.raw_revisions[revision.revision_id] = base.model_copy(deep=True)
        if reader.pending_events is None:
            append_event(bundle, "revision_created", {"revision_id": base.revision_id,
                "capture_id": base.source.capture_id, "source_sha256": hash_value(base.source.model_dump(mode="json"))}, reader=reader)
    if revision.predecessor is not None:
        _record_predecessor(bundle, revision, reader=reader)
    return load_revision(bundle, revision.revision_id, reader=reader), created


def _record_predecessor(bundle, proposed, *, reader):
    import fcntl
    import os
    if reader.pending_events is not None:
        _accept_predecessor(bundle, proposed, reader)
        return
    lock = bundle.resolve(bundle.root / "predecessor.lock")
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        # Refresh the relationship index after acquiring the writer lock.
        from nightdesk.audit import read_events
        reader.set_events(read_events(bundle))
        _accept_predecessor(bundle, proposed, reader)


def _accept_predecessor(bundle, proposed, reader):
    existing = load_revision(bundle, proposed.revision_id, reader=reader)
    reason = None
    try:
        prior = load_revision(bundle, proposed.predecessor, reader=reader)
        if (prior.revision_id == proposed.revision_id or not same_subject(prior, proposed)
                or proposed.predecessor_basis not in {"source_field", "human"}):
            reason = "invalid_predecessor"
    except (ValueError, OSError):
        reason = "invalid_predecessor"
    if existing.predecessor and existing.predecessor != proposed.predecessor:
        reason = "predecessor_conflict"
    if reason:
        kind, payload = "predecessor_rejected", {"revision_id": proposed.revision_id,
                       "predecessor": proposed.predecessor, "reason": reason}
    elif existing.predecessor is None:
        kind, payload = "predecessor_recorded", {"revision_id": proposed.revision_id,
                       "predecessor": proposed.predecessor, "basis": proposed.predecessor_basis}
    else:
        return
    if reader.pending_events is not None:
        reader.pending_events.append((kind, payload))
    else:
        append_event(bundle, kind, payload, reader=reader)
    if kind == "predecessor_recorded":
        reader.predecessors[proposed.revision_id] = (proposed.predecessor, proposed.predecessor_basis)
