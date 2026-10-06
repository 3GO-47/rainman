"""NCAA: ESPN player box scores + CFBD schedules -> game_logs (the atomic unit, same schema as the NFL layer).

Usage: python3 scripts/ncaa/build_game_logs.py [season ...]        (default: every season in ncaa/data/raw/)
Inputs : ncaa/data/raw/player_box_{season}.parquet   one row per player x stat category (passing / rushing / receiving / fumbles ...)
         ncaa/data/raw/schedules_{season}.parquet    game_id, week, kickoff, home/away ESPN ids, points, fbs/fcs division
         ncaa/data/raw/rosters_{season}.parquet      athlete_id -> position, headshot
         ncaa/data/raw/team_info_{season}.parquet    ESPN id -> abbreviation / school / colors / conference / classification
Outputs: ncaa/data/game_logs/game_logs_{season}.csv  (project schema; targets = 0 — college box scores carry no targets)
         ncaa/data/processed/games_{season}.csv      (week,date,vis,home,boxscore,kick_utc,neutral,season_type,vis_pts,home_pts,completed,time_tbd)
         ncaa/data/processed/teams.csv               (code,team_id,school,abbreviation,conference,classification,color,alt_color)
         ncaa/data/processed/players.csv             (player_id,player,pos,headshot)

Conventions
  team code  = ESPN abbreviation (unique across the 136 FBS teams); FCS / D-II opponents keep theirs unless it collides
  week       = CFBD regular-season week; the earlier of a team's two "week 1" games becomes week 0; postseason -> 17 (bowls + CFP
               first round), 18 (quarterfinals), 19 (semifinals), 20 (title game) so a team never has two games in one week
  scope      = every game with at least one FBS side; both offenses are logged (an FCS offense's line vs an FBS defense is
               part of what that defense allowed), DvP is later restricted to FBS defenses
  slot       = usage rank within team-week, cumulative through the current week (no future information) — the same method
               the NFL layer uses for historical seasons: QB by pass attempts, RB by carries + receptions, WR / TE by receptions
  positions  = CFBD roster (same season first, then neighbours); unknown -> inferred from usage, like the NFL layer
"""
import os, sys, csv, glob, re
from collections import defaultdict
import pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
RAW, OUT, LOGS = 'ncaa/data/raw/', 'ncaa/data/processed/', 'ncaa/data/game_logs/'
POST_WEEK = 17
def post_week(start):
    """Postseason rounds by calendar: bowls + CFP first round -> 17, New Year's quarterfinals -> 18, semis -> 19, title game -> 20."""
    d = pd.Timestamp(start) - pd.Timedelta(hours=4)
    if d.month == 12 and d.day <= 30: return 17   # bowls + CFP first round
    if d.month == 12 or d.day <= 3: return 18     # New Year's quarterfinals (Dec 31 - Jan 3)
    if d.day <= 12: return 19
    return 20

def team_table():
    frames = []
    for f in sorted(glob.glob(RAW + 'team_info_*.parquet')):
        t = pd.read_parquet(f, columns=['team_id', 'school', 'abbreviation', 'conference', 'classification', 'color', 'alt_color'])
        t['season'] = int(re.findall(r'(\d{4})', f)[-1]); frames.append(t)
    T = pd.concat(frames).sort_values('season').drop_duplicates('team_id', keep='last')
    T['classification'] = T.classification.fillna('other').str.lower()
    T['abbreviation'] = T.abbreviation.fillna('').astype(str).str.upper().str.replace(r'[^A-Z0-9&-]', '', regex=True)
    T = T.sort_values(['classification', 'school'], key=lambda s: s.map({'fbs': 0, 'fcs': 1}).fillna(2) if s.name == 'classification' else s)
    used, codes = set(), {}
    for r in T.itertuples():
        base = r.abbreviation or re.sub(r'[^A-Z]', '', str(r.school).upper())[:5] or f'T{r.team_id}'
        code, n = base, 2
        while code in used: code, n = f'{base}{n}', n + 1
        used.add(code); codes[int(r.team_id)] = code
    T['code'] = T.team_id.astype(int).map(codes)
    T['color'] = T.color.fillna('#58a6ff'); T['alt_color'] = T.alt_color.fillna('#444444')
    return T[['code', 'team_id', 'school', 'abbreviation', 'conference', 'classification', 'color', 'alt_color']]

