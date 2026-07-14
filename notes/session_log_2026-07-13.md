# Session log — 2026-07-13 (RAINMAN v1 stand-up)

## Completed
- Scaffolded repo structure; checkpointing via notes/scrape_state.json
- ESPN depth charts: 32 teams, 767 players -> data/processed/depth_charts_2026-07-13.csv
  (injury flags 1/0/-1 from ESPN Q/O/IR tags); cross-check flags in depth_chart_flags_2026-07-13.md
- 2026 schedule from PFR (published): schedule_2026.csv, 272 games, byes verified (32)
- Scraped ALL box scores, both seasons, via Chrome same-origin fetch (PFR blocks sandbox + web_fetch
  chokes on box pages): 2025 = 272 games / 5,373 player rows; 2024 = 272 games / 5,329 player rows
- Raw parsed lines cached in data/raw/box_lines_{season}.txt (source pages parsed in-browser)
- game_logs built with slot assignment (see slot_method.md); positions from PFR fantasy pages
- DvP computed: dvp_weekly (1,088 defense-weeks), dvp_season_{2024,2025}, dvp_combined (2024+2025
  equal blend; 2026 gets 2x weight once >=4 weeks exist), matchups_current (364 players, wk1 2026)
- Validated vs legacy NFLLLLL.xlsx Data tab (5 defenses): 86.9% cells exact; slot-independent
  columns 89-100% (QB PY 100%); mismatches are offsetting slot-attribution swaps. validation_2025.md
- dashboard/rainman.html: 5 views, self-contained, all numbers trace to game_logs

## Judgment calls
- Historical slots: cumulative-usage ranking (no ESPN history exists) — slot_method.md
- RB3+/TE3+ fold into RB2+/TE2 buckets to match legacy; QB bucket = all QBs
- D/ST TDs = return/defensive TDs parsed from box-score scoring tables
- 86 Master Key players unmatched to July depth charts (offseason churn) — matchup_unmatched.md

## Deferred / next session
- Weekly Tuesday refresh script (single command: pull new week + depth charts -> rebuild)
- D/ST fantasy scoring beyond TDs (sacks/INTs allowed) if wanted for D/ST streaming
- Playoff games excluded by design (regular season only, matching legacy)
- Depth-chart re-pull + matchup rebuild as rosters settle in August/September

## Dashboard v2 revamp (same session)
- Template externalized to scripts/dashboard_template.html (builder reads it; fixes prior truncation risk)
- New landing view "Psi Matchup Lab" = the workbook's 2025QB/RB/WR/TE sheets, live: every depth-chart
  player (767) with opponent's per-stat DvP ranks (starred cols), raw allowed/gm, composite Psi;
  tabs QB/RB/WR/TE, source toggle (2024/2025/combined), owner/team/search filters, sortable
- New "DvP Rankings" view = Data-tab averages: per-slot tables (rank + raw per stat) + ALL tab
  (32 defenses x all 34 stat ranks in one field)
- Field Matrix: heatmap + per-defense radar "fingerprint" (permeability by slot) + full drill
- Defense Observatory: weekly worldline chart with mu/sigma, momentum (last4 vs season) and
  volatility per slot
- Player Collider: PPR bar chart vs mu, usage worldline, next-4 trajectory, full multi-season log
- Grand Unified Insights: smash/avoid (fusion/fission), momentum shifts, uncertainty principle
  (most/least predictable defenses by CV), 2026 schedule geodesics
- Physics composition: animated constellation particle field, glow accents, dark space palette
- Verified headlessly (jsdom): all views render with real data, zero runtime errors

## Dashboard v3 (same session)
- Team identity layer: ESPN logo CDN + per-team display colors (brightened for dark bg) applied to
  every team reference across all views (tcell/oppcell helpers)
