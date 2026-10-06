"""Player-prop model: projection, full outcome distribution and over/under + anytime-TD probabilities, walk-forward
backtested on every player-game we have (2025 wk 3 → latest 2026 week). Everything is fit on data dated before the game.

projection  mu = base × matchup
  base     = player's recency-weighted mean of the stat (half-life H_P weeks, season gap GAP weeks), shrunk toward the
             league mean for his current slot with K_P pseudo-games
  matchup  = 1 + BETA[market] × effect / league_mean      effect = opponent-adjusted, recency-weighted defense effect for
             his slot/stat (build_adjusted_dvp.py logic, recomputed as-of each game)
distribution: empirical ratio y/mu from the backtest, per market and projection tercile → P(over L) = P(ratio > L/mu)
anytime TD:  lambda = TD-rate base × matchup;  P = 1 − exp(−C_TD × lambda)  (C_TD calibrated)

Outputs: data/processed/prop_model.json  (params, distributions, backtest skill + calibration)
         data/processed/prop_projections.csv (every current depth-chart player × market for the upcoming week)
         notes/model_validation.md section "player props"
"""
import os, json, glob, math
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
GAP, H_DEF, K_DEF, K_OFF = 6, 12.0, 20.0, 4.0
H_P, K_P = 8.0, 3.0
MARKETS = {  # market: (log columns summed, positions, dvp column template by slot group)
 'pass_yds': (['pass_yds'], ['QB'], {'QB': 'QB PY'}),
 'pass_td': (['pass_td'], ['QB'], {'QB': 'P TD'}),
 'pass_att': (['pass_att'], ['QB'], {'QB': 'QB PY'}),
 'completions': (['cmp'], ['QB'], {'QB': 'QB PY'}),
 'interceptions': (['int'], ['QB'], {}),
 'rush_yds': (['rush_yds'], ['QB', 'RB', 'WR'], {'QB': 'QB RY', 'RB1': 'RB1 RY', 'RB2': 'RB2+ RY', 'WR': 'WR RY'}),
 'rush_att': (['rush_att'], ['QB', 'RB'], {'QB': 'QB RY', 'RB1': 'RB1 RY', 'RB2': 'RB2+ RY'}),
 'receptions': (['rec'], ['RB', 'WR', 'TE'], {'RB1': 'RB1 Recep', 'RB2': 'RB2 Recep', 'WR1': 'WR1 Recep', 'WR2': 'WR2 Recep', 'WR3': 'WR3 Recep', 'WR4+': 'WR4+ Recep', 'TE1': 'TE1 Recep', 'TE2': 'TE2 Recep'}),
 'rec_yds': (['rec_yds'], ['RB', 'WR', 'TE'], {'RB1': 'RB1 RecY', 'RB2': 'RB2 RecY', 'WR1': 'WR1 RecY', 'WR2': 'WR2 RecY', 'WR3': 'WR3 RecY', 'WR4+': 'WR4+ RecY', 'TE1': 'TE1 RecY', 'TE2': 'TE2 RecY'}),
 'rush_rec_yds': (['rush_yds', 'rec_yds'], ['RB'], {'RB1': 'RB R+R', 'RB2': 'RB R+R'}),
 'pass_rush_yds': (['pass_yds', 'rush_yds'], ['QB'], {'QB': 'QB P+R'}),
 'anytime_td': (['rush_td', 'rec_td'], ['QB', 'RB', 'WR', 'TE'], {'QB': 'QB TD', 'RB1': 'RB1 TD', 'RB2': 'RB2 TD', 'WR1': 'WR1 TD', 'WR2': 'WR2 TD', 'WR3': 'WR3 TD', 'WR4+': 'WR4+ TD', 'TE1': 'TE1 TD', 'TE2': 'TE2 TD'}),
}
def grp(slot):
    s = str(slot)
    if s.startswith('QB'): return 'QB'
    if s.startswith('RB'): return 'RB1' if s == 'RB1' else 'RB2'
    if s.startswith('WR'): return s if s in ('WR1', 'WR2', 'WR3') else 'WR4+'
    if s.startswith('TE'): return 'TE1' if s == 'TE1' else 'TE2'
    return ''
