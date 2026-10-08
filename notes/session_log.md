
## 2026-07-26 — weekly refresh (scheduled, off-season)
- No 2026 weeks complete (season starts 09-09) — box score scrape skipped. positions_2026.csv not yet on PFR (fantasy page empty pre-season); inference fallback in use.
- ESPN depth charts re-pulled (32 teams, 1272 rows) -> depth_charts_2026-07-26.csv.
- refresh.py + verify_data.py: 45/45 PASS.
- Data quality: Bo Melton (GB, 2025 wks 6/11 + 1 more row) re-inferred RB3->WR4+ because the 07-26 ESPN snapshot lists him at WR and positions_2026.csv is absent. 3 game-log rows changed; minor DvP cell shifts vs 2025 RB/WR slots. Will self-resolve once positions_2026.csv exists; acceptable.

## 2026-09-13 — review + global filters (wk 1 Sunday, pre-scrape)
- NEW scripts/build_kickoffs.py -> data/processed/kickoffs_2026.csv: day / time_et / slate for all 272 games.
  Source: data/raw/pfr_games_2026.md (weeks 1-13 + part of 14; the dump is truncated) +
  data/raw/pfr_week_pages_2026.txt (PFR /years/2026/week_N.htm, weeks 14-18). Wk 18 = TBD (NFL flex).
  Slate counts: TNF 19 · EARLY 131 · LATE 58 · SNF 17 · MNF 17 · INTL 6 · THU 2 · FRI 4 · SAT 2 · TBD 16.
- refresh.py now runs build_kickoffs.py; build_dashboard.py emits games26 = [wk,vis,home,date,day,time_et,slate] + J.week.
- Dashboard: sticky global filter bar (week / slate chips / game / team) -> every view re-renders via RR hooks.
  Removed the per-view week + team selects (lab, insights, chamber, TD board) in favour of the global bar.
  Home / popup cards / player trajectory now use the global week instead of hard-coded wk 1.
- Verified: verify_data.py 45/45 PASS; headless Chromium smoke test across all tabs + filter combos: 0 JS errors.
- Not done this session: 2026 wk 1 box-score scrape (games still in progress) — run the scrape recipe Tuesday.
- (b) URL-hash filter state (readHash/writeHash, hashchange listener, link button copies it); Home slate map
  (click a window -> G.slate); Weekly Matchups grouped under slate headers; sortable Kick column in Matchup Lab,
  slate column in TD Board; .github/workflows/pages.yml (Pages via Actions). Smoke test: 0 JS errors.
- (c) FIX: DvP rank badges were clipped out of the fixed-width stat cells (table.fx 92px cols + ellipsis) on
  Weekly Matchups / Home board / Insights — e.g. "219.6 PaYd…" hid the rank. Badge now renders first, stat cols
  104px, td.st no longer ellipsizes. Verified 60/60 badges inside their cells on a game card.
- (d) Multi-select: G.slates (Set) + new G.pos (Set, QB/RB/WR/TE/D-ST) with `inP(posOf(slot))` applied in lab tabs,
  rankings tabs/ALL columns, matrix columns, chamber rows, TD board, home boards/extremes/movers/SOS, insights, schedule slot.
  Hash: slate=A,B&pos=X,Y. TD board's local pos select removed. Smoke test: 0 JS errors.

## 2026-09-17 — week 1 scraped, week 2 matchups live
- 2026 wk 1: 16/16 box scores via Chrome (317 raw lines, 0 ERR) -> game_logs_2026.csv 314 rows, 3 D/ST TDs.
  Transcription verified by char-count + code-sum checksum against the in-page accumulator.
- positions_2026.csv pulled from PFR fantasy page (425 players) — inference fallback now only 2 rows.
- ESPN depth charts re-pulled 2026-09-17 (32 teams, 558 skill-position rows; OL rows no longer stored).
  Parser JS now lives in notes/scrape_recipe.md.
- refresh.py auto-detected wk 2; matchups_current = wk 2. dvp_combined stays 2024+2025 until 2026 has >=4 weeks
  (compute_dvp label fixed — it previously printed 2026 in seasons_blended even when excluded).
- Dashboard: TREND_SE = latest season with >=4 weeks drives waveforms / momentum / volatility / Observatory default
  (2025 for now; flips to 2026 automatically at wk 4). 2026 is selectable as a DvP source.
- verify_data.py made in-season aware (expected boxscores/team-games derived from scraped weeks): 64/64 PASS.

## 2026-09-23 — week 2 scraped, week 3 matchups live
- 2026 wk 2: 16/16 box scores (324 raw lines, 0 ERR, checksum-verified) -> game_logs_2026 636 rows, 5 D/ST TDs.
- ESPN depth 2026-09-23 (562 rows). Notable: Jayden Daniels O, Caleb Williams D, Goedert D, Reed D, Dart O (Winston QB1 NYG),
  Njoku/Kolar O (LAC), Slayton now IND WR3. New 'D' (doubtful) tag observed — already in OUT_TAGS.
- refresh -> wk 3; blend still 2024+2025 (flips at wk 4). verify_data 64/64. Smoke test 0 JS errors.

## 2026-09-27 — advanced layer: usage, scheme tags, turnover, coaching (Intel tab)
- New sources (public nflverse releases, fetched from the cloud workspace via scripts/fetch_nflverse.py; the desktop
  VM cannot reach github.com): snap_counts, ftn_charting, pbp_participation (2024-25), rosters, depth_charts,
  play-by-play slimmed to 45 cols (data/raw/nflverse/, ~24 MB, committed so the desktop build is offline).
- scripts/build_advanced.py (~7 s from cache): player_usage (11,338 rows joined to game_logs by PFR id),
  team_off/def_tendencies (96 rows each), scheme_tags (192), starter_turnover (128), coaching (96),
  scheme_slot_effects (45).
- Coordinators: 96 HC/OC/DC rows scraped from PFR coaches pages into data/raw/coordinators.csv (blanks filled
  as "<HC> (HC calls ...)"). 2026: 15 new DCs / 21 new OCs / 10 new HCs. New-DC tags inherit the DC's prior
  charted unit (BAL←MIA Weaver, NYG←TEN D. Wilson, PIT←LV P. Graham); other new DCs fall back to the same
  team's 2025 charting and are flagged "NEW DC — verify" in coverage_source.
- Tagging v2: dominant-shell + man/two-high overrides (defense), PROE + percentile tree (offense) — replaced
  v1 which left 15/32 defenses "Multiple" and 22/32 offenses "Pro-style mixed".
