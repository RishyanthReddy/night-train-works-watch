"""Council R2 regressions: immutable evidence, matching and linear read operations."""
import csv
from datetime import date
import json
from pathlib import Path
import time
import yaml

import pytest

from test_phase1_council import workspace,load,edit
from nightdesk import audit
from nightdesk.audit import append_events
from nightdesk.config import get_bundle
from nightdesk.desk import queue,snapshot_revisions
from nightdesk.intake.batch import ingest_batch,load_batch
from nightdesk.intake.mapping import confirm_mapping,ingest,load_capture
from nightdesk.review import record_decision
from nightdesk.store import load_revision,make_revision,revisions,save_revision


def test_unknown_station_area_hop_cannot_supply_line_only_exposure():
    from test_match import run,work
    from nightdesk.match import match_work
    from nightdesk.model import RunPoint
    points=[RunPoint(point_id='syn:'+name,line_arr=arr,line_dep=dep,planned_arr=at,planned_dep=at)
        for name,at,arr,dep in [('a','2026-11-17T22:00+01:00','be:0/100','be:0/100'),
            ('b','2026-11-17T22:10+01:00','be:0/100','zz:9'),('c','2026-11-17T23:00+01:00','zz:9','zz:9')]]
    early=work(line='zz:9',from_point_id=None,to_point_id=None,clock_from='22:00',clock_to='22:05')
    result=match_work(early,run(points=points))
    assert result.outcome=='time_unknown' and result.reasons==['line_unknown_for_pass_window']
    later=work(line='zz:9',from_point_id=None,to_point_id=None,clock_from='22:15',clock_to='22:20')
    result=match_work(later,run(points=points))
    assert result.outcome=='B' and result.overlap_window[0].isoformat()=='2026-11-17T21:15:00+00:00'


def test_strong_endpoints_survive_line_disagreement_and_off_path_b_is_queued(workspace):
    from test_match import run,work
    from nightdesk.match import match_work
    result=match_work(work(line='zz:9'),run())
    assert result.outcome=='A' and 'line_mismatch' in result.reasons
    edit(Path('tests/fixtures/syn/v2/legs.csv'),exit_time='2026-11-17 23:00')
    path=Path('tests/fixtures/syn/v2/works.csv')
    with path.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    extra=dict(rows[0],work_id='syn-off-path',from_point_id='syn:x',to_point_id='syn:y',line='',description='Synthetic weak place evidence')
    with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows+[extra])
    a,c=load(workspace,'v1'),load(workspace,'v2')
    row=next(r for r in queue(workspace,a['capture'].capture_id,c['capture'].capture_id) if r['train_no']=='aa:101')
    assert not row['changed_fields'] and row['checks_after']['works']['B']==row['checks_before']['works']['B']+1


def test_first_audited_predecessor_cannot_be_replaced_in_raw_json(workspace):
    from test_store import source,work
    b=workspace;ref=source().model_copy(update={'bundle':b.name})
    a=make_revision(b,ref,work(description='A'))[0];save_revision(b,a)
    c=make_revision(b,ref,work(description='C'))[0];save_revision(b,c)
    linked=make_revision(b,ref,work(description='B'),a.revision_id,'human')[0];save_revision(b,linked)
    assert load_revision(b,linked.revision_id).predecessor==a.revision_id
    path=b.root/'revisions'/(linked.revision_id+'.json');raw=json.loads(path.read_text())
    raw['predecessor'],raw['predecessor_basis']=c.revision_id,'human';path.write_text(json.dumps(raw))
    with pytest.raises(ValueError,match='predecessor_metadata'):load_revision(b,linked.revision_id)
    assert audit.verify(b)['valid']


@pytest.mark.parametrize('artifact',['capture','batch'])
def test_edited_completeness_flags_cannot_enable_r2(workspace,artifact):
    b=workspace
    result=load(b,'syn_bad') if artifact=='capture' else load(b,'v1')
    if artifact=='capture':
        identifier=result['children']['works'];path=b.root/'captures'/identifier/'capture.json'
        record=json.loads(path.read_text());record['complete']=True;record['incomplete_reasons']=[];path.write_text(json.dumps(record))
        with pytest.raises(ValueError):load_capture(path.parent,b)
    else:
        # A declared-incomplete manifest with otherwise complete children.
        manifest=Path('tests/fixtures/syn/v1/incomplete.yaml')
        manifest.write_text(Path('tests/fixtures/syn/v1/capture.yaml').read_text().replace('complete: true','complete: false'))
        result=ingest_batch(manifest,b);identifier=result['capture'].capture_id
        path=b.root/'batches'/identifier/'batch.json';record=json.loads(path.read_text())
        record['capture'].update(complete=True,declared_complete=True,incomplete_reasons=[]);path.write_text(json.dumps(record))
        with pytest.raises(ValueError):load_batch(b,identifier)
    assert audit.verify(b)['valid']


