"""Append-only JSONL audit log, one file per bundle at <bundle root>/audit.jsonl.

Hash chaining shows internal consistency. An external seal/count is required to
detect truncated tails or a complete rewrite. It does not prove source truth.
Legacy Phase 0 logs can be explicitly upgraded without rewriting their bytes.
"""

from __future__ import annotations

import json
import os
import fcntl
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from nightdesk.config import Bundle, BundleError
from nightdesk.model import AuditEvent, JSONValue

AUDIT_FILE = "audit.jsonl"
UPGRADED_FILE = "audit-v1.jsonl"
EMPTY_HASH = "0" * 64


class AuditError(ValueError):
    """The existing audit file is unreadable, truncated or belongs to another bundle."""


def canonical_json(data: object) -> str:
    """Sorted keys, UTF-8, no extra whitespace, no NaN/Infinity."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def audit_path(bundle: Bundle) -> Path:
    """The bundle's audit file. Refused if it is a symlink or resolves outside the root."""
    upgraded = bundle.root / UPGRADED_FILE
    if upgraded.is_symlink():
        raise BundleError("upgraded audit file is a symlink")
    path = upgraded if upgraded.exists() else bundle.root / AUDIT_FILE
    if path.is_symlink():
        raise BundleError(f"audit file {path} is a symlink")
    bundle.resolve(path)
    return path


def read_events(bundle: Bundle) -> list[AuditEvent]:
    """All events in order. Refuses a truncated last line or an event from another bundle."""
    path = audit_path(bundle)
    if not path.exists():
        return []
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
        return _decode_events(fh.read(), bundle, path)


def _decode_events(raw: bytes, bundle: Bundle, path: Path) -> list[AuditEvent]:
    if raw and not raw.endswith(b"\n"):
        raise AuditError(f"{path}: last line is incomplete")
    events = []
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise AuditError(f"{path}: invalid UTF-8") from None
    for lineno, line in enumerate(lines, start=1):
        try:
            event = AuditEvent.model_validate_json(line)
        except ValueError:
            raise AuditError(f"{path}:{lineno}: invalid event schema") from None
        if event.bundle != bundle.name:
            raise AuditError(f"{path}:{lineno}: event bundle {event.bundle!r} is not {bundle.name!r}")
        if event.seq != lineno - 1:
            raise AuditError(f"{path}:{lineno}: seq {event.seq} expected {lineno - 1}")
        events.append(event)
    if any(e.hash is not None for e in events):
        previous = None
        for event in events:
            if event.hash is None or event.prev_hash != previous or event.hash != event_hash(event):
                raise AuditError(f"{path}: invalid hash chain at seq {event.seq}")
            previous = event.hash
    elif any(e.prev_hash is not None for e in events):
        raise AuditError(f"{path}: hash missing")
    return events


def event_hash(event: AuditEvent) -> str:
    data = event.model_dump(mode="json", exclude={"hash"})
    return hashlib.sha256(canonical_json(data).encode()).hexdigest()


def append_event(
    bundle: Bundle,
    kind: str,
    payload: dict[str, JSONValue] | None = None,
    ts: datetime | None = None,
    *, reader=None,
) -> AuditEvent:
    """Validate and append one event; earlier lines are never rewritten."""
    return append_events(bundle, [(kind, payload or {})], ts, reader=reader)[0]


