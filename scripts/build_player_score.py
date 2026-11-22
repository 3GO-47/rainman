"""Player SCORE — the three things asked to be visible and weighed, per rostered player this week:

  matchup   how soft this week's opponent is for his slot (composite rank among the defenses, as of now)
  red zone  his share of his team's red-zone targets + carries over his last four games
  last 5    his PPR over his last five games against his season average
  incentive (shown, small untested bump) contract thresholds from Spotrac he can still reach, and how hard he must push

The weights are not declared — they are fitted. Every player-game of 2025-26 with a baseline gets the same three numbers as of
that week (percentiles within his position that week) and two outcomes: he beat his own baseline (PPR >= 15% / 3 pts over the mean
of his previous six) and he scored. A ridge regression of (beat + scored) / 2 on the three percentiles gives the weights (negatives
are set to zero); 2025 fits, 2026 tests, and the test split is printed and embedded. SCORE = his weighted percentile blend, 0-100
within his position this week, plus up to 6 points when a reachable incentive needs him at or above his pace.

Inputs: game logs, dvp_weekly.csv, nflverse pbp (red zone), matchups_current.csv, data/raw/spotrac_incentives_<date>.txt
Output: data/processed/player_score.json
"""
import os, re, json, glob
import numpy as np, pandas as pd
import build_categories as BC          # load(), rz_shares(), dvp_rank_asof(), norm(), SLOTSTAT
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SE = BC.CUR; FEATS = ['matchup', 'rz', 'l5']
NICK = {'cardinals': 'ARI', 'falcons': 'ATL', 'ravens': 'BAL', 'bills': 'BUF', 'panthers': 'CAR', 'bears': 'CHI', 'bengals': 'CIN', 'browns': 'CLE', 'cowboys': 'DAL', 'broncos': 'DEN', 'lions': 'DET',
        'packers': 'GB', 'texans': 'HOU', 'colts': 'IND', 'jaguars': 'JAX', 'chiefs': 'KC', 'raiders': 'LV', 'chargers': 'LAC', 'rams': 'LAR', 'dolphins': 'MIA', 'vikings': 'MIN', 'patriots': 'NE',
        'saints': 'NO', 'giants': 'NYG', 'jets': 'NYJ', 'eagles': 'PHI', 'steelers': 'PIT', '49ers': 'SF', 'seahawks': 'SEA', 'buccaneers': 'TB', 'titans': 'TEN', 'commanders': 'WAS'}
STATL = {'REC': 'receptions', 'REY': 'receiving yards', 'RETD': 'receiving TDs', 'RUY': 'rushing yards', 'RUTD': 'rushing TDs', 'TD': 'touchdowns', 'SCY': 'scrimmage yards', 'PAY': 'passing yards', 'PATD': 'passing TDs', 'CMP': 'completions'}
STATF = {'REC': lambda g: g.rec, 'REY': lambda g: g.rec_yds, 'RETD': lambda g: g.rec_td, 'RUY': lambda g: g.rush_yds, 'RUTD': lambda g: g.rush_td, 'TD': lambda g: g.rush_td + g.rec_td,
         'SCY': lambda g: g.rush_yds + g.rec_yds, 'PAY': lambda g: g.pass_yds, 'PATD': lambda g: g.pass_td, 'CMP': lambda g: g.cmp}
slotk = lambda s: 'QB' if str(s).startswith('QB') else s if s in BC.SLOTSTAT else ('WR4+' if str(s).startswith('WR') else 'RB2' if str(s).startswith('RB') else 'TE2' if str(s).startswith('TE') else '')
posof = lambda s: 'QB' if str(s).startswith('QB') else str(s)[:2]

def pct_in(df, col, by):   # percentile 0..1 within group, NaN stays NaN
    return df.groupby(by)[col].rank(pct=True)

