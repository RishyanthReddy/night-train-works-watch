"""Profile a table: per column the inferred type, null rate and up to five sample values.

Inference only describes what the values look like; it changes nothing.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from typing import Any

from nightdesk.intake.table import Table

MAX_SAMPLES = 5
_INT = re.compile(r"[+-]?\d+")
_FLOAT = re.compile(r"[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?")
_BOOL = {"true", "false"}


def is_null(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def value_type(value: Any) -> str:
    """Type name of one non-null value. Strings are classified by their text."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, dt.datetime):
        return "datetime"
    if isinstance(value, dt.date):
        return "date"
    if isinstance(value, dt.time):
        return "time"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    text = str(value).strip()
    if _INT.fullmatch(text):
        return "int"
    if _FLOAT.fullmatch(text):
        return "float"
    if text.lower() in _BOOL:
        return "bool"
    for kind, parse in (("date", dt.date.fromisoformat), ("datetime", dt.datetime.fromisoformat),
                        ("time", dt.time.fromisoformat)):
        try:
            parse(text)
        except ValueError:
            continue
        return kind
    return "string"


def infer(types: Counter[str]) -> str:
    kinds = set(types)
    if not kinds:
        return "empty"
    if len(kinds) == 1:
        return kinds.pop()
    if kinds == {"int", "float"}:
        return "float"
    if kinds == {"date", "datetime"}:
        return "datetime"
    return "mixed"


def display(value: Any) -> Any:
    """JSON-safe form of a sample value; nested JSON keeps its structure."""
    if isinstance(value, (dt.date, dt.time)):
        return value.isoformat()
    return value


def profile(table: Table) -> dict[str, Any]:
    n = len(table.rows)
    columns = []
    for col in table.columns:
        values = [row.get(col) for row in table.rows]
        present = [v for v in values if not is_null(v)]
        types = Counter(value_type(v) for v in present)
        samples: list[Any] = []
        for v in present:
            shown = display(v)
            if shown not in samples:
                samples.append(shown)
            if len(samples) == MAX_SAMPLES:
                break
        nulls = n - len(present)
        columns.append({
            "name": col,
            "type": infer(types),
            "type_counts": dict(sorted(types.items())),
            "null_count": nulls,
            "null_rate": round(nulls / n, 4) if n else 0.0,
            "samples": samples,
        })
    return {
        "path": str(table.path),
        "file_type": table.file_type,
        "row_count": n,
        "skipped_blank_rows": table.skipped_blank_rows,
        "columns": columns,
    }


def format_profile(prof: dict[str, Any]) -> str:
    import json

    lines = [
        f"{prof['path']} ({prof['file_type']}): {prof['row_count']} rows, {len(prof['columns'])} columns",
    ]
    if prof["skipped_blank_rows"]:
        lines.append(f"skipped blank rows: {prof['skipped_blank_rows']}")
    for c in prof["columns"]:
        samples = ", ".join(json.dumps(s, ensure_ascii=False, default=str) for s in c["samples"])
        lines.append(f"- {c['name']}: {c['type']}, null {c['null_rate']:.1%} ({c['null_count']}), samples: {samples}")
    return "\n".join(lines)
