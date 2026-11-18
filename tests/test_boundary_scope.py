"""Mixed requests must not become boundary candidates without explicit links."""
import csv
from datetime import date
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from nightdesk.audit import read_events, verify
from nightdesk.desk import queue, dossier, snapshot_revisions
from nightdesk.intake.mapping import confirm_mapping, ingest
from nightdesk.links import import_links, save_link, coverage_by_train
from nightdesk.model import JourneyLink, JourneyLinkMember
from test_phase1_council import workspace, load

DAY = date(2026, 11, 17)
APP = Path(__file__).resolve().parents[1] / 'src/nightdesk/ui/app.py'


def duplicate_anchor(sequence=1):
    for version in ('v1', 'v2'):
        path = Path('tests/fixtures/syn') / version / 'legs.csv'
        with path.open() as stream:
            reader = csv.DictReader(stream); fields = reader.fieldnames; rows = list(reader)
        rows.append(dict(rows[0], request_id='synthetic-other-request', sequence=str(sequence)))
        if version == 'v2':
            rows[1]['source_status'] = 'synthetic_changed'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def selection(bundle):
    a, b = load(bundle, 'v1'), load(bundle, 'v2')
    link = import_links(bundle, b['children']['links'])[0]
    return (a['capture'].capture_id, b['capture'].capture_id), dict(link_identifier=link, reviewed_points={'syn:border1', 'syn:border2'})


