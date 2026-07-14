"""Transform raw box-score lines into game_logs CSV (the source of truth).

Usage: python3 build_game_logs.py <season>
Inputs:  data/raw/box_lines_{season}.txt   (P|bid|pid|name|TEAM|cmp|att|payds|patd|int|ratt|ryds|rtd|tgt|rec|recyds|rectd|fl and D|bid|team|count)
         data/processed/games_{season}.csv (week,date,vis,home,boxscore)
         data/raw/positions_{season}.csv   (pid,pos from PFR fantasy page)
Outputs: data/game_logs/game_logs_{season}.csv (project schema)
         data/processed/dst_tds_{season}.csv  (season,week,team,opponent,dst_tds -- return/defensive TDs scored)

Slot method (historical seasons, no ESPN depth-chart history available):
  Within each team-week, among players who appeared in that game, rank by CUMULATIVE
  season usage through the current week (no future information):
    QB by pass attempts -> QB1, QB2...
    RB (and FB) by rush_att+targets -> RB1, RB2, RB3...
    WR by targets -> WR1, WR2, WR3, rest WR4+
    TE by targets -> TE1, TE2, rest TE3
  If a starter misses a game he simply doesn't appear; next man up inherits the higher
  slot for that week, which mirrors depth-chart-as-of-that-week behavior.
  Positions come from PFR's season fantasy page; unknown players are inferred
  (pass_att-heavy => QB, targets-only => WR, else RB) and counted in the log output.
"""
import sys, csv, os
from collections import defaultdict

PFR_DISPLAY = {'GNB':'GB','KAN':'KC','LVR':'LV','NWE':'NE','NOR':'NO','SFO':'SF','TAM':'TB','OTI':'TEN','CLT':'IND','CRD':'ARI','HTX':'HOU','RAV':'BAL','RAM':'LAR','SDG':'LAC','RAI':'LV'}
NICK2ABBR = {'Cardinals':'ARI','Falcons':'ATL','Ravens':'BAL','Bills':'BUF','Panthers':'CAR','Bears':'CHI','Bengals':'CIN','Browns':'CLE','Cowboys':'DAL','Broncos':'DEN','Lions':'DET','Packers':'GB','Texans':'HOU','Colts':'IND','Jaguars':'JAX','Chiefs':'KC','Raiders':'LV','Chargers':'LAC','Rams':'LAR','Dolphins':'MIA','Vikings':'MIN','Patriots':'NE','Saints':'NO','Giants':'NYG','Jets':'NYJ','Eagles':'PHI','Steelers':'PIT','Seahawks':'SEA','49ers':'SF','Buccaneers':'TB','Titans':'TEN','Commanders':'WAS'}

def norm_team(t):
    t = t.strip()
    if t in NICK2ABBR: return NICK2ABBR[t]
    u = t.upper()
    return PFR_DISPLAY.get(u, u)

