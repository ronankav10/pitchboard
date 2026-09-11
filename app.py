"""
Pitchboard — microcycle & session planning, Streamlit edition.

Python/Streamlit rebuild of the Claude-artifact version of Pitchboard, for
running locally or deploying on Streamlit Community Cloud. See README.md
for setup, deployment, and the persistence tradeoffs of the SQLite backend
used here.
"""

import json
import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import db
import dayrules
from constants import (
    DAY_CODES, SESSION_TYPES, ZONES, INTENSITIES,
    INTENSITY_FACTOR, SEASON_PHASES, DAY_TYPE_INFO, GENERIC_DAY_INFO,
)

st.set_page_config(page_title="Pitchboard", page_icon="⚽", layout="wide")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
with open(os.path.join(DATA_DIR, "drills.json")) as f:
    DRILL_LIBRARY = json.load(f)

db.init_db()
db.seed_if_empty()

BLOCK_COLUMNS = ["name", "zone", "duration", "intensity", "notes"]
EMPTY_LOAD = {"td": "", "hsr": "", "sprint": "", "explosive": ""}


# ---------------- helpers ----------------

def blank_session(date_str, fixtures):
    code, _ = dayrules.compute_day_code(date.fromisoformat(date_str), fixtures)
    return {
        "date": date_str,
        "session_type": dayrules.default_session_type(code),
        "day_notes": "",
        "blocks": [],
        "load": dict(EMPTY_LOAD),
        "day_code_override": None,
    }


def save_session_field(date_str, fixtures, **patch):
    current = db.get_session(date_str) or blank_session(date_str, fixtures)
    merged = {**current, **patch}
    db.upsert_session(
        date_str, merged["session_type"], merged["day_notes"],
        merged["blocks"], merged["load"], merged.get("day_code_override"),
    )


def session_duration(session):
    return sum(int(b.get("duration") or 0) for b in session.get("blocks", []))


def session_load(session):
    return sum(int(b.get("duration") or 0) * INTENSITY_FACTOR.get(b.get("intensity"), 0)
               for b in session.get("blocks", []))


def intensity_minutes(session):
    m = {"Low": 0, "Medium": 0, "High": 0}
    for b in session.get("blocks", []):
        if b.get("intensity") in m:
            m[b["intensity"]] += int(b.get("duration") or 0)
    return m


def drills_for_zone(zone):
    return [d for d in DRILL_LIBRARY if d["c"] == zone]


def stacked_bar_html(mins):
    total = sum(mins.values())
    colors = {"Low": "#3F8F68", "Medium": "#B97F1F", "High": "#B94433"}
    if total <= 0:
        segments = '<span style="width:100%;background:#DCD6C7"></span>'
    else:
        segments = "".join(
            f'<span style="width:{mins[k] / total * 100:.1f}%;background:{colors[k]}"></span>'
            for k in ("Low", "Medium", "High") if mins[k] > 0
        )
    return (
        '<div style="height:10px;border-radius:5px;overflow:hidden;display:flex;background:#DCD6C7;">'
        + segments + "</div>"
    )


# ---------------- session state defaults ----------------

if "week_start" not in st.session_state:
    st.session_state.week_start = dayrules.monday_of(date.today())
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today().isoformat()


# ---------------- sidebar: season phase + fixtures ----------------

