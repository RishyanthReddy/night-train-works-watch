"""Regressions for Phase2 R1 findings, synthetic inputs and mocked transport."""
from copy import deepcopy
from datetime import date, timedelta
import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile
import pytest
from nightdesk.audit import read_events
from nightdesk.config import get_bundle
from nightdesk.intake.mapping import captures, confirm_mapping
from nightdesk.intake.text import text_guard, submit_text, validate_proposal
from nightdesk.llm.client import propose, consent
from test_text import setup, TEXT, PROPOSAL
from test_gtfs import feed
from test_phase1_council import workspace, load, edit


@pytest.mark.parametrize('key',['synthetic-secret\n','synthetic-secret\r','synthetic secret','synthetic-é'])
def test_invalid_key_never_reaches_transport_audit_or_output(setup,monkeypatch,key,capsys):
    b,p=setup;consent(b,'Synthetic reviewer',allow=True);confirm_mapping(p,b,'Synthetic reviewer')
    monkeypatch.setenv('MISTRAL_API_KEY',key)
    monkeypatch.setattr('http.client.HTTPSConnection',lambda *a,**k: pytest.fail('no connection'))
    result=propose(b,TEXT,p,provider='mistral')
    assert result['reasons']==['mistral_key_invalid_format']
    assert key not in json.dumps(result) and 'synthetic-secret' not in '\n'.join(e.model_dump_json() for e in read_events(b))
    assert not captures(b)


@pytest.mark.parametrize('body',[None,{}, {'choices':[None]}, {'choices':[{'message':None}]}, {'choices':[]}])
def test_malformed_live_envelope_refused(setup,monkeypatch,body):
    b,p=setup;consent(b,'Synthetic reviewer',allow=True);confirm_mapping(p,b,'Synthetic reviewer')
    monkeypatch.setenv('MISTRAL_API_KEY','synthetic-placeholder')
    class Response:
        status=200
        def read(self,n):return json.dumps(body).encode()
    class Connection:
        def __init__(self,*args,**kwargs):pass
        def request(self,*args,**kwargs):pass
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr('http.client.HTTPSConnection',Connection)
    assert propose(b,TEXT,p,provider='mistral')['reasons']==['mistral_transport_or_response_invalid']
    assert read_events(b)[-1].kind=='text_request_refused'


def test_transport_exception_message_is_never_audited(setup,monkeypatch):
    b,p=setup;consent(b,'Synthetic reviewer',allow=True);confirm_mapping(p,b,'Synthetic reviewer')
    monkeypatch.setattr('nightdesk.llm.client._send',lambda text: (_ for _ in ()).throw(ValueError('arbitrary synthetic secret')))
    result=propose(b,TEXT,p,provider='mistral')
    assert result['reasons']==['text_input_or_response_invalid']
    assert 'arbitrary synthetic secret' not in '\n'.join(e.model_dump_json() for e in read_events(b))


@pytest.mark.parametrize('proposal',[None,'synthetic non-object',[],{'fields':[],'quotes':{}},{}])
def test_malformed_replay_visible_without_ui_exception(setup,proposal):
    from streamlit.testing.v1 import AppTest
    b,p=setup;path=Path('bad.json')
    body=dict(version=1,source_text=TEXT,dataset='synthetic_text',licence='synthetic')
    if proposal is not None:body['proposal']=proposal
    path.write_text(json.dumps(body))
    result=propose(b,TEXT,p,provider='replay',replay_path=path)
    assert result['proposal'] is None and result['reasons']==['replay_proposal_invalid']
    app=AppTest.from_string("from nightdesk.ui.app import render_text_intake\nfrom nightdesk.config import get_bundle\nrender_text_intake(get_bundle('practice'),'Synthetic reviewer',lambda x:'mal-'+x)").run()
    next(x for x in app.text_input if x.label=='Notice mapping (YAML)').set_value(str(p))
    next(x for x in app.text_input if x.label=='Recorded example file (local)').set_value(str(path))
    next(x for x in app.text_area if x.label=='Notice text').set_value(TEXT)
    next(x for x in app.selectbox if x.label=='Who drafts the fields').select('replay')
    next(x for x in app.button if x.label=='Draft the fields only').click().run()
    assert not app.exception and any('replay_proposal_invalid' in e.value for e in app.error)
    assert read_events(b)[-1].kind=='text_request_refused' and not captures(b)


