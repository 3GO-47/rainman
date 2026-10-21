"""Backtest (F6 TEST > Backtest): every DvP data set and every board signal, scored against what actually happened.

Everything is point in time — a week is predicted only from games played before it — and every input is a table the site
already builds from data/game_logs (dvp_weekly.csv, the game logs, game_lines.csv, scheme tags / effects, the TD Picks
walk-forward predictions, the frozen picks ledger).

1. DATA SETS — which version of "what this defense allows" best predicts what it allows NEXT week:
     two seasons back · last season · this season to date · the site's combined blend (prior seasons, this season x2 once it
     has 4 weeks) · the opponent-adjusted table (build_adjusted_dvp.py rebuilt with only earlier games) · its last 4 games.
   For every stat column (the 33 legacy DvP columns) and every week: Spearman rank correlation between the data set's
   per-game number and what each defense actually allowed that week, across the defenses that played; then averaged.
   0 = no better than drawing names from a hat, 1 = the order was exactly right.
2. SIGNALS — which board number best calls a player's game (QB1 / RB1 / RB2 / WR1-3 / TE1 owners):
     TD allowed to his slot · yards allowed to his slot · Ψ (mean rank across every stat of his slot) · META (the META tab's
     fold, same weights) · H2H (his PPR vs this opponent against his norm, as META) · SCH (the defense's scheme family vs his
     slot) · the anytime-TD model (TD Picks walk-forward) · the implied team total · his own recent PPR · his own TD rate.
   Scored four ways, each inside the week and position so every week counts the same:
     TD AUC        how often a player who scored was ranked above one who didn't (.50 = coin flip)
     PPR rho       Spearman with his fantasy points
     vs-norm rho   Spearman with his points minus his own shrunk recent average — the pure matchup effect
     soft - tough  points vs his norm in the softest third minus the toughest third
   A QB 'touchdown game' = 2+ TD passes or a rushing TD; everyone else = a rushing or receiving TD.
3. STRATEGIES — the graded record of every frozen position (picks_all.csv), its closing-line check (picks_clv.csv) and the
   TD Picks walk-forward record.
Writes data/processed/backtest.json (embedded by build_dashboard.py as J.backtest)."""
import csv, json, os, sys, collections
import numpy as np, pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(ROOT); sys.path.insert(0, 'scripts')
from build_adjusted_dvp import STAT_COLS, GROUP_STATS, HALF_LIFE, GAP, K_DEF, K_OFF
P = 'data/processed/'
NT = 32
CORE = {'QB1': 'QB', 'RB1': 'RB1', 'RB2': 'RB2', 'WR1': 'WR1', 'WR2': 'WR2', 'WR3': 'WR3', 'TE1': 'TE1'}
POSOF = lambda g: 'QB' if g == 'QB' else g[:2]
TDCOL = {'QB': ['P TD', 'QB TD'], 'RB1': ['RB1 TD'], 'RB2': ['RB2 TD'], 'WR1': ['WR1 TD'], 'WR2': ['WR2 TD'], 'WR3': ['WR3 TD'], 'TE1': ['TE1 TD']}
YDCOL = {'QB': ['QB P+R'], 'RB1': ['RB1 RY', 'RB1 RecY'], 'RB2': ['RB2+ RY', 'RB2 RecY'], 'WR1': ['WR1 RecY'], 'WR2': ['WR2 RecY'],
         'WR3': ['WR3 RecY'], 'TE1': ['TE1 RecY']}
META_W = {'psi': .30, 'td': .25, 'sch': .15, 'h2h': .15, 'atd': .15}
TEAMFIX = {'LA': 'LAR', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}
DSTATS = [c for c in STAT_COLS if c != 'D/ST TD']

