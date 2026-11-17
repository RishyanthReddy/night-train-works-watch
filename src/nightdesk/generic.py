"""Source-linked generic tables and explicit comparisons, without rail inference."""

from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from nightdesk.audit import canonical_json
from nightdesk.config import Bundle
from nightdesk.intake.mapping import captures, check_input, digest, json_value
from nightdesk.intake.table import read_table
from nightdesk.model import GenericRow, SourceRef

RULE_VERSION = "generic-v2"


def row_values(row: GenericRow) -> dict:
    return {"fields": row.fields, "extra": row.extra, "unresolved": row.unresolved}


def source_table(path: str | Path, bundle: Bundle, capture_id: str | None = None):
    """Use the exact imported file version, else expose raw columns as unvalidated.

    Never silently choose a newest mapping when several captures describe a file.
    """
    check_input(path, bundle)
    path = Path(path)
    sha = digest(path.read_bytes())
    matches = [c for c in captures(bundle) if c["metadata"]["path"] == str(path.resolve())
               and c["metadata"]["file_sha256"] == sha]
    if capture_id:
        matches = [c for c in matches if c["capture"].capture_id == capture_id]
        if not matches:
            raise ValueError("selected capture does not match this file version in this bundle")
    if len(matches) > 1:
        raise ValueError("multiple captures for this file version: select --old-capture or --new-capture")
    if matches:
        c = matches[0]
        return {"rows": c["rows"], "rejects": c["rejects"], "mode": "confirmed_mapping",
                "capture": c["capture"].model_dump(mode="json"), "file_sha256": sha}
    table = read_table(path)
    if digest(path.read_bytes()) != sha:
        raise ValueError("input changed while reading; retry")
    now = datetime.now(timezone.utc)
    capture = digest(canonical_json([bundle.name, str(path.resolve()), sha, "unmapped"]).encode())
    rows = []
    for raw, number in zip(table.rows, table.row_numbers):
        ref = SourceRef(bundle=bundle.name, dataset="unmapped", record_id=f"row:{number}",
                        capture_id=capture, content_sha256=digest(canonical_json(json_value(raw)).encode()),
                        captured_at=now, url_or_path=str(path.resolve()), licence="UNKNOWN - not checked")
        rows.append(GenericRow(source=ref, fields=json_value(raw)))
    return {"rows": rows, "rejects": [], "mode": "unmapped_columns_unvalidated", "file_sha256": sha,
            "capture": {"capture_id": capture, "bundle": bundle.name, "dataset": "unmapped", "complete": False}}


def _key(row: GenericRow, field: str):
    value = row.fields.get(field)
    if value is None or (isinstance(value, str) and not value.strip()) or isinstance(value, (list, dict, bool)):
        raise ValueError("missing_or_nonscalar_key")
    return canonical_json(value)


def _field_diffs(old: GenericRow, new: GenericRow) -> list[dict]:
    diffs = []
    for group in ("fields", "extra", "unresolved"):
        a, b = getattr(old, group), getattr(new, group)
        for name in sorted(a.keys() | b.keys()):
            if (name in a) != (name in b) or canonical_json(a.get(name)) != canonical_json(b.get(name)):
                diffs.append({"field": name if group == "fields" else f"{group}.{name}",
                              "old": a.get(name), "new": b.get(name),
                              "old_present": name in a, "new_present": name in b})
    return diffs


def compare_rows(old: list[GenericRow], new: list[GenericRow], key: str | None = None) -> dict:
    """Keyed before/after when identity is usable; otherwise a multiset row diff."""
    bundles = {r.source.bundle for r in old + new}
    if len(bundles) > 1:
        raise ValueError("cannot compare rows from different bundles")
    if key and old + new and not any(key in r.fields for r in old + new):
        raise ValueError(f"comparison key {key!r} is absent from both tables")
    reason = "no_key" if not key else None
    if key:
        try:
            a = {_key(r, key): r for r in old}
            b = {_key(r, key): r for r in new}
            if len(a) != len(old) or len(b) != len(new):
                reason = "duplicate_key"
        except ValueError as exc:
            reason = str(exc)
    changed, unchanged, added, only_old = [], [], [], []
    if reason is None:
        for k in sorted(a.keys() | b.keys()):
            left, right = a.get(k), b.get(k)
            item = {"key": json_value((left or right).fields[key]),
                    "old": left.model_dump(mode="json") if left else None,
                    "new": right.model_dump(mode="json") if right else None}
            if left is None:
                added.append(item)
            elif right is None:
                only_old.append(item)
            else:
                item["field_diffs"] = _field_diffs(left, right)
                (changed if item["field_diffs"] else unchanged).append(item)
    else:
        # Preserve duplicates: each identical old row consumes exactly one new row.
        remaining = defaultdict(deque)
        for row in new:
            remaining[canonical_json(row_values(row))].append(row)
        for row in old:
            bucket = remaining[canonical_json(row_values(row))]
            if bucket:
                unchanged.append({"old": row.model_dump(mode="json"), "new": bucket.popleft().model_dump(mode="json")})
            else:
                only_old.append({"old": row.model_dump(mode="json"), "new": None})
        for bucket in remaining.values():
            added.extend({"old": None, "new": r.model_dump(mode="json")} for r in bucket)
    return {"rule_version": RULE_VERSION, "status": "identity_uncertain" if reason else "compared",
            "reason": reason, "key": key, "changed": changed, "unchanged": unchanged,
            "added": added, "only_in_old": only_old,
            "counts": {"changed": len(changed), "added": len(added), "unchanged": len(unchanged), "only_in_old": len(only_old)},
            "limits": ["Differences describe these selected file rows only.",
                       "A row absent from a selected file is not evidence of cancellation or withdrawal.",
                       "No national approval, journey feasibility or delay prediction is inferred."]}


def compare_files(old, new, bundle: Bundle, key=None, *, old_capture=None, new_capture=None) -> dict:
    a = source_table(old, bundle, old_capture)
    b = source_table(new, bundle, new_capture)
    if a["mode"] != b["mode"]:
        raise ValueError("mode_mismatch: ingest both selected files with compatible mappings before comparison")
    if a["capture"]["dataset"] != b["capture"]["dataset"]:
        raise ValueError("dataset_mismatch: selected captures do not describe the same dataset")
    report = compare_rows(a["rows"], b["rows"], key)
    report.update(bundle=bundle.name,
                  inputs={"old": {k: v for k, v in a.items() if k != "rows"},
                          "new": {k: v for k, v in b.items() if k != "rows"}})
    licences = {r.source.licence for r in a["rows"] + b["rows"]}
    report["data_label"] = "synthetic" if licences == {"synthetic"} else "see_each_source_licence"
    return report
