"""Layer-1 builder for the non-NFL leagues (NBA / WNBA / NHL) on the RAINMAN framework.
Usage: python3 scripts/sports/build.py nba [nhl wnba]      (default: every league with raw data)
Reads  data/sports/<lg>/raw/*.parquet (fetch_sdv.py) + data/raw/slate_all_*.txt (lines, this week)
Writes data/sports/<lg>/processed/{logs,players,dvp,games,ratings,projections,picks}.csv and dashboard/<lg>.html
Every number traces to the box-score parquets: logs -> DvP by slot (sum of the opposing players at a position, per game)
-> ranks (1 = allows the most) -> projections (his blended average x the opponent's trust-shrunk ratio) -> game model
(team margin ratings + home edge) -> frozen, graded picks vs the DraftKings lines on the slate."""
import os, sys, json, glob, re, math, csv
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from config import LEAGUES
ROOT = os.path.join(os.path.dirname(__file__), '..', '..'); os.chdir(ROOT)
TODAY = pd.Timestamp.today().normalize()
NHL_ABBR = {'LAK': 'LA', 'NJD': 'NJ', 'SJS': 'SJ', 'TBL': 'TB'}   # nhle -> ESPN (the slate / logo world)
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import brand

def toi_min(v):
    try: m, s = str(v).split(':'); return int(m) + int(s) / 60
    except Exception: return np.nan

def load_logs(lg, C):
    frames = []
    for y in C['seasons']:
        f = f'data/sports/{lg}/raw/player_box_{y}.parquet'
        if not os.path.exists(f): continue
        d = pd.read_parquet(f)
        if C['sport'] == 'basketball':
            d = d[d.season_type.isin([2, 3]) & d.minutes.notna()].copy()
            d['stype'] = np.where(d.season_type == 3, 'post', 'reg')
            d = d.rename(columns={'athlete_display_name': 'player', 'athlete_id': 'pid', 'team_abbreviation': 'team', 'opponent_team_abbreviation': 'opp', 'home_away': 'ha'})
            d['slot'] = d.athlete_position_abbreviation.map(C['posmap']).fillna('F')
            d['date'] = pd.to_datetime(d.game_date).dt.strftime('%Y-%m-%d'); d['season'] = y; d['gid'] = d.game_id.astype(str)
            d['ha'] = d.ha.map({'home': 'H', 'away': 'A'}); d['starter'] = d.starter.fillna(False).astype(int)
            d['team_logo'] = d.team_logo; d['team_color'] = d.team_color
        else:
            sch = pd.read_parquet(f'data/sports/{lg}/raw/nhl_schedule_{y}.parquet')
            sch = sch[sch.game_type.isin(['R', 'P'])]
            gm = {str(r.game_id): (r.home_team_abbr, r.away_team_abbr, r.game_type) for r in sch.itertuples()}
            d['gid'] = d.game_id.astype(str); d = d[d.gid.isin(gm)].copy()
            d['opp'] = [gm[g][1] if ha == 'home' else gm[g][0] for g, ha in zip(d.gid, d.home_away)]
            d['stype'] = [('post' if gm[g][2] == 'P' else 'reg') for g in d.gid]
            d = d.rename(columns={'player_name': 'player', 'player_id': 'pid', 'team_abbrev': 'team'})
            d['team'] = d.team.map(lambda t: NHL_ABBR.get(t, t)); d['opp'] = d.opp.map(lambda t: NHL_ABBR.get(t, t))
            d['slot'] = d.position.map(C['posmap']).fillna('W'); d.loc[d.saves.notna() | d.shots_against.notna(), 'slot'] = 'G'; d['ha'] = d.home_away.map({'home': 'H', 'away': 'A'})
            d['date'] = pd.to_datetime(d.game_date).dt.strftime('%Y-%m-%d'); d['season'] = y
            d['toi_min'] = d.toi.map(toi_min); d['starter'] = (d.toi_min >= 12).astype(int)
            d['team_logo'] = ''; d['team_color'] = ''
        for k, lbl, dec, col in C['stats']:
            d[k] = col(d) if callable(col) else d[col]
            d[k] = pd.to_numeric(d[k], errors='coerce')
        frames.append(d[['season', 'stype', 'date', 'gid', 'player', 'pid', 'team', 'opp', 'ha', 'slot', 'starter', 'team_logo', 'team_color'] + [k for k, *_ in C['stats']]])
    L = pd.concat(frames, ignore_index=True).sort_values(['date', 'gid', 'team'])
    L = L[L.team.notna() & L.opp.notna() & ~L.team.isin(['STARS', 'STRIPES', 'WORLD', 'TBD'])]
    return L

