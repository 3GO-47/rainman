"""Fetch nflverse public data releases into data/raw/nflverse/ (needs internet; run from any
machine that can reach github.com — the sandbox VM on the desktop cannot, the cloud workspace can).

Usage: python3 scripts/fetch_nflverse.py [seasons...]   (default: 2024 2025 2026)

Files per season (parquet, from https://github.com/nflverse/nflverse-data/releases):
  snap_counts_{s}        player offense/defense/ST snaps + pct per game, keyed by pfr_player_id
  ftn_charting_{s}       FTN play charting: n_blitzers, n_pass_rushers, n_defense_box, play-action,
                         RPO, motion, no-huddle, screens, qb_location (S/U/P)
  pbp_participation_{s}  NGS participation (2024-25 only so far): coverage type, man/zone,
                         offense/defense personnel, defenders in box, pressure
  depth_charts_{s}       weekly team depth charts incl. defense (pos_rank)
  roster_{s}             id crosswalk (pfr_id <-> gsis_id) + positions
  pbp_slim_{s}           play-by-play reduced to the ~45 columns build_advanced.py uses
                         (the full pbp parquet is ~20 MB/season and is NOT kept)
Re-running only downloads what is missing or what is the current season.
"""
import os, sys, urllib.request, datetime
import pandas as pd

os.chdir(os.path.join(os.path.dirname(__file__), '..'))
BASE = 'https://github.com/nflverse/nflverse-data/releases/download'
OUT = 'data/raw/nflverse'
PBP_COLS = ['game_id','season','week','posteam','defteam','play_type','pass','rush','down','ydstogo','qtr',
 'wp','score_differential','shotgun','no_huddle','air_yards','receiver_id','rusher_id','passer_id',
 'pass_attempt','rush_attempt','sack','qb_dropback','qb_scramble','epa','success','yards_gained',
 'complete_pass','pass_location','yardline_100','game_seconds_remaining','half_seconds_remaining',
 'xpass','pass_oe','play_id','drive','fixed_drive','touchdown','interception','fumble_lost',
 'pass_touchdown','rush_touchdown','penalty','two_point_attempt','special_teams_play','cpoe','yac_epa','air_epa']

def get(url, dest):
    try:
        urllib.request.urlretrieve(url, dest)
        if os.path.getsize(dest) < 100:
            os.remove(dest); return False
        return True
    except Exception as e:
        if os.path.exists(dest): os.remove(dest)
        print(f'  skip {os.path.basename(dest)}: {e}'); return False

def main(seasons):
    os.makedirs(OUT, exist_ok=True)
    cur = max(seasons)
    for s in seasons:
        for rel, name in [('snap_counts','snap_counts'),('ftn_charting','ftn_charting'),
                          ('pbp_participation','pbp_participation'),('depth_charts','depth_charts'),
                          ('rosters','roster')]:
            dest = f'{OUT}/{name}_{s}.parquet'
            if os.path.exists(dest) and s != cur: continue
            ok = get(f'{BASE}/{rel}/{name}_{s}.parquet', dest)
            print(f'  {name}_{s}: {"ok" if ok else "unavailable"}')
        slim = f'{OUT}/pbp_slim_{s}.parquet'
        if os.path.exists(slim) and s != cur: continue
        tmp = f'{OUT}/_pbp_full_{s}.parquet'
        if get(f'{BASE}/pbp/play_by_play_{s}.parquet', tmp):
            df = pd.read_parquet(tmp, columns=[c for c in PBP_COLS])
            df.to_parquet(slim, index=False); os.remove(tmp)
            print(f'  pbp_slim_{s}: {len(df)} plays, weeks {int(df.week.min())}-{int(df.week.max())}')
    open(f'{OUT}/_fetched.txt', 'a').write(f'{datetime.date.today()} seasons={seasons}\n')

if __name__ == '__main__':
    main([int(x) for x in sys.argv[1:]] or [2024, 2025, 2026])
