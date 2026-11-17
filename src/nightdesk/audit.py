"""Append-only JSONL audit log, one file per bundle at <bundle root>/audit.jsonl.

Phase 0 only appends and reads. The hash chain, seal and verify come in Phase 1;
nothing here claims tamper-proofing. Payloads should reference restricted sources
via `model.source_ref_payload`, not copy their text.
"""

from __future__ import annotations

import json
import os
import fcntl
from datetime import datetime, timezone
from pathlib import Path

from nightdesk.config import Bundle, BundleError
from nightdesk.model import AuditEvent, JSONValue

AUDIT_FILE = "audit.jsonl"


class AuditError(ValueError):
    """The existing audit file is unreadable, truncated or belongs to another bundle."""


def canonical_json(data: object) -> str:
    """Sorted keys, UTF-8, no extra whitespace, no NaN/Infinity."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def audit_path(bundle: Bundle) -> Path:
    """The bundle's audit file. Refused if it is a symlink or resolves outside the root."""
    path = bundle.root / AUDIT_FILE
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
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        try:
            event = AuditEvent.model_validate_json(line)
        except ValueError as exc:
            raise AuditError(f"{path}:{lineno}: invalid event: {exc}") from exc
        if event.bundle != bundle.name:
            raise AuditError(f"{path}:{lineno}: event bundle {event.bundle!r} is not {bundle.name!r}")
        if event.seq != lineno - 1:
            raise AuditError(f"{path}:{lineno}: seq {event.seq} expected {lineno - 1}")
        events.append(event)
    return events


def append_event(
    bundle: Bundle,
    kind: str,
    payload: dict[str, JSONValue] | None = None,
    ts: datetime | None = None,
) -> AuditEvent:
    """Validate and append one event; earlier lines are never rewritten."""
    return append_events(bundle, [(kind, payload or {})], ts)[0]


def append_events(bundle: Bundle, events: list[tuple[str, dict]], ts: datetime | None = None) -> list[AuditEvent]:
    """One locked batch: validate history once, allocate seq, append all events.

    fcntl locking covers independent CLI processes on the supported Unix hosts.
    This is still a Phase 0 append-only log, without a chain or a seal.
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
        appended = [event.model_copy(update={"seq": len(existing) + i}) for i, event in enumerate(pending)]
        lines = "".join(canonical_json(event.model_dump(mode="json")) + "\n" for event in appended)
        fh.write(lines.encode("utf-8"))
        fh.flush()
    return appended