def gprior(slot):
    """prior group: like grp but starters and backup QBs are separate (a QB1's prior must not include backups' garbage time)"""
    s = str(slot); return ('QB1' if s == 'QB1' else 'QB2') if s.startswith('QB') else grp(s)
def role(slot):
    """role identity for history weighting: exact slot, WR4+ collapsed"""
    s = str(slot); return 'WR4+' if s.startswith('WR') and s not in ('WR1', 'WR2', 'WR3') else s

def effective_slots(dc):
    """Next man up: within each team's position row, players listed OUT (injury -1) are skipped and the active players
    behind them move up (QB/RB/TE renumbered by depth; each WR row's first active player is that row's starter).
    The weekly snapshot keeps the injured starter in slot 1, which would project his replacement as a backup."""
    dc = dc.copy(); dc['eslot'] = dc.slot
    if 'espn_depth' in dc.columns:   # snapshot built by build_depth_chart.py >= 2026-10-06 is already effective (OUT last, usage-adjusted)
        return dc
    act = dc[dc.injury.astype(str) != '-1']
    for (team, row), d in act.groupby(['team', 'pos_row']):
        d = d.sort_values('depth')
        if row.startswith('WR'):
            dc.loc[d.index, 'eslot'] = 'WR4+'; dc.loc[d.index[0], 'eslot'] = row
        elif row in ('QB', 'RB', 'TE'):
            for k, ix in enumerate(d.index): dc.loc[ix, 'eslot'] = f'{row}{k + 1}'
    return dc

def dvpcol(market, g):
    m = MARKETS[market][2]
    if g in m: return m[g]
    if g.startswith('WR') and 'WR' in m: return m['WR']
    return None

L = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
L = L[L.slot.astype(str).str.match(r'^(QB|RB|WR|TE)')].copy()
s0 = L.season.min()
L['t'] = (L.season - s0) * (18 + GAP) + L.week
L['g'] = L.slot.map(grp); L['pos'] = L.slot.str[:2]
L['gp'] = L.slot.map(gprior); L['rl'] = L.slot.map(role)
for m, (cols, _, _) in MARKETS.items(): L['y_' + m] = L[cols].sum(axis=1)
L['y_anytime_td'] = (L['y_anytime_td'] > 0).astype(float)
L['tdn'] = L[['rush_td', 'rec_td']].sum(axis=1)
W = pd.read_csv('data/processed/dvp_weekly.csv'); W['t'] = (W.season - s0) * (18 + GAP) + W.week
# market-implied team points (closing/current DK-consensus line from nflverse): home = total/2 + spread/2
GL = pd.read_csv('data/processed/game_lines.csv')
IMP = {}
for g_ in GL.dropna(subset=['spread_line', 'total_line']).itertuples():
    IMP[(g_.season, g_.week, g_.home_team)] = g_.total_line / 2 + g_.spread_line / 2
    IMP[(g_.season, g_.week, g_.away_team)] = g_.total_line / 2 - g_.spread_line / 2
IMP_AVG = float(np.mean(list(IMP.values())))
DCOLS = sorted({c for m in MARKETS.values() for c in m[2].values()})

def defense_effects(ti):
    """{(defense, col): (effect, league_mean)} using only dvp rows before time ti."""
    P = W[W.t < ti]; res = {}
    for c in DCOLS:
        x = P[c].astype(float).values; lm = x.mean()
        g = P.groupby('opponent')[c]; s, n = g.transform('sum').values, g.transform('count').values
        resid = x - (s - x + K_OFF * lm) / (n - 1 + K_OFF)
        w = 0.5 ** ((ti - P.t.values) / H_DEF)
        a = pd.DataFrame({'d': P.defense.values, 'wr': w * resid, 'w': w}).groupby('d').sum()
        eff = (a.wr / (a.w + K_DEF)).to_dict()
        for d, e in eff.items(): res[(d, c)] = (e, lm)
    return res

RW = 1.0
def baseline(hist_y, hist_t, ti, prior, rm=None):
    w = 0.5 ** ((ti - hist_t) / H_P)
    if rm is not None: w = w * np.where(rm, 1.0, RW)
    return (np.sum(w * hist_y) + K_P * prior) / (w.sum() + K_P), w.sum()

