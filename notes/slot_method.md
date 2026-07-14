# Historical slot-assignment method (2024, 2025 seasons)

ESPN depth-chart history is not available, so historical slots are derived from usage:
within each team-week, among players who appeared in that game, rank by CUMULATIVE season
usage through the current week (no future information):
- QB by pass attempts -> QB1, QB2
- RB (incl. FB) by rush_att+targets -> RB1, RB2, RB3 (RB3+ folds into the RB2+ bucket for DvP)
- WR by targets -> WR1, WR2, WR3, rest WR4+
- TE by targets -> TE1, TE2 (TE3+ folds into TE2 bucket)
If a starter misses a game he doesn't appear; the next man up inherits the higher slot that
week — mirroring depth-chart-as-of-that-week behavior. Positions come from PFR's season
fantasy page; ~1% of rows (56 in 2025) had no listed position and were inferred from usage.
Validated vs legacy workbook: see validation_2025.md. Rows are never retroactively re-slotted.