@pytest.mark.parametrize('n', [200, 800])
def test_mixed_requests_have_bounded_checks_with_or_without_selected_journey(workspace, monkeypatch, n):
    from nightdesk import desk
    template_path = Path('tests/fixtures/syn/v1/legs.csv')
    with template_path.open() as stream:
        reader = csv.DictReader(stream); fields = reader.fieldnames; templates = list(reader)[:2]
    confirm_mapping('mappings/syn_legs.yaml', workspace, 'Synthetic tester')
    captures = []
    for version in ('before', 'after'):
        path = Path(version + '.csv')
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for i in range(n // 2):
                for template, network in zip(templates, ('aa', 'bb')):
                    writer.writerow(dict(template, train_no=f'{network}:{i}', request_id=f'{network}-request-{i}',
                                          source_status=version))
        captures.append(ingest(path, 'mappings/syn_legs.yaml', workspace)['capture_id'])
    calls, scopes = [], []
    check, coverage = desk.check_boundary, desk.coverage_by_train
    def counted(*args, **kwargs):
        calls.append(args); return check(*args, **kwargs)
    def compiled(*args, **kwargs):
        scopes.append(args); return coverage(*args, **kwargs)
    monkeypatch.setattr(desk, 'check_boundary', counted)
    monkeypatch.setattr(desk, 'coverage_by_train', compiled)
    rows = queue(workspace, *captures)
    assert len(rows) == n and not calls and not scopes
    assert all(row['checks_after']['border'] == [{'result': 'unknown', 'reason': 'unlinked'}] for row in rows)
    assert queue(workspace, captures[1], captures[1]) == []
    members = [r for r in snapshot_revisions(workspace, captures[0]) if r.payload.train_no in {'aa:0', 'bb:0'}]
    link = save_link(workspace, JourneyLink(journey_id='synthetic-explicit', basis='human', confirmed_by='Synthetic tester',
        members=[JourneyLinkMember(source=r.source, journey_id='synthetic-explicit', network=r.payload.network,
                    train_no=r.payload.train_no, service_date_rule='2026-11-17') for r in members]))
    rows = queue(workspace, *captures, link_identifier=link, reviewed_points={'syn:border1'})
    assert len(calls) == 4 and len(scopes) == 2
    assert all({a.payload.train_no, b.payload.train_no} == {'aa:0', 'bb:0'} for a, b, _ in calls)
    assert {a.payload.request_id for a, _, _ in calls} != {b.payload.request_id for _, b, _ in calls}
    assert all(row['checks_after']['border'] == [{'result': 'unknown', 'reason': 'unlinked'}]
               for row in rows if row['train_no'] not in {'aa:0', 'bb:0'})


@pytest.mark.parametrize("sequence", [1, 4])
def test_competing_linked_legs_stay_unknown_until_explicit_choices(workspace, sequence):
    duplicate_anchor(sequence); ids, options = selection(workspace)
    rows = queue(workspace, *ids, **options)
    bb = next(row for row in rows if row['train_no'] == 'bb:202')
    report = dossier(workspace, *ids, bb['selection_revision'], DAY, **options)
    assert any(f['reason'] == 'ambiguous_boundary_leg' for f in report['findings'])
    assert not any(f['reason'] == 'boundary_instants_differ' for f in report['findings'])
    choices = [r.revision_id for identifier in ids for r in snapshot_revisions(workspace, identifier)
               if r.subject_type == 'path_leg' and r.payload.request_id == 'syn-request' and r.payload.sequence == 1]
    report = dossier(workspace, *ids, bb['selection_revision'], DAY, **options, boundary_revision_ids=choices)
    assert any(f['reason'] == 'boundary_instants_differ' for f in report['findings'])
    assert report['selections']['boundary_revision_ids'] == sorted(choices)
    assert read_events(workspace)[-1].payload['selections']['boundary_revision_ids'] == sorted(choices)
    assert read_events(workspace)[-1].payload['rule_versions']['boundary_scope'] == 'boundary-scope-v1'
    rows = queue(workspace, *ids, **options, boundary_revision_ids=choices)
    assert next(row for row in rows if row['train_no'] == 'bb:202')['checks_after'] == report['checks_after']
    verify(workspace)
    with pytest.raises(ValueError, match='select_boundary_legs_from_these_captures'):
        queue(workspace, *ids, **options, boundary_revision_ids=['f' * 64])
    too_many = [r.revision_id for identifier in ids for r in snapshot_revisions(workspace, identifier) if r.subject_type == 'path_leg' and r.payload.train_no == 'aa:101']
    report = dossier(workspace, *ids, bb['selection_revision'], DAY, **options, boundary_revision_ids=too_many)
    if sequence == 1:
        assert any(f['reason'] == 'ambiguous_boundary_leg' for f in report['findings'])
    else:
        assert any(f['reason'] == 'boundary_instants_differ' for f in report['findings'])


def test_explicit_link_date_rules_still_govern_candidates(workspace, monkeypatch):
    from nightdesk import desk
    ids, _ = selection(workspace)
    records = snapshot_revisions(workspace, ids[1]); legs = [r for r in records if r.subject_type == 'path_leg']
    def forbidden(*args, **kwargs): pytest.fail('No eligible linked pair for this service date')
    monkeypatch.setattr(desk, 'check_boundary', forbidden)
    for rule, expected in [('2026-11-18', 'unlinked'), ('unsupported-rule', 'unsupported_service_date_rule')]:
        link = JourneyLink(journey_id='synthetic-dates', basis='human', confirmed_by='Synthetic tester',
            members=[JourneyLinkMember(source=r.source, journey_id='synthetic-dates', network=r.payload.network,
                     train_no=r.payload.train_no, service_date_rule=rule) for r in legs])
        identifier = save_link(workspace, link)
        assert all(result == (False, expected) for result in coverage_by_train(link, DAY).values())
        rows = queue(workspace, *ids, link_identifier=identifier)
        assert all(row['checks_after']['border'] == [{'result': 'unknown', 'reason': expected}] for row in rows)


def test_app_explicit_boundary_choices_resolve_ambiguity(workspace, monkeypatch):
    duplicate_anchor(); ids, options = selection(workspace)
    monkeypatch.setenv('NIGHTDESK_BUNDLE', workspace.name)
    app = AppTest.from_file(APP).run(timeout=30)
    def select(label, value):
        next(widget for widget in app.selectbox if widget.label == label).select(value).run(timeout=30)
    select('Before capture', ids[0]); select('After capture', ids[1]); select('Journey link (optional)', options['link_identifier'])
    next(widget for widget in app.text_input if widget.label.startswith('Boundary points')).set_value('syn:border1,syn:border2').run(timeout=30)
    next(widget for widget in app.checkbox if widget.label.startswith('I reviewed')).check().run(timeout=30)
    rows = queue(workspace, *ids, **options); bb = next(row for row in rows if row['train_no'] == 'bb:202')
    select('Open train/date', (bb['selection_revision'], DAY.isoformat()))
    assert not app.exception and any('Boundary source leg choice needed' in warning.value for warning in app.warning)
    choices = [r.revision_id for identifier in ids for r in snapshot_revisions(workspace, identifier)
               if r.subject_type == 'path_leg' and r.payload.request_id == 'syn-request' and r.payload.sequence == 1]
    next(widget for widget in app.multiselect if widget.label == 'Boundary source legs (optional)').set_value(choices).run(timeout=30)
    assert not app.exception
    assert any('boundary_instants_differ' in text.value for text in app.text)
    assert not any('Boundary source leg choice needed' in warning.value for warning in app.warning)
    assert any("Both instants shown in this train’s source offset" in str(panel.value) and
               "23:01" in str(panel.value) and "23:00" in str(panel.value) and "UTC+01:00" in str(panel.value)
               for panel in app.get("html"))


def test_explicit_reentry_choices_check_both_boundaries_and_keep_excluded_unknown(workspace):
    for version in ('v1', 'v2'):
        path = Path('tests/fixtures/syn') / version / 'legs.csv'
        with path.open() as stream:
            reader = csv.DictReader(stream); fields = reader.fieldnames; rows = list(reader)
        rows[2].update(network='aa', train_no='aa:101')
        if version == 'v2':
            rows[1]['exit_time'] = '2026-11-17 23:35'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        path = Path('tests/fixtures/syn') / version / 'links.csv'
        with path.open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['journey', 'network', 'train_no', 'date_rule'])
            writer.writerows([['syn-journey', 'aa', 'aa:101', '*'], ['syn-journey', 'bb', 'bb:202', '*']])
    ids, options = selection(workspace)
    bb = next(r for r in snapshot_revisions(workspace, ids[1]) if r.subject_type == 'path_leg' and r.payload.network == 'bb')
    records = [r for identifier in ids for r in snapshot_revisions(workspace, identifier) if r.subject_type == 'path_leg']
    report = dossier(workspace, *ids, bb.revision_id, DAY, **options)
    assert all(f['reason'] == 'ambiguous_boundary_leg' for f in report['findings'])
    chosen = [r.revision_id for r in records]
    report = dossier(workspace, *ids, bb.revision_id, DAY, **options, boundary_revision_ids=chosen)
    assert len(report['findings']) == 2
    assert all(f['reason'] == 'boundary_instants_differ' for f in report['findings'])
    partial = [r.revision_id for r in records if r.payload.sequence != 3]
    report = dossier(workspace, *ids, bb.revision_id, DAY, **options, boundary_revision_ids=partial)
    assert sum(f['reason'] == 'boundary_instants_differ' for f in report['findings']) == 1
    skipped = [f for f in report['findings'] if f['reason'] == 'boundary_leg_not_selected']
    assert len(skipped) == 1 and skipped[0]['detail']['sequence'] == 3 and skipped[0]['result'] == 'unknown'
    assert 'boundary_leg_not_selected' in report['unknowns']
