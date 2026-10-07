# RAINMAN local loop — runs on Josh's PC, no Claude session, no browser (2026-10-07)

Why: the five Claude scheduled tasks each spun up a full session (clone, Chrome pulls, web upload) — expensive. Everything they
did is HTTP that a Python script on the PC can do directly, so the loop now lives in `scripts/local/` and Task Scheduler runs it.
The Claude tasks are **paused** (not deleted) — re-enable one only if the PC can't run the loop.

## One-time setup (PowerShell)
```
powershell -ExecutionPolicy Bypass -File C:\Users\jwlar\rainman\scripts\local\install.ps1
cd C:\Users\jwlar\rainman; py -3 scripts\local\loop.py --dry        # gate only — shows which leagues are live today
py -3 scripts\local\loop.py --force --no-push                       # full first run (5-15 min), commit kept local
```
Needs Python 3 (py launcher) and Git for Windows. `install.ps1` pip-installs pandas numpy pyarrow beautifulsoup4 lxml openpyxl
and registers **"RAINMAN local loop"** (daily 06:50, wake-to-run, 2 h limit). Output: `notes\local_runs.log` (+ `local_loop.out`).

## Pushing to GitHub (the live site)
The loop commits every run and tries `git push`. It pushes only if Git Credential Manager already holds your GitHub login
(run **one** `git push` yourself in a terminal; GCM opens the browser sign-in and stores the token in Windows Credential
Manager — nothing is written into the repo or any file). Without that, commits pile up locally and the site stays as is;
`git push` by hand publishes them any time. GitHub Pages rebuilds from `dashboard/*.html` on every push.

## What a run does (scripts/local/loop.py)
| step | when | source | writes |
|---|---|---|---|
| slate | every run | ESPN scoreboard, 14 leagues × 8 days, **preseason rows dropped** | data/raw/slate_all_<d>.txt |
| gate | every run | nflverse games.csv, sportsdataverse schedules, slate | — (reg-season/playoff games only) |
| NFL box scores | NFL active, any day, only games not yet in the file | PFR boxscore pages (4 s apart) → nflverse `stats_player_week` fallback (same numbers, ids via roster) | data/raw/box_lines_2026.txt, positions_2026.csv, scrape_state.json |
| NFL depth charts | Tue/Wed/Thu/Sat/Sun or snapshot > 5 d | ESPN core depthcharts + roster injuries | data/raw/espn_depth_<d>.txt → depth_charts_<d>.csv |
| props + Kalshi | Thu/Sat/Sun with games in 7 d | ESPN odds provider 100 (DK) · api.elections.kalshi.com | data/raw/props_2026_wk<W>_<d>.txt, kalshi_<d>.txt |
| nflverse cache | Tue | GitHub releases | data/raw/nflverse/ |
| NFL rebuild | anything new, or Tue/Thu/Sat/Sun | scripts/refresh.py (also runs sports + landing; Odds API only if .env has the key) | dashboard/rainman.html, ncaa.html, nba/nhl/wnba, index |
| NCAA | Tue/Sat in season | ESPN scoreboard + pickcenter → scripts/ncaa/refresh.py | ncaa/data/raw/espn_lines_2026_<d>.txt, dashboard/ncaa.html |
| NBA / NHL / WNBA | only when that league has reg-season/playoff games yesterday/today/next 7 d | sportsdataverse parquets → scripts/sports/build.py | data/sports/<lg>/, dashboard/<lg>.html |
| landing | always | — | dashboard/index.html |
| git | always | commit; push if credentials exist | — |

`--force` ignores the weekday cadence; `--no-push` keeps the commit local; `--dry` prints the gate and exits.
Each step is isolated: a failed pull is logged and the rest of the run continues. If PFR refuses (403/429) the box pull
switches to nflverse for the rest of that run (validated identical on week-4 games: 61/61 player lines, 0 diffs).

## Season gate (`scripts/local/gate.py`)
NFL active = a non-preseason game within ±7 days · NCAA = cfb games in the slate (or Aug–Jan) · NBA/NHL/WNBA active = a
regular-season or playoff game yesterday, today or in the next 7 days (schedule parquets exclude preseason; the slate drops
seasonType 1). Off-season leagues cost nothing: no pulls, no builds.

## Still manual / Claude-only
Nothing in the weekly cadence. Things that still need a person or a session: new-season bootstraps (positions from PFR's
fantasy page if roster ids are missing, schedule parse), MLB / NCAAB / soccer player data (no source yet), and anything UI.