@pytest.mark.parametrize('marker',['ignore  previous instructions','ignore\u200b previous instructions','ignore\nprevious instructions','Ignore the previous instructions','disregard prior instructions','SYSTEM :','<|im_start|>system'])
def test_injection_normalization_before_transport(setup,monkeypatch,marker):
    b,p=setup;monkeypatch.setattr('nightdesk.llm.client._send',lambda t:pytest.fail('must not send'))
    assert propose(b,TEXT+'\n'+marker,p,provider='mistral')['reasons']==['text_addresses_model']


def test_mapping_timezone_and_drafting_proof(setup):
    b,p=setup;proposal=deepcopy(PROPOSAL);proposal['fields'].pop('timezone');proposal['quotes'].pop('timezone')
    result=submit_text(b,TEXT,proposal,p,actor='Synthetic reviewer',mode='replay')
    assert result['accepted']==1
    row=captures(b)[0]['typed_rows'][0]
    assert row.timezone=='Europe/Brussels' and row.proposed_by=='llm'
    assert row.extra['drafted_by']=='replay' and row.extra['reviewed_by']=='Synthetic reviewer'
    assert row.extra['timezone_basis']=='declared_mapping'


@pytest.mark.parametrize('declaration',['Month: December','Month December','Month - December'])
def test_declared_month_inside_range_and_contradiction(setup,declaration):
    b,_=setup;p=deepcopy(PROPOSAL);text=TEXT.replace('2026-11-18','2027-01-05');p['fields']['date_end']='2027-01-05';p['quotes']['date_end']='2027-01-05'
    assert validate_proposal(b,text+'\n'+declaration,p,dataset='synthetic_text',licence='synthetic',mode='manual')[0]
    assert validate_proposal(b,TEXT+'\n'+declaration,PROPOSAL,dataset='synthetic_text',licence='synthetic',mode='manual')[1]==['month_contradicts_dates']


@pytest.mark.parametrize('n',[100,400])
def test_gtfs_calendar_evidence_parsing_linear(tmp_path,monkeypatch,n):
    import nightdesk.adapters.gtfs as gtfs
    monkeypatch.chdir(tmp_path)
    def change(tables):
        service=list(csv.DictReader(io.StringIO(tables['calendar_dates.txt'])))[0]['service_id']
        tables['calendar_dates.txt']='service_id,date,exception_type\n'+''.join(f'{service},{date(2026,1,1)+timedelta(days=i):%Y%m%d},1\n' for i in range(n))
    path=feed(tmp_path,change);original=gtfs._day;calls=[]
    def counted(raw):calls.append(raw);return original(raw)
    monkeypatch.setattr(gtfs,'_day',counted)
    rows,_=gtfs.normalized_rows(path,get_bundle('practice'),namespace='syn',licence='synthetic')
    assert len(rows)==11*n and len(calls)<=2*n
    assert all(len(r['gtfs_evidence']['calendar_exception'])==1 for r in rows)


def test_gtfs_frequency_expansion_limit_and_parser_refusal(tmp_path,monkeypatch):
    import nightdesk.adapters.gtfs as gtfs
    monkeypatch.chdir(tmp_path);b=get_bundle('practice')
    p=feed(tmp_path);monkeypatch.setattr(gtfs,'MAX_GTFS_ROWS',10)
    with pytest.raises(ValueError,match='select_dates_or_trips'):gtfs.import_gtfs(p,b,actor='Synthetic',namespace='syn',licence='synthetic')
    p=feed(tmp_path,lambda t:t.update({'frequencies.txt':'trip_id,start_time,end_time,headway_secs\nES453_v1,00:00:00,23:00:00,600\n'}))
    with pytest.raises(ValueError,match='frequency_service_not_supported'):gtfs.import_gtfs(p,b,actor='Synthetic',namespace='syn',licence='synthetic')
    monkeypatch.setattr(gtfs,'MAX_GTFS_ROWS',50000)
    p=feed(tmp_path,lambda t:t.update({'stops.txt':t['stops.txt'].replace('Bruxelles-Midi','x'*140000)}))
    # Force a deterministic CSV parser field-size failure irrespective of fixture spelling.
    prior=csv.field_size_limit(5)
    try:
        with pytest.raises(ValueError,match='unreadable_archive'):gtfs.import_gtfs(p,b,actor='Synthetic',namespace='syn',licence='synthetic')
    finally:csv.field_size_limit(prior)
    assert len([e for e in read_events(b) if e.kind=='gtfs_import_refused'])==3


