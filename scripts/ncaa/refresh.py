"""RAINMAN-NCAA one-command refresh: pull the GitHub mirrors, rebuild every derived table, write dashboard/ncaa.html.

Usage: python3 scripts/ncaa/refresh.py [--week N] [--no-fetch]

Order: fetch_cfb (GitHub mirrors of ESPN / CFBD) -> build_game_logs (all seasons) -> build_schedule -> compute_dvp (FBS defenses)
       -> build_lines (CFBD 2024-25 + ESPN dumps in ncaa/data/raw/espn_lines_*.txt) -> build_depth_matchups -> build_dashboard --league ncaa
Everything under ncaa/data/processed and ncaa/data/game_logs is reproducible from ncaa/data/raw by rerunning this.
The only step that needs a browser is the current week's ESPN odds (see notes/scrape_recipe.md, "NCAA game lines").
"""
import os, sys, subprocess, glob, datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))

def run(cmd):
    print(f'\n=== {" ".join(cmd)}')
    r = subprocess.run([sys.executable] + cmd)
    if r.returncode: sys.exit(f'FAILED: {cmd}')

def main():
    wk = ['--week', sys.argv[sys.argv.index('--week') + 1]] if '--week' in sys.argv else []
    if '--no-fetch' not in sys.argv: run(['scripts/ncaa/fetch_cfb.py'])
    run(['scripts/ncaa/build_game_logs.py'])
    run(['scripts/ncaa/build_schedule.py'])
    run(['scripts/ncaa/compute_dvp.py'])
    run(['scripts/ncaa/build_lines.py'])
    run(['scripts/ncaa/build_depth_matchups.py'] + wk)
    run(['scripts/build_dashboard.py', '--league', 'ncaa'])
    dumps = sorted(glob.glob('ncaa/data/raw/espn_lines_2026_*.txt'))
    if dumps:
        age = (datetime.date.today() - datetime.date.fromisoformat(dumps[-1][-14:-4])).days
        if age > 6: print(f'  WARNING: newest ESPN odds dump is {age} days old — re-pull this week\'s lines in Chrome')
    else:
        print('  WARNING: no ESPN odds dump for 2026 — the Bets tab has no current-week lines')
    print('  dashboard/ncaa.html rebuilt')

if __name__ == '__main__':
    main()