with st.sidebar:
    st.markdown("## ⚽ Pitchboard")
    st.caption("Microcycle & session planning")

    phase = st.selectbox(
        "Season phase", SEASON_PHASES,
        index=SEASON_PHASES.index(db.get_meta("season_phase", "Maintain"))
        if db.get_meta("season_phase", "Maintain") in SEASON_PHASES else 1,
        key="season_phase_select",
    )
    if phase != db.get_meta("season_phase", "Maintain"):
        db.set_meta("season_phase", phase)

    st.divider()
    st.markdown("### Season fixtures")
    st.caption(
        "Add each match once — every day in the planner is labelled automatically "
        "(MD-4…MD+2) from its gap to the nearest fixture. In a congested run, taper "
        "into the next match takes priority over recovery from the last one, so "
        "recovery days get compressed or skipped — override any single day in the "
        "builder if you'd rather call it differently."
    )
    with st.form("add_fixture_form", clear_on_submit=True):
        fx_date = st.date_input("Match date", value=None, format="YYYY-MM-DD")
        fx_opponent = st.text_input("Opponent")
        fx_competition = st.text_input("Competition")
        fx_venue = st.selectbox("Venue", ["Home", "Away"])
        submitted = st.form_submit_button("Add fixture")
        if submitted and fx_date and fx_opponent:
            db.add_fixture(fx_date.isoformat(), fx_opponent, fx_competition, fx_venue)
            st.rerun()

    fixtures = db.list_fixtures()
    today_str = date.today().isoformat()
    for fxr in fixtures:
        past = fxr["date"] < today_str
        cols = st.columns([5, 1])
        with cols[0]:
            label = f"{fxr['date']} — {fxr['opponent']} ({fxr['venue']})"
            if fxr.get("competition"):
                label += f" · {fxr['competition']}"
            st.markdown(f"{'~~' if past else ''}{label}{'~~' if past else ''}")
        with cols[1]:
            if st.button("✕", key=f"del_fx_{fxr['id']}"):
                db.delete_fixture(fxr["id"])
                st.rerun()

fixtures = db.list_fixtures()  # refresh after any sidebar mutation


# ---------------- week navigation ----------------

nav_cols = st.columns([1, 3, 1, 1])
with nav_cols[0]:
    if st.button("‹ Prev week", use_container_width=True):
        st.session_state.week_start -= timedelta(days=7)
        st.rerun()
with nav_cols[1]:
    st.markdown(f"### {dayrules.fmt_week_range(st.session_state.week_start)}")
with nav_cols[2]:
    if st.button("Next week ›", use_container_width=True):
        st.session_state.week_start += timedelta(days=7)
        st.rerun()
with nav_cols[3]:
    if st.button("Today", use_container_width=True):
        st.session_state.week_start = dayrules.monday_of(date.today())
        st.session_state.selected_date = date.today().isoformat()
        st.rerun()

week_dates = dayrules.week_dates(st.session_state.week_start)
week_date_strs = [d.isoformat() for d in week_dates]
week_sessions = db.list_sessions_between(week_date_strs[0], week_date_strs[-1])

day_cols = st.columns(7)
for i, d in enumerate(week_dates):
    ds = d.isoformat()
    session = week_sessions.get(ds) or blank_session(ds, fixtures)
    code, fixture, is_auto = dayrules.effective_code(d, session, fixtures)
    dur = session_duration(session)
    is_selected = ds == st.session_state.selected_date
    with day_cols[i]:
        st.markdown(f"**{dayrules.fmt_day_header(d)}**")
        code_label = code or "—"
        if not is_auto:
            code_label += " (manual)"
        st.markdown(f"`{code_label}`")
        if fixture and code == "MD":
            st.caption(f"vs {fixture['opponent']} ({fixture['venue'][0]})")
        else:
            st.caption(session["session_type"])
        st.caption(f"{dur} min")
        if st.button("Open" if not is_selected else "● Selected", key=f"day_btn_{ds}",
                     use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state.selected_date = ds
            st.rerun()

st.divider()


# ---------------- builder ----------------

sel_date_str = st.session_state.selected_date
if sel_date_str not in week_date_strs:
    sel_date_str = week_date_strs[0]
    st.session_state.selected_date = sel_date_str
sel_date = date.fromisoformat(sel_date_str)

session = db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures)
code, fixture, is_auto = dayrules.effective_code(sel_date, session, fixtures)
info = DAY_TYPE_INFO.get(code, GENERIC_DAY_INFO)

main_col, summary_col = st.columns([3, 1])

