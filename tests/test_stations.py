"""Reviewed aliases resolve names without changing stored source revisions."""
import csv
from pathlib import Path
import shutil
import yaml
import pytest
from nightdesk.audit import read_events
from nightdesk.config import get_bundle
from nightdesk.match import match_work
from nightdesk.stations import import_aliases, load_aliases
from test_match import work, run
from test_phase1_council import workspace, load

ALIAS = Path(__file__).resolve().parents[1] / 'mappings/aliases/synthetic.yaml'


def table(tmp_path, rows=None):
    path = tmp_path / 'aliases.yaml'
    path.write_text(yaml.safe_dump(rows or yaml.safe_load(ALIAS.read_text())))
    return path


def test_reviewed_resolution_candidates_and_no_guessing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); b = get_bundle('practice'); p = table(tmp_path)
    identifier = import_aliases(p, b, 'Synthetic reviewer')
    resolver = load_aliases(b)
    result = resolver.resolve(' synthetic   ALPHA ')
    assert result.point_id == 'syn:a' and result.reason is None and len(result.input_refs) == 1
    assert result.evidence[0]['source'] and result.input_refs[0].bundle == 'practice'
    ambiguous = resolver.resolve('Synthetic Central')
    assert ambiguous.point_id is None and ambiguous.candidates == ('syn:a', 'syn:c') and ambiguous.reason == 'alias_ambiguous'
    assert resolver.resolve('Synthetic Alph').reason == 'alias_not_found'
    assert resolver.resolve('').point_id is None
    n = len(read_events(b)); assert import_aliases(p, b, 'Another reviewer') == identifier
    assert len(read_events(b)) == n


@pytest.mark.parametrize('update', [{'reviewed': False}, {'reviewed': 'true'}, {'source': ''}, {'point_id': 'bare'}, {'licence': ''}])
def test_unreviewed_or_unsourced_alias_row_is_refused(tmp_path, monkeypatch, update):
    monkeypatch.chdir(tmp_path); body = yaml.safe_load(ALIAS.read_text()); body['aliases'][0].update(update)
    with pytest.raises(ValueError): import_aliases(table(tmp_path, body), get_bundle('practice'), 'Synthetic reviewer')
    assert not read_events(get_bundle('practice'))


def test_tables_are_bundle_scoped_immutable_and_explicit_if_multiple(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); a, b = get_bundle('practice'), get_bundle('test-other')
    p = table(tmp_path); identifier = import_aliases(p, a, 'Synthetic reviewer')
    assert load_aliases(b).resolve('Synthetic Alpha').point_id is None
    with pytest.raises(ValueError, match='not_confirmed'): load_aliases(b, identifier)
    with pytest.raises(ValueError): import_aliases(a.root / 'aliases' / (identifier + '.json'), b, 'Synthetic reviewer')
    body = yaml.safe_load(ALIAS.read_text()); body['aliases'][0]['name'] = 'Other synthetic'
    p.write_text(yaml.safe_dump(body)); second = import_aliases(p, a, 'Synthetic reviewer')
    with pytest.raises(ValueError, match='select_one_alias_table'): load_aliases(a)
    assert load_aliases(a, identifier).resolve('Synthetic Alpha').point_id == 'syn:a'
    assert load_aliases(a, second).resolve('Synthetic Alpha').point_id is None
    target = a.root / 'aliases' / (identifier + '.json'); target.write_text(target.read_text().replace('syn:a', 'syn:z'))
    with pytest.raises(ValueError, match='hash_mismatch'): load_aliases(a, identifier)


