"""Local market pull for the Arb Engine (no key, no browser): DraftKings game lines with prices (ESPN core odds, provider 100),
Kalshi game / spread / total ladders (public trade API) and Polymarket game + prop books (Gamma API) for every league on the slate.

Writes data/raw/markets/{draftkings,kalshi,polymarket}_<today>.txt in the formats scripts/build_arb.py consumes:
  D|espnEventId|homeSpread|overUnder|homeML|awayML|homeSpreadOdds|awaySpreadOdds|overOdds|underOdds|league
  K2|series|ticker|event_ticker|title|yes_sub_title|strike|strike_type|yes_bid|yes_ask|last|volume|close_time
  P|eventSlug|kind|endDateUTC|marketId|question|sportsMarketType|line|outcomes|outcomePrices|bestBid|bestAsk|liquidity|volume
Polymarket props are kept only when the book is two-sided (ask − bid ≤ 0.12); every ladder keeps its 3 rungs nearest 50%.
Usage: python3 scripts/local/pull_markets.py          (run by loop.py; ~1 call per game for DK, ~15 calls total for the exchanges)
"""
import datetime, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get, log
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
TODAY = datetime.date.today().isoformat()
OUT = 'data/raw/markets'; os.makedirs(OUT, exist_ok=True)
ESPN = {'nfl': 'football/nfl', 'cfb': 'football/college-football', 'nba': 'basketball/nba', 'wnba': 'basketball/wnba', 'nhl': 'hockey/nhl', 'mlb': 'baseball/mlb', 'ncaab': 'basketball/mens-college-basketball'}
KALSHI = {'nfl': 'KXNFL', 'nhl': 'KXNHL', 'nba': 'KXNBA', 'mlb': 'KXMLB', 'cfb': 'KXNCAAF', 'wnba': 'KXWNBA', 'ncaab': 'KXNCAAB'}
POLY_SERIES = {'nfl': 12185, 'nhl': 10346, 'nba': 10345, 'cfb': 12756}   # gamma /series?slug=<league>-2026 ids (2026-10-08)
GAME_TYPES = {'moneyline', 'spreads', 'totals', 'team_totals'}
PROP_TYPES = {'passing_yards', 'passing_touchdowns', 'rushing_yards', 'receiving_yards', 'receptions', 'anytime_touchdowns', 'passing_attempts', 'passing_completions',
              'points', 'rebounds', 'assists', 'threes', 'shots_on_goal', 'goals', 'saves'}

