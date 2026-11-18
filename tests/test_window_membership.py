"""Synthetic rolling-window evidence; restricted originals are never test fixtures."""
from datetime import datetime
from copy import deepcopy
import json
from pathlib import Path
import pytest
from nightdesk import changes
from nightdesk.audit import read_events
from nightdesk.config import get_bundle
from nightdesk.model import Capture,SourceRef,WorkNotice
from nightdesk.store import make_revision

REPO=Path(__file__).resolve().parents[1]
WINDOW={'zeitraum':{'type':'ROLLIEREND','stunden':2016}}


def comparison(tmp_path,monkeypatch,old_rows,new_rows,*,complete=True,old_at='2026-11-17T11:19:00+00:00',new_at='2026-11-18T05:24:21+00:00',window=WINDOW,licence="synthetic",source_paths=None,new_window=None,rolling_window_hours=None):
    bundle=get_bundle('test-window',out_root=tmp_path)
    records={}
    def capture(rows,side,stamp):
        ids=[]
        for row in rows:
            payload=WorkNotice(work_id=str(row['id']),country='zz',timezone=row.get('timezone','Europe/Berlin'),
                date_start=row['zeitraum']['beginn'][:10],date_end=row['zeitraum']['ende'][:10],
                extra={k:deepcopy(row[k]) for k in ('zeitraum','gueltigkeiten')})
            src=SourceRef(bundle=bundle.name,dataset='local-window',record_id=str(row['id']),capture_id=side,
                content_sha256='a'*64,captured_at=datetime.fromisoformat(stamp),url_or_path=str((source_paths or {}).get(side,'synthetic')),licence=licence)
            rev,_=make_revision(bundle,src,payload);records[rev.revision_id]=rev;ids.append(rev.revision_id)
        return Capture(capture_id=side,bundle=bundle.name,dataset='local-window',captured_at=datetime.fromisoformat(stamp),
            complete=complete,declared_complete=complete,filter=new_window if side=="new" and new_window is not None else window,revision_ids=ids)
    a,b=capture(old_rows,'old',old_at),capture(new_rows,'new',new_at)
    monkeypatch.setattr(changes,'load_revision',lambda bundle,key,reader=None:records[key])
    result=changes.compare_captures(bundle,a,b,rolling_window_hours=rolling_window_hours)
    return result,bundle,records


def row(identifier,start,end,*,period_end=None,period_start=None):
    return {'id':identifier,'zeitraum':{'beginn':start,'ende':end},'gueltigkeiten':[
        {'vonDatum':(period_start or start)[:10],'vonUhrzeit':(period_start or start)[11:],
         'bisDatum':(period_end or end)[:10],'bisUhrzeit':(period_end or end)[11:]}]}


def classes(result):
    return {x['source']['record_id']:(x['classification'],x['reason']) for x in result.membership_changes}


def test_expired_and_entering_rows_stay_visible_but_not_removed_added(tmp_path,monkeypatch):
    fixture=json.loads((REPO/'tests/fixtures/window-membership.json').read_text())
    assert fixture['data_label']=='synthetic'
    expired,entering=fixture['rows']
    live=row('synthetic-live','2026-11-17T22:00:00','2026-11-19T05:00:00')
    inside=row('synthetic-inside','2027-02-09T10:00:00','2027-02-10T05:00:00')
    result,bundle,records=comparison(tmp_path,monkeypatch,[expired,live],[entering,inside])
    assert classes(result)['synthetic-expired'][0]=='expired_out_of_window'
    assert classes(result)['synthetic-entering'][0]=='entering_window'
    assert [records[x].payload.work_id for x in result.removed]==['synthetic-live']
    assert [records[x].payload.work_id for x in result.added]==['synthetic-inside']
    assert len(result.membership_changes)==4
    audit=read_events(bundle)[-1]
    assert audit.kind=='capture_membership_checked' and audit.payload['membership_changes']==result.model_dump(mode='json')['membership_changes']


