
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
