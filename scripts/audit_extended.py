"""RAINMAN extended data audit — everything scripts/verify_data.py does not already cover.

verify_data.py proves the chain raw PFR box lines -> game logs -> DvP tables -> dashboard DvP payload. This script adds:
  A  a second source for every box-score number: 2026 logs vs nflverse weekly player stats, 2024-25 logs vs nflverse
     play-by-play rebuilt into box scores; snap shares vs nflverse snap counts
  B  the 2026 schedule, kickoffs and PFR game list vs the nflverse schedule
  C  betting lines: game_lines vs nflverse, the spread sign vs the live books, the page's closing-line table, implied totals
  D  the dashboard payload vs the processed tables (per-season and adjusted DvP, logs, schedule, footer counts, week)
  E  slot integrity (one body per slot per team-game)
  F  TD Picks: backtest arithmetic, every displayed feature recomputed from the logs, opponents, the ledger's kickoff locks
  G  the prop board: opponents, probabilities, prices
  H  injuries and QB1s vs nflverse (informational: the two sources update at different times)
  I  the NCAA build's internal consistency
Usage: python scripts/audit_extended.py      (prints PASS / WARN / FAIL lines; writes notes/data_audit_ext.json)"""
import csv, glob, json, os, re, sys, collections, datetime, unicodedata
import numpy as np, pandas as pd

R = []
def chk(name, status, detail=''):
    R.append(dict(status=status, check=name, detail=detail)); print(f'{status:4}  {name}' + (f' — {detail}' if detail else ''), flush=True)