def dvp_tables(L, C):
    """{season|'combined': {team: {slot: {stat: {'avg','rank','gp'}}}}} — allowed per game to each slot (sum of the opposing players at that slot)."""
    keys = [k for k, *_ in C['stats']]
    out = {}
    def table(frame, gpw=None):
        per_game = frame.groupby(['opp', 'gid', 'slot'])[keys].sum().reset_index()      # what each defense (opp) allowed in each game, per slot
        gp = frame.groupby('opp').gid.nunique()
        avg = per_game.groupby(['opp', 'slot'])[keys].mean()
        T = {}
        for (team, slot), row in avg.iterrows():
            T.setdefault(team, {})[slot] = {k: {'avg': round(float(row[k]), 3)} for k in keys}
            T[team][slot]['_gp'] = int(gp.get(team, 0))
        return T
    seasons = sorted(L.season.unique())
    for y in seasons:
        out[str(y)] = table(L[L.season == y])
    cur, prior = seasons[-1], (seasons[-2] if len(seasons) > 1 else None)
    # combined: current counts double once it has min_games_current games per team; before that the prior season carries it
    comb = {}
    teams = set(out[str(cur)]) | (set(out[str(prior)]) if prior else set())
    for t in teams:
        comb[t] = {}
        for slot in C['slots']:
            a = out[str(cur)].get(t, {}).get(slot); b = out[str(prior)].get(t, {}).get(slot) if prior else None
            if not a and not b: continue
            gpa = a['_gp'] if a else 0; wa = 2.0 * min(1.0, gpa / C['min_games_current']) if a else 0.0; wb = 1.0 if b else 0.0
            if wa + wb == 0: continue
            comb[t][slot] = {k: {'avg': round(((a[k]['avg'] * wa if a else 0) + (b[k]['avg'] * wb if b else 0)) / (wa + wb), 3)} for k in keys}
            comb[t][slot]['_gp'] = gpa
    out['combined'] = comb
    # ranks (1 = most allowed) + league averages
    for name, T in out.items():
        for slot in C['slots']:
            for k in keys:
                vals = [(t, T[t][slot][k]['avg']) for t in T if slot in T[t]]
                vals.sort(key=lambda x: -x[1])
                for i, (t, v) in enumerate(vals): T[t][slot][k]['rank'] = i + 1
                lg = float(np.mean([v for _, v in vals])) if vals else 0
                for t, _ in vals: T[t][slot][k]['lg'] = round(lg, 3)
    return out, cur, prior

def players_table(L, C, cur, prior):
    keys = [k for k, *_ in C['stats']]
    rows = []
    for (pid, player), g in L.groupby(['pid', 'player']):
        g = g.sort_values('date'); last = g.iloc[-1]
        curg = g[g.season == cur]; prg = g[g.season == prior] if prior else g.iloc[0:0]
        slot = (curg if len(curg) else g).slot.mode().iloc[0]
        r = dict(pid=pid, player=player, team=last.team, slot=slot, gp=len(curg), gp_prior=len(prg), gp_all=len(g), last_date=last.date,
                 starter_rate=round(float((curg if len(curg) else g).starter.mean()), 2))
        for k in keys:
            r[k] = round(float(curg[k].mean()), 3) if len(curg) else None
            r[k + '_prior'] = round(float(prg[k].mean()), 3) if len(prg) else None
            r[k + '_all'] = round(float(g[k].mean()), 3)
            r[k + '_l5'] = round(float(g.tail(5)[k].mean()), 3)
            r[k + '_l10'] = round(float(g.tail(10)[k].mean()), 3)
            r[k + '_sd'] = round(float(g.tail(25)[k].std(ddof=0)), 3) if len(g) > 2 else None
        rows.append(r)
    return pd.DataFrame(rows)