def test_name_match_uses_reviewed_evidence_and_preserves_original(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); b = get_bundle('practice'); import_aliases(table(tmp_path), b, 'Synthetic reviewer')
    resolver = load_aliases(b)
    original = work(from_point_id=None, to_point_id=None, from_place='Synthetic Alpha', to_place='Synthetic Charlie')
    raw = original.model_dump_json(); result = match_work(original, run(), resolver=resolver)
    assert result.outcome == 'A' and result.place_resolution['from']['point_id'] == 'syn:a'
    assert all(g.passed for g in result.gate_results if g.gate in {'W4', 'W5'})
    assert 'reviewed_alias_resolution' in result.reasons
    assert len(result.input_refs) == 4 and original.model_dump_json() == raw
    ambiguous = match_work(work(from_point_id=None, from_place='Synthetic Central'), run(), resolver=resolver)
    assert ambiguous.outcome == 'B' and 'from_alias_ambiguous' in ambiguous.reasons
    assert ambiguous.place_resolution['from']['candidates'] == ['syn:a', 'syn:c']
    assert match_work(original, run()).outcome != 'A'
    with pytest.raises(ValueError, match='cross_bundle_aliases'):
        match_work(original, run(), resolver=load_aliases(get_bundle('test-other')))
    # An explicit source id takes precedence over a conflicting alias name.
    explicit = match_work(work(from_place='Synthetic Charlie'), run(), resolver=resolver)
    assert not explicit.place_resolution


def test_dossier_alias_results_equal_queue_and_export_sources(workspace):
    from nightdesk.desk import queue, dossier
    from nightdesk.export import export_dossier
    from datetime import date
    for version in ('v1', 'v2'):
        path = Path('tests/fixtures/syn') / version / 'works.csv'
        with path.open() as stream:
            reader = csv.DictReader(stream); fields = reader.fieldnames; rows = list(reader)
        rows[0].update(from_point_id='', to_point_id='')
        rows[0]['from_place'] = 'Synthetic start'; rows[0]['to_place'] = 'Synthetic end'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields + ['from_place', 'to_place']); writer.writeheader(); writer.writerows(rows)
    # Existing mapping leaves unknown columns in extra until YAML explicitly maps them.
    mapping = Path('mappings/syn_works.yaml'); body = yaml.safe_load(mapping.read_text())
    body['fields']['from_place'] = {'column': 'from_place', 'parse': 'str'}
    body['fields']['to_place'] = {'column': 'to_place', 'parse': 'str'}
    mapping.write_text(yaml.safe_dump(body))
    path = Path('aliases.yaml'); path.write_text(yaml.safe_dump({'version': 1, 'aliases': [
        dict(name='Synthetic start', point_id='syn:start', source='authored synthetic run start', licence='synthetic', reviewed=True),
        dict(name='Synthetic end', point_id='syn:end', source='authored synthetic run end', licence='synthetic', reviewed=True)]}))
    identifier = import_aliases(path, workspace, 'Synthetic reviewer')
    a, b = load(workspace, 'v1'), load(workspace, 'v2'); ids = (a['capture'].capture_id, b['capture'].capture_id)
    row = next(r for r in queue(workspace, *ids, alias_table_id=identifier) if r['train_no'] == 'aa:101')
    report = dossier(workspace, *ids, row['selection_revision'], date(2026, 11, 17), alias_table_id=identifier)
    exposure = next(e for e in report['works_exposures'] if e['outcome'] == 'A')
    assert exposure['place_resolution']['from']['point_id'] == 'syn:start'
    assert report['checks_after']['works']['A'] == row['checks_after']['works']['A'] == 1
    assert any(ref['dataset'] == 'station_aliases' for ref in exposure['input_refs'])
    assert report['selections']['alias_table_id'] == identifier
    md, js = export_dossier(report, workspace)
    assert 'station_aliases' in js.read_text() and 'station' in md.read_text()


def test_cli_alias_import_and_no_cross_bundle_lookup(tmp_path, monkeypatch, capsys):
    from nightdesk.cli import main
    monkeypatch.chdir(tmp_path); path = table(tmp_path)
    assert main(['aliases', 'import', str(path), '--actor', 'Synthetic reviewer', '--bundle', 'practice']) == 0
    assert 'confirmed alias table=' in capsys.readouterr().out
    assert load_aliases(get_bundle('practice')).resolve('Synthetic Alpha').point_id == 'syn:a'
    assert load_aliases(get_bundle('test-other')).resolve('Synthetic Alpha').point_id is None
