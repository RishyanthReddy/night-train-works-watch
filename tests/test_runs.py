import csv
import hashlib
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from nightdesk.config import get_bundle
from nightdesk.intake.mapping import captures, confirm_mapping, ingest
from nightdesk.model import RunPoint, RunRow, SourceRef, TrainRun
from nightdesk.runs import build_runs, line_for_matching, segments

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(REPO / "tests/fixtures/runs", tmp_path / "runs")
    (tmp_path / "mappings").mkdir()
    shutil.copy2(REPO / "mappings/infrabel_punctuality.yaml", tmp_path / "mappings/infrabel.yaml")
    monkeypatch.chdir(tmp_path)
    b = get_bundle("practice")
    confirm_mapping("mappings/infrabel.yaml", b)
    return b


def test_three_complete_cc0_groups_with_old_and_new_headers(workspace):
    manifest = json.loads(Path("runs/manifest.json").read_text())
    assert [m["rows"] for m in manifest] == [27, 42, 69]
    for item in manifest:
        path = Path("runs") / item["fixture"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["fixture_sha256"]
        result = ingest(path, "mappings/infrabel.yaml", workspace)
        assert result["accepted"] == item["rows"] and result["rejected"] == 0
    all_runs = [r for c in captures(workspace) for r in build_runs(c["typed_rows"])]
    assert len(all_runs) == 3 and sum(len(r.points) for r in all_runs) == 138
    assert {r.train_no for r in all_runs} == {"be:453", "be:400", "be:475"}
    for run in all_runs:
        times = [p.planned_dep or p.planned_arr for p in run.points if p.planned_dep or p.planned_arr]
        assert times == sorted(times)
        assert len(run.input_refs) == len(run.points)
        assert "assumed Europe/Brussels" in run.extra["assumptions"][0]
    overnight = next(r for r in all_runs if r.train_no == "be:475")
    assert {p.planned_dep.date() for p in overnight.points if p.planned_dep} == {date(2026, 3, 26), date(2026, 3, 27)}
    run = next(r for r in all_runs if r.train_no == "be:400")
    first = next(p for p in run.points if p.point_id == "be-ptcar:825")
    assert first.delay_arr_s == 3280  # raw seconds, not minutes
    assert first.planned_arr.hour == 9 and first.planned_arr.minute == 5
    assert all(s.line is None or not s.line.split(":")[1].startswith("0/") for r in all_runs for s in segments(r))


def point(name, at=None, *, line_dep=None, line_arr=None):
    return RunPoint(point_id="syn:" + name, planned_dep=at, planned_arr=at, line_dep=line_dep, line_arr=line_arr)


def run(points):
    return TrainRun(service_date="2026-11-17", train_no="syn:1", kind="observed", points=points)


def test_d1_departure_at_a_then_arrival_at_b_no_wrong_endpoint_fallback():
    a = point("a", datetime(2026, 11, 17, 23, 55, tzinfo=timezone.utc), line_dep="syn:37", line_arr="syn:wrong-a")
    b = point("b", datetime(2026, 11, 18, 0, 5, tzinfo=timezone.utc), line_dep="syn:wrong-b", line_arr="syn:36")
    s = segments(run([a, b]))[0]
    assert s.line == "syn:37" and s.planned_s == 600
    assert segments(run([a.model_copy(update={"line_dep": None}), b]))[0].line == "syn:36"
    assert segments(run([a.model_copy(update={"line_dep": "syn:0/1"}), b]))[0].line == "syn:36"
    assert segments(run([a.model_copy(update={"line_dep": None}), b.model_copy(update={"line_arr": None})]))[0].line is None


def test_reversed_or_missing_pass_has_no_duration_and_scheduled_does_not_invent_line():
    a = point("a", datetime(2026, 11, 17, 12, tzinfo=timezone.utc))
    b = point("b", datetime(2026, 11, 17, 11, tzinfo=timezone.utc))
    assert segments(run([a, b]))[0].planned_s is None
    assert segments(run([a, point("missing")]))[0].planned_s is None
    scheduled = run([a, b]).model_copy(update={"kind": "scheduled", "path_unresolved": True})
    assert segments(scheduled)[0].line is None


def test_header_reordering_is_not_positional(workspace):
    path = Path("runs/cc0_2023.csv")
    with path.open() as f:
        reader = csv.DictReader(f);columns = reader.fieldnames;rows = list(reader)
    with Path("runs/reordered.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(reversed(columns)))
        writer.writeheader();writer.writerows(rows)
    ingest(path, "mappings/infrabel.yaml", workspace)
    ingest("runs/reordered.csv", "mappings/infrabel.yaml", workspace)
    pair = [c["typed_rows"] for c in captures(workspace)]
    assert [[r.model_dump(exclude={"source"}) for r in group] for group in pair][0] == [r.model_dump(exclude={"source"}) for r in pair[1]]


def test_missing_order_times_and_capture_scopes_never_merge():
    def row(capture, name, at):
        src = SourceRef(bundle="practice", dataset="synthetic", record_id=name, capture_id=capture,
                        content_sha256="a" * 64, captured_at=datetime.now(timezone.utc), url_or_path="synthetic", licence="synthetic")
        return RunRow(point_id="syn:" + name, planned_dep=at, source=src, service_date="2026-11-17", train_no="syn:1")
    a = row("a", "a", datetime(2026, 11, 17, 23, tzinfo=timezone.utc))
    b = row("a", "b", None)
    c = row("b", "c", a.planned_dep)
    observed = build_runs([b, a, c])
    assert len(observed) == 2
    first = next(r for r in observed if len(r.points) == 2)
    assert first.points[0].point_id == "syn:a" and first.unresolved["point_order"]["reason"] == "missing_planned_time"
    assert first.path_unresolved
