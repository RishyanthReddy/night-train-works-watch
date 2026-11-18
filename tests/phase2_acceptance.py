"""CLI and three synthetic real-app cases, prepared in an isolated workspace."""
import csv
from datetime import date
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile
from nightdesk.config import get_bundle,CREDENTIAL_ENV_VARS
from nightdesk.desk import queue,dossier
from nightdesk.intake.batch import confirm_batch,ingest_batch
from nightdesk.links import import_links
from nightdesk.export import export_dossier

REPO=Path(__file__).resolve().parents[1]
CLI=REPO/'.venv/bin/nightdesk'


def build(root):
    shutil.copytree(REPO/'mappings',root/'mappings')
    shutil.copytree(REPO/'tests/fixtures/syn',root/'tests/fixtures/syn')
    shutil.copytree(REPO/'tests/fixtures/text',root/'tests/fixtures/text')
    shutil.copytree(REPO/'tests/fixtures/runs',root/'tests/fixtures/runs')
    os.chdir(root)
    results={}
    for name,reason in [('different','different_boundary_points'),('clock','ambiguous_local_time'),('partial','incomplete_capture')]:
        bundle=get_bundle('test-p2-'+name)
        a_path=Path('tests/fixtures/syn')/(name+'-before');b_path=Path('tests/fixtures/syn')/(name+'-after')
        shutil.copytree('tests/fixtures/syn/v1',a_path);shutil.copytree('tests/fixtures/syn/v2',b_path)
        for side,path in [('before',a_path),('after',b_path)]:
            p=path/'capture.yaml';s=p.read_text().replace('Synthetic v1','Synthetic '+name+' before').replace('Synthetic v2','Synthetic '+name+' after')
            if name=='partial' and side=='after':s=s.replace('complete: true','complete: false')
            p.write_text(s)
            if name in {'clock','different'}:
                p=path/'legs.csv'
                with p.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
                if name=='different' and side=='after':rows[0]['exit_point']='syn:different'
                if name=='clock':
                    for row in rows:
                        row['dates']='2026-10-25'
                        row['entry_time']=row['entry_time'].replace('2026-11-17','2026-10-25').replace('2026-11-18','2026-10-26')
                        row['exit_time']=row['exit_time'].replace('2026-11-17','2026-10-25').replace('2026-11-18','2026-10-26')
                    rows[0]['entry_time']='2026-10-25 01:00';rows[0]['exit_time']='2026-10-25 02:10' if side=='before' else '2026-10-25 02:30'
                    rows[1]['entry_time']='2026-10-25 02:30'
                with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        for path in (a_path,b_path):confirm_batch(path/'capture.yaml',bundle,'Synthetic reviewer')
        a,b=(ingest_batch(path/'capture.yaml',bundle) for path in (a_path,b_path))
        link=import_links(bundle,b['children']['links'])[0]
        opts=dict(link_identifier=link,reviewed_points={'syn:border1','syn:border2'})
        rows=queue(bundle,a['capture'].capture_id,b['capture'].capture_id,**opts)
        row=next(r for r in rows if r['train_no']=='aa:101')
        report=dossier(bundle,a['capture'].capture_id,b['capture'].capture_id,row['selection_revision'],date.fromisoformat(row['service_date']),**opts)
        assert report['findings'][0]['result']=='unknown' and report['findings'][0]['reason']==reason
        export_dossier(report,bundle)
        results[name]=dict(bundle=bundle.name,before=a['capture'].capture_id,after=b['capture'].capture_id,link=link,reason=reason)
        print(name+': unknown / '+reason)
    return results


def cli(root):
    env={k:v for k,v in os.environ.items() if k not in CREDENTIAL_ENV_VARS and k!='NIGHTDESK_BUNDLE'}
    def command(args,expected=0):
        cmd=['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',str(CLI),*args]
        r=subprocess.run(cmd,cwd=root,env=env,text=True,capture_output=True)
        print('$ nightdesk '+' '.join(args));print(r.stdout+r.stderr,end='');print('exit '+str(r.returncode));assert r.returncode==expected
        return r.stdout
    command(['demo','check'])
    body=json.loads((root/'tests/fixtures/text/valid.json').read_text());(root/'notice.txt').write_text(body['source_text'])
    args=['text','propose','notice.txt','--mapping','mappings/synthetic_text.yaml','--provider','replay','--replay','tests/fixtures/text/valid.json']
    one=command(args);two=command(args);assert one==two
    for name in ('injected','wrong-year','month-contradiction'):
        body=json.loads((root/('tests/fixtures/text/'+name+'.json')).read_text());(root/'notice.txt').write_text(body['source_text'])
        command(['text','propose','notice.txt','--mapping','mappings/synthetic_text.yaml','--provider','replay','--replay','tests/fixtures/text/'+name+'.json'],1)
    with ZipFile(root/'schedule.zip','w') as z:
        for p in (REPO/'tests/fixtures/gtfs').glob('*.txt'):z.write(p,p.name)
    command(['gtfs','import','schedule.zip','--actor','Synthetic reviewer','--namespace','synthetic-gtfs','--licence','CC0','--bundle','test-p2-cli'])
    print('PHASE2_ACCEPTANCE_PASS; no live model request')

if __name__=='__main__':
    root=Path(tempfile.mkdtemp(prefix='nightdesk-phase2-accept-'))
    cases=build(root);cli(root)
    (root/'phase2-cases.json').write_text(json.dumps(cases,indent=2))
    (REPO/'.handoff/phase2-acceptance-workspace.txt').write_text(str(root)+'\n')
    print('Retained synthetic workspace: '+str(root))
