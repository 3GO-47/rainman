# Data integrity audit — 2026-10-19

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
PASS  2024 all rows have valid pos (QB RB WR TE, or X = lineman / specialist / fake-punt defender, out of DvP)
PASS  2024 every skill row has a slot, every X row is slot X — 36 X rows
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
PASS  2025 all rows have valid pos (QB RB WR TE, or X = lineman / specialist / fake-punt defender, out of DvP)
PASS  2025 every skill row has a slot, every X row is slot X — 23 X rows
PASS  2025 dvp_weekly rows = 544 — 544
PASS  2025 independent recompute of all 18496 weekly cells — 0 mismatches
PASS  2025 season averages match weekly means — 0 cells off
PASS  2025 ranks: descending RANK.AVG, rank1 = most allowed — 0 off
PASS  2026 raw: 92 unique boxscores (weeks 1-6)
PASS  2026 raw: zero ERR lines
PASS  2026 raw: all P lines have 18 fields
PASS  2026 raw: no duplicate (game,player) rows — 0 dups
PASS  2026 logs rows == raw P lines — 1806 vs 1806
PASS  2026 coverage: every team has all its scheduled games in scraped weeks — min 5 max 6
PASS  2026 coverage: 184 team-games — 184
PASS  2026 reciprocity: every (wk,A,B) has (wk,B,A)
PASS  2026 logs match schedule exactly — 0 mismatches
PASS  2026 fantasy_pts_std formula exact
PASS  2026 ppr = std + rec
PASS  2026 all rows have valid pos (QB RB WR TE, or X = lineman / specialist / fake-punt defender, out of DvP)
PASS  2026 every skill row has a slot, every X row is slot X — 8 X rows
PASS  2026 dvp_weekly rows = 184 — 184
PASS  2026 independent recompute of all 6256 weekly cells — 0 mismatches
PASS  2026 season averages match weekly means — 0 cells off
PASS  2026 ranks: descending RANK.AVG, rank1 = most allowed — 0 off
PASS  combined = (2024+2025+2026x2)/4 (every cell) — 0 off
PASS  composite * = mean of group stat ranks (QB, all 32) — 0 off
PASS  2024 D/ST rows match raw D lines — 56 vs 56
PASS  2024 D/ST totals match
PASS  2025 D/ST rows match raw D lines — 63 vs 63
PASS  2025 D/ST totals match
PASS  2026 D/ST rows match raw D lines — 13 vs 13
PASS  2026 D/ST totals match
PASS  dashboard payload == dvp_combined.csv (2176 cells) — 0 off
PASS  dashboard logs == game_logs rows (12508) — 12508
PASS  dashboard weekly == 1272 defense-weeks — 1272
PASS  dashboard weekly column order correct
PASS  dashboard sched26: 32 teams x 18 wks, 32 byes