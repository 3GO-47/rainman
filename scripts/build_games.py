"""Game-level model + picks ledger.

Inputs : data/processed/game_lines.csv (nflverse: scores, closing spread/total/moneylines — fetch_games.py)
         data/raw/nflverse/pbp_slim_*.parquet (per-game EPA for team ratings)
Outputs: data/processed/team_ratings.csv   — per team, per season-week: offensive / defensive EPA ratings (walk-forward)
         data/processed/game_model.csv     — every 2024-26 game: model spread/total, market line, edge, result, cover
         data/processed/picks_ledger.csv   — FROZEN picks: a week's picks are written once, the first time the week is
                                             upcoming, and never rewritten; later runs only grade them.
         data/processed/picks_retro.csv    — retrospective model picks for weeks that were already played when the
                                             ledger started (clearly labelled: NOT frozen, for calibration only)

Model (deliberately simple and fully transparent):
  rating_off(team) = shrunk mean EPA/play on offense, last 10 games incl. prior season (prior-season games ×0.6)
  rating_def(team) = same for EPA/play allowed (lower = better)
  power rating (srs)  = opponent-adjusted, home-adjusted margin, last 17 games (prior season ×0.6), shrunk k=6, 6 iterations
  model margin        = HFA(1.6) + srs_home − srs_away + 0.5·rest-day difference (cap ±3)
  epa_spread          = the same from EPA ratings (kept as context; corr with result 0.17 vs 0.41 for srs vs 0.50 market)
  model total = league avg total ± pace/EPA adjustment (both offenses' EPA + both defenses' EPA allowed)
  pick ATS   = side where |model − market| ≥ 1.5 pts; pick total = over/under where |model − market| ≥ 2.0
  moneyline  = model win prob (normal, σ=13.5) vs implied prob; pick if edge ≥ 5 pts of probability
"""
import os, glob, math, datetime, sys
import pandas as pd, numpy as np
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
HFA, SIGMA, ATS_EDGE, TOT_EDGE, ML_EDGE = 1.6, 13.5, 3.0, 3.0, 0.99  # ML picks disabled: model win-probs lose to the moneyline market in backtest (41-101)

G = pd.read_csv('data/processed/game_lines.csv')
G = G.sort_values(['season', 'week', 'gameday']).reset_index(drop=True)

# ---- per-game team EPA from pbp_slim (offense EPA/play, defense EPA/play allowed, plays) ----
rows = []
for f in sorted(glob.glob('data/raw/nflverse/pbp_slim_*.parquet')):
    p = pd.read_parquet(f, columns=['game_id', 'season', 'week', 'posteam', 'defteam', 'play_type', 'epa', 'qb_dropback', 'rush_attempt'])
    p = p[p.play_type.isin(['pass', 'run']) & p.posteam.notna() & p.epa.notna()]
    p['posteam'] = p.posteam.replace({'LA': 'LAR'}); p['defteam'] = p.defteam.replace({'LA': 'LAR'})
    o = p.groupby(['game_id', 'season', 'week', 'posteam']).agg(off_epa=('epa', 'mean'), plays=('epa', 'size')).reset_index().rename(columns={'posteam': 'team'})
    d = p.groupby(['game_id', 'season', 'week', 'defteam']).agg(def_epa=('epa', 'mean')).reset_index().rename(columns={'defteam': 'team'})
    rows.append(o.merge(d, on=['game_id', 'season', 'week', 'team']))
TG = pd.concat(rows).sort_values(['team', 'season', 'week']).reset_index(drop=True)
LG_OFF = TG.off_epa.mean()

def rating(team, season, week, n=10, k=4):
    """walk-forward: games strictly before (season, week); prior-season games weighted 0.6; shrunk to league mean"""
    h = TG[(TG.team == team) & ((TG.season < season) | ((TG.season == season) & (TG.week < week)))].tail(n)
    if h.empty: return LG_OFF, LG_OFF, 0
    w = np.where(h.season < season, 0.6, 1.0)
    off = (np.sum(w * h.off_epa) + k * LG_OFF) / (w.sum() + k)
    dfn = (np.sum(w * h.def_epa) + k * LG_OFF) / (w.sum() + k)
    return off, dfn, int(len(h))

# ---- margin-based power rating (SRS-style, opponent-adjusted, walk-forward) — this drives the spread model ----
# per team-game: home-adjusted margin; rating = shrunk mean of (margin + opponent rating), last 17 games, prior season ×0.6
mg = []
for g in G[G.result.notna()].itertuples():
    mg.append((g.season, g.week, g.home_team, g.result - HFA, g.away_team)); mg.append((g.season, g.week, g.away_team, -g.result + HFA, g.home_team))
MG = pd.DataFrame(mg, columns=['season', 'week', 'team', 'adj', 'opp'])
def srs(season, week, n=17, k=6, iters=6):
    h = MG[(MG.season < season) | ((MG.season == season) & (MG.week < week))]
    hh = h.groupby('team').tail(n); r = {t: 0.0 for t in hh.team.unique()}
    for _ in range(iters):
        new = {}
        for t, grp in hh.groupby('team'):
            w = np.where(grp.season < season, 0.6, 1.0); m = grp.adj.values + np.array([r.get(o, 0.0) for o in grp.opp])
            new[t] = float(np.sum(w * m) / (w.sum() + k))
        r = new
    return r