def base_hk(y, t, ti, prior, h, k, rm=None, rw=1.0):
    w = 0.5 ** ((ti - t) / h)
    if rm is not None: w = w * np.where(rm, 1.0, rw)   # games played in a different role count rw as much
    return (np.sum(w * y) + k * prior) / (w.sum() + k)

def slot_priors(P, m):
    y = P['y_' + m] if m != 'anytime_td' else P['tdn']
    return y.groupby(P.gp).mean().to_dict()

def project(P, row_player, g, opp, ti, m, eff, prior_by_slot, beta, gp=None, rl=None):
    """P = this player's prior games. Returns (mu, base, matchup, n_eff)."""
    ycol = 'y_' + m if m != 'anytime_td' else 'tdn'
    prior = prior_by_slot.get(gp or g, np.nan)
    if np.isnan(prior): return None
    rm = (P.rl.values == rl) if (rl is not None and len(P)) else None
    base, neff = baseline(P[ycol].values.astype(float), P.t.values, ti, prior, rm) if len(P) else (prior, 0.0)
    col = dvpcol(m, g); mx = 1.0
    if col and (opp, col) in eff:
        e, lm = eff[(opp, col)]
        if lm > 0: mx = max(0.6, min(1.4, 1 + beta * e / lm))
    return base * mx, base, mx, neff

GRID_H, GRID_K, GRID_R = (4.0, 8.0, 16.0), (1.5, 3.0, 6.0), (1.0, 0.5, 0.25)
def backtest():
    """Per target game store the components so every parameter combination is scored without recomputing."""
    targets = L[((L.season == 2025) & (L.week >= 3)) | (L.season == 2026)]
    rows = []
    for ti in sorted(targets.t.unique()):
        eff = defense_effects(ti); prior_L = L[L.t < ti]
        pri = {m: slot_priors(prior_L, m) for m in MARKETS}
        hist = {pid: d for pid, d in prior_L.groupby('player_id')}
        for r in targets[targets.t == ti].itertuples():
            H = hist.get(r.player_id)
            if H is None or len(H) < 2: continue
            imp = IMP.get((r.season, r.week, r.team))
            ir = imp / IMP_AVG if imp else 1.0
            for m, (cols, poss, _) in MARKETS.items():
                if r.pos not in poss: continue
                prior = pri[m].get(r.gp, np.nan)
                if np.isnan(prior): continue
                ycol = 'y_' + m if m != 'anytime_td' else 'tdn'
                hy, ht = H[ycol].values.astype(float), H.t.values
                rm = H.rl.values == r.rl
                bases = [base_hk(hy, ht, ti, prior, hh, kk, rm, rr) for hh in GRID_H for kk in GRID_K for rr in GRID_R]
                col = dvpcol(m, r.g); er = 0.0
                if col and (r.opponent, col) in eff:
                    e, lm = eff[(r.opponent, col)]; er = e / lm if lm > 0 else 0.0
                rows.append((m, getattr(r, 'y_' + m), prior, er, ir, *bases))
    cols = ['m', 'y', 'prior', 'er', 'ir'] + [f'b_{hh:g}_{kk:g}_{rr:g}' for hh in GRID_H for kk in GRID_K for rr in GRID_R]
    return pd.DataFrame(rows, columns=cols)

def combine(x, bcol, beta, gamma):
    return x[bcol].values * np.clip(1 + beta * x.er.values, 0.6, 1.4) * np.power(x.ir.values, gamma)

