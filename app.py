"""
Pitchboard — microcycle & session planning, Streamlit edition.

Python/Streamlit rebuild of the Claude-artifact version of Pitchboard, for
running locally or deploying on Streamlit Community Cloud. See README.md
for setup, deployment, and the persistence tradeoffs of the SQLite backend
used here.
"""

import json
import os
import re
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import db
import dayrules
from constants import (
    DAY_CODES, SESSION_TYPES, ZONES, INTENSITIES,
    DAY_TYPE_INFO, GENERIC_DAY_INFO,
    parse_required_players, pitch_size_options,
)

st.set_page_config(page_title="Pitchboard", page_icon="⚽", layout="wide")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
with open(os.path.join(DATA_DIR, "drills.json")) as f:
    DRILL_LIBRARY = json.load(f)
with open(os.path.join(DATA_DIR, "drill_images_manifest.json")) as f:
    DRILL_IMAGE_MANIFEST = json.load(f)
DRILL_IMAGE_ROOT = os.path.join(DATA_DIR, "drill_images")

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
        "players": 0,
    }


def save_session_field(date_str, fixtures, **patch):
    current = db.get_session(date_str) or blank_session(date_str, fixtures)
    merged = {**current, **patch}
    db.upsert_session(
        date_str, merged["session_type"], merged["day_notes"],
        merged["blocks"], merged["load"], merged.get("day_code_override"),
        players=merged.get("players", 0),
    )


def session_duration(session):
    return sum(int(b.get("duration") or 0) for b in session.get("blocks", []))


def drills_for_zone(zone):
    return [d for d in DRILL_LIBRARY if d["c"] == zone]


_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def target_upper(target_str):
    """Top of a target range like "5.5–6.0 km" -> 6.0, or the single value
    in "80'" -> 80. None if there's no target or no number in it."""
    if not target_str:
        return None
    nums = [float(n) for n in _NUM_RE.findall(target_str)]
    return max(nums) if nums else None


def over_by_25pct(actual_str, target_str):
    """True if actual_str, parsed as a number, beats target_str's upper
    bound by 25% or more. None (not red/green, just no verdict) if either
    side doesn't parse -- an empty field or a target with no number."""
    upper = target_upper(target_str)
    if upper is None:
        return None
    try:
        actual = float(str(actual_str).strip())
    except (TypeError, ValueError):
        return None
    return actual > upper * 1.25


def render_target_note(actual_str, target_str):
    """Caption under a load field: plain grey when on/under target (or
    when there's nothing to compare), red when 25%+ over it."""
    if not target_str:
        return
    if over_by_25pct(actual_str, target_str):
        st.markdown(f":red[**{actual_str} — 25%+ over target ({target_str})**]")
    else:
        st.caption(f"target {target_str}")


def drills_for_zone_and_players(zone, players):
    """
    Drills in this zone that fit the number of players available.
    `players` <= 0 means "not set" -- no filtering, show everything.
    Returns (visible_drills, hidden_count) -- hidden_count is how many
    drills in this zone were left out because they need more players than
    are available, so the picker can say so.
    """
    all_drills = drills_for_zone(zone)
    if not players or players <= 0:
        return all_drills, 0
    visible, hidden = [], 0
    for d in all_drills:
        required = parse_required_players(d["n"])
        if required is None or required <= players:
            visible.append(d)
        else:
            hidden += 1
    return visible, hidden


# ---------------- session state defaults ----------------

if "week_start" not in st.session_state:
    st.session_state.week_start = dayrules.monday_of(date.today())
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today().isoformat()


# ---------------- sidebar ----------------

with st.sidebar:
    st.markdown("## ⚽ Pitchboard")
    st.caption("Microcycle & session planning")
    st.caption("Manage the season calendar on the **Fixtures** page (above).")

