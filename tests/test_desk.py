import csv
import shutil
from datetime import date
from pathlib import Path

import pytest

from nightdesk.config import get_bundle
from nightdesk.desk import dossier, queue, snapshot
from nightdesk.intake.mapping import captures, confirm_mapping, ingest
from nightdesk.links import import_links

REPO = Path(__file__).resolve().parents[1]


def test_explicit_capture_selection_produces_train_date_queue_then_dossier(tmp_path, monkeypatch):
    shutil.copytree(REPO / "mappings", tmp_path / "mappings")
    shutil.copytree(REPO / "tests/fixtures/paths", tmp_path / "paths")
    monkeypatch.chdir(tmp_path)
    bundle = get_bundle("practice")
    confirm_mapping("mappings/synthetic_path_legs.yaml", bundle)
    old = ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", bundle)
    assert queue(bundle, old["capture_id"], old["capture_id"]) == []
    with Path("paths/legs.csv").open() as f:
        reader = csv.DictReader(f);header = reader.fieldnames;rows = list(reader)
    rows[0]["exit_time"] = "2026-11-17 23:01"
    with Path("paths/legs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header);writer.writeheader();writer.writerows(rows)
    new = ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", bundle)
    changed = queue(bundle, old["capture_id"], new["capture_id"])
    assert len(changed) == 2 and changed[0]["train_no"] == "aa:101"
    assert "exit.at" in changed[0]["changed_fields"] and changed[0]["next_owner"] == "unassigned"
    args = (bundle, old["capture_id"], new["capture_id"], changed[0]["new_revision"], date(2026, 11, 17))
    report = dossier(*args)
    assert report["findings"][0]["reason"] == "unlinked"
    confirm_mapping("mappings/synthetic_links.yaml", bundle)
    crosswalk = ingest("paths/crosswalk.csv", "mappings/synthetic_links.yaml", bundle)
    link = import_links(bundle, crosswalk["capture_id"])[0]
    report = dossier(*args, link_identifier=link, reviewed_points={"syn:border"})
    assert report["findings"][0]["result"] == "unknown"
    assert report["findings"][0]["reason"] == "boundary_service_date_binding_unknown"
    assert report["capture_comparison"]["status"] == "compared"
    with pytest.raises((ValueError, OSError)):
        snapshot(get_bundle("es"), new["capture_id"])
