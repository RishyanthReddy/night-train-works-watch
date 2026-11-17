"""Declared synthetic captures exercise the whole Phase 1 planner workflow."""
from datetime import date
import json
from pathlib import Path
import shutil
import pytest
from nightdesk.config import get_bundle
from nightdesk.intake.batch import confirm_batch, ingest_batch, load_batch
from nightdesk.desk import dossier, queue
from nightdesk.links import import_links
from nightdesk.review import record_decision, follow_up, decisions, follow_ups
from nightdesk.store import revisions
from nightdesk.export import export_dossier
from nightdesk.audit import verify
from nightdesk.changes import compare_captures

REPO=Path(__file__).resolve().parents[1]

@pytest.fixture
def workspace(tmp_path,monkeypatch):
    shutil.copytree(REPO/'mappings',tmp_path/'mappings')
    shutil.copytree(REPO/'tests/fixtures/syn',tmp_path/'tests/fixtures/syn')
    monkeypatch.chdir(tmp_path)
    return get_bundle('test-syn')

def load(bundle, version):
    path=Path('tests/fixtures/syn')/version/'capture.yaml'
    confirm_batch(path,bundle,'Synthetic tester')
    return ingest_batch(path,bundle)

def test_complete_capture_to_dossier_review_export_reimport_and_stale(workspace):
    b=workspace
    old,new=load(b,'v1'),load(b,'v2')
    assert old['capture'].complete and new['capture'].complete
    assert not old['rejects'] and not new['rejects']
    link=import_links(b,new['children']['links'])[0]
    a,c=old['capture'].capture_id,new['capture'].capture_id
    rows=queue(b,a,c)
    assert len(rows)==1 and rows[0]['train_no']=='aa:101'
    identifier=rows[0]['new_revision']
    report=dossier(b,a,c,identifier,date(2026,11,17),works_capture_id=c,run_capture_id=c,link_identifier=link,reviewed_points={'syn:border1'})
    assert {r['outcome'] for r in report['works_exposures']}=={'A','B','time_unknown'}
    assert len(report['unlocated_checks_not_attached_to_train'])==1
    assert report['findings'][0]['result']=='mismatch'
    record_decision(b,identifier,'Synthetic planner','needs_clarification','Boundary question')
    follow_up(b,identifier,'Synthetic owner','Please confirm the boundary')
    report=dossier(b,a,c,identifier,date(2026,11,17))
    md,js=export_dossier(report,b)
    assert md.exists() and json.loads(js.read_text())['follow_ups'][0]['owner']=='Synthetic owner'
    count=len(revisions(b))
    again=load(b,'v2')
    assert again['capture'].capture_id==c and len(revisions(b))==count
    assert queue(b,c,c)==[] and not decisions(b)[0].stale
    load(b,'v3')
    assert decisions(b)[0].stale and follow_ups(b)[0].status=='reopened'
    bad=load(b,'syn_bad')
    assert not bad['capture'].complete and bad['rejects'][0]['gate']=='W1'
    seal=verify(b)
    assert verify(b,seal=seal['hash'],count=seal['count'])

def test_missing_file_is_incomplete_and_cannot_imply_removal(workspace):
    old=load(workspace,'v1')
    Path('tests/fixtures/syn/v2/legs.csv').unlink()
    new=load(workspace,'v2')
    assert not new['capture'].complete and new['failures'][0]['role']=='legs'
    compared=compare_captures(workspace,old['capture'],new['capture'])
    assert compared.reason=='incomplete_capture' and not compared.removed

def test_confirmation_required_before_any_children_and_batch_tamper_refused(workspace):
    with pytest.raises(ValueError,match='mapping_not_confirmed'):
        ingest_batch('tests/fixtures/syn/v1/capture.yaml',workspace)
    assert not list((workspace.root/'captures').glob('*'))
    result=load(workspace,'v1')
    path=workspace.root/'batches'/result['capture'].capture_id/'batch.json'
    doc=json.loads(path.read_text());doc['children'].pop('legs');path.write_text(json.dumps(doc))
    with pytest.raises(ValueError):load_batch(workspace,result['capture'].capture_id)
