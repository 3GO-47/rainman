
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