def incentives(L, team_games):
    files = sorted(glob.glob('data/raw/spotrac_incentives_*.txt'))
    if not files: return {}, None
    cur = L[L.season == SE]; out = {}
    for line in open(files[-1], encoding='utf-8'):
        if line.startswith('#') or '|' not in line: continue
        nick, player, pos, spec = line.rstrip('\n').split('|'); team = NICK.get(nick, nick.upper()); k = BC.norm(player); g = cur[cur.n == k]
        gp = len(g); left = max(0, 17 - team_games.get(team, 0)); rows = []
        for item in spec.split(','):
            m = re.match(r'^([A-Z]+):(\d+)=(\d+)(\*?)$', item)
            if not m or m.group(1) not in STATF: continue
            st, th, pay, cond = m.group(1), int(m.group(2)), int(m.group(3)), bool(m.group(4))
            have = float(STATF[st](g).sum()) if gp else 0.0; avg = have / gp if gp else 0.0; need = th - have
            npg = need / left if left else None; ratio = (npg / avg) if (npg is not None and avg > 0) else None
            status = 'reached' if need <= 0 else 'out of reach' if (left == 0 or ratio is None or ratio > 1.6) else 'on pace' if ratio <= 1.0 else 'needs a push'
            rows.append(dict(stat=st, label=STATL[st], th=th, pay=pay, cond=int(cond), have=round(have, 1), need=round(max(0, need), 1), left=left, npg=None if npg is None else round(npg, 1), avg=round(avg, 1), ratio=None if ratio is None else round(ratio, 2), status=status))
        if not rows: continue
        live = [r for r in rows if r['status'] in ('on pace', 'needs a push')]
        # push: money still in play that needs him AT or ABOVE his pace — peaks when the needed rate is 100-130% of his average
        def close(r): x = r['ratio']; return 0 if x is None else max(0.0, 1 - abs(x - 1.15) / 0.55)
        push = min(1.0, sum(close(r) * max(r['pay'], 50) for r in live) / 600.0)
        nxt = sorted(live, key=lambda r: (-close(r) * max(r['pay'], 50)))[:1]
        out[k] = dict(player=player, team=team, pos=pos, games=gp, left=left, rows=rows, push=round(push, 3), next=nxt[0] if nxt else None, live=len(live), money_live=sum(r['pay'] for r in live))
    return out, os.path.basename(files[-1])

