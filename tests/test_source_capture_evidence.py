import hashlib
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from nightdesk.adapters.strecken_info import stage_works, WORKS_URL
from nightdesk.audit import read_events
from nightdesk.config import get_bundle
from nightdesk.desk import works_evidence
from nightdesk.export import export_works_evidence
from nightdesk.intake.mapping import confirm_mapping, ingest


REPO = Path(__file__).resolve().parents[1]


def saved_works(folder, when, start, end, identifier):
    folder.mkdir()
    row = {"baustellenID": identifier, "wirkung": "TOTALSPERRUNG", "arbeiten": "Synthetic",
           "langnameVon": "Point A", "langnameBis": "Point B", "ril100Von": "AA", "ril100Bis": "BB",
           "streckennummern": ["1"], "zeitraum": {"beginn": start + "T01:00:00", "ende": end + "T02:00:00"},
           "gueltigkeiten": [{"vonDatum": start, "bisDatum": end, "vonUhrzeit": "01:00:00", "bisUhrzeit": "02:00:00"}]}
    body = json.dumps([row]).encode()
    (folder / "baustellen.json").write_bytes(body)
    manifest = {"source": "strecken-info.de", "complete": False,
                "filter": {"zeitraum": {"type": "ROLLIEREND", "stunden": 2016}},
                "files": [{"url": WORKS_URL, "file": "baustellen.json", "fetched_at": when,
                           "status": 200, "bytes": len(body), "records": 1, "sha256": hashlib.sha256(body).hexdigest()}]}
    path = folder / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_saved_works_through_comparison_export_and_app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NIGHTDESK_BUNDLE", "test-works-evidence")
    bundle = get_bundle("test-works-evidence")
    mapping = REPO / "mappings/strecken_info_works.yaml"
    confirm_mapping(mapping, bundle, "Test reviewer")
    old = saved_works(tmp_path / "old", "2026-11-17T11:00:00Z", "2026-11-17", "2026-11-18", "synthetic-old")
    newer = saved_works(tmp_path / "new", "2026-11-18T05:00:00Z", "2027-02-10", "2027-02-11", "synthetic-new")
    ids = [ingest(stage_works(bundle, manifest)["capture"], mapping, bundle)["capture_id"]
           for manifest in (old, newer)]
    report = works_evidence(bundle, ids[1], ids[0])
    assert report["capture"]["captured_at"] == "2026-11-18T05:00:00Z"
    assert report["capture"]["imported_at"] >= report["capture"]["captured_at"]
    assert report["capture_origin"]["evidence"]["licence"] == "UNKNOWN"
    changes = report["comparison"]
    assert changes["added"] == changes["removed"] == []
    assert changes["reason"] == "incomplete_capture"
    assert {item["classification"] for item in changes["membership_changes"]} == {"expired_out_of_window", "entering_window"}
    md, data = export_works_evidence(bundle, ids[1], ids[0])
    assert json.loads(data.read_text()) == report
    assert "expired\\_out\\_of\\_window" in md.read_text()
    assert "capture_membership_checked" in [event.kind for event in read_events(bundle)]
    app = AppTest.from_file(REPO / "src/nightdesk/ui/app.py", default_timeout=30).run()
    app.selectbox(key="test-works-evidence:works").set_value(ids[1])
    app.session_state["test-works-evidence:active_tab"] = "Works evidence"
    app.run()
    assert not app.exception
    app.selectbox(key=f"test-works-evidence:works_before:{ids[1]}").set_value(ids[0]).run()
    assert any("incomplete_capture" in element.value for element in app.info)
    assert not app.exception
    assert any(set(table.value["Finding"]) == {"Left the rolling window after expiry", "Entered the rolling window"}
               for table in app.dataframe if "Finding" in table.value.columns)
    app.text_input(key="test-works-evidence:work_search").set_value("synthetic-new").run()
    app.session_state["test-works-evidence:active_tab"] = "Queue"
    app.run()
    app.session_state["test-works-evidence:active_tab"] = "Works evidence"
    app.run()
    assert app.selectbox(key=f"test-works-evidence:works_before:{ids[1]}").value == ids[0]
    assert app.text_input(key="test-works-evidence:work_search").value == "synthetic-new"


def test_german_saved_source_hash_is_required(tmp_path):
    bundle = get_bundle("test-works-evidence", tmp_path / "out")
    manifest = saved_works(tmp_path / "saved", "2026-11-17T11:00:00Z", "2026-11-17", "2026-11-18", "synthetic")
    manifest.with_name("baustellen.json").write_text("[]")
    with pytest.raises(ValueError, match="works_hash_or_length_mismatch"):
        stage_works(bundle, manifest)
    assert not bundle.root.exists()


def test_future_capture_and_bad_envelope_refused(tmp_path):
    bundle = get_bundle("test-works-evidence", tmp_path / "out")
    mapping = REPO / "mappings/strecken_info_works.yaml"
    confirm_mapping(mapping, bundle, "Test reviewer")
    future = saved_works(tmp_path / "future", "2099-01-01T00:00:00Z", "2027-02-10", "2027-02-11", "synthetic")
    path = Path(stage_works(bundle, future)["capture"])
    with pytest.raises(ValueError, match="capture_time_after_import"):
        ingest(path, mapping, bundle)
    for origin in (None, {"captured_at": -20, "evidence": {}}, {"captured_at": "2026-11-17T11:00:00", "evidence": {}}):
        input_path = tmp_path / "malformed.json"
        input_path.write_text(json.dumps({"_capture": origin, "results": []}))
        with pytest.raises(ValueError, match="^capture_origin_invalid$"):
            ingest(input_path, mapping, bundle)
    assert not (bundle.root / "captures").exists()
