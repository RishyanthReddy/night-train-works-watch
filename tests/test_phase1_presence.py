"""Council R2: source presence and boundary results survive the whole UI path."""
import csv
from datetime import date
import json
from pathlib import Path
import yaml
from streamlit.testing.v1 import AppTest

from test_phase1_council import workspace,load,edit
from nightdesk.desk import dossier,queue
from nightdesk.export import export_dossier
from nightdesk.links import import_links
from nightdesk.review import record_decision,follow_up

DAY=date(2026,11,17)
APP=Path(__file__).resolve().parents[1]/'src/nightdesk/ui/app.py'

def only_then_absent():
    for version in ['v1','v2']:
        p=Path('tests/fixtures/syn')/version/'legs.csv'
        with p.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
        with p.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows[:1] if version=='v1' else [])

def test_whole_leg_removal_and_addition_have_dossiers_and_exports(workspace):
    only_then_absent();b=workspace;a,c=load(b,'v1'),load(b,'v2')
    old,new=a['capture'].capture_id,c['capture'].capture_id
    row=queue(b,old,new)[0]
    assert row['change_kind']=='source_record_removed' and row['new_revision'] is None
    report=dossier(b,old,new,row['selection_revision'],DAY)
    assert report['before'] and report['after'] is None and report['source_presence']=={'before':True,'after':False}
    assert report['changes']['removed']==[row['old_revision']]
    assert 'leg_not_observed' in report['checks_after']['unresolved']
    assert report['work_records_before'] and report['selected_run_before']
    record_decision(b,row['selection_revision'],'Synthetic','needs_clarification','Missing source record has unknown operational meaning')
    follow_up(b,row['selection_revision'],'Synthetic owner','Please clarify the source omission')
    report=dossier(b,old,new,row['selection_revision'],DAY)
    md,js=export_dossier(report,b)
    assert json.loads(js.read_text())['after'] is None and 'Source presence' in md.read_text()
    added=queue(b,new,old)[0]
    assert added['change_kind']=='source_record_added' and added['old_revision'] is None
    report=dossier(b,new,old,added['selection_revision'],DAY)
    assert report['before'] is None and report['source_presence']=={'before':False,'after':True}
    assert report['changes']['added']==[added['new_revision']]
    export_dossier(report,b)

def test_one_sided_partial_capture_keeps_presence_unknown_and_no_removed_list(workspace):
    only_then_absent();p=Path('tests/fixtures/syn/v2/capture.yaml');m=yaml.safe_load(p.read_text());m['complete']=False;p.write_text(yaml.safe_dump(m))
    b=workspace;a,c=load(b,'v1'),load(b,'v2');old,new=a['capture'].capture_id,c['capture'].capture_id
    row=queue(b,old,new)[0]
    assert row['change_kind']=='record_presence_unknown' and row['after_operating'] is None
    report=dossier(b,old,new,row['selection_revision'],DAY)
    assert report['source_presence']['after'] is None and not report['changes']['removed']
    assert report['changes']['status']=='comparison_unavailable'

def test_removed_date_keeps_after_boundary_check_matching_its_queue_row(workspace):
    edit(Path('tests/fixtures/syn/v2/legs.csv'),dates='2026-11-18')
    b=workspace;a,c=load(b,'v1'),load(b,'v2');link=import_links(b,c['children']['links'])[0]
    old,new=a['capture'].capture_id,c['capture'].capture_id
    options=dict(link_identifier=link,reviewed_points={'syn:border1'})
    row=next(r for r in queue(b,old,new,**options) if r['train_no']=='aa:101' and r['service_date']==DAY.isoformat())
    report=dossier(b,old,new,row['selection_revision'],DAY,**options)
    assert report['findings'][0]['reason']=='operating_dates_differ'
    assert report['checks_after']['border']==row['checks_after']['border']
    assert 'border_not_checked' not in report['unknowns']

