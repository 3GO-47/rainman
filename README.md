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
nflverse nfldata games.csv (fetch_games.py) -> game_lines.csv -> build_games.py -> team_ratings / game_model /
                                                 picks_ledger (frozen) / picks_retro
ESPN odds API (Chrome recipe)  -> data/raw/props_2026_wk{W}_{date}.txt -> build_props.py -> props_current / props_ledger
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

## Big Board (F2) — the projection model
```
PROJ = baseline × matchup × scheme × environment × role
baseline    = shrink(own PPR/gm, n_eff, slot league mean, k=3)      own: 2026 games ×2, last 8 games of 2025 ×1
allowed     = (prior-season DvP PPR_allowed(opp, slot) × 4 + season-to-date PPR_allowed × weeks) / (4 + weeks)
matchup     = 1 + (allowed / league_mean(slot) − 1) × w_pos × (0.4 + 0.6·trust/100)     w_pos: QB .35 RB .15 WR .05 TE .25
scheme      = clamp(1 + (scheme_slot_index/100 − 1) × 1.0, 0.85, 1.15)      (2024-25 charting)
environment = 1 + (week percentile of the game's scoring index − 0.5) × 0.1  (tie-breaker; no measurable lift)
role        = 1 + clamp((last-game snap share − season snap share) × 0.6, −0.25, 0.25)   (QB = 1)
Weights were tuned by the walk-forward backtest in the Model Lab (constants live in MODEL in the template).
range       = his own 25th / 80th percentile game × (PROJ / own)              (< 4 games → ±35%)
```
PPR_allowed comes straight from the DvP averages (pass yd/25, 4/pass TD, rush+rec yd/10, 6/TD, 1/rec).
Everything is client-side in `dashboard_template.html` (`projection()`), so the CSV export is the model's output.

## Intel layer (F8) — how the tags are computed
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
player usage) · Big Board (projections + rankings, CSV). F1-F8 keyboard shortcuts; ? glossary; ctrl-K find; mobile-responsive
(viewport meta + media queries); click any player name anywhere for his card.

## Changelog
- 2026-10-05 — Depth charts stay collapsed until you open them (a game/team filter swaps the teams but no longer
  forces the panel open); storyline strips start collapsed. **Waiver radar**: ROSTER filter gains *free agents
  (unrostered)* — every tab narrows to players on no roster in the draft results, and Home shows the radar (QB1s and
  skill players who start or play ≥25% of snaps, ranked 0.4 × PROJ this week + 0.6 × avg PROJ next 3 weeks + role
  trend); with no roster selected Home shows the top 8.
- 2026-10-05 — **F10 Locker Room: storylines, birthdays, rivalries** (birthdays were out of scope in the original
  brief; added on request). *Storylines* per game: college **rivalries** across the line (85 tracked, 38 marquee),
  **alumni** reunions (same college, opposite sidelines), **homecomings** (born ≤100 mi from the stadium), **alma mater**
  games (campus ≤100 mi away), **home-state** games, **revenge** games (faces a 2024-25 team or the club that drafted
  him) and **birthday games**. *Birthdays*: every 2026 player — next birthday, age, turns, birthday games this season,
  today banner. *Rivalries*: this week + the 2026 rivalry calendar (marquee, starter vs starter). Also surfaced on Home
  (storylines + next-14-day birthdays), each Weekly Matchups card, the two-team depth chart (tags next to names) and the
  player card (birthplace, age, this week's threads). Sources: ESPN athlete birthPlace (Chrome), ESPN college venues,
  nflverse rosters (birth date, team history, draft club), offline GeoNames geocoding (`pip install geonamescache`).
- 2026-10-05 — Depth charts show two teams side by side (mirrored by position: QB · RB · WR1-3 · TE · FB, depth #,
  college logo, Q/OUT), with a game picker, a vs-team picker and a swap button. Picking a team auto-loads its opponent;
  the chart follows the filter bar — a selected GAME loads both teams (and opens the panel), a selected TEAM loads it vs
  its opponent that week. Names open the player card.
- 2026-10-05 — **College layer.** Every player's final college (nflverse rosters; first school listed = last attended,
  earlier stops shown as "also attended") with the ESPN college logo, school color bar, conference badge and a tier tint
  (gold = Power-4/Notre Dame · teal = G5 · slate = FCS · magenta = D2/D3/NAIA small school). Shown in the player card
  header (with draft year + overall pick), as a sortable College column on Players (Matchup Lab) and the Big Board, as
  logos in the depth charts, in the Big Board CSV, and as a Players-tab filter (tier / conference / school) + search.
  School ids/colors/conferences: `data/raw/colleges_espn.txt` (ESPN core API via Chrome; 184 schools, 4 without an ESPN
  football program fall back to initials).