def positions():
    P, H = {}, {}
    for f in sorted(glob.glob(RAW + 'rosters_*.parquet'), reverse=True):   # newest first; first seen wins
        R = pd.read_parquet(f, columns=['athlete_id', 'position', 'headshot_url', 'first_name', 'last_name'])
        for r in R.itertuples():
            try: aid = int(r.athlete_id)
            except (TypeError, ValueError): continue
            p = str(r.position or '').upper()
            if p == 'FB': p = 'RB'
            if aid not in P and p in ('QB', 'RB', 'WR', 'TE'): P[aid] = p
            if aid not in H and isinstance(r.headshot_url, str) and r.headshot_url: H[aid] = r.headshot_url
    return P, H

def num(v):
    try: return int(float(v))
    except (TypeError, ValueError): return 0

def main(seasons):
    T = team_table(); T.to_csv(OUT + 'teams.csv', index=False)
    code = dict(zip(T.team_id.astype(int), T.code)); fbs = {int(i) for i in T[T.classification == 'fbs'].team_id}
    POS, HEAD = positions()
    players = {}
    for season in seasons:
        S = pd.read_parquet(RAW + f'schedules_{season}.parquet')
        S = S[(S.home_division == 'fbs') | (S.away_division == 'fbs')].copy()
        S['week_n'] = [post_week(d) if st == 'postseason' else int(w) for st, d, w in zip(S.season_type, S.start_date, S.week)]
        # week-0 games are folded into week 1 upstream: a team with two week-1 games gets the earlier one as week 0
        S = S.sort_values('start_date')
        for tid in set(S.home_id) | set(S.away_id):
            m = S[((S.home_id == tid) | (S.away_id == tid)) & (S.week_n == 1)]
            if len(m) > 1: S.loc[m.index[:-1], 'week_n'] = 0
        games = {}
        with open(OUT + f'games_{season}.csv', 'w', newline='', encoding='utf-8') as fo:
            w = csv.writer(fo); w.writerow(['week', 'date', 'vis', 'home', 'boxscore', 'kick_utc', 'neutral', 'season_type', 'vis_pts', 'home_pts', 'completed', 'time_tbd'])
            for r in S.sort_values('start_date').itertuples():
                hid, aid = int(r.home_id), int(r.away_id)
                if hid not in code or aid not in code: continue
                d = pd.Timestamp(r.start_date)
                g = {'week': r.week_n, 'date': (d - pd.Timedelta(hours=4)).strftime('%Y-%m-%d'),   # ET calendar date
                     'vis': code[aid], 'home': code[hid], 'vis_id': aid, 'home_id': hid, 'kick': r.start_date}
                games[int(r.game_id)] = g
                w.writerow([g['week'], g['date'], g['vis'], g['home'], int(r.game_id), r.start_date, int(bool(r.neutral_site)), r.season_type,
                            num(r.away_points) if pd.notna(r.away_points) else '', num(r.home_points) if pd.notna(r.home_points) else '', int(bool(r.completed)), int(bool(r.start_time_tbd))])
        B = pd.read_parquet(RAW + f'player_box_{season}.parquet')
        B = B[B.category.isin(['passing', 'rushing', 'receiving', 'fumbles']) & B.game_id.isin(games.keys()) & (B.athlete_name != 'Team')]
        B = B.rename(columns={'completions/passingAttempts': 'cmp_att'})
        acc = {}
        for r in B.itertuples():
            k = (int(r.game_id), int(r.athlete_id))
            a = acc.setdefault(k, {'name': r.athlete_name, 'team_id': int(r.team_id), 'cmp': 0, 'att': 0, 'py': 0, 'ptd': 0, 'int': 0,
                                  'ra': 0, 'ry': 0, 'rtd': 0, 'rec': 0, 'recy': 0, 'rectd': 0, 'fl': 0})
            if r.category == 'passing':   # two upstream schemas: stat_1..stat_5 (C/ATT,YDS,AVG,TD,INT) or named columns
                if isinstance(r.stat_1, str):
                    ca = r.stat_1.split('/'); a['cmp'] += num(ca[0]); a['att'] += num(ca[-1])
                    a['py'] += num(r.stat_2); a['ptd'] += num(r.stat_4); a['int'] += num(r.stat_5)
                else:
                    ca = str(r.cmp_att or '0/0').split('/'); a['cmp'] += num(ca[0]); a['att'] += num(ca[-1])
                    a['py'] += num(r.passingYards); a['ptd'] += num(r.passingTouchdowns); a['int'] += num(r.interceptions)
            elif r.category == 'rushing':
                a['ra'] += num(r.rushingAttempts); a['ry'] += num(r.rushingYards); a['rtd'] += num(r.rushingTouchdowns)
            elif r.category == 'receiving':
                a['rec'] += num(r.receptions); a['recy'] += num(r.receivingYards); a['rectd'] += num(r.receivingTouchdowns)
            elif r.category == 'fumbles':
                a['fl'] += num(r.fumblesLost)
        recs, inferred = [], 0
        for (gid, aid), a in acc.items():
            g = games[gid]
            if a['team_id'] not in code: continue
            if a['team_id'] == g['home_id']: team, opp, ha = g['home'], g['vis'], 'H'
            elif a['team_id'] == g['vis_id']: team, opp, ha = g['vis'], g['home'], 'A'
            else: continue
            if not (a['att'] or a['ra'] or a['rec']): continue
            p = POS.get(aid, '')
            if p not in ('QB', 'RB', 'WR', 'TE'):
                inferred += 1
                p = 'QB' if a['att'] >= 3 else ('WR' if a['rec'] > 0 and a['ra'] <= 1 else 'RB')
            std = a['py'] / 25 + a['ptd'] * 4 - a['int'] * 2 + a['ry'] / 10 + a['rtd'] * 6 + a['recy'] / 10 + a['rectd'] * 6 - a['fl'] * 2
            name = re.sub(r'\s+', ' ', str(a['name'])).strip()
            players.setdefault(aid, (name, p, HEAD.get(aid, '')))
            recs.append({'season': season, 'week': g['week'], 'date': g['date'], 'player': name, 'player_id': str(aid), 'team': team,
                         'opponent': opp, 'home_away': ha, 'slot': '', 'pos': p,
                         'pass_yds': a['py'], 'pass_td': a['ptd'], 'pass_att': a['att'], 'cmp': a['cmp'], 'int': a['int'],
                         'rush_att': a['ra'], 'rush_yds': a['ry'], 'rush_td': a['rtd'], 'targets': 0, 'rec': a['rec'],
                         'rec_yds': a['recy'], 'rec_td': a['rectd'], 'fumbles_lost': a['fl'],
                         'fantasy_pts_std': round(std, 2), 'fantasy_pts_ppr': round(std + a['rec'], 2), '_kick': g['kick']})
        # slots: cumulative usage through the current week, ranked within team x position
        recs.sort(key=lambda r: (r['week'], r['_kick']))
        cum = defaultdict(float); by_week = defaultdict(list)
        for r in recs: by_week[r['week']].append(r)
        USAGE = {'QB': lambda r: r['pass_att'], 'RB': lambda r: r['rush_att'] + r['rec'], 'WR': lambda r: r['rec'], 'TE': lambda r: r['rec']}
        for wk in sorted(by_week):
            for r in by_week[wk]: cum[r['player_id']] += USAGE[r['pos']](r)
            teams = defaultdict(list)
            for r in by_week[wk]: teams[(r['team'], r['pos'])].append(r)
            for (t, p), lst in teams.items():
                lst.sort(key=lambda r: (-cum[r['player_id']], -USAGE[p](r), -(r['rec_yds'] + r['rush_yds'] + r['pass_yds']), r['player']))
                for i, r in enumerate(lst, 1):
                    if p == 'QB': r['slot'] = f'QB{min(i, 2)}'
                    elif p == 'RB': r['slot'] = f'RB{min(i, 3)}'
                    elif p == 'WR': r['slot'] = f'WR{i}' if i <= 3 else 'WR4+'
                    else: r['slot'] = f'TE{min(i, 3)}'
        cols = ['season', 'week', 'date', 'player', 'player_id', 'team', 'opponent', 'home_away', 'slot', 'pos',
                'pass_yds', 'pass_td', 'pass_att', 'cmp', 'int', 'rush_att', 'rush_yds', 'rush_td',
                'targets', 'rec', 'rec_yds', 'rec_td', 'fumbles_lost', 'fantasy_pts_std', 'fantasy_pts_ppr']
        os.makedirs(LOGS, exist_ok=True)
        with open(LOGS + f'game_logs_{season}.csv', 'w', newline='', encoding='utf-8') as fo:
            w = csv.DictWriter(fo, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(recs)
        nf = sum(1 for r in recs if r['team'] in set(T[T.classification == 'fbs'].code))
        print(f'game_logs_{season}.csv: {len(recs)} rows ({nf} on FBS offenses) · {len(games)} games · weeks {min(by_week)}-{max(by_week)} · inferred pos {inferred}')
    with open(OUT + 'players.csv', 'w', newline='', encoding='utf-8') as fo:
        w = csv.writer(fo); w.writerow(['player_id', 'player', 'pos', 'headshot'])
        for aid, (n, p, h) in sorted(players.items()): w.writerow([aid, n, p, h])
    print(f'teams.csv: {len(T)} teams ({len(fbs)} FBS) · players.csv: {len(players)}')

if __name__ == '__main__':
    arg = [int(a) for a in sys.argv[1:]] or sorted(int(re.findall(r'(\d{4})', f)[-1]) for f in glob.glob(RAW + 'player_box_*.parquet'))
    main(arg)
