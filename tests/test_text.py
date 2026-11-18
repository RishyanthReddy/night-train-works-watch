"""Quoted text shares deterministic gates; live requests are mocked only."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import pytest
from nightdesk.audit import read_events
from nightdesk.config import get_bundle
from nightdesk.intake.mapping import confirm_mapping, captures
from nightdesk.intake.text import submit_text, validate_proposal
from nightdesk.llm.client import propose, consent
from nightdesk.llm.cache import save

REPO=Path(__file__).resolve().parents[1]
FIELDS=dict(work_id='synthetic-notice', country='zz', date_start='2026-11-17',date_end='2026-11-18',
            clock_from='23:00',clock_to='04:55',recurrence='periodical',weekdays=[1,2,3,4,5],timezone='Europe/Brussels',
            from_place='Synthetic Alpha',to_place='Synthetic Charlie',effect='closure')
TEXT='Synthetic notice. '+ '\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in FIELDS.items())
PROPOSAL={'fields':FIELDS,'quotes':{k:json.dumps(v,ensure_ascii=False) for k,v in FIELDS.items()}}

@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);p=tmp_path/'mapping.yaml';shutil.copy(REPO/'mappings/synthetic_text.yaml',p)
    return get_bundle('practice'),p


def test_manual_no_keys_same_gates_and_preserved_quotes(setup,monkeypatch):
    b,p=setup;monkeypatch.delenv('MISTRAL_API_KEY',raising=False)
    result=submit_text(b,TEXT,PROPOSAL,p,actor='Synthetic person')
    assert result['accepted']==1 and result['rejected']==0
    c=captures(b)[0];assert not c['capture'].complete
    assert c['typed_rows'][0].proposed_by=='manual'
    assert c['typed_rows'][0].extra['evidence']==PROPOSAL['quotes']
    assert c['typed_rows'][0].extra['source_text']==TEXT
    bad=deepcopy(PROPOSAL);bad['fields']['line']='bare';bad['quotes']['line']='bare'
    result=submit_text(b,TEXT+' bare',bad,p,actor='Synthetic person')
    assert result['rejected']==1 and result['reasons']==['schema_invalid']
    assert len(captures(b))==1


def test_exact_field_quote_no_hallucination_or_schema_escape(setup):
    b,p=setup;bad=deepcopy(PROPOSAL);bad['fields']['country']='xx'
    assert not validate_proposal(b,TEXT,bad,dataset='synthetic_text',licence='synthetic',mode='llm')[0]
    bad=deepcopy(PROPOSAL);bad['fields']['extra']={'action':'anything'}
    assert validate_proposal(b,TEXT,bad,dataset='synthetic_text',licence='synthetic',mode='llm')[1]==['proposal_field_not_allowed']
    bad=deepcopy(PROPOSAL);bad['quotes']['country']='not present'
    assert validate_proposal(b,TEXT,bad,dataset='synthetic_text',licence='synthetic',mode='llm')[1]==['field_not_supported_by_quote:country']


def test_off_replay_and_bundle_local_cache(setup):
    b,p=setup
    assert propose(b,TEXT,p)['reasons']==['model_provider_off']
    cached=save(b,TEXT,PROPOSAL,dataset='synthetic_text',licence='synthetic')
    a=propose(b,TEXT,p,provider='replay',replay_path=cached)
    assert a['accepted'] and a['proposal']==PROPOSAL
    assert propose(get_bundle('test-other'),TEXT,p,provider='replay',replay_path=cached)['accepted'] is False
    assert not captures(b)  # proposing cannot import/approve
    cached.write_text(cached.read_text().replace('Synthetic Alpha','forged'))
    assert not propose(b,TEXT,p,provider='replay',replay_path=cached)['accepted']


def test_live_policy_before_transport_and_explicit_revocation(setup,monkeypatch):
    b,p=setup;calls=[]
    monkeypatch.setattr('nightdesk.llm.client._send',lambda text: calls.append(text) or PROPOSAL)
    assert propose(b,TEXT,p,provider='mistral')['reasons']==['bundle_external_processing_disabled']
    monkeypatch.setenv('EXTERNAL_PROCESSING_ALLOWED','true')
    assert not propose(b,TEXT,p,provider='mistral')['accepted'] and not calls
    consent(b,'Synthetic person',allow=True)
    assert propose(b,TEXT,p,provider='mistral')['reasons']==['mapping_confirmation_required']
    confirm_mapping(p,b,'Synthetic person')
    assert propose(b,TEXT,p,provider='mistral')['accepted'] and calls==[TEXT]
    consent(b,'Synthetic person',allow=False)
    assert not propose(b,TEXT,p,provider='mistral')['accepted'] and len(calls)==1
    assert not captures(b)


def test_dataset_default_false_and_nda_requires_consent(setup,monkeypatch):
    b,p=setup;p.write_text(p.read_text().replace('external_processing_allowed: true\n',''))
    consent(b,'Synthetic person',allow=True)
    monkeypatch.setattr('nightdesk.llm.client._send',lambda text: pytest.fail('must not call'))
    assert propose(b,TEXT,p,provider='mistral')['reasons']==['dataset_external_processing_disabled']
    b=get_bundle('es');p.write_text(p.read_text().replace('complete: false','external_processing_allowed: true\ncomplete: false'))
    confirm_mapping(p,b,'Synthetic person')
    assert propose(b,TEXT,p,provider='mistral')['reasons']==['bundle_external_processing_disabled']
    assert submit_text(b,TEXT,PROPOSAL,p,actor='Synthetic person')['accepted']==1


def test_mistral_https_fixed_host_json_and_no_redirect(setup,monkeypatch):
    b,p=setup;consent(b,'Synthetic person',allow=True);confirm_mapping(p,b,'Synthetic person')
    calls=[];monkeypatch.setenv('MISTRAL_API_KEY','synthetic-placeholder')
    class Response:
        status=200
        def read(self,n):return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(PROPOSAL)}}]}).encode()
    class Connection:
        def __init__(self,host,timeout):calls.append(('host',host,timeout))
        def request(self,method,path,body,headers):calls.append((method,path,json.loads(body),headers))
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr('http.client.HTTPSConnection',Connection)
    assert propose(b,TEXT,p,provider='mistral')['accepted']
    assert calls[0][1]=='api.mistral.ai'
    assert calls[1][0:2]==('POST','/v1/chat/completions')
    assert calls[1][2]['temperature']==0 and calls[1][2]['response_format']=={'type':'json_object'}
    Response.status=302;calls.clear()
    assert propose(b,TEXT,p,provider='mistral')['reasons']==['mistral_http_request_refused']
    assert len(calls)==2  # no redirect request
    assert 'synthetic-placeholder' not in '\n'.join(e.model_dump_json() for e in read_events(b))


def test_manual_form_and_cli_without_keys(setup,monkeypatch,capsys):
    b,p=setup
    from nightdesk.cli import main
    notice=Path('notice.txt');notice.write_text(TEXT)
    proposal=Path('proposal.json');proposal.write_text(json.dumps(PROPOSAL))
    assert main(['text','propose',str(notice),'--mapping',str(p)])==1
    assert 'model_provider_off' in capsys.readouterr().out
    assert main(['text','import',str(notice),'--mapping',str(p),'--proposal',str(proposal),'--actor','Synthetic person'])==0
    assert main(['consent','--allow','mistral','--actor','Synthetic person'])==0
    assert read_events(b)[-1].payload['actor']=='Synthetic person'
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_string('''from nightdesk.ui.app import render_text_intake
from nightdesk.config import get_bundle
render_text_intake(get_bundle('practice'), 'Synthetic reviewer', lambda x: 'text-'+x)
''')
    app.run()
    next(x for x in app.text_input if x.label=='Text dataset mapping').set_value(str(p))
    next(x for x in app.text_area if x.label=='Source notice text').set_value(TEXT)
    next(x for x in app.text_area if x.label=='Work fields JSON (manual or proposed)').set_value(json.dumps(FIELDS))
    next(x for x in app.text_area if x.label=='Exact source quotes JSON, keyed by field').set_value(json.dumps(PROPOSAL['quotes']))
    next(x for x in app.button if x.label=='Check and import this work locally').click().run()
    assert not app.exception and not app.error
    assert len(captures(b))==2  # explicit different actor retained as evidence
