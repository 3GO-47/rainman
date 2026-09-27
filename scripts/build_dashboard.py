"""Assemble dashboard/rainman.html from scripts/dashboard_template.html + embedded JSON.
Usage: python3 build_dashboard.py
Every number traces to data/game_logs/ via the derived CSVs. Rerun after any data refresh.
"""
import re, csv, glob, json, os, datetime
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

COV_COLS = ['man_rate','zone_rate','cover0','cover1','cover2','cover3','cover4','cover6','two_man','cover_other','single_high','two_high',
            'base_rate','nickel_rate','dime_rate','four_down_rate','pressure_rate']
def intel_payload():
    """Scheme / tendency / turnover / coaching layer from build_advanced.py outputs (nflverse + FTN charting)."""
    P = 'data/processed/'
    if not os.path.exists(P + 'scheme_tags.csv'): return None
    def num(v, d=3):
        if v is None or v == '' or v == 'nan': return None
        if v in ('True', 'False'): return v == 'True'
        try: return round(float(v), d)
        except ValueError: return v
    def by_season_team(path, keys=('season', 'team'), side=None):
        out = {}
        for r in csv.DictReader(open(path, encoding='utf-8')):
            d = out.setdefault(r['season'], {}).setdefault(r['team'], {})
            row = {k: (v if k in ('coverage_source','evidence','descriptors','primary_tag','coach','coach_from','departed','new_starters','cur_starter_names',
                                 'hc','oc','dc','hc_prev','oc_prev','dc_prev','hc_from','oc_from','dc_from','side','team','season') else num(v))
                   for k, v in r.items() if k not in keys}
            if side and 'side' in r: d[r['side']] = row
            else: d.update(row)
        return out
    intel = {'off': by_season_team(P + 'team_off_tendencies.csv'),
             'def': by_season_team(P + 'team_def_tendencies.csv'),
             'tags': by_season_team(P + 'scheme_tags.csv', side=True),
             'turnover': by_season_team(P + 'starter_turnover.csv', side=True) if os.path.exists(P + 'starter_turnover.csv') else {},
             'coaching': by_season_team(P + 'coaching.csv') if os.path.exists(P + 'coaching.csv') else {},
             'schemeSlot': [{k: num(v, 2) if k not in ('family', 'grp') else v for k, v in r.items()}
                            for r in csv.DictReader(open(P + 'scheme_slot_effects.csv', encoding='utf-8'))] if os.path.exists(P + 'scheme_slot_effects.csv') else []}
    # coverage for uncharted seasons: mirror the same fallback tag_defense used (new DC's prior unit, else same team prior season)
    for s in sorted(intel['def']):
        for t, row in intel['def'][s].items():
            if row.get('coverage_charted') is True and row.get('two_high') is not None: continue
            src = (intel['tags'].get(s, {}).get(t, {}).get('DEF') or {}).get('coverage_source', '')
            m = re.search(r'^(\d{4}) charting.*prior unit \((\w+)\)', src) or re.search(r'^(\d{4}) charting', src)
            if not m: continue
            ss, st = m.group(1), (m.group(2) if m.lastindex == 2 else t)
            base = intel['def'].get(ss, {}).get(st)
            if not base: continue
            for c in COV_COLS: row[c] = base.get(c)
            row['cov_est'] = f'{ss} {st}'
    return intel

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

    # usage layer (build_advanced.py: game_logs x nflverse snap counts / pbp) -> appended to each log row
    usage = {}
    if os.path.exists('data/processed/player_usage.csv'):
        for r in csv.DictReader(open('data/processed/player_usage.csv', encoding='utf-8')):
            f4 = lambda k, d=3: (round(float(r[k]), d) if r[k] not in ('', 'nan') else None)
            usage[(int(r['season']), int(r['week']), r['player_id'])] = [f4('snaps', 0), f4('snap_pct'), f4('target_share'), f4('adot', 1), f4('rush_share'), f4('wopr')]
    logs = []
    for f in sorted(glob.glob('data/game_logs/game_logs_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            logs.append([r['player'], r['player_id'], int(r['season']), int(r['week']), r['team'],
                r['opponent'], r['home_away'], r['slot'], r['pos'], int(r['pass_yds']), int(r['pass_td']),
                int(r['pass_att']), int(r['int']), int(r['rush_att']), int(r['rush_yds']), int(r['rush_td']),
                int(r['targets']), int(r['rec']), int(r['rec_yds']), int(r['rec_td']),
                float(r['fantasy_pts_std']), float(r['fantasy_pts_ppr'])]
                + usage.get((int(r['season']), int(r['week']), r['player_id']), [None] * 6))
    data['logs'] = logs
    data['intel'] = intel_payload()

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
