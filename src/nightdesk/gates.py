"""Common Phase 0 gates. No rail-specific interpretation is done here."""

import re
from datetime import datetime
from pydantic import ValidationError

from nightdesk.model import GenericRow, GateResult, WorkNotice, PathLeg, RunRow, JourneyLinkMember
from nightdesk.config import (WORK_EFFECTS, RECURRENCES, EVENT_KINDS,
                             WORK_YEAR_BEFORE_CAPTURE, WORK_YEAR_AFTER_CAPTURE)
from nightdesk.timeutil import utc

NAMESPACED_FIELDS = {"train_no", "point_id", "line", "line_dep", "line_arr"}
NAMESPACED_ID = re.compile(r"[^\s:]+:[^\s:]+")


def common_gates(row: GenericRow) -> list[GateResult]:
    """C1/C2 are established by the canonical schema; C4/C5 by mapping parsers."""
    results = [GateResult(gate="C1", passed=True), GateResult(gate="C2", passed=True)]
    for name in NAMESPACED_FIELDS & row.fields.keys():
        value = row.fields[name]
        passed = value is None or (isinstance(value, str) and bool(NAMESPACED_ID.fullmatch(value)))
        results.append(GateResult(gate="C3", passed=passed,
                                  reason_code=None if passed else "id_not_namespaced", detail=name))
    return results


TYPED_RECORDS = {"WorkNotice": WorkNotice, "PathLeg": PathLeg,
                 "RunRow": RunRow, "JourneyLinkMember": JourneyLinkMember}
REVISION_FIELDS = {"predecessor", "predecessor_basis"}


def typed_field_names(record: str) -> set[str]:
    model = TYPED_RECORDS[record]
    names = set(model.model_fields) - {"source", "extra", "unresolved"}
    if record == "PathLeg":
        from nightdesk.model import BoundaryEvent
        names |= {f"{side}.{field}" for side in ("entry", "exit") for field in BoundaryEvent.model_fields
                  if field not in {"extra", "unresolved"}}
    return names | REVISION_FIELDS


def typed_record(row: GenericRow, record: str, zone: str | None):
    """Return validated payload plus applicable common/work/leg gates.

    Enum clamping retains original evidence; no place or journey link is guessed.
    """
    values = {}
    raw_weekdays = row.fields.get("weekdays")
    if record == "WorkNotice" and raw_weekdays is not None:
        if not isinstance(raw_weekdays, list) or any(type(d) is not int or d not in range(1, 8) for d in raw_weekdays):
            return None, [GateResult(gate="W3", passed=False, reason_code="invalid_weekdays", detail="weekdays")]
    unknown = dict(row.unresolved)
    for name, value in row.fields.items():
        if name in REVISION_FIELDS:
            continue
        node = values
        parts = name.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    def clamp(node, name, allowed):
        if name in node and node[name] not in allowed:
            unknown[name] = {"raw": node[name], "reason": "unknown_enum"}
            node[name] = "unknown"
    if record == "WorkNotice":
        values.setdefault("timezone", zone)
        clamp(values, "recurrence", RECURRENCES)
        clamp(values, "effect", WORK_EFFECTS)
        clamp(values, "proposed_by", ("adapter", "llm", "manual"))
    if record == "PathLeg":
        for side in ("entry", "exit"):
            event = values.get(side)
            if isinstance(event, dict):
                clamp(event, "kind", EVENT_KINDS)
                event.setdefault("timezone", zone)
                unresolved = row.unresolved.get(side + ".at")
                if unresolved:
                    event["raw_time"] = " ".join(str(x or "") for x in unresolved.get("raw", []))
                    event["unresolved_reason"] = unresolved.get("reason")
                if event.get("at") is not None and not event.get("raw_time"):
                    event["raw_time"] = str(event["at"])
    values.update(extra=row.extra, unresolved=unknown)
    if record in {"RunRow", "JourneyLinkMember"}:
        values["source"] = row.source
    try:
        payload = TYPED_RECORDS[record].model_validate(values)
    except ValidationError as exc:
        # Do not copy source values from Pydantic exception messages into logs.
        return None, [GateResult(gate="C1", passed=False, reason_code="schema_invalid",
                                 detail=".".join(map(str, error["loc"]))) for error in exc.errors()]
    results = [GateResult(gate="C1", passed=True), GateResult(gate="C2", passed=True), GateResult(gate="C3", passed=True)]
    def check(gate, passed, reason, detail):
        results.append(GateResult(gate=gate, passed=passed, reason_code=None if passed else reason, detail=detail))
    if isinstance(payload, WorkNotice):
        year = row.source.captured_at.year
        plausible = (year - WORK_YEAR_BEFORE_CAPTURE <= payload.date_start.year <= year + WORK_YEAR_AFTER_CAPTURE
                     and year - WORK_YEAR_BEFORE_CAPTURE <= payload.date_end.year <= year + WORK_YEAR_AFTER_CAPTURE)
        check("W1", payload.date_end >= payload.date_start and plausible, "invalid_work_dates", "date_start/date_end")
        check("W3", payload.weekdays is None or all(type(d) is int and 1 <= d <= 7 for d in payload.weekdays),
              "invalid_weekdays", "weekdays")
        valid_clock = not (payload.clock_from and payload.clock_from.tzinfo or payload.clock_to and payload.clock_to.tzinfo)
        check("W2", valid_clock, "invalid_work_clock", "clock_from/clock_to")
        if (payload.recurrence == "continuous" and payload.clock_from is not None and payload.clock_to is not None
                and payload.date_start == payload.date_end):
            check("W2", payload.clock_to >= payload.clock_from, "reversed_continuous_window", "clock_from/clock_to")
    if isinstance(payload, PathLeg):
        check("L1", bool(payload.operating_dates), "operating_dates_empty", "operating_dates")
        a, b = payload.entry, payload.exit
        if a and b and a.at is not None and b.at is not None:
            check("L2", utc(b.at) > utc(a.at), "reversed_leg", "exit.at")
    return payload, results


def capture_comparison_gate(old, new) -> GateResult:
    """R2 uses effective completeness, same bundle/dataset and exact filter."""
    from nightdesk.audit import canonical_json
    reason = None
    if old.bundle != new.bundle:
        reason = "bundle_mismatch"
    elif old.dataset != new.dataset:
        reason = "dataset_mismatch"
    elif canonical_json(old.filter) != canonical_json(new.filter):
        reason = "filter_mismatch"
    elif not old.complete or not new.complete:
        reason = "incomplete_capture"
    return GateResult(gate="R2", passed=reason is None, reason_code=reason,
                      detail="Effective completeness and equal source/filter are required for added/removed lists.")
