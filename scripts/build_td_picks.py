"""TD Picks — anytime-touchdown picks for the coming week, built on the Weeklies study.

Every player-game since 2024 gets the pre-kickoff profile the Weeklies tab tests (scoring form, career rate, share of his team's
touchdowns, touches / carries / targets, snap share, the team's implied total and spread, what the opponent allows to his slot
season-long and over its last three games, a TD against this opponent before, home, his depth-chart slot). A ridge-regularised
logistic model turns that profile into P(he scores a rushing or receiving TD).

Honesty:
  * point in time — every feature uses only games played before the one being predicted;
  * walk-forward backtest — for every week of 2025 and 2026 the model is refit on everything before that week and scored on it,
    so the track record on the page is out of sample;
  * frozen picks — the first time a week is scored its picks are written to data/processed/td_picks_ledger.csv and never
    re-scored; results are filled in from the game logs as games are logged (prices may update until kickoff, p never does).

Writes data/processed/td_picks.json (embedded by build_dashboard.py) and data/processed/td_picks_ledger.csv.
Inputs: data/game_logs/game_logs_*.csv, data/processed/{player_usage, game_lines, schedule_2026, games_2026, depth_charts_*,
arb_board, bet_td}.csv — all already produced by the pipeline."""
import csv, glob, json, os, math, datetime, collections, re, sys
import numpy as np

P = 'data/processed/'
TODAY = datetime.date.today()
SEASON = 2026
BUCKET = {'QB1': 'QB1', 'RB1': 'RB1', 'RB2': 'RB2', 'RB3': 'RB3', 'FB1': 'RB3', 'WR1': 'WR1', 'WR2': 'WR2', 'WR3': 'WR3', 'WR4+': 'WR4', 'WR4': 'WR4',
          'TE1': 'TE1', 'TE2': 'TE2', 'TE3': 'TE2', 'TE4': 'TE2'}
BUCKETS = ['QB1', 'RB1', 'RB2', 'RB3', 'WR1', 'WR2', 'WR3', 'WR4', 'TE1', 'TE2']
GRP = {'QB1': 'QB', 'RB1': 'RB1', 'RB2': 'RB2', 'RB3': 'RB2', 'WR1': 'WR1', 'WR2': 'WR2', 'WR3': 'WR3', 'WR4': 'WR4+', 'TE1': 'TE1', 'TE2': 'TE2'}
POS = lambda b: 'QB' if b == 'QB1' else b[:2]
num = lambda v, d=0.0: (float(v) if v not in ('', None, 'nan') else d)

# ---------------- game logs (+ usage) ----------------
usage = {}
if os.path.exists(P + 'player_usage.csv'):
    for r in csv.DictReader(open(P + 'player_usage.csv', encoding='utf-8')):
        usage[(int(r['season']), int(r['week']), r['player_id'])] = (r['snap_pct'], r['target_share'], r['adot'])
logs = []
for f in sorted(glob.glob('data/game_logs/game_logs_*.csv')):
    for r in csv.DictReader(open(f, encoding='utf-8')):
        s, w = int(r['season']), int(r['week'])
        if w > 18: continue
        u = usage.get((s, w, r['player_id']), ('', '', ''))
        logs.append(dict(player=r['player'], pid=r['player_id'], s=s, w=w, team=r['team'], opp=r['opponent'], home=r['home_away'] == 'H',
                         slot=r['slot'], ra=int(r['rush_att']), tgt=int(r['targets']), td=int(r['rush_td']) + int(r['rec_td']),
                         snp=num(u[0], None) if u[0] not in ('', 'nan') else None))
logs.sort(key=lambda r: (r['s'], r['w']))
byname = collections.defaultdict(list)
for r in logs: byname[r['player']].append(r)

# team skill TDs per week, defense TDs allowed per slot group per week
team_td = collections.defaultdict(int); def_td = collections.defaultdict(int); def_wk = collections.defaultdict(set)
for r in logs:
    team_td[(r['s'], r['w'], r['team'])] += r['td']
    b = BUCKET.get(r['slot'])
    if b: def_td[(r['s'], r['w'], r['opp'], GRP[b])] += r['td']; def_wk[(r['s'], r['opp'])].add(r['w'])

