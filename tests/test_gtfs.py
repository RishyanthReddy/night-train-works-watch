"""CC0 schedule import, authored malformed copies, and no booked-path inference."""
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile
import pytest
from nightdesk.adapters.gtfs import gtfs_instant, service_dates, normalized_rows, import_gtfs
from nightdesk.audit import read_events
from nightdesk.config import get_bundle
from nightdesk.runs import build_runs, segments

FIXTURE = Path(__file__).parent / 'fixtures/gtfs'


def feed(tmp_path, change=None):
    tables = {p.name: p.read_text() for p in FIXTURE.glob('*.txt')}
    if change: change(tables)
    target = tmp_path / 'schedule.zip'
    with ZipFile(target, 'w') as archive:
        for name, text in tables.items(): archive.writestr(name, text)
    return target


def parse(path, **kwargs):
    return normalized_rows(path, get_bundle('practice'), namespace='syn-schedule', licence='CC0', **kwargs)[0]


def test_fixture_provenance_and_past_midnight(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name, proof in json.loads((FIXTURE / 'manifest.json').read_text())['files'].items():
        p = FIXTURE / name
        assert hashlib.sha256(p.read_bytes()).hexdigest() == proof['sha256']
        assert len(list(csv.DictReader(io.StringIO(p.read_text())))) == proof['rows']
    rows = parse(feed(tmp_path))
    assert len(rows) == 22 and {r['service_date'] for r in rows} == {'2026-11-09', '2026-11-11'}
    assert rows[10]['planned_arr'] == '2026-11-10T10:00:00+00:00'
    assert rows[10]['gtfs_evidence']['stop_time']['arrival_time'] == '35:00:00'
    assert rows[0]['gtfs_evidence']['calendar_exception'] and rows[0]['gtfs_evidence']['agency']


def test_normal_pipeline_scheduled_only_and_idempotence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); path = feed(tmp_path); b = get_bundle('practice')
    args = dict(actor='Synthetic tester', namespace='syn-schedule', licence='CC0', dates=[date(2026, 11, 9)])
    from nightdesk.intake.mapping import captures
    result = import_gtfs(path, b, **args)
    assert result['accepted'] == 11 and result['rejected'] == 0 and captures(b)[0]['capture'].complete
    assert captures(b)[0]['capture'].filter['adapter_selection'] == '{"dates":["2026-11-09"],"trip_ids":null}'
    from nightdesk.intake.mapping import captures
    rows = captures(b)[0]['typed_rows']; runs = build_runs(rows)
    assert len(runs) == 1 and runs[0].path_unresolved and runs[0].kind == 'scheduled'
    assert all(r.real_arr is None and r.real_dep is None and r.line_arr is None and r.line_dep is None for r in rows)
    assert all(s.line is None for s in segments(runs[0]))
    assert rows[0].extra['gtfs_evidence']['licence'] == 'CC0'
    assert import_gtfs(path, b, **args)['capture_id'] == result['capture_id']
    assert len(captures(b)) == 1


def test_gtfs_dst_time_uses_service_noon_and_elapsed_hours():
    # GTFS specification, not a choice of a wall-clock fold.
    assert gtfs_instant(date(2026, 3, 29), '02:30:00', 'Europe/Brussels') == datetime(2026, 3, 29, 0, 30, tzinfo=timezone.utc)
    assert gtfs_instant(date(2026, 10, 25), '02:30:00', 'Europe/Brussels') == datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc)
    assert gtfs_instant(date(2026, 11, 9), '', 'Europe/Brussels') is None


