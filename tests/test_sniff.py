"""Synthetic files generated in tmp_path; no committed fixtures."""

import datetime as dt
import json
import subprocess
import sys

import pytest
from openpyxl import Workbook

from nightdesk.cli import main
from nightdesk.intake.sniff import profile, value_type
from nightdesk.intake.table import TableError, read_table


def write(path, text, encoding="utf-8"):
    path.write_text(text, encoding=encoding)
    return path


def cols(prof):
    return {c["name"]: c for c in prof["columns"]}


@pytest.fixture
def csv_file(tmp_path):
    rows = ["record_id,status,duration_s,ratio,notes"]
    rows += [f"R{i},open,{i * 10},{i}.5,synthetic" for i in range(1, 8)]
    rows += ["R8,,80,,synthetic", "R9,closed,90,9.5,"]
    return write(tmp_path / "t.csv", "\n".join(rows) + "\n")


def test_csv_profile(csv_file):
    p = profile(read_table(csv_file))
    assert p["row_count"] == 9 and p["file_type"] == "csv"
    c = cols(p)
    assert list(c) == ["record_id", "status", "duration_s", "ratio", "notes"]
    assert c["record_id"]["type"] == "string"
    assert c["record_id"]["samples"] == ["R1", "R2", "R3", "R4", "R5"]
    assert c["duration_s"]["type"] == "int" and c["duration_s"]["null_count"] == 0
    assert c["ratio"]["type"] == "float"
    assert c["status"]["null_count"] == 1 and c["status"]["null_rate"] == round(1 / 9, 4)
    assert c["status"]["samples"] == ["open", "closed"]  # distinct, nulls excluded


def test_csv_values_kept_as_text(csv_file):
    t = read_table(csv_file)
    assert t.rows[0]["duration_s"] == "10"  # sniff infers; reading never converts
    assert t.row_numbers[0] == 2


def test_csv_delimiter_encoding_header_row(tmp_path):
    f = tmp_path / "t.csv"
    f.write_bytes("preamble line\nnaam;plaats\nA;Liège\n".encode("latin-1"))
    with pytest.raises(TableError, match="not valid utf-8"):
        read_table(f, delimiter=";", header_row=2)
    t = read_table(f, delimiter=";", header_row=2, encoding="latin-1")
    assert t.columns == ["naam", "plaats"] and t.rows == [{"naam": "A", "plaats": "Liège"}]
    assert t.row_numbers == [3]


def test_csv_bom_stripped(tmp_path):
    f = tmp_path / "t.csv"
    f.write_bytes(b"\xef\xbb\xbfid,v\n1,2\n")
    assert read_table(f).columns == ["id", "v"]


def test_csv_blank_rows_reported_not_hidden(tmp_path):
    f = write(tmp_path / "t.csv", "id,v\n1,a\n\n,\n2,b\n")
    t = read_table(f)
    assert [r["id"] for r in t.rows] == ["1", "2"]
    assert t.skipped_blank_rows == [3, 4]
    assert profile(t)["skipped_blank_rows"] == [3, 4]


@pytest.mark.parametrize("text, match", [
    ("id,id\n1,2\n", "duplicate column names: 'id'"),
    ("group,,\nid,a,b\n", "blank column names.*flatten"),
    ("id,v\n1,2,3\n", "row 2 has 3 cells, header has 2"),
    ("id,v\n1\n", "row 2 has 1 cells"),
    ('id,v\n1,"unterminated\n', "malformed CSV"),
    ("", "no header row 1"),
    (",\n1,2\n", "header row 1 is empty"),
])
def test_csv_errors(tmp_path, text, match):
    with pytest.raises(TableError, match=match):
        read_table(write(tmp_path / "t.csv", text))


def make_xlsx(path, rows, merge=None, sheet="Data", extra_sheet=False):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for r in rows:
        ws.append(r)
    if merge:
        ws.merge_cells(merge)
    if extra_sheet:
        wb.create_sheet("Second").append(["x"])
    wb.save(path)
    return path


def test_xlsx_profile_native_types(tmp_path):
    f = make_xlsx(tmp_path / "t.xlsx", [
        ["id", "n", "when", "flag", "formula"],
        ["A", 1, dt.datetime(2026, 11, 17, 22, 5), True, "=1+1"],
        ["B", 2.5, dt.datetime(2026, 11, 18, 1, 0), False, None],
        [None, None, None, None, None],
        ["C", None, None, None, None],
    ])
    t = read_table(f)
    assert t.skipped_blank_rows == [4] and t.row_numbers == [2, 3, 5]
    # Formula never evaluated: no cached value was saved, so it reads as None.
    assert t.rows[0]["formula"] is None
    c = cols(profile(t))
    assert c["n"]["type"] == "float" and c["n"]["type_counts"] == {"float": 1, "int": 1}
    assert c["when"]["type"] == "datetime" and c["when"]["samples"][0] == "2026-11-17T22:05:00"
    assert c["flag"]["type"] == "bool"
    assert c["n"]["null_rate"] == round(1 / 3, 4)


def test_xlsx_sheet_and_header_row(tmp_path):
    f = make_xlsx(tmp_path / "t.xlsx", [["title"], ["id", "v"], ["A", 1]], extra_sheet=True)
    assert read_table(f, header_row=2).columns == ["id", "v"]
    assert read_table(f, sheet="Second").columns == ["x"]
    with pytest.raises(TableError, match="no sheet 'Nope'.*Second"):
        read_table(f, sheet="Nope")