- Dashboard: Intel tab (F7) with 4 sub-tabs + drill-downs, obeys global filter (inD for defenses, inF for
  offenses/usage); LOG rows carry snaps/snap%/tgt share/aDOT/rush share/WOPR (indices 22-27); Lab gets snp%/tgt%
  columns (season-to-date, sortable); player card + deep-dive logs show snp%/tgt%/aDOT; game cards show each
  defense's DC + scheme tag. Payload 2.39 MB. Smoke test (Playwright, all tabs + filter interplay): 0 JS errors.
- refresh.py now runs build_advanced.py when the nflverse cache exists (fetch step documented in README).

## 2026-09-27 (b) — seamless UI + insight layer on top of the intel data
- Signals (dashboard_template, all client-side from J.intel + logs): trust(def) 0-100 = 100 − 70×(1−returning starter
  snap %) − 18 if new DC + 3/wk of 2026 data (capped 6); envOf(vis,home) scoring index / pace / plays / PROE with
  week-relative percentiles → tags fast/slow, pass/run-lean, shootout/rock fight; schemeEdge(def,grp) from
  scheme_slot_effects; roleMoves() last 2026 game vs season-to-date snap%/tgt share (min 30% snaps, |Δ| ≥ 12 pts).
- Home: "wk N intel brief" panel under the smash board (environments ranked, fragile priors, role movers,
  scheme edges capped 2 per slot, TE2/WR4+ excluded as low-volume). Game cards: trust pills + env line.
  Player card: DC/scheme/trust/scheme-edge/role line. Lab: sch column + snap arrows.
- UX: Ctrl-K or "/" command palette (players + teams, keyboard nav); click any team code → team filter toggle;
  view fade-in; compact filter-bar buttons; header data counts computed (24/25 + 25/26 + 26/27 · 576 GM · 11,338 rows).
- Smoke test (Playwright): brief renders 48 rows, palette opens Justin Jefferson, team-code click sets BAL filter, 0 JS errors.

## 2026-09-27 (c) — roster filter, my-lineup, Ψ+ conviction
- build_matchups.py: cross-team fallback (last name + first initial + position, unique) and fuzzy last-name match
  within team (Judklins→Judkins); the Master Key team column is draft-day, so 60 traded/signed players now resolve
  to their current team. 42 still unmatched = not on any ESPN depth chart (FA/IR/retired: Mixon, Thielen, Ertz…).
- Dashboard: G.owner + inO/inU; ROSTER select + hash owner=; lineup() panel (1 QB·2 RB·2 WR·1 TE·1 FLEX by Ψ+,
  OUT/bye never start); conv() = 0.55 DvP(Ψ→0-100, shrunk toward 50 by trust) + 0.15 scheme + 0.15 env + 0.15 role;
  Ψ+ column in Lab (sortable) and player-card context line; game cards tag each starter with his owner and
  highlight/dim rows when a roster is selected.
- Smoke test: 12 owners, Blitz → 14 rostered + 2 off-chart, 7 suggested starters, 0 JS errors.

## 2026-09-27 (d) — Big Board: projections + rankings
- projection(u,wk) in dashboard_template (cached per apply): baseline shrunk to slot league mean (LG_PPR from DvP
  combined via pprAllowed), × matchup (trust-shrunk) × scheme (half) × env × role; range from own quantiles.
  Sanity: wk 3 top = Gibbs 27.5 (NYJ), Henry 24.6, Allen 24.3, St. Brown 23.6, CMC 23.6; QB1 Allen, TE1 McBride.
- Big Board view (F2): ALL/QB/RB/WR/TE/FLEX, starters/all-depth, hide OUT, search, CSV export, 23 sortable columns,
  positional ranks computed on the full starter pool so pos# is stable under filters.
- Home top-12 + lifts/drags panel; My Lineup now ranks/picks by PROJ (Ψ+ kept as a column); player card PROJ line.
- Nav reordered to F1 Home · F2 Big Board · F3 Matchups · F4 Players · F5 Defenses · F6 TD Board · F7 Schedule · F8 Intel;
  "?" glossary modal; tab switch scrolls to top. Sticky-header fix: tables inside overflow containers use static th
  (Intel) or no overflow wrapper (Big Board).
- Smoke: 331 rows on the board, 0 JS errors, load 1.8 s headless.

## 2026-09-27 (e) — Model Lab backtest + re-tune
- runBacktest(): 6,009 player-weeks (2025 with 2024 DvP / 2024 env / 2025 coaching+turnover; 2026 wk1-2 with the live
  2024+2025 config), walk-forward baselines. tuneModel(): 324-point grid over matchup weight/mode, trust, scheme, env, role.
- Results (starters, Spearman ρ): baseline .594 · raw prior DvP ×1 .571 · tuned .601. Quintile spreads (actual ÷ baseline,
  hardest→softest): prior DvP ratio 0.956→1.003 (+4.8 pts on a 56-pt ratio swing), blended DvP 0.91→1.00, scheme idx
  0.875→1.03 (near 1:1), role Δ 0.90→1.08, env ≈ flat. By position DvP matters most for QB/TE, ~zero for WR.
- MODEL re-tuned accordingly (matchMode blend k4, matchByPos, schemeW 1, envW .1, roleW .6 clamp .25); live projection()
  and the backtest share applyW()/rawRatio() so the lab reports exactly the live configuration.
- Wk 3 board after re-tune: Allen 24.8, Gibbs 24.5, St. Brown 21.9, Henry 21.1, JSN 20.5.

## 2026-09-29 — week 3 refresh · Games & Picks · props
- Wk 3: 16/16 box scores (336 lines, 22,977 chars, checksum 1,931,399 verified), 317 game-log rows, 3 D/ST TDs; parseBox
  now emits S| final-score lines — all 16 match nflverse results. ESPN depth 2026-09-29: 567 rows (notables: Josh Allen Q,
  Jayden Daniels Q, Caleb Williams D, Baker Mayfield O, Etienne O, Achane IR, Goedert D). refresh -> wk 4; verify 64/64.
- Spot checks: Bijan 29-194-2 + 2-19 = 35.3 PPR; JSN 10-128-2 (+1/1 14 pass) = 35.36; Allen 204-0-2 INT, 22 rush 2 TD,
  1 rec, fumble = 17.46. Snap-count join 100% for wk 3.
- fetch_games.py (nflverse nfldata) -> game_lines.csv 816 games 2024-26 incl. wk 4-5 lines. build_games.py: SRS-style
  margin rating (corr with result .41 vs EPA-rating .17 vs market .50); model spread MAE 10.25 vs market 9.67; ATS by
  |edge| bucket never clears 53%; totals with edge ≥3: 113-94. ML disabled (41-101). 16 wk-4 picks frozen 2026-09-29.