def load_slate(C):
    files = sorted(glob.glob('data/raw/slate_all_*.txt'))
    if not files: return []
    games = []
    for line in open(files[-1], encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if p[1] != C['slate_key'] or p[22] == '1': continue      # preseason rows are ignored
        games.append(dict(eid=p[2], date=p[3], status=p[4], away=p[6], away_name=p[7], away_rec=p[8], away_logo=p[9], home=p[12], home_name=p[13], home_rec=p[14], home_logo=p[15],
                          venue=p[17], tv=p[18], odds=p[19], ou=p[20], neutral=p[23] == '1', note=p[25] if len(p) > 25 else ''))
    return games

def load_schedule(lg, C):
    rows = []
    for y in C['seasons']:
        f = f'data/sports/{lg}/raw/' + C['files']['sched'].format(y=y).split('/')[-1]
        if not os.path.exists(f): continue
        s = pd.read_parquet(f)
        if C['sport'] == 'basketball':
            s = s[s.season_type.isin([2, 3])]
            for r in s.itertuples():
                rows.append(dict(season=y, gid=str(r.game_id), date=str(r.game_date)[:10], dt=str(r.date), away=r.away_abbreviation, home=r.home_abbreviation,
                                 away_score=r.away_score, home_score=r.home_score, done=bool(r.status_type_completed), venue=r.venue_full_name or '', tv=r.broadcast_name or '',
                                 stype='post' if r.season_type == 3 else 'reg'))
        else:
            s = s[s.game_type.isin(['R', 'P'])]
            for r in s.itertuples():
                rows.append(dict(season=y, gid=str(r.game_id), date=str(r.game_date)[:10], dt=str(r.game_time), away=NHL_ABBR.get(r.away_team_abbr, r.away_team_abbr), home=NHL_ABBR.get(r.home_team_abbr, r.home_team_abbr),
                                 away_score=r.away_score, home_score=r.home_score, done=r.game_state in ('OFF', 'FINAL'), venue=r.venue or '', tv='', stype='post' if r.game_type == 'P' else 'reg'))
    S = pd.DataFrame(rows)
    S = S[S.away.notna() & S.home.notna() & ~S.away.isin(['STARS', 'STRIPES', 'WORLD', 'TBD'])]
    return S.sort_values('dt').reset_index(drop=True)

def ratings(S, C, cur, prior):
    """team margin / scoring ratings from finished games: current season weighted up as it accumulates."""
    done = S[S.done & S.home_score.notna()].copy()
    R = {}
    for t in sorted(set(done.away) | set(done.home)):
        g = done[(done.away == t) | (done.home == t)].sort_values('dt')
        pf = np.where(g.home == t, g.home_score, g.away_score).astype(float); pa = np.where(g.home == t, g.away_score, g.home_score).astype(float)
        se = g.season.values
        def agg(mask):
            n = int(mask.sum()); return (float(pf[mask].mean()) if n else None, float(pa[mask].mean()) if n else None, n)
        cpf, cpa, cn = agg(se == cur); ppf, ppa, pn = agg(se == prior) if prior else (None, None, 0)
        wc = 2.0 * min(1.0, cn / C['min_games_current']); wp = 1.0 if pn else 0.0
        if wc + wp == 0: continue
        bpf = ((cpf or 0) * wc + (ppf or 0) * wp) / (wc + wp); bpa = ((cpa or 0) * wc + (ppa or 0) * wp) / (wc + wp)
        l10 = pf[-10:] - pa[-10:]
        R[t] = dict(team=t, gp=cn, pf=round(cpf, 2) if cpf is not None else None, pa=round(cpa, 2) if cpa is not None else None, pf_prior=round(ppf, 2) if ppf is not None else None,
                    pa_prior=round(ppa, 2) if ppa is not None else None, rating=round(bpf - bpa, 3), pace=round(bpf + bpa, 2), l10=round(float(l10.mean()), 2) if len(l10) else None,
                    wins=int((pf > pa)[se == cur].sum()), losses=int((pf < pa)[se == cur].sum()))
    return R

def game_model(games, R, C):
    from math import erf, sqrt
    out = []
    for g in games:
        a, h = R.get(g['away']), R.get(g['home'])
        if not a or not h: out.append(dict(g)); continue
        margin = (h['rating'] - a['rating']) + C['home_edge']            # home − away
        p_home = 0.5 * (1 + erf(margin / (C['margin_sd'] * sqrt(2))))
        total = (h['pace'] + a['pace']) / 2
        m = re.match(r'^(\S+)\s+([+-]?\d+(?:\.\d+)?)$', g.get('odds') or '')
        line = None; ml = None
        if m:
            n = float(m.group(2)); fav = m.group(1)
            if abs(n) >= 100: ml = (fav, n)
            else: line = -abs(n) if fav == g['home'] else abs(n)          # home spread, negative = home favored
        imp_home = None
        if ml:
            p = (-ml[1]) / (-ml[1] + 100) if ml[1] < 0 else 100 / (ml[1] + 100)
            imp_home = p if ml[0] == g['home'] else 1 - p
        out.append(dict(g, model_margin=round(margin, 2), model_total=round(total, 1), p_home=round(p_home, 3), home_line=line, imp_home=round(imp_home, 3) if imp_home is not None else None,
                        home_implied=round((total - margin) / 2 + margin, 1), away_implied=round((total - margin) / 2, 1)))
    return out

def picks(lg, C, games, S):
    """freeze ML / spread / total positions vs the DK line once per game; grade from finished scores."""
    path = f'data/sports/{lg}/processed/picks.csv'
    old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=['type', 'date', 'frozen_on', 'ref', 'game', 'side', 'line', 'model', 'market_ref', 'edge', 'result', 'actual'])
    keys = set(zip(old.type.astype(str), old.ref.astype(str))); new = []        # astype(str): pandas reads ref as int64, the slate carries it as a string, so the dedupe silently missed and re-froze every pick each run
    thr = dict(ml=0.06, spread=2.5 if C['sport'] == 'basketball' else 0.5, total=3.0 if C['sport'] == 'basketball' else 0.45)
    for g in games:
        if 'p_home' not in g or g.get('stype') == 'pre': continue           # no positions on preseason games
        ref = str(g['eid']); gm = f"{g['away']}@{g['home']}"
        def add(t, side, line, model, mref, edge):
            if (t, ref) in keys: return
            keys.add((t, ref)); new.append(dict(type=t, date=g['date'][:10], frozen_on=str(TODAY.date()), ref=ref, game=gm, side=side, line=line, model=model, market_ref=mref, edge=round(edge, 3), result='', actual=''))
        if g.get('imp_home') is not None:
            e = g['p_home'] - g['imp_home']
            if abs(e) >= thr['ml']: add('ML', g['home'] if e > 0 else g['away'], '', g['p_home'] if e > 0 else round(1 - g['p_home'], 3), g['imp_home'] if e > 0 else round(1 - g['imp_home'], 3), abs(e))
        if g.get('home_line') is not None:
            e = g['model_margin'] + g['home_line']                        # model margin vs the spread (home perspective)
            if abs(e) >= thr['spread']: add('ATS', g['home'] if e > 0 else g['away'], g['home_line'], g['model_margin'], g['home_line'], abs(e))
        if g.get('ou'):
            e = g['model_total'] - float(g['ou'])
            if abs(e) >= thr['total']: add('TOTAL', 'Over' if e > 0 else 'Under', float(g['ou']), g['model_total'], float(g['ou']), abs(e))
    allp = pd.concat([old, pd.DataFrame(new)], ignore_index=True) if new else old.copy()
    if len(allp): allp = allp.drop_duplicates(subset=['type', 'ref', 'side'], keep='first').reset_index(drop=True)
    done = {f"{r.away}@{r.home}|{r.date}": r for r in S[S.done & S.home_score.notna()].itertuples()}
    for i, r in allp.iterrows():
        if isinstance(r.result, str) and r.result in ('W', 'L', 'P'): continue
        key = f"{r.game}|{r.date}"; g = done.get(key)
        if g is None: continue
        hs, as_ = float(g.home_score), float(g.away_score); home, away = r.game.split('@')[1], r.game.split('@')[0]
        if r.type == 'ML':
            w = home if hs > as_ else away; allp.at[i, 'result'] = 'W' if w == r.side else 'L'; allp.at[i, 'actual'] = f'{as_:g}-{hs:g}'
        elif r.type == 'ATS':
            cov = (hs - as_) + float(r.line)                                 # home covers if > 0
            res = 'P' if cov == 0 else ('W' if (cov > 0) == (r.side == home) else 'L'); allp.at[i, 'result'] = res; allp.at[i, 'actual'] = hs - as_
        else:
            tot = hs + as_; res = 'P' if tot == float(r.line) else ('W' if (tot > float(r.line)) == (r.side == 'Over') else 'L'); allp.at[i, 'result'] = res; allp.at[i, 'actual'] = tot
    allp.to_csv(path, index=False)
    return allp, len(new)