def test_works_only_dossier_keeps_both_versions_and_their_check_evidence(workspace):
    edit(Path('tests/fixtures/syn/v2/legs.csv'),exit_time='2026-11-17 23:00')
    edit(Path('tests/fixtures/syn/v2/works.csv'),clock_from='01:00',clock_to='02:00')
    b=workspace;a,c=load(b,'v1'),load(b,'v2');old,new=a['capture'].capture_id,c['capture'].capture_id
    row=queue(b,old,new)[0];report=dossier(b,old,new,row['selection_revision'],DAY)
    assert report['checks_before']['works']['A']==1 and report['checks_after']['no_match']==1
    before=next(w for w in report['work_records_before'] if w['payload']['work_id']=='syn-A')
    after=next(w for w in report['work_records'] if w['payload']['work_id']=='syn-A')
    assert before['payload']['clock_from']=='22:00:00' and after['payload']['clock_from']=='01:00:00'
    assert before['source'] and after['source'] and report['works_state_changes']

def test_app_can_review_and_export_a_whole_removed_leg(workspace,monkeypatch):
    only_then_absent();b=workspace;a,c=load(b,'v1'),load(b,'v2');monkeypatch.setenv('NIGHTDESK_BUNDLE',b.name)
    app=AppTest.from_file(APP).run(timeout=30)
    app.selectbox(key=b.name+':before').set_value(a['capture'].capture_id).run()
    app.selectbox(key=b.name+':after').set_value(c['capture'].capture_id).run()
    app.selectbox(key=b.name+':selected').select_index(0).run()
    assert not app.exception and any('is not in the later file' in str(e.value) for e in app.info)
    def field(items,label):return next(e for e in items if e.label==label)
    field(app.text_area,'Why').set_value('Synthetic source omission, not cancellation')
    field(app.button,'Record this decision').click().run()
    assert not app.exception
    field(app.button,'Export this change').click().run()
    assert not app.exception
    assert json.loads(next((b.root/'exports').glob('*.json')).read_text())['after'] is None


def test_a_batch_missing_its_entire_leg_file_remains_selectable_for_unknown_presence(workspace,monkeypatch):
    only_then_absent();Path('tests/fixtures/syn/v2/legs.csv').unlink()
    b=workspace;a,c=load(b,'v1'),load(b,'v2')
    assert not c['capture'].complete and c['failures'][0]['role']=='legs'
    monkeypatch.setenv('NIGHTDESK_BUNDLE',b.name)
    app=AppTest.from_file(APP).run(timeout=30)
    app.selectbox(key=b.name+':before').set_value(a['capture'].capture_id).run()
    app.selectbox(key=b.name+':after').set_value(c['capture'].capture_id).run()
    app.selectbox(key=b.name+':selected').select_index(0).run()
    assert not app.exception
    old,new=a['capture'].capture_id,c['capture'].capture_id
    row=queue(b,old,new)[0];report=dossier(b,old,new,row['selection_revision'],DAY)
    assert report['source_presence']['after'] is None and report['capture_comparison']['reason']=='incomplete_capture'
    assert not report['changes']['removed']


def test_multiple_changed_legs_for_same_train_date_are_one_task_with_explicit_leg_choice(workspace,monkeypatch):
    for version in ['v1','v2']:
        p=Path('tests/fixtures/syn')/version/'legs.csv'
        with p.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
        second=dict(rows[0],request_id='syn-second-request',sequence='4',source_status='offered' if version=='v1' else 'confirmed')
        with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows+[second])
    b=workspace;a,c=load(b,'v1'),load(b,'v2');old,new=a['capture'].capture_id,c['capture'].capture_id
    rows=queue(b,old,new);aa=[row for row in rows if row['train_no']=='aa:101']
    assert len(aa)==1 and len(aa[0]['leg_changes'])==2
    assert aa[0]['change_kind']=='multiple_source_leg_changes'
    monkeypatch.setenv('NIGHTDESK_BUNDLE',b.name)
    app=AppTest.from_file(APP).run(timeout=30)
    app.selectbox(key=b.name+':before').set_value(old).run()
    app.selectbox(key=b.name+':after').set_value(new).run()
    app.selectbox(key=b.name+':selected').select_index(0).run()
    assert not app.exception and app.selectbox(key=b.name+':source_leg').value is None
    app.selectbox(key=b.name+':source_leg').select_index(1).run()
    assert not app.exception and any('aa:101 / 2026-11-17' in e.value for e in app.text)
