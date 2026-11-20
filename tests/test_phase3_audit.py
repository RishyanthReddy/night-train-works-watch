"""P3.4 mutate only copies, verify against a trusted earlier seal/count."""
import json
from pathlib import Path
import pytest
from nightdesk.audit import append_events,audit_path,verify,AuditError
from nightdesk.config import get_bundle
from nightdesk.cli import main


def prepared():
    b=get_bundle('test-audit-copy')
    append_events(b,[('synthetic_first',{'value':'a'}),('synthetic_middle',{'value':'b'}),('synthetic_last',{'value':'c'})])
    seal=verify(b);copy=b.root/'copies'/'tampered.jsonl';copy.parent.mkdir(parents=True)
    return b,seal,copy


@pytest.mark.parametrize('attack',['edit','middle','tail'])
def test_copy_tampering_detected_in_api_and_actual_cli(tmp_path,monkeypatch,attack):
    import subprocess
    from test_text import REPO
    monkeypatch.chdir(tmp_path);b,seal,path=prepared();original=audit_path(b).read_bytes();lines=original.decode().splitlines()
    if attack=='edit':lines[1]=lines[1].replace('"value":"b"','"value":"forged"')
    elif attack=='middle':lines.pop(1)
    else:lines.pop()
    path.write_text('\n'.join(lines)+'\n')
    with pytest.raises(AuditError):verify(b,seal=seal['hash'],count=seal['count'],copy_path=path)
    result=subprocess.run([str(REPO/'.venv/bin/nightdesk'),'audit','verify','--bundle',b.name,'--file',str(path),'--seal',seal['hash'],'--count',str(seal['count'])],text=True,capture_output=True)
    assert result.returncode==1 and 'Traceback' not in result.stderr
    assert audit_path(b).read_bytes()==original and verify(b)['hash']==seal['hash']


def test_copy_verification_requires_external_seal_and_own_bundle_path(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);b,seal,path=prepared();path.write_bytes(audit_path(b).read_bytes())
    assert verify(b,seal=seal['hash'],count=seal['count'],copy_path=path)['external_seal_checked']
    with pytest.raises(AuditError,match='trusted external'):verify(b,copy_path=path)
    foreign=get_bundle('test-foreign-copy');foreign.root.mkdir(parents=True);target=foreign.root/'audit.jsonl';target.write_bytes(path.read_bytes())
    with pytest.raises(ValueError,match='outside bundle'):verify(b,seal=seal['hash'],count=seal['count'],copy_path=target)


def test_production_app_shows_tail_copy_seal_failure(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from test_text import REPO
    monkeypatch.chdir(tmp_path);b,seal,path=prepared();raw=audit_path(b).read_bytes();path.write_text('\n'.join(raw.decode().splitlines()[:-1])+'\n')
    monkeypatch.setenv('NIGHTDESK_BUNDLE',b.name)
    app=AppTest.from_file(str(REPO/'src/nightdesk/ui/app.py')).run()
    next(x for x in app.text_input if x.label=='Saved copy of the history (optional)').set_value(str(path))
    next(x for x in app.text_input if x.label=='Seal from an earlier copy (optional)').set_value(seal['hash'])
    next(x for x in app.text_input if x.label=='Event count from that copy (optional)').set_value(str(seal['count']))
    next(x for x in app.button if x.label=='Check the history').click().run()
    assert not app.exception and any('external_seal_or_count_mismatch' in x.value for x in app.error)
    assert audit_path(b).read_bytes()==raw
