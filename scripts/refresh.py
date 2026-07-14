"""RAINMAN one-command refresh: rebuild everything derivable from data on disk.

Usage: python3 scripts/refresh.py [--week N]

Runs: game logs (every season with raw box lines) -> DvP tables -> matchups -> dashboard.
--week sets the matchup week for the 2026/27 season; if omitted it is auto-detected as the
first week whose games have not all been played yet (falls back to 1 pre-season, 18 after).

This does NOT scrape. Scraping new box scores / depth charts requires the Chrome workflow —
see notes/scrape_recipe.md. Once raw files land, this command makes every derived number
consistent with them. All derived tables are reproducible from data/game_logs + data/raw.
"""
import csv, datetime, glob, json, os, subprocess, sys

os.chdir(os.path.join(os.path.dirname(__file__), '..'))

def run(cmd):
    print(f'\n=== {" ".join(cmd)}')
    r = subprocess.run([sys.executable] + cmd)
    if r.returncode != 0:
        sys.exit(f'FAILED: {cmd}')

def auto_week():
    today = datetime.date.today()
    weeks = {}
    for r in csv.DictReader(open('data/processed/games_2026.csv')):
        weeks.setdefault(int(r['week']), []).append(datetime.date.fromisoformat(r['date']))
    for wk in sorted(weeks):
        if max(weeks[wk]) >= today:
            return wk
    return 18

def main():
    week = None
    if '--week' in sys.argv:
        week = int(sys.argv[sys.argv.index('--week') + 1])
    if week is None:
        week = auto_week()

    seasons = sorted(f.split('_')[-1].split('.')[0] for f in glob.glob('data/raw/box_lines_*.txt'))
    print(f'RAINMAN refresh — seasons with raw data: {seasons} · matchup week: {week} (2026/27)')

    for s in seasons:
        run(['scripts/build_game_logs.py', s])
    run(['scripts/compute_dvp.py'])
    dc = sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1]
    print(f'depth chart snapshot: {dc}')
    run(['scripts/build_matchups.py', dc, str(week)])
    run(['scripts/build_dashboard.py'])

    # summary + anomaly report
    st = json.load(open('notes/scrape_state.json'))
    print('\n=== summary')
    for s in seasons:
        n = sum(1 for _ in open(f'data/game_logs/game_logs_{s}.csv')) - 1
        errs = sum(1 for l in open(f'data/raw/box_lines_{s}.txt') if l.startswith('ERR'))
        wd = st['seasons'].get(s, {}).get('weeks_done', [])
        print(f'  {s}: {n} game-log rows · weeks scraped {min(wd) if wd else "-"}-{max(wd) if wd else "-"} '
              f'· raw ERR lines: {errs}')
    age = (datetime.date.today() - datetime.date.fromisoformat(dc.split("_")[-1][:10])).days
    if age > 9:
        print(f'  WARNING: depth chart snapshot is {age} days old — re-pull ESPN depth charts')
    print('  dashboard/rainman.html rebuilt — open it in a browser')

if __name__ == '__main__':
    main()
