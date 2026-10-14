"""Injuries, both sides of the ball, merged from two sources and tied to the roles RAINMAN already tracks.

Sources (newest wins):
  data/raw/espn_injuries_<date>.txt   I|team|player|pos|status|injury|return|date|fantasy|comment   (ESPN injuries feed, pull_espn.injuries, daily)
  data/raw/nflverse/injuries_2026.parquet                                                      (league report: report status + practice participation)
Roles:
  offense  data/processed/depth_charts_<latest>.csv  (slot, effective depth, usage)   defense  data/processed/units_2026.csv (pos, rank)
Output data/processed/injuries_current.csv — one row per listed player:
  team, player, pos, side, role, depth, status, status_w, injury, return, updated, practice, fantasy, comment, source
status_w = how much of the player's role is expected to be lost this week: Out / IR / PUP / Suspended 1 · Doubtful 0.75 · Questionable 0.4 · Day-to-day 0.25 · Active 0
"""
import os, re, csv, glob, json, datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
TEAM_FIX = {'WSH': 'WAS', 'LA': 'LAR', 'JAC': 'JAX'}
W = {'out': 1.0, 'injured reserve': 1.0, 'ir': 1.0, 'pup': 1.0, 'suspension': 1.0, 'suspended': 1.0, 'doubtful': 0.75, 'questionable': 0.4, 'day-to-day': 0.25, 'active': 0.0}
DEF_ROLE = {'LCB': 'CB', 'RCB': 'CB', 'CB': 'CB', 'NB': 'NB', 'NCB': 'NB', 'SCB': 'NB', 'FS': 'S', 'SS': 'S', 'S': 'S',
            'WLB': 'LB', 'MLB': 'LB', 'SLB': 'LB', 'ILB': 'LB', 'OLB': 'LB', 'LOLB': 'EDGE', 'ROLB': 'EDGE', 'LILB': 'LB', 'RILB': 'LB', 'LB': 'LB', 'WILL': 'LB', 'MIKE': 'LB', 'SAM': 'LB',
            'LDE': 'EDGE', 'RDE': 'EDGE', 'DE': 'EDGE', 'LDT': 'DT', 'RDT': 'DT', 'DT': 'DT', 'NT': 'DT', 'LEO': 'EDGE', 'JACK': 'EDGE'}
nk = lambda n: re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', '', str(n).lower()).replace('.', '').replace("'", '').replace('-', ' ').split()
key = lambda n: ' '.join(nk(n))

