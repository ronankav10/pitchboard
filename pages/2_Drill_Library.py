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
ZONES_WITH_DRILLS = [z for z in ZONES if any(d["c"] == z for d in DRILL_LIBRARY)]

st.markdown("## 🖼️ Drill library")

c1, c2 = st.columns([1, 2])
with c1:
    zone = st.selectbox("Category", ["All"] + ZONES_WITH_DRILLS)
with c2:
    query = st.text_input("Search by name", placeholder="e.g. rondo, 8 v 8, warm up")

drills = DRILL_LIBRARY
if zone != "All":
    drills = [d for d in drills if d["c"] == zone]
if query:
    q = query.lower()
    drills = [d for d in drills if q in d["n"].lower() or q in (d.get("s") or "").lower()]

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
            st.caption(label)

if shown < len(drills):
    if st.button(f"Show more ({len(drills) - shown} remaining)"):
        st.session_state.drill_lib_shown += PAGE_SIZE
        st.rerun()