- Props: ESPN core API propBets (provider 100 = DK) — 1,295 markets/game incl. milestones/quarters; kept full-game totals:
  128 markets, 46 players, 6/16 games posted on Tuesday. build_props.py per-stat projections; 36 leans frozen.
- Dashboard: Games & Picks tab (F9) — matchup cards (market vs model vs ratings vs env/scheme/trust), ledger with
  frozen/retro/backtest records, props table. Payload 2.83 MB. Smoke: 16 cards, 67 ledger rows, 36 prop rows, 0 JS errors.

## 2026-10-01 — Matchup Lab multi-position
- lab(): posSet (Set) replaces single pos; ALL button; single-position layout unchanged (per-stat rank + raw columns);
  multi-position layout = common cols + Ψ/Ψ+/PROJ + one stat line (badge + raw per stat for that player's slot) + ω.
  Sort keys r*/v* only valid in single mode (reset to Ψ on toggle). Global POS filter hides buttons and prunes posSet.
- Smoke: QB 30 rows, QB+RB 61, ALL 185, RB-only 31, global WR filter → 94 rows with QB/RB/TE buttons hidden; 0 JS errors.
- (b) Multi-position view reworked after feedback: instead of one combined stat line, a shared sortable grid
  (PaYd · PaTD · RuYd · Rec · RcYd · TD · P+R/R+Y) with rank badges and raw columns; each slot's stats map into the
  matching column (ucol), blanks where not applicable, nulls sort last in either direction.

## 2026-10-02 — Mobile UI + lazy rendering
- Render registry: RR.push tags each re-render hook with its view (BOOT array). apply() clears PCACHE, runs only the
  visible view's hooks and marks the rest DIRTY; nav click runs a dirty view once. intel() no longer calls render().
- Mobile CSS (≤840px): #gTog toggle (`#gbar:not(.open)>*:not(#gTog):not(#gSum){display:none}` — the earlier `.open`
  rule lost on specificity to the :not() hide rule), chips wrap, select full width, overflow-x on .tbl/.card tables,
  table.fx auto layout, gamecard 1-col.
- Measured (Playwright iPhone 13, Chart.js stubbed): load 908 ms (was 2913), apply 138 ms (was 598), board 464 ms,
  chamber 108 ms; perr/smoke8 0 JS errors. Screenshots home/filters/board/chamber/players/games verified.
- Next: RAINMAN v2 (new UI shell) — prompt at notes/rainman_v2_prompt.md; v1 stays live at the root.

## 2026-10-05 — College layer
- ESPN site.api blocked from the cloud proxy and CORS-blocked in Chrome; sports.core.api.espn.com works in Chrome:
  817 college-football teams (id, color, alt color) + 2025 FBS(80)/FCS(81) group children -> conference. Matched the
  184 nflverse college strings (first-listed school) by location + a 40-entry alias table -> data/raw/colleges_espn.txt.
  Large JS results: write to document.body and read with get_page_text (javascript_tool output truncates ~1 KB).
- build_dashboard.college_payload(): pfr_id -> roster 2026/25/24 college, entry_year, draft_number, draft_club; depth-chart
  names matched exactly, then suffix-normalized, then last name + team, plus alias (Hollywood Brown -> Marquise Brown).
  Coverage: 888 players, depth chart 567/567.
- UI: cinfo/ccell/cbig/clogo helpers (500-dark logo variant with fallback to 500); Players lab College column + #labCol
  filter; Big Board College column + CSV cols; depth-chart logos (names now open the player card). 0 JS errors.

## 2026-10-05 (b) — Two-team depth charts
- dchart() rewritten: #dcGame (week's games) · #dcTeam vs #dcTeam2 · swap; mirrored table.dct (left team | position | right
  team), header with logos, home/away and kickoff. RR hook syncs to G.game (both teams + auto-expand) or G.team (+ its
  opponent via gameOf). Mobile: fixed layout, names wrap, no horizontal overflow at 390 px. 0 JS errors.

## 2026-10-05 (c) — Locker Room: birthdays, rivalries, player-venue connections
- ESPN core API in Chrome: athletes/{espn_id}.birthPlace for 735 players (2025-26 logs + depth chart) ->
  data/raw/espn_birthplaces_2026-10-05.txt; college-football teams/{id}.venue -> data/raw/colleges_venues.txt (Illinois
  venue corrected: ESPN returned Foster Stadium, Lexington VA). Stadium coords: data/raw/nfl_venues.csv (38 incl. 8
  international). Device + cloud proxies block ESPN, and GitHub's CSP blocks fetches from the upload page, so Chrome
  results were read via get_page_text and saved as files.
- scripts/build_connections.py (in refresh.py): geonamescache (pop >= 500) geocodes 600/600 birthplaces (9 small places
  mapped to the nearest GeoNames town); per 2026 game: homecoming <=100 mi, home state, college town <=100 mi, revenge
  (2024/2025 roster team or draft club = opponent), birthday game. 825 rows. Players = box score for played weeks,
  depth chart for upcoming weeks.
- Dashboard: J.college.bd (birth dates), J.conn (connections + birthplaces). JS: RIVALS (85 pairs, MARQUEE 38), clashPair()
  cached per team pair from depth charts; key clash = marquee + a starter on both sides (wk 4: 12; season: 212).
  F10 view (Storylines / Birthdays / Rivalries), Home social slot, chamber storyline <details>, depth-chart tags, popup
  line. 0 JS errors; mobile 390 px no overflow.

## 2026-10-05 (d) — collapsible depth charts + waiver radar
- dchart RR hook no longer calls open(true) on G.game; storyd <details> default closed (chamber + depth chart).
- G.owner='__FA__' = unrostered (inO / chamber mine / gSum label); lineup() renders waiver(slot,full) when no roster
  (top 8) or FA (top 60). Role gate excludes backup QBs/no-snap players (projection fell back to slot means for them).
- Deploy note: Actions run #20 failed with "job was not acquired by Runner of type hosted" (GitHub-side); re-run queued.

## 2026-10-05 (e) — v2 UI shipped as the main site
- v2 = skin over v1 (same payload/formulas): build_dashboard_v2.py injects Google Fonts Inter + skin.css + skin.js into
  the built rainman.html -> dashboard/v2/index.html. skin.js moves header/nav into an aside#rail (SVG icons, spring
  indicator), adds .v2hero per view + Home .kpis, wraps window.runView for count-up/hero refresh, view enter + panel
  stagger, mousemove tilt on .gamecard/.story. Gotchas: font shorthands need a fallback (headless had no Inter);
  overflow-x on panels breaks sticky th (only grid children scroll, their th are static).
