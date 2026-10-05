"""Player <-> game connections for every 2026 game: homecomings (birthplace near the venue), college-town returns
(alma mater campus near the venue), home-state games, revenge games (facing a team he played for in 2024-25 or the
team that drafted him) and birthday games.

Inputs : data/raw/espn_birthplaces_*.txt (ESPN athlete birthPlace), data/raw/colleges_espn.txt + colleges_venues.txt
         (campus city), data/raw/nfl_venues.csv (stadium coords), data/raw/nflverse/games.csv (stadium per game),
         nflverse rosters 2024-26 (espn_id, team history, draft club, birth date), depth chart + 2026 game logs (who plays).
Geocoding: geonamescache (GeoNames places with population >= 500, offline) — city + state; unresolved = no distance.
Output : data/processed/connections_2026.csv  week, game, player, team, opp, type, detail, miles
         data/processed/player_geo.csv         player, birthplace, b_lat, b_lon
Players per game: the actual 2026 game log for weeks already played, the latest depth chart for upcoming weeks.
"""
import os, re, glob, math
import pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
try:
    import geonamescache
except ImportError:
    raise SystemExit('build_connections: geonamescache not installed (pip install geonamescache) — keeping existing connections_2026.csv')

NEAR = 100      # miles: homecoming / college-town radius
CLOSE = 50
gc = geonamescache.GeonamesCache(min_city_population=500)
norm = lambda s: re.sub(r'[^a-z]', '', str(s).lower().replace('saint ', 'st').replace('st. ', 'st').replace('fort ', 'ft'))
IDX = {}
for c in gc.get_cities().values():
    key = (c['countrycode'], c['admin1code'] if c['countrycode'] == 'US' else '')
    for n in {c['name'], *[a for a in c.get('alternatenames', []) if a.isascii()][:6]}:
        k = key + (norm(n),)
        if k not in IDX or c['population'] > IDX[k][2]: IDX[k] = (c['latitude'], c['longitude'], c['population'])
CC = {'USA': 'US', 'Canada': 'CA', 'Australia': 'AU', 'Germany': 'DE', 'England': 'GB', 'Mexico': 'MX', 'Nigeria': 'NG'}
FIX = {('inlandempire', 'CA'): 'riverside', ('longisland', 'NY'): 'hempstead', ('fthood', 'TX'): 'killeen',
       ('dlo', 'MS'): 'mendenhall', ('anaheimhills', 'CA'): 'anaheim', ('dania', 'FL'): 'daniabeach',
       ('capistranobeach', 'CA'): 'danapoint', ('pacoima', 'CA'): 'losangeles', ('sanysidro', 'CA'): 'sandiego',
       ('ellenwood', 'GA'): 'stockbridge', ('tiger', 'GA'): 'clayton', ('chesterfield', 'MI'): 'newbaltimore',
       ('aylett', 'VA'): 'westpoint', ('coldbrook', 'NY'): 'herkimer', ('mountenterprise', 'TX'): 'henderson'}  # nearest GeoNames place
def geo(city, state, country='USA'):
    if not city: return None
    cc = CC.get(country, '')
    n = norm(city); n = FIX.get((n, state), n)
    for k in [(cc, state if cc == 'US' else '', n), (cc, '', n)]:
        if k in IDX: return IDX[k][:2]
    if cc == 'US':  # last resort: best match in any state of the same name prefix
        cands = [v for k, v in IDX.items() if k[0] == 'US' and k[1] == state and k[2].startswith(n[:6])]
        if cands: return max(cands, key=lambda v: v[2])[:2]
    return None
def miles(a, b):
    if not a or not b: return None
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))

# --- players: ESPN birthplace via espn_id; college; team history; draft club
R = {y: pd.read_parquet(f'data/raw/nflverse/roster_{y}.parquet', columns=['full_name', 'pfr_id', 'espn_id', 'team', 'college', 'draft_club', 'birth_date'])
     for y in (2024, 2025, 2026)}
for y in R: R[y]['team'] = R[y].team.replace({'LA': 'LAR'})
allR = pd.concat([R[2026], R[2025], R[2024]])
bp = {}
for f in sorted(glob.glob('data/raw/espn_birthplaces_*.txt')):
    for line in open(f, encoding='utf-8'):
        if line.startswith('#'): continue
        i, c, s, co = (line.rstrip('\n').split('|') + ['', '', ''])[:4]
        if c: bp[i] = (c, s, co)
S = {}
for line in open('data/raw/colleges_espn.txt', encoding='utf-8'):
    if line.startswith('#'): continue
    f = line.rstrip('\n').split('|'); S[re.sub(r'\s+', ' ', f[0]).strip()] = (f[1], f[2])
V = {}
for line in open('data/raw/colleges_venues.txt', encoding='utf-8'):
    if line.startswith('#'): continue
    f = line.rstrip('\n').split('|'); V[f[0]] = (f[2], f[3])
venue = pd.read_csv('data/raw/nfl_venues.csv').set_index('stadium')

dc = pd.read_csv(sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1])
L = pd.concat([pd.read_csv(f) for f in glob.glob('data/game_logs/game_logs_*.csv')])
L26 = L[L.season == 2026]
by_name = allR.dropna(subset=['full_name']).drop_duplicates('full_name').set_index('full_name')
by_id = allR.dropna(subset=['pfr_id']).drop_duplicates('pfr_id').set_index('pfr_id')
nn = lambda n: re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', '', str(n).lower()))
by_norm = {nn(k): k for k in by_name.index}
ALIAS = {'Hollywood Brown': 'Marquise Brown'}
def rrow(name, pid=None):
    if pid is not None and pid in by_id.index: return by_id.loc[pid]
    n = ALIAS.get(name, name)
    if nn(n) in by_norm and n not in by_name.index: n = by_norm[nn(n)]
    if n in by_name.index: r = by_name.loc[n].copy(); r['full_name'] = n; return r
    return None

