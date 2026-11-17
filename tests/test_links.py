from datetime import date
from pathlib import Path
import shutil

import pytest

from nightdesk.audit import read_events
from nightdesk.cli import main
from nightdesk.config import get_bundle
from nightdesk.intake.mapping import confirm_mapping, ingest
from nightdesk.links import confirm_link, covers, find_link, import_links, link_id, links, load_link
from nightdesk.store import revisions

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(REPO / "tests/fixtures/paths", tmp_path / "paths")
    shutil.copytree(REPO / "mappings", tmp_path / "mappings")
    monkeypatch.chdir(tmp_path)
    bundle = get_bundle("practice")
    for file, mapping in [("legs.csv", "synthetic_path_legs.yaml"), ("crosswalk.csv", "synthetic_links.yaml")]:
        confirm_mapping("mappings/" + mapping, bundle)
        ingest("paths/" + file, "mappings/" + mapping, bundle)
    return bundle


def test_no_inference_from_train_or_journey_ref_then_source_crosswalk(workspace):
    from nightdesk.intake.mapping import captures
    leg = revisions(workspace)[0].payload
    assert find_link(leg, date(2026, 11, 17), links(workspace)) == (None, "unlinked")
    capture = next(c for c in captures(workspace) if c["metadata"]["record_type"] == "JourneyLinkMember")
    identifiers = import_links(workspace, capture["capture"].capture_id)
    assert len(identifiers) == 1
    link = load_link(workspace, identifiers[0])
    assert link.basis == "source" and link.source and len(link.members) == 2
    assert covers(link, leg, date(2026, 11, 17)) == (True, None)
    assert find_link(leg, date(2026, 11, 17), links(workspace))[0] == link
    assert import_links(workspace, capture["capture"].capture_id) == identifiers
    assert len(links(workspace)) == 1


def test_human_cli_requires_explicit_members_actor_and_rule(workspace, capsys):
    ids = [r.revision_id for r in revisions(workspace)]
    args = ["links", "confirm", "syn-journey", "--actor", "Planner", "--service-date-rule", "2026-11-17"]
    for identifier in ids:
        args.extend(["--revision", identifier])
    assert main(args) == 0
    assert "confirmed human link" in capsys.readouterr().out
    link = links(workspace)[0]
    assert link.basis == "human" and link.confirmed_by == "Planner"
    assert covers(link, revisions(workspace)[0].payload, date(2026, 11, 18)) == (False, "unlinked")
    assert len(read_events(workspace)) > 0
    assert links(get_bundle("es")) == []


def test_unknown_date_rule_and_conflicting_links_stay_unknown(workspace):
    ids = [r.revision_id for r in revisions(workspace)]
    confirm_link(workspace, "syn-journey", ids, "Planner", "next-day-by-guess")
    leg = revisions(workspace)[0].payload
    assert find_link(leg, date(2026, 11, 17), links(workspace)) == (None, "unsupported_service_date_rule")
    confirm_link(workspace, "syn-journey", ids, "Planner", "*")
    confirm_link(workspace, "different-journey", ids, "Planner", "*")
    assert find_link(leg, date(2026, 11, 17), links(workspace)) == (None, "ambiguous_journey_link")


def test_confirm_refuses_missing_actor_revisions_or_foreign_bundle(workspace):
    ids = [r.revision_id for r in revisions(workspace)]
    for actor, selected in [("", ids), ("Planner", []), ("Planner", [ids[0], ids[0]])]:
        with pytest.raises(ValueError):
            confirm_link(workspace, "syn-journey", selected, actor, "*")
    with pytest.raises((ValueError, OSError)):
        confirm_link(get_bundle("es"), "syn-journey", ids, "Planner", "*")
