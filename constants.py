"""
Static reference data for Pitchboard.

DAY_TYPE_INFO is condensed from the Parma Calcio 1913 "Performance Science -
Coaching Framework" (dated 15/07/2025) -- the more detailed and more recent
of two source documents. That document uses "D" notation; it's kept here as
"MD" to match the day-code convention already used in this app. Numeric
targets are squad-level guidance, not individual prescriptions.
"""

DAY_CODES = ["MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"]

DEFAULT_TYPE = {
    "MD-4": "Strength & Power",
    "MD-3": "Rondo & Positional Play",
    "MD-2": "Speed & Set Plays",
    "MD-1": "Pre-Match Activation",
    "MD": "Match",
    "MD+1": "Recovery",
    "MD+2": "Off",
}

SESSION_TYPES = [
    "Strength & Power",
    "Rondo & Positional Play",
    "Speed & Set Plays",
    "Small-Sided Games",
    "Tactical Shape",
    "Pre-Match Activation",
    "Match",
    "Recovery",
    "Off",
    "Training",
]

ZONES = ["Warm Up", "Conditioning", "Technical", "Possession", "Tactical", "Games", "Recovery", "Match"]

INTENSITIES = ["Low", "Medium", "High"]

INTENSITY_FACTOR = {"Low": 2, "Medium": 4, "High": 7}

SEASON_PHASES = ["Build", "Maintain", "Recover"]

DAY_TYPE_INFO = {
    "MD-4": {
        "title": "Strength Day — neuromuscular focus",
        "aim": "Overload the mechanical component (accelerations, decelerations, changes of direction) — "
               "usually through game principles tied to small-pitch or transition-phase work.",
        "duration": "70–80'", "td": "5.5–6.0 km", "hsr": "300–400 m", "mw": "50–60", "work_rest": "1:3",
        "avoid": [
            "Large sided games",
            "High-intensity / sprint training",
            "Long periods of uninterrupted play — intensity, not duration, is the point",
        ],
        "suggested_zones": ["Conditioning", "Games"],
    },
    "MD-3": {
        "title": "Metabolic Day",
        "aim": "Overload the metabolic system with a major emphasis on high-speed running, using full-pitch "
               "work — aim to overload game intensity so players can cope with elite match demands under fatigue.",
        "duration": "80'", "td": "7.5–8.5 km", "hsr": "700–800 m", "mw": "35–40", "work_rest": None,
        "avoid": [
            "Poor posterior-chain warm-up — use running mechanics & active mobility for hamstrings instead",
            "Small-sided games — let the neuromuscular system recover",
            "Over-coaching interruptions — keep rest periods short, internal load high",
        ],
        "suggested_zones": ["Conditioning", "Possession", "Games"],
    },
    "MD-2": {
        "title": "Technical + Speed Integration (bridge day)",
        "aim": "Short, low-volume session to favour physical and mental recovery after two loading days — "
               "low-volume tactical work, set-pieces, individual technical training. Add controlled max-speed "
               "top-ups for wide/quick players; for youth sector, include a speed-oriented warm-up and "
               "max-speed exposure.",
        "duration": "60–75'", "td": "4.0–4.5 km", "hsr": "50 m", "mw": "5–10", "work_rest": None,
        "avoid": [
            "Game simulations or intense possession",
            "Players 'on-feet' for too long — keep it short and on purpose",
        ],
        "suggested_zones": ["Technical", "Tactical"],
    },
    "MD-1": {
        "title": "Rifinitura",
        "aim": "Final taper — game preparation. Rehearse tactical priorities and set-pieces with last "
               "(non-extensive) intensity. Warm-up should be quick and sharp.",
        "duration": "60–70'", "td": "4.0–4.5 km", "hsr": "80–100 m", "mw": "25–30", "work_rest": "1:4–1.6",
        "avoid": [
            "Large games (more than 2/3 pitch) — avoid excess HSR & sprint distance",
            "Running the session long — creates unwanted volume/fatigue; leave recovery time between reps",
            "Stopping/starting too much for coaching — keep games short but intense",
        ],
        "suggested_zones": ["Tactical", "Technical"],
    },
    "MD": {
        "title": "Match Day",
        "aim": "The game is the principal stimulus. The most consequential decision is how the next 48 hours "
               "are planned — separating compensation from active recovery.",
        "duration": None, "td": None, "hsr": None, "mw": None, "work_rest": None,
        "avoid": [],
        "suggested_zones": ["Match"],
    },
    "MD+1": {
        "title": "Compensation & Active Recovery",
        "aim": "Split by minutes played. High-minute players: active recovery — mobility, low-intensity "
               "technical work, set-piece walkthroughs, targeted prevention. Under-45-minute players: a "
               "compensation session approximating 45–60 min of match exposure (possession + small-sided "
               "games + HIIT).",
        "duration": "70–80' (compensation group)", "td": "6.5 km (compensation group)",
        "hsr": "500–600 m (compensation group)", "mw": "60–70 (compensation group)", "work_rest": None,
        "avoid": [],
        "suggested_zones": ["Recovery", "Possession", "Games"],
    },
    "MD+2": {
        "title": "Off / Individual Restoration",
        "aim": "Rest is programmed, deliberately — off-feet modalities, soft-tissue work, and light individual "
               "activation when needed. Youth sector adaptation: the usual MD+1 compensation work is moved "
               "here instead, so higher-minute youth players still get active recovery and technical touches.",
        "duration": None, "td": None, "hsr": None, "mw": None, "work_rest": None,
        "avoid": [],
        "suggested_zones": ["Recovery"],
    },
}

GENERIC_DAY_INFO = {
    "title": "General / build day",
    "aim": "Outside the ±4-day fixture window — treat as a general training day. In Build phase, use it for "
           "base fitness and technical development; in Maintain, keep it light; in Recover, prioritise "
           "freshness over load.",
    "duration": None, "td": None, "hsr": None, "mw": None, "work_rest": None,
    "avoid": [],
    "suggested_zones": ["Conditioning", "Technical", "Possession"],
}


# ---------------- player-count filtering ----------------

import re

_V_CHAIN_RE = re.compile(r"\d+(?:\s*v\s*\d+)+", re.IGNORECASE)
_V_NUM_RE = re.compile(r"\d+")
_EXTRA_RE = re.compile(r"(\d+)\s*(?:N|GK|Out)\b", re.IGNORECASE)


def parse_required_players(drill_name: str):
    """
    Best-effort estimate of how many players a drill needs, parsed from its
    name -- e.g. "Possession Drill 7 (6 v 6 w 2 N & 2 GK)" -> 16. Looks at
    the parenthesised group description if there is one (so a drill number
    like "Drill 78" is never mistaken for a player count), sums every
    number in a "N v N (v N...)" chain, then adds any extra bodies called
    out as neutrals/keepers/rotation players ("2 N", "1 GK", "4 Out") --
    but not numbers attached to other nouns like "2 Goals" or "3 Zones".

    Returns None when the name has no parseable player count -- most
    warm-ups, individual technical work, and conditioning circuits, which
    aren't tied to a fixed squad size and should never be filtered out by
    a player-count limit.
    """
    m = re.search(r"\(([^)]*)\)", drill_name)
    text = m.group(1) if m else drill_name

    chain = _V_CHAIN_RE.search(text)
    if not chain:
        return None

    total = sum(int(n) for n in _V_NUM_RE.findall(chain.group(0)))
    total += sum(int(n) for n in _EXTRA_RE.findall(text))
    return total
