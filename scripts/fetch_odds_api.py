"""Priced lines from every US book via The Odds API — https://the-odds-api.com (free tier: 500 credits/month).

Setup (once): create a free key at the-odds-api.com, then put it in a file named .env in the repo root:
    ODDS_API_KEY=your_key_here
(.env is git-ignored — the key never goes into the repo or the dashboard; scripts\\local\\set_key.ps1 writes it for you.)

Usage: python3 scripts/fetch_odds_api.py                 # game lines (moneyline, spread, total) for every league on the slate
       python3 scripts/fetch_odds_api.py --props         # + NFL player props (one call per game — ~16 credits, so weekly)
       python3 scripts/fetch_odds_api.py --books fanduel,draftkings
Cost: 1 credit per market per region per call → game lines = 3 credits per league per run; props = 1 credit per event.
Writes data/raw/markets/oddsapi_<date>.csv  (league, home, away, commence, book, market, side, point, price, updated)  → scripts/build_arb.py
       data/raw/odds_api/props_<date>.csv     (player, market, book, side, line, price, event, updated)                 → scripts/build_bets.py
"""
import os, sys, csv, glob, json, datetime, urllib.request, urllib.parse
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
SPORT = {'nfl': 'americanfootball_nfl', 'cfb': 'americanfootball_ncaaf', 'nba': 'basketball_nba', 'wnba': 'basketball_wnba', 'nhl': 'icehockey_nhl', 'mlb': 'baseball_mlb', 'ncaab': 'basketball_ncaab'}
BOOKS = 'fanduel,draftkings,betmgm,caesars,fanatics,espnbet,betrivers,bet365'
PROP_MARKETS = {'player_pass_yds': 'pass_yds', 'player_pass_tds': 'pass_td', 'player_pass_completions': 'completions',
                'player_pass_attempts': 'pass_att', 'player_pass_interceptions': 'interceptions', 'player_rush_yds': 'rush_yds',
                'player_rush_attempts': 'rush_att', 'player_receptions': 'receptions', 'player_reception_yds': 'rec_yds',
                'player_rush_reception_yds': 'rush_rec_yds', 'player_pass_rush_yds': 'pass_rush_yds', 'player_anytime_td': 'anytime_td'}

def key():
    k = os.environ.get('ODDS_API_KEY')
    if not k and os.path.exists('.env'):
        for line in open('.env'):
            if line.strip().startswith('ODDS_API_KEY='): k = line.split('=', 1)[1].strip().strip('"').strip("'")
    if not k: sys.exit('ODDS_API_KEY missing — see the setup note at the top of this file')
    return k

def get(sport, path, **params):
    params['apiKey'] = key()
    url = f'https://api.the-odds-api.com/v4/sports/{sport}{path}?{urllib.parse.urlencode(params)}'
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read()), r.headers.get('x-requests-remaining')

def slate():
    """League → {full team name: slate abbreviation}, plus which leagues have games in the next 8 days."""
    files = sorted(glob.glob('data/raw/slate_all_*.txt')); names, active = {}, set()
    lim = (datetime.datetime.utcnow() + datetime.timedelta(days=8)).strftime('%Y-%m-%dT%H:%MZ')
    if not files: return names, active
    for line in open(files[-1], encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 26 or p[22] == '1': continue
        names.setdefault(p[1], {})[p[7]] = p[6]; names[p[1]][p[13]] = p[12]
        if p[3] <= lim: active.add(p[1])
    return names, active

def main():
    books = BOOKS
    if '--books' in sys.argv: books = sys.argv[sys.argv.index('--books') + 1]
    leagues = sys.argv[sys.argv.index('--leagues') + 1].split(',') if '--leagues' in sys.argv else None
    today = str(datetime.date.today()); os.makedirs('data/raw/markets', exist_ok=True); os.makedirs('data/raw/odds_api', exist_ok=True)
    names, active = slate(); left = '?'; n = 0
    with open(f'data/raw/markets/oddsapi_{today}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['league', 'home', 'away', 'commence', 'book', 'market', 'side', 'point', 'price', 'updated'])
        for lg, sport in SPORT.items():
            if leagues is not None and lg not in leagues: continue
            if leagues is None and lg not in active: continue
            try: lines, left = get(sport, '/odds', regions='us', markets='h2h,spreads,totals', bookmakers=books, oddsFormat='american')
            except Exception as e: print(f'  {lg}: {e}'); continue
            tm = names.get(lg, {})
            for e in lines:
                h, a = tm.get(e['home_team'], e['home_team']), tm.get(e['away_team'], e['away_team'])
                for b in e.get('bookmakers', []):
                    for m in b['markets']:
                        for o in m['outcomes']:
                            w.writerow([lg, h, a, e['commence_time'], b['key'], m['key'], tm.get(o['name'], o['name']), o.get('point', ''), o['price'], m.get('last_update', '')]); n += 1
            print(f'  {lg}: {len(lines)} games · credits left {left}')
    np = 0
    if '--props' in sys.argv and (leagues is None or 'nfl' in leagues) and 'nfl' in active:
        events, left = get(SPORT['nfl'], '/events')
        soon = [e for e in events if e['commence_time'] < (datetime.datetime.utcnow() + datetime.timedelta(days=8)).isoformat()]
        with open(f'data/raw/odds_api/props_{today}.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['player', 'market', 'book', 'side', 'line', 'price', 'event', 'updated'])
            for e in soon:
                try: data, left = get(SPORT['nfl'], f"/events/{e['id']}/odds", regions='us', markets=','.join(PROP_MARKETS), bookmakers=books, oddsFormat='american')
                except Exception as ex: print(f'  props {e["id"]}: {ex}'); continue
                for b in data.get('bookmakers', []):
                    for m in b['markets']:
                        for o in m['outcomes']:
                            side = o['name']; player = o.get('description', '')
                            if m['key'] == 'player_anytime_td': side, player = 'Yes', o.get('description', o['name'])
                            w.writerow([player, PROP_MARKETS[m['key']], 'FD' if b['key'] == 'fanduel' else b['key'], side, o.get('point', ''), o['price'], e['id'], m.get('last_update', '')]); np += 1
    print(f'odds_api: {n} priced outcomes · {np} prop outcomes · credits left {left}')
    return n

if __name__ == '__main__':
    main()
