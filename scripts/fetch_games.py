"""Fetch the nflverse schedule/results/lines file (github.com/nflverse/nfldata, updated after every game) into
data/raw/nflverse/games.csv and derive data/processed/game_lines.csv (2024-2026: scores, closing spread/total/
moneylines, rest days, roof/surface, QBs). Needs github access — run from the cloud workspace like fetch_nflverse.py.
spread_line convention (nflverse): positive = HOME favored by that many points; result = home_score - away_score."""
import os, urllib.request, pandas as pd, datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
URL = 'https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv'
RAW = 'data/raw/nflverse/games.csv'
os.makedirs('data/raw/nflverse', exist_ok=True)
urllib.request.urlretrieve(URL, RAW)
g = pd.read_csv(RAW)
g = g[(g.season >= 2024) & (g.game_type == 'REG')].copy()
g['away_team'] = g.away_team.replace({'LA': 'LAR'}); g['home_team'] = g.home_team.replace({'LA': 'LAR'})
cols = ['game_id','season','week','gameday','weekday','gametime','away_team','home_team','away_score','home_score','result','total',
        'overtime','spread_line','away_spread_odds','home_spread_odds','total_line','under_odds','over_odds','away_moneyline','home_moneyline',
        'away_rest','home_rest','div_game','roof','surface','temp','wind','away_qb_name','home_qb_name','pfr']
g[cols].to_csv('data/processed/game_lines.csv', index=False)
played = g[g.result.notna()]
print(f"game_lines.csv: {len(g)} games 2024-26 · {len(played)} with results · 2026 through week {int(played[played.season==2026].week.max()) if (played.season==2026).any() else 0}"
      f" · lines present for 2026 wk {int(g[(g.season==2026)&g.spread_line.notna()].week.max())}")
open('data/raw/nflverse/_fetched.txt', 'a').write(f'{datetime.date.today()} games.csv\n')
