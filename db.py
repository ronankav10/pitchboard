"""
SQLite persistence for Pitchboard.

Uses a single file, pitchboard.db, created next to this script. This is
deliberately simple (no server, no signup) so the app runs the moment you
`streamlit run app.py`. See README.md for the tradeoffs of this approach
when deployed to Streamlit Community Cloud.
"""

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pitchboard.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS fixtures (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    opponent TEXT NOT NULL,
    competition TEXT,
    venue TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    date TEXT PRIMARY KEY,
    session_type TEXT,
    day_notes TEXT,
    blocks TEXT,
    load TEXT,
    day_code_override TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------- fixtures ----------------

def list_fixtures():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM fixtures ORDER BY date ASC").fetchall()
        return [dict(r) for r in rows]


def add_fixture(date_str, opponent, competition, venue):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO fixtures (id, date, opponent, competition, venue) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), date_str, opponent, competition, venue),
        )


def delete_fixture(fixture_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM fixtures WHERE id = ?", (fixture_id,))


# ---------------- sessions ----------------

def get_session(date_str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE date = ?", (date_str,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["blocks"] = json.loads(d["blocks"]) if d["blocks"] else []
        d["load"] = json.loads(d["load"]) if d["load"] else {"td": "", "hsr": "", "sprint": "", "explosive": ""}
        return d


def upsert_session(date_str, session_type, day_notes, blocks, load, day_code_override):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sessions (date, session_type, day_notes, blocks, load, day_code_override)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(date) DO UPDATE SET
                session_type=excluded.session_type,
                day_notes=excluded.day_notes,
                blocks=excluded.blocks,
                load=excluded.load,
                day_code_override=excluded.day_code_override
            """,
            (date_str, session_type, day_notes, json.dumps(blocks), json.dumps(load), day_code_override),
        )


def list_sessions_between(start_str, end_str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE date >= ? AND date <= ?", (start_str, end_str)
        ).fetchall()
        out = {}
        for r in rows:
            d = dict(r)
            d["blocks"] = json.loads(d["blocks"]) if d["blocks"] else []
            d["load"] = json.loads(d["load"]) if d["load"] else {"td": "", "hsr": "", "sprint": "", "explosive": ""}
            out[d["date"]] = d
        return out


# ---------------- meta (e.g. season phase) ----------------

def get_meta(key, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_meta(key, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


# ---------------- demo seed data ----------------

def seed_if_empty():
    """Populate a realistic demo week the first time the app runs, so it's
    not a blank page. Safe to call every startup -- it's a no-op once any
    fixture exists."""
    if list_fixtures():
        return

    fixtures = [
        ("2026-09-06", "Ashfield Rovers", "Championship", "Home"),
        ("2026-09-13", "Riverside Town", "Championship", "Away"),
        ("2026-09-16", "Colchester Athletic", "League Cup", "Home"),
        ("2026-09-20", "Brackworth United", "Championship", "Away"),
    ]
    for f in fixtures:
        add_fixture(*f)

    def blk(name, zone, duration, intensity, notes=""):
        return {"id": str(uuid.uuid4())[:8], "name": name, "zone": zone, "duration": duration,
                "intensity": intensity, "notes": notes}

    demo_sessions = {
        "2026-09-07": ("Recovery", "Flush and reset — high-minute group active recovery, compensation group extended", [
            blk("Pool Recovery Session", "Recovery", 25, "Low"),
            blk("Possession Drill 22 (5 v 5)", "Possession", 20, "Medium", "Compensation group only"),
            blk("Light Mobility Circuit", "Recovery", 15, "Low"),
        ], {"td": "6.5", "hsr": "550", "sprint": "120", "explosive": "20"}),
        "2026-09-08": ("Off", "Full rest — no scheduled activity", [], {"td": "", "hsr": "", "sprint": "", "explosive": ""}),
        "2026-09-09": ("Strength & Power", "General strength base — trap bar focus", [
            blk("Strength Warm Up 4", "Warm Up", 12, "Low"),
            blk("Strength Conditioning 5", "Conditioning", 25, "High", "Trap bar deadlift, split squat, hip thrust stations"),
            blk("Game 5 (4 v 4)", "Games", 15, "High", "Small pitch — reward rapid accel/decel/COD"),
            blk("Mobility & Cool-Down", "Recovery", 10, "Low"),
        ], {"td": "5.7", "hsr": "340", "sprint": "30", "explosive": "55"}),
        "2026-09-10": ("Rondo & Positional Play", "Ball retention under pressure, full pitch", [
            blk("Warm Up 4 Lanes", "Warm Up", 10, "Low"),
            blk("Rondos (4 v 2)", "Technical", 12, "Medium", "Two-touch, switch on third pass"),
            blk("Possession Drill 78 (8 v 8 w 2 N)", "Possession", 24, "High", "Full pitch — access wide overloads before switch"),
            blk("Game 24 (8 v 8)", "Games", 14, "High", "Short rest periods, high internal load"),
            blk("Cool-Down & Mobility", "Recovery", 8, "Low"),
        ], {"td": "8.0", "hsr": "750", "sprint": "90", "explosive": "25"}),
        "2026-09-11": ("Speed & Set Plays", "Top-end speed, low volume — bridge day", [
            blk("Warm Up 3 Lane Speed", "Warm Up", 10, "Low"),
            blk("Technical Exercise 12", "Technical", 15, "Medium"),
            blk("Tactical Shape and Set Pieces", "Tactical", 20, "Medium", "Corners — near-post routine"),
            blk("Tactical Drill 13 (Defending Around Box)", "Tactical", 12, "Low", "Zonal marking on corners"),
        ], {"td": "4.2", "hsr": "50", "sprint": "60", "explosive": "10"}),
        "2026-09-12": ("Pre-Match Activation", "Sharp, short, high quality — rifinitura", [
            blk("Warm Up Reactions 2", "Warm Up", 12, "Low"),
            blk("Positioning Exercise 1", "Tactical", 15, "Low", "Press triggers vs. opposition shape"),
            blk("Shooting Drill 9", "Technical", 10, "Medium"),
        ], {"td": "4.3", "hsr": "90", "sprint": "25", "explosive": "8"}),
        "2026-09-13": ("Match", "Championship — away at Riverside Town", [
            blk("Warm Up Cross", "Warm Up", 25, "Medium"),
            blk("Match", "Match", 90, "High"),
        ], {"td": "", "hsr": "", "sprint": "", "explosive": ""}),
        "2026-09-16": ("Match", "League Cup — home vs Colchester Athletic", [
            blk("Warm Up Cross", "Warm Up", 20, "Medium"),
            blk("Match", "Match", 90, "High"),
        ], {"td": "", "hsr": "", "sprint": "", "explosive": ""}),
        "2026-09-17": ("Rondo & Positional Play", "Cup turnaround — straight back into MD-3 prep, no recovery day available before Sunday", [
            blk("Warm Up 4 Lanes", "Warm Up", 10, "Low"),
            blk("Possession Drill 64 (8 v 8 - 4 Goals)", "Possession", 22, "High", "Full pitch"),
            blk("Game 14 (8 v 8 - 6 Goals)", "Games", 16, "High"),
        ], {"td": "7.8", "hsr": "720", "sprint": "85", "explosive": "20"}),
    }
    for date_str, (stype, notes, blocks, load) in demo_sessions.items():
        upsert_session(date_str, stype, notes, blocks, load, None)

    set_meta("season_phase", "Maintain")