P = {}   # player -> dict(birth, bgeo, college, cgeo, past teams, draft club, bday)
def info(name, pid=None):
    if name in P: return P[name]
    r = rrow(name, pid); d = {'birth': '', 'bgeo': None, 'college': '', 'cgeo': None, 'past': {}, 'draft': '', 'bday': ''}
    if r is not None:
        b = bp.get(str(r.espn_id).split('.')[0]) if pd.notna(r.espn_id) else None
        if b: d['birth'] = f"{b[0]}, {b[1] or b[2]}"; d['bgeo'] = geo(*b)
        if isinstance(r.college, str):
            key = re.sub(r'\s+', ' ', r.college.split(';')[0]).strip()
            if key in S:
                d['college'] = S[key][1]; loc = V.get(S[key][0]) or V.get(S[key][1])
                if loc: d['cgeo'] = geo(loc[0], loc[1], 'Canada' if loc[1] == 'ON' else 'USA'); d['ccity'] = f'{loc[0]}, {loc[1]}'
        for y in (2024, 2025):
            t = R[y][(R[y].full_name == r.full_name) & R[y].team.notna()]
            if len(t): d['past'][y] = t.team.iloc[-1]
        d['draft'] = r.draft_club.replace('LA', 'LAR') if isinstance(r.draft_club, str) and r.draft_club == 'LA' else (r.draft_club if isinstance(r.draft_club, str) else '')
        d['bday'] = str(r.birth_date)[:10] if pd.notna(r.birth_date) else ''
    P[name] = d; return d

G = pd.read_csv('data/raw/nflverse/games.csv')
G = G[(G.season == 2026) & (G.game_type == 'REG')].copy()
for c in ('away_team', 'home_team'): G[c] = G[c].replace({'LA': 'LAR'})
played = set(L26.week.unique())
rows = []
for g in G.itertuples():
    vg = venue.loc[g.stadium] if g.stadium in venue.index else None
    vgeo = (float(vg.lat), float(vg.lon)) if vg is not None else None
    vname = f"{g.stadium} ({vg.city}{', ' + vg.state if isinstance(vg.state, str) and vg.state else ''})" if vg is not None else g.stadium
    key = f'{g.away_team}@{g.home_team}'
    for team, opp in ((g.away_team, g.home_team), (g.home_team, g.away_team)):
        if g.week in played:
            plist = L26[(L26.week == g.week) & (L26.team == team)][['player', 'player_id']].drop_duplicates('player').values.tolist()
        else:
            plist = [[p, None] for p in dc[dc.team == team].player.unique()]
        for name, pid in plist:
            d = info(name, pid)
            add = lambda t, det, mi=None: rows.append(dict(week=g.week, game=key, player=name, team=team, opp=opp, type=t, detail=det,
                                                           miles=round(mi) if mi is not None else '', venue=g.stadium))
            mb = miles(d['bgeo'], vgeo)
            if mb is not None and mb <= NEAR:
                add('homecoming', f"born in {d['birth']} — {round(mb)} mi from {vname}", mb)
            elif vg is not None and d['birth'] and isinstance(vg.state, str) and vg.state and d['birth'].endswith(', ' + vg.state):
                add('home state', f"born in {d['birth']} — home-state game at {vname}", mb)
            mc = miles(d['cgeo'], vgeo)
            if mc is not None and mc <= NEAR:
                add('college town', f"{d['college']} campus ({d.get('ccity', '')}) is {round(mc)} mi from {vname}", mc)
            for y, t in sorted(d['past'].items(), reverse=True):
                if t == opp and t != team:
                    add('revenge', f"faces {opp}, his team in {y}"); break
            if d['draft'] and d['draft'] == opp and opp not in d['past'].values() and d['draft'] != team:
                add('revenge', f"faces {opp}, the team that drafted him")
            if d['bday'] and isinstance(g.gameday, str) and d['bday'][5:] == g.gameday[5:]:
                add('birthday', f"plays on his birthday ({g.gameday}) — turns {int(g.gameday[:4]) - int(d['bday'][:4])}")
out = pd.DataFrame(rows).drop_duplicates(['week', 'game', 'player', 'type', 'detail'])
out.to_csv('data/processed/connections_2026.csv', index=False)
pg = pd.DataFrame([dict(player=k, birthplace=v['birth'], b_lat=v['bgeo'][0] if v['bgeo'] else '', b_lon=v['bgeo'][1] if v['bgeo'] else '',
                        college=v['college'], college_city=v.get('ccity', '')) for k, v in P.items()])
pg.to_csv('data/processed/player_geo.csv', index=False)
nb = sum(1 for v in P.values() if v['birth']); ng = sum(1 for v in P.values() if v['bgeo'])
print(f"connections_2026.csv: {len(out)} rows · {out.type.value_counts().to_dict()} · players {len(P)} (birthplace {nb}, geocoded {ng})")
miss = sorted({v['birth'] for v in P.values() if v['birth'] and not v['bgeo']})
if miss: print('  birthplaces not geocoded:', miss)