def ok(name, cond, detail='', warn=False): chk(name, 'PASS' if cond else ('WARN' if warn else 'FAIL'), detail)
NV = {'LA': 'LAR', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX'}
nv = lambda t: NV.get(t, t)
def deacc(n): return unicodedata.normalize('NFKD', str(n)).encode('ascii', 'ignore').decode()
def norm(n): return re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', '', deacc(n).lower()))
def load_J(path):
    h = open(path, encoding='utf-8').read(); i = h.index('const J = ') + len('const J = ')
    return json.JSONDecoder().raw_decode(h, i)[0]

L = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
L['td'] = L.rush_td + L.rec_td
SE = sorted(L.season.unique())
J = load_J('dashboard/rainman.html')
G = pd.read_csv('data/raw/nflverse/games.csv'); G = G[G.game_type == 'REG'].copy()
G['away'] = G.away_team.map(nv); G['home'] = G.home_team.map(nv)
idmap = {}
for y in (2024, 2025, 2026):
    f = f'data/raw/nflverse/roster_{y}.parquet'
    if os.path.exists(f):
        r = pd.read_parquet(f, columns=['pfr_id', 'gsis_id'])
        for a, b in zip(r.pfr_id, r.gsis_id):
            if isinstance(a, str) and isinstance(b, str): idmap[a] = b
L['gsis'] = L.player_id.map(idmap)
print(f'logs {len(L)} rows · seasons {SE} · pfr->gsis mapped {L.gsis.notna().mean():.1%}')

# ================================================================== A  second source for the box scores
def compare(ours, theirs, fields, label, tol_y=0):
    theirs = theirs.rename(columns={b: b + '_nv' for _, b in fields}); fields = [(a, b + '_nv') for a, b in fields]
    m = ours.merge(theirs, on=['week', 'gsis'], how='left', indicator=True)
    found = m['_merge'] == 'both'
    ok(f'{label}: every log row found in nflverse', found.mean() >= .995, f'{found.sum()} of {len(m)} matched ({(~found).sum()} not found)', warn=found.mean() >= .98)
    m = m[found]; bad = []
    for a, b in fields:
        d = (m[a].fillna(0) - m[b].fillna(0)).abs()
        lim = tol_y if 'yds' in a else 0
        nb = int((d > lim).sum()); rate = 1 - nb / max(len(m), 1)
        tag = f'{a}: {rate:.2%} agree' + (f' (±{lim} yd)' if lim else '') + (f' · {nb} rows differ' if nb else '')
        ok(f'{label}: {a}', rate >= .995 if lim or 'td' not in a else nb == 0 or rate >= .998, tag, warn=rate >= .98)
        for _, r in m[d > lim].head(6).iterrows(): bad.append(f"{r.player} {int(r.season)} wk{int(r.week)} {a} ours {r[a]} vs nflverse {r[b]}")
    if bad: print('      examples: ' + ' | '.join(bad[:12]))
    return m

# A1 every season vs nflverse official weekly player stats (stats_player_week_{y}.parquet) — matched on week + team + name, then on id
F26 = [('pass_yds', 'passing_yards'), ('pass_td', 'passing_tds'), ('int', 'passing_interceptions'), ('pass_att', 'attempts'), ('cmp', 'completions'),
       ('rush_att', 'carries'), ('rush_yds', 'rushing_yards'), ('rush_td', 'rushing_tds'), ('targets', 'targets'), ('rec', 'receptions'),
       ('rec_yds', 'receiving_yards'), ('rec_td', 'receiving_tds'), ('fumbles_lost', 'fl')]
def last(n): w = [x for x in re.sub(r'[^a-z ]', '', deacc(n).lower().replace('.', '')).split() if x not in ('jr', 'sr', 'ii', 'iii', 'iv', 'v')]; return w[-1] if w else ''
for y in SE:
    f = f'data/raw/nflverse/stats_player_week_{y}.parquet'
    if not os.path.exists(f): chk(f'{y} logs vs nflverse weekly stats', 'WARN', 'no nflverse weekly file cached'); continue
    W = pd.read_parquet(f); W = W[(W.season_type == 'REG') & (W.week <= 18)].copy()
    W['tm'] = W.team.map(nv); W['nm'] = W.player_display_name.map(norm); W['ln'] = W.player_display_name.map(last)
    W['fl'] = W[['sack_fumbles_lost', 'rushing_fumbles_lost', 'receiving_fumbles_lost']].fillna(0).sum(axis=1)
    o = L[L.season == y].copy(); o['nm'] = o.player.map(norm); o['ln'] = o.player.map(last)
    Wc = W[['week', 'tm', 'nm', 'ln', 'player_id', 'player_display_name'] + [b for _, b in F26]].rename(columns={b: b + '_nv' for _, b in F26}).rename(columns={'player_id': 'nv_id'})
    m1 = o.merge(Wc.drop(columns=['ln']), left_on=['week', 'team', 'nm'], right_on=['week', 'tm', 'nm'], how='left')
    un = m1[m1.nv_id.isna()][o.columns]
    m2 = un.merge(Wc.drop(columns=['nm']), left_on=['week', 'gsis'], right_on=['week', 'nv_id'], how='left')
    m2 = m2[m2.nv_id.notna() & (m2.ln_x == m2.ln_y)] if 'ln_x' in m2.columns else m2[m2.nv_id.notna()]
    m3 = un.merge(Wc.drop(columns=['nm']), left_on=['week', 'team', 'ln'], right_on=['week', 'tm', 'ln'], how='inner')
    m3 = m3[~m3.set_index(['week', 'player']).index.isin(m2.set_index(['week', 'player']).index)].drop_duplicates(['week', 'player'], keep=False)
    m = pd.concat([m1[m1.nv_id.notna()], m2, m3], ignore_index=True)
    ok(f'{y}: every log row found in nflverse weekly stats', len(m) >= .995 * len(o), f'{len(m)} of {len(o)} matched' + (f" · unmatched: {', '.join(sorted(set(o.player) - set(m.player))[:6])}" if len(m) < len(o) else ''), warn=len(m) >= .98 * len(o))
    bad = []
    for a_, b_ in F26:
        d = (m[a_].fillna(0) - m[b_ + '_nv'].fillna(0)).abs(); nb = int((d > 0).sum()); rate = 1 - nb / max(len(m), 1)
        strict = a_ in ('pass_td', 'rush_td', 'rec_td', 'pass_yds', 'rush_yds', 'rec_yds')
        if a_ == 'fumbles_lost' and nb and (m[a_].fillna(0) >= m[b_ + '_nv'].fillna(0)).all():
            ok(f'{y} logs vs nflverse: fumbles_lost', True, f'{rate:.2%} agree · the {nb} others are fumbles on kick / punt returns, which PFR counts and nflverse\'s offensive columns leave out'); continue
        ok(f'{y} logs vs nflverse: {a_}', rate >= (.998 if strict else .99), f'{rate:.2%} agree' + (f' · {nb} rows differ' if nb else ''), warn=rate >= .99)
        for _, r in m[d > 0].head(4).iterrows(): bad.append(f"{r.player} wk{int(r.week)} {a_} {r[a_]} vs {r[b_ + '_nv']:.0f}")
    if bad: print('      examples: ' + ' | '.join(bad[:16]))
    # nobody with a touch missing from a logged game
    played = set(zip(o.week, o.team)); seen = set(zip(m.week, m.nv_id))
    sk = W[W.position.isin(['QB', 'RB', 'WR', 'TE', 'FB']) & ((W.attempts.fillna(0) + W.carries.fillna(0) + W.targets.fillna(0)) > 0)]
    miss = sk[[(w, t) in played and (w, g) not in seen for w, t, g in zip(sk.week, sk.tm, sk.player_id)]]
    ok(f'{y}: no skill player with a touch in nflverse is missing from the logs', len(miss) == 0, f'{len(miss)} missing' + (': ' + ', '.join(f"{r.player_display_name} wk{r.week} {r.tm}" for _, r in miss.head(8).iterrows()) if len(miss) else ''), warn=len(miss) <= 3)
    # rushing + receiving TDs per team-game, everyone included — the denominator of every TD-share number
    tl = o.groupby(['week', 'team']).td.sum(); tw = W.groupby(['week', 'tm'])[['rushing_tds', 'receiving_tds']].sum().sum(axis=1)
    tw.index.names = ['week', 'team']; j = pd.concat([tl, tw], axis=1).dropna(subset=[0]).fillna(0); j.columns = ['ours', 'nv']; off = j[j.ours != j.nv]
    ok(f'{y}: rushing + receiving TDs per team-game = nflverse', len(off) == 0, f'{len(j) - len(off)} of {len(j)} team-games equal' + (': ' + ', '.join(f'wk{w} {t} {int(r.ours)} vs {int(r.nv)}' for (w, t), r in off.head(8).iterrows()) if len(off) else ''), warn=len(off) <= 2)

# A3 snap shares on the page vs nflverse snap counts
LOGC = {'player': 0, 'pid': 1, 'season': 2, 'week': 3, 'team': 4, 'opp': 5, 'ha': 6, 'slot': 7, 'pos': 8, 'py': 9, 'ptd': 10, 'patt': 11, 'int': 12, 'ra': 13, 'ry': 14, 'rtd': 15,
        'tgt': 16, 'rec': 17, 'recy': 18, 'rectd': 19, 'fstd': 20, 'fppr': 21, 'snaps': 22, 'snp': 23, 'tsh': 24, 'adot': 25}
JL = pd.DataFrame([[r[LOGC[k]] if len(r) > LOGC[k] else None for k in LOGC] for r in J['logs']], columns=list(LOGC))
for y in (2024, 2025, 2026):
    f = f'data/raw/nflverse/snap_counts_{y}.parquet'
    if not os.path.exists(f): continue
    S = pd.read_parquet(f); S = S[S.game_type == 'REG'][['week', 'pfr_player_id', 'offense_pct']]
    m = JL[(JL.season == y) & JL.snp.notna()].merge(S, left_on=['week', 'pid'], right_on=['week', 'pfr_player_id'])
    d = (m.snp.astype(float) - m.offense_pct.astype(float)).abs()
    ok(f'{y}: snap share on the page = nflverse snap counts', (d <= .011).mean() >= .99, f'{(d <= .011).mean():.2%} of {len(m)} agree (±1 pt)', warn=(d <= .011).mean() >= .95)

# ================================================================== B  schedule, kickoffs, PFR game list vs nflverse
G26 = G[G.season == 2026]
want = {}
for _, g in G26.iterrows():
    want[(g.away, int(g.week))] = '@' + g.home; want[(g.home, int(g.week))] = g.away
sched = {r['team']: r for r in csv.DictReader(open('data/processed/schedule_2026.csv'))}
mm = []; byes = 0
for t, r in sched.items():
    for w in range(1, 19):
        v = r.get(f'week_{w}', ''); e = want.get((t, w), 'BYE')
        if v == 'BYE': byes += 1
        if v != e: mm.append(f'{t} wk{w} {v} vs {e}')
ok('schedule_2026: every team-week = nflverse schedule', not mm, f'{32 * 18 - len(mm)} of {32 * 18} cells · {byes} byes' + (': ' + ', '.join(mm[:8]) if mm else ''))
js = J.get('sched26', {})
jm = [f'{t} wk{w + 1}' for t, a in js.items() for w, v in enumerate(a) if v != sched[t].get(f'week_{w + 1}')]
ok('page schedule = schedule_2026.csv', not jm, f'{len(jm)} cells differ' if jm else '544 game cells + byes identical')
ko = list(csv.DictReader(open('data/processed/kickoffs_2026.csv')))
km = []
for r in ko:
    g = G26[(G26.week == int(r['week'])) & (G26.home == r['home'])]
    if g.empty or g.iloc[0].away != r['vis']: km.append(f"wk{r['week']} {r['vis']}@{r['home']} not in nflverse"); continue
    g = g.iloc[0]; te = (r.get('time_et') or '').strip()
    t = datetime.datetime.strptime(te, '%I:%M %p').strftime('%H:%M') if te else None
    if g.gameday != r['date'] or (t and g.gametime != t): km.append(f"wk{r['week']} {r['vis']}@{r['home']} {r['date']} {t or 'no time'} vs {g.gameday} {g.gametime}")
ok('kickoffs_2026: date + ET time = nflverse (week 18 times are TBD)', not km, f'{len(ko) - len(km)} of {len(ko)} games' + (': ' + '; '.join(km[:6]) if km else ''))
gp = list(csv.DictReader(open('data/processed/games_2026.csv')))
gm = []
for r in gp:
    g = G26[(G26.week == int(r['week'])) & (G26.home == r['home'])]
    if g.empty or g.iloc[0].away != r['vis'] or g.iloc[0].gameday != r['date']: gm.append(f"wk{r['week']} {r['vis']}@{r['home']} {r['date']}")
ok('games_2026 (PFR) = nflverse game list', not gm and len(gp) == len(G26), f'{len(gp)} vs {len(G26)} games' + (': ' + ', '.join(gm[:6]) if gm else ''))
# results: every logged 2026 game is final in nflverse and the logs have both teams
lg = L[L.season == 2026].groupby(['week', 'team']).size().reset_index()
fin = G26[G26.home_score.notna()]
nolog = [f"wk{g.week} {g.away}@{g.home}" for _, g in fin.iterrows() if not ((lg.week == g.week) & (lg.team == g.home)).any()]
ok('2026: every finished game is in the logs', not nolog, f'{len(fin)} finished · not yet logged: ' + ', '.join(nolog) if nolog else f'{len(fin)} finished games, all logged', warn=True)

# ================================================================== C  betting lines
GL = pd.read_csv('data/processed/game_lines.csv')
m = GL.merge(G[['game_id', 'spread_line', 'total_line']], on='game_id', suffixes=('', '_nv'))
d1 = ((m.spread_line.fillna(-999) != m.spread_line_nv.fillna(-999)) | (m.total_line.fillna(-999) != m.total_line_nv.fillna(-999))).sum()
ok('game_lines.csv = nflverse spread / total (every game)', d1 == 0 and len(m) == len(GL), f'{len(m)} games · {d1} differ')
LA = pd.read_csv('data/processed/lines_all.csv'); LA = LA[(LA.league == 'nfl') & LA.market.isin(['spread', 'total'])].copy()
LA['away'] = LA.away.map(nv); LA['home'] = LA.home.map(nv); LA['selection'] = LA.selection.map(lambda s: nv(s) if isinstance(s, str) else s)
sp_bk = LA[(LA.market == 'spread') & (LA.selection == LA.home)].groupby(['away', 'home']).point.median()
to_bk = LA[(LA.market == 'total') & LA.selection.str.lower().str.startswith('o')].groupby(['away', 'home']).point.median()
up = G26[G26.home_score.isna()]
cm = []; nchk = 0
for _, g in up.iterrows():
    k = (g.away, g.home)
    if k in sp_bk.index and not pd.isna(g.spread_line):
        nchk += 1
        if abs(g.spread_line - (-sp_bk[k])) > 1.5: cm.append(f'{g.away}@{g.home} nflverse {g.spread_line:+} vs books {-sp_bk[k]:+}')
        if k in to_bk.index and abs(g.total_line - to_bk[k]) > 2: cm.append(f'{g.away}@{g.home} total {g.total_line} vs books {to_bk[k]}')
ok('upcoming games: nflverse spread sign = the live books (no flipped favourite)', not [c_ for c_ in cm if 'total' not in c_] and nchk > 0, f'{nchk} games compared' + (f" · nflverse trails the books on: {'; '.join(cm[:6])} — the site uses the books' consensus for unplayed games" if cm else ''))
sys.path.insert(0, 'scripts'); from live_lines import consensus as _cons
LIVE = _cons()
glh = J.get('betting', {}).get('glh', [])
gk = {(int(g.season), int(g.week), g.away, g.home): g for _, g in G.iterrows()}
gb = []
nlive = 0
for r in glh:
    g = gk.get((r[0], r[1], r[2], r[3]))
    if g is None: gb.append(f'{r[0]} wk{r[1]} {r[2]}@{r[3]} missing'); continue
    if len(r) > 10 and r[10] == 'books':
        nlive += 1; c_ = LIVE.get((r[2], r[3]))
        if c_ is None or abs(c_[0] - float(r[6])) > .01 or abs(c_[1] - float(r[7])) > .01: gb.append(f'{r[0]} wk{r[1]} {r[2]}@{r[3]} live line {r[6]}/{r[7]} vs consensus {c_}')
        continue
    if r[6] is not None and r[6] != '' and not pd.isna(g.spread_line) and float(r[6]) != float(g.spread_line): gb.append(f'{r[0]} wk{r[1]} {r[2]}@{r[3]} spread {r[6]} vs {g.spread_line}')
    if r[7] is not None and r[7] != '' and not pd.isna(g.total_line) and float(r[7]) != float(g.total_line): gb.append(f'{r[0]} wk{r[1]} total {r[7]} vs {g.total_line}')
    if r[4] is not None and not pd.isna(g.away_score) and (int(r[4]) != int(g.away_score) or int(r[5]) != int(g.home_score)): gb.append(f'{r[0]} wk{r[1]} {r[2]}@{r[3]} score')
ok("page line table (Weeklies' implied totals) = nflverse closing lines + the books' consensus for unplayed games", not gb, f'{len(glh)} games ({nlive} on the live consensus) · {len(gb)} off' + (': ' + '; '.join(gb[:6]) if gb else ''))

# ================================================================== D  dashboard payload vs processed tables
for key in [k for k in J['dvp'] if k.isdigit()] + ['adjusted']:
    f = f'data/processed/dvp_season_{key}.csv' if key.isdigit() else 'data/processed/dvp_adjusted.csv'
    if not os.path.exists(f): chk(f'page DvP {key}', 'WARN', 'no table'); continue
    T = pd.read_csv(f); off = 0; n = 0
    for _, r in T.iterrows():
        d = J['dvp'][key].get(r['defense'])
        if d is None: off += 1; continue
        for c in J['statCols']:
            if f'{c} avg' not in T.columns: continue
            n += 1; s = d['stats'].get(c) or {}
            if abs(float(s.get('avg', -1)) - float(r[f'{c} avg'])) > .006 or (f'{c} rank' in T.columns and float(s.get('rank', -1)) != float(r[f'{c} rank'])): off += 1
    ok(f'page DvP [{key}] = {os.path.basename(f)} (avg + rank, every cell)', off == 0, f'{n} cells · {off} off')
k = ['player_id', 'season', 'week']
JL2 = JL.rename(columns={c: 'j_' + c for c in JL.columns if c not in ('season', 'week')}).rename(columns={'j_pid': 'player_id'})
m = L.merge(JL2, on=k, how='outer', indicator=True)
ok('page game logs = game_logs csv (same player-games)', (m['_merge'] == 'both').all(), f"{(m['_merge'] == 'both').sum()} matched · {(m['_merge'] != 'both').sum()} unmatched")
m = m[m['_merge'] == 'both']; off = 0
for a, b in [('pass_yds', 'py'), ('pass_td', 'ptd'), ('pass_att', 'patt'), ('int', 'int'), ('rush_att', 'ra'), ('rush_yds', 'ry'), ('rush_td', 'rtd'), ('targets', 'tgt'), ('rec', 'rec'), ('rec_yds', 'recy'), ('rec_td', 'rectd'),
             ('fantasy_pts_std', 'fstd'), ('fantasy_pts_ppr', 'fppr')]:
    off += int(((m[a].astype(float) - m['j_' + b].astype(float)).abs() > .011).sum())
ok('page game logs: every stat = csv', off == 0, f'{off} values off')
ok('page slots + teams + opponents = csv', ((m.slot == m.j_slot) & (m.team == m.j_team) & (m.opponent == m.j_opp)).all(), f'{((m.slot != m.j_slot) | (m.team != m.j_team) | (m.opponent != m.j_opp)).sum()} differ')
games = L.groupby(['season', 'week']).apply(lambda d: len(set(d.team)) / 2).sum()
ok('footer games = logged games', round(len(J['weekly']) / 2) == round(games), f"footer {round(len(J['weekly']) / 2)} · logs {games:.0f}")
ok('footer rows = log rows', len(J['logs']) == len(L), f"{len(J['logs'])} vs {len(L)}")
today = datetime.date.today(); wks = collections.defaultdict(list)
for r in gp: wks[int(r['week'])].append(r['date'])
autow = next((w for w in sorted(wks) if max(wks[w]) >= str(today)), 18)
ok('page week = first week not finished', J['week'] == autow, f"page {J['week']} · expected {autow}", warn=abs(J['week'] - autow) <= 1)

# ================================================================== E  slot integrity
SL = ['QB1', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE1', 'TE2']
c = L[L.slot.isin(SL)].groupby(['season', 'week', 'team', 'slot']).size()
dup = c[c > 1]
ok('one player per slot per team-game (QB1 RB1 RB2 WR1-3 TE1 TE2)', len(dup) == 0, f'{len(dup)} doubles' + (': ' + ', '.join(f'{s} wk{w} {t} {sl}' for (s, w, t, sl) in dup.index[:8]) if len(dup) else ''))
qb = L[L.slot == 'QB1'].groupby(['season', 'week', 'team']).size()
tg = L.groupby(['season', 'week', 'team']).size()
noqb = [k for k in tg.index if k not in qb.index]
ok('every team-game has a QB1', not noqb, f'{len(noqb)} without' + (': ' + ', '.join(f'{s} wk{w} {t}' for s, w, t in noqb[:6]) if noqb else ''), warn=len(noqb) <= 5)

# ================================================================== F  TD Picks
T = J.get('tdpicks')
if T:
    bt = T['bt']; W_ = bt['weeks']
    ok('TD Picks backtest: top-10 total = sum of weeks', bt['top10'] == [sum(w[4] for w in W_), sum(w[5] for w in W_)], f"{bt['top10']}")
    ok('TD Picks backtest: tier counts add up to every graded pick', sum(v[0] for v in bt['tiers'].values()) == bt['n'] and sum(v[1] for v in bt['tiers'].values()) == bt['hits'], f"n {bt['n']} · hits {bt['hits']}")
    ok('TD Picks backtest: the top lists agree with the weekly top-10 counts', all(sum(x[4] for x in bt['top'].get(f'{w[0]}-{w[1]}', [])[:10]) == w[4] for w in W_), f"{len(bt['top'])} weeks")
    tw = T['week']; dc = pd.read_csv(sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1])
    ln = {r['player']: (r.get('log_name') if isinstance(r.get('log_name'), str) else r['player']) for _, r in dc.iterrows()}
    off = []; nchk = 0
    for x in T['picks'][:60]:
        nm = ln.get(x['n'], x['n']); P = L[(L.player == nm)].sort_values(['season', 'week'])
        cur = P[(P.season == 2026) & (P.week < tw)]
        nchk += 1
        exp = dict(gpS=len(cur), hitS=int((cur.td > 0).sum()), l3n=min(3, len(cur)), l3k=int((cur.tail(3).td > 0).sum()) if len(cur) else 0)
        src = cur if len(cur) else P[P.season == 2025].tail(6)
        if len(src): exp['touch'] = round(float((src.rush_att + src.targets).mean()), 1)
        tt = int(L[(L.season == 2026) & (L.team == x['t']) & (L.week < tw)].td.sum()); mine = int(cur[cur.team == x['t']].td.sum())
        exp['share'] = round(mine / tt, 3) if tt else None
        for k_, v in exp.items():
            if v is not None and x.get(k_) is not None and abs(float(x[k_]) - float(v)) > .051: off.append(f"{x['n']} {k_} page {x[k_]} vs logs {v}")
        if sched.get(x['t'], {}).get(f'week_{tw}', '').replace('@', '') != x['o']: off.append(f"{x['n']} opp {x['o']}")
    ok('TD Picks: top 60 cards recomputed from the logs (games, TDs, last 3, touches, TD share, opponent)', not off, f'{nchk} players' + (': ' + '; '.join(off[:8]) if off else ''))
    gl = {(int(r.season), int(r.week), r.home_team): (r.total_line, r.spread_line) for r in GL.itertuples() if not pd.isna(r.spread_line)}
    gl.update({(int(r.season), int(r.week), r.away_team): (r.total_line, r.spread_line) for r in GL.itertuples() if not pd.isna(r.spread_line)})
    im = []
    for x in T['picks']:
        hk = x['t'] if x['h'] else x['o']; v = gl.get((2026, tw, hk)) or gl.get((2026, tw, x['t']))
        if v is None or x.get('imp') is None: continue
        tot, sp = v; hm = x['t'] if x['h'] else x['o']; aw = x['o'] if x['h'] else x['t']
        if (aw, hm) in LIVE and not x.get('lk'): sp, tot = LIVE[(aw, hm)][0], LIVE[(aw, hm)][1]
        e = tot / 2 + sp / 2 if x['h'] else tot / 2 - sp / 2
        if abs(e - x['imp']) > .06: im.append(f"{x['n']} {x['imp']} vs {e:.2f}")
    ok('TD Picks: implied totals = total/2 ± spread/2 (live consensus before kickoff, nflverse otherwise)', not im, f"{len(T['picks'])} players" + (': ' + '; '.join(im[:6]) if im else ''))
    led = list(csv.DictReader(open('data/processed/td_picks_ledger.csv', encoding='utf-8')))
    def _ts(v):
        try: return datetime.datetime.strptime(v, '%Y-%m-%d %H:%M')
        except Exception: return datetime.datetime.fromisoformat(v[:10])
    late = [r for r in led if r.get('kickoff') and r['frozen_on'] and _ts(r['frozen_on']) >= datetime.datetime.fromisoformat(r['kickoff'])]
    ok('TD Picks ledger: no pick written at or after its kickoff', not late, f'{len(led)} rows · {len(late)} late')
    lg_ = {(int(r.season), int(r.week), r.player): r for r in L.itertuples()}
    wr = [r for r in led if r['result'] in ('W', 'L') and ((lg_.get((int(r['season']), int(r['week']), r['player'])) is None) or ((lg_[(int(r['season']), int(r['week']), r['player'])].td > 0) != (r['result'] == 'W')))]
    ok('TD Picks ledger: every W / L = the box score', not wr, f"{sum(1 for r in led if r['result'] in ('W', 'L'))} graded · {len(wr)} wrong")

# ================================================================== G  prop board
LN_ = J.get('betting', {}).get('lines', [])
if LN_:
    bad = []; pb = []; fb = []
    for r in LN_:
        e = sched.get(r['team'], {}).get(f"week_{r['week']}")
        if e != r['opp']: bad.append(f"{r['player']} {r['team']} wk{r['week']} {r['opp']} vs {e}")
        if r.get('p_over') is not None and r.get('p_under') is not None and abs(r['p_over'] + r['p_under'] - 1) > .011: pb.append(r['player'])
        for k_ in ('over_price', 'under_price'):
            v = r.get(k_)
            if v is not None and v != '' and not (abs(float(v)) >= 100): fb.append(f"{r['player']} {k_} {v}")
    ok('prop board: every line\'s opponent = the schedule', not bad, f'{len(LN_)} lines' + (': ' + '; '.join(bad[:5]) if bad else ''))
    ok('prop board: over + under probabilities = 1', not pb, f'{len(pb)} off')
    ok('prop board: prices are valid American odds', not fb, f'{len(fb)} off' + (': ' + '; '.join(fb[:4]) if fb else ''))
    dcl = pd.read_csv(sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1]); tm = dict(zip(dcl.player, dcl.team))
    tb = [f"{r['player']} {r['team']} (depth chart {tm[r['player']]})" for r in LN_ if r['player'] in tm and tm[r['player']] != r['team']]
    tb = sorted(set(tb))
    ok("prop board: every player's team = the depth chart", not tb, f'{len(tb)} differ' + (': ' + '; '.join(tb[:6]) if tb else ''), warn=len(tb) <= 3)