def test_stop_timezone_validated_but_stop_times_use_agency_zone(tmp_path,monkeypatch):
    import nightdesk.adapters.gtfs as gtfs
    monkeypatch.chdir(tmp_path)
    def zone(tables,value):
        rows=list(csv.DictReader(io.StringIO(tables['stops.txt'])))
        for row in rows:row['stop_timezone']=value
        out=io.StringIO();w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);tables['stops.txt']=out.getvalue()
    path=feed(tmp_path,lambda t:zone(t,'Europe/London'))
    rows,_=gtfs.normalized_rows(path,get_bundle('practice'),namespace='syn',licence='synthetic')
    assert rows[10]['planned_arr']=='2026-11-10T10:00:00+00:00'
    assert rows[10]['gtfs_evidence']['stop']['stop_timezone']=='Europe/London'
    path=feed(tmp_path,lambda t:zone(t,'Not/AZone'))
    with pytest.raises(ValueError,match='stop_timezone_invalid'):gtfs.normalized_rows(path,get_bundle('practice'),namespace='syn',licence='synthetic')


def test_multitrip_queue_unknown_until_explicit_choice(workspace,tmp_path):
    from nightdesk.adapters.gtfs import import_gtfs
    from nightdesk.desk import queue,dossier,run_options
    from nightdesk.export import export_dossier
    def change(tables):
        trip=tables['trips.txt'].splitlines()[1].split(',');trip[2]='ES453_v2';tables['trips.txt']+=','.join(trip)+'\n'
        tables['stop_times.txt']+='\n'.join(line.replace('ES453_v1','ES453_v2') for line in tables['stop_times.txt'].splitlines()[1:])+'\n'
        tables['calendar_dates.txt']=tables['calendar_dates.txt'].splitlines()[0]+'\nES453_v1,20261117,1\n'
    path=feed(tmp_path,change)
    imported=import_gtfs(path,workspace,actor='Synthetic reviewer',namespace='syn',licence='CC0')
    for v in ('v1','v2'):edit(Path('tests/fixtures/syn')/v/'legs.csv',train_no='syn:ES453')
    a,b=load(workspace,'v1'),load(workspace,'v2');ids=a['capture'].capture_id,b['capture'].capture_id
    rows=queue(workspace,*ids,run_capture_id=imported['capture_id'])
    row=next(r for r in rows if r['train_no']=='syn:ES453')
    assert 'run_selection_required' in row['checks_after']['unresolved']
    report=dossier(workspace,*ids,row['selection_revision'],date(2026,11,17),run_capture_id=imported['capture_id'])
    assert report['selected_run'] is None and 'run_selection_required' in report['unknowns']
    options=run_options(workspace,[imported['capture_id']]);assert len(options)==2
    chosen=[next(iter(options))]
    report=dossier(workspace,*ids,row['selection_revision'],date(2026,11,17),run_capture_id=imported['capture_id'],run_selection_ids=chosen)
    assert report['selected_run']['trip_id'] in {'ES453_v1','ES453_v2'}
    assert report['selections']['run_selection_ids']==chosen
    md,js=export_dossier(report,workspace);assert chosen[0] in js.read_text()
    with pytest.raises(ValueError,match='select_runs_from'):queue(workspace,*ids,run_capture_id=imported['capture_id'],run_selection_ids=['outside'])


def test_multitrip_full_app_exposes_explicit_choices(workspace,tmp_path):
    from nightdesk.adapters.gtfs import import_gtfs
    from streamlit.testing.v1 import AppTest
    from test_phase1_council import REPO
    def change(tables):
        trip=tables['trips.txt'].splitlines()[1].split(',');trip[2]='ES453_v2';tables['trips.txt']+=','.join(trip)+'\n'
        tables['stop_times.txt']+='\n'.join(line.replace('ES453_v1','ES453_v2') for line in tables['stop_times.txt'].splitlines()[1:])+'\n'
        tables['calendar_dates.txt']=tables['calendar_dates.txt'].splitlines()[0]+'\nES453_v1,20261117,1\n'
    imported=import_gtfs(feed(tmp_path,change),workspace,actor='Synthetic reviewer',namespace='syn',licence='CC0')
    for v in ('v1','v2'):edit(Path('tests/fixtures/syn')/v/'legs.csv',train_no='syn:ES453')
    a,b=load(workspace,'v1'),load(workspace,'v2')
    app=AppTest.from_file(str(REPO/'src/nightdesk/ui/app.py')).run()
    next(x for x in app.text_input if x.label=='Case folder').set_value(workspace.name).run()
    next(x for x in app.selectbox if x.label=='Earlier file').select(a['capture'].capture_id).run()
    next(x for x in app.selectbox if x.label=='Later file').select(b['capture'].capture_id).run()
    next(x for x in app.selectbox if x.label=='Actual run file (optional)').select(imported['capture_id']).run()
    assert not app.exception and not app.error
    selector=next(x for x in app.multiselect if x.label=='Actual run records (optional)')
    assert len([o for o in selector.options if 'ES453' in o])==2
    from nightdesk.desk import run_options
    options=run_options(workspace,[imported['capture_id']])
    selector.select(next(i for i,label in options.items() if 'ES453_v2' in label)).run()
    assert not app.exception and not app.error


