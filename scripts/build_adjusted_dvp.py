"""Opponent-adjusted, recency-weighted DvP — the matchup ranking used for betting.

Why (backtested, notes/model_validation.md): a defense's RAW allowed stats do not predict what it allows next week any
better than the league average — the raw number is mostly the offenses it happened to face. Once each game is judged
against what that offense normally produces, and older games fade, the defense signal is real (small, so it is shrunk).

For every defense D and stat column c (the 34 legacy DvP columns, slot-specific):
  residual_g = allowed_g - offense_expectation_g          offense_expectation = that offense's mean production in the
                                                           slot over all OTHER games, shrunk to the league mean (k_off)
  effect_D   = sum(w_g * residual_g) / (sum(w_g) + K_DEF) w_g = 0.5 ** (age_g / HALF_LIFE), age in weeks
  avg        = league_mean_c + effect_D                    "what D allows to a league-average offense in that slot"
Age runs across seasons with a GAP-week offseason, so last year's games fade but still count (turnover is handled by
the shrinkage and by trust in the dashboard). Ranks: 1 = allows the most above expectation (best matchup), like v1.
Writes data/processed/dvp_adjusted.csv (same column layout as dvp_combined.csv) + dvp_adjusted_meta.json.
"""
import os, json
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
HALF_LIFE, GAP, K_DEF, K_OFF = 12.0, 6, 20.0, 4.0   # tuned in notes/model_validation.md
STAT_COLS = ['QB PY','P TD','QB RY','RB1 RY','RB2+ RY','WR RY','RB1 Recep','RB1 RecY','RB2 Recep','RB2 RecY','WR1 Recep',
             'WR1 RecY','WR2 Recep','WR2 RecY','WR3 Recep','WR3 RecY','WR4+ Recep','WR4+ RecY','TE1 Recep','TE1 RecY',
             'TE2 Recep','TE2 RecY','QB TD','RB1 TD','RB2 TD','WR1 TD','WR2 TD','WR3 TD','WR4+ TD','TE1 TD','TE2 TD',
             'D/ST TD','QB P+R','RB R+R']
GROUP_STATS = {'QB':['QB PY','QB RY','QB P+R','P TD','QB TD'],'RB1':['RB1 RY','RB1 Recep','RB1 RecY','RB R+R','RB1 TD'],
 'RB2':['RB2+ RY','RB2 Recep','RB2 RecY','RB R+R','RB2 TD'],'WR1':['WR1 Recep','WR1 RecY','WR1 TD'],'WR2':['WR2 Recep','WR2 RecY','WR2 TD'],
 'WR3':['WR3 Recep','WR3 RecY','WR3 TD'],'WR4+':['WR4+ Recep','WR4+ RecY','WR4+ TD'],'TE1':['TE1 Recep','TE1 RecY','TE1 TD'],
 'TE2':['TE2 Recep','TE2 RecY','TE2 TD'],'D/ST':['D/ST TD']}

def tindex(df):
    s0 = df.season.min()
    return (df.season - s0) * (18 + GAP) + df.week

def main():
    W = pd.read_csv('data/processed/dvp_weekly.csv')
    W['t'] = tindex(W)
    now = W.t.max() + 1                                # predicting the next game
    out = {d: {} for d in sorted(W.defense.unique())}
    for c in STAT_COLS:
        x = W[c].astype(float).values
        lm = x.mean()
        # offense expectation for each row: that offense's mean in the slot over its OTHER games, shrunk (leave-one-out)
        g = W.groupby('opponent')[c]
        s, n = g.transform('sum').values, g.transform('count').values
        off_exp = (s - x + K_OFF * lm) / (n - 1 + K_OFF)
        resid = x - off_exp
        w = 0.5 ** ((now - W.t.values) / HALF_LIFE)
        df = pd.DataFrame({'d': W.defense.values, 'wr': w * resid, 'w': w})
        agg = df.groupby('d').sum()
        eff = agg.wr / (agg.w + K_DEF)
        for d in out: out[d][c] = lm + float(eff.get(d, 0.0))
    T = pd.DataFrame(out).T
    T.index.name = 'defense'
    R = T.rank(ascending=False, method='average')
    res = pd.DataFrame(index=T.index)
    res['seasons_blended'] = f'opp-adjusted · half-life {HALF_LIFE:g} wk'
    for c in STAT_COLS: res[c + ' avg'] = T[c].round(3)
    for c in STAT_COLS: res[c + ' rank'] = R[c]
    for slot, cols in GROUP_STATS.items(): res[slot + ' *'] = R[cols].mean(axis=1).round(2)
    res.reset_index().to_csv('data/processed/dvp_adjusted.csv', index=False)
    json.dump({'half_life_weeks': HALF_LIFE, 'offseason_gap_weeks': GAP, 'k_def': K_DEF, 'k_off': K_OFF,
               'through': f"{int(W.season.max())} wk {int(W[W.season == W.season.max()].week.max())}"},
              open('data/processed/dvp_adjusted_meta.json', 'w'))
    print(f'dvp_adjusted.csv: 32 defenses x {len(STAT_COLS)} stats · half-life {HALF_LIFE} wk · gap {GAP} · K_def {K_DEF}')

if __name__ == '__main__':
    main()