fixtures = db.list_fixtures()


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

    f1, f2, f3, f4 = st.columns([1.3, 1.1, 1.6, 1])
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
    with f4:
        st_players = st.number_input(
            "Players available", min_value=0, step=1,
            value=int(session.get("players") or 0),
            key=f"players_{sel_date_str}",
            help="Used to filter the drill-library picker below. Leave at 0 to see the whole library.",
            on_change=lambda: save_session_field(sel_date_str, fixtures, players=st.session_state[f"players_{sel_date_str}"]),
        )

    st.markdown("#### Estimated training load")
    l1, l2, l3, l4 = st.columns(4)
    load = session.get("load") or dict(EMPTY_LOAD)
    with l1:
        v_td = st.text_input("TD (km)", value=load.get("td", ""), key=f"td_{sel_date_str}",
                              on_change=lambda: save_session_field(sel_date_str, fixtures, load={**(db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures))["load"], "td": st.session_state[f"td_{sel_date_str}"]}))
        render_target_note(v_td, info.get("td"))
    with l2:
        v_hsr = st.text_input("HSR (m)", value=load.get("hsr", ""), key=f"hsr_{sel_date_str}",
                               on_change=lambda: save_session_field(sel_date_str, fixtures, load={**(db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures))["load"], "hsr": st.session_state[f"hsr_{sel_date_str}"]}))
        render_target_note(v_hsr, info.get("hsr"))
    with l3:
        v_sprint = st.text_input("Sprint distance (m)", value=load.get("sprint", ""), key=f"sprint_{sel_date_str}",
                                  on_change=lambda: save_session_field(sel_date_str, fixtures, load={**(db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures))["load"], "sprint": st.session_state[f"sprint_{sel_date_str}"]}))
        st.caption("coach estimate")
    with l4:
        v_explosive = st.text_input("Explosive distance (m)", value=load.get("explosive", ""), key=f"explosive_{sel_date_str}",
                                     on_change=lambda: save_session_field(sel_date_str, fixtures, load={**(db.get_session(sel_date_str) or blank_session(sel_date_str, fixtures))["load"], "explosive": st.session_state[f"explosive_{sel_date_str}"]}))
        st.caption("coach estimate")

    st.markdown("#### Session blocks")
    st.caption("Edit directly, or add from the picker below.")
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
        current_players = int(session.get("players") or 0)
        if current_players > 0:
            st.caption(f"Filtered to {current_players} players (set to 0 for all).")
        qa1, qa2, qa3 = st.columns([1, 2, 1])
        with qa1:
            qa_zone = st.selectbox("Category", ZONES, key=f"qa_zone_{sel_date_str}")
        options, hidden_count = drills_for_zone_and_players(qa_zone, current_players)
        with qa2:
            if options:
                qa_drill = st.selectbox(
                    "Drill", options,
                    format_func=lambda d: (
                        f"{d['s']} — {d['n']}" if d.get("s") else d["n"]
                    ) + (
                        f"  ({parse_required_players(d['n'])} players)"
                        if parse_required_players(d["n"]) is not None else ""
                    ),
                    key=f"qa_drill_{sel_date_str}_{qa_zone}_{current_players}",
                )
            else:
                qa_drill = None
                if hidden_count:
                    st.caption(f"All {hidden_count} need more players — type a name into the table instead.")
                else:
                    st.caption("No drills for this category — type one into the table.")
            if options and hidden_count:
                st.caption(f"{hidden_count} hidden (need more players).")
            if qa_drill is not None:
                required = parse_required_players(qa_drill["n"])
                sizes = pitch_size_options(required)
                if sizes:
                    size_text = " / ".join(f"{label} {dims}" for label, dims in sizes)
                    st.caption(f"Pitch size (~{required} players): {size_text}")
                image_rel = DRILL_IMAGE_MANIFEST.get(qa_drill["n"])
                if image_rel:
                    st.image(os.path.join(DRILL_IMAGE_ROOT, image_rel), width=220)
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

    st.metric("Duration", f"{dur} min")
    render_target_note(dur, info.get("duration"))
