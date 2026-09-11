# Pitchboard (Streamlit)

Microcycle and session planning for a squad — season fixtures, automatic
MD-4…MD+2 day labelling, per-day-type coaching reference (aims, targets,
avoid-lists, suggested drill categories), and estimated training load
(TD / HSR / sprint distance / explosive distance) per session.

This is a Python/Streamlit rebuild of the original Pitchboard, which runs
as a Claude Artifact. The feature set matches; the day-code logic is
identical (same priority rule for congested weeks). It doesn't need Claude
to run — this is a normal Python app you can run on your own machine or
host anywhere that runs Streamlit.

## Requirements

Python 3.10 or newer.

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will open the app in your browser (usually `http://localhost:8501`).
On first run it seeds a demo week's worth of fixtures and sessions so it's
not a blank page — delete `pitchboard.db` at any point to start fresh.

## Data storage

Everything (fixtures, sessions, season phase) lives in a single SQLite file,
`pitchboard.db`, created next to `app.py`. There's no signup, no external
service, and no secrets to configure — it just works the moment you run the
app.

**The tradeoff**, if you deploy this to Streamlit Community Cloud (see
below): that file lives on the app's own container disk. It survives while
the app stays up, but a **new deploy (a git push) or the app being rebuilt
from a long sleep can wipe it**, since Community Cloud doesn't guarantee a
persistent disk across deploys. For your own local use this doesn't matter
at all — it's a normal file on your machine. For a cloud-hosted version you
plan to keep long-term, the two straightforward upgrades later are:

- Periodically back up `pitchboard.db` (e.g. download it from the app, or
  add a small "export data" button).
- Swap the SQLite calls in `db.py` for a hosted free-tier database (Supabase
  Postgres and Turso/LibSQL both have generous free tiers and a similar
  amount of code to wire up) — the rest of the app (`app.py`, `dayrules.py`,
  `constants.py`) doesn't need to change, since they only ever call the
  functions in `db.py`.

## Project layout

```
app.py            Streamlit UI — week navigation, builder, summary
db.py             SQLite persistence (fixtures, sessions, season phase)
dayrules.py       Day-code computation (MD-4…MD+2) and date helpers
constants.py      Reference data — day-type aims/targets/avoid lists, zones, etc.
data/drills.json  Your drill library (556 drills, from your Drill Profiles folders)
requirements.txt  Python dependencies
.streamlit/config.toml   Colour theme
```

## Push it to GitHub

From inside this folder:

```bash
git init                     # skip if already a git repo
git add -A
git commit -m "Pitchboard: Streamlit rebuild"
```

Then on GitHub: create a new repository (github.com → New repository — leave
it empty, no README/license), and push:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

## Deploy on Streamlit Community Cloud (free)

1. Push the repo to GitHub (above).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
3. Click **New app**, pick the repo and branch, and set the main file path
   to `app.py`.
4. Deploy. You'll get a public `*.streamlit.app` URL.

Keep the data-storage tradeoff above in mind — this is a personal planning
tool, so a public URL means anyone with the link can view and edit it
unless you turn on Streamlit's built-in viewer authentication (under the
app's settings on Community Cloud) or keep the link private.

## Day-code logic, briefly

Every calendar day is labelled automatically from its gap to the nearest
fixture: within 4 days *before* a match, it's `MD-4`…`MD-1`; the match
itself is `MD`; within 2 days *after*, it's `MD+1`/`MD+2`. When a day is
close to two fixtures at once (a congested run), the *upcoming* match takes
priority — so a Tuesday cup game followed by a Sunday league game goes
straight from match day into `MD-3` prep, skipping the recovery slot,
matching how a real short turnaround is actually coached. Any single day
can still be overridden by hand in the builder.

The day-type reference content (aims, targets, avoid-lists) is condensed
from the Parma Calcio 1913 "Performance Science – Coaching Framework"
(dated 15/07/2025).
