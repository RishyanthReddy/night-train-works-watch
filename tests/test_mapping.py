"""Synthetic-only mapping and real CLI checks. Never needs keys or network."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from nightdesk.audit import read_events
from nightdesk.cli import main
from nightdesk.config import BundleError, get_bundle
from nightdesk.intake.mapping import (
    Mapping, MappingError, captures, confirm_mapping, ingest, load_mapping,
    map_table, parse_value, FieldSpec,
)
from nightdesk.intake.table import read_table


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = {
        "version": 1, "dataset": "synthetic_admin", "licence": "synthetic",
        "record": "GenericRow", "file": {"type": "csv"}, "complete": True,
        "required": ["record_id", "duration_s"], "fields": {
            "record_id": {"column": "id", "parse": "str"},
            "duration_s": {"column": "seconds", "parse": "seconds"},
        },
    }
    mapping = tmp_path / "map.yaml"
    mapping.write_text(yaml.safe_dump(data))
    file = tmp_path / "input.csv"
    file.write_text("id,seconds,note\na,60,synthetic\nb,wrong,not logged\nc,-3,extra\n")
    return file, mapping, data, get_bundle("practice")


def test_refusal_confirm_ingest_and_rejects(setup, capsys):
    file, mapping, _, bundle = setup
    assert main(["ingest", str(file), "--mapping", str(mapping)]) == 1
    assert "mapping_not_confirmed" in capsys.readouterr().err
    assert main(["mapping", "confirm", str(mapping), "--actor", "Tester"]) == 0
    assert "confirmed " in capsys.readouterr().out
    assert main(["ingest", str(file), "--mapping", str(mapping)]) == 0
    assert "accepted=2 rejected=1" in capsys.readouterr().out
    assert main(["rejects"]) == 0
    out = capsys.readouterr().out
    assert "row=3 field=duration_s reason=invalid_number" in out
    capture = captures(bundle)[0]
    assert [r.fields["duration_s"] for r in capture["rows"]] == [60, -3]
    assert capture["rows"][0].extra == {"note": "synthetic"}
    assert not capture["capture"].complete
    assert "rejected_rows" in capture["capture"].incomplete_reasons
    assert "not logged" not in (bundle.root / "audit.jsonl").read_text()


def test_changed_mapping_needs_new_confirmation_and_bundle_confirmation(setup):
    file, mapping, _, bundle = setup
    confirm_mapping(mapping, bundle)
    mapping.write_text(mapping.read_text() + "# change\n")
    with pytest.raises(MappingError, match="mapping_not_confirmed"):
        ingest(file, mapping, bundle)
    confirm_mapping(mapping, bundle)
    with pytest.raises(MappingError, match="mapping_not_confirmed"):
        ingest(file, mapping, get_bundle("es"))


def test_same_import_reuses_and_keeps_prior_source(setup):
    file, mapping, _, bundle = setup
    confirm_mapping(mapping, bundle)
    a = ingest(file, mapping, bundle)
    before = (bundle.root / "audit.jsonl").read_bytes()
    b = ingest(file, mapping, bundle)
    assert a["capture_id"] == b["capture_id"] and b["reused"]
    assert len(captures(bundle)) == 1
    assert (bundle.root / "audit.jsonl").read_bytes() == before


@pytest.mark.parametrize("change", [
    {"version": 2}, {"version": True}, {"record": "WorkNotice"}, {"arbitrary_code": "no"},
    {"required": ["not_mapped"]}, {"timezone": "not/a-zone"},
    {"fields": {"entry.at": {"column": "a"}}},
    {"fields": {"a": {"column": "id", "parse": "eval:1+1"}}},
    {"fields": {"a": {"column": "id", "parse": "list:;:str"}}},
    {"fields": {"a": {"column": "id", "parse": "datetime:%Y"}}},
    {"fields": {"a": {"column": "id", "parse": "date:"}}},
    {"fields": {"a": {"column": "id", "parse": "str:code"}}},
])
def test_invalid_contract_refused(setup, change):
    _, mapping, data, _ = setup
    data.update(change)
    mapping.write_text(yaml.safe_dump(data))
    with pytest.raises((MappingError, ValueError)):
        load_mapping(mapping)


@pytest.mark.parametrize("text", [
    "!!python/object/apply:os.system ['touch should-not-exist']",
    "version: 1\nversion: 2", "a: &a [*a]", "a: &a [1]\nb: *a",
])
def test_unsafe_or_duplicate_yaml_refused(tmp_path, text):
    path = tmp_path / "bad.yaml"
    path.write_text(text)
    with pytest.raises(MappingError):
        load_mapping(path)
    assert not Path("should-not-exist").exists()


@pytest.mark.parametrize("parser,value,expected", [
    ("int", "-12", -12), ("float", "1.5", 1.5), ("seconds", "-1", -1),
    ("minutes_to_seconds", "1.5", 90), ("minutes_to_seconds", "-0.5", -30),
    ("date:%d/%m/%Y", "17/11/2026", "2026-11-17"),
    ("time:%H:%M", "09:02", "09:02:00"),
    ("datetime:%Y-%m-%d %H:%M", "2026-11-17 09:02", "2026-11-17T09:02:00+01:00"),
    ("datetime:%Y-%m-%dT%H:%M%z", "2026-11-17T09:02+0000", "2026-11-17T09:02:00+00:00"),
    ("enum:{yes_value: accepted}", "garbage", "unknown"),
])
def test_scalar_allowlist(parser, value, expected):
    result, reason = parse_value(value, FieldSpec(column="x", parse=parser), "Europe/Brussels")
    assert result == expected and reason == ("unknown_enum" if parser.startswith("enum:") else None)


@pytest.mark.parametrize("parser,value", [("int", "1.1"), ("seconds", "1.2"),
    ("minutes_to_seconds", "0.001"), ("float", "nan"), ("float", "1e10000"), ("int", True)])
def test_bad_scalar_values_rejected(parser, value):
    with pytest.raises(ValueError):
        parse_value(value, FieldSpec(column="x", parse=parser), None)


@pytest.mark.parametrize("value", ["2026-10-25 02:30", "2026-03-29 02:30"])
def test_ambiguous_time_kept_unresolved(setup, value):
    file, mapping_path, data, bundle = setup
    file.write_text(f"id,seconds,at\na,60,{value}\n")
    data["timezone"] = "Europe/Brussels"
    data["fields"]["at"] = {"column": "at", "parse": "datetime:%Y-%m-%d %H:%M"}
    data["required"].append("at")
    mapping_path.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping_path, bundle)
    result = ingest(file, mapping_path, bundle)
    row = captures(bundle)[0]["rows"][0]
    assert result["accepted"] == 1 and result["rejected"] == 0
    assert row.fields["at"] is None
    assert row.unresolved["at"]["reason"] == "ambiguous_local_time"
    assert row.unresolved["at"]["raw"] == [value]


def test_nested_json_extra_and_date_time(tmp_path):
    path = tmp_path / "nested.json"
    path.write_text(json.dumps([{"id": "a", "period": {"date": "2026-11-17", "time": "10:00", "keep": [1, {"a": 2}]}}]))
    m = Mapping.model_validate({
        "version": 1, "dataset": "synthetic", "licence": "synthetic", "record": "GenericRow",
        "file": {"type": "json"}, "timezone": "Europe/Brussels", "fields": {
            "at": {"parse": "date_time:[period.date, period.time]", "date_format": "%Y-%m-%d", "time_format": "%H:%M"},
        },
    })
    rows, rejects, _ = map_table(read_table(path), m, get_bundle("practice"), "c", datetime.now(timezone.utc))
    assert not rejects
    assert rows[0].fields["at"] == "2026-11-17T10:00:00+01:00"
    assert rows[0].extra == {"id": "a", "period": {"keep": [1, {"a": 2}]}}


def test_namespace_filter_null_default_and_missing_column(setup):
    file, mapping, data, bundle = setup
    data["filter"] = {"note": "synthetic"}
    data["fields"]["train_no"] = {"column": "id"}
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    result = ingest(file, mapping, bundle)
    assert result["accepted"] == 0 and result["rejected"] == 1 and result["filtered"] == 2
    assert captures(bundle)[0]["rejects"][0]["reason"] == "id_not_namespaced"
    data["fields"]["train_no"]["prefix"] = "test:"
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    assert ingest(file, mapping, bundle)["accepted"] == 1


def test_bundle_inputs_cannot_cross(setup):
    _, mapping, _, bundle = setup
    es = Path("data/es/file.csv")
    es.parent.mkdir(parents=True)
    es.write_text("id,seconds\na,1\n")
    confirm_mapping(mapping, bundle)
    with pytest.raises(BundleError):
        ingest(es, mapping, bundle)


def test_optional_null_default_required_and_missing_column(setup):
    file, mapping, data, bundle = setup
    file.write_text("id,seconds,note\na,NULL,hello\n,1,missing-id\n")
    data["fields"]["duration_s"]["default"] = 0
    data["fields"]["optional"] = {"column": "does_not_exist"}
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    assert ingest(file, mapping, bundle)["accepted"] == 0
    assert any(r["reason"] == "column_missing" for r in captures(bundle)[0]["rejects"])
    data["fields"].pop("optional")
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    ingest(file, mapping, bundle)
    found = [c for c in captures(bundle) if c["metadata"]["accepted"] == 1][0]
    assert found["rows"][0].fields["duration_s"] == 0


def test_symlink_artifact_cannot_escape_bundle(setup, tmp_path):
    file, mapping, _, bundle = setup
    confirm_mapping(mapping, bundle)
    ingest(file, mapping, bundle)
    cap = captures(bundle)[0]
    folder = bundle.root / "captures" / cap["capture"].capture_id
    (folder / "rows.jsonl").unlink()
    outside = tmp_path / "outside"
    outside.write_text("private")
    (folder / "rows.jsonl").symlink_to(outside)
    with pytest.raises(BundleError):
        captures(bundle)


def test_bad_default_cannot_bypass_scalar_validation(setup):
    file, mapping, data, bundle = setup
    file.write_text("id,seconds\na,NULL\n")
    data["fields"]["duration_s"]["default"] = "bad"
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    result = ingest(file, mapping, bundle)
    assert result["accepted"] == 0 and result["rejected"] == 1


def test_capture_mismatched_provenance_is_refused(setup):
    file, mapping, _, bundle = setup
    confirm_mapping(mapping, bundle)
    result = ingest(file, mapping, bundle)
    folder = bundle.root / "captures" / result["capture_id"]
    path = folder / "rows.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["source"]["capture_id"] = "other"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(MappingError, match="references disagree"):
        captures(bundle)


def test_invalid_date_source_text_is_not_copied_to_audit(setup):
    file, mapping, data, bundle = setup
    file.write_text("id,seconds,when\na,60,RESTRICTED TEXT\n")
    data["fields"]["when"] = {"column": "when", "parse": "date:%Y-%m-%d"}
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    ingest(file, mapping, bundle)
    assert "RESTRICTED TEXT" not in (bundle.root / "audit.jsonl").read_text()
    assert captures(bundle)[0]["rejects"][0]["reason"] == "invalid_date"


@pytest.mark.parametrize("required", [False, True])
@pytest.mark.parametrize("parser", ["time:%H:%M", "datetime:%Y-%m-%d %H:%M"])
def test_missing_time_is_kept_unresolved_even_when_required(setup, required, parser):
    file, mapping, data, bundle = setup
    file.write_text("id,seconds,at\na,60,\n")
    data["timezone"] = "Europe/Brussels"
    data["fields"]["at"] = {"column": "at", "parse": parser}
    if required:
        data["required"].append("at")
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    result = ingest(file, mapping, bundle)
    assert result["accepted"] == 1 and result["rejected"] == 0
    row = captures(bundle)[0]["rows"][0]
    assert row.fields["at"] is None
    assert row.unresolved["at"] == {"reason": "missing_time", "raw": [""], "timezone": "Europe/Brussels"}
    assert "unresolved_fields" not in captures(bundle)[0]["capture"].incomplete_reasons


def test_missing_joined_time_retains_both_raw_parts(setup):
    file, mapping, data, bundle = setup
    file.write_text("id,seconds,date,time\na,60,2026-11-17,\n")
    data["timezone"] = "Europe/Brussels"
    data["fields"]["at"] = {"parse": "date_time:[date, time]", "date_format": "%Y-%m-%d", "time_format": "%H:%M"}
    data["required"].append("at")
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    assert ingest(file, mapping, bundle)["accepted"] == 1
    assert captures(bundle)[0]["rows"][0].unresolved["at"]["raw"] == ["2026-11-17", ""]


def test_sparse_json_extra_is_not_padded_with_fabricated_fields(setup):
    _, mapping, data, bundle = setup
    file = Path("sparse.json")
    file.write_text('[{"id":"a","seconds":60},{"id":"b","seconds":30,"note":null}]')
    data["file"] = {"type": "json"}
    mapping.write_text(yaml.safe_dump(data))
    confirm_mapping(mapping, bundle)
    ingest(file, mapping, bundle)
    rows = captures(bundle)[0]["rows"]
    assert rows[0].extra == {} and rows[1].extra == {"note": None}
