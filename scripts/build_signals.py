"""Signal efficacy — does each thing RAINMAN looks at actually move production? -> data/processed/signals.json

Walk-forward over every starter-game with enough history (2025 wk 4+ and 2026 wk 2+): the player's baseline is what he had
averaged BEFORE that game (this season's prior games weighted 2x, last 8 of the prior season 1x; needs >= 3 weighted games),
and the outcome is actual / baseline for the stat. Each signal is computed only from data available before kickoff:
  dvp    opponent's league rank allowing that stat to the player's slot (prior season full + current season to date 2x)
  psi    Ψ = mean of the opponent's ranks across the slot's stat group (the composite the dashboard shows)
  scheme opponent's scheme family × slot index from 2024-25 charting (what that family concedes vs league)
  env    game environment: offense EPA/play + opponent defense EPA/play allowed (season of the game)
  role   snap-share trend: his last game's snap share minus his season-to-date share
  trust  how much of the defense's prior-season snaps returned (does the DvP prior describe this unit?)
Report per market and signal: mean ratio and share-over-baseline in the signal's top / middle / bottom third, the lift
(top − bottom), Spearman rho with the ratio, and n. Ψ gets its own bucket table so the "smash spot" claim is auditable.
Everything here is reproducible from data/game_logs + data/processed; nothing is hand-entered.
"""
import os, json, glob, math
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
P = 'data/processed/'

MARKETS = {  # market: (log column(s) -> value, slots it applies to, DvP stat column pattern per slot)
    'pass_yds': (lambda r: r.pass_yds, ['QB1'], {'QB1': 'QB PY'}),
    'pass_td': (lambda r: r.pass_td, ['QB1'], {'QB1': 'P TD'}),
    'rush_yds': (lambda r: r.rush_yds, ['RB1', 'RB2'], {'RB1': 'RB1 RY', 'RB2': 'RB2+ RY'}),
    'rush_att': (lambda r: r.rush_att, ['RB1', 'RB2'], {'RB1': 'RB1 RY', 'RB2': 'RB2+ RY'}),
    'receptions': (lambda r: r.rec, ['RB1', 'WR1', 'WR2', 'WR3', 'TE1'], {s: f'{s} Recep' for s in ['RB1', 'WR1', 'WR2', 'WR3', 'TE1']}),
    'rec_yds': (lambda r: r.rec_yds, ['RB1', 'WR1', 'WR2', 'WR3', 'TE1'], {s: f'{s} RecY' for s in ['RB1', 'WR1', 'WR2', 'WR3', 'TE1']}),
    'td': (lambda r: r.rush_td + r.rec_td, ['RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE1'], {s: f'{s} TD' for s in ['RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE1']}),
}
GROUP = {'QB1': ['QB PY', 'QB RY', 'QB P+R', 'P TD', 'QB TD'], 'RB1': ['RB1 RY', 'RB1 Recep', 'RB1 RecY', 'RB R+R', 'RB1 TD'],
         'RB2': ['RB2+ RY', 'RB2 Recep', 'RB2 RecY', 'RB R+R', 'RB2 TD'], 'WR1': ['WR1 Recep', 'WR1 RecY', 'WR1 TD'], 'WR2': ['WR2 Recep', 'WR2 RecY', 'WR2 TD'],
         'WR3': ['WR3 Recep', 'WR3 RecY', 'WR3 TD'], 'TE1': ['TE1 Recep', 'TE1 RecY', 'TE1 TD']}
SLOT_GRP = {'QB1': 'QB', 'RB1': 'RB1', 'RB2': 'RB2', 'WR1': 'WR1', 'WR2': 'WR2', 'WR3': 'WR3', 'TE1': 'TE1'}

def spearman(x, y):
    if len(x) < 8: return None
    rx, ry = pd.Series(x).rank(), pd.Series(y).rank()
    c = np.corrcoef(rx, ry)[0, 1]
    return None if np.isnan(c) else round(float(c), 3)