- Owner column/filter REMOVED from Matchup Lab per user (not a fantasy-league tool)
- Defense Observatory rebuilt as comparative physics suite:
  * hero banner with team gradient + all-slot Psi field strength
  * worldline chart vs league mu +/- sigma band, with a second defense overlaid (interference partner)
  * interference radar: two defenses' permeability (33-Psi) in team colors
  * energy spectrum: all 32 logos positioned along the Psi axis for any slot (hover = value)
  * phase portrait: season mu vs last-3 mu scatter, logo point markers, equilibrium diagonal
    (above = collapsing, below = tightening)
  * momentum & uncertainty table (Delta-p arrows, sigma, sigma/mu)
- Verified headlessly (jsdom): all views render, 0 runtime errors; JS syntax node-checked

## Dashboard v4 (same session)
- Verified 26/27 schedule end-to-end: schedule_2026.csv is the 2026/27 season from PFR
  (opener NWE@SEA 2026-09-09; spot-check KC: wk1 DEN, wk5 BYE); all views consume it
- NEW Spacetime Grid view: 32 offenses x 18 weeks of 2026/27, every cell = opponent logo,
  color = opponent's Psi vs chosen slot, byes marked, rows sorted easiest->hardest by season SigmaPsi
- Matchup Lab: week selector (1-18) — opponents/ranks recompute live for any 26/27 week, BYE shown
- Insights energy states: now week-aware (wk 1-18 selector), computed live from depth charts +
  26/27 schedule + combined DvP (was frozen at week-1 matchups CSV); OUT players excluded
- All verified headlessly: 0 runtime errors; KC wk1=DEN / wk5=BYE / wk6=LAC confirmed in-render

## Production readiness (v5, final)
- games_2026.csv upgraded: ISO dates + PRECOMPUTED box score ids for all 272 games of 26/27
  (weekly in-season scrape needs no id discovery)
- scrape_state.json registers season 2026 (not_started)
- build_game_logs: position lookup now merges all positions_*.csv files with graceful fallback
  when positions_2026.csv doesn't exist yet
- scripts/refresh.py: one-command rebuild (game logs -> DvP -> matchups -> dashboard),
  auto-detects current 26/27 week from schedule dates, prints summary + anomaly report
  (raw ERR lines, stale depth-chart warning >9 days)
- notes/scrape_recipe.md: complete Chrome scrape recipe (box scores, depth charts, positions)
  so any future session can run the Tuesday refresh without rediscovery
- README.md: system overview, data flow, weekly runbook, status, known gaps
- Verified: full refresh.py run end-to-end clean; dashboard JS syntax-checked
- Note: scripts/_observatory.js is a leftover build fragment (already merged into
  dashboard_template.html); sandbox couldn't delete it — safe to remove manually

## Dashboard v6 (final polish)
- NEW Collision Chamber view: weekly comprehensive matchups — every game of any 26/27 week as a
  card: both offenses' slot owners (QB/RB1/RB2/WR1-3/WR4+/TE1/TE2) vs the opposing defense's Psi,
  each row carrying that defense's weekly-allowed waveform sparkline; field-tilt bar shows which
  offense faces the softer field; byes listed
- Waveform sparklines (inline SVG, smoothed, mu dashed, latest scraped season) added to
  DvP Rankings rows and Matchup Lab rows ("omega opp allows" column)
- Insights now carries a plain-English decoder: what Psi is per role, what FUSION/FISSION/
  momentum/uncertainty/geodesics each tell you
- games26 embedded in dashboard payload; build_dashboard.py tail-truncation repaired
- jsdom verification: 16 wk1 cards / 288 waves / tilt bars, wk5 bye note, 32+119 table waves, 0 errors

## Dashboard v7 — terminal edition
- Full Bloomberg-terminal restyle: pure black, amber command accents, inverse-amber active tabs,
  F1-F8 keyboard bindings for views, dense uppercase headers, no glows/gradients/backgrounds
- Insights rebuilt as decision screens: every TARGET/AVOID row now shows the opponent defense's
  actual per-game production allowed to that role with league rank per stat, defense L3 trend
  arrow, weekly waveform, and the player's own L3 PPR from the latest scraped season
