# RAINMAN — 2026/27 Defense-vs-Position Intelligence

Answers, every week: how many stats does each NFL defense allow to each positional slot
(QB, RB1, RB2, WR1-3, WR4+, TE1, TE2, D/ST), and what does that mean for each player's
matchup. Replaces the legacy NFLLLLL.xlsx workbook. Rank convention everywhere:
**rank 1 = most allowed = best matchup** (legacy RANK.AVG).

## The product
`dashboard/rainman.html` (NFL) and `dashboard/ncaa.html` (NCAA FBS) — single self-contained files, same template.
**v2 shell (2026-10-06):** a two-row top bar with the original tabs — row 1 is Home · Big Board · Weekly Matchups ·
Players · Defenses · TD Board · Schedule · Intel · Games & Picks · Locker Room · Bets (F1–F11), row 2 is that tab's
views (Players: Matchup Lab · Player Explorer · Depth Charts; Defenses: Rankings · Matrix · Observatory; Bets: Player
props · Anytime TD · Game lines; Home: Overview · Insights · Fantasy) with a one-line description of the open view.
Content gets the full width. Skin: pure black background, graphite panels with hairline borders, Inter for chrome and
JetBrains Mono for data, one amber accent (active tab / league), white-filled selected chips, rank badges as tinted
pills (green = allows the most = best matchup, red = stingiest). Long how-to-read paragraphs fold into a `?` chip.
The landing view is the **Matchup Lab** (Players › Matchup Lab): every starter this week with his own per-game
averages (this season, and cumulative across every scraped season — 2024–26) beside what the opponent allows to his
slot, the opponent's DvP rank per stat, Ψ, Ψ+ and projection; every column sorts, every filter (position, depth, injury,
college, slate, game, team, roster) narrows it. ▲/▼ in an avg cell = the opponent allows more / less than the player
averages. F1–F11 jump between tabs, ctrl-K finds any player or team, and
the week / slate / position / game / team filter bar underneath applies to every view. Type: Inter for chrome,
JetBrains Mono for data; one amber accent; rank colors unchanged (green = allows the most = best matchup).
**v3 visuals (2026-10-06):** the tabs that used to be loose stacks of tables are now dense, one-screen views built from a
shared set of primitives (KPI tiles, field-tilt bars, heat cells, thread matrices). Home: KPI strip (smash / avoid /
softest & stingiest D playing / movers / highest total / biggest spread / props posted) → slate board (spread, total,
field tilt, environment rank, storylines, props per game; click filters everything) beside best & worst per role and
movers → top projections beside the DvP field heat for the defenses on the slate → intel brief. TD Board: KPI strip,
TD fields by role, an anytime-TD card board (rush + rec TD rate × end-zone softness), plots folded, table below.
Schedule: lens (next 4 / rest of season / playoffs 15-17), N4 / ROS / PO / Σ columns, sort, legible opponent cells,
sticky team column. Games & Picks: KPI strip + one board table over collapsible game cards, weekly W-L bars on the
ledger (the duplicate props tab moved to Bets). Intel: "this week's scheme edges" — every offense × role vs the scheme
family it faces. Locker Room: thread matrix (game × kind) over collapsible cards sorted by thread count. Bets: KPI
strip (cleared ≥70% / ≤30% L10, biggest line move) and market chips with counts and hit bars.

