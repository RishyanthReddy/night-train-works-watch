import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from nightdesk.audit import read_events
from nightdesk.cli import main
from nightdesk.config import get_bundle
from nightdesk.intake.mapping import captures, confirm_mapping, ingest, load_mapping
from nightdesk.model import SourceRef, WorkNotice
from nightdesk.store import load_revision, make_revision, revisions, save_revision, subject_key

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(REPO / "tests/fixtures/paths", tmp_path / "paths")
    shutil.copytree(REPO / "mappings", tmp_path / "mappings")
    monkeypatch.chdir(tmp_path)
    return get_bundle("practice")


def import_legs(bundle, file="paths/legs.csv", mapping="mappings/synthetic_path_legs.yaml"):
    confirm_mapping(mapping, bundle, "Synthetic tester")
    return ingest(file, mapping, bundle)


def edit_csv(path, update, target=0):
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)
    rows[target].update(update)
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


def test_real_typed_cli_ingest_nested_events_lists_extra_and_crosswalk(workspace, capsys):
    assert main(["mapping", "confirm", "mappings/synthetic_path_legs.yaml"]) == 0
    assert main(["ingest", "paths/legs.csv", "--mapping", "mappings/synthetic_path_legs.yaml"]) == 0
    assert "accepted=2 rejected=0" in capsys.readouterr().out
    c = captures(workspace)[0]
    assert c["capture"].complete and len(c["capture"].revision_ids) == 2
    r = revisions(workspace)[0]
    assert r.identity == "certain" and r.predecessor is None
    assert len(r.payload.operating_dates) == 2
    assert r.payload.extra == {"notes": "Synthetic only"}
    assert r.payload.entry.at.tzinfo is not None
    assert r.payload.entry.timezone == "Europe/Brussels"
    confirm_mapping("mappings/synthetic_links.yaml", workspace)
    result = ingest("paths/crosswalk.csv", "mappings/synthetic_links.yaml", workspace)
    links = next(c for c in captures(workspace) if c["metadata"]["record_type"] == "JourneyLinkMember")
    assert result["accepted"] == 2
    assert links["typed_rows"][0].train_no == "aa:101"


def test_identical_content_reuses_revision_across_captures_paths_and_time(workspace):
    first = import_legs(workspace)
    original = {r.revision_id: r for r in revisions(workspace)}
    before = {p: p.read_bytes() for p in (workspace.root / "revisions").glob("*.json")}
    assert ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", workspace)["reused"]
    shutil.copyfile("paths/legs.csv", "paths/copy.csv")
    second = ingest("paths/copy.csv", "mappings/synthetic_path_legs.yaml", workspace)
    assert first["capture_id"] != second["capture_id"]
    assert second["new_revision_ids"] == []
    assert {r.revision_id: r for r in revisions(workspace)} == original
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert len(captures(workspace)) == 2


def test_status_only_change_new_revision_no_supersession_and_datasets_separate(workspace):
    import_legs(workspace)
    initial = {r.revision_id for r in revisions(workspace)}
    edit_csv("paths/legs.csv", {"source_status": "confirmed"})
    ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", workspace)
    changed = [r for r in revisions(workspace) if r.revision_id not in initial]
    assert len(changed) == 1 and changed[0].source_status == "confirmed" and changed[0].predecessor is None
    other = yaml.safe_load(Path("mappings/synthetic_path_legs.yaml").read_text())
    other["dataset"] = "another_synthetic_dataset"
    Path("other.yaml").write_text(yaml.safe_dump(other))
    confirm_mapping("other.yaml", workspace)
    ingest("paths/legs.csv", "other.yaml", workspace)
    assert len(revisions(workspace)) == 5


@pytest.mark.parametrize("update,gate", [({"exit_time": "2026-11-17 20:00"}, "L2"),
    ({"dates": "not-a-date"}, "C1"), ({"train_no": "101"}, "C3")])
def test_bad_rows_rejected_declared_complete_capture_is_incomplete(workspace, update, gate):
    edit_csv("paths/legs.csv", update)
    result = import_legs(workspace)
    assert result["accepted"] == 1 and result["rejected"] == 1
    c = captures(workspace)[0]
    assert c["capture"].declared_complete and not c["capture"].complete
    assert "rejected_rows" in c["capture"].incomplete_reasons
    assert c["rejects"][0]["gate"] == gate
    assert any(e.kind == "gate_rejected" for e in read_events(workspace))


def test_missing_or_ambiguous_boundaries_kept_with_reasons_and_no_auto_link(workspace):
    edit_csv("paths/legs.csv", {"entry_time": "", "entry_point": "", "entry_kind": "unknown_kind"})
    import_legs(workspace)
    leg = next(r.payload for r in revisions(workspace) if r.payload.network == "aa")
    assert leg.entry.at is None and leg.entry.unresolved_reason == "missing_time" and leg.entry.point_id is None
    assert leg.entry.kind == "unknown" and leg.journey_ref == "syn-journey"
    assert leg.unresolved["entry.kind"]["raw"] == ["unknown_kind"]