def main():
    # ---- roles
    depth = sorted(glob.glob('data/processed/depth_charts_*.csv'))
    off = {}
    if depth:
        for r in csv.DictReader(open(depth[-1], encoding='utf-8')):
            off[(r['team'], key(r['player']))] = dict(role=r['slot'], depth=r['depth'], side='OFF', pos=r['pos_row'].rstrip('0123456789'))
    de = {}
    if os.path.exists('data/processed/units_2026.csv'):
        for r in csv.DictReader(open('data/processed/units_2026.csv', encoding='utf-8')):
            if r['unit'] != 'DEF': continue
            role = DEF_ROLE.get(r['pos'], r['pos'])
            de[(r['team'], key(r['player']))] = dict(role=f"{role}{r['rank']}", depth=r['rank'], side='DEF', pos=r['pos'], base=r['front'])
    # ---- ESPN (newest file)
    rows = {}
    files = sorted(glob.glob('data/raw/espn_injuries_*.txt'))
    if files:
        for line in open(files[-1], encoding='utf-8'):
            if not line.startswith('I|'): continue
            p = line.rstrip('\n').split('|')
            if len(p) < 9: continue
            t = TEAM_FIX.get(p[1], p[1]); st = p[4]
            rows[(t, key(p[2]))] = dict(team=t, player=p[2], pos=p[3], status=st, status_w=W.get(st.lower(), 0.5 if st else 0), injury=p[5], ret=p[6], updated=p[7], fantasy=p[8], comment=p[9] if len(p) > 9 else '', practice='', source='espn')
    # ---- nflverse league report: the current week's practice participation and official status
    try:
        import pandas as pd
        f = 'data/raw/nflverse/injuries_2026.parquet'
        if os.path.exists(f):
            I = pd.read_parquet(f); I = I[I.season_type == 'REG']
            wk = int(I.week.max()) if len(I) else 0
            # the league report only counts for the week on the depth chart: last week's Q tags are not this week's
            # the current week = the first week on the schedule with a game still to be played
            try:
                today = datetime.date.today().isoformat()
                cur_wk = min(int(r['week']) for r in csv.DictReader(open('data/processed/games_2026.csv', encoding='utf-8')) if r['date'] >= today)
            except Exception: cur_wk = wk
            if wk < cur_wk: print(f'  nflverse report is week {wk}, the slate is week {cur_wk} — practice trail only from ESPN until the new report lands'); I = I.iloc[0:0]
            # the report of the newest week only counts if that week has not been played: the depth chart holds the current week
            cur = I[I.week == wk]
            prac = {'Full Participation in Practice': 'FP', 'Limited Participation in Practice': 'LP', 'Did Not Participate In Practice': 'DNP'}
            for r in cur.itertuples():
                t = TEAM_FIX.get(r.team, r.team); k = (t, key(r.full_name))
                pr = prac.get(str(r.practice_status), '')
                st = str(r.report_status) if r.report_status and str(r.report_status) != 'None' else ''
                if k in rows:
                    rows[k]['practice'] = pr; rows[k]['nfl_status'] = st; rows[k]['nfl_week'] = wk
                    if not rows[k]['injury'] and r.report_primary_injury: rows[k]['injury'] = str(r.report_primary_injury)
                elif st:
                    rows[k] = dict(team=t, player=str(r.full_name), pos=str(r.position), status=st, status_w=W.get(st.lower(), 0.4), injury=str(r.report_primary_injury or r.practice_primary_injury or ''), ret='', updated='', fantasy='', comment='', practice=pr, source=f'nflverse wk{wk}', nfl_status=st, nfl_week=wk)
                elif pr and pr != 'FP':
                    rows[k] = dict(team=t, player=str(r.full_name), pos=str(r.position), status='Practice ' + pr, status_w=0.25 if pr == 'DNP' else 0.1, injury=str(r.practice_primary_injury or ''), ret='', updated='', fantasy='', comment='', practice=pr, source=f'nflverse wk{wk}', nfl_status='', nfl_week=wk)
    except Exception as e: print('  nflverse injuries skipped:', e)
    out = []
    for (t, k), r in rows.items():
        role = off.get((t, k)) or de.get((t, k)) or {}
        side = role.get('side') or ('DEF' if r['pos'] in DEF_ROLE or r['pos'] in ('DE', 'DT', 'LB', 'CB', 'S', 'NT', 'OLB', 'ILB', 'SAF') else 'OFF' if r['pos'] in ('QB', 'RB', 'WR', 'TE', 'FB') else 'OL/ST' if r['pos'] in ('OT', 'G', 'C', 'OL', 'K', 'P', 'LS') else '')
        out.append(dict(team=t, player=r['player'], pos=r['pos'], side=side, role=role.get('role', ''), depth=role.get('depth', ''), status=r['status'], status_w=round(float(r['status_w']), 2), injury=r['injury'], ret=r['ret'], updated=r['updated'], practice=r.get('practice', ''), fantasy=r['fantasy'], comment=r['comment'], source=r['source']))
    out.sort(key=lambda x: (x['team'], -x['status_w'], x['side'], x['role']))
    cols = ['team', 'player', 'pos', 'side', 'role', 'depth', 'status', 'status_w', 'injury', 'ret', 'updated', 'practice', 'fantasy', 'comment', 'source']
    os.makedirs('data/processed', exist_ok=True)
    with open('data/processed/injuries_current.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
    n_out = sum(1 for x in out if x['status_w'] >= 1); n_q = sum(1 for x in out if 0 < x['status_w'] < 1)
    print(f"injuries_current.csv: {len(out)} listed · {n_out} out/IR · {n_q} questionable/doubtful/limited · {sum(1 for x in out if x['side']=='DEF')} defenders · sources: {'espn ' + files[-1][-14:-4] if files else 'no ESPN file'} + nflverse")

if __name__ == '__main__':
    main()
