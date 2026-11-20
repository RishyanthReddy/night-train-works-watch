"""P3.2 colliding canonical ids across two bundles and repeated app switches."""
import csv
from datetime import date
import json
from pathlib import Path
import shutil
import pytest
from nightdesk.config import get_bundle
from nightdesk.intake.mapping import confirm_mapping,ingest,captures
from nightdesk.desk import queue,dossier
from nightdesk.export import export_dossier
from nightdesk.review import record_decision,decisions
from nightdesk.audit import read_events
from nightdesk.llm.cache import save
from nightdesk.llm.client import propose
from nightdesk.store import load_revision
from test_text import TEXT,PROPOSAL

REPO=Path(__file__).resolve().parents[1]


def seed(bundle,marker,exit_time):
    root=bundle.resolve(bundle.root/'inputs');root.mkdir(parents=True)
    for role in ('legs','works'):
        confirm_mapping('mappings/syn_'+role+'.yaml',bundle,'Synthetic reviewer')
    def copied(role,version,target):
        with (REPO/'tests/fixtures/syn'/version/(role+'.csv')).open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
        for row in rows:row['notes' if role=='legs' else 'description']=marker
        if role=='legs' and version=='v2':rows[0]['exit_time']=exit_time
        with target.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    identifiers=[]
    for v in ('v1','v2'):
        path=root/(v+'.csv');copied('legs',v,path);identifiers.append(ingest(path,'mappings/syn_legs.yaml',bundle)['capture_id'])
    path=root/'works.csv';copied('works','v1',path);work=ingest(path,'mappings/syn_works.yaml',bundle)['capture_id']
    selected=next(r for r in queue(bundle,*identifiers,works_capture_id=work) if r['train_no']=='aa:101')['selection_revision']
    record_decision(bundle,selected,'Synthetic '+marker,'needs_clarification',marker)
    report=dossier(bundle,*identifiers,selected,date(2026,11,17),works_capture_id=work);export_dossier(report,bundle)
    cache=save(bundle,TEXT+'\n'+marker,PROPOSAL,dataset='synthetic_text',licence='synthetic')
    return dict(bundle=bundle.name,old=identifiers[0],new=identifiers[1],work=work,revision=selected,cache=str(cache),marker=marker)


def prepare(root):
    shutil.copytree(REPO/'mappings',root/'mappings')


def build_pair():
    return [seed(get_bundle('test-collision-a'),'SYNTHETIC_ALPHA_ONLY','2026-11-17 23:01'),
            seed(get_bundle('test-collision-b'),'SYNTHETIC_BETA_ONLY','2026-11-17 23:02')]


def test_colliding_subjects_keep_records_cache_decisions_exports_audit_isolated(tmp_path,monkeypatch):
    prepare(tmp_path);monkeypatch.chdir(tmp_path);a,b=build_pair()
    assert a['revision']!=b['revision']
    for own,other in ((a,b),(b,a)):
        bundle=get_bundle(own['bundle'])
        report=dossier(bundle,own['old'],own['new'],own['revision'],date(2026,11,17),works_capture_id=own['work'])
        assert report['train_no']=='aa:101' and report['after']['payload']['request_id']=='syn-request'
        assert report['work_records'][0]['payload']['work_id']=='syn-A'
        assert own['marker'] in json.dumps(report) and other['marker'] not in json.dumps(report)
        assert all(d.revision_id!=other['revision'] for d in decisions(bundle))
        assert other['marker'] not in '\n'.join(e.model_dump_json() for e in read_events(bundle))
        assert all(other['marker'] not in p.read_text() for p in (bundle.root/'exports').glob('*'))
        assert all(other['marker'] not in p.read_text() for p in (bundle.root/'llm/cache').glob('*'))
        assert propose(bundle,TEXT+'\n'+own['marker'],'mappings/synthetic_text.yaml',provider='replay',replay_path=own['cache'])['accepted']
        assert not propose(bundle,TEXT+'\n'+other['marker'],'mappings/synthetic_text.yaml',provider='replay',replay_path=other['cache'])['accepted']
        with pytest.raises((ValueError,OSError)):load_revision(bundle,other['revision'])
        with pytest.raises((ValueError,OSError)):queue(bundle,other['old'],own['new'])


def test_same_app_repeated_bundle_switches_do_not_render_other_bundle(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    prepare(tmp_path);monkeypatch.chdir(tmp_path);a,b=build_pair()
    app=AppTest.from_file(str(REPO/'src/nightdesk/ui/app.py')).run(timeout=30)
    for own,other in ((a,b),(b,a),(a,b)):
        next(x for x in app.text_input if x.label=='Case folder').set_value(own['bundle']).run()
        next(x for x in app.selectbox if x.label=='Earlier file').select(own['old']).run()
        next(x for x in app.selectbox if x.label=='Later file').select(own['new']).run()
        next(x for x in app.selectbox if x.label=='Engineering works file (optional)').select(own['work']).run()
        next(x for x in app.selectbox if x.label=='Open a train and date').select_index(0).run()
        assert not app.exception and not app.error
        text='\n'.join(str(x.value) for xs in (app.json,app.text,app.markdown) for x in xs)
        assert own['marker'] in text and other['marker'] not in text
        next(x for x in app.button if x.label=='Export this change').click().run()
        assert not app.exception
        assert all(other['marker'] not in p.read_text() for p in (get_bundle(own['bundle']).root/'exports').glob('*'))
