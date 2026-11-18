"""Poisoned source text cannot import, review, alter mappings, or run actions."""
import hashlib
import json
from pathlib import Path
import pytest
from nightdesk.audit import read_events
from nightdesk.intake.mapping import captures
from nightdesk.intake.text import submit_text
from nightdesk.llm.client import propose
from nightdesk.review import record_decision, decisions
from test_text import setup, REPO

ROOT=REPO/'tests/fixtures/text'

@pytest.mark.parametrize('name,reason',[('injected','text_addresses_model'),('wrong-year','invalid_work_dates'),('month-contradiction','month_contradicts_dates')])
def test_poison_rejected_without_other_state_change(setup,name,reason):
    b,p=setup;valid=json.loads((ROOT/'valid.json').read_text())
    submit_text(b,valid['source_text'],valid['proposal'],p,actor='Synthetic person')
    identifier=captures(b)[0]['capture'].revision_ids[0]
    record_decision(b,identifier,'Synthetic reviewer','needs_clarification','Synthetic test')
    before_reviews=decisions(b);before_caps=[c['capture'].model_dump_json() for c in captures(b)]
    before_map=hashlib.sha256(p.read_bytes()).hexdigest()
    frozen={x:x.read_bytes() for x in b.root.rglob('*') if x.is_file() and x.suffix=='.json'}
    body=json.loads((ROOT/(name+'.json')).read_text())
    replay=propose(b,body['source_text'],p,provider='replay',replay_path=ROOT/(name+'.json'))
    assert not replay['accepted'] and reason in replay['reasons']
    result=submit_text(b,body['source_text'],body['proposal'],p,actor='Synthetic person')
    assert result=={'accepted':0,'rejected':1,'reasons':[reason]}
    assert decisions(b)==before_reviews and [c['capture'].model_dump_json() for c in captures(b)]==before_caps
    assert hashlib.sha256(p.read_bytes()).hexdigest()==before_map
    assert all(x.read_bytes()==raw for x,raw in frozen.items())
    assert not Path('injected-action').exists()
    assert read_events(b)[-1].payload['reasons']==[reason]


def test_replay_same_with_network_denied_and_repeated_inputs(setup):
    b,p=setup;body=json.loads((ROOT/'valid.json').read_text())
    args=(b,body['source_text'],p)
    one=propose(*args,provider='replay',replay_path=ROOT/'valid.json')
    two=propose(*args,provider='replay',replay_path=ROOT/'valid.json')
    assert one==two and one['accepted'] and not captures(b)


def test_malicious_replay_visible_in_form(setup):
    from streamlit.testing.v1 import AppTest
    b,p=setup;body=json.loads((ROOT/'injected.json').read_text())
    app=AppTest.from_string('''from nightdesk.ui.app import render_text_intake
from nightdesk.config import get_bundle
render_text_intake(get_bundle('practice'), 'Synthetic reviewer', lambda x: 'poison-'+x)
''').run()
    next(x for x in app.text_input if x.label=='Text dataset mapping').set_value(str(p))
    next(x for x in app.text_input if x.label=='Replay file (local)').set_value(str(ROOT/'injected.json'))
    next(x for x in app.text_area if x.label=='Source notice text').set_value(body['source_text'])
    next(x for x in app.selectbox if x.label=='Text proposal provider').select('replay')
    next(x for x in app.button if x.label=='Get proposal only').click().run()
    assert not app.exception and any('text_addresses_model' in x.value for x in app.error)
    assert not captures(b)
