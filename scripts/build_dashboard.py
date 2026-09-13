"""Assemble dashboard/rainman.html from scripts/dashboard_template.html + embedded JSON.
Usage: python3 build_dashboard.py
Every number traces to data/game_logs/ via the derived CSVs. Rerun after any data refresh.
"""
import csv, glob, json, os, datetime
import pandas as pd

STAT_COLS = ['QB PY','P TD','QB RY','RB1 RY','RB2+ RY','WR RY','RB1 Recep','RB1 RecY',
 'RB2 Recep','RB2 RecY','WR1 Recep','WR1 RecY','WR2 Recep','WR2 RecY','WR3 Recep','WR3 RecY',
 'WR4+ Recep','WR4+ RecY','TE1 Recep','TE1 RecY','TE2 Recep','TE2 RecY','QB TD','RB1 TD',
 'RB2 TD','WR1 TD','WR2 TD','WR3 TD','WR4+ TD','TE1 TD','TE2 TD','D/ST TD','QB P+R','RB R+R']
SLOTS = ['QB','RB1','RB2','WR1','WR2','WR3','WR4+','TE1','TE2','D/ST']
GROUP_STATS = {'QB':['QB PY','QB RY','QB P+R','P TD','QB TD'],
 'RB1':['RB1 RY','RB1 Recep','RB1 RecY','RB R+R','RB1 TD'],
 'RB2':['RB2+ RY','RB2 Recep','RB2 RecY','RB R+R','RB2 TD'],
 'WR1':['WR1 Recep','WR1 RecY','WR1 TD'],'WR2':['WR2 Recep','WR2 RecY','WR2 TD'],
 'WR3':['WR3 Recep','WR3 RecY','WR3 TD'],'WR4+':['WR4+ Recep','WR4+ RecY','WR4+ TD'],
 'TE1':['TE1 Recep','TE1 RecY','TE1 TD'],'TE2':['TE2 Recep','TE2 RecY','TE2 TD'],
 'D/ST':['D/ST TD']}
PRIMARY = {'QB':'QB PY','RB1':'RB1 RY','RB2':'RB2+ RY','WR1':'WR1 RecY','WR2':'WR2 RecY',
 'WR3':'WR3 RecY','WR4+':'WR4+ RecY','TE1':'TE1 RecY','TE2':'TE2 RecY','D/ST':'D/ST TD'}

def dvp_table(path):
    df = pd.read_csv(path)
    out = {}
    for _, r in df.iterrows():
        d = r['defense']
        out[d] = {'stats': {c: {'avg': round(float(r[c+' avg']), 2), 'rank': float(r[c+' rank'])}
                            for c in STAT_COLS},
                  'comps': {s: float(r[s+' *']) for s in SLOTS if (s+' *') in df.columns}}
    return out

def main():
    data = {'built': str(datetime.date.today()), 'statCols': STAT_COLS, 'slots': SLOTS,
            'groupStats': GROUP_STATS, 'primary': PRIMARY}
    data['dvp'] = {}
    for f in sorted(glob.glob('data/processed/dvp_season_[0-9]*.csv')):
        data['dvp'][f.split('_')[-1].split('.')[0]] = dvp_table(f)
    data['dvp']['combined'] = dvp_table('data/processed/dvp_combined.csv')
    data['blend'] = pd.read_csv('data/processed/dvp_combined.csv')['seasons_blended'].iloc[0]

    wk = pd.read_csv('data/processed/dvp_weekly.csv')
    data['weekly'] = [[r['defense'], int(r['season']), int(r['week']), r['opponent']] +
                      [round(float(r[c]), 1) for c in STAT_COLS] for _, r in wk.iterrows()]

    logs = []
    for f in sorted(glob.glob('data/game_logs/game_logs_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            logs.append([r['player'], r['player_id'], int(r['season']), int(r['week']), r['team'],
                r['opponent'], r['home_away'], r['slot'], r['pos'], int(r['pass_yds']), int(r['pass_td']),
                int(r['pass_att']), int(r['int']), int(r['rush_att']), int(r['rush_yds']), int(r['rush_td']),
                int(r['targets']), int(r['rec']), int(r['rec_yds']), int(r['rec_td']),
                float(r['fantasy_pts_std']), float(r['fantasy_pts_ppr'])])
    data['logs'] = logs

    data['matchups'] = list(csv.DictReader(open('data/processed/matchups_current.csv', encoding='utf-8')))
    sched = {}
    for r in csv.DictReader(open('data/processed/schedule_2026.csv')):
        sched[r['team']] = [r[f'week_{i}'] for i in range(1, 19)]
    data['sched26'] = sched
    # games26 row: [week, vis, home, date, day, time_et, slate] — kickoff cols from kickoffs_2026.csv
    kick = {}
    if os.path.exists('data/processed/kickoffs_2026.csv'):
        for r in csv.DictReader(open('data/processed/kickoffs_2026.csv')):
            kick[(int(r['week']), r['vis'], r['home'])] = (r['day'], r['time_et'], r['slate'])
    data['games26'] = [[int(r['week']), r['vis'], r['home'], r['date']] +
                       list(kick.get((int(r['week']), r['vis'], r['home']), ('', '', 'TBD')))
                       for r in csv.DictReader(open('data/processed/games_2026.csv'))]
    # current 2026/27 matchup week (set by refresh.py via build_matchups.py)
    data['week'] = int(data['matchups'][0]['week']) if data['matchups'] else 1
    dcp = sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1]
    data['depth'] = list(csv.DictReader(open(dcp, encoding='utf-8')))
    data['depthDate'] = dcp.split('_')[-1][:10]

    def np_default(o):
        import numpy as np
        if isinstance(o, np.integer): return int(o)
        if isinstance(o, np.floating): return float(o)
        raise TypeError(type(o))
    payload = json.dumps(data, separators=(',', ':'), default=np_default)
    template = open('scripts/dashboard_template.html', encoding='utf-8').read()
    html = template.replace('__DATA__', payload)
    os.makedirs('dashboard', exist_ok=True)
    open('dashboard/rainman.html', 'w', encoding='utf-8').write(html)
    print(f'dashboard/rainman.html written: {len(html)//1024} KB, logs={len(logs)}, '
          f'weekly={len(data["weekly"])}, matchups={len(data["matchups"])}')

if __name__ == '__main__':
    main()
