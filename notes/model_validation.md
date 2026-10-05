# Model validation — betting layer

Everything here is walk-forward: each prediction uses only games before it. Rerun `scripts/build_prop_model.py` to refresh the props table (it replaces its own section).

## Does a defense's DvP predict what it allows next week? (2026-10-05)
Target: stats allowed to each slot in the next game, 2025 wk 3 → 2026 wk 3. Skill = 1 − MSE / MSE(league mean for that stat).

| predictor | skill |
|---|---|
| raw DvP (season-to-date allowed, the v1 ranking) | −0.4% to −4% (worse than league average) |
| offense only (opponent's recency-weighted production, half-life 6–8 wk) | +7.87% |
| offense + opponent-adjusted defense effect (half-life 12 wk, shrink K_DEF=20) | +8.4% |

Reading: raw "yards allowed" mostly reflects which offenses a defense happened to face. Judging each game against what that offense normally produces, fading older games (half-life 8–17 wk all within 0.1pp; 12 chosen), and shrinking hard toward zero leaves a real but small defense signal. That adjusted version (`dvp_adjusted.csv`) now drives the matchup ranks across the dashboard; the raw tables are still available in the source toggles.

<!-- props:start -->
## Player props — walk-forward backtest (2026-10-05)
Skill = 1 − MSE / MSE(slot-mean) for yardage/count markets; anytime TD = 1 − logloss / logloss(slot-mean rate).
Targets: every QB/RB/WR/TE game with ≥2 prior games, 2025 wk 3 → latest 2026 week; projections use only earlier data.
"form + matchup + game" adds the opponent-adjusted defense effect (β) and the market-implied team total (γ).

| market | games | player form only | form + matchup + game | tuned |
|---|---|---|---|---|
| pass_yds | 668 | +25.09% | +26.31% | H=16 K=1.5 β=1.5 γ=0.0 |
| pass_td | 668 | +9.11% | +10.11% | H=16 K=3 β=1.0 γ=0.5 |
| pass_att | 668 | +22.86% | +23.54% | H=16 K=1.5 β=1.0 γ=0.0 |
| completions | 668 | +23.24% | +24.54% | H=16 K=1.5 β=1.5 γ=0.0 |
| interceptions | 668 | -0.53% | -0.53% | H=4 K=6 β=0.0 γ=0.0 |
| rush_yds | 4243 | +11.34% | +12.24% | H=16 K=6 β=0.0 γ=0.5 |
| rush_att | 2087 | +16.22% | +16.22% | H=4 K=1.5 β=0.0 γ=0.0 |
| receptions | 4735 | +14.46% | +14.59% | H=8 K=3 β=0.5 γ=0.0 |
| rec_yds | 4735 | +9.74% | +10.35% | H=8 K=6 β=0.5 γ=0.5 |
| rush_rec_yds | 1419 | +13.31% | +14.04% | H=8 K=3 β=0.0 γ=0.5 |
| pass_rush_yds | 668 | +24.47% | +25.78% | H=16 K=1.5 β=1.5 γ=0.0 |
| anytime_td | 5403 | +1.98% | +2.46% | H=8 K=6 β=0.0 γ=1.0 c=0.9 |
<!-- props:end -->