def test_model_draft_origin_survives_form_import(setup):
    from streamlit.testing.v1 import AppTest
    from test_text import REPO
    b,p=setup;replay=REPO/'tests/fixtures/text/valid.json';body=json.loads(replay.read_text())
    app=AppTest.from_string("from nightdesk.ui.app import render_text_intake\nfrom nightdesk.config import get_bundle\nrender_text_intake(get_bundle('practice'),'Synthetic reviewer',lambda x:'draft-'+x)").run()
    next(x for x in app.text_input if x.label=='Notice mapping (YAML)').set_value(str(p))
    next(x for x in app.text_input if x.label=='Recorded example file (local)').set_value(str(replay))
    next(x for x in app.text_area if x.label=='Notice text').set_value(body['source_text'])
    next(x for x in app.selectbox if x.label=='Who drafts the fields').select('replay')
    next(x for x in app.button if x.label=='Draft the fields only').click().run()
    assert not app.exception and not app.error
    assert next(x for x in app.selectbox if x.label=='Who drafted this').value=='replay'
    next(x for x in app.button if x.label=='Check and add this work').click().run()
    assert not app.exception and not app.error
    row=captures(b)[0]['typed_rows'][0]
    assert row.proposed_by=='llm' and row.extra['drafted_by']=='replay'


def test_encrypted_zip_is_audited_refusal(tmp_path,monkeypatch):
    import struct
    from nightdesk.adapters.gtfs import import_gtfs
    monkeypatch.chdir(tmp_path);b=get_bundle('practice');path=feed(tmp_path);raw=bytearray(path.read_bytes())
    # Authored malformed copy: set encryption flag without decryptable contents.
    for signature,offset in [(b'PK\x03\x04',6),(b'PK\x01\x02',8)]:
        start=0
        while (index:=raw.find(signature,start))!=-1:
            flags=struct.unpack_from('<H',raw,index+offset)[0]
            struct.pack_into('<H',raw,index+offset,flags|1);start=index+len(signature)
    path.write_bytes(raw)
    with pytest.raises(ValueError,match='unreadable_archive'):import_gtfs(path,b,actor='Synthetic reviewer',namespace='syn',licence='synthetic')
    assert read_events(b)[-1].kind=='gtfs_import_refused' and not captures(b)


@pytest.mark.parametrize('field,value',[('licence',[]),('licence',{}),('dataset',[]),('dataset',{}),('source_text',[]),('bundle',{}),('version',True)])
def test_replay_metadata_types_refuse_api_ui_cli(setup,field,value):
    import subprocess
    from test_text import REPO
    from streamlit.testing.v1 import AppTest
    b,p=setup;body=dict(version=1,dataset='synthetic_text',licence='synthetic',source_text=TEXT,proposal=PROPOSAL)
    body[field]=value;path=Path('metadata.json');path.write_text(json.dumps(body));notice=Path('notice.txt');notice.write_text(TEXT)
    result=propose(b,TEXT,p,provider='replay',replay_path=path)
    assert result['proposal'] is None and result['reasons']==['replay_input_mismatch']
    assert read_events(b)[-1].kind=='text_request_refused'
    cli=subprocess.run([str(REPO/'.venv/bin/nightdesk'),'text','propose',str(notice),'--mapping',str(p),'--provider','replay','--replay',str(path)],capture_output=True,text=True)
    assert cli.returncode==1 and 'Traceback' not in cli.stderr and 'replay_input_mismatch' in cli.stdout
    app=AppTest.from_string("from nightdesk.ui.app import render_text_intake\nfrom nightdesk.config import get_bundle\nrender_text_intake(get_bundle('practice'),'Synthetic reviewer',lambda x:'metadata-'+x)").run()
    next(x for x in app.text_input if x.label=='Notice mapping (YAML)').set_value(str(p))
    next(x for x in app.text_input if x.label=='Recorded example file (local)').set_value(str(path))
    next(x for x in app.text_area if x.label=='Notice text').set_value(TEXT)
    next(x for x in app.selectbox if x.label=='Who drafts the fields').select('replay')
    next(x for x in app.button if x.label=='Draft the fields only').click().run()
    assert not app.exception and any('replay_input_mismatch' in e.value for e in app.error)
    assert read_events(b)[-1].kind=='text_request_refused' and not captures(b)


