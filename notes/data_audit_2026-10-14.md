# Data integrity audit — 2026-10-14

**64/64 checks passed**

PASS  2024 raw: 272 unique boxscores (weeks 1-18)
PASS  2024 raw: zero ERR lines
PASS  2024 raw: all P lines have 18 fields
PASS  2024 raw: no duplicate (game,player) rows — 0 dups
PASS  2024 logs rows == raw P lines — 5329 vs 5329
PASS  2024 coverage: every team has all its scheduled games in scraped weeks — min 17 max 17
PASS  2024 coverage: 544 team-games — 544
PASS  2024 reciprocity: every (wk,A,B) has (wk,B,A)
PASS  2024 logs match schedule exactly — 0 mismatches
PASS  2024 fantasy_pts_std formula exact
PASS  2024 ppr = std + rec
PASS  2024 all rows have valid pos
PASS  2024 all rows have a slot
PASS  2024 dvp_weekly rows = 544 — 544
PASS  2024 independent recompute of all 18496 weekly cells — 0 mismatches
PASS  2024 season averages match weekly means — 0 cells off
PASS  2024 ranks: descending RANK.AVG, rank1 = most allowed — 0 off
PASS  2025 raw: 272 unique boxscores (weeks 1-18)
PASS  2025 raw: zero ERR lines
PASS  2025 raw: all P lines have 18 fields
PASS  2025 raw: no duplicate (game,player) rows — 0 dups
PASS  2025 logs rows == raw P lines — 5373 vs 5373
PASS  2025 coverage: every team has all its scheduled games in scraped weeks — min 17 max 17
PASS  2025 coverage: 544 team-games — 544
PASS  2025 reciprocity: every (wk,A,B) has (wk,B,A)
PASS  2025 logs match schedule exactly — 0 mismatches
PASS  2025 fantasy_pts_std formula exact
PASS  2025 ppr = std + rec
PASS  2025 all rows have valid pos
PASS  2025 all rows have a slot
PASS  2025 dvp_weekly rows = 544 — 544
PASS  2025 independent recompute of all 18496 weekly cells — 0 mismatches
PASS  2025 season averages match weekly means — 0 cells off
PASS  2025 ranks: descending RANK.AVG, rank1 = most allowed — 0 off
PASS  2026 raw: 79 unique boxscores (weeks 1-5)
PASS  2026 raw: zero ERR lines
PASS  2026 raw: all P lines have 18 fields
PASS  2026 raw: no duplicate (game,player) rows — 0 dups
PASS  2026 logs rows == raw P lines — 1559 vs 1559
PASS  2026 coverage: every team has all its scheduled games in scraped weeks — min 4 max 5
PASS  2026 coverage: 158 team-games — 158
PASS  2026 reciprocity: every (wk,A,B) has (wk,B,A)
PASS  2026 logs match schedule exactly — 0 mismatches
PASS  2026 fantasy_pts_std formula exact
PASS  2026 ppr = std + rec
PASS  2026 all rows have valid pos
PASS  2026 all rows have a slot
PASS  2026 dvp_weekly rows = 158 — 158
PASS  2026 independent recompute of all 5372 weekly cells — 0 mismatches
PASS  2026 season averages match weekly means — 0 cells off
PASS  2026 ranks: descending RANK.AVG, rank1 = most allowed — 0 off
PASS  combined = (2024+2025+2026x2)/4 (every cell) — 0 off
PASS  composite * = mean of group stat ranks (QB, all 32) — 0 off
PASS  2024 D/ST rows match raw D lines — 56 vs 56
PASS  2024 D/ST totals match
PASS  2025 D/ST rows match raw D lines — 63 vs 63
PASS  2025 D/ST totals match
PASS  2026 D/ST rows match raw D lines — 12 vs 12
PASS  2026 D/ST totals match
PASS  dashboard payload == dvp_combined.csv (2176 cells) — 0 off
PASS  dashboard logs == game_logs rows (12261) — 12261
PASS  dashboard weekly == 1246 defense-weeks — 1246
PASS  dashboard weekly column order correct
PASS  dashboard sched26: 32 teams x 18 wks, 32 byes