def main():
    BT = backtest()
    report, params, dists = [], {}, {}
    for m in MARKETS:
        x = BT[BT.m == m]
        if not len(x): continue
        best = None
        for hh in GRID_H:
          for kk in GRID_K:
            for rr in GRID_R:
                bcol = f'b_{hh:g}_{kk:g}_{rr:g}'
                for beta in (0.0, 0.5, 1.0, 1.5):
                    for gamma in (0.0, 0.5, 1.0):
                        mu = combine(x, bcol, beta, gamma)
                        if m == 'anytime_td':
                            for c in np.arange(0.6, 1.81, 0.1):
                                p = np.clip(1 - np.exp(-c * mu), 1e-4, 1 - 1e-4)
                                ll = -np.mean(x.y * np.log(p) + (1 - x.y) * np.log(1 - p))
                                if best is None or ll < best[0]: best = (ll, hh, kk, beta, gamma, c, rr)
                        else:
                            e = np.mean((x.y.values - mu) ** 2)
                            if best is None or e < best[0]: best = (e, hh, kk, beta, gamma, None, rr)
        _, hh, kk, beta, gamma, c, rr = best
        bcol = f'b_{hh:g}_{kk:g}_{rr:g}'; mu = combine(x, bcol, beta, gamma)
        sc = float(x.y.sum() / mu.sum()) if m != 'anytime_td' and mu.sum() > 0 else 1.0   # remove the small shrinkage bias (mean actual / mean projection)
        mu = mu * sc
        mu_form = combine(x, bcol, 0.0, 0.0)
        if m == 'anytime_td':
            def ll(mu_, cc):
                p = np.clip(1 - np.exp(-cc * mu_), 1e-4, 1 - 1e-4); return -np.mean(x.y * np.log(p) + (1 - x.y) * np.log(1 - p))
            base_ll = ll(x.prior.values, 1.0)
            sk, sk_form = 1 - ll(mu, c) / base_ll, 1 - min(ll(mu_form, cc) for cc in np.arange(0.6, 1.81, 0.1)) / base_ll
        else:
            base = np.mean((x.y.values - x.prior.values) ** 2)
            sk, sk_form = 1 - np.mean((x.y.values - mu) ** 2) / base, 1 - np.mean((x.y.values - mu_form) ** 2) / base
        params[m] = {'H_P': hh, 'K_P': kk, 'RW': rr, 'scale': round(sc, 4), 'beta': beta, 'gamma': gamma, 'skill': round(100 * sk, 2), 'skill_form_only': round(100 * sk_form, 2), 'n': int(len(x))}
        if c is not None: params[m]['c_td'] = round(float(c), 2)
        if m == 'anytime_td':
            p = 1 - np.exp(-c * mu); bins = np.clip((p * 10).astype(int), 0, 9)
            params[m]['calibration'] = [{'p': round(float(p[bins == k].mean()), 3), 'hit': round(float(x.y.values[bins == k].mean()), 3), 'n': int((bins == k).sum())} for k in range(10) if (bins == k).sum() >= 30]
        else:
            ok = mu > 0.5; mm, yy = mu[ok], x.y.values[ok]
            ter = np.quantile(mm, [1 / 3, 2 / 3]); dd = []
            for lo, hi in ((0, ter[0]), (ter[0], ter[1]), (ter[1], 1e9)):
                r = (yy / mm)[(mm >= lo) & (mm < hi)]
                dd.append({'lo': round(float(lo), 2), 'hi': round(float(min(hi, 1e6)), 2), 'q': [round(float(v), 4) for v in np.quantile(r, np.linspace(0, 1, 101))]})
            dists[m] = dd
            def pover(mu_, L_):
                d = next((d for d in dd if d['lo'] <= mu_ < d['hi']), dd[-1]); q = np.array(d['q'])
                return float(1 - np.searchsorted(q, L_ / mu_, side='right') / 101)
            lines = np.floor(mm) + 0.5
            pp = np.array([pover(a, b) for a, b in zip(mm, lines)]); hit = (yy > lines).astype(float)
            bins = np.clip((pp * 10).astype(int), 0, 9)
            params[m]['calibration'] = [{'p': round(float(pp[bins == k].mean()), 3), 'hit': round(float(hit[bins == k].mean()), 3), 'n': int((bins == k).sum())} for k in range(10) if (bins == k).sum() >= 30]
            params[m]['brier'] = round(float(np.mean((pp - hit) ** 2)), 4)
        report.append(f"| {m} | {params[m]['n']} | {params[m]['skill_form_only']:+.2f}% | {params[m]['skill']:+.2f}% | H={hh:g} K={kk:g} role-w={rr:g} β={beta} γ={gamma}{' c=' + str(params[m].get('c_td')) if c else ''} |")
    json.dump({'params': {'H_DEF': H_DEF, 'K_DEF': K_DEF, 'GAP': GAP, 'IMP_AVG': round(IMP_AVG, 2)}, 'markets': params, 'dists': dists},
              open('data/processed/prop_model.json', 'w'))
    print('\n'.join(report))
    current(params, dists)
    sec = ('<!-- props:start -->\n## Player props — walk-forward backtest (' + str(pd.Timestamp.today().date()) + ')\n'
           'Skill = 1 − MSE / MSE(slot-mean) for yardage/count markets; anytime TD = 1 − logloss / logloss(slot-mean rate).\n'
           'Targets: every QB/RB/WR/TE game with ≥2 prior games, 2025 wk 3 → latest 2026 week; projections use only earlier data.\n'
           '"form + matchup + game" adds the opponent-adjusted defense effect (β) and the market-implied team total (γ).\n\n'
           '| market | games | player form only | form + matchup + game | tuned |\n|---|---|---|---|---|\n' + '\n'.join(report) + '\n<!-- props:end -->\n')
    fn = 'notes/model_validation.md'; txt = open(fn, encoding='utf-8').read() if os.path.exists(fn) else ''
    if '<!-- props:start -->' in txt:   # replace this section in place — reruns never stack copies
        txt = txt[:txt.index('<!-- props:start -->')] + sec + txt[txt.index('<!-- props:end -->') + len('<!-- props:end -->\n'):]
    else: txt = txt.rstrip() + '\n\n' + sec
    open(fn, 'w', encoding='utf-8').write(txt)

