# 2025 DvP validation vs legacy NFLLLLL.xlsx Data tab

Comparison grain: defense x week x 34 stat columns. Legacy BYE rows skipped.
**Overall: 2522/2890 cells exact (87.3%)**

## ARI: 531/578 cells exact (91.9%)
- wk2 WR1 RecY: legacy=100 ours=-2 (diff -102)
- wk10 WR2 RecY: legacy=74 ours=3 (diff -71)
- wk10 WR3 RecY: legacy=3 ours=74 (diff +71)
- wk2 WR2 RecY: legacy=48 ours=100 (diff +52)
- wk2 WR3 RecY: legacy=-2 ours=48 (diff +50)
- wk7 WR1 RecY: legacy=37 ours=72 (diff +35)
- wk7 WR2 RecY: legacy=72 ours=37 (diff -35)
- wk17 WR4+ RecY: legacy=5 ours=26 (diff +21)
- wk17 TE2 RecY: legacy=60 ours=39 (diff -21)
- wk18 WR2 RecY: legacy=19 ours=0 (diff -19)
- wk18 WR3 RecY: legacy=6 ours=19 (diff +13)
- wk5 WR3 RecY: legacy=17 ours=6 (diff -11)
- ... and 35 more

## ATL: 500/578 cells exact (86.5%)
- wk13 WR1 RecY: legacy=19 ours=102 (diff +83)
- wk13 WR2 RecY: legacy=102 ours=19 (diff -83)
- wk17 WR3 RecY: legacy=67 ours=0 (diff -67)
- wk17 WR4+ RecY: legacy=0 ours=67 (diff +67)
- wk12 RB1 RecY: legacy=43 ours=4 (diff -39)
- wk12 RB2 RecY: legacy=4 ours=43 (diff +39)
- wk16 WR1 RecY: legacy=14 ours=52 (diff +38)
- wk16 WR2 RecY: legacy=52 ours=14 (diff -38)
- wk14 RB2+ RY: legacy=78 ours=46 (diff -32)
- wk14 WR RY: legacy=-1 ours=31 (diff +32)
- wk14 WR2 RecY: legacy=35 ours=67 (diff +32)
- wk14 WR3 RecY: legacy=67 ours=35 (diff -32)
- ... and 66 more

## BAL: 503/578 cells exact (87.0%)
- wk12 WR1 RecY: legacy=65 ours=9 (diff -56)
- wk12 WR3 RecY: legacy=9 ours=65 (diff +56)
- wk16 WR2 RecY: legacy=16 ours=69 (diff +53)
- wk16 WR3 RecY: legacy=69 ours=16 (diff -53)
- wk17 WR1 RecY: legacy=113 ours=62 (diff -51)
- wk17 WR2 RecY: legacy=62 ours=113 (diff +51)
- wk1 WR1 RecY: legacy=112 ours=64 (diff -48)
- wk1 WR2 RecY: legacy=64 ours=112 (diff +48)
- wk4 WR1 RecY: legacy=83 ours=38 (diff -45)
- wk4 WR2 RecY: legacy=38 ours=83 (diff +45)
- wk8 WR1 RecY: legacy=73 ours=114 (diff +41)
- wk8 WR2 RecY: legacy=114 ours=73 (diff -41)
- ... and 63 more

## KC: 485/578 cells exact (83.9%)
- wk11 WR3 RecY: legacy=82 ours=0 (diff -82)
- wk11 WR4+ RecY: legacy=0 ours=82 (diff +82)
- wk8 RB1 RecY: legacy=64 ours=0 (diff -64)
- wk8 RB2 RecY: legacy=0 ours=64 (diff +64)
- wk3 RB1 RecY: legacy=61 ours=7 (diff -54)
- wk3 RB2 RecY: legacy=7 ours=61 (diff +54)
- wk16 RB1 RecY: legacy=53 ours=0 (diff -53)
- wk16 RB2 RecY: legacy=0 ours=53 (diff +53)
- wk5 WR3 RecY: legacy=15 ours=64 (diff +49)
- wk5 WR2 RecY: legacy=64 ours=16 (diff -48)
- wk1 RB1 RY: legacy=48 ours=5 (diff -43)
- wk1 RB2+ RY: legacy=5 ours=48 (diff +43)
- ... and 81 more

## SF: 503/578 cells exact (87.0%)
- wk11 WR2 RecY: legacy=66 ours=5 (diff -61)
- wk11 WR3 RecY: legacy=15 ours=66 (diff +51)
- wk4 WR2 RecY: legacy=42 ours=0 (diff -42)
- wk4 WR3 RecY: legacy=0 ours=42 (diff +42)
- wk13 TE1 RecY: legacy=4 ours=43 (diff +39)
- wk13 TE2 RecY: legacy=43 ours=4 (diff -39)
- wk8 RB1 RecY: legacy=49 ours=13 (diff -36)
- wk8 RB2 RecY: legacy=21 ours=57 (diff +36)
- wk8 WR1 RecY: legacy=34 ours=63 (diff +29)
- wk8 WR3 RecY: legacy=63 ours=34 (diff -29)
- wk18 WR2 RecY: legacy=29 ours=2 (diff -27)
- wk18 WR3 RecY: legacy=2 ours=29 (diff +27)
- ... and 63 more


## Known causes of differences
- Slot attribution: legacy used hand-maintained weekly depth charts; RAINMAN ranks players
  by cumulative usage through the current week (see notes/slot_method.md). Totals across
  a position group (e.g. QB PY, RB R+R, WR RY) should match almost exactly; per-slot splits
  (RB1 vs RB2+, WR1 vs WR2...) can differ where the two methods disagree on slot.
- Legacy hand-entry errors are possible; PFR box scores are the source of truth here.