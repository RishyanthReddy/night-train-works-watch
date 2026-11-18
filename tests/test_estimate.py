"""No numeric delay prediction, including when the caller supplies one."""
import re
from nightdesk.estimate import estimate_delay
from nightdesk.audit import read_events
from test_phase1_council import workspace, load


def test_delay_always_refuses_without_number():
    for args in ({}, {'minutes': 123, 'effect': 'closure'}, {'validated': True}):
        refusal = estimate_delay(**args)
        assert refusal.reason_code == 'prediction_not_validated'
        assert refusal.detail and refusal.what_would_fix_it
        assert not re.search(r'\d', refusal.model_dump_json())
        assert set(refusal.model_dump()) == {'reason_code','detail','what_would_fix_it'}


def test_dossier_export_and_ui_refusal(workspace):
    from datetime import date
    from nightdesk.desk import queue, dossier
    from nightdesk.export import export_dossier
    a,b = load(workspace,'v1'),load(workspace,'v2')
    ids=a['capture'].capture_id,b['capture'].capture_id
    row=queue(workspace,*ids)[0]
    report=dossier(workspace,*ids,row['selection_revision'],date.fromisoformat(row['service_date']))
    md,js=export_dossier(report,workspace)
    assert report['delay_request'] == estimate_delay().model_dump(mode='json')
    assert 'prediction' in md.read_text() and 'prediction_not_validated' in js.read_text()
    from streamlit.testing.v1 import AppTest
    # Test the same dossier renderer with actual evidence, not a mock forecast.
    app=AppTest.from_string('''import streamlit as st
from nightdesk.ui.app import render_dossier
from nightdesk.config import get_bundle
render_dossier(get_bundle('test-council'), st.session_state.report, 'Synthetic reviewer', lambda x: 'refusal-'+x)
''')
    app.session_state['report']=report;app.run(timeout=30)
    next(b for b in app.button if b.label=='Ask for a delay estimate').click().run()
    assert not app.exception and any('Delay prediction is unavailable' in w.value for w in app.warning)
    assert read_events(workspace)[-1].kind == 'delay_request_refused'
