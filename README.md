# RAINMAN — 2026/27 Defense-vs-Position Intelligence

Answers, every week: how many stats does each NFL defense allow to each positional slot
(QB, RB1, RB2, WR1-3, WR4+, TE1, TE2, D/ST), and what does that mean for each player's
matchup. Replaces the legacy NFLLLLL.xlsx workbook. Rank convention everywhere:
**rank 1 = most allowed = best matchup** (legacy RANK.AVG).

## The product
`dashboard/rainman.html` — single self-contained file, open in any browser. Views:
- **Ψ Matchup Lab** — every depth-chart player with his opponent's per-stat DvP ranks, raw
  allowed/gm, and composite Ψ, for any 2026/27 week (the legacy 2025QB/RB/WR/TE sheets, live)
- **DvP Rankings** — 32 defenses × every stat (rank + raw) per slot, plus an ALL-stats field
- **Field Matrix** — 32×10 Ψ heatmap with per-defense radar fingerprint drill-down
- **Spacetime Grid** — all 32 offenses × 18 weeks of 2026/27, colored by opponent softness per slot
- **Defense Observatory** — worldline vs league μ±σ, two-defense interference radar, energy
  spectrum of all 32 logos, phase portrait (collapsing vs tightening), momentum/uncertainty table
- **Player Collider** — full multi-season game logs, PPR/usage charts, next-4 trajectory
- **Grand Unified Insights** — week-aware smash/avoid, momentum shifts, volatility, schedule geodesics

## Global filter bar (every tab)
The sticky bar under the nav drives every view at once:
- **WEEK** — the 2026/27 week (defaults to the current week from `refresh.py`; Home, TD Board,
  Weekly Matchups, Matchup Lab, popup cards and the Schedule highlight all follow it)
- **SLATE** — TNF · SUN 1P (1:00 ET / 12:00 CT) · SUN 4P (4:05-4:25 ET / 3:05-3:25 CT) · SNF · MNF,
  plus THU DAY / FRI / SAT / INTL AM when the week has them; wk 18 = TBD until the NFL flexes.
  Chips toggle, so any combination works (e.g. SUN 4P + SNF)
- **POS** — QB / RB / WR / TE / D-ST, multi-select; narrows every view to those slots (Lab and
  Rankings tabs, Matrix columns, game-card rows, TD Board, Home boards, insight screens)
- **GAME** — a single matchup (chronological list for the week, with kickoff time)
- **TEAM** — one team; combine with slate/game to narrow further
Player views show players whose team is in the filter; defense views show the filtered teams'
defenses **and the defenses they face that week**; the Observatory auto-selects the two sides of
a chosen game. The bar's summary shows games/teams matched, kickoff (ET + CT) and byes.
Kickoffs come from `data/processed/kickoffs_2026.csv` (built by `scripts/build_kickoffs.py`
from the PFR schedule + week pages in `data/raw/`).

Filter state lives in the URL hash (`#wk=3&slate=LATE,SNF&pos=RB,WR&game=GB@MIN&team=MIN`) — the **link** button
copies it, so a bookmark or a pasted link reopens the exact view. Home also has a **slate map**
(every kickoff window with the field-tilt favorite; click a window to filter every tab), Weekly
Matchups groups its game cards under slate headers, and the Matchup Lab / TD Board carry a
sortable kick column.

## Live deploy
`.github/workflows/pages.yml` publishes `dashboard/rainman.html` to GitHub Pages on every push
to main (one-time: Settings → Pages → Source = *GitHub Actions*). Live at
https://3go-47.github.io/rainman/ once enabled.

## Data flow (every number traces to data/game_logs/)
```
PFR box scores (Chrome scrape) -> data/raw/box_lines_{season}.txt
  -> scripts/build_game_logs.py  -> data/game_logs/game_logs_{season}.csv   [source of truth]
  -> scripts/compute_dvp.py      -> dvp_weekly / dvp_season_{s} / dvp_combined
PFR schedule + week pages     -> scripts/build_kickoffs.py -> kickoffs_2026.csv (day/time/slate)
ESPN depth charts (Chrome)      -> scripts/build_depth_chart.py -> depth_charts_{date}.csv
PFR schedule                    -> schedule_2026.csv (26/27, byes marked, box ids precomputed)
  -> scripts/build_matchups.py  -> matchups_current.csv
  -> scripts/build_dashboard.py -> dashboard/rainman.html
```
`scripts/dashboard_template.html` is the dashboard source; the builder injects fresh JSON.

## Weekly refresh (Tuesdays in-season)
1. Ask Claude to scrape the new week + re-pull depth charts (recipe: `notes/scrape_recipe.md`;
   ~16 box scores ≈ 2 minutes; everything checkpoints in `notes/scrape_state.json` and resumes)
2. `python3 scripts/refresh.py` — rebuilds every derived table + the dashboard, auto-detects
   the current 26/27 week, reports row counts and anomalies

dvp_combined weighting: prior seasons only until 2026 has ≥4 weeks of data, then the current
season counts 2×.

## Views (final)
Home (smash board + full insight screens) · TD Board (phase-space + collider scatters, filters,
true WR1-WR12 labels) · Weekly Matchups (16 game cards, gridiron tilt) · Players (collapsible
depth charts, depth/injury filters, popup player cards, deep dives) · Defenses (rankings /
matrix / observatory) · Schedule (6-band heat grid). F1-F6 keyboard shortcuts; mobile-responsive
(viewport meta + media queries); click any player name anywhere for his card.

## Changelog
- 2026-09-13 (c) — multi-select slate chips + multi-select POS filter (QB/RB/WR/TE/D-ST) applied to every
  tab; clipped rank badges fixed (badge-first, wider stat cells).
- 2026-09-13 (b) — URL-hash filter state + link button; Home slate map; slate headers in Weekly
  Matchups; kick column in Lab + TD Board; GitHub Pages deploy workflow.
- 2026-09-13 — global week/slate/game/team filter bar across every tab; kickoff times + slate
  buckets for all 272 games; single global week (no more hard-coded wk 1 on Home/popups);
  system panel counts computed from the payload; headless render test passes with 0 JS errors.

## Status (as of 2026-07-14)
- 2024 + 2025 seasons fully scraped: 544/544 box scores, 10,702 game-log rows, 0 fetch errors
- 2025 DvP validated vs legacy workbook: 86.9% cells exact; slot-independent columns 89-100%
  (diffs are offsetting slot-attribution swaps — `notes/validation_2025.md`, `notes/slot_method.md`)
- 2026/27 schedule loaded (272 games, ISO dates, box ids precomputed for in-season scraping)
- Depth charts snapshot 2026-07-13 (re-pull as rosters settle; flags in notes/)
- Known gaps: D/ST scoring is return/def TDs only (no sacks/INTs); playoffs excluded by design
- Data audit: scripts/verify_data.py — 45/45 checks (independent recompute of all 36,992 weekly
  DvP cells, rank math, blend, dashboard payload) + exact external validation vs PFR player pages
