"""NCAA: team x week schedule grid + kickoff slates for the current season, from ncaa/data/processed/games_{season}.csv.

Usage: python3 scripts/ncaa/build_schedule.py [season]      (default 2026)
Outputs: ncaa/data/processed/schedule_{season}.csv   team, week_1 .. week_20  ('@OPP' / 'OPP' / 'BYE' / '' once the regular season ends)
         ncaa/data/processed/kickoffs_{season}.csv   week, vis, home, date, day, time_et, slate   (joins 1:1 onto games_{season}.csv)
Only FBS teams get a grid row (opponents may be FCS — they still appear as the opponent code).
Slates (Eastern kickoff): MIDWK Tue/Wed · THU · FRI · SAT_AM < 2 PM · SAT_PM 2-6:59 PM · SAT_NT 7-9:59 PM · SAT_LT >= 10 PM · SUN/MON · TBD
"""
import os, sys, csv, datetime, zoneinfo
from collections import Counter
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = 'ncaa/data/processed/'
ET = zoneinfo.ZoneInfo('America/New_York')
NWEEKS = 20

def slate(day, mins, tbd):
    if tbd: return 'TBD'
    if day in ('Tue', 'Wed'): return 'MIDWK'
    if day == 'Thu': return 'THU'
    if day == 'Fri': return 'FRI'
    if day == 'Sat':
        if mins < 14 * 60: return 'SAT_AM'
        if mins < 19 * 60: return 'SAT_PM'
        if mins < 22 * 60: return 'SAT_NT'
        return 'SAT_LT'
    return 'SUNMON'

def main(season):
    teams = {r['code']: r for r in csv.DictReader(open(OUT + 'teams.csv', encoding='utf-8'))}
    fbs = [c for c, r in teams.items() if r['classification'] == 'fbs']
    games = list(csv.DictReader(open(OUT + f'games_{season}.csv', encoding='utf-8')))
    grid = {t: [''] * NWEEKS for t in fbs}
    last_reg = max(int(g['week']) for g in games if g['season_type'] == 'regular')
    for g in games:
        wk = int(g['week'])
        if wk < 1: continue
        if g['vis'] in grid: grid[g['vis']][wk - 1] = '@' + g['home']
        if g['home'] in grid: grid[g['home']][wk - 1] = g['vis']
    for t in fbs:   # BYE = open date inside the team's scheduled regular season; blank after its last scheduled game
        last = max([i for i in range(last_reg) if grid[t][i]] or [-1])
        for i in range(last + 1):
            if not grid[t][i]: grid[t][i] = 'BYE'
    with open(OUT + f'schedule_{season}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['team'] + [f'week_{i}' for i in range(1, NWEEKS + 1)])
        for t in sorted(fbs): w.writerow([t] + grid[t])
    out = []
    for g in games:
        k = datetime.datetime.fromisoformat(g['kick_utc'].replace('Z', '+00:00')).astimezone(ET)
        tbd = g.get('time_tbd') == '1'
        day = k.strftime('%a'); mins = k.hour * 60 + k.minute
        t = '' if tbd else k.strftime('%I:%M %p').lstrip('0')
        out.append({'week': g['week'], 'vis': g['vis'], 'home': g['home'], 'date': g['date'], 'day': day, 'time_et': t, 'slate': slate(day, mins, tbd)})
    with open(OUT + f'kickoffs_{season}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['week', 'vis', 'home', 'date', 'day', 'time_et', 'slate']); w.writeheader(); w.writerows(out)
    print(f'schedule_{season}.csv: {len(fbs)} FBS teams x {NWEEKS} weeks (regular season through week {last_reg}) · '
          f'kickoffs_{season}.csv: {len(out)} games · slates {dict(Counter(r["slate"] for r in out))}')

if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2026)
