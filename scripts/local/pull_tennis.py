"""Tennis pulls for the local loop (runs on Josh's PC — full internet; nothing here needs a key).

1. Match history + rankings: Jeff Sackmann's open ATP / WTA datasets, from the tennis-sackmann-archive mirror
   (github.com/Aneeshers/tennis-sackmann-archive — Sackmann's own repos were gone when this was built, 2026-10-08).
   The mirror stops in May 2026, so step 2 tops the history up from ESPN's own completed results:
     data/raw/tennis/{atp,wta}_matches_{year}.csv   one row per completed tour-level match with serve stats, ranks, surface
     data/raw/tennis/{atp,wta}_rankings_current.csv  ranking_date, rank, player_id, points
     data/raw/tennis/{atp,wta}_players.csv           player_id, first, last, hand, dob, ioc, height
   Past seasons are fetched once; the current season and the rankings refresh when the cached copy is older than 20 h.
2. History top-up: ESPN's scoreboard walked back day by day, completed singles only, into
     data/raw/tennis/espn_results.csv   tour,date,compId,tournament,round,surface_hint,winner_id,winner,loser_id,loser,score
   Each run fills in the days it has not got yet (BACKFILL per run), so the gap between the mirror and today closes over a few runs
   and then only new days are fetched. notes/tennis_state.json remembers which dates are done.
3. The week's matches: ESPN's public tennis scoreboard (site.api.espn.com …/tennis/{atp,wta}/scoreboard?dates=YYYYMMDD) for today + 7 days,
   singles only, de-duplicated by competition id ->
     data/raw/tennis/espn_<today>.txt   M|tour|compId|tournament|tournId|round|dateUTC|status|city|court|p1id|p1name|p1flag|p2id|p2name|p2flag|winner|score
4. Match markets (no key): Kalshi KXATPMATCH / KXWTAMATCH (one market per player, YES bid/ask) and Polymarket ATP / WTA series (one event per match, moneyline) ->
     data/raw/tennis/markets_<today>.txt
       K|tour|ticker|event_ticker|player|yes_bid|yes_ask|volume|close_time
       P|tour|slug|endDate|question|outcomes|outcomePrices|bestBid|bestAsk|liquidity|gameStartTime
scripts/tennis/build.py turns all of this into dashboard/tennis.html.
"""
import csv, datetime, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import get, log, TODAY, TODAY_S
RAW = 'data/raw/tennis'; os.makedirs(RAW, exist_ok=True)
ARCHIVE = 'https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main'
SACK = {'atp': f'{ARCHIVE}/atp', 'wta': f'{ARCHIVE}/wta'}
STATE = 'notes/tennis_state.json'; RESULTS = 'data/raw/tennis/espn_results.csv'
BACKFILL = int(sys.argv[sys.argv.index('--backfill') + 1]) if '--backfill' in sys.argv else 60   # days of ESPN history per run, newest gap first
SITE = 'https://site.api.espn.com/apis/site/v2/sports/tennis'
KALSHI = {'atp': 'KXATPMATCH', 'wta': 'KXWTAMATCH'}
POLY = {'atp': 10365, 'wta': 10366}          # gamma /series?slug=atp|wta (2026-10-08)
YEARS = list(range(2023, TODAY.year + 1))

def fresh(path, hours):
    return os.path.exists(path) and (time.time() - os.path.getmtime(path)) < hours * 3600

def sackmann():
    n = 0
    for tour, base in SACK.items():
        for y in YEARS:
            f = f'{RAW}/{tour}_matches_{y}.csv'
            if fresh(f, 20 if y == TODAY.year else 24 * 365): continue
            try:
                txt = get(f'{base}/{tour}_matches_{y}.csv', pace=0.5)
                if txt.startswith('404') or 'tourney_id' not in txt[:200]: raise ValueError('not a matches file')
                open(f, 'w', encoding='utf-8').write(txt); n += 1
            except Exception as e: log(f'  sackmann {tour} {y}: {str(e)[:80]}')
        for name in ('rankings_current', 'players'):
            f = f'{RAW}/{tour}_{name}.csv'
            if fresh(f, 20 if name == 'rankings_current' else 24 * 14): continue
            try:
                txt = get(f'{base}/{tour}_{name}.csv', pace=0.5)
                if txt.startswith('404'): raise ValueError('404')
                open(f, 'w', encoding='utf-8').write(txt); n += 1
            except Exception as e: log(f'  sackmann {tour} {name}: {str(e)[:80]}')
    log(f'  sackmann: {n} files refreshed'); return n

