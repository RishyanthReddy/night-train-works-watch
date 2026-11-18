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
    assert main(['demo','check'])==0
    assert 'input references checked' in capsys.readouterr().out
    load(workspace,'v1');load(workspace,'v2')
    assert len(check_demo('mappings/demo.yaml',workspace).assets)==27
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
    # Author a new input not in the public allowlist. Even a synthetic licence is insufficient.
    from nightdesk.intake.mapping import confirm_mapping,ingest
    Path('unlisted.json').write_text('[{"country":"zz","date_start":"2026-11-17","date_end":"2026-11-18"}]')
    confirm_mapping('mappings/synthetic_text.yaml',workspace,'Synthetic tester')
    ingest('unlisted.json','mappings/synthetic_text.yaml',workspace)
    with pytest.raises(ValueError,match='not_manifest'):check_demo('mappings/demo.yaml',workspace)