def slate():
    files = sorted(glob.glob('data/raw/slate_all_*.txt'))
    if not files: return []
    G = []
    for line in open(files[-1], encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 26 or p[22] == '1': continue
        G.append(dict(lg=p[1], id=p[2], date=p[3], away=p[6], home=p[12]))
    return G

def draftkings(G):
    lines = ['# D|espnEventId|homeSpread|overUnder|homeML|awayML|homeSpreadOdds|awaySpreadOdds|overOdds|underOdds|league  (ESPN core odds provider 100 = DraftKings; pulled %s)' % TODAY]
    lim = (datetime.datetime.utcnow() + datetime.timedelta(days=8)).strftime('%Y-%m-%dT%H:%MZ')
    for g in G:
        path = ESPN.get(g['lg'])
        if not path or g['date'] > lim: continue
        sport, league = path.split('/')
        try:
            o = json.loads(get(f'https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{g["id"]}/competitions/{g["id"]}/odds/100', pace=0.6))
        except Exception as e:
            continue
        h, a = o.get('homeTeamOdds') or {}, o.get('awayTeamOdds') or {}
        v = lambda x: '' if x is None else x
        lines.append('|'.join(str(v(x)) for x in ['D', g['id'], o.get('spread'), o.get('overUnder'), h.get('moneyLine'), a.get('moneyLine'), h.get('spreadOdds'), a.get('spreadOdds'), o.get('overOdds'), o.get('underOdds'), g['lg']]))
    open(f'{OUT}/draftkings_{TODAY}.txt', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    log(f'  draftkings: {len(lines) - 1} games priced'); return len(lines) - 1

def kalshi(G):
    leagues = {g['lg'] for g in G}
    lines = ['# K2|series|ticker|event_ticker|title|yes_sub_title|strike|strike_type|yes_bid|yes_ask|last|volume|close_time  (api.elections.kalshi.com; pulled %s)' % TODAY]
    n = 0
    for lg, pre in KALSHI.items():
        if lg not in leagues: continue
        for s in ('GAME', 'SPREAD', 'TOTAL'):
            cur = ''
            for _ in range(8):
                try: j = json.loads(get(f'https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&status=open&series_ticker={pre}{s}' + (f'&cursor={cur}' if cur else ''), pace=0.4))
                except Exception: break
                for m in j.get('markets', []):
                    bid, ask = m.get('yes_bid_dollars'), m.get('yes_ask_dollars')
                    if not (bid or ask): continue
                    if s != 'GAME' and not (0.25 <= float(bid or 0) <= 0.75): continue      # ladders: keep the rungs near the main line
                    lines.append('|'.join(str(x if x is not None else '') for x in ['K2', pre + s, m.get('ticker'), m.get('event_ticker'), (m.get('title') or '').replace('|', '/'), (m.get('yes_sub_title') or '').replace('|', '/'),
                                  m.get('floor_strike', m.get('cap_strike', '')), m.get('strike_type', ''), bid, ask, m.get('last_price_dollars', ''), round(float(m.get('volume_fp') or 0)), (m.get('close_time') or '')[:16]]))
                    n += 1
                cur = j.get('cursor') or ''
                if not cur: break
    open(f'{OUT}/kalshi_{TODAY}.txt', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    log(f'  kalshi: {n} markets'); return n

def polymarket(G):
    leagues = {g['lg'] for g in G}
    lines = ['# P|eventSlug|kind|endDateUTC|marketId|question|sportsMarketType|line|outcomes|outcomePrices|bestBid|bestAsk|liquidity|volume  (gamma-api.polymarket.com; pulled %s)' % TODAY]
    lim = (datetime.datetime.utcnow() + datetime.timedelta(days=8)).strftime('%Y-%m-%dT%H:%M:%SZ')
    n = 0
    clean = lambda s: re.sub(r'[\[\]" ]', '', str(s or ''))
    for lg, sid in POLY_SERIES.items():
        if lg not in leagues: continue
        for off in (0, 100, 200):
            try: ev = json.loads(get(f'https://gamma-api.polymarket.com/events?series_id={sid}&closed=false&limit=100&offset={off}&order=endDate&ascending=true', pace=0.5))
            except Exception: break
            if not ev: break
            for e in ev:
                slug = e.get('slug', '')
                kind = 'props' if slug.endswith('-player-props') else 'game' if re.search(r'-\d{4}-\d{2}-\d{2}$', slug) else ''
                if not kind or (e.get('endDate') or '') > lim: continue
                by = {}
                for m in e.get('markets', []):
                    if m.get('closed') or not m.get('active'): continue
                    t = m.get('sportsMarketType') or ''
                    if kind == 'game' and t not in GAME_TYPES: continue
                    if kind == 'props' and t not in PROP_TYPES: continue
                    bid, ask = m.get('bestBid'), m.get('bestAsk')
                    if bid is None or ask is None or ask - bid > 0.12: continue
                    pr = [float(x) for x in clean(m.get('outcomePrices')).split(',') if x]
                    if t == 'anytime_touchdowns':
                        if bid < 0.08: continue
                    elif t != 'moneyline' and (not pr or min(pr) < 0.2): continue
                    key = (str(m.get('question', '')).split(':')[0] + '|' + t) if kind == 'props' else t
                    by.setdefault(key, []).append((abs((pr[0] if pr else .5) - .5), m, pr))
                for key, arr in by.items():
                    one = key.endswith('|anytime_touchdowns') or key == 'moneyline'
                    arr.sort(key=lambda x: x[0])
                    for _, m, pr in arr[:1 if one else (2 if kind == 'props' else 3)]:
                        lines.append('|'.join(str(x) for x in ['P', slug, kind, e.get('endDate', ''), m.get('id'), str(m.get('question', '')).replace('|', '/'), m.get('sportsMarketType', ''), '' if m.get('line') is None else m.get('line'),
                                      clean(m.get('outcomes')), ','.join(str(x) for x in pr), m.get('bestBid'), m.get('bestAsk'), round(m.get('liquidityNum') or 0), round(m.get('volumeNum') or 0)]))
                        n += 1
            if len(ev) < 100: break
    open(f'{OUT}/polymarket_{TODAY}.txt', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    log(f'  polymarket: {n} markets'); return n

def main():
    G = slate()
    if not G: log('  markets: no slate file'); return 0
    return draftkings(G) + kalshi(G) + polymarket(G)

if __name__ == '__main__':
    main()
