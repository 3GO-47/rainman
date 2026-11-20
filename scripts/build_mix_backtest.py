"""Mixture backtest — every signal the dash has for a prop line, alone and in every combination, graded on the frozen ledger.

One row per (week, player, market) at the line most books posted. Every signal is rebuilt AS OF that week (only games before it):
  mdl      the prop model's P(over) frozen with the line          edge    model P(over) minus the market's de-vigged P(over)
  projgap  model projection vs the line                            l10/l5  his over-rate against this line, last 10 / 5 games
  avg      his season average vs the line                          l3      his last-3 average vs the line
  h2h      his average vs this opponent vs the line                dvp     what this defense allows his slot in this stat vs the league, season
  dvp3/5   the same over the defense's last 3 / 5 games            env     his team's implied points          home    home / away
Each signal votes over / under / abstains. Tested: each alone, every agreeing combination of up to 4, and a walk-forward logistic
blend (fit on earlier weeks only, bet the next week). Units are paid at the best posted price for the side (-110 where none was stored).
Output: data/processed/mix_backtest.json + a printed summary.
"""
import os, re, json, glob, itertools
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SE = 2026
nk = lambda n: re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv|v)\b', '', str(n).lower().replace('.', ' ')))
COLS = {'pass_yds': ['pass_yds'], 'pass_td': ['pass_td'], 'pass_att': ['pass_att'], 'completions': ['cmp'], 'interceptions': ['int'], 'rush_yds': ['rush_yds'],
        'rush_att': ['rush_att'], 'receptions': ['rec'], 'rec_yds': ['rec_yds'], 'rush_rec_yds': ['rush_yds', 'rec_yds'], 'pass_rush_yds': ['pass_yds', 'rush_yds']}
BASE = sorted({c for v in COLS.values() for c in v})
def slotg(s):
    s = str(s)
    if s.startswith('QB'): return 'QB'
    if s.startswith('RB') or s.startswith('FB'): return 'RB1' if s == 'RB1' else 'RB2'
    if s.startswith('WR'): return s if s in ('WR1', 'WR2', 'WR3') else 'WR4+'
    if s.startswith('TE'): return 'TE1' if s == 'TE1' else 'TE2'
    return ''
def dec(p):
    try: p = float(p)
    except Exception: return None
    if p != p or p == 0: return None
    return 1 + p / 100 if p > 0 else 1 + 100 / abs(p)

def load():
    L = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
    L = L[L.season >= SE - 1].copy(); L['k'] = L.player.map(nk); L['t'] = L.season * 100 + L.week; L['g'] = L.slot.map(slotg)
    for c in BASE: L[c] = pd.to_numeric(L[c], errors='coerce').fillna(0)
    led = pd.read_csv('data/processed/bet_ledger.csv'); led = led[led.result.isin(['W', 'L'])].copy()
    G = pd.read_csv('data/processed/game_lines.csv'); G = G[G.season == SE]
    return L, led, G

