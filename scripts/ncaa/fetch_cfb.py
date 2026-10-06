"""Fetch the college-football source files RAINMAN-NCAA derives everything from (no API key needed).

All of it is the sportsdataverse mirror of ESPN / CFBD data on GitHub, reachable from the cloud workspace:
  player box scores  github.com/sportsdataverse/sportsdataverse-data  release espn_cfb_player_box/player_box_{season}.parquet
  schedules + scores raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main/schedules/parquet/cfb_schedules_{season}.parquet
  rosters            .../rosters/parquet/rosters_{season}.parquet          (position, headshot url)
  team info          .../team_info/parquet/cfb_team_info_{season}.parquet  (ESPN id, abbreviation, colors, conference, FBS/FCS)
  betting lines      .../betting/parquet/cfb_line_odds.parquet             (DraftKings / ESPN Bet / Bovada closing + opening, through 2025)

Usage: python3 scripts/ncaa/fetch_cfb.py [--force]
Writes ncaa/data/raw/*.parquet and ncaa/notes/fetch_state.json (ETag / size per file so unchanged files are skipped).
The mirror itself updates several times a week in season (Sat 16:00 / 20:15 UTC, Sun + Mon 06:30 UTC).
"""
import os, sys, json, urllib.request, datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
RAW = 'ncaa/data/raw/'
SEASONS = (2024, 2025, 2026)
SDV = 'https://github.com/sportsdataverse/sportsdataverse-data/releases/download/'
CFR = 'https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main/'
FILES = {}
for s in SEASONS:
    FILES[f'player_box_{s}.parquet'] = f'{SDV}espn_cfb_player_box/player_box_{s}.parquet'
    FILES[f'schedules_{s}.parquet'] = f'{CFR}schedules/parquet/cfb_schedules_{s}.parquet'
    FILES[f'rosters_{s}.parquet'] = f'{CFR}rosters/parquet/rosters_{s}.parquet'
    FILES[f'team_info_{s}.parquet'] = f'{CFR}team_info/parquet/cfb_team_info_{s}.parquet'
FILES['line_odds.parquet'] = f'{CFR}betting/parquet/cfb_line_odds.parquet'

def main():
    force = '--force' in sys.argv
    os.makedirs(RAW, exist_ok=True); os.makedirs('ncaa/notes', exist_ok=True)
    sp = 'ncaa/notes/fetch_state.json'
    state = json.load(open(sp)) if os.path.exists(sp) else {}
    for name, url in FILES.items():
        dst = RAW + name
        req = urllib.request.Request(url, headers={'User-Agent': 'rainman-ncaa/1.0'})
        prev = state.get(name, {})
        if not force and os.path.exists(dst) and prev.get('etag'):
            req.add_header('If-None-Match', prev['etag'])
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read(); etag = r.headers.get('ETag', '')
        except urllib.error.HTTPError as e:
            if e.code == 304:
                print(f'  {name}: unchanged'); continue
            print(f'  {name}: HTTP {e.code} — kept previous copy' if os.path.exists(dst) else f'  {name}: HTTP {e.code} MISSING'); continue
        if data[:4] != b'PAR1':
            print(f'  {name}: not a parquet file ({len(data)} bytes) — skipped'); continue
        open(dst, 'wb').write(data)
        state[name] = {'etag': etag, 'bytes': len(data), 'fetched': datetime.datetime.utcnow().isoformat(timespec='minutes') + 'Z', 'url': url}
        print(f'  {name}: {len(data)//1024} KB')
    json.dump(state, open(sp, 'w'), indent=1)

if __name__ == '__main__':
    main()