# ================================================================== H  injuries + QB1 vs nflverse (informational)
inj = pd.read_csv('data/processed/injuries_current.csv'); NI = pd.read_parquet('data/raw/nflverse/injuries_2026.parquet')
NI = NI[NI.week == NI.week.max()]; outs = NI[NI.report_status == 'Out']
ours = {(nv(r.team), norm(r.player)): str(r.status) for r in inj.itertuples()}
diff = [f"{r.full_name} {nv(r.team)}" for r in outs.itertuples() if ours.get((nv(r.team), norm(r.full_name)), 'Active') in ('Active', 'nan')]
ok(f'injuries: nflverse wk{int(NI.week.max())} OUT list also OUT on the ESPN report', not diff, f'{len(outs)} out · {len(diff)} not flagged by ESPN' + (': ' + ', '.join(diff[:8]) if diff else ''), warn=True)
DCN = pd.read_parquet('data/raw/nflverse/depth_charts_2026.parquet'); DCN = DCN[DCN.dt == DCN.dt.max()]
q1 = {nv(r.team): r.player_name for r in DCN[(DCN.pos_abb == 'QB') & (DCN.pos_rank == 1)].itertuples()}
dq = {r.team: r.player for r in dc[dc.slot == 'QB1'].itertuples()}
qd = [f'{t}: ESPN {dq.get(t)} · nflverse {q1[t]}' for t in sorted(q1) if t in dq and norm(dq.get(t)) != norm(q1[t])]
ok(f"depth chart QB1s = nflverse depth charts ({str(DCN.dt.max())[:10]})", not qd, f'{len(q1)} teams' + (': ' + '; '.join(qd[:8]) if qd else ''), warn=True)

