"""Reproductions from council round 1. Inputs here are synthetic only."""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

from nightdesk.audit import append_events, read_events
from nightdesk.cli import main
from nightdesk.config import BundleError, get_bundle
from nightdesk.export import escaped
from nightdesk.generic import compare_files
from nightdesk.intake.mapping import captures, confirm_mapping, ingest


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = {"version": 1, "dataset": "synthetic", "licence": "synthetic", "record": "GenericRow",
            "file": {"type": "csv"}, "required": ["id", "duration_s"], "fields": {
                "id": {"column": "id", "parse": "str"},
                "duration_s": {"column": "seconds", "parse": "seconds"},
                "state": {"column": "state", "parse": "enum:{open: open}"}}}
    Path("map.yaml").write_text(yaml.safe_dump(spec))
    b = get_bundle("practice")
    confirm_mapping("map.yaml", b)
    return b, spec


def test_case_alias_cannot_bypass_nda_or_foreign_bundle_guard(workspace):
    bundle, _ = workspace
    for parent in (Path("data/es"), Path("data/out/test-other")):
        parent.mkdir(parents=True)
        (parent / "synthetic.csv").write_text("id,seconds,state\na,60,open\n")
    if not Path("DATA/ES/synthetic.csv").exists():
        pytest.skip("case aliases do not exist on this filesystem")
    for alias in ("DATA/ES/synthetic.csv", "DATA/OUT/test-other/synthetic.csv"):
        with pytest.raises(BundleError):
            ingest(alias, "map.yaml", bundle)
    assert captures(bundle) == []


def test_flatten_cannot_cross_known_bundle_roots(workspace, capsys):
    Path("data/es").mkdir(parents=True)
    source = Path("data/es/synthetic.csv")
    source.write_text("id,seconds,state\na,60,open\n")
    output = Path("data/out/practice/leak.csv")
    for bundle in ("practice", "es"):
        assert main(["flatten", str(source), "--header-rows", "1", "--out", str(output), "--bundle", bundle]) == 1
        assert not output.exists()


@pytest.mark.parametrize("bad", ["1e5000", "1e100000000", "1e-100000000", "1e-999", "9" * 2000])
def test_extreme_numeric_cell_is_rejected_without_losing_good_rows(workspace, bad):
    bundle, _ = workspace
    Path("input.csv").write_text(f"id,seconds,state\na,60,open\nb,{bad},open\n")
    result = ingest("input.csv", "map.yaml", bundle)
    assert result["accepted"] == 1 and result["rejected"] == 1
    expected = "integer_seconds_required" if bad == "1e-999" else "number_out_of_range"
    assert captures(bundle)[0]["rejects"][0]["reason"] == expected
    assert captures(bundle)[0]["rows"][0].fields["duration_s"] == 60
    assert any(e.kind == "gate_rejected" for e in read_events(bundle))


def test_ingest_audit_reads_history_twice_independent_of_row_count(workspace, monkeypatch):
    import nightdesk.audit as audit
    bundle, _ = workspace
    Path("input.csv").write_text("id,seconds,state\n" + "".join(f"syn-{i},60,open\n" for i in range(2000)))
    decode = audit._decode_events
    reads = []
    def counted(raw, bundle, path):
        reads.append(len(raw))
        return decode(raw, bundle, path)
    monkeypatch.setattr(audit, "_decode_events", counted)
    assert ingest("input.csv", "map.yaml", bundle)["accepted"] == 2000
    assert len(reads) == 2  # confirmation lookup and the single locked append batch
    assert len(read_events(bundle)) == 2002


def test_independent_process_writers_get_unique_audit_sequences(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = """from nightdesk.audit import append_event
from nightdesk.config import get_bundle
for i in range(20): append_event(get_bundle('test-writers'), 'synthetic', {'n': i})
"""
    def run(_):
        return subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp_path, capture_output=True, text=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(4)))
    assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
    assert [e.seq for e in read_events(get_bundle("test-writers"))] == list(range(80))


def test_mixed_mapping_modes_and_datasets_are_refused(workspace):
    bundle, spec = workspace
    for name in ("a.csv", "b.csv"):
        Path(name).write_text("id,seconds,state\na,60,open\n")
    ingest("a.csv", "map.yaml", bundle)
    with pytest.raises(ValueError, match="mode_mismatch"):
        compare_files("a.csv", "b.csv", bundle, "id")
    spec["dataset"] = "different_synthetic_dataset"
    Path("other.yaml").write_text(yaml.safe_dump(spec))
    confirm_mapping("other.yaml", bundle)
    ingest("b.csv", "other.yaml", bundle)
    with pytest.raises(ValueError, match="dataset_mismatch"):
        compare_files("a.csv", "b.csv", bundle, "id")


def test_unknown_enum_keeps_raw_value_and_required_whitespace_is_rejected(workspace):
    bundle, _ = workspace
    Path("input.csv").write_text("id,seconds,state\na,60,bogus_state\n   ,90,open\n")
    result = ingest("input.csv", "map.yaml", bundle)
    assert result["accepted"] == 1 and result["rejected"] == 1
    c = captures(bundle)[0]
    assert c["rows"][0].fields["state"] == "unknown"
    assert c["rows"][0].unresolved["state"]["raw"] == ["bogus_state"]
    assert c["rows"][0].unresolved["state"]["reason"] == "unknown_enum"
    assert c["rejects"][0]["reason"] == "required_missing"


def test_apostrophes_are_not_corrupted_and_key_typos_are_named(workspace, capsys):
    assert escaped("O'Brien") == "O'Brien"
    for name in ("a.csv", "b.csv"):
        Path(name).write_text("id,seconds,state\na,60,open\n")
    assert main(["compare", "a.csv", "b.csv", "--key", "recordid"]) == 1
    assert "comparison key 'recordid' is absent" in capsys.readouterr().err