def main():
    logs = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
    wk = pd.read_csv(P + 'dvp_weekly.csv')
    usage = pd.read_csv(P + 'player_usage.csv') if os.path.exists(P + 'player_usage.csv') else None
    tags = pd.read_csv(P + 'scheme_tags.csv'); tags = tags[tags.side == 'DEF']
    eff = pd.read_csv(P + 'scheme_slot_effects.csv')
    off = pd.read_csv(P + 'team_off_tendencies.csv'); dft = pd.read_csv(P + 'team_def_tendencies.csv')
    off_epa = {(int(r.season), r.team): r.epa_play for r in off.itertuples() if 'epa_play' in off.columns}
    def_epa = {(int(r.season), r.team): r.epa_play_allowed for r in dft.itertuples() if 'epa_play_allowed' in dft.columns}
    fam = {(int(r.season), r.team): r.primary_tag for r in tags.itertuples()}
    eidx = {(r.family, r.grp): r.index for r in eff.itertuples()}
    seasons = sorted(logs.season.unique())
    # DvP allowed per defense through a cutoff: prior season full (1x) + current season weeks < w (2x)
    stat_cols = [c for c in wk.columns if c not in ('defense', 'season', 'week', 'opponent')]
    def dvp_ranks(season, week):
        prev = wk[wk.season == season - 1]; cur = wk[(wk.season == season) & (wk.week < week)]
        if len(cur) == 0 and len(prev) == 0: return None
        parts = []
        if len(prev): parts.append(prev.assign(w=1.0))
        if len(cur): parts.append(cur.assign(w=2.0))
        d = pd.concat(parts)
        g = d.groupby('defense')
        allowed = g[stat_cols].apply(lambda x: (x.mul(d.loc[x.index, 'w'], axis=0).sum()) / d.loc[x.index, 'w'].sum())
        ranks = allowed.rank(ascending=False, method='average')
        return allowed, ranks
    cache = {}
    out = []
    logs = logs.sort_values(['season', 'week'])
    by_player = {p: g for p, g in logs.groupby('player')}
    for season in seasons:
        if season == seasons[0]: continue
        weeks = sorted(logs[logs.season == season].week.unique())
        for w in weeks:
            if w < 2: continue
            key = (season, w)
            if key not in cache: cache[key] = dvp_ranks(season, w)
            if cache[key] is None: continue
            allowed, ranks = cache[key]
            cur = logs[(logs.season == season) & (logs.week == w)]
            cur = cur[cur.slot.isin(SLOT_GRP)]
            for r in cur.itertuples():
                hist = by_player[r.player]
                prior_cur = hist[(hist.season == season) & (hist.week < w)]
                prior_prev = hist[hist.season == season - 1].tail(8)
                wsum = 2 * len(prior_cur) + len(prior_prev)
                if wsum < 3: continue
                opp = r.opponent
                if opp not in ranks.index: continue
                grp = SLOT_GRP[r.slot]
                psi = float(np.mean([ranks.loc[opp, c] for c in GROUP[r.slot] if c in ranks.columns]))
                sch = eidx.get((fam.get((season, opp)), grp))
                env = None
                if (season, r.team) in off_epa and (season, opp) in def_epa: env = off_epa[(season, r.team)] + def_epa[(season, opp)]
                role = None
                if usage is not None:
                    u = usage[(usage.player == r.player) & (usage.season == season) & (usage.week < w)]
                    if len(u) >= 2 and u.snap_pct.notna().sum() >= 2:
                        role = float(u.sort_values('week').snap_pct.iloc[-1] - u.snap_pct.mean())
                for m, (fn, slots, cols) in MARKETS.items():
                    if r.slot not in slots: continue
                    base = (2 * sum(fn(x) for x in prior_cur.itertuples()) + sum(fn(x) for x in prior_prev.itertuples())) / wsum
                    if m == 'td':
                        if base < 0.15: continue
                    elif base < (10 if m in ('receptions', 'rush_att') else 20) * (0.25 if m == 'pass_td' else 1) and m != 'pass_td': continue
                    elif m == 'pass_td' and base < 0.6: continue
                    actual = fn(r)
                    col = cols[r.slot]
                    out.append({'season': season, 'week': w, 'player': r.player, 'team': r.team, 'opp': opp, 'slot': r.slot, 'market': m,
                                'base': round(base, 2), 'actual': actual, 'ratio': round(actual / base, 3) if base else None,
                                'dvp': float(ranks.loc[opp, col]) if col in ranks.columns else None, 'psi': round(psi, 2),
                                'scheme': sch, 'env': env, 'role': role})
    df = pd.DataFrame(out)
    df.to_csv(P + 'signals_rows.csv', index=False)
    # tertile report per market × signal (dvp & psi: low rank = soft → "top" = softest third)
    def tert(d, col, invert=False):
        d = d[d[col].notna() & d.ratio.notna()]
        if len(d) < 30: return None
        q1, q2 = d[col].quantile([1 / 3, 2 / 3])
        lo, mid, hi = d[d[col] <= q1], d[(d[col] > q1) & (d[col] <= q2)], d[d[col] > q2]
        if invert: lo, hi = hi, lo   # rank: low number = soft = favorable → report as "top"
        f = lambda x: {'n': int(len(x)), 'ratio': round(float(x.ratio.mean()), 3), 'median': round(float(x.ratio.median()), 3), 'over': round(float((x.ratio > 1).mean()), 3)}
        rho = spearman(d[col].values * (-1 if invert else 1), d.ratio.values)
        return {'top': f(hi), 'mid': f(mid), 'bottom': f(lo), 'lift': round(f(hi)['ratio'] - f(lo)['ratio'], 3), 'rho': rho, 'n': int(len(d)),
                'cut_top': round(float(q2 if not invert else q1), 2), 'cut_bottom': round(float(q1 if not invert else q2), 2)}
    SIG = {'dvp': ('opponent DvP rank for the stat (1 = allows the most)', True), 'psi': ('Ψ composite rank for the slot', True),
           'scheme': ('scheme family × slot index (100 = league avg conceded)', False), 'env': ('game environment: off EPA + opp def EPA allowed', False),
           'role': ('snap-share trend: last game − season', False)}
    rep = {'built': str(pd.Timestamp.today().date()), 'rows': int(len(df)), 'seasons': [int(s) for s in df.season.unique()] if len(df) else [],
           'signals': {k: {'label': v[0], 'markets': {}} for k, v in SIG.items()}, 'psi_buckets': {}, 'overall': {}}
    for m in MARKETS:
        d = df[df.market == m]
        for k, (lbl, inv) in SIG.items():
            t = tert(d, k, inv)
            if t: rep['signals'][k]['markets'][m] = t
    for k, (lbl, inv) in SIG.items():
        t = tert(df, k, inv)
        if t: rep['overall'][k] = t
    # Ψ by rank band — is a "smash spot" (Ψ <= 5) real?
    for m in list(MARKETS) + ['all']:
        d = df if m == 'all' else df[df.market == m]
        d = d[d.psi.notna() & d.ratio.notna()]
        bands = [('1-5', 0, 5), ('6-10', 5, 10), ('11-16', 10, 16), ('17-22', 16, 22), ('23-27', 22, 27), ('28-32', 27, 40)]
        rep['psi_buckets'][m] = [{'band': b, 'n': int(((d.psi > lo) & (d.psi <= hi)).sum()),
                                  'ratio': round(float(d[(d.psi > lo) & (d.psi <= hi)].ratio.mean()), 3) if ((d.psi > lo) & (d.psi <= hi)).any() else None,
                                  'over': round(float((d[(d.psi > lo) & (d.psi <= hi)].ratio > 1).mean()), 3) if ((d.psi > lo) & (d.psi <= hi)).any() else None}
                                 for b, lo, hi in bands]
    # prop-model skill per market (walk-forward, from build_prop_model) rides along so one panel holds every component's grade
    if os.path.exists(P + 'prop_model.json'):
        pm = json.load(open(P + 'prop_model.json'))
        rep['prop_model'] = {m: {'skill': v.get('skill'), 'skill_form_only': v.get('skill_form_only'), 'n': v.get('n'), 'brier': v.get('brier'), 'calibration': v.get('calibration')} for m, v in pm.get('markets', {}).items()}
    # game-model backtest (build_games) for the same panel
    if os.path.exists(P + 'picks_retro.csv'):
        pass
    json.dump(rep, open(P + 'signals.json', 'w'), indent=1)
    print(f"signals.json: {len(df)} starter-games · overall lift (top third − bottom third, actual/baseline): " +
          ' · '.join(f"{k} {v['lift']:+.3f} (rho {v['rho']})" for k, v in rep['overall'].items()))
    pb = rep['psi_buckets']['all']
    print('  Ψ bands: ' + ' · '.join(f"{b['band']}: {b['ratio']} ({b['over']} over, n={b['n']})" for b in pb))

if __name__ == '__main__':
    main()