- Collision Chamber rows: composite replaced with raw stats-allowed-per-game + rank next to
  every player (composite retained only as the per-side mean footer)
- Shared allowLine()/lbl() helpers keep Chamber and Insights formats identical

## Dashboard v8
- De-oranged: accent swapped from amber to steel blue (#58a6ff); column headers neutral grey;
  heat ramp desaturated (green -> muted olive -> red, no neon)
- Stat alignment: chamber + insights rows now use four fixed-width stat columns (ORDER map:
  QB PaYd/RuYd/PaTD/TD, RB RuYd/Rec/RcYd/TD, WR-TE RcYd/Rec/-/TD) — every value/rank pair
  lines up vertically; insights headers name each stat column per role
- Verified: uniform 4 .st cells across all 288 chamber rows + 70 insights rows, 0 errors

## Dashboard v9 — condensed to 5 screens + Home command center
- 8 tabs -> 5: F1 HOME / F2 WEEKLY MATCHUPS (chamber) / F3 PLAYERS (lab + collider merged,
  click a player row -> deep dive below) / F4 DEFENSES (rankings|matrix|observatory subtabs) /
  F5 SCHEDULE (spacetime grid). No content removed.
- HOME: system status, wk-1 board (best+worst matchup per role with raw allowed stats),
  field extremes per slot (bleeds most / locks down + waveforms), momentum top-6,
  volatility top-6, season slates (QB/RB1/WR1/TE1 easiest+hardest), and the full week-by-week
  insight screens below the fold.
- Verified: 5 nav buttons, subtab toggling, lab->collider click-through, 0 runtime errors.

## Dashboard v10 — position identity + illustrations
- Fixed position palette: QB #4fc3f7 blue / RB+FB #b388ff violet / WR #f06292 pink /
  TE #ffd600 gold / D-ST #90a4ae grey (chosen to never collide with the green-red heat ramp)
- Hand-drawn SVG glyphs per position (QB football, RB cutback arrow, WR route tree,
  TE block-and-release, D/ST shield) — 494 instances across screens
- Slot chips (glyph + label in position color) replace plain text in: home board, field
  extremes, movers/volatility, chamber rows, lab rows+tabs, rankings tabs, matrix headers,
  observatory hero, insight panel headers (headers now colored by position); legend on home
- Verified: chips render on all screens, 0 runtime errors

## Dashboard v11 — hard alignment + gridiron illustrations
- 47 tables converted to fixed layouts with explicit colgroups (chamber both sides, all insight
  target/avoid tables, home wk-1 board): every stat column now shares exact pixel positions
  across rows, tables, and cards; long names ellipsize instead of pushing columns
- Chamber tilt bar replaced with a drawn gridiron: turf, yard lines + hashes, midfield stripe,
  team-colored end zones, and a laced football sitting at the data-driven field position (16/wk)
- Header wordmark now carries a football; Schedule view gets a goalpost glyph
- Verified: 47/47 colgroups present, 16 field illustrations, 0 runtime errors

## Dashboard v12 — homepage curvature illustration
- One comprehensive general-relativity illustration leads the homepage: a spacetime sheet
  (10 gridlines, Gaussian deformation) bent by the week's best matchup at each of 7 roles.
  Well depth = 33-Psi from real combined DvP; opponent logo at the rim, player's team logo at
  the bottom of the well; labels carry player, raw stat allowed/gm, and Psi in position colors.
  Einstein field equation inscribed top-right. All data-driven, rebuilt on every refresh.
- Verified: 7 wells, 14 logos, 22 labels, deepest well = QB Dart vs DAL (251.9 PaYd/gm, Psi 1.8)

## Dashboard v13 — curvature sheet replaced with THE DRIVE
- The rubber-sheet illustration degenerated (all best matchups near rank 1 -> uniform max-depth
  wells -> wave spaghetti + label collisions). Replaced with a football-native drive chart:
  7 lanes (one per role), green PAYDIRT end zone at left, Psi gridlines as yard markers,
  each lane a team-logo ball carrier positioned by opponent softness with a momentum arrow
  p = (33-Psi) toward the end zone, opponent logo + raw stat allowed inline. Compact (310px),
  collision-free, readable at a glance.

## Dashboard v14 — hero finalized: WK1 SMASH BOARD (bullet chart)
- Drive chart replaced with a professional bullet-chart board: 7 rows (one per role), fixed
  columns (role, team logo, player, vs/@ + opp logo, bar, value, rank chip, Psi). Bar length =
  raw production the opponent surrenders per game to that role, scaled to the league max;
  dashed white tick = league average. Bars in position colors; everything on a fixed grid,
  collision-impossible. Verified: 7 bars/ticks/rank chips, 14 logos, 0 runtime errors.

## Data integrity audit (2026-07-14)
- scripts/verify_data.py: 45/45 checks passed — raw layer (272 boxscores/season, 0 ERR, 0 dups),
  coverage (32x17 both seasons, schedule-exact, reciprocal), fantasy formulas, slot utilization,
  INDEPENDENT pandas recompute of all 36,992 weekly DvP cells (0 mismatches), season averages,
  RANK.AVG descending rank math, combined blend, composites, D/ST attribution, dashboard payload
  equivalence (2,176 cells), weekly column mapping, schedule payload
- External: 6/6 player-season totals exact vs PFR player pages
- Legacy validation extended to 8 defenses: 86.7% cell-exact, same benign swap pattern
- Report: notes/data_audit_2026-07-14.md

## Dashboard v15 — five user revisions (2026-07-14)
1. Depth charts now visible: Players tab opens with a depth-chart viewer (team select, all
   position columns in depth order, Q/OUT flags, ESPN snapshot date + weekly re-pull reminder)
2. Players tab filters: depth (1st string only [default] / top 2 / all) + injury (hide OUT
   [default] / include) alongside existing team/search/week/source; QB tab now defaults to 32
   starters instead of 119 bodies
3. Home smash board expanded: QB RB1 RB2 WR1 WR2 WR3 WR4 TE1 TE2 + FLEX1/FLEX2 (best remaining
   RB/WR/TE, real slot shown); every row now carries the FULL stat line the opponent allows
   (yards, receptions, PaTD for QBs, total TDs) each with league-rank chip, plus primary-stat
   bullet bar vs league average
4. New F6 TD BOARD page: composite TD rankings for all 532 slot owners, any week — QB score =
   mean of PaTD + rush/rec TD ranks, others = slot TD rank; raw TD/gm, rank badges, TD waveform
5. Schedule grid formatting strengthened: cell tint alpha .30 -> .55, saturation tuned, and the
   Psi value printed in every cell next to the opponent logo
- Verified in-render: depth viewer 32 teams, filters 32<->119, 11 smash rows/36 rank chips,
  532 TD rows (#1 Dart: 1.9 PaTD rk1 + 0.5 ruTD rk1), sked tint+values, 0 runtime errors

## Dashboard v16 (2026-07-14)
1. Depth charts collapsible on Players tab (collapsed by default -> rankings immediately visible)
3. Smash board rebuilt in HTML (was SVG): grid rows with position rail, player+opponent stack,
   rounded primary-vs-league bar, four aligned stat blocks with rank chips, Psi column;
   FLEX = best remaining non-QB (any RB/WR/TE)
4. TD Board: right side now carries a TD-volume bar per row (scaled to that role's league range,
   tick = league avg, colored by TD rank); moved to nav slot 2 (F2), Weekly Matchups -> F3
5. Schedule heat strengthened again: solid tint (alpha .8), bold dark Psi values in-cell
NEW: player popup cards — click any player name anywhere (smash board, TD board, chamber,
   insights, home board, lab): per-season + overall averages, ppr sparkline, history vs next
   opponent, what that opponent allows to his slot, last-10 log, deep-dive shortcut; ESC/overlay
   closes. Verified: nav order, collapse toggle, 11 smash rows/44 stat blocks, 532 TD bars,
   popup open/sections/close — 0 runtime errors

## Dashboard v17 (2026-07-14)
3. FLEX pool restricted to RB1/WR1/WR2/TE1 (now Gesicki TE1 + Mike Evans WR1); FLEX rows get
   their own identity: white rail/label with a star glyph (no longer TE gold)
4. TD Board bars redesigned: contained rounded track with border, gradient fill, in-bar
   league-avg tick and the raw TD/gm value printed inside
5. Schedule heat switched from continuous ramp to 6 discrete bands (greens -> slate middle ->
   reds, no yellow mush); ranks 15 and 19 now land in visibly different bands; legend added;
   in-cell values white bold
- Popup fixes: deep-dive button now switches view AND scrolls to the rendered dive; popup shows
  the FULL latest-season (2025) game log for every player (2024 via deep dive)
- Verified: flex = TE1+WR1 white rails, 532 labeled TD bars, bands distinct, deep-dive renders

## Dashboard v18 (2026-07-14)
- TD COLLIDER scatterplot atop the TD Board: x = TD matchup rank (reversed, right = softest
  field), y = the player's own TDs/gm from 2025 (passing incl. for QBs); 130 team-logo points,
  dashed quadrant lines at rank 16.5 and mean TD rate, quadrant captions (FUSION CORE / PROVEN
  BUT WALLED OFF / OPEN FIELD UNPROVEN / DEAD ZONE); reactive to week + position filters;
  tooltips carry player/rank/rate
- Player popup gains a second tab: "<slot> dvp rankings" — all 32 defenses vs that player's
  role (Psi-sorted, per-stat avg + rank), with his week-1 opponent outlined in cyan
- Verified: 130-point scatter w/ quadrant plugin, popup tab toggle, 32 ranking rows, opponent
  highlight, 0 runtime errors

## Dashboard v19 — FINAL (2026-07-14)
- TD PHASE SPACE scatter added beside the collider: all 32 defenses plotted by passing TDs vs
  rushing TDs allowed /gm (computed live from raw 24-25 game logs), team-logo points, league-mean
  crosshairs, and Sigma equipotential contours (total TDs/gm iso-lines at 1.6/2.0/2.4/2.8) —
  the TD rankings themselves, as a field
- Bars everywhere now grow in with a physics-curve ease (cubic-bezier); header carries p=mv
- Verified: 32 defenses plotted (KC 1.24 air/0.79 ground ... ), equipotential plugin attached,
  130-pt collider intact, 0 runtime errors

## Dashboard v20 (2026-07-14)
- TD Board filters: slot scope (core = one WR4 per team [default] / every body / any single
  slot group) + team filter, alongside week + position
- True WR pecking order labels EVERYWHERE: bench WRs now labeled WR4, WR5, WR6...WR12 by
  team-wide depth order (starters WR1-3, then bench by depth+row); applies to TD board, Players
  tab, popups; chamber/home now pick the top-ordered body for WR4+/TE2 slots
- Verified: core default = 288 rows (QB1..WR4,TE2), all-bodies = 532 with WR1..WR12 labels,
  team filter -> 17 rows for KC, 0 runtime errors

## v21 — FINAL: mobile + verification + GitHub (2026-07-14)
- Mobile: viewport meta, inline football favicon, responsive media queries (<=840px: single-column
  grids, horizontally scrollable panels/tables, compact nav without F-key chips, tighter controls)
- Final data verification: scripts/verify_data.py 45/45 PASSED post all UI changes; final render
  smoke: 6 nav, 10 home panels, 11 smash rows, 288 TD rows, 16 chamber cards, 32 sked rows, 0 errors
- Git repo initialized (built on native fs, copied to mount — the mount corrupts git's atomic
  writes, documented here for future sessions): commit d5daab9, 50 files, clean status, fsck clean
- README finalized with views summary + audit status
