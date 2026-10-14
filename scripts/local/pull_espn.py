"""Local ESPN pulls (public JSON APIs, no key, no browser) — Python ports of the Chrome recipes in notes/scrape_recipe.md.
Each sub-command writes the same raw file the recipe wrote, so every downstream script is unchanged:
  depth  -> data/raw/espn_depth_<today>.txt   (TEAM|POSROW|DEPTH|NAME|TAG; core depthcharts + roster injuries)
  props  -> data/raw/props_2026_wk<W>_<today>.txt (GM| / PB| DraftKings player props, provider 100)
  slate  -> data/raw/slate_all_<today>.txt     (every league's next 8 days, G| rows; preseason rows dropped)
  ncaa   -> ncaa/data/raw/espn_lines_2026_<today>.txt (GL| current-week scoreboard + pickcenter closes for played weeks)
Usage: python scripts/local/pull_espn.py depth|props|slate|ncaa [...]"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get, get_json, log, write_lines, TODAY, TODAY_S, ESPN_NFL

SITE = 'https://site.api.espn.com/apis/site/v2/sports'
CORE = 'https://sports.core.api.espn.com/v2/sports'
TAG = {'Questionable': 'Q', 'Doubtful': 'D', 'Out': 'O', 'Injured Reserve': 'IR', 'Physically Unable to Perform': 'PUP', 'Suspension': 'SUSP',
       'Suspended': 'SUSP', 'Non-Football Injury': 'NFI', 'Non Football Injury': 'NFI', 'Day-To-Day': ''}

def season_year():
    return TODAY.year if TODAY.month >= 3 else TODAY.year - 1

# ---------------------------------------------------------------- depth charts
# ESPN retired the core-API depthcharts endpoint (every season now answers {"error":{"code":404}} — first seen
# 2026-10-08, confirmed against 2025 too). The team depth page is server-rendered and carries the same data as
# JSON in window['__espnfitt__'] -> page.content.depth.dethTeamGroups: one group per unit (offense, defense,
# special teams), each a list of rows [POS, athlete, athlete, ...] in depth order, every athlete tagged with
# its injury codes. The offense group is the one that starts with QB. Output format is unchanged:
# TEAM|POSROW|DEPTH|NAME|TAG, WR rows numbered WR1..WR3 in page order. An empty pull is never written —
# the old 0-row snapshots were what starved build_depth_chart — it just returns None and says so.
WEB = 'https://www.espn.com/nfl/team/depth/_/name'
INJ = {'P': '', 'Q': 'Q', 'D': 'D', 'O': 'O', 'IR': 'IR', 'PUP': 'PUP', 'SUS': 'SUSP', 'SUSP': 'SUSP', 'NFI': 'NFI'}
# espn.com serves the server-rendered __espnfitt__ blob to document requests; Accept: */* gets a client-rendered shell.
HTML_HDR = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none', 'Sec-Fetch-User': '?1', 'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}
NFLV = 'https://github.com/nflverse/nflverse-data/releases/download'

def depth_nflverse():
    """Browser-free depth charts: nflverse mirrors the same ESPN depth chart daily (~15:00Z) as depth_charts_{season}.parquet,
    with the same names, rows (pos_slot 1/2/8 = the WR1/WR2/WR3 rows) and order (pos_rank). Tags: roster status RES/PUP/NON/SUS
    -> IR/PUP/NFI/SUSP (long-term, always current), plus the week's injury report (Out/Doubtful/Questionable -> O/D/Q) once it
    exists for the UPCOMING week (on Tuesday the newest report is last week's, so it is not applied). Writes the same
    team|row|depth|name|tag lines the ESPN page gives, so build_depth_chart.py is unchanged."""
    import pandas as pd
    season = TODAY.year if TODAY.month >= 3 else TODAY.year - 1
    os.makedirs('data/raw/nflverse', exist_ok=True)
    files = {}
    for rel, name in (('depth_charts', 'depth_charts'), ('rosters', 'roster'), ('injuries', 'injuries')):
        dest = f'data/raw/nflverse/{name}_{season}.parquet'
        try:
            b = get(f'{NFLV}/{rel}/{name}_{season}.parquet', binary=True, timeout=120)
            if len(b) > 100: open(dest, 'wb').write(b)
        except Exception as e:
            log(f'  nflverse {name}_{season}: {str(e)[:70]} — using the cached file if there is one')
        if os.path.exists(dest): files[name] = dest
    if 'depth_charts' not in files:
        log('depth (nflverse): no depth_charts parquet — NOT writing a snapshot; the last good one stands'); return None
    d = pd.read_parquet(files['depth_charts'])
    asof = str(d.dt.max())
    d = d[(d.dt == d.dt.max()) & (d.pos_grp == '3WR 1TE') & d.pos_abb.isin(['QB', 'RB', 'WR', 'TE', 'FB'])].copy()
    TEAM = {'LA': 'LAR'}                                   # nflverse -> ESPN/RAINMAN codes (everything else already matches)
    d['team'] = d.team.map(lambda t: TEAM.get(t, t))
    d['gsis'] = d.gsis_id.astype(str)
    tag = {}
    try:
        played = int(pd.read_csv(f'data/game_logs/game_logs_{season}.csv', usecols=['week']).week.max())
    except Exception:
        played = 0
    if 'injuries' in files:
        i = pd.read_parquet(files['injuries'], columns=['team', 'week', 'gsis_id', 'report_status'])
        wk = int(i.week.max())
        if wk > played:
            rs = {'Out': 'O', 'Doubtful': 'D', 'Questionable': 'Q'}
            n = 0
            for _, x in i[i.week == wk].iterrows():
                t = rs.get(str(x.report_status))
                if t: tag[str(x.gsis_id)] = t; n += 1
            log(f'  injury report week {wk}: {n} players tagged O/D/Q')
        else:
            log(f'  newest injury report is week {wk} (already played) — not applied; IR/PUP from the roster only')
    if 'roster' in files:
        r = pd.read_parquet(files['roster'], columns=['gsis_id', 'status', 'week'])
        r = r[r.week == r.week.max()]
        st = {'RES': 'IR', 'PUP': 'PUP', 'NON': 'NFI', 'SUS': 'SUSP'}
        for _, x in r.iterrows():
            t = st.get(str(x.status))
            if t: tag[str(x.gsis_id)] = t                    # long-term status outranks the weekly report
    lines = []
    for team, T in d.groupby('team'):
        for pos in ('QB', 'RB', 'WR', 'TE', 'FB'):
            P = T[T.pos_abb == pos]
            if P.empty: continue
            slots = sorted(P.pos_slot.unique()) if pos == 'WR' else [None]
            for k, sl in enumerate(slots, 1):
                rows = (P[P.pos_slot == sl] if sl is not None else P).sort_values('pos_rank')
                label = f'WR{k}' if pos == 'WR' else pos
                for dep, (_, x) in enumerate(rows.iterrows(), 1):
                    lines.append('|'.join([team, label, str(dep), str(x.player_name), tag.get(x.gsis, '')]))
    nteams = len({l.split('|')[0] for l in lines})
    if nteams < 24:
        log(f'depth (nflverse): only {nteams} teams ({len(lines)} rows) — NOT writing a snapshot; the last good one stands'); return None
    out = f'data/raw/espn_depth_{TODAY_S}.txt'
    write_lines(out, lines)
    log(f'depth: {len(lines)} rows / {nteams} teams from nflverse (ESPN chart as of {asof}) -> {out}')
    return out

def depth():
    lines = []
    for team in ESPN_NFL:
        try:
            html = get(f'{WEB}/{team.lower()}', pace=1.0, headers=HTML_HDR)
            m = re.search(r"window\['__espnfitt__'\]\s*=\s*(\{.*?\});\s*</script>", html, re.S)
            if not m: raise ValueError('no __espnfitt__ blob')
            groups = json.loads(m.group(1))['page']['content']['depth']['dethTeamGroups']
            off = next((g for g in groups if g.get('rows') and g['rows'][0] and g['rows'][0][0] == 'QB'), None)
            if not off: raise ValueError('no offense group')
            wr = 0
            for row in off['rows']:
                pos = row[0]
                if pos not in ('QB', 'RB', 'WR', 'TE', 'FB'): continue
                if pos == 'WR': wr += 1
                label = f'WR{wr}' if pos == 'WR' else pos
                for d, a in enumerate(row[1:], 1):
                    nm = (a or {}).get('name') or (a or {}).get('displayName') or ''
                    if not nm: continue
                    tag = ''
                    for code in (a.get('injuries') or []):
                        c = code if isinstance(code, str) else (code or {}).get('abbreviation', '')
                        tag = INJ.get(c, c) or tag
                    lines.append('|'.join([team, label, str(d), nm, tag]))
        except Exception as e:
            log(f'  {team}: depth failed {str(e)[:80]}')
    nteams = len({l.split('|')[0] for l in lines})
    if nteams < 24:
        log(f'depth: only {nteams} teams parsed from espn.com ({len(lines)} rows) — falling back to the nflverse mirror')
        return depth_nflverse()
    out = f'data/raw/espn_depth_{TODAY_S}.txt'
    write_lines(out, lines)
    log(f'depth: {len(lines)} rows / {nteams} teams -> {out}')
    return out

# ---------------------------------------------------------------- DraftKings props (ESPN odds provider 100)
def props(week=None):
    # The whole-season scoreboard (dates=YYYY) is calendar-year and capped at 100 events, so on 2026-10-10 it
    # answered with January's week 18. Ask the live scoreboard instead; if every game it shows is final we are
    # between weeks and the next one is the one to price. propBets itself has been answering empty since ESPN
    # retired its core API in Oct 2026 — the Odds API (fetch_odds_api.py) is the live props source now; this
    # stays as a probe and writes nothing when it finds nothing, so build_props never sees a junk file.
    y = season_year()
    if not week:
        sb0 = get_json(f'{SITE}/football/nfl/scoreboard', pace=1.0)
        week = (sb0.get('week') or {}).get('number')
        ev0 = sb0.get('events') or []
        if week and ev0 and all(((e.get('status') or {}).get('type') or {}).get('completed') for e in ev0): week += 1
    if not week: log('props: no current week on the scoreboard'); return None
    sb = get_json(f'{SITE}/football/nfl/scoreboard?seasontype=2&week={week}', pace=1.0)
    lines, n = [], 0
    for e in sb.get('events', []):
        c = e['competitions'][0]
        home = next(t for t in c['competitors'] if t['homeAway'] == 'home'); away = next(t for t in c['competitors'] if t['homeAway'] == 'away')
        od = (c.get('odds') or [{}])[0]
        lines.append('|'.join(['GM', e['id'], away['team']['abbreviation'], home['team']['abbreviation'], e['date'].replace(':00Z', 'Z'), od.get('details', ''), str(od.get('overUnder', ''))]))
        seen = set(); page = 1
        while page <= 6:
            try: pb = get_json(f'{CORE}/football/nfl/events/{e["id"]}/competitions/{e["id"]}/odds/100/propBets?limit=500&page={page}', pace=0.7)
            except Exception: break
            for it in pb.get('items', []):
                m = (it.get('type') or {}).get('name', '')
                if not m.startswith('Total ') or 'Kick' in m or 'Field Goal' in m or 'Extra Point' in m: continue
                aid = (it.get('athlete') or {}).get('$ref', '').split('/athletes/')[-1].split('?')[0]
                cur = ((it.get('current') or {}).get('target') or {}).get('value'); op = ((it.get('open') or {}).get('target') or {}).get('value')
                if not aid or cur is None: continue
                k = (aid, m)
                if k in seen: continue
                seen.add(k)
                lines.append('|'.join(['PB', e['id'], aid, str((it.get('type') or {}).get('id', '')), m, str(cur), '' if op is None else str(op), (it.get('lastModified') or '')[:17].replace(':00Z', 'Z')]))
                n += 1
            if page >= int(pb.get('pageCount', 1) or 1): break
            page += 1
    if not n:
        log(f'props: week {week} · {sum(1 for l in lines if l.startswith("GM"))} games · 0 markets — nothing written (ESPN propBets is empty; the Odds API carries props now)')
        return None
    out = f'data/raw/props_{y}_wk{week}_{TODAY_S}.txt'
    write_lines(out, lines)
    log(f'props: week {week} · {sum(1 for l in lines if l.startswith("GM"))} games · {n} markets -> {out}')
    return out

# ---------------------------------------------------------------- multi-sport slate
SLATE = [('nfl', 'football/nfl', ''), ('cfb', 'football/college-football', '&groups=80'), ('nba', 'basketball/nba', ''), ('ncaab', 'basketball/mens-college-basketball', '&groups=50'),
         ('wnba', 'basketball/wnba', ''), ('mlb', 'baseball/mlb', ''), ('nhl', 'hockey/nhl', '')] + [(s, f'soccer/{s}', '') for s in ['eng.1', 'usa.1', 'uefa.champions', 'esp.1', 'ger.1', 'ita.1', 'fra.1']]

def injuries():
    """ESPN's injuries feed for all 32 teams (status, injury, return date, the beat note) -> data/raw/espn_injuries_<today>.txt
    I|team|player|pos|status|injury|return|date|fantasy|comment   Both sides of the ball; 'Active' rows (recently on a report, playing) are kept for the trail."""
    try: j = get_json(f'{SITE}/football/nfl/injuries', pace=0.5)
    except Exception as e: log(f'  injuries: {str(e)[:80]}'); return None
    abbr = {str(v): k for k, v in ESPN_NFL.items()}
    lines = []
    for t in j.get('injuries', []):
        tm = abbr.get(str(t.get('id')), '')
        if not tm: continue
        for i in t.get('injuries', []):
            a = i.get('athlete') or {}; d = i.get('details') or {}
            lines.append('|'.join(str(x or '').replace('|', '/') for x in ['I', tm, a.get('displayName'), (a.get('position') or {}).get('abbreviation'), i.get('status'), d.get('type'), d.get('returnDate'), (i.get('date') or '')[:10], (d.get('fantasyStatus') or {}).get('description'), (i.get('shortComment') or '')[:160]]))
    out = f'data/raw/espn_injuries_{TODAY_S}.txt'
    write_lines(out, lines, header=f'# I|team|player|pos|status|injury|return|date|fantasy|comment  (site.api.espn.com/apis/site/v2/sports/football/nfl/injuries; pulled {TODAY_S})')
    log(f'  injuries: {len(lines)} rows, {sum(1 for l in lines if "|Active|" not in l)} not active -> {out}'); return out

def slate(days=8):
    rows, seen = [], set()
    for lg, path, extra in SLATE:
        for i in range(days):
            d = (TODAY + datetime.timedelta(days=i)).strftime('%Y%m%d')
            try: sb = get_json(f'{SITE}/{path}/scoreboard?dates={d}{extra}&limit=400', pace=0.4)
            except Exception as e:
                log(f'  slate {lg} {d}: {str(e)[:60]}'); continue
            for e in sb.get('events', []):
              try:
                if e['id'] in seen: continue
                seen.add(e['id'])
                c = e['competitions'][0]
                st = (e.get('season') or {}).get('type') or (sb.get('season') or {}).get('type') or ''
                if str(st) == '1': continue                              # preseason is ignored
                def T(side):
                    t = next((x for x in c['competitors'] if x['homeAway'] == side), {})
                    tm = t.get('team', {}); rk = (t.get('curatedRank') or {}).get('current', '')
                    return [str(tm.get('id', '')), tm.get('abbreviation', ''), tm.get('displayName', '').replace('|', '/'), next((r.get('summary', '') for r in t.get('records', []) if r.get('type') == 'total'), ''),
                            (tm.get('logo') or '').replace('https://a.espncdn.com/i/teamlogos/', ''), '' if rk in ('', 99, '99') else str(rk)]
                od = (c.get('odds') or [{}])[0] or {}
                rows.append('|'.join(['G', lg, e['id'], e['date'].replace(':00Z', 'Z'), ((e.get('status') or {}).get('type') or {}).get('name', '')] + T('away') + T('home') +
                                     [((c.get('venue') or {}).get('fullName') or '').replace('|', '/'), ','.join(b for bc in c.get('broadcasts', []) for b in bc.get('names', [])),
                                      od.get('details', ''), str(od.get('overUnder', '')), str((e.get('week') or {}).get('number', '')), str(st), '1' if c.get('neutralSite') else '0',
                                      (od.get('provider') or {}).get('name', ''), (((c.get('notes') or [{}])[0] or {}).get('headline') or '').replace('|', '/')]))
              except Exception as ex:                         # one malformed event (a null odds/notes/status block) used to abort the whole slate
                log(f'  slate {lg} event {e.get("id")}: {type(ex).__name__} {str(ex)[:60]}')
    out = f'data/raw/slate_all_{TODAY_S}.txt'
    write_lines(out, rows, f'# multi-sport slate · pulled {TODAY_S} locally (scripts/local/pull_espn.py slate) · preseason rows dropped')
    log(f'slate: {len(rows)} games -> {out}')
    return out if rows else None

# ---------------------------------------------------------------- NCAA game lines
def ncaa():
    y = season_year()
    sb = get_json(f'{SITE}/football/college-football/scoreboard?dates={y}&seasontype=2&groups=80&limit=400', pace=1.0)
    wk = sb.get('week', {}).get('number', 0); lines = []
    cl = lambda x, k: str(x[k]['line']).lstrip('ou') if x and x.get(k) and x[k].get('line') is not None else ''
    od = lambda x, k: str(x[k]['odds']).replace('+', '') if x and x.get(k) and x[k].get('odds') is not None else ''
    def row(e, w, o):
        c = e['competitions'][0]; h = next(t for t in c['competitors'] if t['homeAway'] == 'home'); a = next(t for t in c['competitors'] if t['homeAway'] == 'away')
        ps, tt, ml = (o or {}).get('pointSpread') or {}, (o or {}).get('total') or {}, (o or {}).get('moneyline') or {}
        return '|'.join(['GL', str(y), str(w), e['id'], a['team']['id'], h['team']['id'], a['team']['abbreviation'], h['team']['abbreviation'],
                         cl(ps.get('home'), 'close'), cl(ps.get('home'), 'open'), cl(tt.get('over'), 'close'), cl(tt.get('over'), 'open'),
                         od(ml.get('home'), 'close'), od(ml.get('away'), 'close'), ((o or {}).get('provider') or {}).get('name', ''), e['date'], e['status']['type']['name']])
    for e in sb.get('events', []):
        lines.append(row(e, wk, (e['competitions'][0].get('odds') or [None])[0]))
    for w in range(1, wk):                                             # closing lines of played weeks (pickcenter)
        try: wsb = get_json(f'{SITE}/football/college-football/scoreboard?dates={y}&seasontype=2&week={w}&groups=80&limit=400', pace=1.0)
        except Exception: continue
        for e in wsb.get('events', []):
            try:
                sm = get_json(f'{SITE}/football/college-football/summary?event={e["id"]}', pace=0.6)
                pc = sm.get('pickcenter') or []
                o = next((p for p in pc if (p.get('provider') or {}).get('name') == 'DraftKings'), pc[0] if pc else None)
                lines.append(row(e, w, o))
            except Exception: continue
    out = f'ncaa/data/raw/espn_lines_{y}_{TODAY_S}.txt'
    write_lines(out, lines, f'# ESPN college-football odds pulled locally {TODAY_S} (DraftKings): week {wk} scoreboard + pickcenter closes for weeks 1-{wk - 1}\n'
                '# GL|season|week|eventId|awayId|homeId|awayAbbr|homeAbbr|homeSpreadClose|homeSpreadOpen|totalClose|totalOpen|homeMLClose|awayMLClose|provider|date|status')
    log(f'ncaa lines: week {wk} · {len(lines)} rows -> {out}')
    return out if lines else None

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'slate'
    {'depth': depth, 'props': props, 'slate': slate, 'ncaa': ncaa}[what]()
