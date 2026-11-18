"""P3.1: authored unseen file shapes reach sourced exports with no core edits."""
import csv
from datetime import date
import json
from pathlib import Path
import shutil
import pytest
import yaml
from openpyxl import Workbook
from nightdesk.config import get_bundle,CREDENTIAL_ENV_VARS
from nightdesk.intake.mapping import confirm_mapping,ingest,captures
from nightdesk.intake.text import submit_text
from nightdesk.cli import main
from nightdesk.desk import queue,dossier
from nightdesk.export import export_dossier,export_comparison
from nightdesk.review import record_decision
from nightdesk.generic import compare_files

REPO=Path(__file__).resolve().parents[1]


def prepare(root):
    shutil.copytree(REPO/'tests/fixtures/swap',root/'swap')
    shutil.copytree(REPO/'mappings',root/'mappings')


def german_proposal():
    fields=dict(work_id='syn-swap-work',country='zz',from_place='Synthetik Nord',to_place='Synthetik Süd',
        date_start='2026-11-17',date_end='2026-11-18',clock_from='23:00',clock_to='04:55')
    quotes={k:v for k,v in fields.items()};quotes.update(date_start='17.11.2026',date_end='18.11.2026')
    return dict(fields=fields,quotes=quotes)


def execute(root):
    b=get_bundle('test-swap')
    confirm_mapping('mappings/swap_paths.yaml',b,'Synthetic reviewer')
    old=ingest('swap/path_before.csv','mappings/swap_paths.yaml',b)
    new=ingest('swap/path_after.csv','mappings/swap_paths.yaml',b)
    old_record=captures(b)[0]['typed_rows'][0]
    assert old_record.train_no=='zz:77' and old_record.operating_dates==[date(2026,11,17)]
    assert old_record.exit.at.date()==date(2026,11,18) and old_record.extra['beleg']=='Synthetic swap source'
    assert old_record.entry.raw_time=='17.11.2026 23:00'
    # A merged spreadsheet is refused; flattening is explicit and preserves input.
    with Path('swap/path_after.csv').open() as f:rows=list(csv.reader(f,delimiter=';'))
    wb=Workbook();ws=wb.active;ws.append(['Plan']+[None]*(len(rows[0])-1));ws.merge_cells(start_row=1,start_column=1,end_row=1,end_column=len(rows[0]))
    for row in rows:ws.append(row)
    xlsx=Path('swap/merged.xlsx');wb.save(xlsx);before=xlsx.read_bytes()
    assert main(['sniff',str(xlsx)])==1
    assert main(['flatten',str(xlsx),'--header-rows','2','--out','swap/flattened.csv','--bundle',b.name])==0
    body=yaml.safe_load(Path('mappings/swap_paths.yaml').read_text());body['file']['delimiter']=','
    for spec in body['fields'].values():spec['column']='Plan_'+spec['column']
    flat_mapping=Path('mappings/swap_flattened.yaml');flat_mapping.write_text(yaml.safe_dump(body))
    confirm_mapping(flat_mapping,b,'Synthetic reviewer');assert ingest('swap/flattened.csv',flat_mapping,b)['accepted']==1
    assert xlsx.read_bytes()==before
    manual=submit_text(b,Path('swap/notice-de.txt').read_text(),german_proposal(),'mappings/synthetic_text.yaml',actor='Synthetic reviewer')
    assert manual['accepted']==1 and manual['rejected']==0
    row=queue(b,old['capture_id'],new['capture_id'])[0]
    report=dossier(b,old['capture_id'],new['capture_id'],row['selection_revision'],date(2026,11,17),works_capture_id=manual['capture_id'])
    record_decision(b,row['selection_revision'],'Synthetic reviewer','needs_clarification','Synthetic swap question')
    report=dossier(b,old['capture_id'],new['capture_id'],row['selection_revision'],date(2026,11,17),works_capture_id=manual['capture_id'])
    md,js=export_dossier(report,b)
    assert report['data_label']=='synthetic' and report['local_reviews']
    assert report['work_records'][0]['payload']['recurrence']=='unknown'
    assert '17.11.2026' in js.read_text() and report['work_records'][0]['payload']['extra']['source_text'].startswith('Synthetische')
    assert md.exists() and report['delay_request']['reason_code']=='prediction_not_validated'
    confirm_mapping('mappings/swap_admin.yaml',b,'Synthetic reviewer')
    admin=[ingest('swap/admin_'+v+'.csv','mappings/swap_admin.yaml',b) for v in ('before','after')]
    c=captures(b);by_id={x['capture'].capture_id:x for x in c}
    generic=compare_files('swap/admin_before.csv','swap/admin_after.csv',b,'ticket',old_capture=admin[0]['capture_id'],new_capture=admin[1]['capture_id'])
    gm,gj=export_comparison(generic,b,b.root/'exports')
    assert generic['counts']['changed']==1 and gm.exists() and gj.exists()
    return dict(bundle=b.name,old=old['capture_id'],new=new['capture_id'],work=manual['capture_id'],revision=row['selection_revision'])


def test_unseen_csv_merged_xlsx_german_manual_generic_end_to_end(tmp_path,monkeypatch):
    for key in CREDENTIAL_ENV_VARS:monkeypatch.delenv(key,raising=False)
    prepare(tmp_path);monkeypatch.chdir(tmp_path);execute(tmp_path)
