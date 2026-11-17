"""Regressions for independently reproduced Phase 1 council findings."""
import csv
from datetime import date
import json
from pathlib import Path
import shutil

import pytest
from nightdesk.audit import read_events, verify
from nightdesk.config import get_bundle
from nightdesk.desk import dossier, queue, snapshot_revisions
from nightdesk.intake.batch import confirm_batch, ingest_batch
from nightdesk.links import import_links
from nightdesk.review import record_decision, decisions, follow_up, follow_ups, answer_follow_up
from nightdesk.store import load_revision

REPO = Path(__file__).resolve().parents[1]

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(REPO/'mappings',tmp_path/'mappings')
    shutil.copytree(REPO/'tests/fixtures/syn',tmp_path/'tests/fixtures/syn')
    monkeypatch.chdir(tmp_path)
    return get_bundle('test-council')

def load(bundle, version):
    p=Path('tests/fixtures/syn')/version/'capture.yaml'
    confirm_batch(p,bundle,'Synthetic tester')
    return ingest_batch(p,bundle)

def selected(bundle, old, new):
    return queue(bundle,old['capture'].capture_id,new['capture'].capture_id)[0]['new_revision']

def edit(path, **updates):
    with path.open() as f:
        r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    rows[0].update(updates)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def test_removed_operating_day_visible_in_queue_and_export(workspace):
    edit(Path('tests/fixtures/syn/v1/legs.csv'),dates='2026-11-17;2026-11-18')
    edit(Path('tests/fixtures/syn/v2/legs.csv'),dates='2026-11-18')
    a,b=load(workspace,'v1'),load(workspace,'v2')
    rows=queue(workspace,a['capture'].capture_id,b['capture'].capture_id)
    removed=next(r for r in rows if r['service_date']=='2026-11-17')
    assert removed['before_operating'] and not removed['after_operating']
    report=dossier(workspace,a['capture'].capture_id,b['capture'].capture_id,removed['new_revision'],date(2026,11,17))
    assert report['operating_date_presence']=={'before':True,'after':False}
    assert 'cancellation' not in report['changes']['field_diffs'][0]['field']

def test_revert_observation_stales_newer_review_and_new_review_on_return_is_current(workspace):
    b=workspace;a,c=load(b,'v1'),load(b,'v2')
    identifier=selected(b,a,c)
    record_decision(b,identifier,'Synthetic','needs_clarification','Synthetic B')
    # A new manifest refers to exactly the old source captures. No new revision_created.
    p=Path('tests/fixtures/syn/v1/return.yaml')
    p.write_text(Path('tests/fixtures/syn/v1/capture.yaml').read_text().replace('Synthetic v1','Synthetic return A'))
    before=sum(e.kind=='revision_created' for e in read_events(b))
    back=ingest_batch(p,b)
    assert before==sum(e.kind=='revision_created' for e in read_events(b))
    assert decisions(b)[0].stale
    row=queue(b,a['capture'].capture_id,c['capture'].capture_id)[0]
    assert row['local_review'].endswith('(stale)')
    old_id=next(r.revision_id for r in snapshot_revisions(b,back['capture'].capture_id) if r.subject_type=='path_leg' and r.payload.network=='aa')
    record_decision(b,old_id,'Synthetic','accepted_locally','Re-reviewed returning A')
    assert not decisions(b)[-1].stale
    assert decisions(b)[0].stale  # never revive an earlier decision automatically

def test_reanswered_follow_up_can_close_then_reopen_again(workspace):
    b=workspace;a,c=load(b,'v1'),load(b,'v2');identifier=selected(b,a,c)
    f=follow_up(b,identifier,'Synthetic owner','Synthetic question')
    answer_follow_up(b,f.follow_up_id,'Synthetic owner','First answer')
    assert follow_ups(b)[0].status=='answered'
    load(b,'v3');assert follow_ups(b)[0].status=='reopened'
    answer_follow_up(b,f.follow_up_id,'Synthetic owner','Answer after reopening')
    assert follow_ups(b)[0].status=='answered'
    load(b,'v3');assert follow_ups(b)[0].status=='answered'
    p=Path('tests/fixtures/syn/v1/return.yaml');p.write_text(Path('tests/fixtures/syn/v1/capture.yaml').read_text().replace('Synthetic v1','Synthetic return'))
    ingest_batch(p,b);assert follow_ups(b)[0].status=='reopened'

