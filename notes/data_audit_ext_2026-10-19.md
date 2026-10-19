# Full data audit — 2026-10-19

Scope: every calculated data set on the NFL dashboard (rainman.html) and the NCAA dashboard (ncaa.html): game logs, slots,
DvP (per season, combined, adjusted), schedule and kickoffs, betting lines and implied totals, TD Picks (model, backtest,
ledger), the prop board / METAPROP, Weeklies signals, the player card, injuries and depth charts, page footer counts.

Result after fixes: **scripts/verify_data.py 64/64 PASS · scripts/audit_extended.py 89 PASS, 1 WARN (explained), 0 FAIL ·
browser-computed numbers match an independent Python recompute.**

## How it was checked
- `scripts/verify_data.py` (existing): raw PFR box lines -> game logs -> DvP tables -> page, every cell recomputed.
- `scripts/audit_extended.py` (new, rerunnable): a second source for every box-score number (nflverse official weekly
  player stats, all three seasons), schedule / kickoffs / lines vs nflverse and the live books, page payload vs processed
  tables, slot integrity, TD Picks features and ledger, prop board, injuries + QB1s vs nflverse, NCAA consistency.
- Browser check (Playwright): Weeklies signal hit rates, the player card's season / H2H / opponent-allowed rows and
  METAPROP's L10 / average, each recomputed independently in Python from the game logs.
- `scripts/validate_vs_legacy.py` + position-group totals vs the legacy NFLLLLL.xlsx Data tab (2025, all 32 defenses).

## What matched (highlights)
- Game logs vs nflverse official stats, 2024-2026 (12,280 player-games): pass / rush / receiving yards, attempts,
  completions, carries, targets, receptions, every TD and interception — 100% (two 2026 rows differ by one target
  between the two official sources).
- Rushing + receiving TDs per team-game vs nflverse: 1,248 of 1,248.
- Snap shares vs nflverse snap counts: 100% (±1 pt). Schedule 576/576 cells. PFR game list = nflverse 272/272.
- game_lines = nflverse every game; page DvP (2024, 2025, 2026, combined, adjusted) = the tables, every cell;
  page logs = csv, every stat; footer 624 games / 12,280 rows correct; page week correct.
- TD Picks: top-60 cards recomputed (games, TDs, last 3, touches, TD share, opponent), implied totals, backtest arithmetic,
  no pick written at or after kickoff. Prop board: opponents, probabilities, prices.
- Weeklies (every season): Implied 24+ 969/3,151 · TD every other game 701/1,780 · TD share + implied 24+ 204/391 ·
  18+ touches 275/572 — identical in Python and on the page. Player card and METAPROP (25 rows) identical.
- NCAA: page logs = csv (51,431), no duplicates, fantasy formula exact, page DvP = table (4,692 cells).
- Legacy workbook 2025: position-group totals match 96.5-100% of defense-weeks; slot-level cells 89.2% exact — the gaps
  are slot splits (usage-ranked vs hand-entered) and the workbook counting Taysom Hill / trick-play passes as QB stats.

## Errors found and fixed
1. **Non-offensive players in skill slots (67 player-games).** PFR's fantasy page lists skill players only; everyone else
   had a guessed position, so punters, kickers, linemen and fake-punt defenders landed in RB3 / WR4+ — sometimes WR3
   (Jake Matthews OT 2026 wk5, Alex Cappa G 2025 wk6, Wanya Morris OT TD 2024 wk2), and Braden Mann's −34-yard fake
   punt cut TB's 2025 wk4 RB rushing allowed. Fix (build_game_logs.py): positions now come from nflverse (the week's
   player stats, then rosters); linemen / K / P / LS -> pos X; a defender counts on offense only if he played offensive
   snaps that game (Travis Hunter, a DT at fullback stay). X rows stay in the logs (team TD totals whole) but out of every
   slot and DvP bucket. Everything downstream was rebuilt; TD Picks backtest now AUC 0.697, top-10 137/230, 50%+ tier
   138/223 (62%).
2. **Kickoff times never picked up schedule changes.** kickoffs_2026 came from PFR's preseason dump; CHI@GB wk5 was listed
   4:25 PM but kicked off at 1:00 PM (ESPN 17:00 UTC, nflverse 13:00). That put it in the wrong slate chip and would have
   locked TD Picks at the wrong time for any flexed game. Fix (build_kickoffs.py): nflverse's daily game list and ESPN's
   scoreboard now override PFR (latest wins); week 18 stays TBD until set.
3. **Lines for games still to play trailed the market.** nflverse's line updates about once a day; the books had moved
   DEN@ARI and KC@SEA totals 2.5 points, and DAL@PHI had no line at all (TD Picks assumed 22). Fix (new live_lines.py):
   games not yet kicked off use the median across every book the loop prices; finished games keep nflverse's closing line.
   Used by TD Picks and the Weeklies / Game View line table (marked 'books').
4. **verify_data.py treated a week in progress as missing data** (expected all week-6 games once one was logged). Now it
   expects only games that are final.

## Explained, not errors
- Fumbles lost: ~15 rows a season where PFR counts a fumble on a kick / punt return and nflverse's offensive columns
  don't (Shaheed, Mims, Velus Jones, other return men). The site keeps PFR's count (it matches fantasy scoring).
- Zach Davidson (BUF TE) 2024 wk13: one incomplete target in nflverse, absent from PFR's box; no catch, no yards.
- Marvin Harrison Jr.: traded to HOU — the prop board and depth chart say HOU, his past games say ARI (both right).
- Injuries: every player nflverse lists OUT for week 6 is also OUT on the ESPN report the site uses; QB1 for all 32 teams
  matches nflverse's depth charts.