def main():
    L, U, D, G, TD = BC.load(); RZ = BC.rz_shares(); RK = BC.dvp_rank_asof(D)
    L = L.sort_values(['n', 'season', 'week']).reset_index(drop=True)
    L['base'] = L.groupby('n').fantasy_pts_ppr.transform(lambda s: s.shift(1).rolling(6, min_periods=3).mean())
    L['hit'] = (L.fantasy_pts_ppr >= np.maximum(1.15 * L.base, L.base + 3)).where(L.base.notna())
    L['rz_g'] = [RZ.get((se, w, t, n), 0.0) for se, w, t, n in zip(L.season, L.week, L.team, L.n)]
    L['rz'] = L.groupby('n').rz_g.transform(lambda s: s.shift(1).rolling(4, min_periods=2).mean())
    L['l5m'] = L.groupby('n').fantasy_pts_ppr.transform(lambda s: s.shift(1).rolling(5, min_periods=3).mean())
    L['seavg'] = L.groupby(['n', 'season']).fantasy_pts_ppr.transform(lambda s: s.shift(1).expanding(min_periods=3).mean())
    L['l5'] = (L.l5m - L.seavg) / np.maximum(L.seavg, 3.0)
    L['sk'] = L.slot.map(slotk); L['p'] = L.slot.map(posof)
    rk = [RK.get((se, w, o, sk)) for se, w, o, sk in zip(L.season, L.week, L.opponent, L.sk)]
    L['matchup'] = [np.nan if r is None else 1 - (r[0] - 1) / max(1, r[1] - 1) for r in rk]      # 1 = the softest defense for his slot
    E = L[L.season.isin(BC.SEASONS) & L.base.notna() & (L.base >= 4) & L.p.isin(['QB', 'RB', 'WR', 'TE'])].copy()
    for f in FEATS: E[f + '_p'] = pct_in(E, f, ['season', 'week', 'p']).fillna(.5)
    E['y'] = (E.hit.astype(float) + (E.td >= 1).astype(float)) / 2
    def fit(df, lam=5.0):
        X = df[[f + '_p' for f in FEATS]].values - .5; y = df.y.values - df.y.mean(); return np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)
    tr, te = E[E.season < SE], E[E.season == SE]
    def evaluate(df, w):
        s = (df[[f + '_p' for f in FEATS]].values - .5) @ w; q = pd.qcut(pd.Series(s).rank(method='first'), 5, labels=False).values
        return dict(n=int(len(df)), top=dict(n=int((q == 4).sum()), beat=round(float(df.hit[q == 4].mean()), 3), td=round(float((df.td[q == 4] >= 1).mean()), 3), ppr_over=round(float((df.fantasy_pts_ppr - df.base)[q == 4].mean()), 2)),
                    bottom=dict(n=int((q == 0).sum()), beat=round(float(df.hit[q == 0].mean()), 3), td=round(float((df.td[q == 0] >= 1).mean()), 3), ppr_over=round(float((df.fantasy_pts_ppr - df.base)[q == 0].mean()), 2)),
                    field=dict(beat=round(float(df.hit.mean()), 3), td=round(float((df.td >= 1).mean()), 3)))
    w_tr = np.clip(fit(tr), 0, None); test = evaluate(te, w_tr) if len(tr) > 500 and w_tr.sum() > 0 else None
    w_all = np.clip(fit(E), 0, None); wn = w_all / w_all.sum() if w_all.sum() > 0 else np.array([1, 0, 0.0])
    single = {}
    for f in FEATS:
        s = E[f + '_p']; hi = E[s >= .8]; lo = E[s <= .2]
        single[f] = dict(top_beat=round(float(hi.hit.mean()), 3), top_td=round(float((hi.td >= 1).mean()), 3), bottom_beat=round(float(lo.hit.mean()), 3), bottom_td=round(float((lo.td >= 1).mean()), 3))
    print('weights (fitted on 2025-26, negatives zeroed):', {f: round(float(x), 3) for f, x in zip(FEATS, wn)}, '| raw coefficients', {f: round(float(x), 4) for f, x in zip(FEATS, fit(E))})
    print('each alone, top fifth vs bottom fifth (beat baseline / scored):', single)
    print('fit on 2025, tested on 2026:', test)
    # ---- this week
    M = pd.read_csv('data/processed/matchups_current.csv'); wk = int(M.week.iloc[0]); cur = L[L.season == SE]
    team_games = cur.groupby('team').week.nunique().to_dict()
    INC, inc_src = incentives(L, team_games)
    PRIM = {'QB': ('pass_yds', 'pass yds'), 'RB': ('rush_yds', 'rush yds'), 'WR': ('rec_yds', 'rec yds'), 'TE': ('rec_yds', 'rec yds')}
    rows = []
    for m in M.itertuples():
        n = BC.norm(m.player); H = L[L.n == n]
        if not len(H) or int(m.injury) == -1: continue
        pos = posof(m.slot)
        if pos not in PRIM: continue
        opp = str(m.opponent).replace('@', ''); bye = opp in ('BYE', 'nan', '')
        Hc = H[H.season == SE]; last5 = H.tail(5); r = None if bye else RK.get((SE, wk, opp, slotk(m.slot)))
        rz4 = float(H.rz_g.tail(4).mean()) if len(H) >= 2 else None; rzse = float(Hc.rz_g.mean()) if len(Hc) else None
        sem = float(Hc.fantasy_pts_ppr.mean()) if len(Hc) >= 3 else None; l5m = float(last5.fantasy_pts_ppr.mean()) if len(last5) >= 3 else None
        pc, pl = PRIM[pos]
        rows.append(dict(player=m.player, n=n, team=m.team, opp=None if bye else opp, slot=m.slot, p=pos, matchup=np.nan if r is None else 1 - (r[0] - 1) / max(1, r[1] - 1), mrank=None if r is None else int(r[0]),
                         rz=np.nan if rz4 is None else rz4, rz_se=rzse, l5=np.nan if (sem is None or l5m is None) else (l5m - sem) / max(sem, 3.0), ppr_l5=l5m, ppr_se=sem,
                         stat=pl, stat_l5=float(last5[pc].mean()) if len(last5) else None, stat_se=float(Hc[pc].mean()) if len(Hc) else None, gp=int(len(Hc))))
    C = pd.DataFrame(rows)
    for f in FEATS: C[f + '_p'] = C.groupby('p')[f].rank(pct=True)
    X = C[[f + '_p' for f in FEATS]].fillna(.5).values; C['raw'] = X @ wn
    C['score'] = (100 * C.groupby('p').raw.rank(pct=True)).round(0)
    C.loc[C.opp.isna(), 'score'] = np.nan
    players = {}
    r3 = lambda v: None if v is None or v != v else round(float(v), 3)
    for c in C.itertuples():
        inc = INC.get(c.n); bump = round(6 * inc['push'], 1) if inc else 0
        sc = None if c.score != c.score else int(min(100, round(c.score + bump)))
        players[c.n] = dict(player=c.player, team=c.team, opp=c.opp, slot=c.slot, pos=c.p, score=sc, base=None if c.score != c.score else int(c.score), bump=bump, mrank=c.mrank, matchup_p=r3(c.matchup_p), rz=r3(c.rz), rz_se=r3(c.rz_se), rz_p=r3(c.rz_p),
                            l5=r3(c.l5), l5_p=r3(c.l5_p), ppr_l5=r3(c.ppr_l5), ppr_se=r3(c.ppr_se), stat=c.stat, stat_l5=r3(c.stat_l5), stat_se=r3(c.stat_se), gp=c.gp, inc=inc)
    for k, inc in INC.items():      # incentive players not on this week's board still get listed
        if k not in players: players[k] = dict(player=inc['player'], team=inc['team'], pos=inc['pos'], score=None, inc=inc)
    out = dict(built=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), week=wk, weights={f: round(float(x), 3) for f, x in zip(FEATS, wn)}, single=single, test=test, n_fit=int(len(E)),
               incentives_source=inc_src, players=players,
               defs=dict(matchup='how soft this week\'s opponent is for his slot (composite rank among the defenses)', rz='his share of his team\'s red-zone targets and carries, last four games',
                         l5='his PPR over his last five games against his season average', inc='Spotrac contract thresholds he can still reach; the bump is a judgment call, not a tested weight'))
    json.dump(out, open('data/processed/player_score.json', 'w'), separators=(',', ':'), default=lambda o: None if (isinstance(o, float) and o != o) else (int(o) if isinstance(o, np.integer) else float(o)))
    live = sorted([v for v in players.values() if v.get('inc') and v['inc']['next']], key=lambda v: -v['inc']['push'])
    print(f"player_score.json: week {wk} · {int(C.score.notna().sum())} scored · {len(INC)} players with incentives ({len(live)} with one still in play)")
    for v in live[:12]:
        x = v['inc']['next']; print(f"  {v['player']:22} {v['team']:3} ${x['pay']}K at {x['th']} {x['label']} · has {x['have']} · needs {x['npg']}/g over {x['left']} (avg {x['avg']}, {x['ratio']}x) · {x['status']}")
    top = C.sort_values('score', ascending=False).head(10); print('top scores:', [(r.player, r.p, int(r.score)) for r in top.itertuples()])

if __name__ == '__main__':
    main()