def projections(P, dvp, C, upcoming, cur):
    """per player on the slate × market: base (season / prior / last-10 blend) × trust-shrunk opponent ratio, with a band."""
    D = dvp['combined']; keys = C['markets']; rows = []
    nxt = {}
    for g in upcoming:
        nxt.setdefault(g['away'], (g['home'], g['date'])); nxt.setdefault(g['home'], (g['away'], g['date']))
    for r in P.itertuples():
        if r.team not in nxt: continue
        opp, date = nxt[r.team]; T = D.get(opp, {}).get(r.slot)
        if r.gp + r.gp_prior < 3: continue
        for k in keys:
            cur_v = getattr(r, k); pr = getattr(r, k + '_prior'); l10 = getattr(r, k + '_l10'); sd = getattr(r, k + '_sd')
            if cur_v is None and pr is None: continue
            wc = min(1.0, r.gp / 15) if cur_v is not None else 0; wp = (1 - wc) if pr is not None else 0
            season = ((cur_v or 0) * wc + (pr or 0) * wp) / (wc + wp) if (wc + wp) else (cur_v if cur_v is not None else pr)
            base = 0.65 * season + 0.35 * l10 if l10 == l10 else season
            if T and T[k]['lg']:
                ratio = T[k]['avg'] / T[k]['lg']; trust = min(1.0, T['_gp'] / 15) * 0.6 if T.get('_gp') else 0.3
                mx = 1 + (ratio - 1) * trust
            else: ratio, mx = 1.0, 1.0
            proj = base * mx; s = sd if sd == sd and sd else 0.35 * max(base, 0.5)
            rows.append(dict(player=r.player, pid=r.pid, team=r.team, opp=opp, date=date, slot=r.slot, market=k, base=round(base, 2), proj=round(proj, 2), mx=round(mx, 3), ratio=round(ratio, 3),
                             opp_rank=T[k]['rank'] if T else None, opp_allowed=T[k]['avg'] if T else None, q10=round(max(0, proj - 1.28 * s), 1), q90=round(proj + 1.28 * s, 1), gp=r.gp, gp_prior=r.gp_prior))
    return pd.DataFrame(rows)