def ratings_table():
    out = []
    for (s, w), grp in G.groupby(['season', 'week']):
        pr = srs(s, w)
        for t in pd.unique(pd.concat([grp.away_team, grp.home_team])):
            o, d, n = rating(t, s, w)
            out.append(dict(season=s, week=w, team=t, srs=round(pr.get(t, 0.0), 2), off_epa=round(o, 4), def_epa=round(d, 4), games_in_window=n, net=round(o - d, 4)))
    return pd.DataFrame(out)

RT = ratings_table()
RT.to_csv('data/processed/team_ratings.csv', index=False)
R = {(r.season, r.week, r.team): r for r in RT.itertuples()}
PLAYS = 63.0  # offensive plays per team per game (league avg)

def raw_margin(g):
    h, a = R[(g.season, g.week, g.home_team)], R[(g.season, g.week, g.away_team)]
    return ((h.off_epa - a.def_epa) - (a.off_epa - h.def_epa)) * PLAYS
def raw_total(g):
    h, a = R[(g.season, g.week, g.home_team)], R[(g.season, g.week, g.away_team)]
    return ((h.off_epa + a.def_epa) + (a.off_epa + h.def_epa) - 4 * LG_OFF) * PLAYS

G['raw_margin'] = G.apply(raw_margin, axis=1)
G['raw_total'] = G.apply(raw_total, axis=1)
rest = (G.home_rest.fillna(7) - G.away_rest.fillna(7)).clip(-6, 6) * 0.5
# fit K (points per raw EPA-margin unit) on completed 2024-25 games, then a total scale + intercept
fit = G[(G.season <= 2025) & G.result.notna()]
K = float(np.sum(fit.raw_margin * (fit.result - HFA)) / np.sum(fit.raw_margin ** 2))
KT = float(np.sum((fit.raw_total - fit.raw_total.mean()) * (fit.total - fit.total.mean())) / np.sum((fit.raw_total - fit.raw_total.mean()) ** 2))
T0 = float(fit.total.mean() - KT * fit.raw_total.mean())
G['epa_spread'] = (HFA + K * G.raw_margin + rest).round(1)            # EPA view (context only — weak predictor, see README)
G['model_spread'] = (HFA + G.apply(lambda g: R[(g.season, g.week, g.home_team)].srs - R[(g.season, g.week, g.away_team)].srs, axis=1) + rest).round(1)  # home − away
G['model_total'] = (T0 + KT * G.raw_total).round(1)
G['win_prob_home'] = G.model_spread.apply(lambda m: 0.5 * (1 + math.erf(m / (SIGMA * math.sqrt(2)))))
G['edge_spread'] = (G.model_spread - G.spread_line).round(1)          # + = model likes HOME more than market
G['edge_total'] = (G.model_total - G.total_line).round(1)
def implied(ml):
    if pd.isna(ml): return np.nan
    return (-ml / (-ml + 100)) if ml < 0 else 100 / (ml + 100)
G['imp_home'] = G.home_moneyline.apply(implied); G['imp_away'] = G.away_moneyline.apply(implied)
vig = G.imp_home + G.imp_away
G['imp_home_fair'] = G.imp_home / vig
G['edge_ml_home'] = (G.win_prob_home - G.imp_home_fair).round(3)

def picks(g):
    ats = tot = ml = ''
    if pd.notna(g.spread_line):
        if g.edge_spread >= ATS_EDGE: ats = f'{g.home_team} {-g.spread_line:+g}'
        elif g.edge_spread <= -ATS_EDGE: ats = f'{g.away_team} {g.spread_line:+g}'
    if pd.notna(g.total_line):
        if g.edge_total >= TOT_EDGE: tot = f'OVER {g.total_line:g}'
        elif g.edge_total <= -TOT_EDGE: tot = f'UNDER {g.total_line:g}'
    if pd.notna(g.edge_ml_home):
        if g.edge_ml_home >= ML_EDGE: ml = f'{g.home_team} ML {int(g.home_moneyline):+d}'
        elif g.edge_ml_home <= -ML_EDGE: ml = f'{g.away_team} ML {int(g.away_moneyline):+d}'
    return pd.Series(dict(pick_ats=ats, pick_total=tot, pick_ml=ml))
G = pd.concat([G, G.apply(picks, axis=1)], axis=1)

