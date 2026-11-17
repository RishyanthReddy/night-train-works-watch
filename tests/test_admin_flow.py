"""Real synthetic fixtures, alternate mapping and mapped export end to end."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from nightdesk.audit import read_events
from nightdesk.cli import main
from nightdesk.config import get_bundle
from nightdesk.generic import compare_files, source_table
from nightdesk.intake.mapping import captures, confirm_mapping, ingest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(REPO / "tests/fixtures/admin", tmp_path / "tests/fixtures/admin")
    shutil.copytree(REPO / "mappings", tmp_path / "mappings")
    monkeypatch.chdir(tmp_path)
    return get_bundle("practice")


def test_admin_full_flow_and_alternate_mapping(workspace, capsys):
    bundle = workspace
    a, b, alt = [f"tests/fixtures/admin/admin_{suffix}.csv" for suffix in ("v1", "v2", "alt")]
    assert main(["sniff", a]) == 0
    assert main(["ingest", a, "--mapping", "mappings/admin_v1.yaml"]) == 1
    assert main(["mapping", "confirm", "mappings/admin_v1.yaml"]) == 0
    assert main(["ingest", a, "--mapping", "mappings/admin_v1.yaml"]) == 0
    assert main(["ingest", b, "--mapping", "mappings/admin_v1.yaml"]) == 0
    assert main(["rejects"]) == 0
    assert "field=duration_s reason=invalid_number" in capsys.readouterr().out
    assert main(["compare", a, b, "--key", "record_id", "--out", str(bundle.root)]) == 0
    out = capsys.readouterr().out
    assert "changed=2 added=1 unchanged=2 only_in_old=0" in out
    report = json.loads(next(bundle.root.glob("comparison-*.json")).read_text())
    assert report["data_label"] == "synthetic"
    assert len(report["inputs"]["new"]["rejects"]) == 1
    assert report["inputs"]["new"]["mode"] == "confirmed_mapping"
    assert main(["mapping", "confirm", "mappings/admin_alt.yaml"]) == 0
    assert main(["ingest", alt, "--mapping", "mappings/admin_alt.yaml"]) == 0
    rows_a = source_table(a, bundle)["rows"]
    rows_alt = source_table(alt, bundle)["rows"]
    assert [(r.fields, r.extra, r.unresolved) for r in rows_a] == [(r.fields, r.extra, r.unresolved) for r in rows_alt]
    assert rows_a[0].source != rows_alt[0].source
    assert all(e.bundle == "practice" for e in read_events(bundle))
    # Gates cannot silently produce a removal/cancellation from a rejected newer row.
    assert "removed" not in report


def test_mappings_are_not_silently_chosen(workspace):
    a = "tests/fixtures/admin/admin_v1.csv"
    mapping = "mappings/admin_v1.yaml"
    confirm_mapping(mapping, workspace)
    first = ingest(a, mapping, workspace)
    other = Path("mappings/other.yaml")
    data = yaml.safe_load(Path(mapping).read_text())
    data["fields"]["owner"]["prefix"] = "another:"
    other.write_text(yaml.safe_dump(data))
    confirm_mapping(other, workspace)
    second = ingest(a, other, workspace)
    with pytest.raises(ValueError, match="multiple captures"):
        compare_files(a, a, workspace, "record_id")
    report = compare_files(a, a, workspace, "record_id", old_capture=first["capture_id"], new_capture=second["capture_id"])
    assert report["counts"]["changed"] == 4


def test_es_bundle_output_and_confirmation_isolation(workspace):
    a, mapping = "tests/fixtures/admin/admin_v1.csv", "mappings/admin_v1.yaml"
    es = get_bundle("es")
    confirm_mapping(mapping, es)
    result = ingest(a, mapping, es)
    assert result["bundle"] == "es"
    assert captures(workspace) == []
    assert all(r.source.bundle == "es" for r in captures(es)[0]["rows"])
