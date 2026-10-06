"""Bet board data: every posted player-prop line priced by the prop model, anytime-TD fair prices, and the same-game
correlation table that prices parlays.

Inputs : data/processed/prop_projections.csv + prop_model.json   (build_prop_model.py)
         data/processed/props_current.csv                        (DraftKings lines via ESPN — no prices; -110 assumed)
         data/raw/odds_api/*.csv                                 (FanDuel / other books with prices, fetch_odds_api.py)
Outputs: data/processed/bet_lines.csv   one row per player × market × book × line: P(over), P(under), fair odds, EV
         data/processed/bet_corr.json   residual correlations between roles/stats in the same game (SGP pricing)
EV: P(win) × decimal payout − 1, from the book's price when we have it; at an assumed −110 when the feed has none.
"""
import os, json, glob, math
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
MK = {'Passing Yards': 'pass_yds', 'Pass Completions': 'completions', 'Passing Touchdowns': 'pass_td', 'Passing Attempts': 'pass_att',
      'Passing Interceptions': 'interceptions', 'Passing Plus Rushing Yards': 'pass_rush_yds', 'Carries': 'rush_att', 'Rushing Yards': 'rush_yds',
      'Receiving Yards': 'rec_yds', 'Receptions': 'receptions', 'Rushing Plus Receiving Yards': 'rush_rec_yds'}
# The book's line already contains information the model doesn't (injuries, role news, sharp money). Until the graded
# ledger can estimate it, the model's probability is shrunk toward the market's ~50% at the line: p = .5 + W_MODEL*(p_model-.5)
W_MODEL = 0.35
N_FULL = 4.0   # the model earns its full weight only with >= 4 recency-weighted games of the player's own history in this role
wt = lambda neff: W_MODEL * min(1.0, float(neff or 0) / N_FULL) if neff == neff else 0.0
dec = lambda am: 1 + (am / 100 if am > 0 else 100 / -am)
def fair(p):
    if p <= 0 or p >= 1: return None
    return round(-100 * p / (1 - p)) if p >= .5 else round(100 * (1 - p) / p)

