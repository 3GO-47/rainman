"""Derive data/processed/kickoffs_2026.csv — kickoff day / time (ET) / slate bucket per game.

Sources (both in data/raw/, both fetched from Pro Football Reference):
  pfr_games_2026.md         /years/2026/games.htm markdown dump (has Day + Time columns; truncated at wk 14)
  pfr_week_pages_2026.txt   /years/2026/week_N.htm lines for the weeks the dump is missing
Output joins 1:1 onto data/processed/games_2026.csv on (week, vis, home).

Slate buckets (Eastern kickoff):  TNF  Thu/Wed night      EARLY  Sun 1:00 PM      LATE  Sun 4:05/4:25 PM
  SNF  Sun >= 7 PM   MNF  Mon   INTL  Sun 9:30 AM (London/Europe)   THU  Thanksgiving-day Thu games
  FRI / SAT  holiday + late-season Saturday windows                   TBD  week 18 (NFL flexes all times)
Usage: python3 scripts/build_kickoffs.py
"""
import csv, re, datetime, os, sys
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

SLUG2ABBR = {'crd':'ARI','atl':'ATL','rav':'BAL','buf':'BUF','car':'CAR','chi':'CHI','cin':'CIN',
 'cle':'CLE','dal':'DAL','den':'DEN','det':'DET','gnb':'GB','htx':'HOU','clt':'IND','jax':'JAX',
 'kan':'KC','rai':'LV','sdg':'LAC','ram':'LAR','mia':'MIA','min':'MIN','nwe':'NE','nor':'NO',
 'nyg':'NYG','nyj':'NYJ','phi':'PHI','pit':'PIT','sea':'SEA','sfo':'SF','tam':'TB','oti':'TEN','was':'WAS'}
NAME2ABBR = {'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF',
 'Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE',
 'Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB',
 'Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC',
 'Las Vegas Raiders':'LV','Los Angeles Chargers':'LAC','Los Angeles Rams':'LAR','Miami Dolphins':'MIA',
 'Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG',
 'New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','Seattle Seahawks':'SEA',
 'San Francisco 49ers':'SF','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WAS'}
DAY3 = {'Wednesday':'Wed','Thursday':'Thu','Friday':'Fri','Saturday':'Sat','Sunday':'Sun','Monday':'Mon'}

def norm_time(t):
    t = t.strip().upper().replace(' ', '')
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(AM|PM)', t)
    if not m: return ''
    h, mi, ap = int(m.group(1)), m.group(2), m.group(3)
    return f'{h}:{mi} {ap}'

def minutes(t):  # '4:25 PM' -> minutes since midnight
    m = re.fullmatch(r'(\d{1,2}):(\d{2}) (AM|PM)', t)
    h = int(m.group(1)) % 12 + (12 if m.group(3) == 'PM' else 0)
    return h * 60 + int(m.group(2))

def slate(week, day, t):
    if week == 18 or not t: return 'TBD'
    mn = minutes(t)
    if day in ('Thu', 'Wed'): return 'TNF' if mn >= 19 * 60 else 'THU'
    if day == 'Mon': return 'MNF'
    if day == 'Sat': return 'SAT'
    if day == 'Fri': return 'FRI'
    if day == 'Sun':
        if mn < 12 * 60: return 'INTL'
        if mn < 15 * 60: return 'EARLY'
        if mn < 19 * 60: return 'LATE'
        return 'SNF'
    return 'OTHER'

def main():
    rows = {}
    for line in open('data/raw/pfr_games_2026.md', encoding='utf-8', errors='replace'):
        if not line.startswith('|'): continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 9 or not re.fullmatch(r'\d+', cells[0]): continue
        teams = re.findall(r'/teams/(\w+)/\d+\.htm', line)
        if len(teams) < 2: continue
        wk, day = int(cells[0]), cells[1]
        vis, home = SLUG2ABBR[teams[0]], SLUG2ABBR[teams[1]]
        rows[(wk, vis, home)] = (day, norm_time(cells[-1]))
    for line in open('data/raw/pfr_week_pages_2026.txt', encoding='utf-8'):
        if line.startswith('#') or '|' not in line: continue
        wk, day, _date, t, game = [c.strip() for c in line.split('|')]
        v, h = [x.strip() for x in game.split('@')]
        key = (int(wk), NAME2ABBR[v], NAME2ABBR[h])
        if key not in rows:
            rows[key] = (DAY3[day.title()], norm_time(t))
    games = list(csv.DictReader(open('data/processed/games_2026.csv')))
    out, missing = [], []
    for g in games:
        key = (int(g['week']), g['vis'], g['home'])
        day, t = rows.get(key, ('', ''))
        if not day: missing.append(key)
        if not day and g['date']:
            day = datetime.date.fromisoformat(g['date']).strftime('%a')
        out.append({'week': key[0], 'vis': g['vis'], 'home': g['home'], 'date': g['date'],
                    'day': day, 'time_et': t, 'slate': slate(key[0], day, t)})
    with open('data/processed/kickoffs_2026.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['week','vis','home','date','day','time_et','slate'])
        w.writeheader(); w.writerows(out)
    from collections import Counter
    print(f'kickoffs_2026.csv: {len(out)} games · slates {dict(Counter(r["slate"] for r in out))}')
    if missing:
        print(f'  WARNING {len(missing)} games without kickoff source: {missing}', file=sys.stderr)

if __name__ == '__main__':
    main()
