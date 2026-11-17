import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nightdesk.config import BundleError, get_bundle
from nightdesk.export import export_comparison, markdown
from nightdesk.generic import compare_files, compare_rows
from nightdesk.model import GenericRow, SourceRef


def row(key, value, *, bundle="practice", record="row:2"):
    return GenericRow(source=SourceRef(
        bundle=bundle, dataset="synthetic", record_id=record, capture_id="synthetic-v1",
        captured_at=datetime(2026, 11, 17, tzinfo=timezone.utc), content_sha256="a" * 64,
        url_or_path="/synthetic/file.csv", licence="synthetic"), fields={"id": key, "value": value})


def test_keyed_diffs_have_sources_and_only_file_meaning():
    a = [row("a", 1), row("b", 2), row("c", 3)]
    b = [row("a", 10), row("b", 2), row("d", 4)]
    report = compare_rows(a, b, "id")
    assert report["counts"] == {"changed": 1, "added": 1, "unchanged": 1, "only_in_old": 1}
    assert report["changed"][0]["field_diffs"] == [{"field": "value", "old": 1, "new": 10, "old_present": True, "new_present": True}]
    for group in ("changed", "added", "unchanged", "only_in_old"):
        for item in report[group]:
            assert any(item.get(k) and item[k]["source"]["record_id"] == "row:2" for k in ("old", "new"))
    assert "removed" not in report


def test_no_key_multiset_preserves_duplicates():
    r = row("a", 1)
    report = compare_rows([r, r], [r])
    assert report["status"] == "identity_uncertain" and report["reason"] == "no_key"
    assert report["counts"] == {"changed": 0, "added": 0, "unchanged": 1, "only_in_old": 1}


@pytest.mark.parametrize("rows,reason", [([row("a", 1), row("a", 2)], "duplicate_key"),
    ([row(None, 1)], "missing_or_nonscalar_key"), ([row([1], 1)], "missing_or_nonscalar_key")])
def test_uncertain_key_never_guesses_field_comparison(rows, reason):
    report = compare_rows(rows, [row("z", 1)], "id")
    assert report["status"] == "identity_uncertain" and report["reason"] == reason
    assert report["changed"] == []


def test_null_extra_presence_and_unresolved_changes():
    a = row("a", None).model_copy(update={"extra": {"nested": {"x": 1}}})
    b = row("a", None).model_copy(update={"fields": {"id": "a"}, "extra": {"nested": {"x": 2}},
                                        "unresolved": {"at": {"reason": "ambiguous_local_time"}}})
    report = compare_rows([a], [b], "id")
    diffs = report["changed"][0]["field_diffs"]
    assert {d["field"] for d in diffs} == {"value", "extra.nested", "unresolved.at"}
    assert next(d for d in diffs if d["field"] == "value")["new_present"] is False


def test_bundles_cannot_mix():
    with pytest.raises(ValueError, match="different bundles"):
        compare_rows([row("a", 1)], [row("a", 1, bundle="es")], "id")


def test_real_raw_compare_export_and_escaping(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a, b = Path("old.csv"), Path("new.csv")
    a.write_text('id,value\na,"<script>alert(1)</script> ![x](https://invalid)"\n')
    b.write_text("id,value\na,new\n")
    bundle = get_bundle("practice")
    report = compare_files(a, b, bundle, "id")
    assert report["inputs"]["old"]["mode"] == "unmapped_columns_unvalidated"
    assert report["data_label"] == "see_each_source_licence"
    md, js = export_comparison(report, bundle, bundle.root)
    text = md.read_text()
    assert "<script>" not in text and "![x](https://invalid)" not in text
    assert "&lt;script&gt;" in text
    assert "row%3A2" in text and "sha256=" in text
    assert json.loads(js.read_text()) == report
    before = js.read_bytes()
    assert export_comparison(report, bundle, bundle.root) == (md, js)
    assert js.read_bytes() == before
    with pytest.raises(BundleError):
        export_comparison(report, bundle, "data/out/es")


def test_export_refuses_symlink_target_and_foreign_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = Path("a.csv")
    a.write_text("id\na\n")
    bundle = get_bundle("practice")
    report = compare_files(a, a, bundle, "id")
    md, js = export_comparison(report, bundle, bundle.root)
    js.unlink()
    sentinel = tmp_path / "private.json"
    sentinel.write_text("private")
    js.symlink_to(sentinel)
    with pytest.raises((ValueError, BundleError)):
        export_comparison(report, bundle, bundle.root)
    assert sentinel.read_text() == "private"
    with pytest.raises(ValueError, match="another bundle"):
        export_comparison(report, get_bundle("es"), "data/out/es")


def test_json_absent_key_and_explicit_null_are_a_real_field_change(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a, b = Path("old.json"), Path("new.json")
    a.write_text('[{"id":"a"},{"id":"b","note":"keep"}]')
    b.write_text('[{"id":"a","note":null},{"id":"b","note":"keep"}]')
    report = compare_files(a, b, get_bundle("practice"), "id")
    assert report["counts"]["changed"] == 1 and report["counts"]["unchanged"] == 1
    assert report["changed"][0]["field_diffs"] == [{"field": "note", "old": None, "new": None,
                                                    "old_present": False, "new_present": True}]
    assert "note" not in report["changed"][0]["old"]["fields"]


def test_rendering_change_preserves_earlier_export_pair(tmp_path, monkeypatch):
    import nightdesk.export as exporter
    monkeypatch.chdir(tmp_path)
    source = Path("synthetic.csv")
    source.write_text("id,value\na,one\n")
    bundle = get_bundle("practice")
    report = compare_files(source, source, bundle, "id")
    renderer = exporter.markdown
    monkeypatch.setattr(exporter, "markdown", lambda r: "# Earlier renderer\n")
    old_paths = export_comparison(report, bundle, bundle.root)
    monkeypatch.setattr(exporter, "markdown", renderer)
    new_paths = export_comparison(report, bundle, bundle.root)
    assert old_paths != new_paths
    assert old_paths[0].read_text() == "# Earlier renderer\n"
    assert new_paths[0].read_text().startswith("# Generic comparison")