@pytest.mark.parametrize('target',['replay','model-envelope','model-content'])
def test_deep_json_becomes_audited_refusal(setup,monkeypatch,target):
    b,p=setup;deep='['*50000+'0'+']'*50000
    if target=='replay':
        path=Path('deep.json');path.write_text('{"version":1,"x":'+deep+'}')
        result=propose(b,TEXT,p,provider='replay',replay_path=path)
        assert result['reasons']==['replay_input_mismatch']
    else:
        consent(b,'Synthetic reviewer',allow=True);confirm_mapping(p,b,'Synthetic reviewer');monkeypatch.setenv('MISTRAL_API_KEY','synthetic-placeholder')
        class Response:
            status=200
            def read(self,n):
                return deep.encode() if target=='model-envelope' else json.dumps({'choices':[{'finish_reason':'stop','message':{'content':deep}}]}).encode()
        class Connection:
            def __init__(self,*a,**kw):pass
            def request(self,*a,**kw):pass
            def getresponse(self):return Response()
            def close(self):pass
        monkeypatch.setattr('http.client.HTTPSConnection',Connection)
        result=propose(b,TEXT,p,provider='mistral')
        assert result['reasons']==['mistral_transport_or_response_invalid']
    assert result['proposal'] is None and read_events(b)[-1].kind=='text_request_refused' and not captures(b)


def test_corrupt_deflate_refused_and_audited(tmp_path,monkeypatch):
    import struct
    from zipfile import ZIP_DEFLATED
    from test_gtfs import FIXTURE
    from nightdesk.adapters.gtfs import import_gtfs
    monkeypatch.chdir(tmp_path);b=get_bundle('practice');path=Path('corrupt.zip')
    with ZipFile(path,'w',compression=ZIP_DEFLATED) as archive:
        for source in FIXTURE.glob('*.txt'):archive.writestr(source.name,source.read_bytes())
    raw=bytearray(path.read_bytes());name_len,extra_len=struct.unpack_from('<HH',raw,26);start=30+name_len+extra_len
    for i in range(start,start+38):raw[i]^=0xff
    path.write_bytes(raw)
    with pytest.raises(ValueError,match='gtfs_unreadable_archive'):import_gtfs(path,b,actor='Synthetic reviewer',namespace='syn',licence='synthetic')
    assert read_events(b)[-1].kind=='gtfs_import_refused' and not captures(b)


def test_missing_timezone_provenance_says_none(setup):
    b,p=setup;p.write_text(p.read_text().replace('timezone: Europe/Brussels\n',''))
    proposal=deepcopy(PROPOSAL);proposal['fields'].pop('timezone');proposal['quotes'].pop('timezone')
    assert submit_text(b,TEXT,proposal,p,actor='Synthetic reviewer')['accepted']==1
    row=captures(b)[0]['typed_rows'][0]
    assert row.timezone is None and row.extra['timezone_basis']=='none'


@pytest.mark.parametrize('phrase',['This is a 3 month period.','Works for one month of December nights.'])
def test_ordinary_month_prose_is_not_a_declaration(setup,phrase):
    b,p=setup
    assert validate_proposal(b,TEXT+'\n'+phrase,PROPOSAL,dataset='synthetic_text',licence='synthetic',mode='manual')[0]
    assert validate_proposal(b,TEXT+'\nMonth: NotAMonth',PROPOSAL,dataset='synthetic_text',licence='synthetic',mode='manual')[1]==['declared_month_unknown']
    assert validate_proposal(b,TEXT+'\nMonth December',PROPOSAL,dataset='synthetic_text',licence='synthetic',mode='manual')[1]==['month_contradicts_dates']
