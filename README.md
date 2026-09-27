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
nflverse releases (fetch_nflverse.py, needs github.com) -> data/raw/nflverse/*.parquet
  (snap counts · FTN charting · NGS participation · play-by-play slim · rosters · depth charts)
  -> scripts/build_advanced.py  -> player_usage (snaps, snap%, target/rush/air-yard share, aDOT, WOPR)
                                   team_off_tendencies / team_def_tendencies (per season)
                                   scheme_tags (computed DC/OC scheme + evidence + coverage source)
                                   starter_turnover (top-11-by-snaps YoY: retained/departed/new)
                                   coaching (HC/OC/DC per season, change flags, where the new coach came from;
                                             source: data/raw/coordinators.csv, PFR coaches pages)
                                   scheme_slot_effects (scheme family x slot PPR index)
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

## Intel layer (F7) — how the tags are computed
- **Defense scheme tag** = dominant coverage shell over charted pass plays (C3 vs C1/C0 vs C4/C6 vs C2/2-man),
  overridden by man ≥40% ("Man-heavy · Cover-1 press") or two-high ≥50% & zone ≥65% ("Two-high zone shell");
  "multiple / disguise" when no shell reaches 36%. Descriptors: blitz rate (5+ rushers) vs league percentiles,
  average box, base/nickel/dime personnel. Evidence string carries every underlying rate.
- **2026 coverage** is not charted yet by NGS participation: the tag uses the coordinator's most recent charted
  unit (new DC → his prior team's 2025 unit, e.g. BAL ← Weaver's MIA; returning DC → same team 2025), marked †
  and named in `coverage_source`. FTN-charted fields (blitz, box, pressure) and pbp EPA are live 2026 data.
- **Offense scheme tag** = PROE (pass-first ≥ +3 / run-first ≤ −3) + tree by league-percentile means:
  under-center play-action/motion (Shanahan/McVay), spread shotgun-RPO-tempo, or vertical air-raid; descriptors
  when a rate is ≥78th percentile (play-action heavy, motion-heavy, RPO-heavy, up-tempo, screen game, vertical,
  quick game, slow pace) + personnel (11-heavy ≥72%, heavy ≥35%).
- **Turnover** = top-11 defenders/offensive players by snaps each season; turnover % = share of last season's
  eleven who are not in this season's eleven; returning-snap % = share of their snaps still on the roster.
  Departed players carry a destination (new team / bench-injured / left NFL-FA); new starters a source
  (team / promoted / rookie).
- **Player usage** = game_logs ⋈ nflverse snap counts on PFR id; target/rush/air-yard shares from pbp per game.

## Views (final)
Home (smash board + full insight screens) · TD Board (phase-space + collider scatters, filters,
true WR1-WR12 labels) · Weekly Matchups (16 game cards, gridiron tilt) · Players (collapsible
depth charts, depth/injury filters, popup player cards, deep dives) · Defenses (rankings /
matrix / observatory) · Schedule (6-band heat grid) · Intel (DC/OC scheme tags, tendencies, turnover,
player usage). F1-F7 keyboard shortcuts; mobile-responsive
(viewport meta + media queries); click any player name anywhere for his card.

## Changelog
- 2026-09-27 (c) — ROSTER filter (draft-results owner) in the global bar, applied to every board; "My lineup"
  panel on Home when a roster is selected (ranked by Ψ+ with suggested starters, trust / scheme / role columns);
  Ψ+ conviction score (DvP Ψ shrunk by defense trust + scheme edge + game environment + role) in Matchup Lab and
  player cards; owner tags + roster highlighting on game cards; build_matchups re-matches drafted players who
  changed teams since the draft (60 recovered, e.g. Diggs NE→WAS, Waddle MIA→DEN).
- 2026-09-27 (b) — Home "Intel brief": game environments (scoring index = both offenses' EPA + both defenses'
  EPA allowed, pace, PROE, shootout / rock-fight tags), role movers (last game vs season snap + target share),
  scheme edges (opponent scheme family × slot, league-indexed), fragile priors (defense trust score = returning
  starter snaps − new-DC penalty + 2026 weeks). Trust pills + environment line on every game card and player
  card; scheme-edge column + usage arrows in Matchup Lab; Ctrl-K / "/" command palette (jump to any player or
  team); click any team code anywhere to toggle it as the team filter; header counts computed from the payload.
- 2026-09-27 — Intel tab (F7): DC/OC scheme tags with evidence, coverage-shell mix, blitz/box/personnel,
  EPA allowed, PROE/play-action/motion/tempo, scheme × slot index, defensive + offensive starter turnover,
  coaching changes (15 new DCs, 21 new OCs, 10 new HCs in 2026). Snap% / target share in Matchup Lab,
  player cards and deep-dive game logs; scheme line on every Weekly Matchups game card; refresh.py runs
  build_advanced.py.
- 2026-09-23 — 2026 wk 2 box scores + 09-23 depth charts; wk 3 matchups live.
- 2026-09-17 — 2026 wk 1 box scores + positions + fresh depth charts; wk 2 matchups live; trend season
  auto-selects the latest season with ≥4 weeks; verify_data in-season aware (64/64).
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
