"""
Fixtures — season calendar management, on its own page so it's not
competing for space with the week planner.
"""

import json
import os

import pandas as pd
import streamlit as st
from datetime import date

import db

st.set_page_config(page_title="Pitchboard — Fixtures", page_icon="📅", layout="wide")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
db.init_db()
db.seed_if_empty()

st.markdown("## 📅 Season fixtures")
st.caption(
    "Add each match once — days are labelled MD-4…MD+2 automatically. In a congested "
    "run, the next match takes priority over recovery from the last one; override any "
    "day manually in the planner if needed."
)

with st.form("add_fixture_form", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
    with c1:
        fx_date = st.date_input("Match date", value=None, format="YYYY-MM-DD")
    with c2:
        fx_opponent = st.text_input("Opponent")
    with c3:
        fx_competition = st.text_input("Competition", value="Serie A")
    with c4:
        fx_venue = st.selectbox("Venue", ["Home", "Away"])
    submitted = st.form_submit_button("Add fixture")
    if submitted and fx_date and fx_opponent:
        db.add_fixture(fx_date.isoformat(), fx_opponent, fx_competition, fx_venue)
        st.rerun()

st.divider()

fixtures = db.list_fixtures()
today_str = date.today().isoformat()

if not fixtures:
    st.info("No fixtures yet — add one above.")
else:
    played = [f for f in fixtures if f["date"] < today_str]
    upcoming = [f for f in fixtures if f["date"] >= today_str]

    st.markdown(f"**{len(upcoming)} upcoming · {len(played)} played · {len(fixtures)} total**")

    def fixture_table(rows, empty_msg):
        if not rows:
            st.caption(empty_msg)
            return
        for fxr in rows:
            cols = st.columns([2, 3, 2, 1, 1])
            cols[0].markdown(f"**{fxr['date']}**")
            cols[1].markdown(fxr["opponent"])
            cols[2].markdown(fxr.get("competition") or "—")
            cols[3].markdown(fxr["venue"])
            if cols[4].button("✕ Remove", key=f"del_fx_{fxr['id']}"):
                db.delete_fixture(fxr["id"])
                st.rerun()

    header = st.columns([2, 3, 2, 1, 1])
    for h, label in zip(header, ["Date", "Opponent", "Competition", "Venue", ""]):
        h.markdown(f"_{label}_")

    st.markdown("#### Upcoming")
    fixture_table(upcoming, "No upcoming fixtures.")

    st.markdown("#### Played")
    fixture_table(list(reversed(played)), "No fixtures played yet.")

st.divider()
with st.expander("Reload the official 2026-27 Serie A calendar"):
    st.caption("Replaces the list below with the full official calendar — doesn't touch the week planner.")
    if st.button("Reload from data/fixtures_2026_27.json"):
        with open(os.path.join(DATA_DIR, "fixtures_2026_27.json")) as f:
            db.replace_all_fixtures(json.load(f))
        st.rerun()