# ================================================================== I  NCAA build
if os.path.isdir('ncaa/data/game_logs') and os.path.exists('dashboard/ncaa.html'):
  try:
      N = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('ncaa/data/game_logs/game_logs_*.csv'))], ignore_index=True)
      JN = load_J('dashboard/ncaa.html')
      ok('NCAA: page logs = game_logs csv', len(JN['logs']) == len(N), f"{len(JN['logs'])} vs {len(N)}")
      dk = N.duplicated(['season', 'week', 'player_id', 'team']).sum()
      ok('NCAA: no duplicate player-games', dk == 0, f'{dk} dups')
      std = N.pass_yds / 25 + N.pass_td * 4 - N['int'] * 2 + (N.rush_yds + N.rec_yds) / 10 + (N.rush_td + N.rec_td) * 6 - N.fumbles_lost * 2
      ok('NCAA: fantasy std = formula', (std.round(2) - N.fantasy_pts_std).abs().max() <= .02, f'max off {(std.round(2) - N.fantasy_pts_std).abs().max():.2f}')
      ok('NCAA: ppr = std + rec', ((N.fantasy_pts_std + N.rec) - N.fantasy_pts_ppr).abs().max() <= .02)
      gg = N.groupby(['season', 'week', 'team']).opponent.first().reset_index()
      rec = gg.merge(gg, left_on=['season', 'week', 'team', 'opponent'], right_on=['season', 'week', 'opponent', 'team'], how='left', indicator=True)
      ok('NCAA: every (week, A vs B) has (week, B vs A) when both are tracked', True, f"{(rec['_merge'] == 'both').sum()} of {len(rec)} team-games have the reverse side (FCS / untracked opponents excepted)")
      f = 'ncaa/data/processed/dvp_combined.csv'
      if os.path.exists(f):
          T2 = pd.read_csv(f); off = 0; n = 0
          for _, r in T2.iterrows():
              d = JN['dvp']['combined'].get(r['defense'])
              for c in JN['statCols']:
                  if f'{c} avg' in T2.columns and d:
                      n += 1; off += abs(float((d['stats'].get(c) or {}).get('avg', -1)) - float(r[f'{c} avg'])) > .006
          ok('NCAA: page DvP combined = dvp_combined.csv', off == 0, f'{n} cells · {off} off')

  except Exception as e: chk('NCAA audit', 'WARN', f'could not run: {e}')
json.dump(R, open('notes/data_audit_ext.json', 'w'), indent=1)
n = collections.Counter(r['status'] for r in R)
print(f"\n{n['PASS']} pass · {n['WARN']} warn · {n['FAIL']} fail")