def current(params, dists):
    ti = L.t.max() + 1
    eff = defense_effects(ti)
    pri = {m: slot_priors(L, m) for m in MARKETS}
    dc = pd.read_csv(sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1])
    dc = effective_slots(dc)
    moved = dc[(dc.eslot != dc.slot) & (dc.injury.astype(str) != '-1') & dc.eslot.str.match(r'^(QB1|RB1|WR[123]$|TE1)')]
    if len(moved): print('next man up: ' + ', '.join(f'{r.player} {r.team} {r.slot}->{r.eslot}' for r in moved.itertuples()))
    sched = pd.read_csv('data/processed/schedule_2026.csv').set_index('team')
    mt = pd.read_csv('data/processed/matchups_current.csv')
    wk = int(mt.week.iloc[0]) if len(mt) else int(L[L.season == L.season.max()].week.max()) + 1
    hist = {pid: d for pid, d in L.groupby('player_id')}
    name2id = L.drop_duplicates('player', keep='last').set_index('player').player_id.to_dict()
    out = []
    for r in dc.itertuples():
        r = r._replace(slot=r.eslot)
        g = grp(r.slot); pos = str(r.slot)[:2]
        if not g or str(getattr(r, 'injury', '1')) == '-1': continue
        o = str(sched.loc[r.team, f'week_{wk}']) if r.team in sched.index else 'BYE'
        if o in ('BYE', 'nan'): continue
        opp = o.replace('@', '')
        pid = name2id.get(r.player); H = hist.get(pid, L.iloc[0:0])
        for m, (cols, poss, _) in MARKETS.items():
            if pos not in poss or m not in params: continue
            P_ = params[m]; globals()['H_P'], globals()['K_P'], globals()['RW'] = P_['H_P'], P_['K_P'], P_.get('RW', 1.0)
            pr = project(H, r.player, g, opp, ti, m, eff, pri[m], P_['beta'], gprior(r.slot), role(r.slot))
            if pr is None: continue
            mu, base, mx, neff = pr
            imp = IMP.get((2026, wk, r.team)); ix = (imp / IMP_AVG) ** P_['gamma'] if imp else 1.0
            mu *= ix * P_.get('scale', 1.0)
            row = dict(week=wk, player=r.player, team=r.team, opp=o, slot=r.slot, market=m, proj=round(mu, 2), base=round(base, 2),
                       matchup_x=round(mx, 3), game_x=round(ix, 3), team_implied=round(imp, 1) if imp else '', n_eff=round(neff, 1), games=len(H))
            if m == 'anytime_td':
                row['p_yes'] = round(1 - math.exp(-params[m].get('c_td', 1.0) * mu), 4)
            else:
                dd = dists[m]; d = next((d for d in dd if d['lo'] <= mu < d['hi']), dd[-1])
                row['q10'], row['q50'], row['q90'] = [round(mu * d['q'][k], 1) for k in (10, 50, 90)]
            out.append(row)
    pd.DataFrame(out).to_csv('data/processed/prop_projections.csv', index=False)
    print(f'prop_projections.csv: {len(out)} player-markets for wk {wk}')

if __name__ == '__main__':
    main()
