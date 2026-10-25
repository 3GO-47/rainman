"""META backtest — does the matchup score predict production, and which weights/transforms predict it best?
-> data/processed/meta_backtest.json (the dashboard reads `weights` + `cfg` from it; everything else is the audit trail)

One row per starter-game (slots QB1 RB1 RB2 WR1 WR2 WR3 TE1), 2025 wk 2+ and 2026 wk 2+, with a baseline: his PPR average
before that game (this season's prior games 2x, last 8 of the prior season 1x; >= 3 weighted games). Outcome = actual PPR / baseline.
Every signal is computed exactly the way the META tab computes it, from data available before kickoff:
  psi   Ψ: mean of the opponent's DvP ranks across his slot's stat group (prior season 1x + this season to date 2x)  -> (NT-rank)/(NT-1)
  td    the opponent's rank allowing TDs to his slot (QB: rushing TD, the tab's default)                            -> (NT-rank)/(NT-1)
  sch   scheme family x slot index (what that family concedes vs league), no injury lift (not reconstructible)      -> percentile in the week
  h2h   his PPR in prior meetings with this opponent minus his baseline, x min(n,3)/3                                -> percentile in the week
  atd   the anytime-TD model's walk-forward probability (td_picks_wf.csv)                                           -> percentile within his position
  env   his team's implied points from the closing spread/total (game_lines.csv)                                    -> percentile in the week
  form  opportunities per game over his last two games vs his season rate (rush att + targets; QB: pass att + rush att) -> percentile within position
META = 50 + (100 * weighted mean - 50) * (.6 + .4 * coverage) * (.75 + .25 * agreement) [v41]; variants switch the shrink terms off,
bend the components toward the extremes (gamma), or drop a signal (ablation). Weights are learned WALK-FORWARD: for every test
week the weights come only from rows before it, so the out-of-sample numbers are honest. Scored by Spearman rho with the ratio,
the lift (mean ratio, top third minus bottom third) and the top decile's ratio / share over baseline. Nothing hand-entered.
Usage: python3 scripts/build_meta_backtest.py [--quick]
"""
import os, json, glob, sys, math
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'data/processed/'
QUICK = '--quick' in sys.argv
SLOTS = ['QB1', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE1']
GROUP = {'QB1': ['QB PY', 'QB RY', 'QB P+R', 'P TD', 'QB TD'], 'RB1': ['RB1 RY', 'RB1 Recep', 'RB1 RecY', 'RB R+R', 'RB1 TD'],
         'RB2': ['RB2+ RY', 'RB2 Recep', 'RB2 RecY', 'RB R+R', 'RB2 TD'], 'WR1': ['WR1 Recep', 'WR1 RecY', 'WR1 TD'], 'WR2': ['WR2 Recep', 'WR2 RecY', 'WR2 TD'],
         'WR3': ['WR3 Recep', 'WR3 RecY', 'WR3 TD'], 'TE1': ['TE1 Recep', 'TE1 RecY', 'TE1 TD']}
TDCOL = {'QB1': 'QB TD', 'RB1': 'RB1 TD', 'RB2': 'RB2 TD', 'WR1': 'WR1 TD', 'WR2': 'WR2 TD', 'WR3': 'WR3 TD', 'TE1': 'TE1 TD'}
SLOT_GRP = {'QB1': 'QB', 'RB1': 'RB1', 'RB2': 'RB2', 'WR1': 'WR1', 'WR2': 'WR2', 'WR3': 'WR3', 'TE1': 'TE1'}
POS = {'QB1': 'QB', 'RB1': 'RB', 'RB2': 'RB', 'WR1': 'WR', 'WR2': 'WR', 'WR3': 'WR', 'TE1': 'TE'}
SIGS = ['psi', 'td', 'sch', 'h2h', 'atd', 'env', 'form']
W_V40 = {'psi': .30, 'td': .25, 'sch': .15, 'h2h': .15, 'atd': .15}
NT = 32

def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = ~np.isnan(x) & ~np.isnan(y)
    if m.sum() < 8: return None
    rx, ry = pd.Series(x[m]).rank().values, pd.Series(y[m]).rank().values
    c = np.corrcoef(rx, ry)[0, 1]
    return None if np.isnan(c) else float(c)

def pct_within(s, by):
    """mid-rank percentile within a pool (the tab's pct()): share below + half the ties, 0..1"""
    return s.groupby(by).rank(pct=True, method='average') - 0.5 / s.groupby(by).transform('count')

# ---------------------------------------------------------------- rows
def build_rows():
    logs = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
    logs = logs.sort_values(['season', 'week']).reset_index(drop=True)
    for c in ['rush_att', 'targets', 'pass_att', 'fantasy_pts_ppr', 'rush_td', 'rec_td']: logs[c] = pd.to_numeric(logs[c], errors='coerce').fillna(0)
    logs['opps'] = np.where(logs.slot == 'QB1', logs.pass_att + logs.rush_att, logs.rush_att + logs.targets)
    wk = pd.read_csv(P + 'dvp_weekly.csv')
    stat_cols = [c for c in wk.columns if c not in ('defense', 'season', 'week', 'opponent')]
    tags = pd.read_csv(P + 'scheme_tags.csv'); tags = tags[tags.side == 'DEF']
    eff = pd.read_csv(P + 'scheme_slot_effects.csv')
    fam = {(int(r.season), r.team): r.primary_tag for r in tags.itertuples()}
    eidx = {(r.family, r.grp): float(r.index) for r in eff.itertuples()}
    gl = pd.read_csv(P + 'game_lines.csv')
    imp = {}
    for r in gl.itertuples():
        if r.total_line != r.total_line: continue
        sp = r.spread_line if r.spread_line == r.spread_line else 0.0
        imp[(int(r.season), int(r.week), r.home_team)] = r.total_line / 2 + sp / 2
        imp[(int(r.season), int(r.week), r.away_team)] = r.total_line / 2 - sp / 2
    atd = {}
    if os.path.exists(P + 'td_picks_wf.csv'):
        for r in pd.read_csv(P + 'td_picks_wf.csv').itertuples(): atd[(int(r.season), int(r.week), r.player)] = float(r.p)
    def dvp_ranks(season, week):
        prev = wk[wk.season == season - 1]; cur = wk[(wk.season == season) & (wk.week < week)]
        parts = []
        if len(prev): parts.append(prev.assign(w=1.0))
        if len(cur): parts.append(cur.assign(w=2.0))
        if not parts: return None
        d = pd.concat(parts)
        allowed = d.groupby('defense')[stat_cols].apply(lambda x: x.mul(d.loc[x.index, 'w'], axis=0).sum() / d.loc[x.index, 'w'].sum())
        return allowed.rank(ascending=False, method='average')
    by_player = {p: g for p, g in logs.groupby('player')}
    seasons = sorted(logs.season.unique()); out = []
    for season in seasons[1:]:
        for w in sorted(logs[logs.season == season].week.unique()):
            if w < 2: continue
            ranks = dvp_ranks(season, w)
            if ranks is None: continue
            cur = logs[(logs.season == season) & (logs.week == w) & logs.slot.isin(SLOTS)]
            for r in cur.itertuples():
                hist = by_player[r.player]
                pc = hist[(hist.season == season) & (hist.week < w)]
                pp = hist[hist.season == season - 1].tail(8)
                wsum = 2 * len(pc) + len(pp)
                if wsum < 3: continue
                base = (2 * pc.fantasy_pts_ppr.sum() + pp.fantasy_pts_ppr.sum()) / wsum
                if base < 4: continue   # a sub-4-point baseline makes the ratio noise
                opp = r.opponent
                if opp not in ranks.index: continue
                psi = float(np.mean([ranks.loc[opp, c] for c in GROUP[r.slot] if c in ranks.columns]))
                tdr = float(ranks.loc[opp, TDCOL[r.slot]]) if TDCOL[r.slot] in ranks.columns else np.nan
                sch = eidx.get((fam.get((season, opp)), SLOT_GRP[r.slot]))
                prior = hist[(hist.season < season) | ((hist.season == season) & (hist.week < w))]
                vs = prior[prior.opponent == opp]
                h2h = (vs.fantasy_pts_ppr.mean() - base) * min(len(vs), 3) / 3 if len(vs) else np.nan
                form = np.nan
                if len(pc) >= 2 and pc.opps.mean() > 0: form = pc.opps.tail(2).mean() / pc.opps.mean() - 1
                out.append({'season': season, 'week': w, 'player': r.player, 'team': r.team, 'opp': opp, 'slot': r.slot, 'pos': POS[r.slot],
                            'base': base, 'actual': float(r.fantasy_pts_ppr), 'ratio': float(r.fantasy_pts_ppr) / base,
                            'scored': int((r.rush_td + r.rec_td) > 0),
                            'psi': psi, 'td': tdr, 'sch': (sch - 100) if sch is not None else np.nan, 'h2h': h2h,
                            'atd': atd.get((season, w, r.player), np.nan), 'env': imp.get((season, w, r.team), np.nan), 'form': form})
    df = pd.DataFrame(out)
    df['wkkey'] = df.season * 100 + df.week
    df['poskey'] = df.wkkey.astype(str) + df.pos
    # components, 0..1, 1 = soft, exactly as the tab
    df['c_psi'] = ((NT - df.psi) / (NT - 1)).clip(0, 1)
    df['c_td'] = ((NT - df.td) / (NT - 1)).clip(0, 1)
    df['c_sch'] = pct_within(df.sch, df.wkkey)
    df['c_h2h'] = pct_within(df.h2h, df.wkkey)
    df['c_env'] = pct_within(df.env, df.wkkey)
    df['c_atd'] = pct_within(df.atd, df.poskey)
    df['c_form'] = pct_within(df.form, df.poskey)
    return df

# ---------------------------------------------------------------- scoring
def meta_score(df, W, cfg):
    """vectorised META for weights W (dict) and cfg {gamma, cov, agree, pct_rank}"""
    gamma = cfg.get('gamma', 1.0)
    C = {}
    for k in SIGS:
        if k not in W or W[k] <= 0: continue
        c = df['c_' + k].values.astype(float)
        if cfg.get('pct_rank') and k in ('psi', 'td'):   # percentile instead of the linear rank map
            c = df['p_' + k].values.astype(float)
        if gamma != 1.0:
            d = c - 0.5; c = 0.5 + np.sign(d) * (np.abs(2 * d) ** gamma) / 2
        C[k] = c
    Wt = sum(W[k] for k in C)
    s = np.zeros(len(df)); w = np.zeros(len(df)); n = np.zeros(len(df)); soft = np.zeros(len(df)); hard = np.zeros(len(df))
    for k, c in C.items():
        m = ~np.isnan(c)
        s[m] += W[k] * c[m]; w[m] += W[k]; n[m] += 1; soft[m] += (c[m] >= .65); hard[m] += (c[m] <= .35)
    cov = np.where(Wt > 0, w / Wt, 0)
    agree = np.where(n > 0, 1 - np.minimum(soft, hard) / np.maximum(n, 1), 1)
    base = np.where(w > 0, 100 * s / np.maximum(w, 1e-9), 50)
    f = np.ones(len(df))
    if cfg.get('cov', True): f = f * (.6 + .4 * cov)
    if cfg.get('agree', True): f = f * (.75 + .25 * agree)
    meta = 50 + (base - 50) * f
    meta[w == 0] = np.nan
    return meta, cov

def metrics(meta, df, label=''):
    m = ~np.isnan(meta); y = df.ratio.values
    if m.sum() < 50: return None
    mm, yy = meta[m], y[m]
    q1, q2 = np.quantile(mm, [1 / 3, 2 / 3]); d9 = np.quantile(mm, .9); d1 = np.quantile(mm, .1)
    top, bot = yy[mm >= q2], yy[mm <= q1]
    return {'n': int(m.sum()), 'rho': round(spearman(mm, yy), 4), 'lift': round(float(top.mean() - bot.mean()), 3),
            'top3': round(float(top.mean()), 3), 'bot3': round(float(bot.mean()), 3), 'over_top3': round(float((top > 1).mean()), 3), 'over_bot3': round(float((bot > 1).mean()), 3),
            'dec_top': round(float(yy[mm >= d9].mean()), 3), 'dec_bot': round(float(yy[mm <= d1].mean()), 3), 'over_dec_top': round(float((yy[mm >= d9] > 1).mean()), 3)}

# ---------------------------------------------------------------- fitting (walk-forward)
def fit_nnls(df, keys, cfg):
    """non-negative least squares of the target on (c_k - .5), missing -> 0 (neutral); returns normalised weights.
    cfg['target']: 'ratio' (actual/base - 1) or 'log' (log ratio, clipped to +-1.5 so one 8x game cannot set the weights);
    cfg['ridge']: pull toward equal weights (lambda x n), the stabiliser when two signals overlap (TD inside Ψ)."""
    X = np.column_stack([np.nan_to_num(df['c_' + k].values - .5, nan=0.0) for k in keys])
    y = np.clip(np.log(np.maximum(df.ratio.values, 1e-3)), -1.5, 1.5) if cfg.get('target') == 'log' else df.ratio.values - 1
    m = ~np.isnan(y); X, y = X[m], y[m]
    lam = cfg.get('ridge', 0.0) * len(y); eqw = np.full(len(keys), 1.0 / len(keys)) * (np.abs(y).mean() * 2)
    w = np.full(len(keys), 1.0 / len(keys)); XtX = X.T @ X + lam * np.eye(len(keys)); Xty = X.T @ y + lam * eqw
    L = np.linalg.eigvalsh(XtX).max() or 1
    for _ in range(3000):
        w = np.maximum(0, w - (XtX @ w - Xty) / L)
    if w.sum() <= 0: w = np.ones(len(keys))
    return {k: float(v / w.sum()) for k, v in zip(keys, w)}

def fit_rho(df, keys, cfg, start=None):
    """coordinate ascent on Spearman rho over the weight simplex (grid per signal, 3 passes)"""
    grid = [0, .25, .5, .75, 1, 1.5, 2, 3]
    w = dict(start) if start else {k: 1.0 for k in keys}
    y = df.ratio.values
    def score(wd):
        if sum(wd.values()) <= 0: return -9
        m, _ = meta_score(df, wd, cfg); r = spearman(m, y); return -9 if r is None else r
    best = score(w)
    for _ in range(2 if QUICK else 3):
        for k in keys:
            for g in grid:
                t = dict(w); t[k] = g
                sc = score(t)
                if sc > best + 1e-6: best, w = sc, t
    tot = sum(w.values()) or 1
    return {k: float(v / tot) for k, v in w.items()}

def walk_forward(df, keys, cfg, fitter, min_train=1500, per_pos=False):
    """weights learned only from rows before each test week; returns the pooled out-of-sample META and the last fitted weights"""
    weeks = sorted(df.wkkey.unique()); meta = np.full(len(df), np.nan); last = None; fits = {}
    for wkk in weeks:
        tr = df[df.wkkey < wkk]; te_idx = np.where(df.wkkey.values == wkk)[0]
        if len(tr) < min_train: continue
        if per_pos:
            for pos in ['QB', 'RB', 'WR', 'TE']:
                trp = tr[tr.pos == pos]; tep = te_idx[df.pos.values[te_idx] == pos]
                if len(trp) < 300 or not len(tep): continue
                w = fitter(trp, keys, cfg); fits[pos] = w
                meta[tep], _ = meta_score(df.iloc[tep], w, cfg)
            last = fits
        else:
            w = fitter(tr, keys, cfg); last = w
            meta[te_idx], _ = meta_score(df.iloc[te_idx], w, cfg)
    return meta, last

# ---------------------------------------------------------------- main
def main():
    df = build_rows()
    df['p_psi'] = pct_within(-df.psi, df.wkkey); df['p_td'] = pct_within(-df.td, df.wkkey)
    print(f'rows {len(df)} · seasons {df.groupby("season").week.agg(["min","max","count"]).to_dict("index")}')
    cov = {k: round(float(df[k].notna().mean()), 3) for k in SIGS}
    print('coverage', cov)
    # single-signal skill (same scale as the tab's components)
    single = {}
    for k in SIGS:
        c = df['c_' + k].values.astype(float)
        single[k] = {'rho': round(spearman(c, df.ratio.values) or 0, 4), 'n': int((~np.isnan(c)).sum()),
                     'lift': round(float(df.ratio[c >= np.nanquantile(c, 2/3)].mean() - df.ratio[c <= np.nanquantile(c, 1/3)].mean()), 3),
                     'rho_td': round(spearman(c, df.scored.values) or 0, 4)}
    print('single-signal rho:', {k: v['rho'] for k, v in single.items()})
    base_cfg = {'gamma': 1.0, 'cov': True, 'agree': True}
    sig = json.load(open(P + 'signals.json')) if os.path.exists(P + 'signals.json') else {}
    o = sig.get('overall', {})
    L = lambda k: max(.04, min(.30, float(o[k]['lift']))) if k in o else None
    w41 = {'psi': L('psi'), 'td': L('dvp'), 'sch': L('scheme'), 'env': L('env'), 'form': L('role'), 'h2h': .06, 'atd': .12}
    w41 = {k: v for k, v in w41.items() if v is not None}; t = sum(w41.values()); w41 = {k: v / t for k, v in w41.items()}
    eq = {k: 1 / len(SIGS) for k in SIGS}
    variants = []
    def add(name, meta, W=None, cfg=None, note=''):
        m = metrics(meta, df)
        if m: variants.append(dict(name=name, note=note, weights={k: round(v, 3) for k, v in W.items()} if isinstance(W, dict) and all(not isinstance(v, dict) for v in W.values()) else W, cfg=cfg, **m))
    # fixed-weight formulas (no fitting -> every row is out of sample)
    add('v40 hand weights (Ψ TD SCH H2H ATD)', meta_score(df, W_V40, base_cfg)[0], W_V40, base_cfg, 'the tab before v41')
    add('v41 lift weights (+ENV +FORM)', meta_score(df, w41, base_cfg)[0], w41, base_cfg, 'weights from signals.json lift; ENV there was EPA-based, here it is the implied total')
    add('equal weights, 7 signals', meta_score(df, eq, base_cfg)[0], eq, base_cfg)
    add('equal · no shrink terms', meta_score(df, eq, {'gamma': 1, 'cov': False, 'agree': False})[0], eq, {'gamma': 1, 'cov': False, 'agree': False})
    # learned weights, walk-forward
    CFGS = [('base', base_cfg), ('no agree', {'gamma': 1, 'cov': True, 'agree': False}), ('no cov', {'gamma': 1, 'cov': False, 'agree': True}),
            ('gamma 1.5', {'gamma': 1.5, 'cov': True, 'agree': True}), ('gamma 2', {'gamma': 2.0, 'cov': True, 'agree': True}),
            ('pct ranks', {'gamma': 1, 'cov': True, 'agree': True, 'pct_rank': True}),
            ('log target', {'gamma': 1, 'cov': True, 'agree': True, 'target': 'log'}), ('log · gamma 1.5', {'gamma': 1.5, 'cov': True, 'agree': True, 'target': 'log'}),
            ('ridge .02', {'gamma': 1, 'cov': True, 'agree': True, 'ridge': .02}), ('ridge .02 · gamma 1.5', {'gamma': 1.5, 'cov': True, 'agree': True, 'ridge': .02}),
            ('log · ridge .02 · gamma 1.5', {'gamma': 1.5, 'cov': True, 'agree': True, 'target': 'log', 'ridge': .02})]
    for fname, fitter in [('NNLS', fit_nnls), ('rho-max', fit_rho)]:
        for cfg_name, cfg in CFGS:
            if fname == 'rho-max' and (QUICK or cfg_name not in ('base', 'gamma 1.5', 'gamma 2')): continue
            if fname == 'rho-max' and (cfg.get('target') or cfg.get('ridge')): continue
            meta, last = walk_forward(df, SIGS, cfg, fitter)
            add(f'{fname} · {cfg_name} · walk-forward', meta, last, cfg, 'weights refit before every test week from earlier weeks only')
    # greedy forward selection (walk-forward rho): which signals earn a place, in order
    g15 = {'gamma': 1.5, 'cov': True, 'agree': True}
    chosen_keys, path = [], []
    while len(chosen_keys) < len(SIGS):
        best_k, best_r = None, -9
        for k in SIGS:
            if k in chosen_keys: continue
            meta, _ = walk_forward(df, chosen_keys + [k], g15, fit_nnls)
            m = metrics(meta, df); r = m['rho'] if m else -9
            if r > best_r: best_k, best_r = k, r
        gain = best_r - (path[-1]['rho'] if path else 0)
        path.append({'add': best_k, 'rho': round(best_r, 4), 'gain': round(gain, 4)})
        if path and len(path) > 1 and gain < 0.002: path[-1]['kept'] = False; break
        path[-1]['kept'] = True; chosen_keys.append(best_k)
    meta, last = walk_forward(df, chosen_keys, g15, fit_nnls)
    add(f'NNLS · gamma 1.5 · forward-selected ({"+".join(chosen_keys)}) · walk-forward', meta, last, dict(g15, keys=chosen_keys), 'greedy: add the signal that lifts out-of-sample rho most, stop under +0.002')
    # nested version: the selection itself is redone inside every training window (no peeking at the test week at all)
    def fit_fwd(tr, keys, cfg):
        sel = []; prev = -9
        while len(sel) < len(keys):
            bk, br = None, -9
            for k in keys:
                if k in sel: continue
                w = fit_nnls(tr, sel + [k], cfg); r = spearman(meta_score(tr, w, cfg)[0], tr.ratio.values) or -9
                if r > br: bk, br = k, r
            if sel and br - prev < 0.002: break
            sel.append(bk); prev = br
        return fit_nnls(tr, sel, cfg)
    # out-of-time check of the selection itself: choose the signal set on 2025 alone, grade it on 2026
    d25 = df[df.season == df.season.min()].reset_index(drop=True); sel = []; prev = 0
    while len(sel) < len(SIGS):
        bk, br = None, -9
        for k in SIGS:
            if k in sel: continue
            m, _ = walk_forward(d25, sel + [k], g15, fit_nnls, min_train=800); mm = metrics(m, d25); r = mm['rho'] if mm else -9
            if r > br: bk, br = k, r
        if sel and br - prev < 0.002: break
        sel.append(bk); prev = br
    holdout = {'selected_on': int(df.season.min()), 'signals': sel, 'tested_on': int(df.season.max())}
    for nm, keys in [('selected', sel), ('all7', SIGS), ('psi_only', ['psi'])]:
        m, _ = walk_forward(df, keys, g15, fit_nnls); mm = metrics(np.where(df.season.values == df.season.max(), m, np.nan), df)
        holdout[nm] = {k: mm[k] for k in ('rho', 'lift', 'dec_top', 'n')} if mm else None
    simple = {k: 1 / 3 for k in ('psi', 'form', 'env')}
    add('Ψ + FORM + ENV equal', meta_score(df, simple, g15)[0], simple, g15, 'the three signals the ablation says carry, equal weights')
    # per-position weights
    meta, last = walk_forward(df, SIGS, base_cfg, fit_nnls, per_pos=True)
    add('NNLS per position · walk-forward', meta, last, base_cfg, 'separate weights for QB / RB / WR / TE')
    # ablation on the best fixed recipe: drop one signal at a time (NNLS walk-forward)
    abl = {}
    for k in SIGS:
        keys = [s for s in SIGS if s != k]
        meta, _ = walk_forward(df, keys, base_cfg, fit_nnls)
        m = metrics(meta, df); abl[k] = {'rho_without': m['rho'], 'lift_without': m['lift']} if m else None
    # pick: best out-of-sample rho among learned variants, ties -> simpler (fewer cfg knobs)
    learned = [v for v in variants if 'walk-forward' in v['name'] and v.get('weights') and all(not isinstance(x, dict) for x in v['weights'].values())]
    # selection: rho differences under one standard error (~1/sqrt(n)) are noise, so among the recipes within 0.005 of the best rho
    # take the one whose top decile produces the most (that is what a best-picks board is for), then the fewer knobs
    se = 1 / math.sqrt(max(len(df) - 3, 1)); top_rho = max(v['rho'] for v in learned)
    cands = [v for v in learned if v['rho'] >= top_rho - 0.005]
    best = max(cands, key=lambda v: (round(v['dec_top'], 2), -len([k for k in v['cfg'] if v['cfg'][k] not in (1, 1.0, True, None, 0)])))
    # final weights for the live tab: refit the chosen recipe on EVERYTHING (the walk-forward number above is its honest grade)
    fitter = fit_nnls if best['name'].startswith('NNLS') else fit_rho
    KEYS = best['cfg'].get('keys', SIGS)
    rho_ppr = round(spearman(meta_score(df, Wfin_dummy, base_cfg)[0], df.actual.values), 4) if False else None
    Wfin = fitter(df, KEYS, best['cfg'])
    rng = np.random.default_rng(7); boots = []
    for _ in range(30):
        idx = rng.integers(0, len(df), len(df)); boots.append(fitter(df.iloc[idx], KEYS, best['cfg']))
    wsd = {k: round(float(np.std([b[k] for b in boots])), 3) for k in KEYS}
    full = metrics(meta_score(df, Wfin, best['cfg'])[0], df)
    # calibration of the chosen recipe (walk-forward scores) by META band
    mbest = [v for v in variants if v['name'] == best['name']][0]
    meta_wf, _ = walk_forward(df, KEYS, best['cfg'], fitter)
    bands = []
    for lo, hi in [(0, 35), (35, 45), (45, 55), (55, 65), (65, 75), (75, 101)]:
        m = (meta_wf >= lo) & (meta_wf < hi)
        if m.sum(): bands.append({'band': f'{lo}-{min(hi,100)}', 'n': int(m.sum()), 'ratio': round(float(df.ratio[m].mean()), 3), 'over': round(float((df.ratio[m] > 1).mean()), 3),
                                  'td': round(float(df.scored[m].mean()), 3), 'ppr': round(float(df.actual[m].mean()), 2)})
    bypos = {}
    for pos in ['QB', 'RB', 'WR', 'TE']:
        m = df.pos.values == pos; mm = metrics(np.where(m, meta_wf, np.nan), df); bypos[pos] = mm
    byseason = {}
    for s in sorted(df.season.unique()):
        m = df.season.values == s; byseason[int(s)] = metrics(np.where(m, meta_wf, np.nan), df)
    extra = {'rho_vs_ppr': round(spearman(meta_wf, df.actual.values) or 0, 4), 'rho_vs_td': round(spearman(meta_wf, df.scored.values) or 0, 4), 'se_rho': round(se, 4)}
    rep = {'built': str(pd.Timestamp.today().date()), 'rows': int(len(df)), 'coverage': cov, 'single': single, 'variants': variants, 'ablation': abl,
           'chosen': best['name'], 'weights': {k: round(v, 3) for k, v in Wfin.items()}, 'weights_sd': wsd, 'forward': path, 'holdout': holdout, 'cfg': {k: v for k, v in best['cfg'].items() if k != 'keys'}, 'in_sample': full, 'chosen_oos': {k: best[k] for k in ('rho','lift','dec_top','dec_bot','over_dec_top','n')}, 'extra': extra,
           'bands': bands, 'by_pos': bypos, 'by_season': byseason,
           'notes': ['outcome = actual PPR / his pre-game baseline (this season 2x, last 8 of prior season 1x)',
                     'walk-forward: weights for a test week come only from earlier weeks; the chosen recipe is then refit on everything for the live tab',
                     'SCH here has no injury lift (not reconstructible for past weeks); the tab adds 0.6 x lift on top',
                     'signals.json ENV (EPA) is season-wide and leaks the future; ENV here is the closing implied total, available before kickoff',
                     'rho differences under one standard error (se_rho) are noise']}
    json.dump(rep, open(P + 'meta_backtest.json', 'w'), indent=1)
    print(f"meta_backtest.json: {len(df)} starter-games · chosen {best['name']} · out-of-sample rho {best['rho']} lift {best['lift']:+.3f} · weights {rep['weights']}")
    for v in sorted(variants, key=lambda v: -v['rho']): print(f"  {v['rho']:+.4f}  lift {v['lift']:+.3f}  dec {v['dec_top']:.3f}/{v['dec_bot']:.3f}  {v['name']}")
    print('  ablation (rho without):', {k: v['rho_without'] for k, v in abl.items() if v})
    print('  bands:', ' · '.join(f"{b['band']}: {b['ratio']} ({b['over']} over, TD {b['td']}, n={b['n']})" for b in bands))

if __name__ == '__main__':
    main()