def main(season):
    games = {}
    for r in csv.DictReader(open(f'data/processed/games_{season}.csv')):
        games[r['boxscore']] = r
    # positions: merge every available season file, older first so the newest wins;
    # the current season's file (if present) takes final precedence
    import glob as _glob
    pos = {}
    for pf in sorted(_glob.glob('data/raw/positions_*.csv')):
        if pf.endswith(f'{season}.csv'):
            continue
        pos.update(dict(csv.reader(open(pf))))
    own = f'data/raw/positions_{season}.csv'
    if os.path.exists(own):
        pos.update(dict(csv.reader(open(own))))
    else:
        print(f'WARN: no positions_{season}.csv yet — using prior seasons + inference '
              f'(pull https://www.pro-football-reference.com/years/{season}/fantasy.htm when available)')

    prows, drows = [], []
    for line in open(f'data/raw/box_lines_{season}.txt', encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('P|'):
            f = line.split('|')
            if len(f) != 18: continue
            prows.append(f[1:])
        elif line.startswith('D|'):
            f = line.split('|')
            drows.append(f[1:])
        elif line.startswith('ERR|'):
            print('WARN skipped:', line)

    inferred = 0
    recs = []
    for f in prows:
        bid, pid, name, team = f[0], f[1], f[2], norm_team(f[3])
        g = games.get(bid)
        if not g:
            continue
        num = [int(x or 0) for x in f[4:]]
        cmp_, att, payds, patd, pint, ratt, ryds, rtd, tgt, rec, recyds, rectd, fl = num
        p = pos.get(pid, '')
        if p == 'FB': p = 'RB'
        if p not in ('QB','RB','WR','TE'):
            inferred += 1
            if att >= 3: p = 'QB'
            elif tgt > 0 and ratt <= 1: p = 'WR'
            else: p = 'RB'
        opp = g['vis'] if team == g['home'] else g['home']
        ha = 'H' if team == g['home'] else 'A'
        std = payds/25 + patd*4 - pint*2 + ryds/10 + rtd*6 + recyds/10 + rectd*6 - fl*2
        recs.append({'season':season,'week':int(g['week']),'date':g['date'],'player':name,
            'player_id':pid,'team':team,'opponent':opp,'home_away':ha,'pos':p,'slot':'',
            'pass_yds':payds,'pass_td':patd,'pass_att':att,'cmp':cmp_,'int':pint,
            'rush_att':ratt,'rush_yds':ryds,'rush_td':rtd,'targets':tgt,'rec':rec,
            'rec_yds':recyds,'rec_td':rectd,'fumbles_lost':fl,
            'fantasy_pts_std':round(std,2),'fantasy_pts_ppr':round(std+rec,2)})

    # slot assignment: cumulative usage through current week
    recs.sort(key=lambda r: r['week'])
    cum = defaultdict(float)  # (pid) -> usage
    by_week = defaultdict(list)
    for r in recs: by_week[r['week']].append(r)
    USAGE = {'QB': lambda r: r['pass_att'], 'RB': lambda r: r['rush_att']+r['targets'],
             'WR': lambda r: r['targets'], 'TE': lambda r: r['targets']}
    for wk in sorted(by_week):
        for r in by_week[wk]:
            cum[r['player_id']] += USAGE[r['pos']](r)
        teams = defaultdict(list)
        for r in by_week[wk]: teams[(r['team'], r['pos'])].append(r)
        for (t, p), lst in teams.items():
            lst.sort(key=lambda r: -cum[r['player_id']])
            for i, r in enumerate(lst, 1):
                if p == 'QB': r['slot'] = f'QB{min(i,2)}'
                elif p == 'RB': r['slot'] = f'RB{min(i,3)}'
                elif p == 'WR': r['slot'] = f'WR{i}' if i <= 3 else 'WR4+'
                elif p == 'TE': r['slot'] = f'TE{min(i,3)}'

    os.makedirs('data/game_logs', exist_ok=True)
    cols = ['season','week','date','player','player_id','team','opponent','home_away','slot','pos',
            'pass_yds','pass_td','pass_att','cmp','int','rush_att','rush_yds','rush_td',
            'targets','rec','rec_yds','rec_td','fumbles_lost','fantasy_pts_std','fantasy_pts_ppr']
    with open(f'data/game_logs/game_logs_{season}.csv','w',newline='',encoding='utf-8') as fo:
        w = csv.DictWriter(fo, fieldnames=cols); w.writeheader(); w.writerows(recs)

    with open(f'data/processed/dst_tds_{season}.csv','w',newline='') as fo:
        w = csv.writer(fo); w.writerow(['season','week','team','opponent','dst_tds'])
        for bid, team, cnt in drows:
            g = games.get(bid)
            if not g: continue
            t = norm_team(team)
            opp = g['vis'] if t == g['home'] else g['home']
            w.writerow([season, g['week'], t, opp, cnt])

    print(f'game_logs_{season}.csv: {len(recs)} rows, weeks {min(by_week)}-{max(by_week)}, '
          f'inferred pos: {inferred}, dst rows: {len(drows)}')

if __name__ == '__main__':
    main(sys.argv[1])