def load_state():
    try: return json.load(open(STATE))
    except Exception: return {}

def espn_history(days=BACKFILL):
    """Walk ESPN's scoreboard backwards and keep every completed singles match, so the Elo history runs to yesterday
    even though the public archive stops in May. Only dates not already on file are fetched."""
    st = load_state(); done = set(st.get('days') or [])
    have = set()
    rows = []
    if os.path.exists(RESULTS):
        for r in csv.DictReader(open(RESULTS, encoding='utf-8')): rows.append(r); have.add(r['compId'])
    cols = ['tour', 'date', 'compId', 'tournament', 'round', 'court', 'winner_id', 'winner', 'loser_id', 'loser', 'score']
    todo = []
    for i in range(1, 400):
        d = (TODAY - datetime.timedelta(days=i)).strftime('%Y%m%d')
        if d not in done: todo.append(d)
        if len(todo) >= days: break
    n = 0
    for d in todo:
        ok = True
        for tour in ('atp', 'wta'):
            try: sb = json.loads(get(f'{SITE}/{tour}/scoreboard?dates={d}', pace=0.35))
            except Exception as e: ok = False; log(f'  espn history {tour} {d}: {str(e)[:50]}'); continue
            for e in sb.get('events', []):
                for grp in e.get('groupings', []):
                    if 'singles' not in ((grp.get('grouping') or {}).get('slug') or ''): continue
                    for c in grp.get('competitions', []):
                        if c['id'] in have or ((c.get('status') or {}).get('type') or {}).get('name') != 'STATUS_FINAL': continue
                        P = c.get('competitors', [])
                        w = next((x for x in P if x.get('winner')), None); l = next((x for x in P if x is not w), None)
                        if not w or not l: continue
                        nm = lambda x: ((x.get('athlete') or {}).get('displayName') or '').replace(',', ' ')
                        pid = lambda x: str((re.search(r'/id/(\d+)', (((x.get('athlete') or {}).get('links') or [{}])[0]).get('href', '')) or [None, ''])[1] or x.get('id', ''))
                        if not nm(w) or not nm(l): continue
                        sc = ' '.join(f"{(w.get('linescores') or [{}])[k].get('value', '')}-{(l.get('linescores') or [{}])[k].get('value', '')}" for k in range(len(w.get('linescores') or []))) if w.get('linescores') else ''
                        have.add(c['id']); n += 1
                        rows.append(dict(tour=tour, date=d, compId=c['id'], tournament=str(e.get('name', '')).replace(',', ' '), round=str((c.get('round') or {}).get('displayName', '')).replace(',', ' '),
                                         court=str((c.get('venue') or {}).get('fullName', '')).replace(',', ' '), winner_id=pid(w), winner=nm(w), loser_id=pid(l), loser=nm(l), score=sc))
        if ok: done.add(d)
    rows.sort(key=lambda r: (r['date'], r['compId']))
    with open(RESULTS, 'w', newline='', encoding='utf-8') as f:
        wtr = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); wtr.writeheader(); wtr.writerows(rows)
    st['days'] = sorted(done)[-400:]; os.makedirs('notes', exist_ok=True); json.dump(st, open(STATE, 'w'), indent=1)
    log(f'  espn history: +{n} completed matches ({len(todo)} new days) · {len(rows)} on file'); return n