def test_uncertain_identity_is_explicit_and_capture_not_complete(workspace):
    edit_csv("paths/legs.csv", {"sequence": ""})
    import_legs(workspace)
    r = next(r for r in revisions(workspace) if r.payload.network == "aa")
    assert r.identity == "uncertain" and r.subject_key.startswith("unresolved:")
    assert "identity_uncertain" in captures(workspace)[0]["capture"].incomplete_reasons


def test_duplicate_subjects_in_single_capture_block_completeness(workspace):
    with Path("paths/legs.csv").open() as f:
        lines = f.readlines()
    Path("paths/legs.csv").write_text("".join(lines + [lines[1]]))
    import_legs(workspace)
    assert "duplicate_subject" in captures(workspace)[0]["capture"].incomplete_reasons


def source(bundle="practice", dataset="synthetic"):
    return SourceRef(bundle=bundle, dataset=dataset, record_id="syn-1", capture_id="c",
                     content_sha256="a" * 64, captured_at=datetime(2026, 11, 17, tzinfo=timezone.utc),
                     url_or_path="synthetic.json", licence="synthetic")


def work(**updates):
    return WorkNotice(**(dict(work_id="syn-w", country="zz", date_start="2026-11-17", date_end="2026-11-18") | updates))


def test_r1_valid_predecessor_and_bad_link_keeps_revision(workspace):
    a, reason = make_revision(workspace, source(), work(description="old"))
    save_revision(workspace, a)
    b, reason = make_revision(workspace, source(), work(description="new"), a.revision_id, "source_field")
    assert reason is None and b.predecessor == a.revision_id
    for predecessor, basis in [("f" * 64, "human"), (b.revision_id, "human"), (a.revision_id, "guess")]:
        candidate, reason = make_revision(workspace, source(), work(description="new"), predecessor, basis)
        assert reason == "invalid_predecessor" and candidate.predecessor is None
    wrong, _ = make_revision(workspace, source(dataset="other"), work())
    save_revision(workspace, wrong)
    candidate, reason = make_revision(workspace, source(), work(description="new"), wrong.revision_id, "human")
    assert reason == "invalid_predecessor" and candidate.identity == "certain"


def test_loading_revision_rechecks_hash_and_bundle(workspace):
    r, _ = make_revision(workspace, source(), work())
    save_revision(workspace, r)
    assert load_revision(workspace, r.revision_id) == r
    path = workspace.root / "revisions" / (r.revision_id + ".json")
    data = json.loads(path.read_text());data["payload"]["description"] = "modified"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="hash_mismatch"):
        load_revision(workspace, r.revision_id)
    with pytest.raises(ValueError, match="cross_bundle"):
        make_revision(workspace, source(bundle="es"), work())


@pytest.mark.parametrize("updates", [{"date_start": "2016-10-16"}, {"date_end": "2026-11-16"}, {"weekdays": [0, 8]}])
def test_work_record_gates_reject_bad_dates_or_weekdays(workspace, updates):
    from nightdesk.gates import typed_record
    from nightdesk.model import GenericRow
    fields = dict(work_id="syn-work", country="zz", date_start="2026-11-17", date_end="2026-11-18") | updates
    row = GenericRow(source=source(), fields=fields)
    _, gates = typed_record(row, "WorkNotice", "Europe/Brussels")
    assert any(not g.passed and g.gate in {"W1", "W3"} for g in gates)


def test_incomplete_capture_cannot_declare_added_or_removed(workspace):
    from nightdesk.gates import capture_comparison_gate
    import_legs(workspace)
    a = captures(workspace)[0]["capture"]
    edit_csv("paths/legs.csv", {"exit_time": "bad-time"})
    ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", workspace)
    b = next(c["capture"] for c in captures(workspace) if c["capture"].capture_id != a.capture_id)
    assert a.complete and b.declared_complete and not b.complete
    assert capture_comparison_gate(a, b).reason_code == "incomplete_capture"
    assert capture_comparison_gate(a, a.model_copy(update={"filter": {"network": "aa"}})).reason_code == "filter_mismatch"


def test_rejected_predecessor_link_is_audited_and_revision_kept(workspace):
    mapping = Path("mappings/synthetic_path_legs.yaml")
    spec = yaml.safe_load(mapping.read_text())
    spec["fields"]["predecessor"] = {"column": "bad_predecessor", "parse": "str"}
    spec["fields"]["predecessor_basis"] = {"column": "basis", "parse": "str"}
    mapping.write_text(yaml.safe_dump(spec))
    with Path("paths/legs.csv").open() as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row.update(bad_predecessor="f" * 64, basis="source_field")
    with Path("paths/legs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    assert import_legs(workspace)["accepted"] == 2
    assert all(r.predecessor is None for r in revisions(workspace))
    assert sum(e.kind == "predecessor_rejected" for e in read_events(workspace)) == 2
