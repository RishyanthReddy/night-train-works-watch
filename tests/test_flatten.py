import csv
import io

import pytest
from openpyxl import Workbook

from nightdesk.cli import main
from nightdesk.intake.flatten import flatten
from nightdesk.intake.table import TableError, read_table


def test_merged_xlsx_refuses_then_flattens(tmp_path, capsys):
    path = tmp_path / "synthetic.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Identity", "Duration", None])
    ws.merge_cells("B1:C1")
    ws.append(["record_id", "planned_s", "actual_s"])
    ws.append(["syn-a", 30, 40])
    wb.save(path)
    before = path.read_bytes()
    with pytest.raises(TableError, match="flatten"):
        read_table(path)
    dest = tmp_path / "flat.csv"
    assert main(["flatten", str(path), "--header-rows", "2", "--out", str(dest)]) == 0
    table = read_table(dest)
    assert table.columns == ["Identity_record_id", "Duration_planned_s", "Duration_actual_s"]
    assert table.rows[0]["Duration_actual_s"] == "40"
    assert path.read_bytes() == before
    assert main(["flatten", str(path), "--header-rows", "2", "--out", str(dest)]) == 1


def test_flat_csv_stdout_and_original_preserved(tmp_path, capsys):
    path = tmp_path / "synthetic.csv"
    path.write_text("Identity,Duration\nrecord_id,seconds\na,30\n")
    assert main(["flatten", str(path), "--header-rows", "2"]) == 0
    assert list(csv.reader(io.StringIO(capsys.readouterr().out))) == [
        ["Identity_record_id", "Duration_seconds"], ["a", "30"]]


def test_flatten_refuses_bad_headers_and_counts(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("A,A\nid,id\na,b\n")
    with pytest.raises(TableError, match="duplicate"):
        flatten(path, 2)
    with pytest.raises(TableError):
        flatten(path, 0)
    with pytest.raises(TableError):
        flatten(path, 10)