@pytest.mark.parametrize('complete',[False,True])
def test_every_period_and_inclusive_date_only_ends_are_checked(tmp_path,monkeypatch,complete):
    outer_expired=row('later-period','2026-11-17T22:00:00','2026-11-18T05:00:00',period_end='2026-11-19T05:00:00')
    date_only=row('date-only','2026-11-17T22:00:00','2026-11-18T05:00:00');date_only['gueltigkeiten'][0]['bisUhrzeit']=''
    result,_,_=comparison(tmp_path,monkeypatch,[outer_expired,date_only],[],complete=complete)
    assert all(x['classification']!='expired_out_of_window' for x in result.membership_changes)
    assert len(result.removed)==(2 if complete else 0)
    assert result.status==('compared' if complete else 'comparison_unavailable')
    if not complete:assert result.reason=='incomplete_capture'


@pytest.mark.parametrize('mutation',[lambda r:r.update(timezone=None),lambda r:r.update(gueltigkeiten=[]),
    lambda r:r['gueltigkeiten'].append({'bisDatum':'2027-01-01'}),lambda r:r['zeitraum'].update(ende='2026-11-18Tinvalid')])
@pytest.mark.parametrize('complete',[False,True])
@pytest.mark.parametrize('side',['old','new'])
def test_unproved_validity_notes_do_not_suppress_r2_presence(tmp_path,monkeypatch,mutation,complete,side):
    item=row('synthetic-unproved','2026-11-17T22:00:00','2026-11-18T05:00:00');mutation(item)
    result,_,_=comparison(tmp_path,monkeypatch,[item] if side=='old' else [],[item] if side=='new' else [],complete=complete)
    assert classes(result)['synthetic-unproved'][0]=='membership_unknown'
    assert len(result.removed if side=='old' else result.added)==int(complete)


def test_window_edge_requires_all_period_starts_and_exact_clock(tmp_path,monkeypatch):
    edge=row('edge','2027-02-09T12:19:00','2027-02-10T05:00:00')
    before=row('before','2027-02-09T12:18:59','2027-02-10T05:00:00')
    earlier_period=row('period-before','2027-02-09T22:00:00','2027-02-10T05:00:00',period_start='2027-02-08T22:00:00')
    result,_,records=comparison(tmp_path,monkeypatch,[],[edge,before,earlier_period])
    assert classes(result)['edge'][0]=='entering_window'
    assert {records[x].payload.work_id for x in result.added}=={'before','period-before'}


def test_no_rolling_filter_never_infers_entering_window(tmp_path,monkeypatch):
    result,_,_=comparison(tmp_path,monkeypatch,[],[row('future','2027-02-10T22:00:00','2027-02-11T05:00:00')],window={})
    assert len(result.added)==1 and classes(result)['future'][0]=='only_in_selected_new'


