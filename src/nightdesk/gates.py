"""Common Phase 0 gates. No rail-specific interpretation is done here."""

import re

from nightdesk.model import GenericRow, GateResult

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