def espn(days=8):
    rows, seen = [], set()
    clean = lambda s: str(s or '').replace('|', '/').replace('\n', ' ').strip()
    for tour in ('atp', 'wta'):
        for i in range(days):
            d = (TODAY + datetime.timedelta(days=i)).strftime('%Y%m%d')
            try: sb = json.loads(get(f'{SITE}/{tour}/scoreboard?dates={d}', pace=0.5))
            except Exception as e: log(f'  espn {tour} {d}: {str(e)[:60]}'); continue
            for e in sb.get('events', []):
                for grp in e.get('groupings', []):
                    slug = ((grp.get('grouping') or {}).get('slug') or '')
                    if 'singles' not in slug: continue
                    for c in grp.get('competitions', []):
                        if c['id'] in seen: continue
                        seen.add(c['id'])
                        P = sorted(c.get('competitors', []), key=lambda x: x.get('order', 0))
                        def A(x):
                            a = x.get('athlete') or {}; href = ((a.get('links') or [{}])[0]).get('href', '')
                            m = re.search(r'/id/(\d+)', href)
                            return [m.group(1) if m else str(x.get('id', '')), clean(a.get('displayName')), ((a.get('flag') or {}).get('href') or '').split('/')[-1].replace('.png', '')]
                        if len(P) < 2: continue
                        w = next((A(x)[1] for x in P if x.get('winner')), '')
                        score = ' '.join(f"{(P[0].get('linescores') or [{}])[k].get('value', '')}-{(P[1].get('linescores') or [{}])[k].get('value', '')}" for k in range(len(P[0].get('linescores') or []))) if P[0].get('linescores') else ''
                        st = ((c.get('status') or {}).get('type') or {}).get('name', '')
                        rows.append('|'.join(['M', tour, c['id'], clean(e.get('name')), str(e.get('id', '')), clean((c.get('round') or {}).get('displayName')), c.get('date', '').replace(':00Z', 'Z'), st,
                                              clean((c.get('venue') or {}).get('fullName')), clean((c.get('venue') or {}).get('court'))] + A(P[0]) + A(P[1]) + [w, score]))
    out = f'{RAW}/espn_{TODAY_S}.txt'
    open(out, 'w', encoding='utf-8').write(f'# M|tour|compId|tournament|tournId|round|dateUTC|status|city|court|p1id|p1name|p1flag|p2id|p2name|p2flag|winner|score  (ESPN tennis scoreboard, singles, pulled {TODAY_S})\n' + '\n'.join(rows) + '\n')
    log(f'  espn tennis: {len(rows)} singles matches -> {out}'); return len(rows)

def markets():
    lines = [f'# K|tour|ticker|event_ticker|player|yes_bid|yes_ask|volume|close_time · P|tour|slug|endDate|question|outcomes|outcomePrices|bestBid|bestAsk|liquidity|gameStartTime  (pulled {TODAY_S})']
    n = 0
    for tour, series in KALSHI.items():
        cur = ''
        for _ in range(10):
            try: j = json.loads(get(f'https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&status=open&series_ticker={series}' + (f'&cursor={cur}' if cur else ''), pace=0.4))
            except Exception as e: log(f'  kalshi {series}: {str(e)[:60]}'); break
            for m in j.get('markets', []):
                if not (m.get('yes_bid_dollars') or m.get('yes_ask_dollars')): continue
                lines.append('|'.join(str(x if x is not None else '') for x in ['K', tour, m.get('ticker'), m.get('event_ticker'), (m.get('yes_sub_title') or '').replace('|', '/'), m.get('yes_bid_dollars'), m.get('yes_ask_dollars'), round(float(m.get('volume_fp') or 0)), (m.get('close_time') or '')[:16]])); n += 1
            cur = j.get('cursor') or ''
            if not cur: break
    clean = lambda s: re.sub(r'[\[\]"]', '', str(s or '')).replace('|', '/')
    lim = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=9)).strftime('%Y-%m-%dT%H:%M:%SZ')
    for tour, sid in POLY.items():
        for off in (0, 100, 200, 300):
            try: ev = json.loads(get(f'https://gamma-api.polymarket.com/events?series_id={sid}&closed=false&limit=100&offset={off}&order=endDate&ascending=true', pace=0.5))
            except Exception as e: log(f'  polymarket {tour}: {str(e)[:60]}'); break
            if not ev: break
            for e in ev:
                if (e.get('endDate') or '') > lim: continue
                for m in e.get('markets', []):
                    if (m.get('sportsMarketType') or '') != 'moneyline' or m.get('closed') or m.get('bestBid') is None or m.get('bestAsk') is None: continue
                    lines.append('|'.join(str(x) for x in ['P', tour, e.get('slug', ''), e.get('endDate', ''), str(m.get('question', '')).replace('|', '/'), clean(m.get('outcomes')), clean(m.get('outcomePrices')), m.get('bestBid'), m.get('bestAsk'), round(m.get('liquidityNum') or 0), (m.get('gameStartTime') or '')[:16]])); n += 1
            if len(ev) < 100: break
    out = f'{RAW}/markets_{TODAY_S}.txt'
    open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    log(f'  tennis markets: {n} lines -> {out}'); return n

def main():
    sackmann(); espn_history(); n = espn(); markets()
    return n

if __name__ == '__main__' and '--history-only' in sys.argv:
    espn_history(); sys.exit(0)

if __name__ == '__main__':
    main()