# closing lines -> implied team total and spread from the team's side
LN = {}
for r in csv.DictReader(open(P + 'game_lines.csv')):
    sp, tot = r['spread_line'], r['total_line']
    if sp in ('', 'nan') or tot in ('', 'nan'): continue
    s, w, sp, tot = int(r['season']), int(r['week']), float(sp), float(tot)
    LN[(s, w, r['home_team'])] = (tot / 2 + sp / 2, sp); LN[(s, w, r['away_team'])] = (tot / 2 - sp / 2, -sp)

# league slot means (the prior every shrunk feature leans on)
cnt = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0, 0])
for r in logs:
    b = BUCKET.get(r['slot'])
    if not b: continue
    c = cnt[b]; c[0] += 1; c[1] += (r['td'] > 0); c[2] += r['ra'] + r['tgt']; c[3] += r['tgt']; c[4] += r['ra']
SM = {b: (cnt[b][1] / cnt[b][0] if cnt[b][0] else .2) for b in BUCKETS}
STOUCH = {b: (cnt[b][2] / cnt[b][0] if cnt[b][0] else 5) for b in BUCKETS}
STGT = {b: (cnt[b][3] / cnt[b][0] if cnt[b][0] else 3) for b in BUCKETS}
SRA = {b: (cnt[b][4] / cnt[b][0] if cnt[b][0] else 2) for b in BUCKETS}
# share prior: a slot's typical share of its team's skill TDs
shr = collections.defaultdict(list)
for (s, w, t), tt in team_td.items(): pass
SSHARE = {'QB1': .06, 'RB1': .28, 'RB2': .12, 'RB3': .05, 'WR1': .17, 'WR2': .11, 'WR3': .07, 'WR4': .04, 'TE1': .1, 'TE2': .04}

_dcache = {}
def def_rate(s, W, d, g):
    """TDs the defense allows per game to the slot group going into week W: prior season until 4 current games, then (2·cur + prior)/3."""
    k = (s, W, d, g)
    if k in _dcache: return _dcache[k]
    cw = [w for w in def_wk.get((s, d), ()) if w < W]
    cur = sum(def_td.get((s, w, d, g), 0) for w in cw) / len(cw) if cw else None
    pw = def_wk.get((s - 1, d), ())
    pri = sum(def_td.get((s - 1, w, d, g), 0) for w in pw) / len(pw) if pw else None
    v = ((2 * cur + pri) / 3 if pri is not None else cur) if cw and len(cw) >= 4 else (pri if pri is not None else cur)
    _dcache[k] = v
    return v

FEATS = ['form', 'l3', 'crate', 'share', 'touch', 'tgt', 'ra', 'ra_qb', 'snp', 'imp', 'sp', 'def', 'def_l3', 'h2h', 'home'] + ['b_' + b for b in BUCKETS if b != 'WR3']