def main():
    M = json.load(open('data/processed/prop_model.json'))
    PJ = pd.read_csv('data/processed/prop_projections.csv')
    key = lambda n: ''.join(ch for ch in str(n).lower() if ch.isalpha())
    PJ['k'] = PJ.player.map(key)
    lines = []
    if os.path.exists('data/processed/props_current.csv'):
        D = pd.read_csv('data/processed/props_current.csv')
        for r in D.itertuples():
            m = MK.get(r.market)
            if m: lines.append(dict(player=r.player, market=m, book='DK', line=r.line, over=None, under=None, open=r.open, updated=r.updated))
    for f in sorted(glob.glob('data/raw/odds_api/props_*.csv'))[-1:]:
        O = pd.read_csv(f)
        for (pl, m, bk, ln), g in O.groupby(['player', 'market', 'book', 'line']):
            ov = g[g.side == 'Over'].price; un = g[g.side == 'Under'].price
            lines.append(dict(player=pl, market=m, book=bk, line=ln, over=float(ov.iloc[0]) if len(ov) else None,
                              under=float(un.iloc[0]) if len(un) else None, open=None, updated=g.updated.iloc[0]))
    out = []
    for x in lines:
        r = PJ[(PJ.k == key(x['player'])) & (PJ.market == x['market'])]
        if x['market'] == 'anytime_td': continue          # priced separately below
        if not len(r) or x['market'] not in M['dists']: continue
        r = r.iloc[0]; mu = float(r.proj); dd = M['dists'][x['market']]
        d = next((d for d in dd if d['lo'] <= mu < d['hi']), dd[-1]); q = np.array(d['q'])
        po = float(1 - np.searchsorted(q, x['line'] / mu, side='right') / 101) if mu > 0 else 0.0
        pu = 1 - po   # pushes impossible on .5 lines; whole-number lines rare in props
        ov, un = x['over'] or -110, x['under'] or -110
        # market probability at the line: no-vig from both prices when we have them, else 50%
        pm = .5
        if x['over'] and x['under']:
            io, iu = 1 / dec(x['over']), 1 / dec(x['under']); pm = io / (io + iu)
        pao = pm + wt(r.n_eff) * (po - pm); pau = 1 - pao
        evo, evu = pao * dec(ov) - 1, pau * dec(un) - 1
        side = 'Over' if evo >= evu else 'Under'
        out.append(dict(week=int(r.week), player=r.player, team=r.team, opp=r.opp, slot=r.slot, market=x['market'], book=x['book'],
                        line=x['line'], over_price=x['over'], under_price=x['under'], priced=x['over'] is not None,
                        proj=round(mu, 1), q10=r.q10, q50=r.q50, q90=r.q90, p_over_model=round(po, 3), p_over=round(pao, 3), p_under=round(pau, 3),
                        fair_over=fair(pao), fair_under=fair(pau), side=side, ev=round(100 * max(evo, evu), 1),
                        matchup_x=r.matchup_x, game_x=r.game_x, team_implied=r.team_implied, n_eff=r.n_eff, w_model=round(wt(r.n_eff), 3),
                        skill=M['markets'][x['market']]['skill'], open=x['open'], updated=x['updated']))
    B = pd.DataFrame(out)
    B.to_csv('data/processed/bet_lines.csv', index=False)
    # anytime TD: every projected player, fair price from the model; book price + EV where a priced feed has it
    T = PJ[PJ.market == 'anytime_td'].copy()
    prices = {}
    for f in sorted(glob.glob('data/raw/odds_api/props_*.csv'))[-1:]:
        O = pd.read_csv(f); O = O[O.market == 'anytime_td']
        for r in O.itertuples(): prices.setdefault(key(r.player), {})[r.book] = float(r.price)
    rows = []
    for r in T.itertuples():
        p = float(r.p_yes); pr = prices.get(r.k, {}); bk, best = (max(pr.items(), key=lambda kv: kv[1]) if pr else (None, None))
        pm = (1 / dec(best)) / 1.045 if best else None                     # ~4.5% hold removed from a one-sided price
        w_ = wt(getattr(r, 'n_eff', N_FULL))
        pa = pm + w_ * (p - pm) if pm else p
        rows.append(dict(week=r.week, player=r.player, team=r.team, opp=r.opp, slot=r.slot, lam=r.proj, p_model=round(p, 3), p=round(pa, 3),
                         fair=fair(p), book=bk, price=best, ev=round(100 * (pa * dec(best) - 1), 1) if best else None, w_model=round(w_, 3),
                         matchup_x=r.matchup_x, game_x=r.game_x, team_implied=r.team_implied))
    pd.DataFrame(rows).sort_values('p_model', ascending=False).to_csv('data/processed/bet_td.csv', index=False)
    print(f'bet_td.csv: {len(rows)} anytime-TD prices ({sum(1 for x in rows if x["price"])} with a book price)')
    print(f'bet_lines.csv: {len(B)} priced lines · books {sorted(B.book.unique()) if len(B) else []}')
    ledger(B)
    corr()

def ledger(B):
    """Freeze every priced line the first time it is seen (the model's call at that moment) and grade it from the game logs.
    This is the honest record: it is what tunes W_MODEL and shows whether the edges are real."""
    LP = 'data/processed/bet_ledger.csv'
    cols = ['frozen_on', 'week', 'player', 'team', 'opp', 'market', 'book', 'line', 'over_price', 'under_price', 'proj', 'p_over_model',
            'p_over', 'side', 'ev', 'n_eff', 'actual', 'result']
    led = pd.read_csv(LP) if os.path.exists(LP) else pd.DataFrame(columns=cols)
    k = lambda d: d.week.astype(str) + '|' + d.player + '|' + d.market + '|' + d.book + '|' + d.line.astype(str)
    new = B[~k(B).isin(set(k(led)) if len(led) else set())].copy()
    if len(new):
        new['frozen_on'] = str(pd.Timestamp.today().date()); new['actual'] = np.nan; new['result'] = ''
        led = pd.concat([led, new[cols]], ignore_index=True)
    L = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
    L = L[L.season == L.season.max()]
    COLS = {'pass_yds': ['pass_yds'], 'pass_td': ['pass_td'], 'pass_att': ['pass_att'], 'completions': ['cmp'], 'interceptions': ['int'],
            'rush_yds': ['rush_yds'], 'rush_att': ['rush_att'], 'receptions': ['rec'], 'rec_yds': ['rec_yds'],
            'rush_rec_yds': ['rush_yds', 'rec_yds'], 'pass_rush_yds': ['pass_yds', 'rush_yds']}
    for i, r in led.iterrows():
        if isinstance(r.result, str) and r.result: continue
        g = L[(L.player == r.player) & (L.week == r.week)]
        if not len(g): continue
        a = float(g[COLS[r.market]].sum(axis=1).iloc[0]); led.at[i, 'actual'] = a
        led.at[i, 'result'] = 'P' if a == r.line else ('W' if (a > r.line) == (r.side == 'Over') else 'L')
    led.to_csv(LP, index=False)
    gr = led[led.result.isin(['W', 'L'])]
    if len(gr): print(f"bet_ledger.csv: {len(led)} frozen · graded {len(gr)}: {(gr.result == 'W').sum()}-{(gr.result == 'L').sum()}")
    else: print(f'bet_ledger.csv: {len(led)} frozen · none graded yet')

