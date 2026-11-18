"""Public demo rejects undeclared/transitively restricted data before display."""
import hashlib
import json
from pathlib import Path
import shutil
import yaml
import pytest
from nightdesk.demo import check_demo
from nightdesk.config import get_bundle
from test_phase1_council import workspace,load,REPO


def manifest(tmp_path,items):
    assets=[]
    for path,licence,refs in items:
        assets.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),licence=licence,input_refs=[str(p) for p in refs]))
    p=tmp_path/'demo.yaml';p.write_text(yaml.safe_dump(dict(version=1,assets=assets)));return p


def test_current_manifest_cli_and_bundle_inputs(workspace,capsys):
    from nightdesk.cli import main
    assert main(['demo','check'])==1  # workspace has no text fixtures yet
    shutil.copytree(REPO/'tests/fixtures/text',Path('tests/fixtures/text'))
    shutil.copytree(REPO/'tests/fixtures/runs',Path('tests/fixtures/runs'))
    assert main(['demo','check'])==0
    assert 'input references checked' in capsys.readouterr().out
    load(workspace,'v1');load(workspace,'v2')
    assert len(check_demo('mappings/demo.yaml',workspace).assets)==29
    from nightdesk.config import Bundle
    with pytest.raises(ValueError,match='nda_bundle'):check_demo('mappings/demo.yaml',Bundle(workspace.name,True,workspace.root))


def test_transitive_restricted_missing_and_tampered_inputs(tmp_path):
    child=tmp_path/'private.csv';child.write_text('authored synthetic negative-test placeholder\n')
    parent=tmp_path/'report.json';parent.write_text(json.dumps({'input_refs':[{'url_or_path':str(child),'licence':'restricted'}]}))
    p=manifest(tmp_path,[(parent,'synthetic',[]),(child,'synthetic',[])])
    with pytest.raises(ValueError,match='restricted|licence_mismatch'):check_demo(p)
    parent.write_text(json.dumps({'input_refs':[str(child)]}))
    p=manifest(tmp_path,[(parent,'synthetic',[])])
    with pytest.raises(ValueError,match='not_manifest'):check_demo(p)
    p=manifest(tmp_path,[(parent,'synthetic',[]),(child,'CC0',[])])
    assert check_demo(p)
    child.write_text('changed\n')
    with pytest.raises(ValueError,match='hash_mismatch'):check_demo(p)


def test_cycles_and_unlisted_bundle_capture(workspace,tmp_path):
    a=tmp_path/'a.txt';b=tmp_path/'b.txt';a.write_text('synthetic');b.write_text('synthetic')
    with pytest.raises(ValueError,match='cycle'):check_demo(manifest(tmp_path,[(a,'synthetic',[b]),(b,'synthetic',[a])]))
    shutil.copytree(REPO/'tests/fixtures/text',Path('tests/fixtures/text'))
    shutil.copytree(REPO/'tests/fixtures/runs',Path('tests/fixtures/runs'))
    # Author a new input not in the public allowlist. Even a synthetic licence is insufficient.
    from nightdesk.intake.mapping import confirm_mapping,ingest
    Path('unlisted.json').write_text('[{"country":"zz","date_start":"2026-11-17","date_end":"2026-11-18"}]')
    confirm_mapping('mappings/synthetic_text.yaml',workspace,'Synthetic tester')
    ingest('unlisted.json','mappings/synthetic_text.yaml',workspace)
    with pytest.raises(ValueError,match='not_manifest'):check_demo('mappings/demo.yaml',workspace)


def test_public_bundle_guards_cli_ingress_and_locks_app(workspace, monkeypatch, capsys):
    from streamlit.testing.v1 import AppTest
    from nightdesk.cli import main
    from nightdesk.desk import run_options
    from nightdesk.intake.mapping import captures

    shutil.copytree(REPO/'tests/fixtures/text',Path('tests/fixtures/text'))
    shutil.copytree(REPO/'tests/fixtures/runs',Path('tests/fixtures/runs'))
    bundle = get_bundle('demo')
    manifest_path = 'tests/fixtures/syn/v1/capture.yaml'
    assert main(['capture','confirm',manifest_path,'--actor','Synthetic tester','--bundle','demo']) == 0
    assert main(['capture','import',manifest_path,'--bundle','demo']) == 0
    rule = 'mappings/infrabel_punctuality.yaml'
    assert main(['mapping','confirm',rule,'--actor','Test','--bundle','demo']) == 0
    assert main(['ingest','tests/fixtures/runs/cc0_2026.csv','--mapping',rule,'--bundle','demo']) == 0
    assert 'accepted=42 rejected=0' in capsys.readouterr().out
    existing = {item['capture'].capture_id for item in captures(bundle)}
    assert existing
    unknown = Path('unlisted.csv')
    unknown.write_text('unlisted fixture\n')
    assert main(['ingest',str(unknown),'--mapping','mappings/syn_works.yaml','--bundle','demo']) == 1
    assert 'demo_input_not_manifest_listed' in capsys.readouterr().err
    assert main(['capture','import',str(unknown),'--bundle','demo']) == 1
    assert main(['gtfs','import',str(unknown),'--namespace','syn','--licence','CC0','--actor','Test',
                 '--bundle','demo']) == 1
    assert main(['consent','--actor','Test','--allow','mistral','--bundle','demo']) == 1
    assert {item['capture'].capture_id for item in captures(bundle)} == existing
    monkeypatch.setenv('NIGHTDESK_BUNDLE', workspace.name)
    monkeypatch.setenv('NIGHTDESK_PUBLIC_DEMO', '1')
    app = AppTest.from_file(REPO/'src/nightdesk/ui/app.py', default_timeout=30).run()
    assert not app.exception
    assert all(widget.label != 'Bundle' for widget in app.text_input)
    assert any(caption.value.startswith('Public demo:') for caption in app.sidebar.caption)
    replay = app.selectbox(key='demo:demo_replay')
    replay.set_value(Path('tests/fixtures/text/injected.json').resolve())
    app.button(key='demo:demo_replay_button').click().run()
    assert not app.exception
    assert any('text_addresses_model' in error.value for error in app.error)
    real_capture = next(item['capture'].capture_id for item in captures(bundle) if item['metadata']['licence'] == 'CC0')
    app.session_state['demo:active_tab'] = 'Run evidence'
    app.selectbox(key='demo:runs').set_value(real_capture).run()
    selection, = run_options(bundle, [real_capture])
    app.selectbox(key=f'demo:source_run:{real_capture}').set_value(selection).run()
    assert not app.exception
    assert any('infrabel_punctuality · CC0' in text.value for text in app.text)
    assert any('Time basis' in item.value and 'Europe/Brussels' in item.value for item in app.text)
    assert any('Source did not declare complete coverage' in item.value for item in app.warning)
    assert any('Observed departure' in table.value.columns for table in app.dataframe)
    point_key = f'demo:clock_point:{real_capture}:{selection}'
    app.selectbox(key=point_key).select_index(1).run()
    app.session_state['demo:active_tab'] = 'CO₂ scenario'
    app.run().number_input(key='demo:co2_distance').set_value(1200.0).run()
    app.session_state['demo:active_tab'] = 'Queue'
    app.run()
    app.session_state['demo:active_tab'] = 'Run evidence'
    app.run()
    assert app.selectbox(key=f'demo:source_run:{real_capture}').value == selection
    assert app.selectbox(key=point_key).value == 1
    app.session_state['demo:active_tab'] = 'CO₂ scenario'
    app.run()
    assert app.number_input(key='demo:co2_distance').value == 1200.0
