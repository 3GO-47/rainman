"""First TD scorer layer -> data/processed/first_td.json (embedded by build_dashboard.py as J.firstTd).

Source of truth for history: nflverse play-by-play (data/raw/nflverse/pbp_slim_{season}.parquet), every touchdown play with the
scorer's gsis id (receiver on a pass TD, rusher on a rush TD; defensive / special-teams scores carry no id and are logged as the
scoring team's D/ST). A game's FIRST TD = the earliest touchdown by game clock; each team's first TD is also kept.
Names come from the season roster parquet; the scorer's depth slot that week comes from data/game_logs (never re-slotted).

Board for the live week: P(player scores the game's first TD) = P(his team scores the game's first TD) x his share of his team's
anytime-TD chances (the TD Picks model), where P(team first) = team implied points / (both teams' implied points). That is a proxy,
not a fitted model -- the walk-forward check below says how often the top pick per game was right, so the tab can say so.
Prices: Kalshi FIRSTTD markets (data/processed/kalshi_markets.csv); The Odds API's first-TD market is not pulled.
"""
import csv, glob, json, os, re, unicodedata, datetime
import pandas as pd, numpy as np

P = 'data/processed/'
OUT = P + 'first_td.json'
SEASONS = [int(re.search(r'(\d{4})', f).group(1)) for f in sorted(glob.glob('data/raw/nflverse/pbp_slim_*.parquet'))]
TEAM = {'LA': 'LAR'}
def nrm(n): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', str(n)).encode('ascii', 'ignore').decode().lower().replace(' jr', '').replace(' sr', '').replace(' iii', '').replace(' ii', ''))
def amer(p):
    if p is None or p <= 0 or p >= 1: return None
    return int(round(-100 * p / (1 - p))) if p >= .5 else int(round(100 * (1 - p) / p))

# ---------- names ----------
names = {}
for s in SEASONS:
    f = f'data/raw/nflverse/roster_{s}.parquet'
    if os.path.exists(f):
        r = pd.read_parquet(f, columns=['gsis_id', 'full_name', 'position']).dropna(subset=['gsis_id']).drop_duplicates('gsis_id')
        for g, n, pos in r.itertuples(index=False): names[g] = (n, pos)

# ---------- game-log slots: (season, week, team, nrm(name)) -> slot ----------
slots = {}
for s in SEASONS:
    f = f'data/game_logs/game_logs_{s}.csv'
    if not os.path.exists(f): continue
    for r in csv.DictReader(open(f, encoding='utf-8')):
        slots[(int(r['season']), int(r['week']), r['team'], nrm(r['player']))] = r['slot']

# ---------- every TD, every game ----------
firsts = []        # game-first: one per game
tfirsts = []       # team-first: one per team per game
for s in SEASONS:
    d = pd.read_parquet(f'data/raw/nflverse/pbp_slim_{s}.parquet')
    td = d[d.touchdown == 1].copy()
    td['clock'] = td.game_seconds_remaining.fillna(-1)
    td = td.sort_values(['game_id', 'clock'], ascending=[True, False])
    def row(x):
        off = (x.pass_touchdown == 1) or (x.rush_touchdown == 1)
        scorer_team = TEAM.get(x.posteam, x.posteam) if off else TEAM.get(x.defteam, x.defteam)
        gid = x.receiver_id if x.pass_touchdown == 1 else (x.rusher_id if x.rush_touchdown == 1 else None)
        nm, pos = names.get(gid, (None, None)) if gid else (None, None)
        if not nm: nm, pos = f'{scorer_team} D/ST', 'D/ST'
        allowed = TEAM.get(x.defteam, x.defteam) if off else TEAM.get(x.posteam, x.posteam)
        sl = slots.get((int(x.season), int(x.week), scorer_team, nrm(nm))) or ('D/ST' if pos == 'D/ST' else '')
        secs = int(x.game_seconds_remaining) if pd.notna(x.game_seconds_remaining) else None
        return dict(season=int(x.season), week=int(x.week), game=x.game_id, team=scorer_team, vs=allowed, player=nm, pos=pos or '', slot=sl,
                    how='pass' if x.pass_touchdown == 1 else 'rush' if x.rush_touchdown == 1 else 'def/st', qtr=int(x.qtr) if pd.notna(x.qtr) else None,
                    clock=secs, home=bool(x.posteam == x.game_id.split('_')[-1]) if off else bool(x.defteam == x.game_id.split('_')[-1]))
    for gid_, g in td.groupby('game_id', sort=False):
        firsts.append(row(g.iloc[0]))
        seen = set()
        for x in g.itertuples():
            r = row(x)
            if r['team'] in seen: continue
            seen.add(r['team']); tfirsts.append(r)