def profile(prev, s, w, team, opp, slot, home):
    """the pre-kickoff profile from earlier games only; returns (feature dict, display dict)."""
    b = BUCKET[slot]; g = GRP[b]
    cur = [p for p in prev if p['s'] == s]; last = [p for p in prev if p['s'] == s - 1]
    tdS = sum(p['td'] for p in cur); gpS = len(cur)
    tdC = sum(p['td'] for p in prev); gC = len(prev)
    hitC = sum(p['td'] > 0 for p in prev); hitS = sum(p['td'] > 0 for p in cur)
    crate = (hitC + 4 * SM[b]) / (gC + 4)
    rate = (hitS + 3 * crate) / (gpS + 3)
    l3n = min(3, gpS); l3k = sum(p['td'] > 0 for p in cur[-3:]) if gpS else 0
    l3 = (l3k + crate) / (l3n + 1)
    src = cur if cur else last[-6:]
    touch = np.mean([p['ra'] + p['tgt'] for p in src]) if src else STOUCH[b]
    tgt = np.mean([p['tgt'] for p in src]) if src else STGT[b]
    ra = np.mean([p['ra'] for p in src]) if src else SRA[b]
    sn = [p['snp'] for p in src if p['snp'] is not None]
    snp = np.mean(sn) if sn else None
    tw = [x for x in range(1, w) if (s, x, team) in team_td]
    tt = sum(team_td[(s, x, team)] for x in tw); mine = sum(p['td'] for p in cur if p['team'] == team)
    share = (mine + 2 * SSHARE[b]) / (tt + 2)
    imp, sp = LN.get((s, w, team), (None, None))
    dr = def_rate(s, w, opp, g)
    dw = sorted(x for x in def_wk.get((s, opp), ()) if x < w)[-3:]
    dl3 = (sum(def_td.get((s, x, opp, g), 0) for x in dw) / len(dw)) if len(dw) >= 2 else dr
    h2h = int(any(p['opp'] == opp and p['td'] > 0 for p in prev))
    f = dict(form=rate - crate, l3=l3, crate=crate, share=share, touch=touch, tgt=tgt, ra=ra, ra_qb=ra if b == 'QB1' else 0.0,
             snp=snp if snp is not None else (.85 if b in ('QB1', 'WR1', 'WR2', 'TE1') else .5), imp=imp if imp is not None else 22.0,
             sp=sp if sp is not None else 0.0, h2h=h2h, home=int(home), **{'def': dr if dr is not None else .3, 'def_l3': dl3 if dl3 is not None else .3})
    for x in BUCKETS:
        if x != 'WR3': f['b_' + x] = int(b == x)
    d = dict(tdS=tdS, gpS=gpS, hitS=hitS, l3k=l3k, l3n=l3n, gC=gC, hitC=hitC, mine=mine, tt=tt, imp=imp, sp=sp, dr=dr, dl3=dl3,
             touch=float(touch), tgt=float(tgt), ra=float(ra), snp=snp, b=b, g=g, h2h=h2h)
    return f, d

# ---------------- training rows (every logged player-game, point in time) ----------------
rows = []
for name, L in byname.items():
    for i, r in enumerate(L):
        if r['slot'] not in BUCKET: continue
        f, d = profile(L[:i], r['s'], r['w'], r['team'], r['opp'], r['slot'], r['home'])
        rows.append((r['s'], r['w'], [f[k] for k in FEATS], int(r['td'] > 0), BUCKET[r['slot']], name, r['team']))
rows.sort(key=lambda x: (x[0], x[1]))
Xall = np.array([x[2] for x in rows], float); yall = np.array([x[3] for x in rows], float)
key = np.array([x[0] * 100 + x[1] for x in rows]); bk = np.array([x[4] for x in rows])
print(f'td_picks: {len(rows)} player-games · field {yall.mean():.1%}')

def fit(X, y, lam=2.0, iters=40):
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    Z = (X - mu) / sd; n, k = Z.shape; Zb = np.hstack([np.ones((n, 1)), Z]); beta = np.zeros(k + 1)
    beta[0] = math.log(max(y.mean(), 1e-3) / max(1 - y.mean(), 1e-3))
    R = np.eye(k + 1) * lam; R[0, 0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Zb @ beta))); Wt = p * (1 - p)
        H = Zb.T @ (Zb * Wt[:, None]) + R; gr = Zb.T @ (y - p) - R @ beta
        st = np.linalg.solve(H, gr); beta += st
        if np.abs(st).max() < 1e-7: break
    return mu, sd, beta
def predict(m, X):
    mu, sd, beta = m; Z = (X - mu) / sd
    return 1 / (1 + np.exp(-(beta[0] + Z @ beta[1:])))