def corr():
    """Residual correlations (each stat minus the player's season mean) between role-stats in the same game."""
    L = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
    L = L[L.slot.astype(str).str.match(r'^(QB1|RB1|RB2|WR1|WR2|WR3|TE1)$')].copy()
    L['td'] = ((L.rush_td + L.rec_td) > 0).astype(float)
    L['rush_rec_yds'] = L.rush_yds + L.rec_yds
    ST = {'QB1': ['pass_yds', 'pass_td', 'rush_yds', 'pass_att'], 'RB1': ['rush_yds', 'rec_yds', 'receptions', 'td'], 'RB2': ['rush_yds', 'td'],
          'WR1': ['rec_yds', 'receptions', 'td'], 'WR2': ['rec_yds', 'receptions', 'td'], 'WR3': ['rec_yds', 'td'], 'TE1': ['rec_yds', 'receptions', 'td']}
    L = L.rename(columns={'rec': 'receptions'})
    cols = sorted({c for v in ST.values() for c in v})
    for c in cols: L[c + '_r'] = L[c] - L.groupby(['player_id', 'season'])[c].transform('mean')
    gl = pd.read_csv('data/processed/game_lines.csv').dropna(subset=['total_line', 'total'])
    tot = {}
    for g in gl.itertuples():
        for t in (g.home_team, g.away_team): tot[(g.season, g.week, t)] = g.total - g.total_line
    wide = {}
    for (se, wk, tm), g in L.groupby(['season', 'week', 'team']):
        rec = {}
        for r in g.itertuples():
            for st in ST.get(r.slot, []): rec[f'{r.slot}:{st}'] = getattr(r, st + '_r')
        rec['GAME:total_over'] = tot.get((se, wk, tm), np.nan)
        wide[(se, wk, tm)] = rec
    Wd = pd.DataFrame.from_dict({f'{k[0]}|{k[1]}|{k[2]}': v for k, v in wide.items()}, orient='index')
    C = Wd.corr(min_periods=150).round(3)
    # opponent pairs (cross-team): QB1 pass yds vs opposing QB1 pass yds etc. via game key
    opp = {}
    for (se, wk, tm), g in L.groupby(['season', 'week', 'team']):
        o = g.opponent.iloc[0]; opp[f'{se}|{wk}|{tm}'] = f'{se}|{wk}|{o}'
    X = Wd.copy(); X.columns = ['OPP_' + c for c in X.columns]
    X.index = [opp.get(i, i) for i in Wd.index]
    J2 = Wd.join(X, how='inner')
    CO = J2.corr(min_periods=150).loc[Wd.columns, X.columns].round(3)
    out = {'same': {a: {b: C.loc[a, b] for b in C.columns if a != b and pd.notna(C.loc[a, b])} for a in C.index},
           'opp': {a: {b[4:]: CO.loc[a, b] for b in CO.columns if pd.notna(CO.loc[a, b])} for a in CO.index},
           'n_games': int(len(Wd))}
    json.dump(out, open('data/processed/bet_corr.json', 'w'))
    print(f"bet_corr.json: {len(out['same'])} role-stats · e.g. QB1 pass_yds ~ WR1 rec_yds rho {out['same'].get('QB1:pass_yds', {}).get('WR1:rec_yds')}"
          f" · QB1 pass_yds ~ game over rho {out['same'].get('QB1:pass_yds', {}).get('GAME:total_over')}")

if __name__ == '__main__':
    main()