def test_local_german_snapshots_when_present(tmp_path,monkeypatch):
    """Practice only. No row content is committed, printed, exported or demoed.

    The test declares Europe/Berlin for these naive clocks, as a local mapping
    choice; it does not infer a timezone from the feed. Without that declaration
    the synthetic test above requires unknown. The missing 14th manifest never
    becomes complete or gets an invented capture timestamp.
    """
    root=REPO/'data/snapshots/de';names=['2026-11-14','2026-11-17T1119Z','2026-11-18T0524Z']
    if not all((root/n/'baustellen.json').is_file() for n in names):pytest.skip('local restricted practice captures absent; synthetic cases remain mandatory')
    raw=[{str(r['baustellenID']):r for r in json.loads((root/n/'baustellen.json').read_text())} for n in names]
    manifests=[json.loads((root/n/'manifest.json').read_text()) for n in names[1:]]
    assert all(m['complete'] is False for m in manifests)
    assert manifests[0]['revision']['baustellenDatenstand']==manifests[1]['revision']['baustellenDatenstand']
    a,b=raw[1:];shared=a.keys()&b.keys()
    assert len(shared)==44952 and all(a[k]==b[k] for k in shared)
    assert len(a.keys()-b.keys())==776 and len(b.keys()-a.keys())==456
    def minimal(rows,keys):
        return [dict(id=k,zeitraum=rows[k]['zeitraum'],gueltigkeiten=rows[k]['gueltigkeiten']) for k in sorted(keys)]
    stamp=lambda m:next(x['fetched_at'] for x in m['files'] if x['file']=='baustellen.json')
    result,_,_=comparison(tmp_path/'pair17',monkeypatch,minimal(a,a.keys()-b.keys()),minimal(b,b.keys()-a.keys()),complete=False,
        old_at=stamp(manifests[0]),new_at=stamp(manifests[1]),window=manifests[0]['filter'],licence='UNKNOWN',source_paths={'old':root/names[1]/'baustellen.json','new':root/names[2]/'baustellen.json'})
    assert result.status=='comparison_unavailable' and not result.removed and not result.added
    counts={c:sum(x['classification']==c for x in result.membership_changes) for c in ('expired_out_of_window','entering_window')}
    assert counts=={'expired_out_of_window':776,'entering_window':456}
    a,b=raw[:2];gone=a.keys()-b.keys()
    assert len(gone)==3496
    assert sum(a[k]['zeitraum']['ende'][:10]>'2026-11-18' for k in gone)==199
    # No manifest on the 14th: do not invent one. Old-only expiry needs only the
    # established newer instant. It is also the analytical reference timestamp
    # for old rows, not a claimed 14th capture instant. Old filter unknown; new
    # filter retained. R2 refuses filter mismatch, but expiry remains inspectable.
    result,_,_=comparison(tmp_path/'pair14',monkeypatch,minimal(a,gone),[],complete=False,
        old_at=stamp(manifests[0]),new_at=stamp(manifests[0]),window={},new_window=manifests[0]['filter'],licence='UNKNOWN',source_paths={'old':root/names[0]/'baustellen.json'})
    expired={x['source']['record_id'] for x in result.membership_changes if x['classification']=='expired_out_of_window'}
    assert expired and expired.isdisjoint({k for k in gone if a[k]['zeitraum']['ende'][:10]>'2026-11-18'})
    assert len(result.membership_changes)==3496 and not result.added and not result.removed


from test_phase1_council import workspace,load


def test_window_reasons_reach_real_dossier_both_exports_and_audit(workspace):
    import csv
    from datetime import date
    from nightdesk.desk import queue,dossier
    from nightdesk.export import export_dossier
    for version in ('v1','v2'):
        path=Path('tests/fixtures/syn')/version/'works.csv'
        with path.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
        rows[0]['work_id']='synthetic-expired' if version=='v1' else 'synthetic-entering'
        rows[0]['date_start']='2026-11-01' if version=='v1' else '2027-02-28'
        rows[0]['date_end']='2026-11-02' if version=='v1' else '2027-03-01'
        with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    a,b=load(workspace,'v1'),load(workspace,'v2');old,new=a['capture'].capture_id,b['capture'].capture_id
    selected=queue(workspace,old,new)[0]['selection_revision']
    report=dossier(workspace,old,new,selected,date(2026,11,17),rolling_window_hours=2016)
    for key in ('capture_comparison','work_membership_comparison'):
        compared=report[key]
        classifications={x['classification'] for x in compared['membership_changes']}
        assert {'expired_out_of_window','entering_window'}<=classifications, (key, compared['status'], compared['reason'], classifications)
        excluded={x['revision_id'] for x in compared['membership_changes'] if x['classification'] in classifications}
        assert excluded.isdisjoint(compared['removed']+compared['added'])
    md,js=export_dossier(report,workspace)
    for reason in ('expired_out_of_window','entering_window','all_validity_ended_before_capture','all_validity_starts_at_previous_window_edge'):
        assert reason in js.read_text() and reason.replace('_','\\_') in md.read_text()
    events=read_events(workspace)
    checked=next(e for e in reversed(events) if e.kind=='dossier_checked')
    assert checked.payload['capture_comparison']['membership_changes']==report['capture_comparison']['membership_changes']
    assert checked.payload['work_membership_comparison']==report['work_membership_comparison']
    assert not any('new work' in x.lower() for x in (md.read_text(),js.read_text()))