def grade(g):
    if pd.isna(g.result): return pd.Series(dict(cover_home=np.nan, over=np.nan, res_ats='', res_total='', res_ml=''))
    ch = np.sign(g.result - g.spread_line) if pd.notna(g.spread_line) else np.nan   # +1 home covers, 0 push, -1 away
    ov = np.sign(g.total - g.total_line) if pd.notna(g.total_line) else np.nan
    def wl(pick, side_sign):
        if not pick: return ''
        if side_sign == 0: return 'PUSH'
        return 'W' if side_sign > 0 else 'L'
    r_ats = wl(g.pick_ats, ch * (1 if g.pick_ats.startswith(g.home_team) else -1)) if g.pick_ats else ''
    r_tot = wl(g.pick_total, ov * (1 if g.pick_total.startswith('OVER') else -1)) if g.pick_total else ''
    r_ml = ''
    if g.pick_ml:
        home_won = g.result > 0
        r_ml = 'PUSH' if g.result == 0 else ('W' if home_won == g.pick_ml.startswith(g.home_team) else 'L')
    return pd.Series(dict(cover_home=ch, over=ov, res_ats=r_ats, res_total=r_tot, res_ml=r_ml))
G = pd.concat([G, G.apply(grade, axis=1)], axis=1)

cols = ['game_id', 'season', 'week', 'gameday', 'away_team', 'home_team', 'away_score', 'home_score', 'result', 'total',
        'spread_line', 'total_line', 'away_moneyline', 'home_moneyline', 'model_spread', 'epa_spread', 'model_total', 'win_prob_home', 'imp_home_fair',
        'edge_spread', 'edge_total', 'edge_ml_home', 'pick_ats', 'pick_total', 'pick_ml', 'res_ats', 'res_total', 'res_ml',
        'away_rest', 'home_rest', 'roof', 'away_qb_name', 'home_qb_name', 'pfr']
GM = G[cols].copy()
GM.to_csv('data/processed/game_model.csv', index=False)

# ---- frozen ledger ----
LP = 'data/processed/picks_ledger.csv'
led = pd.read_csv(LP) if os.path.exists(LP) else pd.DataFrame(columns=['frozen_on'] + cols)
cur = GM[(GM.season == 2026) & GM.result.isna() & GM.spread_line.notna()]
upcoming_week = int(cur.week.min()) if len(cur) else None
new = cur[(cur.week == upcoming_week) & ~cur.game_id.isin(led.game_id)] if upcoming_week else cur.iloc[0:0]
if len(new):
    new = new.copy(); new.insert(0, 'frozen_on', str(datetime.date.today()))
    led = pd.concat([led, new], ignore_index=True)
# grade previously frozen picks with today's results (results/grades only — picks and lines stay as frozen)
res = GM.set_index('game_id')
for i, r in led.iterrows():
    if r.game_id in res.index and pd.notna(res.loc[r.game_id, 'result']):
        g = res.loc[r.game_id]
        for c in ['away_score', 'home_score', 'result', 'total']: led.at[i, c] = g[c]
        # re-grade against the FROZEN line/pick
        ch = np.sign(g.result - r.spread_line); ov = np.sign(g.total - r.total_line)
        led.at[i, 'res_ats'] = ('PUSH' if ch == 0 else ('W' if (ch > 0) == str(r.pick_ats).startswith(r.home_team) else 'L')) if isinstance(r.pick_ats, str) and r.pick_ats else ''
        led.at[i, 'res_total'] = ('PUSH' if ov == 0 else ('W' if (ov > 0) == str(r.pick_total).startswith('OVER') else 'L')) if isinstance(r.pick_total, str) and r.pick_total else ''
        led.at[i, 'res_ml'] = ('PUSH' if g.result == 0 else ('W' if (g.result > 0) == str(r.pick_ml).startswith(r.home_team) else 'L')) if isinstance(r.pick_ml, str) and r.pick_ml else ''
led.to_csv(LP, index=False)
# retrospective (unfrozen) picks for 2026 weeks already played before the ledger existed
retro = GM[(GM.season == 2026) & GM.result.notna() & ~GM.game_id.isin(led.game_id)]
retro.to_csv('data/processed/picks_retro.csv', index=False)

def record(df, col):
    v = df[col][df[col].isin(['W', 'L', 'PUSH'])]
    return f"{(v=='W').sum()}-{(v=='L').sum()}-{(v=='PUSH').sum()}"
bt = GM[(GM.season <= 2025) & GM.result.notna()]
print(f"team_ratings: {len(RT)} rows · K={K:.2f} pts per EPA-margin unit · total scale {KT:.2f}+{T0:.1f}")
print(f"game_model: {len(GM)} games · 2024-25 backtest ATS {record(bt,'res_ats')} · totals {record(bt,'res_total')} · ML {record(bt,'res_ml')} "
      f"(picks only where edge ≥ {ATS_EDGE}/{TOT_EDGE} pts / {int(ML_EDGE*100)}% prob)")
mae_model = (bt.model_spread - bt.result).abs().mean(); mae_mkt = (bt.spread_line - bt.result).abs().mean()
print(f"  spread MAE vs result: model {mae_model:.2f} · market {mae_mkt:.2f}")
print(f"picks_ledger: {len(led)} frozen picks (upcoming week {upcoming_week}, {len(new)} new) · retro 2026: ATS {record(retro,'res_ats')} · totals {record(retro,'res_total')} · ML {record(retro,'res_ml')}")
