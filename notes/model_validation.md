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

## Week 4 ledger + model fixes (2026-10-06)
First graded week of the bet ledger (126 DK lines, MNF pending): every line on the model's side 54-64; **plays (EV ≥ 3%) 27-20 (57.4%)**;
by edge: EV ≥ 10% 5-2, 6–10% 11-6, 3–6% 11-12, < 3% 27-44. The record rises with the edge, which is the pattern a real edge
should show — but it is one week. The model leaned Under on 91 of 118 lines and Overs hit 55%; the QB markets were worst
(pass yds 3-9, pass att 1-4). Causes found and fixed (wk 4 rows stay frozen as they were):
- **QB prior mixed starters with backups.** Slot priors grouped every QB together, so a starter with thin history was
  shrunk toward a mean that included backups' garbage-time lines. Priors now split QB1 / QB2. Walk-forward MSE:
  pass yds −24%, pass att −28%, completions −26%, pass+rush yds −26%, pass TD −8%.
- **Role weighting.** Games a player logged in a different role now count 25–50% (tuned per market, `role-w`); small gains for RB/WR markets.
- **Mean-bias scale.** Each market's projections are scaled so the walk-forward mean projection equals the mean outcome (scale 0.96–1.00).
- **Next man up.** The weekly ESPN snapshot keeps an injured starter in slot 1; projections now skip OUT players and promote the
  next active player (e.g. a backup QB starting is projected as a QB1).
- **Evidence-scaled weight.** The model's weight vs the market (max 35%) now scales with the player's history in the role
  (full weight at ≥ 4 weighted games), so thin-history players no longer produce large paper edges.
Result for the wk 5 lines: 34 Over / 36 Under (wk 4: 27 Over / 91 Under), 9 plays.

<!-- props:start -->
## Player props — walk-forward backtest (2026-10-06)
Skill = 1 − MSE / MSE(slot-mean) for yardage/count markets; anytime TD = 1 − logloss / logloss(slot-mean rate).
Targets: every QB/RB/WR/TE game with ≥2 prior games, 2025 wk 3 → latest 2026 week; projections use only earlier data.
"form + matchup + game" adds the opponent-adjusted defense effect (β) and the market-implied team total (γ).

| market | games | player form only | form + matchup + game | tuned |
|---|---|---|---|---|
| pass_yds | 698 | +10.83% | +14.92% | H=4 K=3 role-w=0.5 β=1.0 γ=0.5 |
| pass_td | 698 | +2.87% | +6.84% | H=4 K=6 role-w=1 β=0.5 γ=1.0 |
| pass_att | 698 | +10.18% | +11.05% | H=4 K=1.5 role-w=0.25 β=1.0 γ=0.0 |
| completions | 698 | +11.11% | +13.39% | H=8 K=1.5 role-w=0.25 β=1.5 γ=0.0 |
| interceptions | 698 | -0.49% | -0.50% | H=4 K=6 role-w=0.5 β=0.0 γ=0.0 |
| rush_yds | 4462 | +12.59% | +13.23% | H=8 K=3 role-w=0.25 β=0.0 γ=0.5 |
| rush_att | 2192 | +19.22% | +19.21% | H=4 K=1.5 role-w=0.25 β=0.0 γ=0.0 |
| receptions | 4981 | +14.45% | +14.77% | H=8 K=3 role-w=0.5 β=0.5 γ=0.0 |
| rec_yds | 4981 | +9.89% | +10.84% | H=16 K=6 role-w=0.5 β=0.5 γ=0.5 |
| rush_rec_yds | 1494 | +14.38% | +15.07% | H=8 K=3 role-w=0.25 β=0.0 γ=0.5 |
| pass_rush_yds | 698 | +10.39% | +14.75% | H=4 K=3 role-w=0.5 β=1.0 γ=0.5 |
| anytime_td | 5679 | +2.03% | +2.50% | H=16 K=6 role-w=0.5 β=0.0 γ=1.0 c=0.9 |
<!-- props:end -->