def test_checks_audited_once_with_sources_versions_and_results(workspace):
    b=workspace;a,c=load(b,'v1'),load(b,'v2');identifier=selected(b,a,c)
    link=import_links(b,c['children']['links'])[0]
    args=(b,a['capture'].capture_id,c['capture'].capture_id,identifier,date(2026,11,17))
    options=dict(works_capture_id=c['capture'].capture_id,run_capture_id=c['capture'].capture_id,link_identifier=link,reviewed_points={'syn:border1'})
    before=len(read_events(b));report=dossier(*args,**options)
    assert len(read_events(b))==before+1
    event=read_events(b)[-1]
    assert event.kind=='dossier_checked' and event.hash==report['check_audit']['hash']
    assert {e['outcome'] for e in event.payload['exposures']}=={'A','B','time_unknown','unlocated'}
    assert event.payload['findings'][0]['result']=='mismatch'
    assert event.payload['revision_refs'] and event.payload['rule_versions']['time']=='time-v1'
    assert 'Synthetic A' not in event.model_dump_json()
    dossier(*args,**options);assert len(read_events(b))==before+1
    verify(b)

def test_work_payload_extra_and_run_evidence_survive_dossier(workspace):
    for version in ['v1','v2']:
        p=Path('tests/fixtures/syn')/version/'works.csv'
        with p.open() as f:r=csv.DictReader(f);rows=list(r);fields=r.fieldnames
        for row in rows:row['unmapped_note']='<script>synthetic-extra</script>'
        with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields+['unmapped_note']);w.writeheader();w.writerows(rows)
    b=workspace;a,c=load(b,'v1'),load(b,'v2');identifier=selected(b,a,c)
    report=dossier(b,a['capture'].capture_id,c['capture'].capture_id,identifier,date(2026,11,17),works_capture_id=c['capture'].capture_id,run_capture_id=c['capture'].capture_id)
    assert any(w['payload']['description']=='Synthetic A' for w in report['work_records'])
    assert report['work_records'][0]['payload']['extra']['unmapped_note']=='<script>synthetic-extra</script>'
    assert report['selected_run']['kind']=='scheduled' and report['selected_run']['input_refs']
    from nightdesk.export import export_dossier
    md,js=export_dossier(report,b)
    assert '<script>' not in md.read_text() and json.loads(js.read_text())['work_records']==report['work_records']

def test_source_metadata_tamper_refused_and_raw_time_keeps_source_cells(workspace):
    b=workspace;c=load(b,'v1')
    r=next(r for r in snapshot_revisions(b,c['capture'].capture_id) if r.subject_type=='path_leg' and r.payload.network=='aa')
    assert r.payload.exit.raw_time=='2026-11-17 23:00'
    path=b.root/'revisions'/(r.revision_id+'.json');doc=json.loads(path.read_text());doc['source']['licence']='CC0';doc['source']['url_or_path']='/forged.csv';path.write_text(json.dumps(doc))
    with pytest.raises(ValueError,match='source'):load_revision(b,r.revision_id)


def test_equal_date_sets_do_not_bypass_incomplete_boundary_capture():
    from test_border import setup, check, source
    from nightdesk.model import Capture
    a,b,link=setup()
    ca=Capture(capture_id="syn-a",bundle="practice",dataset="synthetic",captured_at=source().captured_at,
               declared_complete=True,complete=False,incomplete_reasons=["rejected_rows"],revision_ids=[a.revision_id,b.revision_id])
    found=check(a,b,link,left_capture=ca,right_capture=ca)
    assert found.result=="unknown" and found.reason=="incomplete_capture"


def test_row_warnings_do_not_change_effective_completeness(workspace):
    edit(Path('tests/fixtures/syn/v1/legs.csv'),entry_time='',exit_kind='not-a-kind')
    a=load(workspace,'v1')
    assert a['capture'].complete and not a['rejects']
    leg=next(r for r in snapshot_revisions(workspace,a['capture'].capture_id) if r.subject_type=='path_leg' and r.payload.network=='aa')
    assert leg.payload.entry.at is None and leg.payload.exit.kind=='unknown'
    assert leg.payload.unresolved
    b=load(workspace,'v2')
    from nightdesk.changes import compare_captures
    assert compare_captures(workspace,a['capture'],b['capture']).status=='compared'