def build(lg):
    C = LEAGUES[lg]; out = f'data/sports/{lg}/processed'; os.makedirs(out, exist_ok=True)
    L = load_logs(lg, C); dvp, cur, prior = dvp_tables(L, C); P = players_table(L, C, cur, prior)
    S = load_schedule(lg, C); R = ratings(S, C, cur, prior); slate = load_slate(C)
    # upcoming games: the slate (lines) merged with the schedule for the next 14 days
    horizon = (TODAY + pd.Timedelta(days=14)).strftime('%Y-%m-%d')
    up = S[(~S.done) & (S.date >= (TODAY - pd.Timedelta(days=1)).strftime('%Y-%m-%d')) & (S.date <= horizon)]
    by = {(g['away'], g['home'], g['date'][:10]): g for g in slate}
    games = []
    for r in up.itertuples():
        g = by.get((r.away, r.home, r.date), {})
        games.append(dict(eid=r.gid, date=g.get('date', r.dt), day=r.date, away=r.away, home=r.home, venue=g.get('venue') or r.venue, tv=g.get('tv') or r.tv, odds=g.get('odds', ''), ou=g.get('ou', ''),
                          away_rec=g.get('away_rec', ''), home_rec=g.get('home_rec', ''), neutral=g.get('neutral', False), note=g.get('note', ''), stype=r.stype))
    seen = {(g['away'], g['home'], g['day']) for g in games}
    for g in slate:                                   # slate games the schedule parquet doesn't carry yet (late adds; preseason is filtered out of the slate)
        d = g['date'][:10]
        if (g['away'], g['home'], d) in seen or d < str(TODAY.date()): continue
        games.append(dict(eid=g['eid'], date=g['date'], day=d, away=g['away'], home=g['home'], venue=g['venue'], tv=g['tv'], odds=g['odds'], ou=g['ou'], away_rec=g['away_rec'], home_rec=g['home_rec'],
                          neutral=g['neutral'], note=g['note'], stype='reg'))
    games.sort(key=lambda g: g['date'])
    games = game_model(games, R, C)
    PK, n_new = picks(lg, C, games, S)
    PJ = projections(P, dvp, C, games, cur)
    # teams (logo / color / name) from the box scores + slate
    teams = {}
    for r in L.drop_duplicates('team').itertuples():
        teams[r.team] = dict(abbr=r.team, logo=r.team_logo or '', color=('#' + r.team_color) if isinstance(r.team_color, str) and r.team_color and not r.team_color.startswith('#') else (r.team_color or ''))
    for g in slate:
        for side in ('away', 'home'):
            t = teams.setdefault(g[side], dict(abbr=g[side], logo='', color=''))
            t['name'] = g[side + '_name']; t['rec'] = g[side + '_rec']
            if not t['logo'] and g[side + '_logo']: t['logo'] = 'https://a.espncdn.com/i/teamlogos/' + g[side + '_logo']
    for t in teams.values():
        if not t['logo']: t['logo'] = f"https://a.espncdn.com/i/teamlogos/{lg}/500/{t['abbr'].lower()}.png"
        t.setdefault('name', t['abbr'])
    # write processed
    keys = [k for k, *_ in C['stats']]
    L.to_csv(f'{out}/logs.csv', index=False); P.to_csv(f'{out}/players.csv', index=False); PJ.to_csv(f'{out}/projections.csv', index=False)
    pd.DataFrame(games).to_csv(f'{out}/games.csv', index=False); pd.DataFrame(R.values()).to_csv(f'{out}/ratings.csv', index=False)
    rows = []
    for name, T in dvp.items():
        for t in T:
            for slot in T[t]:
                for k in keys: rows.append(dict(src=name, team=t, slot=slot, stat=k, avg=T[t][slot][k]['avg'], rank=T[t][slot][k].get('rank'), lg=T[t][slot][k].get('lg'), gp=T[t][slot]['_gp']))
    pd.DataFrame(rows).sort_values(['src', 'team', 'slot'], kind='stable').to_csv(f'{out}/dvp.csv', index=False)   # deterministic order (set iteration is not)
    # payload
    keep = L[L.season >= (prior or cur)] if prior else L
    cols = ['season', 'stype', 'date', 'player', 'pid', 'team', 'opp', 'ha', 'slot', 'starter'] + [k for k in keys if k not in ('pra', 'pr', 'pa', 'ra')]
    logs = keep[cols].copy()
    for k in [c for c in cols if c in keys]: logs[k] = logs[k].round(2)
    # compact payload: whole-number floats serialise as ints (0 not 0.0) — the page stays under GitHub's 10 MB upload cap
    def compact(v): return int(v) if isinstance(v, float) and v == v and v.is_integer() else v
    logs_arr = [[compact(v) for v in row] for row in logs.fillna('').values.tolist()]
    def nz(v): return None if (isinstance(v, float) and math.isnan(v)) else (int(v) if isinstance(v, float) and v.is_integer() else v)
    J = dict(league=lg, label=C['label'], sport=C['sport'], logo=C['logo'], built=str(pd.Timestamp.now())[:16], seasons=sorted(int(x) for x in L.season.unique()), cur=int(cur), prior=int(prior) if prior else None,
             slots=C['slots'], stats=[dict(k=k, label=l, dec=d) for k, l, d, _ in C['stats']], markets=C['markets'], logCols=cols, logs=logs_arr,
             dvp=dvp, teams=teams, ratings=R, games=games, players=[{k: nz(v) for k, v in r.items()} for r in P.to_dict('records')],
             proj=[{k: nz(v) for k, v in r.items()} for r in PJ.to_dict('records')], picks=[{k: nz(v) for k, v in r.items()} for r in PK.to_dict('records')],
             slateDate=(sorted(glob.glob('data/raw/slate_all_*.txt'))[-1][-14:-4] if glob.glob('data/raw/slate_all_*.txt') else ''), rotation=C['rotation'])
    tpl = open('scripts/sport_template.html', encoding='utf-8').read()
    _i = tpl.index('<style>') + 7; _j = tpl.index('</style>')
    _css, _blocks = brand.themed_css(tpl[_i:_j])
    _tc = brand.team_color_css({k: (v.get('color') or '') for k, v in (teams or {}).items()})
    tpl = (tpl[:_i] + _css + tpl[_j:]
           .replace('__BRAND_BOOT__', brand.THEME_BOOT).replace('__BRAND_JS__', '<script>' + brand.THEME_JS + '</script>')
           .replace('__BRAND_MARK__', brand.mascot('counting', 20, 'rmask hdr')).replace('__BRAND_SWITCH__', brand.theme_switch_html()))
    tpl = tpl.replace('__BRAND_CSS__', brand.THEME_CSS + brand.alias_css('alt') + brand.SWITCH_CSS
                      + '.brand .rmask{vertical-align:-5px;margin-right:3px}.right .rmsw{margin-left:8px}' + _blocks + _tc)
    html = tpl.replace('__DATA__', json.dumps(J, separators=(',', ':'), default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else (o.item() if hasattr(o, 'item') else str(o))))
    open(f'dashboard/{lg}.html', 'w', encoding='utf-8').write(html)
    print(f"{lg}: {len(L):,} log rows ({', '.join(str(s) for s in J['seasons'])}) · {len(P)} players · {len(games)} games in the next 14 days ({sum(1 for g in games if g.get('odds'))} with lines) · {len(PJ)} projections · picks {len(PK)} (+{n_new}) · dashboard/{lg}.html {os.path.getsize(f'dashboard/{lg}.html') // 1024} KB")

if __name__ == '__main__':
    for lg in (sys.argv[1:] or [l for l in LEAGUES if glob.glob(f'data/sports/{l}/raw/player_box_*.parquet')]):
        build(lg)
