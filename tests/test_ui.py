"""AppTest supplements the required viewed browser checks; it does not replace them."""

import csv
from pathlib import Path
import shutil

import pytest
from streamlit.testing.v1 import AppTest

from nightdesk.config import get_bundle
from nightdesk.intake.mapping import confirm_mapping, ingest
from nightdesk.review import decisions, follow_ups

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "src/nightdesk/ui/app.py"


@pytest.mark.parametrize("train", ["aa:101", "aa:[APPROVED](#approved)"])
def test_queue_open_dossier_record_local_review_and_question(tmp_path, monkeypatch, train):
    shutil.copytree(REPO / "mappings", tmp_path / "mappings")
    shutil.copytree(REPO / "tests/fixtures/paths", tmp_path / "paths")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NIGHTDESK_BUNDLE", "test-ui")
    bundle = get_bundle("test-ui")
    confirm_mapping("mappings/synthetic_path_legs.yaml", bundle)
    with Path("paths/legs.csv").open() as f:
        reader = csv.DictReader(f);header = reader.fieldnames;rows = list(reader)
    rows[0]["train_no"] = train
    with Path("paths/legs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header);writer.writeheader();writer.writerows(rows)
    old = ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", bundle)
    rows[0]["exit_time"] = "2026-11-17 23:01"
    with Path("paths/legs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header);writer.writeheader();writer.writerows(rows)
    new = ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", bundle)
    app = AppTest.from_file(APP).run(timeout=20)
    assert not app.exception
    app.selectbox(key="test-ui:before").set_value(old["capture_id"]).run()
    app.selectbox(key="test-ui:after").set_value(new["capture_id"]).run()
    options = app.selectbox(key="test-ui:selected").options
    assert f"{train} / 2026-11-17" in options
    app.selectbox(key="test-ui:selected").select_index(0).run()
    assert not app.exception
    assert any(f"{train} / 2026-11-17" in t.value for t in app.text)
    assert any(f"<h2>Train {train}</h2>" == element.value for element in app.get("html"))
    def by_label(elements, label):
        return next(e for e in elements if e.label == label)
    by_label(app.text_area, "Why").set_value("Synthetic question about this revision")
    by_label(app.text_input, "Who should answer (optional)").set_value("Person A")
    by_label(app.text_area, "What needs answering (optional)").set_value("Please confirm the boundary point")
    by_label(app.button, "Record this decision").click().run()
    assert not app.exception
    assert len(decisions(bundle)) == 1 and decisions(bundle)[0].disposition == "needs_clarification"
    assert follow_ups(bundle)[0].owner == "Person A" and follow_ups(bundle)[0].deadline is None
    by_label(app.button, "Export this change").click().run()
    assert not app.exception and len(list((bundle.root / "exports").glob("*.json"))) == 1
    assert not any("DeltaGenerator" in str(e.value) for e in app.markdown)
    clock_panels = [str(element.value) for element in app.get("html")]
    assert any("23:00" in panel and "23:01" in panel and "UTC+01:00" in panel
               for panel in clock_panels)
    assert any("Follow-up · Person A" in element.value for element in app.text)
    assert any("all 2 dates this train runs" in item.value for item in app.warning)
    assert any("Which date that time belongs to cannot be checked" in item.value for item in app.warning)

    app.selectbox(key="test-ui:before").set_value(new["capture_id"])
    app.selectbox(key="test-ui:after").set_value(old["capture_id"]).run()
    assert any("was recorded before the one marked Earlier" in item.value for item in app.warning)

    app.selectbox(key="test-ui:before").set_value(old["capture_id"]).run()
    assert not app.exception
    assert any("Nothing changed between these two files" in item.value for item in app.info)
    assert not any(f"<h2>Train {train}</h2>" == element.value for element in app.get("html"))