def test_weekly_calendar_and_exceptions():
    calendar = [dict(service_id='s', start_date='20261109', end_date='20261115', **{k: '1' if k=='monday' else '0' for k in ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')})]
    exceptions = [dict(service_id='s', date='20261109', exception_type='2'), dict(service_id='s', date='20261111', exception_type='1')]
    assert service_dates(calendar, exceptions) == {'s': {date(2026, 11, 11)}}
    with pytest.raises(ValueError, match='duplicate'): service_dates(calendar, exceptions + exceptions)


@pytest.mark.parametrize('old,new,reason', [('35:00:00','35:99:00','invalid_gtfs_time'),('35:00:00','01:00:00','reversed_stop_times'),('prague_hl_n_main_station,11','unknown,11','invalid_stop_reference')])
def test_malformed_schedule_refused_without_capture(tmp_path, monkeypatch, old, new, reason):
    monkeypatch.chdir(tmp_path); b = get_bundle('practice')
    p = feed(tmp_path, lambda tables: tables.update({'stop_times.txt': tables['stop_times.txt'].replace(old,new)}))
    with pytest.raises(ValueError, match=reason): import_gtfs(p, b, actor='Synthetic tester', namespace='syn', licence='CC0')
    assert read_events(b)[-1].kind == 'gtfs_import_refused'
    assert not (b.root / 'captures').exists()


def test_trip_variants_never_merge_and_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    def change(tables):
        trip = tables['trips.txt'].splitlines()[1].split(','); trip[2] = 'ES453_v2'
        tables['trips.txt'] += ','.join(trip) + '\n'
        tables['stop_times.txt'] += '\n'.join(line.replace('ES453_v1','ES453_v2') for line in tables['stop_times.txt'].splitlines()[1:]) + '\n'
    p = feed(tmp_path, change)
    from nightdesk.cli import main
    assert main(['gtfs','import',str(p),'--bundle','practice','--actor','Synthetic tester','--namespace','syn','--licence','CC0','--service-date','2026-11-09']) == 0
    assert 'scheduled' in capsys.readouterr().out
    from nightdesk.intake.mapping import captures
    runs = build_runs(captures(get_bundle('practice'))[0]['typed_rows'])
    assert len(runs) == 2 and {r.trip_id for r in runs} == {'ES453_v1','ES453_v2'}


def test_foreign_bundle_input_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); a, b = get_bundle('practice'), get_bundle('test-other')
    a.root.mkdir(parents=True); p = feed(a.root)
    with pytest.raises(ValueError): normalized_rows(p, b, namespace='syn', licence='CC0')


def test_imported_gtfs_exact_endpoints_still_capped_at_b(tmp_path,monkeypatch):
    from nightdesk.match import match_work
    from nightdesk.model import WorkNotice
    from nightdesk.store import make_revision
    from nightdesk.intake.mapping import captures
    monkeypatch.chdir(tmp_path); b=get_bundle('practice');path=feed(tmp_path)
    import_gtfs(path,b,actor='Synthetic tester',namespace='syn',licence='CC0',dates=[date(2026,11,9)])
    run=build_runs(captures(b)[0]['typed_rows'])[0]
    source=run.input_refs[0].model_copy(update={'dataset':'synthetic','licence':'synthetic'})
    work=WorkNotice(work_id='authored-gtfs-test',country='zz',from_point_id=run.points[0].point_id,
        to_point_id=run.points[-1].point_id,date_start='2026-11-09',date_end='2026-11-10',
        clock_from='18:00',clock_to='12:00',recurrence='continuous',timezone='Europe/Brussels')
    revision=make_revision(b,source,work)[0]
    result=match_work(revision,run)
    assert result.outcome=='B' and 'path_unresolved' in result.reasons


def test_invalid_agency_timezone_refuses_and_is_audited(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);b=get_bundle('practice')
    path=feed(tmp_path,lambda tables: tables.update({'agency.txt':tables['agency.txt'].replace('Europe/Brussels','Synthetic/Invalid')}))
    with pytest.raises(ValueError,match='agency_timezone_invalid'):
        import_gtfs(path,b,actor='Synthetic tester',namespace='syn',licence='CC0')
    assert read_events(b)[-1].kind=='gtfs_import_refused'