# ---------------- walk-forward backtest ----------------
TIERS = [('lock', .5, 1.01), ('strong', .4, .5), ('solid', .3, .4), ('long', .2, .3), ('low', 0, .2)]
bt_weeks, allp, ally, allb, allk = [], [], [], [], []
eval_keys = sorted(set(k for k in key if k >= 202501))
for ek in eval_keys:
    tr = key < ek; te = key == ek
    if tr.sum() < 1500 or te.sum() < 50: continue
    m = fit(Xall[tr], yall[tr]); p = predict(m, Xall[te]); y = yall[te]; bb = bk[te]
    # base: league slot rate from the training rows
    base = np.array([yall[tr][bk[tr] == b].mean() if (bk[tr] == b).any() else yall[tr].mean() for b in bb])
    o = np.argsort(-p); top10 = y[o[:10]]
    pos = np.array([POS(b) for b in bb]); top3 = []
    for ps in ('QB', 'RB', 'WR', 'TE'):
        idx = np.where(pos == ps)[0]; idx = idx[np.argsort(-p[idx])][:3]; top3 += list(y[idx])
    ll = -np.mean(y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1)))
    llb = -np.mean(y * np.log(np.clip(base, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - base, 1e-6, 1)))
    bt_weeks.append([int(ek // 100), int(ek % 100), int(te.sum()), int(y.sum()), int(top10.sum()), int(len(top10)), int(sum(top3)), int(len(top3)), round(float(ll), 4), round(float(llb), 4)])
    allp += list(p); ally += list(y); allb += list(base); allk += [ek] * len(p)
allp, ally, allb = np.array(allp), np.array(ally), np.array(allb); allk = np.array(allk)
def pav(p, y, bins=24):
    """isotonic calibration: quantile-bin the predictions, pool adjacent violators, interpolate between block centres."""
    o = np.argsort(p); p, y = p[o], y[o]; ch = np.array_split(np.arange(len(p)), bins)
    xs = [p[c].mean() for c in ch if len(c)]; ys = [y[c].mean() for c in ch if len(c)]; ws = [len(c) for c in ch if len(c)]
    B = [[xs[i], ys[i], ws[i]] for i in range(len(xs))]; i = 0
    while i < len(B) - 1:
        if B[i][1] > B[i + 1][1]:
            w = B[i][2] + B[i + 1][2]; B[i] = [(B[i][0] * B[i][2] + B[i + 1][0] * B[i + 1][2]) / w, (B[i][1] * B[i][2] + B[i + 1][1] * B[i + 1][2]) / w, w]; del B[i + 1]; i = max(i - 1, 0)
        else: i += 1
    bx, by = np.array([b[0] for b in B]), np.array([b[1] for b in B])
    return lambda q: np.interp(q, bx, by)
raw = allp.copy()
for ek in sorted(set(allk)):
    prior = allk < ek
    if prior.sum() >= 2000: cal = pav(raw[prior], ally[prior]); allp[allk == ek] = cal(raw[allk == ek])
CAL = pav(raw, ally)
def auc(p, y):
    o = np.argsort(p); r = np.empty(len(p)); r[o] = np.arange(1, len(p) + 1); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else None
calib = []
edges = [0, .1, .15, .2, .25, .3, .35, .4, .45, .5, .6, 1.01]
for a, b in zip(edges[:-1], edges[1:]):
    m = (allp >= a) & (allp < b)
    if m.sum() >= 20: calib.append([round(float(allp[m].mean()), 3), round(float(ally[m].mean()), 3), int(m.sum())])
tiers = {t: [int(((allp >= a) & (allp < b)).sum()), int(ally[(allp >= a) & (allp < b)].sum())] for t, a, b in TIERS}
ll = float(-np.mean(ally * np.log(np.clip(allp, 1e-6, 1)) + (1 - ally) * np.log(np.clip(1 - allp, 1e-6, 1))))
llb = float(-np.mean(ally * np.log(np.clip(allb, 1e-6, 1)) + (1 - ally) * np.log(np.clip(1 - allb, 1e-6, 1))))
bt = dict(calibrated=True, weeks=bt_weeks, calib=calib, tiers=tiers, auc=round(auc(allp, ally), 3), auc_base=round(auc(allb, ally), 3), ll=round(ll, 4), ll_base=round(llb, 4),
          n=int(len(allp)), hits=int(ally.sum()), top10=[sum(w[4] for w in bt_weeks), sum(w[5] for w in bt_weeks)], top3pos=[sum(w[6] for w in bt_weeks), sum(w[7] for w in bt_weeks)])
print(f'  walk-forward {len(bt_weeks)} weeks · AUC {bt["auc"]} (slot-only {bt["auc_base"]}) · log loss {bt["ll"]} vs {bt["ll_base"]} · top-10 {bt["top10"][0]}/{bt["top10"][1]} · tiers {tiers}')

# ---------------- the target week ----------------
games = list(csv.DictReader(open(P + 'games_2026.csv')))
by_wk = collections.defaultdict(list)
for g in games: by_wk[int(g['week'])].append(g)
def main_date(w):
    c = collections.Counter(g['date'] for g in by_wk[w]); return datetime.date.fromisoformat(c.most_common(1)[0][0])
target = next((w for w in sorted(by_wk) if main_date(w) >= TODAY), max(by_wk))
if '--week' in sys.argv: target = int(sys.argv[sys.argv.index('--week') + 1])
tgames = by_wk[target]; tdates = sorted(g['date'] for g in tgames)
sched = {r['team']: r for r in csv.DictReader(open(P + 'schedule_2026.csv'))}
dcp = sorted(glob.glob(P + 'depth_charts_*.csv'))[-1]
depth = list(csv.DictReader(open(dcp, encoding='utf-8')))
model = fit(Xall, yall)
mu, sd, beta = model
LBL = dict(form='form this season vs his career', l3='TDs in his last three', crate='career TD rate', share='share of his team\'s TDs', touch='touches a game', tgt='targets a game',
           ra='carries a game', ra_qb='QB carries', snp='snap share', imp='team implied total', sp='spread', h2h='scored vs them before', home='home', **{'def': 'what the defense allows his slot', 'def_l3': 'what the defense allowed his slot lately'})

def norm(n): return re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', '', n.lower()))
# posted anytime-TD prices for the target week (best Yes across books / exchanges)
price = {}
if os.path.exists(P + 'arb_board.csv'):
    for r in csv.DictReader(open(P + 'arb_board.csv', encoding='utf-8')):
        if r.get('league') != 'nfl' or r.get('stat') != 'anytime_td' or not r.get('best_a_american'): continue
        k = (r.get('kickoff') or '')[:10]
        if tdates and not (tdates[0] <= k <= (datetime.date.fromisoformat(tdates[-1]) + datetime.timedelta(days=1)).isoformat()): continue
        nm = norm(r['player']); am = float(r['best_a_american']); dec = float(r['best_a_dec'])
        if nm not in price or dec > price[nm][1]: price[nm] = (am, dec, r.get('best_a_src', ''))
oldm = {}
if os.path.exists(P + 'bet_td.csv'):
    for r in csv.DictReader(open(P + 'bet_td.csv', encoding='utf-8')):
        if r.get('week') and int(r['week']) == target and r.get('p_model'): oldm[norm(r['player'])] = float(r['p_model'])
def fair(p): return int(round(-100 * p / (1 - p))) if p >= .5 else int(round(100 * (1 - p) / p))

picks = []
for dr in depth:
    slot = dr['slot']
    if slot not in BUCKET or dr['team'] not in sched: continue
    raw = sched[dr['team']].get(f'week_{target}', '')
    if not raw or raw == 'BYE': continue
    opp = raw.replace('@', ''); home = not raw.startswith('@')
    nm = dr.get('log_name') or dr['player']
    prev = [r for r in byname.get(nm, []) if (r['s'], r['w']) < (SEASON, target)]
    f, d = profile(prev, SEASON, target, dr['team'], opp, slot, home)
    x = np.array([f[k] for k in FEATS], float); z = (x - mu) / sd; contrib = beta[1:] * z
    p_raw = float(1 / (1 + np.exp(-(beta[0] + contrib.sum())))); p = float(CAL(np.array([p_raw]))[0])
    why = []
    for j in np.argsort(-contrib):
        k = FEATS[j]
        if contrib[j] <= .05 or k.startswith('b_') or k == 'home' or (k == 'ra' and d['b'] == 'QB1'): continue
        if k == 'ra_qb': t = f"{d['ra']:.1f} carries a game"
        elif k == 'form': t = f"TD in {d['hitS']} of {d['gpS']} — below his career norm" if d['gpS'] else 'scoring history'
        elif k == 'l3': t = f"TD in {d['l3k']} of his last {d['l3n']}"
        elif k == 'crate': t = f"career: TD in {d['hitC']} of {d['gC']}"
        elif k == 'share': t = f"{d['mine']} of his team's {d['tt']} TDs"
        elif k == 'touch': t = f"{d['touch']:.1f} touches a game"
        elif k == 'tgt': t = f"{d['tgt']:.1f} targets a game"
        elif k == 'ra': t = f"{d['ra']:.1f} carries a game"
        elif k == 'snp': t = f"{d['snp']:.0%} of snaps" if d['snp'] is not None else 'every-down role'
        elif k == 'imp': t = f"team implied {d['imp']:.1f}" if d['imp'] is not None else 'team total'
        elif k == 'sp': t = f"favored by {d['sp']:g}" if d['sp'] and d['sp'] > 0 else 'spread'
        elif k == 'def': t = f"{opp} allows {d['dr']:.2f} TD/g to {d['g']}s" if d['dr'] is not None else 'soft defense'
        elif k == 'def_l3': t = f"{opp} gave {d['g']}s {d['dl3']:.1f} TD/g lately" if d['dl3'] is not None else 'defense trend'
        elif k == 'h2h': t = f"scored vs {opp} before"
        else: t = LBL.get(k, k)
        why.append(t)
        if len(why) == 3: break
    risk = None
    for j in np.argsort(contrib):
        k = FEATS[j]
        if contrib[j] >= -.12: break
        if k == 'sp' and d['sp'] is not None and d['sp'] < 0: risk = f"underdog by {abs(d['sp']):g}"
        elif k == 'imp' and d['imp'] is not None and d['imp'] < 21.5: risk = f"team implied only {d['imp']:.1f}"
        elif k == 'def' and d['dr'] is not None: risk = f"{opp} allows just {d['dr']:.2f} TD/g to {d['g']}s"
        elif k == 'def_l3' and d['dl3'] is not None: risk = f"{opp} has held {d['g']}s to {d['dl3']:.1f} TD/g lately"
        elif k == 'l3' and d['l3n'] >= 2 and d['l3k'] == 0: risk = f"no TD in his last {d['l3n']}"
        elif k == 'touch' and d['b'] != 'QB1' and d['touch'] < STOUCH[d['b']]: risk = f"only {d['touch']:.1f} touches a game"
        elif k == 'snp' and d['snp'] is not None and d['snp'] < .6: risk = f"plays {d['snp']:.0%} of snaps"
        if risk: break
    pr = price.get(norm(dr['player'])) or price.get(norm(nm))
    ev = round(p * pr[1] - 1, 3) if pr else None
    tier = next(t for t, a, b in TIERS if a <= p < b)
    picks.append(dict(n=dr['player'], t=dr['team'], o=opp, h=home, s=slot, b=d['b'], pos=POS(d['b']), inj=dr.get('injury', '1'), p=round(p, 4), fair=fair(p),
                      tier=tier, why=why, risk=risk, praw=round(p_raw, 4), price=int(pr[0]) if pr else None, book=pr[2] if pr else None, ev=ev, pm=oldm.get(norm(dr['player'])),
                      imp=round(d['imp'], 1) if d['imp'] is not None else None, sp=d['sp'], hitS=d['hitS'], gpS=d['gpS'], l3k=d['l3k'], l3n=d['l3n'],
                      share=round(d['mine'] / d['tt'], 3) if d['tt'] else None, touch=round(d['touch'], 1), dr=round(d['dr'], 2) if d['dr'] is not None else None))
picks.sort(key=lambda x: -x['p'])
for ps in ('QB', 'RB', 'WR', 'TE'):
    for i, x in enumerate([x for x in picks if x['pos'] == ps and x['inj'] != '-1']): x['rp'] = i + 1
for i, x in enumerate([x for x in picks if x['inj'] != '-1']): x['ra'] = i + 1

# ---------------- the frozen ledger: first scoring of a week is the record ----------------
LP = P + 'td_picks_ledger.csv'
COLS = ['season', 'week', 'frozen_on', 'player', 'team', 'opp', 'slot', 'pos', 'p', 'fair', 'tier', 'rank_all', 'rank_pos', 'price', 'book', 'result']
led = list(csv.DictReader(open(LP, encoding='utf-8'))) if os.path.exists(LP) else []
if '--refreeze' in sys.argv and not any(r['result'] in ('W', 'L') for r in led if int(r['season']) == SEASON and int(r['week']) == target):
    led = [r for r in led if not (int(r['season']) == SEASON and int(r['week']) == target)]
have = {(int(r['season']), int(r['week'])) for r in led}
if (SEASON, target) not in have:
    for x in picks:
        if x['inj'] == '-1' or x['p'] < .15: continue
        led.append(dict(season=SEASON, week=target, frozen_on=str(TODAY), player=x['n'], team=x['t'], opp=x['o'], slot=x['s'], pos=x['pos'], p=x['p'], fair=x['fair'],
                        tier=x['tier'], rank_all=x.get('ra', ''), rank_pos=x.get('rp', ''), price=x['price'] if x['price'] is not None else '', book=x['book'] or '', result=''))
    print(f'  froze {sum(1 for r in led if int(r["week"]) == target and int(r["season"]) == SEASON)} picks for week {target}')
# prices may improve until kickoff; p never changes
pk = {(x['n'], target): x for x in picks}
logged = {(r['s'], r['w'], r['player']): r for r in logs}
teams_logged = collections.defaultdict(set)
for r in logs: teams_logged[(r['s'], r['w'])].add(r['team'])
for r in led:
    s, w = int(r['season']), int(r['week'])
    if w == target and s == SEASON and (r['player'], w) in pk and pk[(r['player'], w)]['price'] is not None:
        r['price'], r['book'] = pk[(r['player'], w)]['price'], pk[(r['player'], w)]['book']
    lg = logged.get((s, w, r['player']))
    if lg: r['result'] = 'W' if lg['td'] > 0 else 'L'
    elif r['team'] in teams_logged.get((s, w), ()): r['result'] = 'void'
with open(LP, 'w', newline='', encoding='utf-8') as fh:
    wr = csv.DictWriter(fh, fieldnames=COLS); wr.writeheader(); [wr.writerow({c: r.get(c, '') for c in COLS}) for r in led]
rec = []
for (s, w) in sorted({(int(r['season']), int(r['week'])) for r in led}):
    R = [r for r in led if int(r['season']) == s and int(r['week']) == w]
    g = [r for r in R if r['result'] in ('W', 'L')]
    top = sorted([r for r in g if r['rank_all']], key=lambda r: int(r['rank_all']))[:10]
    t = {k: [sum(1 for r in g if r['tier'] == k), sum(1 for r in g if r['tier'] == k and r['result'] == 'W')] for k, _, _ in TIERS}
    rec.append(dict(s=s, w=w, frozen=R[0]['frozen_on'], n=len(R), graded=len(g), wins=sum(r['result'] == 'W' for r in g), top10=[sum(r['result'] == 'W' for r in top), len(top)], tiers=t,
                    rows=[[r['player'], r['team'], r['opp'], r['slot'], float(r['p']), r['tier'], int(r['rank_all']) if r['rank_all'] else None, r['price'], r['book'], r['result']] for r in R if r['rank_all'] and int(r['rank_all']) <= 40]))

out = dict(built=str(TODAY), season=SEASON, week=target, dates=[tdates[0], tdates[-1]] if tdates else None, games=len(tgames), depth=dcp.split('_')[-1][:10],
           priced=sum(1 for x in picks if x['price'] is not None),
           model=dict(feats=FEATS, coef=[round(float(c), 4) for c in beta[1:]], icpt=round(float(beta[0]), 4), n=len(rows), field=round(float(yall.mean()), 4),
                      labels={k: LBL.get(k, k) for k in FEATS}),
           bt=bt, picks=picks, record=rec)
json.dump(out, open(P + 'td_picks.json', 'w'), separators=(',', ':'))
print(f'  week {target}: {len(picks)} players scored · {out["priced"]} with a posted price · top: ' + ', '.join(f"{x['n']} {x['p']:.0%}" for x in picks[:5]))
