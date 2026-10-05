"""FanDuel (and other books) lines WITH prices from The Odds API — https://the-odds-api.com (free tier: 500 credits/month).

Setup (once): create a free key at the-odds-api.com, then put it in a file named .env in the repo root:
    ODDS_API_KEY=your_key_here
.env is git-ignored — the key never goes into the repo or the dashboard.

Usage: python3 scripts/fetch_odds_api.py            # FanDuel props + game lines for the upcoming NFL week
       python3 scripts/fetch_odds_api.py --books fanduel,draftkings
Cost: 1 credit per event × market-group per region (≈ 16 games × 1 props call + 1 lines call ≈ 17-20 credits per run).
Writes data/raw/odds_api/props_<date>.csv  (player, market, book, side, line, price, updated)
       data/raw/odds_api/lines_<date>.csv  (home, away, book, market, side, point, price, updated)
"""
import os, sys, csv, json, datetime, urllib.request, urllib.parse
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
BASE = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl'
PROP_MARKETS = {'player_pass_yds': 'pass_yds', 'player_pass_tds': 'pass_td', 'player_pass_completions': 'completions',
                'player_pass_attempts': 'pass_att', 'player_pass_interceptions': 'interceptions', 'player_rush_yds': 'rush_yds',
                'player_rush_attempts': 'rush_att', 'player_receptions': 'receptions', 'player_reception_yds': 'rec_yds',
                'player_rush_reception_yds': 'rush_rec_yds', 'player_pass_rush_yds': 'pass_rush_yds', 'player_anytime_td': 'anytime_td'}
TEAM = {'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL', 'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR',
        'Chicago Bears': 'CHI', 'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL', 'Denver Broncos': 'DEN',
        'Detroit Lions': 'DET', 'Green Bay Packers': 'GB', 'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
        'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC', 'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA',
        'Minnesota Vikings': 'MIN', 'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG', 'New York Jets': 'NYJ',
        'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT', 'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA',
        'Tampa Bay Buccaneers': 'TB', 'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS'}

def key():
    k = os.environ.get('ODDS_API_KEY')
    if not k and os.path.exists('.env'):
        for line in open('.env'):
            if line.strip().startswith('ODDS_API_KEY='): k = line.split('=', 1)[1].strip()
    if not k: sys.exit('ODDS_API_KEY missing — see the setup note at the top of this file')
    return k

def get(path, **params):
    params['apiKey'] = key()
    url = f'{BASE}{path}?{urllib.parse.urlencode(params)}'
    with urllib.request.urlopen(url, timeout=30) as r:
        left = r.headers.get('x-requests-remaining')
        return json.loads(r.read()), left

def main():
    books = 'fanduel'
    if '--books' in sys.argv: books = sys.argv[sys.argv.index('--books') + 1]
    today = str(datetime.date.today()); os.makedirs('data/raw/odds_api', exist_ok=True)
    events, left = get('/events')
    soon = [e for e in events if e['commence_time'] < (datetime.datetime.utcnow() + datetime.timedelta(days=8)).isoformat()]
    lines, left = get('/odds', regions='us', markets='h2h,spreads,totals', bookmakers=books, oddsFormat='american')
    with open(f'data/raw/odds_api/lines_{today}.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['home', 'away', 'commence', 'book', 'market', 'side', 'point', 'price', 'updated'])
        for e in lines:
            for b in e.get('bookmakers', []):
                for m in b['markets']:
                    for o in m['outcomes']:
                        w.writerow([TEAM.get(e['home_team'], e['home_team']), TEAM.get(e['away_team'], e['away_team']), e['commence_time'],
                                    b['key'], m['key'], TEAM.get(o['name'], o['name']), o.get('point', ''), o['price'], m.get('last_update', '')])
    n = 0
    with open(f'data/raw/odds_api/props_{today}.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['player', 'market', 'book', 'side', 'line', 'price', 'event', 'updated'])
        for e in soon:
            data, left = get(f"/events/{e['id']}/odds", regions='us', markets=','.join(PROP_MARKETS), bookmakers=books, oddsFormat='american')
            for b in data.get('bookmakers', []):
                for m in b['markets']:
                    for o in m['outcomes']:
                        side = o['name']; player = o.get('description', '')
                        if m['key'] == 'player_anytime_td': side, player = 'Yes', o.get('description', o['name'])
                        w.writerow([player, PROP_MARKETS[m['key']], 'FD' if b['key'] == 'fanduel' else b['key'], side, o.get('point', ''),
                                    o['price'], e['id'], m.get('last_update', '')]); n += 1
    print(f'odds_api: {len(lines)} games of lines · {n} prop outcomes from {len(soon)} events · credits left {left}')

if __name__ == '__main__':
    main()
