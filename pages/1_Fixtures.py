"""
Fixtures — season calendar management, on its own page so it's not
competing for space with the week planner.
"""

import json
import os
from datetime import date, timedelta

import streamlit as st

import db
import dayrules

st.set_page_config(page_title="Pitchboard — Fixtures", page_icon="📅", layout="wide")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
db.init_db()
db.seed_if_empty()

EMPTY_LOAD = {"td": "", "hsr": "", "sprint": "", "explosive": ""}


def set_in_off(date_str, fixtures, code, off):
    """Quick toggle used by the calendar list below -- only touches
    session_type, leaving any blocks/notes/load already on that day alone."""
    current = db.get_session(date_str)
    new_type = "Off" if off else dayrules.default_session_type(code)
    if current:
        db.upsert_session(
            date_str, new_type, current["day_notes"], current["blocks"],
            current["load"], current.get("day_code_override"),
            players=current.get("players", 0),
        )
    else:
        db.upsert_session(date_str, new_type, "", [], dict(EMPTY_LOAD), None)


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
today = date.today()
today_str = today.isoformat()

if not fixtures:
    st.info("No fixtures yet — add one above.")
else:
    played = [f for f in fixtures if f["date"] < today_str]
    upcoming = [f for f in fixtures if f["date"] >= today_str]
    st.markdown(f"**{len(upcoming)} upcoming · {len(played)} played · {len(fixtures)} total**")

    with st.expander(f"Played ({len(played)})"):
        if not played:
            st.caption("No fixtures played yet.")
        for fxr in reversed(played):
            cols = st.columns([2, 3, 2, 1])
            cols[0].markdown(f"**{fxr['date']}**")
            cols[1].markdown(fxr["opponent"])
            cols[2].markdown(fxr.get("competition") or "—")
            cols[3].markdown(fxr["venue"])

    st.markdown("#### Season calendar")
    st.caption(
        "Every day from today through the season, so you can block out days off without "
        "opening each one in the planner. Match days show automatically; \"In\" leaves a "
        "day as a normal training day (whatever the planner already has it set to)."
    )

    range_start = max(today, date.fromisoformat(min(f["date"] for f in fixtures)))
    range_end = date.fromisoformat(max(f["date"] for f in fixtures)) + timedelta(days=2)
    all_days = [range_start + timedelta(days=i) for i in range((range_end - range_start).days + 1)]

    sessions_by_date = db.list_sessions_between(range_start.isoformat(), range_end.isoformat())

    PAGE_SIZE = 30
    if "fixtures_cal_shown" not in st.session_state:
        st.session_state.fixtures_cal_shown = PAGE_SIZE
    shown = min(st.session_state.fixtures_cal_shown, len(all_days))

    for d in all_days[:shown]:
        ds = d.isoformat()
        session = sessions_by_date.get(ds)
        code, fixture, is_auto = dayrules.effective_code(d, session, fixtures)
        row = st.columns([2, 1, 3, 2])
        row[0].markdown(f"**{dayrules.fmt_day_header(d)}**")
        row[1].markdown(f"`{code or '—'}`")
        if fixture and code == "MD":
            row[2].markdown(f"Match — vs {fixture['opponent']} ({fixture['venue']})")
            if row[3].button("✕ Remove fixture", key=f"cal_del_{fixture['id']}"):
                db.delete_fixture(fixture["id"])
                st.rerun()
        else:
            current_type = (session or {}).get("session_type") or code and dayrules.default_session_type(code)
            is_off_now = current_type == "Off"
            choice = row[2].selectbox(
                "Status", ["In", "Off"], index=1 if is_off_now else 0,
                key=f"cal_status_{ds}", label_visibility="collapsed",
            )
            if (choice == "Off") != is_off_now:
                set_in_off(ds, fixtures, code, choice == "Off")
                st.rerun()

    if shown < len(all_days):
        if st.button(f"Show more days ({len(all_days) - shown} remaining)"):
            st.session_state.fixtures_cal_shown += PAGE_SIZE
            st.rerun()

st.divider()
with st.expander("Reload the official 2026-27 Serie A calendar"):
    st.caption("Replaces the list above with the full official calendar — doesn't touch the week planner.")
    if st.button("Reload from data/fixtures_2026_27.json"):
        with open(os.path.join(DATA_DIR, "fixtures_2026_27.json")) as f:
            db.replace_all_fixtures(json.load(f))
        st.rerun()