F = pd.DataFrame(firsts); TF = pd.DataFrame(tfirsts)

# ---------- summaries ----------
def dist(df, key):
    c = df[key].replace('', 'other').value_counts(); n = int(c.sum())
    return {k: [int(v), round(v / n, 3)] for k, v in c.items()} if n else {}
cur = max(SEASONS)
by_slot = {str(s): dist(F[F.season == s], 'slot') for s in SEASONS}; by_slot['all'] = dist(F, 'slot')
by_how = {str(s): dist(F[F.season == s], 'how') for s in SEASONS}
home_first = {str(s): round(float((F[F.season == s].home).mean()), 3) for s in SEASONS}
by_qtr = {str(s): dist(F[F.season == s].assign(q=lambda x: x.qtr.fillna(0).astype(int).astype(str)), 'q') for s in SEASONS}
# which slot scores first AGAINST each defense (game-first and team-first)
def_allow = {}
for s in SEASONS:
    for vs, g in TF[TF.season == s].groupby('vs'):
        def_allow.setdefault(str(s), {})[vs] = dict(n=int(len(g)), slot=dist(g, 'slot'), how=dist(g, 'how'))
# each offense: who scores its first TD
off_first = {}
for s in SEASONS:
    for t, g in TF[TF.season == s].groupby('team'):
        top = g.player.value_counts().head(5)
        off_first.setdefault(str(s), {})[t] = dict(n=int(len(g)), slot=dist(g, 'slot'), players=[[k, int(v)] for k, v in top.items()])
# players: game-first and team-first counts per season
players = {}
for s in SEASONS:
    gf = F[F.season == s].groupby(['player', 'team']).size(); tf = TF[TF.season == s].groupby(['player', 'team']).size()
    for (p, t), v in tf.items():
        players.setdefault(p, {}).setdefault(str(s), {}).update(team=t, team_first=int(v), game_first=int(gf.get((p, t), 0)))

# ---------- the walk-forward check: top pick per game by the proxy model, weeks 2025-1 .. ----------
GL = pd.read_csv(P + 'game_lines.csv')
imp = {}
for g in GL.itertuples():
    if pd.isna(g.total_line) or pd.isna(g.spread_line): continue
    h = g.total_line / 2 + g.spread_line / 2; a = g.total_line - h
    imp[(int(g.season), int(g.week), g.home_team)] = (h, a, g.game_id); imp[(int(g.season), int(g.week), g.away_team)] = (a, h, g.game_id)
wf = pd.read_csv(P + 'td_picks_wf.csv') if os.path.exists(P + 'td_picks_wf.csv') else pd.DataFrame()
check = []
if len(wf):
    wf['team'] = wf.team.map(lambda t: TEAM.get(t, t))
    for (s, w), g in wf.groupby(['season', 'week']):
        tsum = g.groupby('team').p.sum()
        rows = []
        for r in g.itertuples():
            k = (int(s), int(w), r.team)
            if k not in imp or tsum.get(r.team, 0) <= 0: continue
            mine, theirs, gid = imp[k]
            pt = mine / (mine + theirs) if mine + theirs > 0 else .5
            rows.append((gid, r.player, r.team, pt * r.p / tsum[r.team]))
        if not rows: continue
        R = pd.DataFrame(rows, columns=['game', 'player', 'team', 'pf'])
        top = R.sort_values('pf', ascending=False).groupby('game').head(1)
        actual = F[(F.season == s) & (F.week == w)].set_index('game')
        hit = 0; n = 0; team_hit = 0
        for t in top.itertuples():
            if t.game not in actual.index: continue
            n += 1; a = actual.loc[t.game]
            if nrm(a.player) == nrm(t.player): hit += 1
            if a.team == t.team: team_hit += 1
        if n: check.append(dict(season=int(s), week=int(w), games=n, hit=hit, team_hit=team_hit, top_p=round(float(top.pf.mean()), 3)))