def append_events(bundle: Bundle, events: list[tuple[str, dict]], ts: datetime | None = None, *, deduplicate=False, reader=None) -> list[AuditEvent]:
    """One locked batch: validate history once, allocate seq, append all events.

    fcntl locking covers independent CLI processes on the supported Unix hosts.
    Existing lines are never rewritten.
    """
    pending = [AuditEvent(seq=0, ts=ts or datetime.now(timezone.utc), bundle=bundle.name,
                          kind=kind, payload=payload) for kind, payload in events]
    if not pending:
        return []
    # Validate serialisation before creating a file (including numeric range).
    for event in pending:
        canonical_json(event.model_dump(mode="json"))
    bundle.root.mkdir(parents=True, exist_ok=True)
    path = audit_path(bundle)  # re-check after mkdir: root must not be a symlink
    # O_NOFOLLOW: refuse if audit.jsonl itself is a symlink; O_APPEND: never overwrite.
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise BundleError(f"cannot open audit file {path}: {exc}") from exc
    with os.fdopen(fd, "a+b") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        fh.seek(0)
        existing = _decode_events(fh.read(), bundle, path)
        if existing and existing[-1].hash is None:
            raise AuditError("legacy_log_needs_upgrade: run nightdesk audit upgrade --actor <person> --bundle <bundle>")
        if deduplicate:
            known = {(e.kind, canonical_json(e.payload)) for e in existing}
            pending = [e for e in pending if (e.kind, canonical_json(e.payload)) not in known]
        appended = []
        previous = existing[-1].hash if existing else None
        for i, event in enumerate(pending):
            event = event.model_copy(update={"seq": len(existing) + i, "prev_hash": previous})
            event = event.model_copy(update={"hash": event_hash(event)})
            appended.append(event)
            previous = event.hash
        lines = "".join(canonical_json(event.model_dump(mode="json")) + "\n" for event in appended)
        fh.write(lines.encode("utf-8"))
        fh.flush()
    if reader is not None:
        reader.check_bundle(bundle)
        reader.set_events(existing + appended)
    return appended


def verify(bundle: Bundle, *, seal: str | None = None, count: int | None = None) -> dict:
    if (seal is None) != (count is None):
        raise AuditError("external seal and count must be supplied together")
    events = read_events(bundle)
    if events and any(e.hash is None for e in events):
        raise AuditError("legacy_log_needs_upgrade")
    final = events[-1].hash if events else EMPTY_HASH
    if seal is not None and (seal != final or count != len(events)):
        raise AuditError("external_seal_or_count_mismatch")
    return {"valid": True, "hash": final, "count": len(events), "external_seal_checked": seal is not None,
            "limits": "Internal consistency only; no proof of source truth. Tail/rewrite detection needs a trusted external seal and count."}


def upgrade_legacy(bundle: Bundle, actor: str) -> dict:
    """Create a chained copy, preserve original Phase 0 log, record its hash.

    No automatic rewrite or deletion of old evidence. A previously chained log
    needs no upgrade. seq values for old events remain stable.
    """
    import tempfile
    if not actor.strip():
        raise ValueError("actor_required")
    current = audit_path(bundle)
    if not current.exists():
        return verify(bundle)
    fd = os.open(current, os.O_RDWR | os.O_NOFOLLOW)
    with os.fdopen(fd, "r+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        raw = handle.read()
        events = _decode_events(raw, bundle, current)
        if not events or events[-1].hash is not None:
            return {"valid": True, "hash": events[-1].hash if events else EMPTY_HASH, "count": len(events), "already_chained": True}
        target = bundle.resolve(bundle.root / UPGRADED_FILE)
        if target.exists():
            return verify(bundle)
        events.append(AuditEvent(seq=len(events), ts=datetime.now(timezone.utc), bundle=bundle.name,
                                 kind="legacy_chain_upgraded", payload={"actor": actor, "legacy_file": AUDIT_FILE,
                                 "legacy_sha256": hashlib.sha256(raw).hexdigest(), "legacy_count": len(events)}))
        out, previous = [], None
        for event in events:
            event = event.model_copy(update={"prev_hash": previous})
            event = event.model_copy(update={"hash": event_hash(event)})
            out.append(canonical_json(event.model_dump(mode="json")) + "\n")
            previous = event.hash
        fd, temporary = tempfile.mkstemp(prefix=".audit-upgrade-", dir=bundle.real_root())
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                output.write("".join(out))
                output.flush()
                os.fsync(output.fileno())
            os.rename(temporary, target)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
    return verify(bundle)


def append_once(bundle: Bundle, kind: str, payload: dict) -> AuditEvent:
    """Record a deterministic application check once, including concurrent rerenders."""
    added = append_events(bundle, [(kind, payload)], deduplicate=True)
    if added:
        return added[0]
    return next(e for e in reversed(read_events(bundle)) if e.kind == kind and e.payload == payload)
