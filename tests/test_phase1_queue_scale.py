"""R3 queue enumeration and explicit missing-boundary evidence."""
from datetime import date
from types import SimpleNamespace
from pathlib import Path
import csv
import pytest
from test_phase1_council import workspace, load
from nightdesk.desk import _checks, queue, dossier
from nightdesk.links import import_links
from test_border import source
from nightdesk.model import JourneyLink, JourneyLinkMember

DAY=date(2026,11,17)

@pytest.mark.parametrize("n", [100,400,800])
def test_leg_sequence_inspections_are_bounded_per_selected_context(n,monkeypatch):
    accesses=[0]
    class Payload:
        train_no="aa:1"
        @property
        def sequence(self):
            accesses[0]+=1
            return 1
    legs=[SimpleNamespace(payload=Payload(),revision_id=str(i),identity="certain",source=source()) for i in range(n)]
    def no_pair(*args,**kwargs):
        pytest.fail("No adjacent sequence exists")
    monkeypatch.setattr("nightdesk.desk.check_boundary",no_pair)
    for side in range(2):
        context={"runs":[],"works":[],"legs":legs,"capture":SimpleNamespace(capture_id="synthetic-capture")}
        for revision in legs:
            result=_checks(revision,DAY,context,None,set())
            assert result["summary"]["unresolved"]==["no_run_selected","unlinked"]
    assert accesses[0]<=4*n


def test_only_actual_adjacent_pairs_are_checked(monkeypatch):
    n=500;calls=[]
    legs=[SimpleNamespace(payload=SimpleNamespace(sequence=i+1,train_no=f"aa:{i}",network="aa"),revision_id=str(i),identity="certain",source=source()) for i in range(n)]
    def check(a,b,*args,**kwargs):
        calls.append((a.payload.sequence,b.payload.sequence))
        return SimpleNamespace(result="unknown",reason="unlinked")
    monkeypatch.setattr("nightdesk.desk.check_boundary",check)
    link=JourneyLink(journey_id="synthetic-link",basis="source",source=source(),members=[
        JourneyLinkMember(source=source(),journey_id="synthetic-link",network="aa",train_no=f"aa:{i}",service_date_rule="*") for i in range(n)])
    for side in range(2):
        context={"runs":[],"works":[],"legs":legs,"capture":SimpleNamespace(capture_id="synthetic-capture")}
        for revision in legs: _checks(revision,DAY,context,link,set())
    assert len(calls)==4*(n-1)
    assert all(b==a+1 for a,b in calls)


def test_removed_neighbour_is_an_explicit_unknown_in_remaining_leg(workspace):
    p=Path("tests/fixtures/syn/v2/legs.csv")
    with p.open() as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    with p.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows[1:])
    a,b=load(workspace,"v1"),load(workspace,"v2")
    link=import_links(workspace,a["children"]["links"])[0]
    options=dict(link_identifier=link,reviewed_points={"syn:border1","syn:border2"})
    ids=(a["capture"].capture_id,b["capture"].capture_id)
    row=next(r for r in queue(workspace,*ids,**options) if r["train_no"]=="bb:202")
    report=dossier(workspace,*ids,row["selection_revision"],DAY,**options)
    missing=[f for f in report["findings"] if f["reason"]=="adjacent_leg_not_observed"]
    assert len(missing)==1 and missing[0]["result"]=="unknown"
    assert missing[0]["detail"]["selected_capture"]==ids[1]
    assert "adjacent_leg_not_observed" in report["unknowns"]
    assert row["checks_after"]["border"]==report["checks_after"]["border"]
    assert row["checks_after"]["unresolved"].count("no_run_selected")==1
    assert any(f["result"]=="agrees_on_checked_fields" for f in report["findings"])
    # Source membership alone never fabricates a missing-neighbour check
    # when the planner has not selected an explicit journey link.
    unlinked=dossier(workspace,*ids,row["selection_revision"],DAY)
    assert not any(f["reason"]=="adjacent_leg_not_observed" for f in unlinked["findings"])