def test_xlsx_merged_header_refused(tmp_path):
    f = make_xlsx(tmp_path / "t.xlsx", [["Period", None, "id"], ["from", "to", None], [1, 2, "A"]], merge="A1:B1")
    with pytest.raises(TableError, match="merged cells.*A1:B1.*flatten"):
        read_table(f)


def test_xlsx_errors(tmp_path):
    with pytest.raises(TableError, match="duplicate"):
        read_table(make_xlsx(tmp_path / "d.xlsx", [["id", "id"], [1, 2]]))
    with pytest.raises(TableError, match="beyond the 1 header columns"):
        read_table(make_xlsx(tmp_path / "w.xlsx", [["id"], [1, "stray"]]))
    bad = write(tmp_path / "bad.xlsx", "not a zip")
    with pytest.raises(TableError, match="cannot open as XLSX"):
        read_table(bad)


def test_json_records_path_and_nesting(tmp_path):
    data = {"meta": {"source": "synthetic"}, "data": {"items": [
        {"id": "W1", "period": {"from": "2026-11-17", "to": "2026-11-20"}, "tags": ["a", "b"], "km": 1.5},
        {"id": "W2", "period": {"from": "2026-11-18", "to": None}, "extra_key": "only here"},
    ]}}
    f = write(tmp_path / "t.json", json.dumps(data))
    t = read_table(f, records_path="data.items")
    assert t.columns == ["id", "period", "tags", "km", "extra_key"]
    assert t.rows[0]["period"] == {"from": "2026-11-17", "to": "2026-11-20"}  # structure kept
    assert "tags" not in t.rows[1] and t.row_numbers == [0, 1]
    c = cols(profile(t))
    assert c["period"]["type"] == "object" and c["tags"]["type"] == "array"
    assert c["extra_key"]["null_rate"] == 0.5
    assert c["period"]["samples"][0] == {"from": "2026-11-17", "to": "2026-11-20"}


@pytest.mark.parametrize("text, kw, match", [
    ('{"items": []}', {}, "top level is an object.*items"),
    ('{"items": []}', {"records_path": "rows"}, "no key 'rows'"),
    ('[1, 2]', {}, "record 0 is a int"),
    ('{"a": 1, "a": 2}', {}, "duplicate key 'a'"),
    ('[{"x": NaN}]', {}, "non-finite"),
    ('[{"x": 1e999}]', {}, "out of range"),
    ('[{"x": 1}', {}, "malformed JSON"),
    ('"text"', {}, "expected a list of objects"),
])
def test_json_errors(tmp_path, text, kw, match):
    with pytest.raises(TableError, match=match):
        read_table(write(tmp_path / "t.json", text), **kw)


def test_option_and_type_errors(tmp_path):
    with pytest.raises(TableError, match="pass --type"):
        read_table(write(tmp_path / "t.txt", "a\n"))
    assert read_table(tmp_path / "t.txt", "csv").columns == ["a"]
    with pytest.raises(TableError, match="file not found"):
        read_table(tmp_path / "missing.csv")
    with pytest.raises(TableError, match="records_path applies to JSON"):
        read_table(tmp_path / "t.txt", "csv", records_path="x")
    with pytest.raises(TableError, match="one character"):
        read_table(tmp_path / "t.txt", "csv", delimiter=";;")


@pytest.mark.parametrize("value, kind", [
    ("12", "int"), ("-3", "int"), ("1.5", "float"), ("1e3", "float"), ("TRUE", "bool"),
    ("2026-11-17", "date"), ("2026-11-17T22:05:00+01:00", "datetime"), ("22:05", "time"),
    ("abc", "string"), ("1,5", "string"), ({"a": 1}, "object"), ([1], "array"),
])
def test_value_type(value, kind):
    assert value_type(value) == kind


def test_cli_sniff_text_and_json(csv_file, capsys):
    assert main(["sniff", str(csv_file)]) == 0
    out = capsys.readouterr().out
    assert "9 rows, 5 columns" in out and "- duration_s: int, null 0.0% (0)" in out
    assert main(["sniff", str(csv_file), "--json"]) == 0
    prof = json.loads(capsys.readouterr().out)
    assert cols(prof)["status"]["null_count"] == 1


def test_cli_sniff_error_exit(tmp_path, capsys):
    f = write(tmp_path / "t.csv", "id,id\n1,2\n")
    assert main(["sniff", str(f)]) == 1
    assert "duplicate column names" in capsys.readouterr().err


def test_cli_sniff_json_records_path(tmp_path, capsys):
    f = write(tmp_path / "t.json", '{"r": {"items": [{"id": 1, "n": {"a": [1]}}]}}')
    assert main(["sniff", str(f), "--records-path", "r.items", "--json"]) == 0
    prof = json.loads(capsys.readouterr().out)
    assert cols(prof)["n"]["samples"] == [{"a": [1]}]


def test_installed_entry_point(csv_file):
    """The real console script, as a separate process."""
    exe = __import__("shutil").which("nightdesk") or str(
        __import__("pathlib").Path(sys.executable).with_name("nightdesk"))
    done = subprocess.run([exe, "sniff", str(csv_file)], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert "record_id: string" in done.stdout
    bad = subprocess.run([exe, "sniff", str(csv_file), "--sheet", "x"], capture_output=True, text=True, check=False)
    assert bad.returncode == 1 and "sheet applies to XLSX" in bad.stderr