def test_unknown_old_filter_describes_expiry_but_never_infers_entering(tmp_path,monkeypatch):
    result,_,_=comparison(tmp_path,monkeypatch,
        [row('expired','2026-11-17T22:00:00','2026-11-18T05:00:00')],
        [row('future','2027-02-10T22:00:00','2027-02-11T05:00:00')],window={},new_window=WINDOW)
    assert result.status=='comparison_unavailable' and result.reason=='filter_mismatch'
    assert classes(result)['expired'][0]=='expired_out_of_window'
    assert classes(result)['future']==('membership_unknown','filter_mismatch')
    assert not result.removed and not result.added


@pytest.mark.parametrize('window,hours,expected',[
    (WINDOW,100,'rolling_window_conflict'),
    ({'roles':{'works':WINDOW}},100,'rolling_window_conflict'),
    ({'roles':{'first':WINDOW,'second':{'zeitraum':{'type':'ROLLIEREND','stunden':100}}}},100,'rolling_window_conflict'),
    (WINDOW,2016,'source_membership_only_not_publication_or_cancellation'),
    ({},100,'all_validity_starts_at_previous_window_edge'),
    ({'zeitraum':{'type':'FIXED','stunden':2016}},100,'rolling_window_conflict'),
])
def test_explicit_window_fills_absence_but_never_overrides_declarations(tmp_path,monkeypatch,window,hours,expected):
    item=row('synthetic-inside-declared','2026-11-25T22:00:00','2026-11-26T05:00:00')
    result,bundle,_=comparison(tmp_path,monkeypatch,[],[item],window=window,rolling_window_hours=hours)
    entry=result.membership_changes[0]
    assert entry['reason']==expected
    assert len(result.added)==int(entry['classification']!='entering_window')
    if expected=='rolling_window_conflict':
        assert entry['classification']=='membership_unknown' and entry['declared_windows']['old']
        assert entry['selected_window_hours']==hours
    assert read_events(bundle)[-1].payload['membership_changes']==result.model_dump(mode='json')['membership_changes']


@pytest.mark.parametrize('side,conflicting',[('old',True),('new',True),('old',False),('new',False)])
def test_ordinary_json_intake_checks_canonical_raw_consistency(tmp_path,monkeypatch,side,conflicting):
    """Real confirmation/intake/captures/comparison, no revision or clock mocks."""
    from datetime import timedelta,timezone
    import yaml
    from nightdesk.intake.mapping import confirm_mapping,ingest,captures
    monkeypatch.chdir(tmp_path);bundle=get_bundle('test-intake-validity')
    today=datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('Europe/Berlin')).date()
    first=today+timedelta(days=-2 if side=='old' else 100)
    last=first+timedelta(days=1)
    target=row('synthetic-raw-date-proof',first.isoformat()+'T22:00:00',last.isoformat()+'T05:00:00')
    raw={k:target[k] for k in ('zeitraum','gueltigkeiten')}
    work=dict(work_id=target['id'],country='zz',date_start=first.isoformat(),date_end=last.isoformat(),**raw)
    if conflicting:work['date_end' if side=='old' else 'date_start']=(today+timedelta(days=2 if side=='old' else 3)).isoformat()
    anchor=dict(work_id='synthetic-shared-anchor',country='zz',date_start=today.isoformat(),date_end=(today+timedelta(days=1)).isoformat())
    mapping=dict(version=1,dataset='synthetic-conflict',licence='synthetic',record='WorkNotice',file={'type':'json'},
        timezone='Europe/Berlin',complete=True,required=['work_id','country','date_start','date_end'],
        fields={k:{'column':k,'parse':'date:%Y-%m-%d' if k.startswith('date_') else 'str'} for k in anchor})
    Path('mapping.yaml').write_text(yaml.safe_dump(mapping));confirm_mapping('mapping.yaml',bundle,'Synthetic tester')
    for name in ('old','new'):
        Path(name+'.json').write_text(json.dumps([anchor]+([work] if name==side else [])))
        imported=ingest(name+'.json','mapping.yaml',bundle)
        assert imported['accepted']==1+int(name==side) and imported['rejected']==0
    saved={Path(c['metadata']['path']).stem:c['capture'] for c in captures(bundle)}
    result=changes.compare_captures(bundle,saved['old'],saved['new'],rolling_window_hours=2016)
    entry=result.membership_changes[0]
    assert entry['source']['licence']=='synthetic' and entry['canonical_validity']
    assert entry['validity_bounds']
    if conflicting:
        assert entry['classification']=='membership_unknown' and entry['reason']=='canonical_raw_validity_conflict'
        assert len(result.removed if side=='old' else result.added)==1
    else:
        assert entry['classification']==('expired_out_of_window' if side=='old' else 'entering_window')
        assert not result.removed and not result.added
    assert read_events(bundle)[-1].payload['membership_changes']==result.model_dump(mode='json')['membership_changes']