def test_valid_later_predecessor_is_append_only_and_conflicts_are_audited(workspace):
    from nightdesk.store import make_revision, save_revision
    from test_store import source, work
    b=workspace;ref=source().model_copy(update={'bundle':b.name})
    a=make_revision(b,ref,work(description='A'))[0];save_revision(b,a)
    other=make_revision(b,ref,work(description='Other'))[0];save_revision(b,other)
    c=make_revision(b,ref,work(description='B'))[0];save_revision(b,c)
    path=b.root/'revisions'/(c.revision_id+'.json');original=path.read_bytes()
    linked,reason=make_revision(b,ref,work(description='B'),a.revision_id,'source_field')
    assert reason is None
    kept,created=save_revision(b,linked)
    assert not created and kept.predecessor==a.revision_id and path.read_bytes()==original
    assert any(e.kind=='predecessor_recorded' for e in read_events(b))
    conflict,reason=make_revision(b,ref,work(description='B'),other.revision_id,'human')
    assert reason is None
    kept,_=save_revision(b,conflict)
    assert kept.predecessor==a.revision_id and path.read_bytes()==original
    assert read_events(b)[-1].payload['reason']=='predecessor_conflict'


def test_line_only_clock_must_overlap_the_matching_segment():
    from test_match import run,work
    from nightdesk.match import match_work
    from nightdesk.model import RunPoint
    points=[RunPoint(point_id='syn:'+pt,line_arr=arr,line_dep=dep,planned_arr=at,planned_dep=at)
            for pt,at,arr,dep in [('a','2026-11-17T22:00+01:00','zz:1','zz:1'),
             ('b','2026-11-17T22:10+01:00','zz:1','zz:9'),('c','2026-11-17T23:00+01:00','zz:9','zz:9')]]
    w=work(line='zz:9',from_point_id=None,to_point_id=None,clock_from='22:00',clock_to='22:05')
    assert match_work(w,run(points=points)) is None
    w=work(line='zz:9',from_point_id=None,to_point_id=None,clock_from='22:15',clock_to='22:20')
    exposure=match_work(w,run(points=points))
    assert exposure.outcome=='B' and exposure.overlap_window[0].isoformat()=='2026-11-17T21:15:00+00:00'


def test_works_only_exposure_disappearing_stays_in_queue(workspace):
    edit(Path('tests/fixtures/syn/v2/legs.csv'),exit_time='2026-11-17 23:00')
    edit(Path('tests/fixtures/syn/v2/works.csv'),clock_from='01:00',clock_to='02:00')
    b=workspace;a,c=load(b,'v1'),load(b,'v2')
    rows=queue(b,a['capture'].capture_id,c['capture'].capture_id)
    assert len(rows)==1 and rows[0]['changed_fields']==[] and rows[0]['checks_changed']
    assert rows[0]['checks_before']['works']['A']==1 and rows[0]['checks_after']['works']['A']==0
    assert rows[0]['checks_after']['no_match']==1
    assert 'unlinked' in rows[0]['checks_after']['unresolved']
    report=dossier(b,a['capture'].capture_id,c['capture'].capture_id,rows[0]['new_revision'],date(2026,11,17))
    assert report['changes']['field_diffs']==[] and report['no_match_checked_pairs']==1


def test_neighbor_boundary_change_can_queue_unchanged_leg(workspace):
    edit(Path('tests/fixtures/syn/v2/legs.csv'),exit_time='2026-11-17 23:00')
    p=Path('tests/fixtures/syn/v2/legs.csv')
    with p.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    rows[1]['entry_time']='2026-11-17 23:01'
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    b=workspace;a,c=load(b,'v1'),load(b,'v2');link=import_links(b,c['children']['links'])[0]
    rows=queue(b,a['capture'].capture_id,c['capture'].capture_id,link_identifier=link,reviewed_points={'syn:border1'})
    aa=next(row for row in rows if row['train_no']=='aa:101')
    assert not aa['changed_fields'] and aa['checks_changed']
    assert aa['checks_after']['border'][0]['result']=='mismatch'


def test_global_unlocated_change_does_not_attach_a_queue_task_to_every_train(workspace):
    edit(Path('tests/fixtures/syn/v2/legs.csv'),exit_time='2026-11-17 23:00')
    p=Path('tests/fixtures/syn/v2/works.csv')
    with p.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    rows[2]['clock_from'],rows[2]['clock_to']='01:00','02:00'
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    b=workspace;a,c=load(b,'v1'),load(b,'v2')
    assert queue(b,a['capture'].capture_id,c['capture'].capture_id)==[]


def test_missing_capture_evidence_cannot_produce_a_positive_boundary_check():
    from test_border import setup,DAY
    from nightdesk.border import check_boundary
    a,b,link=setup()
    result=check_boundary(a,b,DAY,link=link,reviewed_points={'syn:border'})
    assert result.result=='unknown' and result.reason=='capture_completeness_unknown'
