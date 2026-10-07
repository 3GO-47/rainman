"""Local ESPN pulls (public JSON APIs, no key, no browser) — Python ports of the Chrome recipes in notes/scrape_recipe.md.
Each sub-command writes the same raw file the recipe wrote, so every downstream script is unchanged:
  depth  -> data/raw/espn_depth_<today>.txt   (TEAM|POSROW|DEPTH|NAME|TAG; core depthcharts + roster injuries)
  props  -> data/raw/props_2026_wk<W>_<today>.txt (GM| / PB| DraftKings player props, provider 100)
  slate  -> data/raw/slate_all_<today>.txt     (every league's next 8 days, G| rows; preseason rows dropped)
  ncaa   -> ncaa/data/raw/espn_lines_2026_<today>.txt (GL| current-week scoreboard + pickcenter closes for played weeks)
Usage: python scripts/local/pull_espn.py depth|props|slate|ncaa [...]"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get_json, log, write_lines, TODAY, TODAY_S, ESPN_NFL

SITE = 'https://site.api.espn.com/apis/site/v2/sports'
CORE = 'https://sports.core.api.espn.com/v2/sports'
TAG = {'Questionable': 'Q', 'Doubtful': 'D', 'Out': 'O', 'Injured Reserve': 'IR', 'Physically Unable to Perform': 'PUP', 'Suspension': 'SUSP',
       'Suspended': 'SUSP', 'Non-Football Injury': 'NFI', 'Non Football Injury': 'NFI', 'Day-To-Day': ''}

def season_year():
    return TODAY.year if TODAY.month >= 3 else TODAY.year - 1

# ---------------------------------------------------------------- depth charts
def depth():
    y = season_year(); lines = []
    for team, tid in ESPN_NFL.items():
        try:
            ro = get_json(f'{SITE}/football/nfl/teams/{tid}/roster', pace=1.0)
            names, tags = {}, {}
            for grp in ro.get('athletes', []):
                for a in grp.get('items', []):
                    names[str(a['id'])] = a.get('displayName', '')
                    t = ''
                    for inj in a.get('injuries', []) or []:
                        t = TAG.get(inj.get('status', ''), (inj.get('status') or '')[:1].upper()) or t
                    if grp.get('position') == 'injuredReserveOrOut' and not t: t = 'IR'
                    if grp.get('position') == 'suspended': t = 'SUSP'
                    tags[str(a['id'])] = t
            dc = get_json(f'{CORE}/football/nfl/seasons/{y}/teams/{tid}/depthcharts', pace=1.0)
            off = next((it for it in dc.get('items', []) if 'qb' in (it.get('positions') or {})), None)
            if not off: log(f'  {team}: no offense formation'); continue
            for key, P in off['positions'].items():
                pos = (P.get('position') or {}).get('abbreviation', key.upper())
                if pos not in ('QB', 'RB', 'WR', 'TE', 'FB'): continue
                ath = P.get('athletes', [])
                slots = sorted({a.get('slot', 1) for a in ath})
                for si, slot in enumerate(slots, 1):
                    row = sorted((a for a in ath if a.get('slot', 1) == slot), key=lambda a: a.get('rank', 99))
                    label = f'WR{si}' if pos == 'WR' else pos
                    for d, a in enumerate(row, 1):
                        aid = (a.get('athlete') or {}).get('$ref', '').split('/athletes/')[-1].split('?')[0]
                        nm = names.get(aid)
                        if not nm:
                            try: nm = get_json(f'{CORE}/football/nfl/athletes/{aid}', pace=0.5).get('displayName', '')
                            except Exception: nm = ''
                        if nm: lines.append('|'.join([team, label, str(d), nm, tags.get(aid, '')]))
        except Exception as e:
            log(f'  {team}: depth failed {str(e)[:80]}')
    out = f'data/raw/espn_depth_{TODAY_S}.txt'
    write_lines(out, lines)
    log(f'depth: {len(lines)} rows / {len({l.split("|")[0] for l in lines})} teams -> {out}')
    return out if lines else None

# ---------------------------------------------------------------- DraftKings props (ESPN odds provider 100)
def props(week=None):
    y = season_year()
    sb = get_json(f'{SITE}/football/nfl/scoreboard?seasontype=2&dates={y}' + (f'&week={week}' if week else ''), pace=1.0)
    week = week or sb.get('week', {}).get('number')
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
    out = f'data/raw/props_{y}_wk{week}_{TODAY_S}.txt'
    write_lines(out, lines)
    log(f'props: week {week} · {sum(1 for l in lines if l.startswith("GM"))} games · {n} markets -> {out}')
    return out if n else None

# ---------------------------------------------------------------- multi-sport slate
SLATE = [('nfl', 'football/nfl', ''), ('cfb', 'football/college-football', '&groups=80'), ('nba', 'basketball/nba', ''), ('ncaab', 'basketball/mens-college-basketball', '&groups=50'),
         ('wnba', 'basketball/wnba', ''), ('mlb', 'baseball/mlb', ''), ('nhl', 'hockey/nhl', '')] + [(s, f'soccer/{s}', '') for s in ['eng.1', 'usa.1', 'uefa.champions', 'esp.1', 'ger.1', 'ita.1', 'fra.1']]

def slate(days=8):
    rows, seen = [], set()
    for lg, path, extra in SLATE:
        for i in range(days):
            d = (TODAY + datetime.timedelta(days=i)).strftime('%Y%m%d')
            try: sb = get_json(f'{SITE}/{path}/scoreboard?dates={d}{extra}&limit=400', pace=0.4)
            except Exception as e:
                log(f'  slate {lg} {d}: {str(e)[:60]}'); continue
            for e in sb.get('events', []):
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
                od = (c.get('odds') or [{}])[0]
                rows.append('|'.join(['G', lg, e['id'], e['date'].replace(':00Z', 'Z'), (e.get('status') or {}).get('type', {}).get('name', '')] + T('away') + T('home') +
                                     [((c.get('venue') or {}).get('fullName') or '').replace('|', '/'), ','.join(b for bc in c.get('broadcasts', []) for b in bc.get('names', [])),
                                      od.get('details', ''), str(od.get('overUnder', '')), str((e.get('week') or {}).get('number', '')), str(st), '1' if c.get('neutralSite') else '0',
                                      (od.get('provider') or {}).get('name', ''), ((c.get('notes') or [{}])[0].get('headline') or '').replace('|', '/')]))
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