**v4 model & markets (2026-10-06):** the dashboard now tracks positions, not just matchups.
*Markets (Bets tab)* — one dense table per market (pass yds / TD / att, rush yds / att, receptions, rec yds, anytime TD, game
lines): his per-game averages, what the opponent allows to his slot (rank), volume × matchup (the ranking), the model's
projection with its 10–90% band, the posted line (DraftKings or the Kalshi ladder's implied line), model P(over), his
L10 over-rate at that line, the Kalshi exchange price and the model–exchange gap; click a row for game-by-game bars.
*Projections (Big Board)* — projected statistics per starter and market (median + band) and the DK-points translation;
PPR is no longer the headline. *Games & Picks* — one unified ledger (`data/processed/picks_all.csv`) with sub-tabs for
Moneyline (model vs Kalshi mid, ≥6 pts), Spreads and Totals (game model vs DK, ≥3 pts), Props (prop model EV at −110),
Anytime TD (model vs Kalshi, ≥8 pts) and DFS mock entries (one DK Classic lineup per slate — main / early / afternoon /
primetime / full — frozen and graded on real DK points; capped when `data/raw/dk_salaries_wk{N}.csv` is present, uncapped
otherwise); every row carries the market reference it was judged against and is graded in place. *Intel › Signals* — a
walk-forward audit (`scripts/build_signals.py`) of what each input is worth: top-third vs bottom-third lift in actual ÷
baseline for DvP rank, Ψ, scheme family, environment and role trend, per market, plus a Ψ-band table and the prop model's
skill by market. Ψ is kept but no longer labels anything a "smash spot"; the Home market board ranks by volume × stat
matchup. *Kalshi* — `scripts/build_kalshi.py` parses the exchange pull (notes/scrape_recipe.md) into implied lines and
probabilities. Every player reference carries his team logo; ▲/green always means more production for the offense.

**Effective depth charts (2026-10-06):** ESPN leaves injured starters in their slot for weeks (Baker Mayfield "QB1 · O"),
which mis-slots the real starter. `scripts/build_depth_chart.py` now derives the *effective* chart: OUT/IR players drop to
the bottom of their row and the next man holds the slot (Jalon Daniels QB1); within RB/TE/WR rows a player who has taken
≥25% more opportunities than the man above him over the team's last two games (and a real workload) moves up, and the three
WR starters are ordered by last-two-games targets. Every row carries `note` (why he moved), `trend` (▲ rising / ▼ fading
workload vs his season rate), `l2`/`se` (opps per game, last 2 · season), `gp`, `espn_depth` and `log_name` (game-log
spelling, so averages join). The dashboard shows ▲▼● glyphs next to names (hover for the reason) and the Depth Charts view
shows workload and the ESPN listing where it differs.

The legacy F1–F11 tab buttons still exist hidden (`#legacyNav`) as the routing model — every old cross-link and
re-render path works unchanged; the top bar's `go(view)` clicks them and then selects the sub-panel. The URL hash
carries `v=<view>` plus the filters, so a shared link opens the exact screen.

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

## Bet Board (F2) — betting layer
Pipeline (all in `refresh.py`, all reproducible from `data/game_logs/`):
1. `build_adjusted_dvp.py` → `dvp_adjusted.csv`: opponent-adjusted, recency-weighted DvP (half-life 12 wk, shrink K=20).
   This is now the default matchup ranking everywhere (raw/combined tables remain in the source toggles). Why: raw
   allowed totals did not predict next week's allowed stats in walk-forward testing; the adjusted version does (small).
2. `build_prop_model.py` → `prop_model.json`, `prop_projections.csv`: per market, projection = player form (recency,
   shrunk to slot) × matchup (adjusted DvP, β) × market-implied team total (γ); walk-forward tuned; outcome
   distributions from historical residuals. Results in `notes/model_validation.md`.
3. `build_bets.py` → `bet_lines.csv` (lines + model + EV), `bet_td.csv` (anytime-TD fair prices), `bet_ledger.csv`
   (every line frozen when first seen, graded from box scores), `bet_corr.json` (same-game correlations for SGPs).
   Probability = market + w·(model − market), w up to 35% and scaled down for players with < 4 games of history in the role, until the ledger shows a bigger edge.
4. Prices: DraftKings lines via ESPN arrive without prices (EV assumes −110). For **FanDuel prices**, put a free
   The Odds API key in `.env` (`ODDS_API_KEY=...`, git-ignored); `refresh.py` then runs `fetch_odds_api.py`.

UI tabs: **Props** (sortable by EV, matchup rank, projection; range bar = 10th–90th pct with line marker; confidence
dots = weighted games of history) · **Anytime TD** (fair price; type a book price → EV) · **Parlay / SGP** (legs priced
jointly with a Gaussian copula over measured correlations; enter the book's price → EV + capped fractional Kelly stake;
log the ticket) · **Ledger** (model's frozen picks + your logged tickets, auto-graded, ROI, CSV export; your tickets
live in this browser's storage) · **Model** (walk-forward skill and calibration per market).
The v2 site opens on the Bet Board; Home is one click away.

## Reverting the UI (kept on purpose)
- Classic v1 UI is always live at **/v1/** (rebuilt every refresh from `scripts/dashboard_template.html`).
- Frozen snapshots served at **/archive/**: `rainman_v1_2026-10-05.html` (last v1-as-main build, commit f13c159) and
  `rainman_v2.0_2026-10-05.html` (first v2 build, commit e57433e).
- One-step revert of the main site to v1: in `.github/workflows/pages.yml` change the root copy to
  `cp dashboard/rainman.html _site/index.html` (or `git revert` the commits after f13c159). Git history keeps every build.

## Live deploy
`.github/workflows/pages.yml` publishes `dashboard/rainman.html` (root), `dashboard/ncaa.html`
(/ncaa.html), `dashboard/v2/` and `dashboard/archive/` to GitHub Pages on every push to main.
Live at https://3go-47.github.io/rainman/ — the original terminal UI; the NFL | NCAA switch in
the header carries the current tab / week / filters across (hash is preserved).

## NCAA FBS layer (`ncaa/`, `scripts/ncaa/`) — same terminal, 138 defenses
`dashboard/ncaa.html` is the same template fed college data. Everything lives under a league
root `ncaa/data/{raw,game_logs,processed}` with the NFL schemas, so `compute_dvp` logic, the
dashboard builder and every tab are shared; `scripts/build_dashboard.py --league ncaa` injects
`J.league` (team map / logos / colors, 20-week calendar, kickoff slates, conference filter,
tabs to hide). Hidden for college: Intel (nflverse scheme data), Games & Picks (no college pick
model), Locker Room (NFL-only connections); Bets shows game lines only until a college prop
feed exists.

Sources (all public, no key; `scripts/ncaa/fetch_cfb.py`):
- player box scores: ESPN via the sportsdataverse-data `espn_cfb_player_box` releases, 2024-26
  (one row per player × stat category; two upstream passing schemas handled)
- schedules / scores / FBS-FCS flags / kickoffs / TBD flags: cfbfastR-data schedules (CFBD)
- team ids, abbreviations, colors, conference, classification: cfbfastR-data team_info
- positions + headshots: cfbfastR-data rosters · lines 2024-25: cfbfastR-data `cfb_line_odds`
  (DraftKings > ESPN Bet > Bovada) · lines 2026: ESPN scoreboard / summary odds pulled in Chrome
  (`ncaa/data/raw/espn_lines_2026_*.txt`, recipe in notes/scrape_recipe.md)

Conventions that differ from the NFL layer (all documented in the script headers):
- slots are usage rank within team-week, cumulative through that week (no public college depth
  charts) — the same method the NFL layer uses for historical seasons; the depth-chart snapshot
  is the last-3-games usage ranking (most recent game ×2); injury flags are unknown (1)
- week 0 games (the earlier of a team's two "week 1" games) are week 0; postseason = 17 (bowls +
  CFP first round), 18 (quarterfinals), 19 (semis), 20 (title) so no team has two games in a week
- every offense that faced an FBS defense counts toward that defense's allowed stats (FCS
  opponents included, per-game legacy convention); FCS defenses get no DvP row; blend 2024+2025+2026×2
- no targets or snap counts exist in college box scores (targets = 0; usage columns blank)
- team colors: ESPN primaries that are too dark on black fall back to a real secondary color or
  are lightened (build_dashboard.readable)

Refresh: `python3 scripts/ncaa/refresh.py` (fetch → logs → schedule → DvP → lines → depth /
matchups → dashboard; `--no-fetch` to rebuild offline). The mirror updates Sat 16:00 / 20:15
and Sun + Mon 06:30 UTC in season; current-week odds need the Chrome pull.

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

## Layers (2026-10-07)
**Layer 0 — `dashboard/index.html`** (the site root): every sport as a selectable bubble (a small physics field — bubbles
sized by games this week, spring + collision), with the next seven days of games per sport underneath: logos, records, AP
ranks, Central-time kickoff, broadcast, DraftKings spread / moneyline and total, venue and headline (London game, playoff
round, NBA China game …). NFL and CFB open the full model; NBA, NCAAB, WNBA, MLB, NHL and Soccer (EPL, MLS, UCL, La Liga,
Bundesliga, Serie A, Ligue 1) open a schedule shell on the same framework with the pipeline status board. Everything comes
from `data/raw/slate_all_<date>.txt` (ESPN scoreboard, see notes/scrape_recipe.md) via `scripts/build_landing.py`.

**Layer 1 — `rainman.html` (NFL) and `ncaa.html` (CFB)**: five major tabs (F1–F5), each with minor tabs:
- **Home** — Overview (KPIs · slate ribbon of game tiles with implied team totals, DK and Kalshi lines, tilt, env rank and
  the game's narrative chip · market board · DvP field · movers) · Insights (storylines of the week, best/worst per role,
  field extremes, momentum, volatility, schedule strength) · Fantasy.
- **Matchups** — Big Board (matchup rankings: the opponent's rank in every market the player lives on, MATCH = mean rank,
  projection bands, and the force-simulated matchup map — x = matchup, y = yards percentile within position, size = volume)
  · Matchups (every game of the week on one screen: both offenses vs the opposing defense as heat strips with the softest
  stat per starter, lines, tilt, narratives; any card opens to the full slot-by-slot tables) · TD Board (now with the Kalshi
  anytime price on every card).
- **Players** — Matchup Lab · Player Explorer · Depth Charts (the field: both defenses in their base front and both
  offenses in 3WR-1TE, built from nflverse/ESPN units with college, size, experience, usage and injury on every chip;
  gold ring = alumni link across the line, red = college rivalry; the game's rivalry / streak / coach-revenge / rematch
  chips on top; list view kept as a toggle).
- **Intel** — Intel (scheme, personnel, turnover, coaching, signal audit) · Locker Room · Defenses · Matrix · Observatory · Schedule.
- **Picks** — Games & Picks (ML, ATS, totals, props, TD, DFS, ledger) · Markets · Anytime TD · Game lines.

## Changelog
- 2026-10-07 — **v5: Layer 0 + five-tab Layer 1.** Multi-sport landing (`index.html`, 13 leagues, 291 games) with
  sport shells; navigation collapsed from eleven tabs to Home / Matchups / Players / Intel / Picks; the Matchups grid
  (every game at once); the depth-chart field (full units from nflverse: OL, 4-3 / 3-4 fronts, special teams, bios);
  game narratives (`build_narratives.py`: division, curated rivalries, last meeting, streaks, playoff rematches, coaches
  vs former teams, player revenge); Big Board matchup rankings + force-simulated matchup map; home slate ribbon.
  New scripts: build_units.py, build_narratives.py, build_landing.py (all in refresh.py). Pages workflow serves every
  dashboard/*.html with index.html as the root.
- 2026-10-06 — **v3 "storm terminal" redesign + betting depth.** Broadcast header (condensed type, section tabs with a
  sliding indicator), a live ticker of the week's plays, scoreboard tiles, and money-green for edges. Player headshots
  (ESPN, mapped from nflverse ids) on plays, props, smash board, depth-chart starters and the player card. **Top plays**
  cards on the Bet Board; every prop shows his **last 10 games against the line** (hit squares + count) and L5 average;
  the player card lists his lines for the week with hit history. Explanatory notes are visible again (clamped to two
  lines, click to expand) instead of hidden behind chips. Completions now graded (cmp added to the log payload).
  Previous UI frozen at `/archive/rainman_v2.1_2026-10-06.html`; `/archive/` now has an index page.
- 2026-10-06 — **Consolidated navigation: 11 tabs → 5 sections.** Bets · Games · Matchups · Defenses · Players, each with
  sub-views; duplicate panels removed (old Home copies, legacy prop leans, second sides/totals table); depth charts open by
  default; game cards fold under the lines table; status notes collapse; payload −50 KB. `build_props.py` retired from the
  refresh (its ledger file is kept as history).
- 2026-10-06 — **Week 4 graded, week 5 loaded, prop model fixed.** First ledger week: plays (EV ≥ 3%) 27-20, record rising
  with edge (details in `notes/model_validation.md`). Fixes: QB1/QB2 priors split (QB projection error −24–28%), role-weighted
  history, mean-bias scale, next-man-up projections for OUT starters, model weight scaled by the player's history. Bet Board
  gains a **Sides & totals** tab (spreads/totals, implied team points, model edges, honest backtest) and a ledger broken
  down by edge bucket and market with week filter.
- 2026-10-05 — **Betting-first: Bet Board (F2).** Matchup rankings now opponent-adjusted + recency-weighted (half-life
  12 wk) because raw DvP failed a walk-forward test; per-market prop model (form × matchup × implied team total) with
  honest skill numbers; priced props, anytime-TD fair prices, correlated SGP pricer with Kelly staking, frozen + graded
  ledger, personal bet tracker; FanDuel prices via The Odds API key in `.env`. v2 lands on the Bet Board; Home gains a
  "best prop edge" tile. Tabs renumbered F1–F11.
- 2026-10-05 — **v2 refinement pass.** Home reorganized into a purposeful order (KPIs → storylines & birthdays → top
  projections → smash board → waiver radar / lineup → intel brief → slate map → deep-dive analytics, collapsed); the
  redundant system panel removed (its facts live in the sidebar). Every panel title collapses its card (remembered per
  browser). Long explanatory paragraphs sit behind "How to read this" chips. Column headers align with their data;
  tables size to content and scroll inside their card with edge shadows instead of truncating; game cards stack their
  two sides when narrow; Chart.js themed to the UI; Locker Room cards lead with marquee rivalries + connections, the
  rest behind "+ more". Mobile: swipeable KPI strip, short tab labels, no duplicate eyebrow. Revert path documented.
- 2026-10-05 — **New UI (v2) is now the main site**; the classic terminal UI stays live at `/v1/`. v2 is a new shell
  and design system layered over the same engine (`scripts/build_dashboard_v2.py` = v1 build + `scripts/v2/skin.css`
  + `scripts/v2/skin.js`), so every number is identical: sidebar navigation with a spring-physics active indicator
  (bottom tab bar on phones), glass filter strip, Inter typography, rounded card system, per-page hero headers, Home
  KPI tiles (games + live kickoff countdown, top projection, smash spot, waiver #1, storylines), view transitions,
  staggered card entrances, count-up numbers, cursor-tilt game cards; honors reduced-motion.
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