wf_tot = dict(games=sum(c['games'] for c in check), hit=sum(c['hit'] for c in check), team_hit=sum(c['team_hit'] for c in check))

# ---------- the live board ----------
tdp = json.load(open(P + 'td_picks.json')) if os.path.exists(P + 'td_picks.json') else {}
week = int(tdp.get('week') or 0)
kal = pd.read_csv(P + 'kalshi_markets.csv') if os.path.exists(P + 'kalshi_markets.csv') else pd.DataFrame()
kal = kal[kal.market == 'first_td'] if len(kal) else kal
kmap = {}
for r in kal.itertuples():
    if pd.isna(r.player): continue
    kmap[(int(r.week), nrm(r.player))] = dict(p=float(r.p_mid) if pd.notna(r.p_mid) else None, bid=r.p_bid, ask=r.p_ask, vol=int(r.volume) if pd.notna(r.volume) else 0, game=f'{r.away}@{r.home}')
board = []
picks = tdp.get('picks') or []
tsum = {}
for x in picks: tsum[x['t']] = tsum.get(x['t'], 0) + (x.get('p') or 0)
for x in picks:
    t, o = x['t'], x['o']; mine = x.get('imp'); theirs = next((y.get('imp') for y in picks if y['t'] == o and y.get('imp') is not None), None)
    pt = (mine / (mine + theirs)) if mine and theirs else .5
    share = (x.get('p') or 0) / tsum[t] if tsum.get(t) else 0
    pf = pt * share
    k = kmap.get((week, nrm(x['n'])), {})
    hist = players.get(x['n'], {})
    board.append(dict(player=x['n'], team=t, opp=o, home=bool(x.get('h')), slot=x.get('s'), pos=x.get('pos'), inj=x.get('inj'), ko=x.get('ko'),
                      p_any=x.get('p'), p_team=round(pt, 3), share=round(share, 3), p_first=round(pf, 4), fair=amer(pf),
                      kalshi=k.get('p'), kalshi_fair=amer(k.get('p')) if k.get('p') else None, edge=round(pf - k['p'], 4) if k.get('p') is not None else None, vol=k.get('vol'),
                      first_cur=(hist.get(str(cur)) or {}).get('game_first', 0), tfirst_cur=(hist.get(str(cur)) or {}).get('team_first', 0),
                      first_prev=sum((hist.get(str(s)) or {}).get('game_first', 0) for s in SEASONS if s != cur),
                      tier=x.get('tier'), why=x.get('why'), lk=x.get('lk'), res=x.get('res')))
board.sort(key=lambda b: -b['p_first'])

# results by week (so the tab can grade the week picked up top)
results = {}
for r in F.itertuples():
    results.setdefault(str(r.season), {}).setdefault(str(r.week), []).append(dict(game=r.game, player=r.player, team=r.team, vs=r.vs, slot=r.slot, how=r.how, qtr=r.qtr, clock=r.clock, home=r.home))
tresults = {}
for r in TF.itertuples():
    tresults.setdefault(str(r.season), {}).setdefault(str(r.week), []).append(dict(game=r.game, player=r.player, team=r.team, vs=r.vs, slot=r.slot, how=r.how, qtr=r.qtr, clock=r.clock))

out = dict(built=datetime.date.today().isoformat(), seasons=SEASONS, week=week, by_slot=by_slot, by_how=by_how, home_first=home_first, by_qtr=by_qtr,
           def_allow=def_allow, off_first=off_first, players=players, results=results, tresults=tresults, board=board, check=check, wf=wf_tot,
           kalshi_n=int(len(kal[kal.week == week])) if len(kal) else 0,
           note='P(first) = team implied share x his share of the team\'s anytime-TD chances; prices are Kalshi mid; the Odds API first-TD market is not pulled')
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print(f'first_td.json: {len(F)} games with a first TD across {SEASONS} · week {week} board {len(board)} players · Kalshi first-TD markets this week {out["kalshi_n"]} · '
      f'walk-forward top pick per game {wf_tot["hit"]}/{wf_tot["games"]} right ({(100*wf_tot["hit"]/wf_tot["games"]) if wf_tot["games"] else 0:.1f}%), team right {wf_tot["team_hit"]}/{wf_tot["games"]}')
