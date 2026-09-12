# Pitchboard — Project Reference

## What this is
Microcycle and session-planning app for a squad: season fixtures, automatic
MD-4…MD+2 day labelling (with congestion-priority logic for compressed
weeks), a per-day-type coaching reference panel (aims, targets, avoid-lists,
suggested drill categories), and estimated training load (TD / HSR / sprint
distance / explosive distance) per session. Originally built as a Claude
Artifact, then rebuilt as a standalone Python/Streamlit app so it doesn't
need Claude to run.

## Where it lives
- **Local folder:** `~/pitchboard` on your Mac (`app.py`, `dayrules.py`,
  `db.py`, `constants.py`, `data/drills.json`, and this file)
- **GitHub:** `github.com/ronankav10/pitchboard` — should be a **private** repo
- **Deployed app:** not deployed yet — see "Next steps" below

## Making changes going forward
1. Tell me (Claude) what you want changed.
2. I write the change directly into the files on your Mac (your desktop
   app is connected, so no downloads needed).
3. You push it live:
   ```bash
   cd ~/pitchboard
   git add -A
   git commit -m "describe the change"
   git push
   ```
4. Once it's deployed on Streamlit Cloud, a push auto-redeploys within
   about a minute — same URL, no redeploy steps needed on your end.

## Features currently in the app
- Season fixture calendar (date, opponent, competition, venue) on its own
  **Fixtures** page (in the sidebar page nav) — seeded with Parma Calcio
  1913's full 38-match Serie A 2026-27 calendar (`data/fixtures_2026_27.json`),
  with a one-click reload if it ever needs resetting to the official list
- A day-by-day "Season calendar" on the Fixtures page covering every day
  from today through the season, with an In/Off dropdown per day so you
  can block out rest days without opening each one in the planner (match
  days are automatic and can't be toggled there)
- Automatic day-code labelling for every date (MD-4…MD+2) from its gap to
  the nearest fixture, with the upcoming match taking priority over a
  previous one in a congested week — any single day can be overridden
  by hand
- Rolling 5-day view (starting today, paged with Prev/Next/Today) with day
  cards and a session builder: a day-type override, a Coaching focus field,
  a Physical focus field, block list via a data table, and a "quick add
  from drill library" picker (556 drills carried over from your Drill
  Profiles folders) — there's no manual "session type" dropdown anymore,
  it's computed automatically from the day code (or set to "Off" via the
  Fixtures page)
- Estimated training load fields (TD / HSR / sprint distance / explosive
  distance) per session, with the TD/HSR/Duration numbers turning red if
  they exceed the day-type's recommended target by more than 25%
- "Players available" field per session that filters the drill-library
  picker to drills that fit your headcount (parsed from the drill name,
  e.g. "6 v 6 w 2 N" needs 14) — drills without a parseable player count
  (most warm-ups, individual technical work, conditioning circuits) always
  stay visible regardless
- Pitch-size suggestions (compact/expanded estimates, not measured data)
  shown alongside each drill based on the players it needs
- **Drill Library** page — browse all 555 drill diagrams by category, with
  search; the quick-add picker on the main page also shows a thumbnail of
  whatever drill is selected. Images are re-encoded JPEGs (~24MB total,
  down from ~146MB of source PNGs) pulled from your Liverpool Drill
  Profiles folders — `data/drill_images_manifest.json` maps each drill
  name to its image path.

## Data storage
Everything lives in a single SQLite file, `pitchboard.db`, created next to
`app.py` on first run — no signup, no external service. See `README.md`
for the tradeoff if you deploy to Streamlit Community Cloud (that file can
be wiped on a redeploy — fine for local use, worth revisiting if you keep
a cloud-hosted version long-term).

## Terminal / setup gotchas (in case you need this again)
- Use `python3` / `pip3` on macOS, not `python`/`pip`
- GitHub auth: use `gh auth login` (browser-based), not username/password
- When pasting multi-line commands into Terminal, paste **one line at a
  time** — pasting a block can occasionally strip line breaks and merge
  commands

## IP note
The day-type reference panel is condensed from Parma Calcio 1913's
internal coaching framework document, and the drill library was pulled
from the Liverpool Sports Science Drill Profiles folders — both are
club-owned material, not yours to publish. Following the same approach as
HIT Builder, this repo and any deployed app should stay **private**:
a private GitHub repo, and — once deployed — Streamlit Community Cloud
set to invite-only rather than "anyone with the link". Let me know if
you'd rather handle it differently (e.g. stripping that content out of
what goes to GitHub and keeping it local-only).

## Next steps (not done yet)
1. ~~Create a private GitHub repo and push~~ — done, pushed to
   `github.com/ronankav10/pitchboard`. Worth a quick check on github.com
   that it's set to **Private** (Settings → General → Danger Zone shows
   current visibility).
2. Deploy on [share.streamlit.io](https://share.streamlit.io), then set
   the app to **Private** under its Share settings and add viewers by
   email.

## Getting help later
This whole conversation stays in your Claude chat history if you want to
scroll back through the full detail — this file is just the condensed
version for quick reference.