def test_conflicting_validity_is_retained_in_real_dossier_exports_and_audit(workspace):
    import csv,yaml
    from datetime import date
    from nightdesk.desk import queue,dossier
    from nightdesk.export import export_dossier
    mapping=Path('mappings/syn_works.yaml');spec=yaml.safe_load(mapping.read_text());spec['file']['type']='json';mapping.write_text(yaml.safe_dump(spec))
    for version in ('v1','v2'):
        folder=Path('tests/fixtures/syn')/version
        with (folder/'works.csv').open() as f:rows=list(csv.DictReader(f))
        r=rows[0];r['work_id']='synthetic-conflict-'+version
        if version=='v1':
            r.update(date_start='2026-11-17',date_end='2026-11-20',**{k:v for k,v in row('ignored','2026-11-17T22:00:00','2026-11-18T05:00:00').items() if k!='id'})
        else:
            r.update(date_start='2026-11-30',date_end='2027-03-02',**{k:v for k,v in row('ignored','2027-03-01T22:00:00','2027-03-02T05:00:00').items() if k!='id'})
        (folder/'works.json').write_text(json.dumps(rows))
        manifest=folder/'capture.yaml';body=yaml.safe_load(manifest.read_text());next(f for f in body['files'] if f['role']=='works')['path']='works.json';manifest.write_text(yaml.safe_dump(body))
    a,b=load(workspace,'v1'),load(workspace,'v2');old,new=a['capture'].capture_id,b['capture'].capture_id
    selected=queue(workspace,old,new)[0]['selection_revision']
    report=dossier(workspace,old,new,selected,date(2026,11,17),rolling_window_hours=2016)
    for key in ('capture_comparison','work_membership_comparison'):
        result=report[key];assert len(result['added'])==len(result['removed'])==1
        assert all(e['reason']=='canonical_raw_validity_conflict' for e in result['membership_changes'])
    md,js=export_dossier(report,workspace)
    assert 'canonical_raw_validity_conflict' in js.read_text() and 'canonical\\_raw\\_validity\\_conflict' in md.read_text()
    assert 'validity_bounds' in js.read_text() and 'canonical_validity' in js.read_text()
    event=next(e for e in reversed(read_events(workspace)) if e.kind=='dossier_checked')
    assert event.payload['capture_comparison']['membership_changes']==report['capture_comparison']['membership_changes']


def test_explicit_hours_also_respect_new_capture_declaration(tmp_path,monkeypatch):
    item=row('synthetic-new-policy','2026-11-25T22:00:00','2026-11-26T05:00:00')
    result,_,_=comparison(tmp_path,monkeypatch,[],[item],window={},new_window=WINDOW,rolling_window_hours=100)
    assert result.reason=='filter_mismatch' and not result.added
    entry=result.membership_changes[0]
    assert entry['classification']=='membership_unknown' and entry['reason']=='rolling_window_conflict'
    assert entry['declared_windows']['new']==[WINDOW['zeitraum']] and entry['selected_window_hours']==100