- 2026-10-02 — Mobile + performance pass. Views render lazily: only the visible tab re-renders on a filter change, the
  others are marked dirty and rebuilt when opened (mobile load 2.9 s → 0.9 s, filter apply 600 → 140 ms). ≤840 px:
  the filter bar collapses behind a ⚙ FILTERS toggle, nav scrolls horizontally, tables scroll inside their cards,
  game cards stack, tap targets ≥36 px. Desktop unchanged.
- 2026-10-01 — Players tab: position buttons now toggle and combine (ALL / QB / RB / WR / TE in any mix). With one
  position selected the per-stat DvP columns stay; with several, the stats sit in a shared sortable grid (PaYd · PaTD ·
  RuYd · Rec · RcYd · TD · P+R/R+Y, rank badges + raw) plus a Pos column and Ψ / Ψ+ / PROJ. Respects the global POS filter.
- 2026-09-29 — 2026 wk 3 box scores (16/16, checksum-verified, scores cross-checked vs nflverse) + ESPN depth charts 09-29;
  wk 4 matchups live; blend flips to 2024+2025+2026×2 at the wk 4 refresh. **Games & Picks (F9)**: nflverse lines/results
  (scores, DK-consensus spread/total/moneyline, rest, QBs) → walk-forward power ratings + spread/total model → picks where
  the model disagrees ≥3 pts, **frozen** when first built and graded against the frozen line; honest 2024-25 backtest
  shown next to the live record (ATS 49%, totals 55%; the market is the better forecaster; moneyline picks removed after
  going 41-101). **Player props**: DraftKings lines via ESPN's public odds feed (no key), joined to per-stat projections,
  L10 over-rates and DvP ranks; leans frozen and auto-graded. Scrape recipes documented; refresh.py runs both builders.
- 2026-09-27 (e) — **Model Lab** (Big Board → expand): walk-forward backtest of PROJ over 6,009 player-weeks (all of
  2025 + 2026 wk 1-2), each week rebuilt with only pre-kickoff information. Findings drove a re-tune: a raw
  prior-season DvP multiplier makes rankings worse (ρ .571 vs .594 baseline-only); DvP blended with season-to-date
  and applied at position weights (QB .35 · RB .15 · WR .05 · TE .25) is neutral-to-positive; scheme family × slot is
  the strongest opponent signal (full weight); role trend helps; environment adds nothing (0.1 tie-breaker). Live
  model: ρ .601 starters (baseline .594, naive DvP .571), MAE 4.93, well calibrated by decile. The lab shows every
  variant per season/position, factor quintile spreads, calibration, and the live configuration.
- 2026-09-27 (d) — **Big Board (F2)**: weekly player projections + rankings that fold every layer together —
  PROJ = own PPR/gm (this season 2×, last 8 of '25, shrunk to the slot mean) × PPR the opponent allows to his slot
  vs league (shrunk by defense trust) × scheme family × game environment × role trend; floor/ceiling from his own
  25th-80th percentile game; overall + positional ranks, lift vs baseline, every factor as a sortable column, CSV
  export; ALL/QB/RB/WR/TE/FLEX tabs; obeys week/slate/pos/game/team/roster filters. Home shows the top-12 board and
  biggest lifts/drags; My Lineup ranks and picks starters by projection; player cards carry the PROJ arithmetic.
  Nav reordered (Home · Big Board · Matchups · Players · Defenses · TD Board · Schedule · Intel, F1-F8); "?" glossary.
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
