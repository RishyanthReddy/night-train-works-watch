import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from streamlit.testing.v1 import AppTest

from nightdesk.adapters import infrabel
from nightdesk.config import get_bundle
from nightdesk.intake.mapping import captures, confirm_mapping, ingest
from nightdesk.desk import run_options
from nightdesk.export import export_run_evidence
from nightdesk.runs import build_runs


def row(point, clock):
    return {
        "datdep": "2026-11-16", "train_no": "453", "train_serv": "EURSLEEPER",
        "ptcar_lg_nm_nl": point, "line_no_dep": "1", "line_no_arr": "1",
        "planned_date_arr": "2026-11-16", "planned_time_arr": clock,
        "planned_date_dep": "2026-11-16", "planned_time_dep": clock,
        "real_date_arr": "2026-11-16", "real_time_arr": clock,
        "real_date_dep": "2026-11-16", "real_time_dep": clock,
        "delay_arr": 0, "delay_dep": 0,
    }


def page(total, rows):
    return json.dumps({"total_count": total, "results": rows}).encode()


def test_paginated_capture_replays_through_confirmed_intake(tmp_path, monkeypatch):
    monkeypatch.setattr(infrabel, "PAGE_SIZE", 1)
    bundle = get_bundle("test-infrabel", tmp_path)
    responses = [page(2, [row("Point A", "18:00:00")]), page(2, [row("Point B", "18:05:00")])]
    queries = []

    def read(path):
        queries.append(parse_qs(urlsplit(path).query))
        return responses[len(queries) - 1]

    monkeypatch.setattr(infrabel, "_read_page", read)
    saved = infrabel.fetch_d1(bundle)
    assert [q["offset"] for q in queries] == [["0"], ["1"]]
    assert all(q["where"] == ['train_serv="EURSLEEPER"'] for q in queries)
    manifest = json.loads(Path(saved["manifest"]).read_text())
    assert manifest["complete"] is False and manifest["rows"] == 2
    for info, raw in zip(manifest["pages"], responses):
        assert (Path(saved["manifest"]).parent / info["file"]).read_bytes() == raw
        assert info["sha256"] == hashlib.sha256(raw).hexdigest()
    mapping = Path(__file__).resolve().parents[1] / "mappings/infrabel_d1.yaml"
    confirm_mapping(mapping, bundle, "Test data reviewer")
    result = ingest(saved["capture"], mapping, bundle)
    assert result["accepted"] == 2 and result["rejected"] == 0
    capture = captures(bundle)[0]
    assert not capture["capture"].complete
    run, = build_runs(capture["typed_rows"])
    assert run.train_no == "be:453" and run.kind == "observed"
    assert run.points[0].point_id == "be-infrabel-d1:Point%20A"
    assert run.points[0].real_dep.isoformat() == "2026-11-16T18:00:00+01:00"
    assert run.points[1].extra["d1_fetched_at"] == manifest["pages"][1]["fetched_at"]
    assert run.points[1].extra["d1_source_url"] == manifest["pages"][1]["url"]
    selection, = run_options(bundle, [result["capture_id"]])
    md, json_path = export_run_evidence(bundle, result["capture_id"], selection)
    evidence = json.loads(json_path.read_text())
    assert "Source run evidence" in md.read_text()
    assert evidence["capture"]["complete"] is False
    assert evidence["run"]["points"][0]["real_dep"] == "2026-11-16T18:00:00+01:00"
    assert evidence["run"]["points"][0]["source"]["capture_id"] == result["capture_id"]


def test_changed_pagination_publishes_no_capture(tmp_path, monkeypatch):
    monkeypatch.setattr(infrabel, "PAGE_SIZE", 1)
    pages = iter([page(2, [row("A", "18:00:00")]), page(1, [])])
    monkeypatch.setattr(infrabel, "_read_page", lambda _: next(pages))
    bundle = get_bundle("test-infrabel", tmp_path)
    with pytest.raises(ValueError, match="infrabel_page_count_changed"):
        infrabel.fetch_d1(bundle)
    assert not (bundle.root / "infrabel").exists()


def test_source_train_labels_render_as_plain_text(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NIGHTDESK_BUNDLE", "test-source-label")
    bundle = get_bundle("test-source-label")
    label = "![sample](//example.invalid/synthetic)"
    source_row = {**row("Point A", "18:00:00"), "train_no": label}
    monkeypatch.setattr(infrabel, "_read_page", lambda _: page(1, [source_row]))
    staged = infrabel.fetch_d1(bundle)
    mapping = repo / "mappings/infrabel_d1.yaml"
    confirm_mapping(mapping, bundle, "Test reviewer")
    capture = ingest(staged["capture"], mapping, bundle)["capture_id"]
    app = AppTest.from_file(repo / "src/nightdesk/ui/app.py", default_timeout=30).run()
    app.selectbox(key="test-source-label:runs").set_value(capture)
    app.session_state["test-source-label:active_tab"] = "Run evidence"
    app.run()
    selection, = run_options(bundle, [capture])
    app.selectbox(key=f"test-source-label:source_run:{capture}").set_value(selection).run()
    assert not app.exception
    assert any(label in element.value for element in app.tabs[3].text)
    assert not any(label in element.value for element in app.tabs[3].caption)
