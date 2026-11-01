"""
Drill Library — browse the drill diagrams by category, with search.
"""

import json
import os

import streamlit as st

from constants import ZONES

st.set_page_config(page_title="Pitchboard — Drill Library", page_icon="🖼️", layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "drills.json")) as f:
    DRILL_LIBRARY = json.load(f)
with open(os.path.join(DATA_DIR, "drill_images_manifest.json")) as f:
    IMAGE_MANIFEST = json.load(f)

IMAGE_ROOT = os.path.join(DATA_DIR, "drill_images")
DRILLS_PATH = os.path.join(DATA_DIR, "drills.json")


def save_description(drill_name, text):
    """Write one drill's description back into data/drills.json. Re-reads the
    file first so two quick edits can't overwrite each other, then replaces it
    atomically. The edit is part of the repo, so it's backed up on git push."""
    with open(DRILLS_PATH) as f:
        library = json.load(f)
    for d in library:
        if d["n"] == drill_name:
            d["d"] = text.strip()
    tmp = DRILLS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(library, f, ensure_ascii=False)
    os.replace(tmp, DRILLS_PATH)
ZONES_WITH_DRILLS = [z for z in ZONES if any(d["c"] == z for d in DRILL_LIBRARY)]

st.markdown("## 🖼️ Drill library")

c1, c2 = st.columns([1, 2])
with c1:
    zone = st.selectbox("Category", ["All"] + ZONES_WITH_DRILLS)
with c2:
    query = st.text_input("Search name or description", placeholder="e.g. rondo, 8 v 8, pressing, crossing")

drills = DRILL_LIBRARY
if zone != "All":
    drills = [d for d in drills if d["c"] == zone]
if query:
    q = query.lower()
    drills = [d for d in drills if q in d["n"].lower() or q in (d.get("s") or "").lower() or q in (d.get("d") or "").lower()]

drills = sorted(drills, key=lambda d: (d["c"], d.get("s") or "", d["n"]))

st.caption(f"{len(drills)} drill{'s' if len(drills) != 1 else ''}")

PAGE_SIZE = 24
if "drill_lib_shown" not in st.session_state:
    st.session_state.drill_lib_shown = PAGE_SIZE
if query or zone != "All":
    pass  # keep whatever count is already expanded
shown = min(st.session_state.drill_lib_shown, len(drills))

cols_per_row = 4
rows = [drills[i:i + cols_per_row] for i in range(0, shown, cols_per_row)]
for row in rows:
    cols = st.columns(cols_per_row)
    for col, d in zip(cols, row):
        with col:
            rel = IMAGE_MANIFEST.get(d["n"])
            if rel:
                st.image(os.path.join(IMAGE_ROOT, rel), use_container_width=True)
            else:
                st.caption("(no image)")
            label = f"{d['s']} — {d['n']}" if d.get("s") else d["n"]
            st.markdown(f"**{label}**")
            if d.get("d"):
                st.caption(d["d"])
            with st.popover("✏️ Edit description"):
                with st.form(f"form_{d['n']}", border=False):
                    new_text = st.text_area("Description", value=d.get("d", ""), height=160)
                    if st.form_submit_button("Save", type="primary"):
                        save_description(d["n"], new_text)
                        st.toast(f"Saved: {d['n']}")
                        st.rerun()

if shown < len(drills):
    if st.button(f"Show more ({len(drills) - shown} remaining)"):
        st.session_state.drill_lib_shown += PAGE_SIZE
        st.rerun()
