"""Explicitly join header rows into a new local CSV; never execute macros."""

import csv
import io
from pathlib import Path
from nightdesk.config import Bundle, get_bundle, selected_bundle_name

from nightdesk.intake.mapping import write_private, check_input
from nightdesk.intake.table import TableError, _check_header, detect_type


def flatten(path: str | Path, header_rows: int, *, sheet=None, delimiter=",", encoding="utf-8-sig") -> str:
    path = Path(path)
    if header_rows < 1:
        raise TableError("header_rows must be at least 1")
    kind = detect_type(path)
    if kind == "csv":
        if len(delimiter) != 1:
            raise TableError("delimiter must be one character")
        with path.open(encoding=encoding, newline="") as fh:
            rows = list(csv.reader(fh, delimiter=delimiter, strict=True))
    elif kind == "xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(path, data_only=True, keep_vba=False, keep_links=False)
        try:
            if sheet and sheet not in wb.sheetnames:
                raise TableError(f"sheet {sheet!r} not found")
            ws = wb[sheet] if sheet else wb.worksheets[0]
            # Expand only explicitly merged cells, never guess a blank header's parent.
            for merged in list(ws.merged_cells.ranges):
                if merged.min_row <= header_rows < merged.max_row:
                    raise TableError("merged header extends into data; choose all header rows")
                if merged.min_row > header_rows:
                    raise TableError("merged data cells need a source-specific adapter")
                value = ws.cell(merged.min_row, merged.min_col).value
                ws.unmerge_cells(str(merged))
                for cells in ws.iter_rows(min_row=merged.min_row, max_row=merged.max_row,
                                          min_col=merged.min_col, max_col=merged.max_col):
                    for cell in cells:
                        cell.value = value
            rows = list(ws.iter_rows(values_only=True))
        finally:
            wb.close()
    else:
        raise TableError("flatten supports CSV/XLSX headers; JSON has no header rows")
    if len(rows) < header_rows:
        raise TableError("file has fewer rows than header_rows")
    width = max(map(len, rows), default=0)
    headers = []
    for col in range(width):
        parts = []
        for row in rows[:header_rows]:
            value = row[col] if col < len(row) else None
            part = str(value).strip() if value is not None else ""
            if part and part not in parts:
                parts.append(part)
        headers.append("_".join(parts))
    _check_header(path, 1, headers)
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(headers)
    for number, row in enumerate(rows[header_rows:], start=header_rows + 1):
        if len(row) > width or (kind == "csv" and len(row) != width and any(row)):
            raise TableError(f"row {number} has an inconsistent cell count")
        writer.writerow(row)
    return out.getvalue()


def write_flat(path: str | Path, output: str | Path, *, bundle: Bundle | None = None, **options):
    bundle = bundle or get_bundle(selected_bundle_name())
    check_input(path, bundle)
    check_input(output, bundle)
    if Path(path).resolve() == Path(output).resolve():
        raise TableError("flatten output must be a new file")
    text = flatten(path, **options)
    write_private(Path(output), text)
