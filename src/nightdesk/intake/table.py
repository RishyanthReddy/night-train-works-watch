"""Read a CSV, XLSX or JSON file into one table of values (shared by sniff and mapping).

Reads cell values only: XLSX formulas are not evaluated (cached values are read)
and macros are never run. Problems raise TableError naming the file, row and
reason; no row is dropped silently.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FILE_TYPES = ("csv", "xlsx", "json")
SUFFIX_TYPES = {".csv": "csv", ".xlsx": "xlsx", ".xlsm": "xlsx", ".json": "json"}
FLATTEN_HINT = (
    "merged or multi-row headers are not supported; "
    "flatten first: nightdesk flatten <file> --header-rows 2"
)


class TableError(ValueError):
    """The file cannot be read as one table; the message says where and why."""


@dataclass
class Table:
    path: Path
    file_type: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_numbers: list[int]  # CSV/XLSX: 1-based row in the file; JSON: 0-based record index
    skipped_blank_rows: list[int] = field(default_factory=list)


def detect_type(path: Path, file_type: str | None = None) -> str:
    if file_type:
        if file_type not in FILE_TYPES:
            raise TableError(f"unknown file type {file_type!r}; use one of {', '.join(FILE_TYPES)}")
        return file_type
    try:
        return SUFFIX_TYPES[path.suffix.lower()]
    except KeyError:
        raise TableError(f"{path}: cannot tell the file type from {path.suffix!r}; pass --type") from None


def read_table(
    path: str | Path,
    file_type: str | None = None,
    *,
    encoding: str = "utf-8-sig",
    delimiter: str = ",",
    sheet: str | None = None,
    header_row: int = 1,
    records_path: str | None = None,
) -> Table:
    path = Path(path)
    kind = detect_type(path, file_type)
    if not path.is_file():
        raise TableError(f"{path}: file not found")
    if header_row < 1:
        raise TableError(f"header_row must be 1 or more, got {header_row}")
    if kind != "json" and records_path:
        raise TableError("records_path applies to JSON files only")
    if kind != "xlsx" and sheet:
        raise TableError("sheet applies to XLSX files only")
    if kind == "csv":
        return _read_csv(path, encoding, delimiter, header_row)
    if kind == "xlsx":
        return _read_xlsx(path, sheet, header_row)
    if header_row != 1:
        raise TableError("header_row does not apply to JSON files")
    return _read_json(path, encoding, records_path)


def _check_header(path: Path, header_row: int, names: list[str]) -> list[str]:
    names = [n.strip() for n in names]
    if not any(names):
        raise TableError(f"{path}: header row {header_row} is empty")
    blank = [i + 1 for i, n in enumerate(names) if not n]
    if blank:
        raise TableError(
            f"{path}: header row {header_row} has blank column names at positions "
            f"{blank}; {FLATTEN_HINT}"
        )
    seen: dict[str, int] = {}
    dupes = []
    for i, n in enumerate(names, start=1):
        if n in seen:
            dupes.append(f"{n!r} (positions {seen[n]} and {i})")
        seen.setdefault(n, i)
    if dupes:
        raise TableError(f"{path}: header row {header_row} has duplicate column names: {', '.join(dupes)}")
    return names


def _read_csv(path: Path, encoding: str, delimiter: str, header_row: int) -> Table:
    if len(delimiter) != 1:
        raise TableError(f"delimiter must be one character, got {delimiter!r}")
    try:
        with path.open(encoding=encoding, newline="") as fh:
            records = list(csv.reader(fh, delimiter=delimiter, strict=True))
    except UnicodeDecodeError as exc:
        raise TableError(f"{path}: not valid {encoding}: {exc}; pass --encoding") from exc
    except LookupError as exc:
        raise TableError(f"unknown encoding {encoding!r}") from exc
    except csv.Error as exc:
        raise TableError(f"{path}: malformed CSV: {exc}") from exc
    if len(records) < header_row:
        raise TableError(f"{path}: has {len(records)} rows, no header row {header_row}")
    columns = _check_header(path, header_row, records[header_row - 1])
    table = Table(path, "csv", columns, [], [])
    for number, cells in enumerate(records[header_row:], start=header_row + 1):
        if not any(c.strip() for c in cells):
            table.skipped_blank_rows.append(number)
            continue
        if len(cells) != len(columns):
            raise TableError(f"{path}: row {number} has {len(cells)} cells, header has {len(columns)}")
        table.rows.append(dict(zip(columns, cells)))
        table.row_numbers.append(number)
    return table


def _read_xlsx(path: Path, sheet: str | None, header_row: int) -> Table:
    from openpyxl import load_workbook

    try:
        # data_only: cached cell values, formulas are not evaluated; VBA is not loaded.
        wb = load_workbook(path, data_only=True, keep_vba=False, keep_links=False)
    except Exception as exc:  # openpyxl raises several unrelated types for bad files
        raise TableError(f"{path}: cannot open as XLSX: {exc}") from exc
    try:
        if sheet is None:
            ws = wb.worksheets[0]
        elif sheet in wb.sheetnames:
            ws = wb[sheet]
        else:
            raise TableError(f"{path}: no sheet {sheet!r}; sheets: {wb.sheetnames}")
        merged = [str(r) for r in ws.merged_cells.ranges if r.min_row <= header_row <= r.max_row]
        if merged:
            raise TableError(f"{path}: header row {header_row} has merged cells {merged}; {FLATTEN_HINT}")
        all_rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
    if len(all_rows) < header_row:
        raise TableError(f"{path}: sheet {ws.title!r} has {len(all_rows)} rows, no header row {header_row}")
    header = list(all_rows[header_row - 1])
    while header and header[-1] in (None, ""):
        header.pop()  # trailing empty cells are not columns
    columns = _check_header(path, header_row, ["" if h is None else str(h) for h in header])
    table = Table(path, "xlsx", columns, [], [])
    for number, cells in enumerate(all_rows[header_row:], start=header_row + 1):
        cells = list(cells)
        if all(c is None or (isinstance(c, str) and not c.strip()) for c in cells):
            table.skipped_blank_rows.append(number)
            continue
        beyond = [c for c in cells[len(columns):] if c not in (None, "")]
        if beyond:
            raise TableError(f"{path}: row {number} has values beyond the {len(columns)} header columns")
        cells += [None] * (len(columns) - len(cells))
        table.rows.append(dict(zip(columns, cells[: len(columns)])))
        table.row_numbers.append(number)
    return table


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise TableError(f"duplicate key {key!r} in a JSON object")
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise TableError(f"non-finite number {name} is not valid JSON")


def _reject_non_finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise TableError(f"number {text} is out of range")
    return value


def _read_json(path: Path, encoding: str, records_path: str | None) -> Table:
    try:
        data = json.loads(
            path.read_text(encoding=encoding),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
            parse_float=_reject_non_finite_float,
        )
    except TableError as exc:
        raise TableError(f"{path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise TableError(f"{path}: not valid {encoding}: {exc}; pass --encoding") from exc
    except LookupError as exc:
        raise TableError(f"unknown encoding {encoding!r}") from exc
    except json.JSONDecodeError as exc:
        raise TableError(f"{path}: malformed JSON: {exc}") from exc

    records = data
    if records_path:
        for part in records_path.split("."):
            if not isinstance(records, dict) or part not in records:
                raise TableError(f"{path}: records_path {records_path!r}: no key {part!r}")
            records = records[part]
    if isinstance(records, dict):
        lists = [k for k, v in records.items() if isinstance(v, list)]
        raise TableError(f"{path}: top level is an object; pass --records-path (list keys: {lists})")
    if not isinstance(records, list):
        raise TableError(f"{path}: records are a {type(records).__name__}, expected a list of objects")

    columns: list[str] = []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise TableError(f"{path}: record {i} is a {type(rec).__name__}, expected an object")
        columns += [k for k in rec if k not in columns]
    # Keep original keys: absence and explicit null are distinct source facts.
    return Table(path, "json", columns, records, list(range(len(records))))
