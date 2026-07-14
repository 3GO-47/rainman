"""Parse a PFR /years/YYYY/games.htm page (markdown-converted via web_fetch)
into (a) a games list CSV and (b) for future seasons, a team x week schedule grid.

Usage: python3 parse_schedule.py <fetched_markdown_file> <season> <out_dir>
Outputs:
  <out_dir>/games_<season>.csv         (week, date, vis, home, boxscore_url if present)
  <out_dir>/schedule_<season>.csv      (team x week grid, BYE marked) - regular season only
"""
import sys, re, csv, os

SLUG2ABBR = {
    'crd':'ARI','atl':'ATL','rav':'BAL','buf':'BUF','car':'CAR','chi':'CHI','cin':'CIN',
    'cle':'CLE','dal':'DAL','den':'DEN','det':'DET','gnb':'GB','htx':'HOU','clt':'IND',
    'jax':'JAX','kan':'KC','rai':'LV','sdg':'LAC','ram':'LAR','mia':'MIA','min':'MIN',
    'nwe':'NE','nor':'NO','nyg':'NYG','nyj':'NYJ','phi':'PHI','pit':'PIT','sea':'SEA',
    'sfo':'SF','tam':'TB','oti':'TEN','was':'WAS'}

def main(path, season, out_dir):
    text = open(path, encoding='utf-8', errors='replace').read()
    games = []
    for line in text.splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 7:
            continue
        wk = cells[0]
        if not re.fullmatch(r'\d+', wk):
            continue  # skip preseason (PreX), playoffs (WildCard etc.) and headers
        teams = re.findall(r'/teams/(\w+)/\d+\.htm', line)
        if len(teams) < 2:
            continue
        vis, home = SLUG2ABBR[teams[0]], SLUG2ABBR[teams[1]]
        box = re.search(r'/boxscores/(\d{9}\w+)\.htm', line)
        # date: find a cell like "September 4" possibly with year
        date = ''
        m = re.search(r'(January|February|August|September|October|November|December)\s+\d+', line)
        if m: date = m.group(0)
        games.append({'week': int(wk), 'date': date, 'vis': vis, 'home': home,
                      'boxscore': box.group(1) if box else ''})
    os.makedirs(out_dir, exist_ok=True)
    with open(f'{out_dir}/games_{season}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['week','date','vis','home','boxscore'])
        w.writeheader(); w.writerows(games)
    # grid
    weeks = sorted({g['week'] for g in games})
    grid = {t: {w: 'BYE' for w in weeks} for t in SLUG2ABBR.values()}
    for g in games:
        grid[g['vis']][g['week']] = '@' + g['home']
        grid[g['home']][g['week']] = g['vis']
    with open(f'{out_dir}/schedule_{season}.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['team'] + [f'week_{k}' for k in weeks])
        for t in sorted(grid):
            w.writerow([t] + [grid[t][k] for k in weeks])
    print(f'{season}: {len(games)} games, weeks {min(weeks)}-{max(weeks)}, '
          f'boxscore links: {sum(1 for g in games if g["boxscore"])}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
