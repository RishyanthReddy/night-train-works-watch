import math

import pytest
from streamlit.testing.v1 import AppTest

from nightdesk.co2 import scenario_difference_kg


@pytest.mark.parametrize(("mode", "result"), [("Car", 1725), ("Domestic air", 3300), ("Long-distance coach", 50)])
def test_scenario_uses_uba_factors_and_grams_to_kg(mode, result):
    assert scenario_difference_kg(100, 500, 0.25, mode) == result
    assert scenario_difference_kg(100, 500, 0, mode) == 0


@pytest.mark.parametrize("args", [(-1, 500, 0.25, "Car"), (2.5, 500, 0.25, "Car"),
                                 (10, math.inf, 0.25, "Car"), (10, 500, 1.5, "Car"),
                                 (10, 500, 0.25, "Unknown")])
def test_scenario_refuses_invalid_assumptions(args):
    with pytest.raises(ValueError):
        scenario_difference_kg(*args)


def test_scenario_card_changes_with_assumptions():
    app = AppTest.from_string("""
from nightdesk.ui.scenario import render_scenario
render_scenario(lambda name: name)
""").run()
    assert not app.exception and app.metric[0].value == "1,725.0 kg CO₂e"
    assert any("reference year 2024" in item.value for item in app.markdown)
    app.selectbox(key="co2_mode").select("Long-distance coach")
    app.slider(key="co2_share").set_value(100).run()
    assert not app.exception and app.metric[0].value == "200.0 kg CO₂e"