- pages.yml: root + /v2/ = v2, /v1/ + /rainman.html = classic. refresh.py runs build_dashboard_v2.py.
- Playwright: home/board/chamber/players/games/locker/popup/mobile 0 JS errors; 390 px no overflow.

## 2026-10-05 (f) — v2 refinement + revert safety
- dashboard/archive/: frozen v1 (f13c159) + v2.0 (e57433e) builds, published at /archive/ by pages.yml.
- skin.js polish() via debounced MutationObserver on <main>: capH, alignHeads (th align = first data row td align),
  notes (>=150 chars -> .infob chip), collapsible (panel>h3 without id/controls; localStorage rm.v2.col; Home deep
  panels default collapsed by title regex), homeOrder (#homeTop display:contents + CSS order), overflow (.hscroll).
- Bugs caught: #home{display:flex} overrode [hidden] (home rendered under every tab); regex /board — best/ matched
  "smash board — best matchup"; custom-toggle h3s (#mlToggle/#dcToggle) excluded from collapse.
- Template: storyBlock non-compact = marquee&top rivalries + connections, rest in <details class="storymore">.

## 2026-10-05 (g) — betting layer + Bet Board
- New: build_adjusted_dvp.py, build_prop_model.py, build_bets.py, fetch_odds_api.py (key only in .env). Template DSRC =
  'adjusted' default for every matchup ranking view (15 usages); betting_payload() → J.betting.
- Bet Board module (template, before BOOT): tabs Props/TD/SGP/Ledger/Model; Gaussian copula (Cholesky + seeded
  mulberry RNG, 40k sims) with corr fallback RB2→RB1, WR3→WR2→WR1; same-player legs ρ=.55; localStorage rm.slip,
  rm.bets, rm.bankroll, rm.kelly, rm.sgpPrice. Name clash: `BT` already used by Model Lab → BETS.
- v2: lands on Bet Board unless hash contains "home"; KPI "best prop edge" (n_eff≥3); 6-col KPI grid.
- model_validation.md rewritten: DvP backtest table + props section replaced in place by build_prop_model (markers).
- Playwright: v1/v2/mobile all tabs 0 JS errors, 390 px no overflow. Wk4 lines are DK (unpriced); wk5 after Tuesday refresh.

## 2026-10-06 (a) — Tuesday refresh (wk 4 partial) + prop-model fixes
- PFR wk 4 box scores (15/16; MNF ATL@NO pending) appended to box_lines_2026.txt (306 lines, checksum verified);
  scrape_state boxscores_done lists them. ESPN depth 2026-10-06 (578 rows). DK wk 5 props (TNF + PHI@JAX only so far;
  ESPN core API names now carry " (incl. overtime)" — stripped; timestamp field is lastUpdated).
- build_games.py: ledger res_* columns read back as float when empty -> cast to object before grading.
- build_prop_model: gprior (QB1/QB2 split), role() weighting grid GRID_R, per-market mean scale, effective_slots() next man up.
- build_bets: wt(n_eff) evidence-scaled model weight; ledger gains n_eff; wk 5 rows frozen pre-fix were removed and refrozen
  (no games played yet). Template: ledger by EV bucket/market + week filter; Sides & totals tab.

## 2026-10-06 (b) — IA consolidation
- Template nav = 5 section buttons (data-sec) + #subnav (inside #top) built by go(v); SECS/SECOF/VLBL/ALLV/CURVIEW/LASTV;
  go() dispatches 'rm:view' (v2 skin listens for indicator + hero). apply() uses CURVIEW. F1–F5 = sections.
- New panes: mlab (lab moved out of players), trends (insights rest() -> trendsView()), fantasy (#lineupSlot), home gets
  #homeBot (brief + slate map). Deleted: homeBoard(), socialHome(), home best/worst, momentum, volatility, SOS, system panel,
  games props() + BET.props payload, betboard sides() -> global sidesTable() at top of games matchups().
- v2: VIEWS per pane, KPIs on bets (games/plays/edge/smash/storylines), homeOrder + order CSS removed, betstatus collapsed by default.

## 2026-10-06 (c) — v3 redesign
- skin.css rewritten (tokens: --money #19e68c, --signal, --hot, --ice; fonts Barlow Condensed + Inter). skin.js: header#hdr
  (brand, nav moved in, sliding .ind, search + glossary), #ticker (EV>=3 lines, duplicated run for loop, click -> playerPop),
  footer#ftr (data meta), notes clamp (.v2note) instead of infob chips, countUp only on .kpi .v (table numbers no longer animate).
- Template: hs() headshots (J.ph name->espn id from roster_2026 via pfr_id / name+team), PLOG/MSTAT/mhist/hitStrip/mAvg,
  playsStrip() top-plays cards, props columns Last 10 + L5 avg, popup lines block, smash board + depth-chart starter headshots,
  LOG.cmp (index 28). Local screenshots: npm @fontsource fonts served through playwright routes (google fonts blocked here).

## 2026-10-06 (e) — revert to v1 + F11 Bets + NCAA layer
- Main site = original v1 terminal (f13c159 template) + additive F11 Bets tab (prop-research layout: list of hit-rate pills,
  research pane with game-by-game chart vs an adjustable line, alt-line ladder, splits, opponent panel, model as labeled
  reference; "every starter" research mode defaults to the player's last-10 median line). Games & Picks keeps the model.
- NCAA FBS: `ncaa/` league root + `scripts/ncaa/` (fetch_cfb, build_game_logs, build_schedule, compute_dvp, build_lines,
  build_depth_matchups, refresh). 50,176 player-game rows 2024-26 (2,742 FBS-involved games), 138 defenses, DvP ties out
  to the box (OSU wk1 2025 QB PY allowed 170 = Arch Manning). Template is league-aware via J.league (TEAM map, LOGO/HEAD
  paths, slates, NWK, NT-scaled rank colors, conference filter, hidden tabs); NFL page byte-identical in behavior (0 errors).
- Sandbox cannot reach ESPN; GitHub raw/releases can. 2026 lines = ESPN odds pulled in Chrome (448 games: wk 6 scoreboard +
  wk 1-5 summary pickcenter). pages.yml now also publishes ncaa.html + archive/.

## 2026-10-06 (f) — v2 shell: task-based navigation + restyle
- Restore point first: dashboard/archive/rainman_v1.2_2026-10-06.html + ncaa_v1.0_2026-10-06.html, scripts/archive template copy,
  notes/restore_points.md (commit 8d03e1d / tag v1.2-pre-revamp).
- Shell: #app = #side (brand + league switch, find, SECTIONS nav with descriptions, footer) + #body (#top sticky: breadcrumb
  header with view description, week, summary; #gbar filters) + main (containers unchanged). Legacy nav kept hidden in
  #legacyNav as the routing model; go(id) clicks it, then selects sub-panels (players: #dcView/#lab/#player; defenses:
  #defTabs; bets: #r11Tabs; home: [data-sub] wrappers overview / insights / fantasy). Hash gains v=<view>. Keys 1-9.
- Sidebar collapses to a numbered rail (localStorage rm.side). Container query stacks the two matchup tables when main
  < 1340px so player names never truncate. Panels scroll horizontally instead of the page; th no longer sticky.
- Style: tokens (--bg #0a0c10, --panel, --s2/--s3, --edge, --accent #f0b429), Inter + JetBrains Mono via Google Fonts,
  rounded cards, uppercase mono th, chips/selects/tabs restyled; F11 r11* components mapped to tokens.
- Explorer opens with quick picks (this season's top PPR scorers per position); depth charts auto-expand in their view.
- Verified: Playwright tour of every sidebar item, NFL + NCAA, 1500 and 390 px: 0 JS errors, scrollWidth == viewport.

## 2026-10-06 (g) — top bar replaces the sidebar
- Josh: "i dont like the sidebar" -> chose a two-row top bar. #hdr = brand + league switch, #tnav section tabs, find /
  week / glossary / share; #sub = #snav views of the active section + #crumb one-line description; #gbar unchanged;
  footer .sfoot carries the data provenance. Removed #side, #rail, side-min/side-open, #gTog. Clicking a section tab
  returns to the last view used in it (SEC_LAST). Mobile: section tabs wrap onto their own scrollable row.
- Verified: Playwright tour of every view, NFL + NCAA, 1500 and 390 px: 0 JS errors, scrollWidth == viewport.

## 2026-10-06 (h) — Matchup board is the landing view; player averages
- Josh: the filterable / sortable player list vs opposing defensive ranks is the most valuable part; wants player
  averages for the current season and cumulative 2024-26, NFL + NCAA.
- `lab` is the default view (no hash). (Briefly renamed "Matchup board" / moved under "This week" — reverted, see (i).) Column groups: opp DvP rank | model (Ψ Ψ+ PROJ) | player avg / gm | opp allows / gm | ω.
- Player averages: statOf(col, logRow) maps every DvP stat column to the player's own game-log stat (QB TD = rush+rec TD,
  P+R, R+R); avgOf over PLOGS[player] for LAST_SE (current season) and all seasons; #labAvg picks which leads the cell
  and sorts (the other sits small); ▲/▼ compares the lead average to the opponent's allowed/gm; GP = season · all.
  Multi-position grid gets the same via the unified columns (x0..x6). Sticky player column; College column NFL-only.
- Verified: both leagues, 1500 + 390 px, 0 JS errors, no page overflow (board scrolls inside its panel).

## 2026-10-06 (i) — original tab names back
- Josh: "just go back to the old tab header names". Top row = the eleven v1 tabs with their F-key labels (Home, Big
  Board, Weekly Matchups, Players, Defenses, TD Board, Schedule, Intel, Games & Picks, Locker Room, Bets); row 2 = the
  original sub-tabs (Overview/Insights/Fantasy · Matchup Lab/Player Explorer/Depth Charts · Rankings/Matrix/Observatory ·
  Player props/Anytime TD/Game lines); single-view tabs hide the sub row's tabs. F1–F11 route through go(); number keys
  dropped. F-key labels and the find-button text hide under 1750 px so all eleven tabs fit at 1500. Item ids unchanged
  (hashes still work; lines2 aliases glines). Matchup Lab stays the landing view.

## 2026-10-06 (j) — pro skin: black background
- Josh: "the only rule is black background. everything else is up to you. make it professional."
- Tokens: --bg #000, --panel #0b0b0c, --s2/--s3 graphite, --edge #1d1e21 / #2a2b30, neutral greys (no blue tint),
  accent #e8b339 used only for active tab underline / league switch / links; selected chips are white-filled.
- Rank badges: gradeStyle() tinted pills (hue from gradeH, translucent bg + colored figure + inset hairline) replace solid
  blocks; gradeColor desaturated; matrix bands muted; POSC muted. Panels radius 4, no fade animation, th 9.5px caps.
- Slate map packs windows into CSS columns (.smap) instead of a 3-col grid with tall empty cells.
- foldNotes(): any .controls > .note over 90 chars becomes a ? hint chip (hover / tap shows the text); MutationObserver
  re-folds after re-renders.
- Verified: both leagues, 1500 + 390 px, 0 JS errors, no page overflow.

## 2026-10-06 (k) — effective depth charts + player averages on every player tab
- Josh: rosters must reflect long-term injuries (Daniels QB1 for TB while Mayfield is out; Kamara RB1 with Etienne on IR,
  Miller vs Donaldson for RB2), then bring every tab to the Matchup Lab's level of detail.
- build_depth_chart.py rewritten: effective slots (OUT last, usage-adjacent swaps for RB/TE/WR rows, WR starters ordered by
  L2 targets), note / trend / l2 / se / gp / espn_depth / log_name columns. 10-06 snapshot rebuilt from the raw ESPN dump:
  53 effective changes (TB QB Daniels, CHI QB Bagent, WAS QB Kaliakmanis, NYJ RB Allen, PHI TE Ertz, MIN WR Felton, ...).
  NO backfield unchanged by rule (Miller 16 vs Donaldson 6 opps L2) — the trend glyphs carry the story instead.
- build_prop_model.effective_slots() trusts a snapshot that already has espn_depth (no second re-slotting).
- Template: UNIVERSE gains ln/note/trend/l2/se/gp/espn; PLOGS/USG joins use the log name (Kenny -> Kenneth Gainwell,
  "Jr." suffixes); trendGlyph() on Lab, Big Board, TD Board, Weekly Matchups, Depth Charts. Weekly Matchups cells show
  "his <avg> ▲/▼" under what the defense allows; TD Board gets his TD/gm (season · all · gp); Big Board gets PPR/gm
  (season · all · gp); Depth Charts show effective order, strike-through OUT, workload 12/9, "esp N" when ESPN differs.
- Verified: both leagues, 1500 + 390 px, 0 JS errors, no page overflow.

## 2026-10-06 (l) — v3 visuals: Home, TD Board, Schedule, Games & Picks, Intel, Locker Room, Bets
- Josh: "far too much wasted space and unholistic views on the homepage. make new visuals. drastic improvements" to the
  seven tabs above.
- Primitives: kpi(), hbar(), tiltBar(), heatCell(), meanPsi(); CSS .kpis/.kpi, .hg2/.hg2b/.hg3, .srow/.rrow, .heat, .tdcards,
  .sk heat grid, .gboard, .wkbars, .tagmx, .mkchips. Home composition rewritten (slate map + smash board + two projection
  tables → KPI strip, slate board, role board, movers, single projections table with PPR/gm, DvP field heat). TD board:
  fields by role + anytime cards (rush+rec rate × field) + folded plots. Schedule: lens/sort/summary columns, abbr cells.
  Games: board table, <details> cards (open for the filtered game), weekly bars, props tab retired. Intel: #inWeek scheme
  edge table (offense × role, starter named). Locker: thread matrix + sorted collapsible cards. Bets: #r11Kpi + market chips
  (old #r11Mk hidden).
- Verified: both leagues, 1500 + 390 px, 0 JS errors, no page overflow.

## 2026-10-06 (m) — v4: markets, Kalshi, stat projections, unified picks + DFS, signal audit, logos
- Josh's seven asks: autonomous loop; logos with every player + correct color semantics; pull lines from DK / FanDuel / Kalshi /
  Polymarket; Ψ is undefined and untracked — smash spots must name the market; projected stats not fantasy points + DFS mock
  entries tracked; all picks (ML/ATS/totals/props/TD/DFS) on Games & Picks; Intel tabs must grade their contribution; redo Bets.
- Sources: Kalshi public API works from a kalshi.com tab in Chrome (DK sportsbook + DFS APIs are blocked for Chrome; FanDuel
  blocked; Polymarket reachable but has no NFL game markets under the nfl tag). Sandbox + device VM have no network at all.
  First pull: 1,190 open markets → data/raw/kalshi_2026-10-06.txt (aggregated, 32 KB) → build_kalshi.py (322 subjects).
- New scripts: build_kalshi.py, build_signals.py (7,479 starter-games: env +24% lift, dvp +9%, scheme +6.5%, psi +5.2%,
  role +4.5%; Ψ 1–5 band ratio 1.048 vs 28–32 0.946), build_dfs.py (5 slates, uncapped until a DK salary CSV exists),
  build_picks.py (picks_all.csv: ML vs Kalshi ≥.06, ATS/TOTAL carried, PROP carried, TD vs Kalshi ≥.08/.12, DFS). refresh.py
  runs them (skip signals with --no-signals). Dashboard payload: kalshi, picksAll, dfs, signals.
- Template v4 module: MKT market map, marketRows() (own avg × allowed/league), bets11 rewritten (Markets tables, TD table,
  game lines with Kalshi vs DK vs model), board() rewritten (stat projections), picksTab() for Games & Picks sub-tabs,
  signalsPanel() on Intel (default tab), homeBoard() = market board (Ψ smash/avoid tiles + PPR table removed), logoize()
  observer adds team logos to every .plink/.pp, .up/.dn colors fixed (▲ = green = good for the offense).

## 2026-10-07 — (n) v5: Layer 0 landing + five-tab Layer 1
- Josh's spec: Layer 0 = every sport as bubbles + the week's games; Layer 1.<sport> mirrors the NFL dashboard; NFL tabs
  collapsed to Home (Overview/Insights/Fantasy), Matchups (Big Board/Matchups/TD Board), Players (Lab/Explorer/Depth
  Charts as a football field with defenses, colleges, rivalries), Intel (+ Locker Room, Defenses, Schedule), Picks
  (Games & Picks + Bets subtabs). "Make the data pop; use visualizations, physics, images; data first, picks later."
- Data: data/raw/slate_all_2026-10-07.txt (ESPN scoreboard, 13 leagues × 8 days = 291 games, via Chrome on example.com —
  date ranges 400, teams endpoint CORS-blocked, downloads unreliable → <pre> + get_page_text transport). nflverse
  depth_charts/roster parquet already in the repo → build_units.py (2,325 unit rows, 2,576 bios; 19 teams run a 3-4
  base, 13 a 4-3). build_narratives.py (600 rows: 209 rematches, 151 revenge, 104 rivalry, 96 division, 31 streaks,
  9 coach-vs-former-team). build_landing.py → index.html + nba/ncaab/wnba/mlb/nhl/soccer.html shells.
- Template: SECTIONS → five majors (default view = Home Overview; league switch gained an "all sports" link);
  chamber() rewritten as the Matchups grid (cards: lines, implied totals, Kalshi ML, tilt, narrative chips, both
  offenses' core starters with per-stat rank heat cells + best stat; expand → old tables); dchart() gained the field
  mode (SVG 1000×420, vertical broadcast layout, chips with ESPN headshots + initials fallback, college, OUT/Q);
  board() gained MATCH (mean opponent rank across markets), rank cells in every market, default sort by MATCH, and the
  force-simulated matchup map; home Overview: slate tile ribbon full width above the market board; Insights: storylines
  panel; TD cards: Kalshi price. build_dashboard payload: units/unitCols/narr. Pages workflow copies dashboard/*.html.
- Tested: Playwright tour of every view (NFL + NCAA, 1500 and 390) — no page errors; the new views verified by screenshot.
- (n2) Josh's follow-ups: Layer 0 rebuilt twice (real league marks from ESPN's CDN dark set + the NCAA mark; no drawn icons,
  no animation; calendar strip, today strip, hero + marquee, day/team/text filters, sortable lines board, team filter);
  Big Board matchup map made static (collisions relaxed synchronously); Matchups = one card per row, two games per screen,
  with the allowed amount inside every rank cell; universal table sorting (sortableAll: every <th> of every table sorts,
  custom th[data-k] sorters kept; ranks() handlers limited to data-k headers — the old handler crashed on the ω column);
  Defenses Rankings + Matrix got a "compare with" second data set (ranks side by side with the shift, two matrices);
  depth-chart field is now an X-and-O diagram in team colors with college logos (no turf, no headshots).
- (n3) "keep building": Player Explorer's empty state is now a starter index per position (season line, L5, usage, MATCH,
  all sortable); Matchups cards carry each starter's own season averages under his name; depth-chart field falls back
  to the list on pages without unit charts (NCAA); Layer 0 shows the NFL model's softest matchups per market (top three
  matchup multipliers among the 40 highest-volume starters, from prop_projections.csv) when NFL is selected.
- (n4) Other sports. Discovery: the sandbox can reach github.com, and sportsdataverse publishes ESPN/NHL box scores as
  GitHub release parquets (sportsdataverse/sportsdataverse-data: espn_nba_player_boxscores, nhl_player_boxscores,
  espn_wnba_player_boxscores, schedules, team boxes) — so NBA / NHL / WNBA need no browser at all. New: scripts/sports/
  {config,fetch_sdv,build}.py + scripts/sport_template.html → dashboard/{nba,nhl,wnba}.html (Home / Matchups / Players /
  Intel / Picks). NBA 56,746 player-games (2024-25 + 2025-26; 2026-27 appears when hoopR publishes it), NHL 113,391
  (three seasons incl. the first week of 2026-27), WNBA 12,757. Slots G/F/C (ESPN box positions) and C/W/D/G. Game
  model = margin ratings + home edge; picks frozen vs DK lines from the slate (no preseason). data/sports/*/processed/
  logs.csv is git-ignored (derived, ~10 MB). Layer 0: NBA/NHL/WNBA now LIVE with their own softest-matchup teasers.
  Chrome downloads were tested again (trusted click on a visible link) and still do not land — the slate stays on the
  <pre> + get_page_text path.

### (n5) other sports deployed · daily task live — 2026-10-07
- Deployed 234e77f..adc7858 via GitHub web upload (scripts/sports new dir, landing/template/refresh, nba/nhl/wnba raw parquets + processed, dashboard index/nba/nhl/wnba + shells, notes, README, .gitignore). Remote == local verified; device synced by bundle (notes/_sync_sports.bundle, removed).
- nhl.html was 10.6 MB (> GitHub's 10 MB upload cap) → sports/build.py now drops the unused `gid` column and serialises whole-number floats as ints: nhl 9.1 MB, nba 7.9 MB, wnba 1.8 MB. dvp.csv rows now sorted (src, team, slot) so reruns are byte-stable.
- Scheduled task created: "RAINMAN daily sports" trig_018ZQT7m5DRWpvEk818mZfcb — CRON_TZ=America/Chicago 50 6 * * 0,1,3,5,6 (skips Tue weekly refresh / Thu midweek, which already run sports via refresh.py), device-bound, push on. Prompt = autoloop §1b.
- Live check (Chrome): index / nba / nhl / wnba all 200 with the 06:35–06:36 builds; NHL page J.logs 57,478 rows, 127 games next 14 days.
- Still shells: MLB, NCAAB, soccer — no browser-free player box-score source found yet (sportsdataverse MBB release 404, baseballr = NCAA only). Next candidate: ESPN scoreboard/boxscore recipe through Chrome, same transport as the slate.

### (n6) local loop replaces the Claude scheduled tasks — 2026-10-07
- Josh: scheduled tasks burn too much usage → run locally or gate on in-season/games, ignore preseason. Built scripts/local/
  (common, pull_box [PFR + nflverse fallback], pull_espn [depth via core depthcharts+roster injuries, DK props, slate, NCAA lines],
  pull_kalshi, gate, loop, rainman.cmd, install.ps1). Validated: nflverse fallback == PFR on 3 week-4 games (61 lines, 0 diffs);
  ESPN depthcharts JSON (slot=row, rank=order) reproduces the 10-06 Chrome pull for NE exactly.
- Preseason dropped from the slate (pull), landing and sport pages; slate-only games now 'reg'. Season gate per league.
- positions_2026.csv now also filled from the nflverse roster (+375 ids): 16 fullback/TE rows across 2024-26 moved WR→RB/TE.
- All five Claude tasks disabled (weekly refresh, midweek lines, Saturday slate, pregame freeze, daily sports). Not deleted.

### (n7) dashboard revision: insight-first pass — 2026-10-07
- Backup first: tag `backup-v5-2026-10-07`, branch `backup/v5-2026-10-07`, zip at C:\Users\jwlar\rainman\backups\rainman_backup_v5_2026-10-07.zip (backups/ is git-ignored).
- Home/Overview: + standings (8 divisions, W-L, div record, PF/PA, ±, streak, L5 dots, conference seed today), + season leaders (9 categories, top 5, bars, per-game),
  + every defense ranked by position (all 32 × 9 slots, two side-by-side tables, this week's opponent, μ; replaces the 12-team "DvP field"), movers widened to 14.
  Removed: birthdays panel (out of scope per project rules) and the storylines duplicate (Locker Room has them). Intel brief tables got headers and plain titles.
- Insights: removed the duplicated storylines / momentum / "uncertainty principle" / "geodesics" panels; one schedule-strength table for every slot (rest of season), volatility table kept; "how to read" shortened.
- Big Board: bubble cloud → position lanes (x = MATCH rank, dot = volume, median tick, three softest / toughest named per lane).
- Picks: 9 internal tabs + 3 sub-tabs → ONE page: record by type KPIs, this week's card (all types, type chips, sorted by edge), game model board, graded history (collapsed), DFS lineups (collapsed). Section now has two items: Picks · Markets (markets / anytime TD / game lines are chips inside Markets).
- Intel: default view "This week" (what each defense's style gives up per position), then How each defense plays · How each offense plays · Defense style vs position · Player usage · Model audit (last). Column labels and notes rewritten in plain language; the signal-audit page now opens with a sentence explaining what it measures.
- Observatory: worldline / interference / energy spectrum / phase portrait / FUSION / EVENT HORIZON → "allowed by week", "head to head", "where every defense sits", "season vs last 3 games", "allows the most / least".
- Sport pages (NBA/NHL/WNBA): standings & ratings table sorted by record (+ win%, ±/g), season leaders per market (min 3 games).
- Every table on every view is sortable (59/59 NFL, 47/47 NCAA checked); fixed a latent crash in Matchups cards (lbl(null) on padded stat columns).
- Not deployed by web upload (usage): committed locally + synced to the PC; `git push` from the PC publishes.

### (n8) full-dash cull + defense game logs — 2026-10-07
- Removed: Home market board and intel brief (Intel tab keeps that content), Locker Room Birthdays tab + birthday threads, popup birthday line, TD Board "phase space / collider" plots. Matrix table now full width (drill opens beside it).
- Fantasy default (no roster picked) = league board: every roster's suggested lineup total, range, byes/outs, top projection, softest / toughest matchup; waiver radar below. Click a roster → its lineup.
- Defense game logs: `defLogBlock(def, slot)` from J.logs (who held the slot vs that defense each week + his line + PPR, per-game averages, prior seasons collapsed).
  Player popup: the opponent's log vs his slot under "what X allows"; in the DvP-rankings tab every defense row expands to its log. Defenses tab: click any defense → its logs for the selected slot (or every slot in ALL).
- Every table still sortable (55/55 NFL, 43/43 NCAA, popup tables included).

### (n9) five-point redo — 2026-10-07
1. Locker Room: Birthdays back (Josh's call), grouped by distance from the player's NEXT game with a ± window (1/3/7/14/30 d), list format; new tabs Alumni · Homecoming · Alma mater · Home state · Revenge (one table each from build_connections rows).
2. Big Board: usage gate (QB ≥50% snaps · RB ≥30% snaps or 8 touches/g · WR/TE ≥45% snaps and ≥10% tgt share or 3.5 tgt/g; toggle to "everyone"); four quadrants (QB/RB/WR/TE) with the 8 best matchups ranked by DK points × softness, showing snap/tgt share, MATCH, softest market and DK pts; full board collapsed below.
3. Matchups rebuilt: one game per screen (min-height 100vh), header with logos/records/implied totals/lines/Kalshi/env/storyline chips, a per-slot Ψ strip (which offense has the softer field at each of 9 slots), both sides with QB·RB1·RB2·WR1·WR2·WR3·WR4+·TE1·TE2: player + usage (snap %, tgt %, opp/g), his 2026 line, the defense's rank+allowed per stat, projection with floor–ceiling band; defense style lines; storylines collapsed; jump chips per game.
4. Depth charts: field drawing removed; clean lists — offense QB/RB/WR1-3/TE depth 1-4 (college logo, Q/OUT, trend, snap %, opp/g), defense LB/CB/S starters + next up from nflverse units (no OL/DL); game picker, two teams side by side.
5. Insights: all tables replaced by visuals — per-role bar charts (five softest / five hardest fields), defense extremes dumbbells per slot on a league-average scale, rest-of-season schedule heat strip with slot chips, volatility bars + waveforms.
6. Fantasy → DFS (DraftKings Classic): frozen optimal lineup per slate (value per $1k when salaries exist), stacks + bring-backs, top plays per roster spot (usage-filtered), DK scoring note; league-roster filter hidden.

### (n10) public-facing clean-up — 2026-10-07
- Every view opens with a plain-English intro box (what it shows + how-to-read chips); long panel subtitles and footnotes fold into ⓘ hovers. Filter bar untouched.
- Removed redundant views: Matchup Lab (Big Board + Explorer cover it), Matrix (Home's all-32 grid + Defenses cover it). TD Board tiles dropped (table has them). Insights schedule heat strip dropped (Schedule tab is that).
- Player Explorer landing = compact directory (PPR/g, L5, snap%, tgt%, form sparkline) — no more stat dump.
- College home: the slate is 8 marquee tiles (closest spreads, highest totals, power conferences) + one sortable table of all 58 games instead of 58 tiles; standings by conference (FBS, no NFL divisions); Matchups jump becomes a select when >16 games.
- Views: NFL 18 → Home (Overview·Insights·DFS) · Matchups (Big Board·Matchups·TD Board) · Players (Explorer·Depth) · Intel (Intel·Locker Room·Defenses·Observatory·Schedule) · Picks (Picks·Markets).

(n11) 2026-10-07 — whole-site pass. Landing page rewritten (scripts/build_landing.py): sport selector tiles with model records, today's slate across every league, per-league trio (marquee game · softest matchups · model record), one sortable week table with day chips, standings from slate records, how-to-read cards. MLB / NCAAB / Soccer shells now share the same page (schedule + lines + records) until a box-score source lands. NBA / NHL / WNBA pages (scripts/sport_template.html) get the same treatment as NFL: plain-English intro box per view, long explanatory notes folded into ⓘ hovers, redundant subtitle removed. All pages checked headless: zero JS errors, intros on every view.
(n12) 2026-10-07 — Layer 0 rebuilt from scratch after the n11 version was rejected as the same text-card layout. New landing: sport bubbles sized by games this week (real league marks, static) with the model's graded-result strip; today's games on one clock (a lane per league, each game a logo chip at its kickoff, "now" marker); the week as a wall of game cards (logos, records, ranks, kickoff, TV, tilt bar = favorite's share of implied points or win odds, moneyline-aware) with day / competition chips and a sortable-list toggle; the edges as bars (opponent's adjusted DvP rank in the exact stat, #1 = allows the most; biggest favorites; highest totals; model record with W/L strip); records as win% bars. Long weeks default to today. Shells (MLB / NCAAB / Soccer) share the page.
(n13) 2026-10-08 — two new directions off Layer 0. ARB ENGINE (scripts/build_arb.py → dashboard/arb.html): every game line quantified across DraftKings (ESPN core odds, priced ML/spread/total), Kalshi (public trade API: GAME / SPREAD / TOTAL ladders; YES at the ask, NO at 1−bid, 7%·P·(1−P) taker fee added to cost) and Polymarket (Gamma API, series nfl-2026 = 12185, nhl 10346, nba 10345, cfb 12756; moneyline/spreads/totals/team totals, props kept only when two-sided). Normalized rows → data/processed/lines_all.csv; two-way markets paired (spreads on the away handicap) → fair probability = average of each source's de-vigged two-sided price (exchange mid-points) → arb_board.csv, arb_opps.csv (stake split per $100, fee-adjusted), ev_opps.csv (EV%, ¼ Kelly). Page: coverage matrix, arbitrage cards, board of game cards with every source's price chip (gold = best, EV on every chip, single-source lines behind a toggle), sortable +EV table; any chip saves a play (localStorage rainman.plays). First pull 2026-10-08 via Chrome (NFL only): 454 lines, 153 markets, 3 arbs ≤0.8%, 8 +EV ≥1%. scripts/local/pull_markets.py reproduces the pull for every league on the PC loop (loop.py: markets → build_arb → build_social). Polymarket's own fetch() from gamma pages hangs — navigate to the JSON URL instead; kalshi.com same-origin fetch also hung today — navigate per series. SOCIAL (scripts/build_social.py → dashboard/social.html, local-only prototype as chosen): profile handle, manual play log for any slate game, drafts saved from the Arb Engine (set a stake → ledger), ledger with W/L/P grading (NFL game lines auto-grade from game_lines.csv finals), record / units / ROI / weekly bars, weekly-units leaderboard (you + imported friends), feed with tail, share link (plays carried in the URL hash), JSON backup/restore. DK/FD have no account API — stated on the page; Kalshi/Polymarket imports marked coming. Landing header links to both.