# ---------------- inputs ----------------
W = pd.read_csv(P + 'dvp_weekly.csv')
S0 = int(W.season.min())
tix = lambda s, w: (s - S0) * (18 + GAP) + w
W['t'] = tix(W.season, W.week)
logs = pd.concat([pd.read_csv(f) for f in sorted(__import__('glob').glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
logs = logs[logs.week <= 18].sort_values(['season', 'week']).reset_index(drop=True)
logs['slot'] = logs.slot.fillna('').astype(str)
CUR = int(logs.season.max())
EVAL = {CUR - 1: list(range(2, 19)), CUR: sorted(w for w in logs[logs.season == CUR].week.unique() if w >= 2)}
LBL = lambda S: {'p2': str(S - 2), 'p1': str(S - 1), 'cur': str(S), 'comb': 'combined', 'adj': 'adjusted', 'l4': 'last 4 games'}
ROLE = {'p2': 'two seasons back', 'p1': 'last season', 'cur': 'this season to date', 'comb': 'the site\'s blend',
        'adj': 'opponent-adjusted, recent games count more', 'l4': 'the defense\'s last four games'}

def adjusted(t0):
    D = W[W.t < t0]; out = {}
    for c in STAT_COLS:
        x = D[c].astype(float).values; lm = x.mean()
        g = D.groupby('opponent')[c]; s, n = g.transform('sum').values, g.transform('count').values
        off = (s - x + K_OFF * lm) / (n - 1 + K_OFF); w = 0.5 ** ((t0 - D.t.values) / HALF_LIFE)
        a = pd.DataFrame({'d': D.defense.values, 'wr': w * (x - off), 'w': w}).groupby('d').sum()
        out[c] = lm + a.wr / (a.w + K_DEF)
    return pd.DataFrame(out)

_SC = {}
def sources(S, wk):
    if (S, wk) in _SC: return _SC[(S, wk)]
    cur = W[(W.season == S) & (W.week < wk)]; out = {}
    for k in (2, 1):
        pr = W[W.season == S - k]
        if len(pr): out[f'p{k}'] = pr.groupby('defense')[STAT_COLS].mean()
    if len(cur): out['cur'] = cur.groupby('defense')[STAT_COLS].mean()
    fr = [W[W.season == s].groupby('defense')[STAT_COLS].mean() for s in sorted(W.season.unique()) if s < S]
    if len(cur) and cur.week.nunique() >= 4: fr += [out['cur']] * 2      # compute_dvp.py: this season x2 once it has 4 weeks
    if fr: out['comb'] = sum(fr) / len(fr)
    out['adj'] = adjusted(tix(S, wk))
    if len(cur): out['l4'] = cur.sort_values('week').groupby('defense').tail(4).groupby('defense')[STAT_COLS].mean()
    _SC[(S, wk)] = out
    return out

_DC = {}
def dvpcache(S, wk):
    """per data set and slot group: TD allowed (and its rank), yards allowed, Ψ (minus the mean rank, so higher = softer)."""
    if (S, wk) not in _DC:
        out = {}
        for k, T in sources(S, wk).items():
            R = T.rank(ascending=False); gg = {}
            for g in set(CORE.values()):
                td = T[TDCOL[g]].sum(axis=1)
                gg[g] = dict(tdA=td.to_dict(), tdR=td.rank(ascending=False).to_dict(), ydA=T[YDCOL[g]].sum(axis=1).to_dict(),
                             psi=(-R[GROUP_STATS[g]].mean(axis=1)).to_dict())
            out[k] = gg
        _DC[(S, wk)] = out
    return _DC[(S, wk)]

def conc(a, b):
    """pairs ordered the same way / the opposite way (ties in either skipped): 'called the softer defense right' counts."""
    a, b = np.asarray(a, float), np.asarray(b, float); iu = np.triu_indices(len(a), 1)
    x = np.sign(a[:, None] - a[None, :])[iu] * np.sign(b[:, None] - b[None, :])[iu]
    return int((x > 0).sum()), int((x < 0).sum())

def rho(a, b):
    a, b = pd.Series(np.asarray(a, float)).rank(), pd.Series(np.asarray(b, float)).rank()
    if a.std() == 0 or b.std() == 0 or len(a) < 5: return None
    return float(np.corrcoef(a, b)[0, 1])
def auc(y, p):
    y, p = np.asarray(y, int), pd.Series(np.asarray(p, float)).rank().values
    n1 = y.sum(); n0 = len(y) - n1
    return float((p[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else None
r3 = lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 3)
FAM = lambda c: 'TD' if 'TD' in c else 'Rec' if 'Recep' in c else 'Yds'
GRPC = lambda c: 'QB' if c.startswith(('QB', 'P TD')) else c[:2]

# ---------------- 1. data sets: what a defense allows next week ----------------
DR = []
for S, weeks in EVAL.items():
    for wk in weeks:
        act = W[(W.season == S) & (W.week == wk)].set_index('defense')
        if len(act) < 16: continue
        for k, T in sources(S, wk).items():
            dd = [d for d in act.index if d in T.index]
            for c in DSTATS:
                r = rho(T.loc[dd, c].values, act.loc[dd, c].values)
                if r is not None: DR.append((S, wk, k, c, r) + conc(T.loc[dd, c].values, act.loc[dd, c].values))
DR = pd.DataFrame(DR, columns=['S', 'wk', 'src', 'c', 'r', 'cr', 'dc'])
PR = lambda x: r3(x.cr.sum() / max(1, x.cr.sum() + x.dc.sum()))
DR['fam'] = DR.c.map(FAM); DR['grp'] = DR.c.map(GRPC)
dsets = {}
for S, g in DR.groupby('S'):
    rows = []
    wk_mean = g.groupby(['wk', 'src']).r.mean().unstack()
    wins = wk_mean.idxmax(axis=1).value_counts()
    for k, h in g.groupby('src'):
        rows.append(dict(k=k, lbl=LBL(S)[k], role=ROLE[k], all=r3(h.r.mean()), pr=PR(h), prf={f: PR(x) for f, x in h.groupby('fam')},
                         prg={p: PR(x) for p, x in h.groupby('grp')}, prc={c: PR(x) for c, x in h.groupby('c')},
                         prwf={int(w): {f: PR(y) for f, y in x.groupby('fam')} for w, x in h.groupby('wk')}, prw={int(w): PR(x) for w, x in h.groupby('wk')}, se=r3(h.r.std() / np.sqrt(len(h))), n=len(h),
                         fam={f: r3(x.r.mean()) for f, x in h.groupby('fam')}, grp={p: r3(x.r.mean()) for p, x in h.groupby('grp')},
                         wins=int(wins.get(k, 0)), weeks=int(h.wk.nunique()),
                         wk={int(w): r3(v) for w, v in wk_mean[k].dropna().items()}))
    rows.sort(key=lambda r: -(r['pr'] or -9))
    dsets[str(int(S))] = dict(rows=rows, weeks=[int(w) for w in sorted(g.wk.unique())], cells=len(g))

# ---------------- 2. signals: the player's game ----------------
logs['td'] = logs.rush_td + logs.rec_td
logs['tdg'] = np.where(logs.slot.str.startswith('QB'), ((logs.pass_td >= 2) | (logs.rush_td > 0)).astype(int), (logs.td > 0).astype(int))
hist = collections.defaultdict(list)                       # player_id -> earlier games (season, week, opp, ppr, tdg)
slotmean = {}
for S in EVAL:
    pr = logs[(logs.season < S) & logs.slot.isin(CORE)]
    slotmean[S] = {s: (g.fantasy_pts_ppr.mean(), g.tdg.mean()) for s, g in pr.groupby('slot')}
LN = {}
for r in csv.DictReader(open(P + 'game_lines.csv')):
    if r['spread_line'] in ('', 'nan') or r['total_line'] in ('', 'nan'): continue
    s, w, sp, tot = int(r['season']), int(r['week']), float(r['spread_line']), float(r['total_line'])
    LN[(s, w, TEAMFIX.get(r['home_team'], r['home_team']))] = tot / 2 + sp / 2; LN[(s, w, TEAMFIX.get(r['away_team'], r['away_team']))] = tot / 2 - sp / 2
TAG = {(int(r['season']), r['team']): r['primary_tag'] for r in csv.DictReader(open(P + 'scheme_tags.csv', encoding='utf-8')) if r['side'] == 'DEF'}
EFF = {(r['family'], r['grp']): float(r['index']) for r in csv.DictReader(open(P + 'scheme_slot_effects.csv', encoding='utf-8'))}
WF = {}
if os.path.exists(P + 'td_picks_wf.csv'):
    for r in csv.DictReader(open(P + 'td_picks_wf.csv', encoding='utf-8')): WF[(int(r['season']), int(r['week']), r['player'], r['team'])] = float(r['p'])

SRCS = ['p2', 'p1', 'cur', 'comb', 'adj', 'l4']
rows = []
for i, r in enumerate(logs.itertuples()):
    S, wk = r.season, r.week
    if S in EVAL and wk in EVAL[S] and r.slot in CORE:
        g = CORE[r.slot]; H = hist[r.player_id]
        sm = slotmean[S].get(r.slot, (10.0, .3))
        last = H[-8:]; base = (sum(h[3] for h in last) + 3 * sm[0]) / (len(last) + 3)
        l16 = H[-16:]; tdr = (sum(h[4] for h in l16) + 3 * sm[1]) / (len(l16) + 3)
        vs = [h for h in H if h[2] == r.opponent]
        hb = np.mean([h[3] for h in H]) if H else None; hp = np.mean([h[3] for h in vs]) if vs else None
        hS = (hp - hb) * min(len(vs), 3) / 3 if hp is not None and hb is not None else None
        fam = TAG.get((S, r.opponent)); e = EFF.get((fam, g)) if fam else None
        row = dict(S=S, wk=wk, pos=POSOF(g), grp=g, opp=r.opponent, name=r.player, team=r.team, slot=r.slot, ppr=r.fantasy_pts_ppr, res=r.fantasy_pts_ppr - base, tdg=int(r.tdg),
                   h2h=hS, sch=None if e is None else e - 100, atd=WF.get((S, wk, r.player, r.team)), imp=LN.get((S, wk, r.team)), form=base, tdr=tdr)
        for k, G in dvpcache(S, wk).items():
            x = G[g]
            if r.opponent not in x['tdA']: continue
            for m in ('tdA', 'tdR', 'ydA', 'psi'): row[f'{m}_{k}'] = float(x[m][r.opponent])
        rows.append(row)
    hist[r.player_id].append((S, wk, r.opponent, r.fantasy_pts_ppr, int(r.tdg)))
F = pd.DataFrame(rows)

def mpct(df, col, by):
    return df.groupby(by)[col].rank(pct=True)
# META, per data set, exactly as the META tab folds it (percentiles among the week's slot owners)
for k in SRCS:
    if f'psi_{k}' not in F: continue
    c_psi = ((NT + F[f'psi_{k}']) / (NT - 1)).clip(0, 1)            # psi stored negative: (NT - rank) / (NT - 1)
    c_td = ((NT - F[f'tdR_{k}']) / (NT - 1)).clip(0, 1)
    c_h2h = mpct(F, 'h2h', ['S', 'wk']); c_sch = mpct(F, 'sch', ['S', 'wk']); c_atd = mpct(F, 'atd', ['S', 'wk', 'pos'])
    C = pd.DataFrame({'psi': c_psi, 'td': c_td, 'sch': c_sch, 'h2h': c_h2h, 'atd': c_atd})
    Wt = pd.Series(META_W); num = (C * Wt).sum(axis=1, min_count=1); den = C.notna().mul(Wt).sum(axis=1)
    F[f'meta_{k}'] = np.where(den > 0, 50 + (100 * num / den - 50) * (.6 + .4 * den / Wt.sum()), np.nan)
    F.loc[F[f'psi_{k}'].isna(), f'meta_{k}'] = np.nan

SIGS = [('tdA', 'TD allowed to his slot', 'touchdowns the opponent allows to his slot per game', 1),
        ('ydA', 'Yards allowed to his slot', 'yards the opponent allows to his slot per game (QB: pass + rush; RB: rush + receiving)', 1),
        ('psi', 'Ψ', 'the opponent\'s mean rank across every stat of his slot (the Player Grid number)', 1),
        ('meta', 'META', 'the META tab\'s fold: Ψ .30 · TD .25 · SCH .15 · H2H .15 · anytime-TD model .15', 1),
        ('h2h', 'H2H', 'his own PPR against this opponent before, against his norm (shrunk under 3 meetings)', 0),
        ('sch', 'SCH', 'what the opponent\'s scheme family gives up to his slot vs league (2024-25 charting)', 0),
        ('atd', 'Anytime-TD model', 'TD Picks: the walk-forward model\'s chance he scores (refit on earlier weeks only)', 0),
        ('imp', 'Implied team total', 'the betting market\'s points for his team (closing spread and total)', 0),
        ('form', 'His recent PPR', 'his own average over his last 8 games, shrunk to the slot', 0),
        ('tdr', 'His TD rate', 'how often he has scored over his last 16 games, shrunk to the slot', 0)]

def score(df, col, minn=20):
    """metrics for one signal over df (rows that have it). Each slot group (QB, RB1, RB2, WR1-3, TE1) is scored inside its own
    week, so a soft matchup is compared with other players in the same role that week — not RB1s against RB2s; positions and
    ALL are the n-weighted mean of their slot groups."""
    d = df[df[col].notna()]
    out = dict(n=int(len(d)), cov=r3(len(d) / max(1, len(df))))
    if len(d) < 40: return out
    d = d.assign(q=d.groupby(['S', 'wk', 'grp'])[col].rank(pct=True))
    per = {}
    for g, x in d.groupby('grp'):
        if len(x) < minn: continue
        top, bot = x[x.q > 2 / 3], x[x.q <= 1 / 3]
        per[g] = (len(x), dict(auc=auc(x.tdg, x.q), rr=rho(x.q, x.ppr), rn=rho(x.q, x.res),
                               edge=(top.res.mean() - bot.res.mean()) if len(top) and len(bot) else None,
                               tdt=top.tdg.mean() if len(top) else None, tdb=bot.tdg.mean() if len(bot) else None))
    def fold(keys):
        acc, n = collections.defaultdict(list), 0
        for g in keys:
            if g not in per: continue
            m, ms = per[g]; n += m
            for k, v in ms.items():
                if v is not None and not np.isnan(v): acc[k].append((v, m))
        res = {k: r3(sum(v * w for v, w in L) / sum(w for _, w in L)) for k, L in acc.items()}
        res['n'] = n
        return res
    for p, keys in (('QB', ['QB']), ('RB', ['RB1', 'RB2']), ('WR', ['WR1', 'WR2', 'WR3']), ('TE', ['TE1'])):
        if any(g in per for g in keys): out[p] = fold(keys)
    out.update({k: v for k, v in fold(list(per)).items() if k != 'n'})
    return out

VFMT = dict(tdA=lambda v: f'{v:.2f} TD/g', ydA=lambda v: f'{v:.0f} yd/g', psi=lambda v: f'Ψ {-v:.1f}', meta=lambda v: f'META {v:.0f}',
            h2h=lambda v: f'{v:+.1f} vs norm', sch=lambda v: f'{v:+.0f}%', atd=lambda v: f'{100 * v:.0f}%', imp=lambda v: f'{v:.1f} pts',
            form=lambda v: f'{v:.1f} PPR/g', tdr=lambda v: f'{100 * v:.0f}%')
sigs = {}
for S in EVAL:
    D = F[F.S == S]; sd = {}
    for key, lbl, desc, srcdep in SIGS:
        if srcdep:
            sd[key] = dict(lbl=lbl, desc=desc, src={k: score(D, f'{key}_{k}') for k in SRCS if f'{key}_{k}' in D})
        else:
            sd[key] = dict(lbl=lbl, desc=desc, all=score(D, key))
    # week by week (combined data set for the DvP signals)
    wkly = {}
    for wk, x in D.groupby('wk'):
        wkly[int(wk)] = {key: (lambda s: {'auc': s.get('auc'), 'rn': s.get('rn')})(score(x, f'{key}_comb' if srcdep else key)) for key, _, _, srcdep in SIGS}
    # the proof behind every bar: week by week, and the players each signal rated highest / lowest each week (with what happened)
    hist, ex = {}, {}
    NEX = 5 if S == CUR else 2
    for key, lbl, desc, srcdep in SIGS:
        for var, col in ([(f'{key}@{k}', f'{key}_{k}') for k in ('comb', 'adj')] if srcdep else [(key, key)]):
            if col not in D: continue
            h, e = {}, {}
            for wk, x in D.groupby('wk'):
                m = score(x, col)
                h[int(wk)] = [m.get('n'), m.get('auc'), m.get('tdt'), m.get('tdb'), r3(m.get('edge'))]
                y = x[x[col].notna()]
                if not len(y): continue
                y = y.assign(q=y.groupby('grp')[col].rank(pct=True)).sort_values(['q', col], ascending=False)
                ro = lambda r: [r['name'], r['team'], r['opp'], r['slot'], VFMT[key](r[col]), int(r['tdg']), round(float(r['ppr']), 1), round(float(r['res']), 1)]
                e[int(wk)] = dict(top=[ro(r) for _, r in y.head(NEX).iterrows()], bot=[ro(r) for _, r in y.tail(NEX).iloc[::-1].iterrows()])
            hist[var], ex[var] = h, e
    sigs[str(int(S))] = dict(sig=sd, wk=wkly, hist=hist, ex=ex, n=int(len(D)), weeks=[int(w) for w in sorted(D.wk.unique())], td=r3(D.tdg.mean()))

# ---------------- 3. strategies: the frozen picks, graded ----------------
strat = []
def _win(r):
    """profit on a win, per unit staked: the posted price when the pick has one, the market's price for ML / TD, else -110."""
    try: a = float(r['price'])
    except (KeyError, TypeError, ValueError): a = float('nan')
    if a == a and a != 0: return a / 100 if a > 0 else 100 / -a
    try: m = float(r['market_ref'])
    except (TypeError, ValueError): m = float('nan')
    if r['type'] in ('ML', 'TD') and 0 < m < 1: return 1 / m - 1
    return 100 / 110
if os.path.exists(P + 'picks_all.csv'):
    pk = pd.read_csv(P + 'picks_all.csv')
    if 'price' not in pk: pk['price'] = np.nan
    clv = pd.read_csv(P + 'picks_clv.csv') if os.path.exists(P + 'picks_clv.csv') else None
    pk['dw'] = [_win(r) for _, r in pk.iterrows()]
    pk['u'] = np.where(pk.result == 'W', pk.dw, np.where(pk.result == 'L', -1.0, 0.0))
    pk['be'] = 1 / (1 + pk.dw)
    NAME = {'ML': 'Moneyline picks', 'ATS': 'Against the spread', 'TOTAL': 'Game totals', 'PROP': 'Player props — the card', 'TD': 'Anytime-TD bets',
            'LEAN': 'Player props — every lean (the old way)'}
    if 'bet' not in pk: pk['bet'] = '1'
    isbet = pk.bet.astype(str).isin(['1', '1.0'])
    sets = [(t, g) for t, g in pk[(pk.type != 'DFS') & isbet].groupby('type')] + [('LEAN', pk[pk.type == 'PROP'])]
    for t, g in sets:
        gr = g[g.result.isin(['W', 'L'])]
        if not len(gr): continue
        w = int((gr.result == 'W').sum()); l = int((gr.result == 'L').sum())
        row = dict(k=t, lbl=NAME.get(t, t), w=w, l=l, p=int((g.result == 'P').sum()), hit=r3(w / (w + l)), be=r3(gr.be.mean()),
                   units=round(float(g.u.sum()), 1), open=int((~g.result.isin(['W', 'L', 'P', 'G'])).sum()), priced=int(pd.to_numeric(g.price, errors='coerce').notna().sum()))
        if clv is not None:
            base = 'PROP' if t == 'LEAN' else t
            c = clv[(clv.type == base) & clv.beat.notna()]
            if t == 'PROP': c = c[c.ref.isin(g.ref)]
            if len(c): row['clv'] = r3(c.beat.astype(str).str.lower().isin(['true', '1', '1.0']).mean()); row['clvn'] = int(len(c))
        row['wk'] = {int(k): [int((x.result == 'W').sum()), int((x.result == 'L').sum()), round(float(x.u.sum()), 1), int(len(x))] for k, x in g.groupby('week')}   # v32: per week W, L, units, frozen
        strat.append(row)
    # the card, built step by step from every lean: what each rule removed and what it did to the money
    pp = pk[pk.type == 'PROP'].copy(); pp['why'] = pp.get('why', '').fillna('') if 'why' in pp else ''
    steps = [('every prop the books posted (the old way)', []), ('the model\'s edge is 6% or more', ['edge under 6%']),
             ('the price is between −200 and +200', ['edge under 6%', 'price outside -200..+200']),
             ('the model itself gives the side 50%+', ['edge under 6%', 'price outside -200..+200', 'model under 50%']),
             ('one bet per player — his biggest edge', ['edge under 6%', 'price outside -200..+200', 'model under 50%', 'not his best edge']),
             ('at most 3 per game — the card', ['edge under 6%', 'price outside -200..+200', 'model under 50%', 'not his best edge', 'game already has 3'])]
    funnel = []
    for lbl, drop in steps:
        y = pp[~pp.why.isin(drop)]; g2 = y[y.result.isin(['W', 'L'])]; w = int((g2.result == 'W').sum())
        funnel.append(dict(lbl=lbl, n=int(len(y)), w=w, l=int(len(g2) - w), hit=r3(w / len(g2)) if len(g2) else None, units=round(float(g2.u.sum()), 1),
                           wk={int(k): round(float(v), 1) for k, v in g2.groupby('week').u.sum().items()}, wn={int(k): int(v) for k, v in y.groupby('week').size().items()}))
    CARD = dict(rules=['the model\'s edge at the posted price is 6% or more', 'the price is between −200 and +200 — no long-shot strikes, no heavy juice',
                       'the model\'s own chance for that side is 50% or more', 'one bet per player per game — his biggest edge',
                       'at most 3 bets per game — the biggest edges'], funnel=funnel,
                insample=[4, 5, 6],
                note='rules picked on Oct 19 from weeks 4–6, so those weeks are in-sample — week 7 on is the real test')
tdp = {}
if os.path.exists(P + 'td_picks.json'):
    bt = json.load(open(P + 'td_picks.json')).get('bt', {})
    tdp = dict(auc=bt.get('auc'), base=bt.get('auc_base'), top10=bt.get('top10'), lock=(bt.get('tiers') or {}).get('lock'), weeks=len(bt.get('weeks') or []))

# ---------------- plain-language takeaways ----------------
def f2(v): return '—' if v is None else f'{v:+.2f}'.replace('+0.', '+.').replace('-0.', '−.')
ins = []
for S in (str(CUR), str(CUR - 1)):
    if S not in dsets: continue
    R = dsets[S]['rows']; b = R[0]; lo = R[-1]
    tdbest = max(R, key=lambda r: r['fam'].get('TD') or -9)
    ins.append(dict(k='ds', s=S, t=f"{S}: the best guide to what a defense allows next week was <b>{b['lbl']}</b> ({b['role']}) — rank correlation {f2(b['all'])}, "
               f"best in {b['wins']} of {b['weeks']} weeks; the weakest was {lo['lbl']} ({f2(lo['all'])}). Touchdowns are the noisiest: the best data set for TDs "
               f"({tdbest['lbl']}) reached only {f2(tdbest['fam'].get('TD'))}."))
for S in (str(CUR), str(CUR - 1)):
    if S not in sigs: continue
    sd = sigs[S]['sig']
    def val(key, m):
        v = sd[key]; s = v['src'].get('comb') if 'src' in v else v['all']
        return (s or {}).get(m)
    cand = [(key, sd[key]['lbl']) for key, *_ in SIGS]
    ta = sorted([(val(k, 'auc'), l) for k, l in cand if val(k, 'auc') is not None], reverse=True)
    rn = sorted([(val(k, 'rn'), l) for k, l in cand if val(k, 'rn') is not None and k not in ('form', 'tdr')], reverse=True)
    a3 = lambda v: '—' if v is None else f'{v:.3f}'
    if ta: ins.append(dict(k='td', s=S, t=f"{S}, picking touchdowns: <b>{ta[0][1]}</b> ranked scorers best (AUC {ta[0][0]:.3f}; .500 = coin flip), then {ta[1][1]} ({ta[1][0]:.3f}). "
                      f"TD allowed to his slot: {a3(val('tdA', 'auc'))} · Ψ: {a3(val('psi', 'auc'))} · META: {a3(val('meta', 'auc'))} · H2H: {a3(val('h2h', 'auc'))}."))
    if rn: ins.append(dict(k='mu', s=S, t=f"{S}, the matchup itself (did a player beat his own average?): <b>{rn[0][1]}</b> was the best read (ρ {f2(rn[0][0])}); "
                      f"soft third vs tough third by Ψ: {f2(val('psi', 'edge'))} PPR, by TD allowed: {f2(val('tdA', 'edge'))}, by SCH: {f2(val('sch', 'edge'))}, by H2H: {f2(val('h2h', 'edge'))}."))
for S in (str(CUR), str(CUR - 1)):
    if S not in sigs: continue
    sd = sigs[S]['sig']; g = lambda k, src, m: ((sd[k].get('src') or {}).get(src) or {}).get(m)
    cmp = [(sd[k]['lbl'], g(k, 'adj', 'rn'), g(k, 'comb', 'rn')) for k in ('tdA', 'ydA', 'psi', 'meta')]
    wn = sum(1 for _, a_, c_ in cmp if a_ is not None and c_ is not None and a_ > c_)
    ins.append(dict(k='src', s=S, t=f"{S}: read through the <b>adjusted</b> table instead of the combined blend (the site's default), the matchup signals got better at calling "
                    f"who beat his own average in {wn} of 4 cases — Ψ {f2(g('psi', 'adj', 'rn'))} vs {f2(g('psi', 'comb', 'rn'))}, TD allowed {f2(g('tdA', 'adj', 'rn'))} vs {f2(g('tdA', 'comb', 'rn'))}."))
    ma, pa, ta_ = g('meta', 'comb', 'auc'), g('psi', 'comb', 'auc'), g('tdA', 'comb', 'auc')
    if ma is not None and pa is not None and ta_ is not None:
        ins.append(dict(k='meta', s=S, t=f"{S}: META {'beat' if ma > max(pa, ta_) else 'did not beat'} its own parts at picking scorers (AUC {ma:.3f} vs Ψ {pa:.3f}, TD allowed {ta_:.3f}) — "
                        f"most of its edge comes from the anytime-TD model folded inside it ({(sd['atd']['all'] or {}).get('auc') or 0:.3f} on its own)."))
    h = sd['h2h']['all']
    if h.get('auc') is not None:
        ins.append(dict(k='h2h', s=S, t=f"{S}: H2H (how he did against this opponent before) carried <b>no signal</b> — AUC {h['auc']:.3f}, below a coin flip, and ρ {f2(h.get('rn'))} against his norm; "
                        f"only {h['cov']:.0%} of players had a prior meeting." if h['auc'] < .52 else f"{S}: H2H AUC {h['auc']:.3f} on the {h['cov']:.0%} of players with a prior meeting."))
for st in strat:
    if st['w'] + st['l'] >= 10:
        d = st['units']
        ins.append(dict(k='st', s='all', t=f"{st['lbl']}: {st['w']}-{st['l']} ({st['hit']:.1%}) against a break-even of {st['be']:.1%} — "
                        + (f'<b style="color:var(--green)">+{d:.1f} units</b>' if d > 0 else f'<b style="color:var(--red)">{d:.1f} units</b>')
                        + (f" · beat the closing line {st['clv']:.0%} of the time" if st.get('clv') is not None else '') + '.'))

out = dict(card=CARD if 'CARD' in dir() else None, built=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), cur=CUR, eval={str(k): v for k, v in EVAL.items()}, dsets=dsets, sigs=sigs,
           srcs=SRCS, lbl={str(S): LBL(S) for S in EVAL}, role=ROLE, strat=strat, tdp=tdp, ins=ins)
json.dump(out, open(P + 'backtest.json', 'w'), separators=(',', ':'), default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print(f'backtest: data sets {len(DR)} defense-stat-weeks · signals {len(F)} player-games ({", ".join(f"{S}: {sigs[str(S)][chr(110)]}" for S in EVAL)}) · '
      f'strategies {len(strat)} · {os.path.getsize(P + "backtest.json") // 1024} KB')
for i in ins: print('  ·', i['t'].replace('<b>', '').replace('</b>', '')[:220])