def main():
    L, led, G = load()
    cur = L[L.season == SE]
    byp = {k: g.sort_values('t') for k, g in L.groupby('k')}
    # defense allowed per (def, slot group, week) and the weeks each defense played
    DA = cur.groupby(['opponent', 'g', 'week'])[BASE].sum(); DW = cur.groupby('opponent').week.apply(lambda s: sorted(set(s))).to_dict()
    da = {k: v for k, v in zip(DA.index, DA.values)}; bi = {c: i for i, c in enumerate(BASE)}
    def allowed(d, g, w, m):
        v = da.get((d, g, w)); return 0.0 if v is None else float(sum(v[bi[c]] for c in COLS[m]))
    lgc = {}
    def league(g, wk, m):
        key = (g, wk, m)
        if key not in lgc:
            vs = [allowed(d, g, w, m) for d, ws in DW.items() for w in ws if w < wk]; lgc[key] = np.mean(vs) if vs else np.nan
        return lgc[key]
    env = {}
    for r in G.itertuples():
        if r.spread_line != r.spread_line or r.total_line != r.total_line: continue
        env[(int(r.week), r.home_team)] = r.total_line / 2 + r.spread_line / 2; env[(int(r.week), r.away_team)] = r.total_line / 2 - r.spread_line / 2
    fix = {'LA': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX'}; env = {(w, fix.get(t, t)): v for (w, t), v in env.items()}
    def signals(H, w, m, line, d, sg, team, home, pm, pk, proj):
        prior = H[H.t < SE * 100 + w]; ser = prior[COLS[m]].sum(axis=1).values; curs = prior[prior.season == SE][COLS[m]].sum(axis=1).values; den = max(line, 1.0)
        dws = [x for x in DW.get(d, []) if x < w]; lg = league(sg, w, m)
        dv = lambda n: (np.mean([allowed(d, sg, x, m) for x in dws[-n:]]) / lg - 1) if (len(dws) >= min(n, 3) and lg and lg == lg and lg > 0) else np.nan
        h2 = prior[prior.opponent == d][COLS[m]].sum(axis=1).values; e = env.get((w, team))
        return dict(mdl=pm - .5 if pm == pm else np.nan, edge=pm - pk if pm == pm and pk == pk else np.nan, projgap=(proj - line) / den if proj == proj else np.nan,
                    l10=(np.mean(ser[-10:] > line) - .5) if len(ser) >= 4 else np.nan, l5=(np.mean(ser[-5:] > line) - .5) if len(ser) >= 4 else np.nan,
                    avg=(curs.mean() - line) / den if len(curs) >= 3 else np.nan, l3=(ser[-3:].mean() - line) / den if len(ser) >= 3 else np.nan,
                    h2h=(h2.mean() - line) / den if len(h2) >= 1 else np.nan, dvp=dv(99), dvp3=dv(3), dvp5=dv(5),
                    env=(e - 22.5) / 22.5 if e is not None else np.nan, home=.5 if home else -.5,
                    l10k=int((ser[-10:] > line).sum()) if len(ser) else 0, l10n=int(min(10, len(ser))), dvp_allowed=float(np.mean([allowed(d, sg, x, m) for x in dws])) if dws else None, dvp_lg=float(lg) if lg == lg else None)
    rows = []
    for (w, p, m), g in led.groupby(['week', 'player', 'market']):
        if m not in COLS: continue
        line = g.line.mode().iloc[0]; gg = g[g.line == line]; actual = float(gg.actual.iloc[0])
        if actual == line: continue
        H = byp.get(nk(p));
        if H is None: continue
        me = H[(H.season == SE) & (H.week == w)]
        if not len(me): continue
        me = me.iloc[0]
        op = [x for x in map(dec, gg.over_price) if x]; up = [x for x in map(dec, gg.under_price) if x]
        kal = gg[gg.book.astype(str).str.lower() == 'kalshi']; ko = [x for x in map(dec, kal.over_price) if x]; ku = [x for x in map(dec, kal.under_price) if x]
        sg = me.g; S = signals(H, int(w), m, float(line), me.opponent, sg, me.team, me.home_away == 'H', gg.p_over_model.mean(), gg.p_over.mean(), gg.proj.mean())
        rows.append(dict(week=int(w), player=p, market=m, line=float(line), actual=actual, over=int(actual > line), po=max(op) if op else 1.909, pu=max(up) if up else 1.909,
                         ko=max(ko) if ko else np.nan, ku=max(ku) if ku else np.nan, slot=sg, **{k: v for k, v in S.items() if k in ('mdl', 'edge', 'projgap', 'l10', 'l5', 'avg', 'l3', 'h2h', 'dvp', 'dvp3', 'dvp5', 'env', 'home')}))
    D = pd.DataFrame(rows); SIG = ['mdl', 'edge', 'projgap', 'l10', 'l5', 'avg', 'l3', 'h2h', 'dvp', 'dvp3', 'dvp5', 'env', 'home']
    TH = dict(mdl=.03, edge=.03, projgap=.05, l10=.1, l5=.1, avg=.05, l3=.05, h2h=.05, dvp=.10, dvp3=.10, dvp5=.10, env=.08, home=0)
    V = np.zeros((len(D), len(SIG)), dtype=int)
    for j, s in enumerate(SIG):
        x = D[s].values; V[:, j] = np.where(np.isnan(x) | (np.abs(x) <= TH[s]) & (s != 'home'), 0, np.sign(x)).astype(int)
    over = D.over.values; po = D.po.values; pu = D.pu.values; wk = D.week.values
    def score(side, mask=None):   # side: +1 over / -1 under / 0 no bet
        b = side != 0
        if mask is not None: b &= mask
        if not b.any(): return dict(n=0, w=0, hit=None, units=0.0, flat=0.0, roi=None)
        win = (side[b] == 1) == (over[b] == 1); price = np.where(side[b] == 1, po[b], pu[b])
        u = np.where(win, price - 1, -1.0).sum(); f = np.where(win, .909, -1.0).sum()
        return dict(n=int(b.sum()), w=int(win.sum()), hit=round(float(win.mean()), 4), units=round(float(u), 1), flat=round(float(f), 1), roi=round(float(u / b.sum()), 4))
    weeks = sorted(D.week.unique()); print(f'{len(D)} graded player-markets · weeks {weeks[0]}–{weeks[-1]} · over rate {over.mean():.3f}')
    out = dict(built=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), n=int(len(D)), weeks=[int(x) for x in weeks], over_rate=round(float(over.mean()), 4), signals=SIG, thresholds=TH)
    # 0. baselines
    out['baseline'] = dict(always_under=score(np.full(len(D), -1)), always_over=score(np.full(len(D), 1)))
    print('always under', out['baseline']['always_under'], '| always over', out['baseline']['always_over'])
    # 1. each signal alone
    out['single'] = {}
    for j, s in enumerate(SIG):
        r = score(V[:, j]); r['weeks_up'] = int(sum(1 for w in weeks if (score(V[:, j], wk == w)['units'] or 0) > 0)); r['over_side'] = score(np.where(V[:, j] == 1, 1, 0)); r['under_side'] = score(np.where(V[:, j] == -1, -1, 0)); out['single'][s] = r
        print(f"  {s:8} n {r['n']:5} hit {r['hit']} units {r['units']:7} roi {r['roi']} weeks up {r['weeks_up']}/{len(weeks)} | over {r['over_side']['hit']} ({r['over_side']['n']}) under {r['under_side']['hit']} ({r['under_side']['n']})")
    # 2. every agreeing combination of up to 4 signals
    combos = []
    for k in (1, 2, 3, 4):
        for c in itertools.combinations(range(len(SIG)), k):
            sub = V[:, c]; side = np.where((sub == 1).all(axis=1), 1, np.where((sub == -1).all(axis=1), -1, 0)); combos.append((c, side))
    def tab(mask):
        res = []
        for c, side in combos:
            r = score(side, mask); r['c'] = c; res.append(r)
        return res
    full = tab(None); perw = {w: tab(wk == w) for w in weeks}
    for i, r in enumerate(full): r['weeks_up'] = int(sum(1 for w in weeks if perw[w][i]['units'] > 0)); r['weeks_bet'] = int(sum(1 for w in weeks if perw[w][i]['n'] >= 5))
    best = sorted([r for r in full if r['n'] >= 250], key=lambda r: -r['roi'])[:25]
    out['combos_in_sample'] = [dict(signals=[SIG[j] for j in r['c']], n=r['n'], hit=r['hit'], units=r['units'], flat=r['flat'], roi=r['roi'], weeks_up=r['weeks_up'], weeks_bet=r['weeks_bet']) for r in best]
    print('\nbest agreeing combinations, all weeks (IN-SAMPLE, n ≥ 250):')
    for r in out['combos_in_sample'][:12]: print(f"  {' + '.join(r['signals']):32} n {r['n']:5} hit {r['hit']} units {r['units']:7} roi {r['roi']} up {r['weeks_up']}/{r['weeks_bet']}")
    # 3. walk-forward: pick the combination on the weeks before, bet it the next week
    wf = []; picks = []
    for w in weeks:
        tr = [x for x in weeks if x < w]
        if len(tr) < 2: continue
        trm = np.isin(wk, tr); cand = [(i, score(side, trm)) for i, (c, side) in enumerate(combos)]
        cand = [(i, r) for i, r in cand if r['n'] >= 150]
        if not cand: continue
        top = sorted(cand, key=lambda x: -x[1]['roi'])[:5]
        for rank, (i, rtr) in enumerate(top):
            te = score(combos[i][1], wk == w); picks.append(dict(week=int(w), rank=rank + 1, signals=[SIG[j] for j in combos[i][0]], train=dict(n=rtr['n'], hit=rtr['hit'], roi=rtr['roi']), test=te))
        te1 = score(combos[top[0][0]][1], wk == w); wf.append(dict(week=int(w), signals=[SIG[j] for j in combos[top[0][0]][0]], **te1))
        side5 = np.zeros(len(D), dtype=int)
        for i, _ in top:
            s = combos[i][1]; side5 = np.where(side5 == 0, s, side5)
        wf[-1]['top5'] = score(side5, wk == w)
    out['walk_forward'] = wf
    tot = lambda rs: dict(n=sum(r['n'] for r in rs), w=sum(r['w'] for r in rs), units=round(sum(r['units'] for r in rs), 1), flat=round(sum(r['flat'] for r in rs), 1))
    t1 = tot(wf); t5 = tot([r['top5'] for r in wf]); out['walk_forward_total'] = dict(top1=t1, top5=t5)
    print('\nwalk-forward (combination chosen on earlier weeks, bet the next):')
    for r in wf: print(f"  wk {r['week']}: {' + '.join(r['signals']):28} n {r['n']:4} hit {r['hit']} units {r['units']:6} | top-5 union n {r['top5']['n']:4} hit {r['top5']['hit']} units {r['top5']['units']}")
    print(f"  total top-1: {t1['w']}-{t1['n'] - t1['w']} ({t1['w'] / max(1, t1['n']):.3f}) {t1['units']:+} units · top-5 union: {t5['w']}-{t5['n'] - t5['w']} ({t5['w'] / max(1, t5['n']):.3f}) {t5['units']:+} units")
    # 4. walk-forward logistic blend
    X = np.nan_to_num(D[SIG].values.astype(float)); X = np.clip(X, -1.5, 1.5)
    def fit(Xt, yt, lam=5.0, it=40):
        mu = Xt.mean(0); sd = Xt.std(0) + 1e-9; Z = np.c_[np.ones(len(Xt)), (Xt - mu) / sd]; b = np.zeros(Z.shape[1]); R = np.eye(Z.shape[1]) * lam; R[0, 0] = 0
        for _ in range(it):
            p = 1 / (1 + np.exp(-Z @ b)); Wd = p * (1 - p) + 1e-9; b = b + np.linalg.solve(Z.T @ (Z * Wd[:, None]) + R, Z.T @ (yt - p) - R @ b)
        return b, mu, sd
    pred = np.full(len(D), np.nan)
    for w in weeks:
        trm = wk < w
        if trm.sum() < 800: continue
        b, mu, sd = fit(X[trm], over[trm].astype(float)); te = wk == w; pred[te] = 1 / (1 + np.exp(-(np.c_[np.ones(te.sum()), (X[te] - mu) / sd] @ b)))
    out['logit'] = {}; has = ~np.isnan(pred); print('\nwalk-forward logistic blend of all signals (fit on earlier weeks only):')
    for thr in (.52, .54, .56, .58, .60, .62):
        side = np.where(has & (pred >= thr), 1, np.where(has & (pred <= 1 - thr), -1, 0)); r = score(side); r['by_week'] = {int(w): score(side, wk == w) for w in weeks if (has & (wk == w)).any()}; r['weeks_up'] = sum(1 for v in r['by_week'].values() if v['units'] > 0)
        out['logit'][str(thr)] = r; print(f"  P ≥ {thr}: n {r['n']:5} hit {r['hit']} units {r['units']:7} flat {r['flat']:7} roi {r['roi']} weeks up {r['weeks_up']}/{len(r['by_week'])}  by week: " + ' '.join(f"{w}:{v['units']:+.0f}" for w, v in r['by_week'].items()))
    b, mu, sd = fit(X, over.astype(float)); out['logit_weights'] = {s: round(float(x), 3) for s, x in zip(SIG, b[1:])}
    print('  weights (per 1 sd, + = over):', out['logit_weights'])
    # the price that survives: Kalshi only
    if D.ko.notna().any():
        thr = .56; side = np.where(has & (pred >= thr), 1, np.where(has & (pred <= 1 - thr), -1, 0)); km = np.where(side == 1, D.ko.values, np.where(side == -1, D.ku.values, np.nan)); b2 = (side != 0) & ~np.isnan(km)
        win = (side[b2] == 1) == (over[b2] == 1); u = np.where(win, km[b2] - 1, -1.0).sum(); out['kalshi_only'] = dict(thr=thr, n=int(b2.sum()), w=int(win.sum()), hit=round(float(win.mean()), 4) if b2.any() else None, units=round(float(u), 1))
        print('  the same blend at P ≥ .56, Kalshi prices only:', out['kalshi_only'])
    # by market for the blend at .56
    side = np.where(has & (pred >= .56), 1, np.where(has & (pred <= .44), -1, 0)); out['logit_by_market'] = {m: score(side, (D.market == m).values) for m in sorted(D.market.unique())}
    print('  by market at .56:', {m: (v['n'], v['hit'], v['units']) for m, v in out['logit_by_market'].items()})
    out['logit_by_side'] = dict(over=score(np.where(side == 1, 1, 0)), under=score(np.where(side == -1, -1, 0))); print('  by side:', {k: (v['n'], v['hit'], v['units']) for k, v in out['logit_by_side'].items()})
    # ---- the rule the test supports: his last-10 over-rate and the defense (season) point the same way; tier A adds the projection
    ix = {s_: j for j, s_ in enumerate(SIG)}
    def rule(sub):
        c = [ix[x] for x in sub]; v = V[:, c]; return np.where((v == 1).all(axis=1), 1, np.where((v == -1).all(axis=1), -1, 0))
    RULES = {'B': ['l10', 'dvp'], 'A': ['projgap', 'l10', 'dvp']}
    out['rules'] = {}
    print('\nthe rule (fixed after seeing all weeks, so its own record is in-sample; the walk-forward line above is the honest estimate):')
    for name, sub in RULES.items():
        side = rule(sub); r = score(side); r['signals'] = sub; r['by_week'] = {int(w): score(side, wk == w) for w in weeks}
        r['over'] = score(np.where(side == 1, 1, 0)); r['under'] = score(np.where(side == -1, -1, 0))
        km = np.where(side == 1, D.ko.values, np.where(side == -1, D.ku.values, np.nan)); b2 = (side != 0) & ~np.isnan(km); win = (side[b2] == 1) == (over[b2] == 1)
        r['kalshi'] = dict(n=int(b2.sum()), w=int(win.sum()), hit=round(float(win.mean()), 4) if b2.any() else None, units=round(float(np.where(win, km[b2] - 1, -1.0).sum()), 1))
        r['by_market'] = {m: score(side, (D.market == m).values) for m in sorted(D.market.unique()) if score(side, (D.market == m).values)['n']}
        out['rules'][name] = r
        print(f"  tier {name} ({' + '.join(sub)}): {r['w']}-{r['n'] - r['w']} ({r['hit']}) {r['units']:+} units · over {r['over']['w']}-{r['over']['n'] - r['over']['w']} under {r['under']['w']}-{r['under']['n'] - r['under']['w']} · Kalshi prices {r['kalshi']} · by week " + ' '.join(f"{w}:{v['w']}-{v['n'] - v['w']}" for w, v in r['by_week'].items()))
        print('     by market:', {m: f"{v['w']}-{v['n'] - v['w']}" for m, v in r['by_market'].items()})
    # ---- this week's plays from the live lines
    plays = []
    if os.path.exists('data/processed/bet_lines.csv'):
        B = pd.read_csv('data/processed/bet_lines.csv'); cw = int(B.week.iloc[0]) if len(B) else None
        for (p, m), g in B.groupby(['player', 'market']):
            if m not in COLS: continue
            H = byp.get(nk(p))
            if H is None or len(H[(H.season == SE) & (H.week == cw)]): continue          # no history, or his game is already played
            line = float(g.line.mode().iloc[0]); gg = g[g.line == line]; r0 = gg.iloc[0]; opp = str(r0.opp); home = not opp.startswith('@'); d = opp.replace('@', ''); sg = slotg(r0.slot)
            S = signals(H, cw, m, line, d, sg, r0.team, home, gg.p_over_model.mean(), gg.p_over.mean(), gg.proj.mean())
            vote = {s_: (0 if (S[s_] != S[s_] or (abs(S[s_]) <= TH[s_] and s_ != 'home')) else int(np.sign(S[s_]))) for s_ in SIG}
            tier = None
            for name in ('A', 'B'):
                vs = [vote[x] for x in RULES[name]]
                if vs[0] != 0 and all(v == vs[0] for v in vs): tier = name; side = vs[0]; break
            if not tier: continue
            op = [(dec(x), b) for x, b in zip(gg.over_price, gg.book) if dec(x)]; up = [(dec(x), b) for x, b in zip(gg.under_price, gg.book) if dec(x)]; best = max(op if side == 1 else up, default=(None, None))
            am = lambda dd: None if not dd else int(round((dd - 1) * 100)) if dd >= 2 else int(round(-100 / (dd - 1)))
            q50 = gg.q50.mean() if 'q50' in gg else np.nan
            plays.append(dict(tier=tier, player=p, team=r0.team, opp=opp, slot=str(r0.slot), market=m, line=line, side='OVER' if side == 1 else 'UNDER', l10k=S['l10k'], l10n=S['l10n'],
                              dvp=None if S['dvp'] != S['dvp'] else round(float(S['dvp']), 3), dvp3=None if S['dvp3'] != S['dvp3'] else round(float(S['dvp3']), 3), allowed=None if S['dvp_allowed'] is None else round(S['dvp_allowed'], 1), league=None if S['dvp_lg'] is None else round(S['dvp_lg'], 1),
                              proj=None if q50 != q50 else round(float(q50), 1), dvp3_agrees=int(vote['dvp3'] == side), model_agrees=int(vote['mdl'] == side), price=am(best[0]), book=best[1], books=int(gg.book.nunique())))
        plays.sort(key=lambda x: (x['tier'], -x['dvp3_agrees'], -abs(x['l10k'] / max(1, x['l10n']) - .5)))
        out['current'] = dict(week=cw, plays=plays)
        print(f"\nweek {cw} plays still to be played: {len(plays)} (tier A {sum(1 for x in plays if x['tier'] == 'A')}, tier B {sum(1 for x in plays if x['tier'] == 'B')})")
        for x in plays[:40]: print(f"  {x['tier']} {x['player']:22} {x['team']:3} {x['opp']:5} {x['market']:11} {x['side']:5} {x['line']:6} · L10 {x['l10k']}/{x['l10n']} over · def allows {x['allowed']} vs lg {x['league']} · proj {x['proj']} · dvp3 {'✓' if x['dvp3_agrees'] else '·'} · {x['price']} {x['book']}")
    json.dump(out, open('data/processed/mix_backtest.json', 'w'), default=lambda o: int(o) if isinstance(o, np.integer) else float(o) if isinstance(o, np.floating) else list(o))
    D.assign(pred=pred).to_csv('data/processed/mix_backtest_rows.csv', index=False)

if __name__ == '__main__':
    main()
