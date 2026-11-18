"""One scenario card with assumptions and source factors visible."""

import streamlit as st

from nightdesk.co2 import ALTERNATIVES, RAIL_FACTOR, REFERENCE_YEAR, SOURCE_URL, scenario_difference_kg


def render_scenario(key):
    with st.container(border=True):
        st.subheader("Transport emissions scenario")
        st.caption("Adjust these assumptions to compare rail with another mode over the same distance.")
        left, right = st.columns(2)
        with left:
            passengers = st.number_input("Passengers · assumption", min_value=0, max_value=100_000,
                                         value=100, step=1, key=key("co2_passengers"))
            distance = st.number_input("Route distance (km) · assumption", min_value=0.0, max_value=20_000.0,
                                       value=500.0, step=10.0, key=key("co2_distance"))
        with right:
            alternative = st.selectbox("Alternative mode · assumption", tuple(ALTERNATIVES), key=key("co2_mode"))
            share = st.slider("Passengers using the alternative (%) · assumption", 0, 100, 25, key=key("co2_share"))
        difference = scenario_difference_kg(passengers, distance, share / 100, alternative)
        st.metric("Alternative minus rail for this scenario", f"{difference:,.1f} kg CO₂e")
        st.caption(f"{RAIL_FACTOR} g CO₂e per passenger-km for long-distance rail · "
                   f"{ALTERNATIVES[alternative]} for {alternative.lower()}")
        st.markdown(f"[German Environment Agency, TREMOD 6.71B · reference year {REFERENCE_YEAR}]({SOURCE_URL})")
        st.caption("German average factors. The domestic air factor includes non-CO₂ effects. "
                   "The result describes the entered scenario.")
