import csv
import shutil
from pathlib import Path

import pytest

from nightdesk.audit import read_events
from nightdesk.cli import main
from nightdesk.config import get_bundle
from nightdesk.intake.mapping import confirm_mapping, ingest
from nightdesk.review import record_decision, follow_up, follow_ups, decisions, answer_follow_up
from nightdesk.store import revisions

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(REPO / "tests/fixtures/paths", tmp_path / "paths")
    shutil.copytree(REPO / "mappings", tmp_path / "mappings")
    monkeypatch.chdir(tmp_path)
    b = get_bundle("practice")
    confirm_mapping("mappings/synthetic_path_legs.yaml", b)
    ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", b)
    return b


def selected(bundle):
    return next(r for r in revisions(bundle) if r.payload.network == "aa")


def change_file():
    path = Path("paths/legs.csv")
    with path.open() as f:
        reader = csv.DictReader(f);header = reader.fieldnames;rows = list(reader)
    rows[0]["source_status"] = "confirmed"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header);writer.writeheader();writer.writerows(rows)


def test_new_revision_stales_review_reopens_question_history_preserved(workspace):
    revision = selected(workspace)
    d = record_decision(workspace, revision.revision_id, "Planner", "needs_clarification", "Synthetic boundary question")
    question = follow_up(workspace, revision.revision_id, "Person A", "Please confirm the point")
    answer_follow_up(workspace, question.follow_up_id, "Person A", "Synthetic answer")
    assert not d.stale and follow_ups(workspace)[0].status == "answered"
    audit_before = (workspace.root / "audit.jsonl").read_bytes()
    ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", workspace)
    assert not decisions(workspace)[0].stale  # same revision is not a newer revision
    change_file()
    ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", workspace)
    assert decisions(workspace)[0].stale
    assert follow_ups(workspace)[0].status == "reopened" and follow_ups(workspace)[0].owner == "Person A"
    assert (workspace.root / "audit.jsonl").read_bytes().startswith(audit_before)
    assert len(decisions(workspace)) == 1 and len(follow_ups(workspace)) == 1
    assert revision.source_status == "offered" and revision.import_status == "accepted"


def test_real_cli_review_and_followup(workspace, capsys):
    revision = selected(workspace)
    assert main(["review", revision.revision_id, "--actor", "Planner", "--disposition", "needs_clarification",
                 "--reason", "Synthetic reason", "--owner", "Person A", "--question", "What changed?"]) == 0
    assert '"needs_clarification"' in capsys.readouterr().out
    assert decisions(workspace)[0].revision_id == revision.revision_id
    assert follow_ups(workspace)[0].deadline is None


def test_reviewing_old_revision_after_new_import_is_visibly_stale(workspace):
    old = selected(workspace)
    change_file();ingest("paths/legs.csv", "mappings/synthetic_path_legs.yaml", workspace)
    d = record_decision(workspace, old.revision_id, "Planner", "accepted_locally", "I inspected an older snapshot")
    assert d.stale


def test_no_deadline_guess_empty_owner_or_cross_bundle_evidence(workspace):
    revision = selected(workspace)
    with pytest.raises(ValueError):
        follow_up(workspace, revision.revision_id, "Person A", "Question", deadline="2026-11-19T00:00Z")
    with pytest.raises(ValueError):
        follow_up(workspace, revision.revision_id, " ", "Question")
    with pytest.raises((ValueError, OSError)):
        record_decision(get_bundle("es"), revision.revision_id, "Planner", "accepted_locally", "Test")
    with pytest.raises(ValueError):
        record_decision(workspace, revision.revision_id, "Planner", "accepted_locally", "Test",
                        evidence=[revision.source.model_copy(update={"bundle": "es"})])
    with pytest.raises(ValueError):
        answer_follow_up(workspace, "not-in-this-bundle", "Planner", "Answer")