with main_col:
    st.markdown(f"## {dayrules.fmt_day_header(sel_date)} · {code or 'General / Build day'}")

    fixture_note = ""
    if fixture:
        if code == "MD":
            fixture_note = f"Match: vs {fixture['opponent']} ({fixture['venue']}) — {fixture.get('competition') or ''}"
        elif code and code.startswith("MD-"):
            fixture_note = f"Building toward vs {fixture['opponent']} ({fixture['venue']}) on {fixture['date']}"
        elif code and code.startswith("MD+"):
            fixture_note = f"Following vs {fixture['opponent']} ({fixture['venue']}) on {fixture['date']}"
    if fixture_note:
        st.caption(fixture_note)

    f1, f2, f3 = st.columns(3)
    with f1:
        st_type = st.selectbox(
            "Session type", SESSION_TYPES,
            index=SESSION_TYPES.index(session["session_type"]) if session["session_type"] in SESSION_TYPES else 0,
            key=f"type_{sel_date_str}",
            on_change=lambda: save_session_field(sel_date_str, fixtures, session_type=st.session_state[f"type_{sel_date_str}"]),
        )
    with f2:
        override_options = [""] + DAY_CODES
        current_override = session.get("day_code_override") or ""
        st_override = st.selectbox(
            "Day type override", override_options,
            index=override_options.index(current_override) if current_override in override_options else 0,
            format_func=lambda v: "Auto (computed)" if v == "" else v,
            key=f"override_{sel_date_str}",
            on_change=lambda: save_session_field(sel_date_str, fixtures, day_code_override=(st.session_state[f"override_{sel_date_str}"] or None)),
        )
    with f3:
        st_notes = st.text_input(
            "Coaching focus", value=session["day_notes"],
            key=f"notes_{sel_date_str}",
            on_change=lambda: save_session_field(sel_date_str, fixtures, day_notes=st.session_state[f"notes_{sel_date_str}"]),
        )

    with st.expander(f"Key things to manipulate — {code or 'General'}", expanded=True):
        st.markdown(f"**{info['title']}**")
        st.write(info["aim"])
        target_fields = [
            ("Duration", info.get("duration")), ("TD", info.get("td")),
            ("HSR", info.get("hsr")), ("Mech Work", info.get("mw")),
            ("Work:Rest", info.get("work_rest")),
        ]
        target_fields = [t for t in target_fields if t[1]]
        if target_fields:
            tcols = st.columns(len(target_fields))
            for tcol, (label, value) in zip(tcols, target_fields):
                tcol.metric(label, value)
        else:
            st.caption("No fixed numeric targets for this day.")
        if info["avoid"]:
            st.markdown("**Avoid:**")
            for a in info["avoid"]:
                st.markdown(f"- {a}")
        if info["suggested_zones"]:
            st.caption("Suggested drill categories: " + ", ".join(info["suggested_zones"]))

    st.markdown("#### Estimated training load")
    l1, l2, l3, l4 = st.columns(4)
    load = session.get("load") or dict(EMPTY_LOAD)
    with l1:
        v_td = st.text_input("TD (km)", value=load.get("td", ""), key=f"td_{sel_date_str}",
                              on_change=lambda: save_session_field(sel_date_str, fixtures, load={**(db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures))["load"], "td": st.session_state[f"td_{sel_date_str}"]}))
        if info.get("td"):
            st.caption(f"target {info['td']}")
    with l2:
        v_hsr = st.text_input("HSR (m)", value=load.get("hsr", ""), key=f"hsr_{sel_date_str}",
                               on_change=lambda: save_session_field(sel_date_str, fixtures, load={**(db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures))["load"], "hsr": st.session_state[f"hsr_{sel_date_str}"]}))
        if info.get("hsr"):
            st.caption(f"target {info['hsr']}")
    with l3:
        v_sprint = st.text_input("Sprint distance (m)", value=load.get("sprint", ""), key=f"sprint_{sel_date_str}",
                                  on_change=lambda: save_session_field(sel_date_str, fixtures, load={**(db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures))["load"], "sprint": st.session_state[f"sprint_{sel_date_str}"]}))
        st.caption("coach estimate")
    with l4:
        v_explosive = st.text_input("Explosive distance (m)", value=load.get("explosive", ""), key=f"explosive_{sel_date_str}",
                                     on_change=lambda: save_session_field(sel_date_str, fixtures, load={**(db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures))["load"], "explosive": st.session_state[f"explosive_{sel_date_str}"]}))
        st.caption("coach estimate")

    st.markdown("#### Session blocks")
    st.caption(
        "Edit directly in the table — use the + row at the bottom to add a block, "
        "or the picker below to add one from your drill library."
    )
    blocks = session.get("blocks") or []
    blocks_df = pd.DataFrame(blocks, columns=BLOCK_COLUMNS) if blocks else pd.DataFrame(columns=BLOCK_COLUMNS)

    editor_version_key = f"blocks_editor_version_{sel_date_str}"
    if editor_version_key not in st.session_state:
        st.session_state[editor_version_key] = 0

    edited_df = st.data_editor(
        blocks_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"blocks_editor_{sel_date_str}_{st.session_state[editor_version_key]}",
        column_config={
            "name": st.column_config.TextColumn("Drill / block name", width="large"),
            "zone": st.column_config.SelectboxColumn("Category", options=ZONES, width="medium"),
            "duration": st.column_config.NumberColumn("Duration (min)", min_value=0, step=5, width="small"),
            "intensity": st.column_config.SelectboxColumn("Intensity", options=INTENSITIES, width="small"),
            "notes": st.column_config.TextColumn("Coaching point", width="large"),
        },
    )
    new_blocks = edited_df.fillna({"zone": "Technical", "intensity": "Medium", "duration": 0, "name": "", "notes": ""}).to_dict("records")
    for b in new_blocks:
        b["duration"] = int(b["duration"]) if str(b["duration"]).strip() != "" else 0
        if b["zone"] not in ZONES:
            b["zone"] = "Technical"
        if b["intensity"] not in INTENSITIES:
            b["intensity"] = "Medium"
    if new_blocks != blocks:
        save_session_field(sel_date_str, fixtures, blocks=new_blocks)
        session["blocks"] = new_blocks

    with st.expander("Quick add from drill library"):
        qa1, qa2, qa3 = st.columns([1, 2, 1])
        with qa1:
            qa_zone = st.selectbox("Category", ZONES, key=f"qa_zone_{sel_date_str}")
        options = drills_for_zone(qa_zone)
        with qa2:
            if options:
                qa_drill = st.selectbox(
                    "Drill", options,
                    format_func=lambda d: f"{d['s']} — {d['n']}" if d.get("s") else d["n"],
                    key=f"qa_drill_{sel_date_str}_{qa_zone}",
                )
            else:
                qa_drill = None
                st.caption("No drills in the library for this category yet — type a name straight into the table instead.")
        with qa3:
            st.write("")
            st.write("")
            if st.button("+ Add block", key=f"qa_add_{sel_date_str}", disabled=qa_drill is None):
                current = db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures)
                current["blocks"].append({
                    "name": qa_drill["n"], "zone": qa_zone, "duration": 10,
                    "intensity": "Medium", "notes": "",
                })
                save_session_field(sel_date_str, fixtures, blocks=current["blocks"])
                st.session_state[editor_version_key] += 1
                st.rerun()

with summary_col:
    st.markdown("### Session summary")
    live_session = db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures)
    dur = session_duration(live_session)
    dsl = session_load(live_session)
    mins = intensity_minutes(live_session)

    m1, m2 = st.columns(2)
    m1.metric("Duration", f"{dur} min")
    m2.metric("Dynamic Stress Load", f"{dsl} a.u.")
    st.markdown(stacked_bar_html(mins), unsafe_allow_html=True)
    st.caption("🟢 Low  🟠 Medium  🔴 High")

    st.markdown("#### Week DSL")
    chart_rows = []
    for d in week_dates:
        ds = d.isoformat()
        s = week_sessions.get(ds) or blank_session(ds, fixtures)
        if ds == sel_date_str:
            s = live_session
        chart_rows.append({"Day": d.strftime("%a"), "DSL": session_load(s)})
    chart_df = pd.DataFrame(chart_rows).set_index("Day")
    st.bar_chart(chart_df, height=200)
    st.caption("Dynamic Stress Load estimated as duration × intensity tier (2 / 4 / 7) "
               "until synced with GPS session data.")