def test_legacy_capture_recomputes_reject_completeness_without_artifact_commit(workspace):
    b=workspace;result=load(b,'syn_bad');identifier=result['children']['works'];folder=b.root/'captures'/identifier
    # Simulate the historical format in a synthetic temporary workspace. This
    # is a compatibility fixture, not a claim against a fully rewritten log.
    metadata=json.loads((folder/'metadata.json').read_text());metadata.pop('format_version');(folder/'metadata.json').write_text(json.dumps(metadata))
    events=[(e.kind,{k:v for k,v in e.payload.items() if k!='artifact_hashes'}) for e in audit.read_events(b)]
    audit.audit_path(b).unlink();append_events(b,events)
    assert not load_capture(folder,b)['capture'].complete
    capture=json.loads((folder/'capture.json').read_text());capture.update(complete=True,incomplete_reasons=[]);(folder/'capture.json').write_text(json.dumps(capture))
    with pytest.raises(ValueError,match='completeness'):load_capture(folder,b)


def test_reused_reader_never_leaks_to_a_new_operation_or_bundle(workspace):
    from nightdesk.store import ReadSession
    b=workspace;c=load(b,'v1');reader=ReadSession(b)
    rows=snapshot_revisions(b,c['capture'].capture_id,reader=reader)
    with pytest.raises(ValueError,match='cross_bundle'):load_revision(get_bundle('test-other'),rows[0].revision_id,reader=reader)
    path=b.root/'revisions'/(rows[0].revision_id+'.json');record=json.loads(path.read_text());record['source']['licence']='forged';path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='source'):load_revision(b,rows[0].revision_id)


def test_two_2000_row_captures_have_bounded_audit_and_capture_reads(tmp_path,monkeypatch):
    import nightdesk.audit as audit_module
    repo=Path(__file__).resolve().parents[1]
    with (repo/'tests/fixtures/syn/v1/works.csv').open() as f:template=next(csv.DictReader(f))
    monkeypatch.chdir(tmp_path);b=get_bundle('test-scaling')
    spec=yaml.safe_load((repo/'mappings/syn_works.yaml').read_text())
    spec['fields']['predecessor']={'column':'predecessor','parse':'str'}
    spec['fields']['predecessor_basis']={'column':'predecessor_basis','parse':'str'}
    mapping=tmp_path/'scaling.yaml';mapping.write_text(yaml.safe_dump(spec))
    template.update(predecessor='',predecessor_basis='')
    confirm_mapping(mapping,b,'Synthetic scaling tester')
    counters={'audit':0,'capture':0}
    real_events=audit_module.read_events;real_text=Path.read_text
    def events(bundle):
        counters['audit']+=1
        assert counters['audit']<=6,'audit read once per row instead of once per operation'
        return real_events(bundle)
    def read_text(path,*args,**kwargs):
        if path.name=='capture.json':
            counters['capture']+=1
            assert counters['capture']<=6,'capture read once per revision instead of once per operation'
        return real_text(path,*args,**kwargs)
    monkeypatch.setattr(audit_module,'read_events',events);monkeypatch.setattr(Path,'read_text',read_text)
    timings={};results=[];first_ids={}
    for version in ['before','after']:
        path=Path(version+'.csv')
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(template));writer.writeheader()
            writer.writerows(dict(template,work_id=f'synthetic-scale-{i}',description='Synthetic '+version,
                predecessor=first_ids.get(f'synthetic-scale-{i}',''),predecessor_basis='source_field' if version=='after' else '') for i in range(2000))
        counters.update(audit=0,capture=0);start=time.perf_counter();results.append(ingest(path,mapping,b));timings[version+'_ingest']=round(time.perf_counter()-start,3)
        if version=='before':
            first_ids={r.payload.work_id:r.revision_id for r in snapshot_revisions(b,results[0]['capture_id'])}
    for name,operation in [('snapshot',lambda:snapshot_revisions(b,results[1]['capture_id'])),('all_revisions',lambda:revisions(b))]:
        counters.update(audit=0,capture=0);start=time.perf_counter();records=operation();timings[name]=round(time.perf_counter()-start,3)
        assert len(records)==(2000 if name=='snapshot' else 4000)
        if name=='snapshot':assert all(r.predecessor==first_ids[r.payload.work_id] for r in records)
        assert counters['audit']<=2 and counters['capture']<=2
    counters.update(audit=0,capture=0);start=time.perf_counter()
    record_decision(b,records[-1].revision_id,'Synthetic reviewer','needs_clarification','Synthetic scale question')
    timings['record_decision']=round(time.perf_counter()-start,3)
    print('Synthetic scaling seconds:',json.dumps(timings,sort_keys=True))


def test_check_audit_deduplication_does_not_depend_on_local_review_labels(workspace):
    b=workspace;a,c=load(b,'v1'),load(b,'v2');old,new=a['capture'].capture_id,c['capture'].capture_id
    row=queue(b,old,new)[0];before=sum(e.kind=='comparison_checked' for e in audit.read_events(b))
    record_decision(b,row['selection_revision'],'Synthetic','needs_clarification','Synthetic review')
    row=queue(b,old,new)[0]
    assert row['local_review']=='needs_clarification'
    assert sum(e.kind=='comparison_checked' for e in audit.read_events(b))==before
