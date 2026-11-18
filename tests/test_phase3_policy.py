"""P3.3 NDA-marked synthetic data requires explicit per-bundle consent."""
import json
from pathlib import Path
import shutil
from nightdesk.config import get_bundle,FIXED_BUNDLES
from nightdesk.intake.mapping import confirm_mapping,captures
from nightdesk.intake.text import submit_text
from nightdesk.llm.client import propose
from nightdesk.audit import read_events
from nightdesk.cli import main
from test_text import TEXT,PROPOSAL,REPO


def test_synthetic_nda_consent_cli_fixed_mocked_host_cache_and_revocation(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);monkeypatch.setitem(FIXED_BUNDLES,'test-nda-synthetic',True)
    b=get_bundle('test-nda-synthetic');p=Path('mapping.yaml');shutil.copy2(REPO/'mappings/synthetic_text.yaml',p)
    confirm_mapping(p,b,'Synthetic reviewer')
    assert b.nda and submit_text(b,TEXT,PROPOSAL,p,actor='Synthetic reviewer')['accepted']==1
    connections=[]
    class Response:
        status=200
        def read(self,n):return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(PROPOSAL)}}]}).encode()
    class Connection:
        def __init__(self,host,timeout):connections.append(dict(host=host,timeout=timeout))
        def request(self,method,path,body,headers):connections[-1].update(method=method,path=path)
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr('http.client.HTTPSConnection',Connection)
    monkeypatch.setenv('MISTRAL_API_KEY','synthetic-placeholder')
    monkeypatch.setenv('NIGHTDESK_EXTERNAL_PROCESSING_ALLOWED','true')
    monkeypatch.setenv('EXTERNAL_PROCESSING_ALLOWED','true')
    assert propose(b,TEXT,p,provider='mistral')['reasons']==['bundle_external_processing_disabled']
    assert not connections and read_events(b)[-1].kind=='text_request_refused'
    assert main(['consent','--bundle',b.name,'--allow','mistral','--actor','Synthetic authorizer'])==0
    event=read_events(b)[-1];assert event.kind=='model_consent' and event.payload==dict(actor='Synthetic authorizer',provider='mistral',allowed=True)
    assert event.ts.tzinfo is not None
    assert propose(b,TEXT,p,provider='mistral')['accepted']
    assert len(connections)==1 and connections[0]['host']=='api.mistral.ai' and connections[0]['path']=='/v1/chat/completions'
    caches=list((b.root/'llm/cache').glob('*.json'));assert len(caches)==1 and b.resolve(caches[0])
    assert TEXT in caches[0].read_text().replace('\\n','\n').replace('\\"','"')
    other=get_bundle('test-nda-other');assert not propose(other,TEXT,p,provider='replay',replay_path=caches[0])['accepted']
    assert not (other.root/'llm/cache').exists()
    # A private cached replay stays usable locally, and does not make another call.
    assert propose(b,TEXT,p,provider='replay',replay_path=caches[0])['accepted'] and len(connections)==1
    assert main(['consent','--bundle',b.name,'--revoke','mistral','--actor','Synthetic authorizer'])==0
    assert not propose(b,TEXT,p,provider='mistral')['accepted'] and len(connections)==1
    assert all('synthetic-placeholder' not in x.read_text() for x in b.root.rglob('*') if x.is_file())
    assert all(row.source.bundle==b.name for capture in captures(b) for row in capture['rows'])


def test_nda_model_refusal_is_visible_in_production_form(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.chdir(tmp_path);monkeypatch.setitem(FIXED_BUNDLES,'test-nda-screen',True)
    p=Path('mapping.yaml');shutil.copy2(REPO/'mappings/synthetic_text.yaml',p)
    b=get_bundle('test-nda-screen');confirm_mapping(p,b,'Synthetic reviewer')
    monkeypatch.setenv('NIGHTDESK_BUNDLE',b.name)
    monkeypatch.setattr('http.client.HTTPSConnection',lambda *a,**k: (_ for _ in ()).throw(AssertionError('no transport before consent')))
    app=AppTest.from_file(str(REPO/'src/nightdesk/ui/app.py')).run()
    next(x for x in app.text_input if x.label=='Text dataset mapping').set_value(str(p))
    next(x for x in app.text_area if x.label=='Source notice text').set_value(TEXT)
    next(x for x in app.selectbox if x.label=='Text proposal provider').select('mistral')
    next(x for x in app.button if x.label=='Get proposal only').click().run()
    assert not app.exception and any('bundle_external_processing_disabled' in e.value for e in app.error)
    assert read_events(b)[-1].payload['reason']=='bundle_external_processing_disabled'
    assert not captures(b)
