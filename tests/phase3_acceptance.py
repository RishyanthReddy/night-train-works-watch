"""Retained authored synthetic Phase3 rehearsal; no live model/scanner requests."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from test_phase3_swap import prepare,execute,german_proposal,REPO
from test_phase3_isolation import build_pair,seed
from nightdesk.config import get_bundle,CREDENTIAL_ENV_VARS
from nightdesk.audit import audit_path,verify
from nightdesk.intake.mapping import captures


def build(root):
    prepare(root);os.chdir(root);swap=execute(root)
    # Committed public demo inputs, copied without modification for an asset check.
    for name in ('syn','text'):shutil.copytree(REPO/'tests/fixtures'/name,root/'tests/fixtures'/name)
    pair=build_pair()
    nda=seed(get_bundle('es'),'SYNTHETIC_NDA_EXERCISE_ONLY','2026-11-17 23:03')
    b=get_bundle(pair[0]['bundle']);sealed=verify(b);copy=b.root/'audit-copies'/'tail-cut.jsonl';copy.parent.mkdir()
    copy.write_text('\n'.join(audit_path(b).read_text().splitlines()[:-1])+'\n')
    return dict(swap=swap,pair=pair,nda=nda,audit=dict(bundle=b.name,copy=str(copy),seal=sealed['hash'],count=sealed['count']))


def cli(root,cases):
    env={k:v for k,v in os.environ.items() if k not in CREDENTIAL_ENV_VARS and k!='NIGHTDESK_BUNDLE'}
    def command(args,expected=0):
        cmd=['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',str(REPO/'.venv/bin/nightdesk'),*args]
        r=subprocess.run(cmd,cwd=root,env=env,text=True,capture_output=True)
        print('$ [network denied] nightdesk '+' '.join(args));print(r.stdout+r.stderr,end='');print('exit '+str(r.returncode));assert r.returncode==expected
    b=cases['swap']['bundle']
    command(['sniff','swap/path_before.csv','--delimiter',';'])
    command(['mapping','confirm','mappings/swap_paths.yaml','--actor','Synthetic reviewer','--bundle',b])
    command(['ingest','swap/path_after.csv','--mapping','mappings/swap_paths.yaml','--bundle',b])
    (root/'german-proposal.json').write_text(json.dumps(german_proposal()))
    command(['text','import','swap/notice-de.txt','--proposal','german-proposal.json','--mapping','mappings/synthetic_text.yaml','--actor','Synthetic reviewer','--bundle',b])
    cs=captures(get_bundle(b));admin={Path(c['metadata']['path']).name:c['capture'].capture_id for c in cs if c['metadata']['dataset']=='synthetic_swap_admin'}
    command(['compare','swap/admin_before.csv','swap/admin_after.csv','--old-capture',admin['admin_before.csv'],'--new-capture',admin['admin_after.csv'],'--key','ticket','--bundle',b,'--out',str(get_bundle(b).root/'cli-exports')])
    command(['text','propose','swap/notice-de.txt','--mapping','mappings/synthetic_text.yaml','--provider','mistral','--bundle','es'],1)
    audit=cases['audit']
    command(['audit','verify','--bundle',audit['bundle'],'--file',audit['copy'],'--seal',audit['seal'],'--count',str(audit['count'])],1)
    command(['audit','verify','--bundle',audit['bundle']])
    command(['demo','check'])
    print('PHASE3_ACCEPTANCE_PASS: no live model/scanner/remote; consent mocked in tests')


if __name__=='__main__':
    root=Path(tempfile.mkdtemp(prefix='nightdesk-phase3-accept-'))
    cases=build(root);cli(root,cases)
    (root/'phase3-cases.json').write_text(json.dumps(cases,indent=2))
    (REPO/'.handoff/phase3-acceptance-workspace.txt').write_text(str(root)+'\n')
    print('Retained synthetic workspace: '+str(root))
