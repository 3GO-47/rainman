"""Full data-integrity audit. Recomputes the entire DvP layer INDEPENDENTLY (pandas,
different code path than compute_dvp.py) from data/game_logs/ and compares every cell.
Also checks raw-layer coverage, rank math, combined blend, dashboard payload, fantasy
point formulas, slot utilization, and D/ST attribution.

Usage: python3 verify_data.py   -> prints report + writes notes/data_audit_<date>.md
"""
import csv, glob, json, re, datetime
import pandas as pd
import numpy as np

REPORT = []
FAIL = []
def ok(name, cond, detail=''):
    line = f'{"PASS" if cond else "FAIL"}  {name}' + (f' — {detail}' if detail else '')
    REPORT.append(line)
    if not cond: FAIL.append(line)

STAT_COLS = ['QB PY','P TD','QB RY','RB1 RY','RB2+ RY','WR RY','RB1 Recep','RB1 RecY',
 'RB2 Recep','RB2 RecY','WR1 Recep','WR1 RecY','WR2 Recep','WR2 RecY','WR3 Recep','WR3 RecY',
 'WR4+ Recep','WR4+ RecY','TE1 Recep','TE1 RecY','TE2 Recep','TE2 RecY','QB TD','RB1 TD',
 'RB2 TD','WR1 TD','WR2 TD','WR3 TD','WR4+ TD','TE1 TD','TE2 TD','D/ST TD','QB P+R','RB R+R']

def independent_weekly(logs, dst):
    """Recompute defense-week stat matrix from raw game logs with fresh pandas logic."""
    g = logs.copy()
    g['bucket'] = g['slot'].replace({'QB1':'QB','QB2':'QB','RB3':'RB2','TE3':'TE2'})
    out = {}
    for (d, w), sub in g.groupby(['opponent','week']):
        r = dict.fromkeys(STAT_COLS, 0)
        qb = sub[sub['pos']=='QB']
        r['QB PY'] = qb['pass_yds'].sum(); r['P TD'] = qb['pass_td'].sum()
        r['QB RY'] = qb['rush_yds'].sum()
        r['QB TD'] = (qb['rush_td']+qb['rec_td']).sum()
        r['QB P+R'] = r['QB PY']+r['QB RY']
        rb = sub[sub['pos']=='RB']
        r['RB R+R'] = (rb['rush_yds']+rb['rec_yds']).sum()
        for b_in, b_out in [('RB1','RB1'),('RB2','RB2')]:
            x = rb[rb['bucket']==b_in]
            r[f'{b_out} RY' if b_out=='RB1' else 'RB2+ RY'] = x['rush_yds'].sum()
            r[f'{b_out} Recep'] = x['rec'].sum(); r[f'{b_out} RecY'] = x['rec_yds'].sum()
            r[f'{b_out} TD'] = (x['rush_td']+x['rec_td']).sum()
        wr = sub[sub['pos']=='WR']
        r['WR RY'] = wr['rush_yds'].sum()
        for b in ['WR1','WR2','WR3','WR4+']:
            x = wr[wr['bucket']==b]
            r[f'{b} Recep'] = x['rec'].sum(); r[f'{b} RecY'] = x['rec_yds'].sum()
            r[f'{b} TD'] = (x['rush_td']+x['rec_td']).sum()
        te = sub[sub['pos']=='TE']
        for b in ['TE1','TE2']:
            x = te[te['bucket']==b]
            r[f'{b} Recep'] = x['rec'].sum(); r[f'{b} RecY'] = x['rec_yds'].sum()
            r[f'{b} TD'] = (x['rush_td']+x['rec_td']).sum()
        out[(d,w)] = r
    for _, row in dst.iterrows():
        key = (row['opponent'], row['week'])
        if key in out: out[key]['D/ST TD'] += row['dst_tds']
    return out

def main():
    seasons = sorted(int(f.split('_')[-1].split('.')[0]) for f in glob.glob('data/game_logs/game_logs_*.csv'))
    wdf = pd.read_csv('data/processed/dvp_weekly.csv')

    for se in seasons:
        logs = pd.read_csv(f'data/game_logs/game_logs_{se}.csv')
        games = pd.read_csv(f'data/processed/games_{se}.csv')
        dst = pd.read_csv(f'data/processed/dst_tds_{se}.csv')
        raw = open(f'data/raw/box_lines_{se}.txt', encoding='utf-8').read().splitlines()
        plines = [l for l in raw if l.startswith('P|')]
        # --- raw layer ---
        ok(f'{se} raw: 272 unique boxscores', len({l.split("|")[1] for l in plines})==272)
        ok(f'{se} raw: zero ERR lines', not any(l.startswith('ERR') for l in raw))
        ok(f'{se} raw: all P lines have 18 fields', all(len(l.split('|'))==18 for l in plines))
        dup = len(plines) - len({(l.split('|')[1], l.split('|')[2]) for l in plines})
        ok(f'{se} raw: no duplicate (game,player) rows', dup==0, f'{dup} dups')
        ok(f'{se} logs rows == raw P lines', len(logs)==len(plines), f'{len(logs)} vs {len(plines)}')
        # --- coverage ---
        tg = logs.groupby(['team','week']).size().reset_index()
        per_team = tg.groupby('team').size()
        ok(f'{se} coverage: 32 teams x 17 games', (per_team==17).all() and len(per_team)==32,
           f'min {per_team.min()} max {per_team.max()}')
        gm = logs.groupby(['week','team','opponent']).ngroups
        ok(f'{se} coverage: 544 team-games', gm==544, str(gm))
        # both sides of each game present + opponents reciprocal
        pairs = set(map(tuple, logs[['week','team','opponent']].drop_duplicates().values))
        ok(f'{se} reciprocity: every (wk,A,B) has (wk,B,A)',
           all((w,o,t) in pairs for (w,t,o) in pairs))
        # schedule match
        sched_pairs = set()
        for _, r in games.iterrows():
            sched_pairs.add((r['week'], r['vis'], r['home'])); sched_pairs.add((r['week'], r['home'], r['vis']))
        ok(f'{se} logs match schedule exactly', pairs==sched_pairs,
           f'{len(pairs^sched_pairs)} mismatches')
        # --- fantasy points formula ---
        std = logs['pass_yds']/25 + logs['pass_td']*4 - logs['int']*2 + logs['rush_yds']/10 \
              + logs['rush_td']*6 + logs['rec_yds']/10 + logs['rec_td']*6 - logs['fumbles_lost']*2
        ok(f'{se} fantasy_pts_std formula exact', (abs(std.round(2)-logs['fantasy_pts_std'])<0.011).all())
        ok(f'{se} ppr = std + rec', (abs((logs['fantasy_pts_std']+logs['rec']).round(2)-logs['fantasy_pts_ppr'])<0.011).all())
        # --- slot utilization: every row lands in a DvP bucket ---
        ok(f'{se} all rows have valid pos', logs['pos'].isin(['QB','RB','WR','TE']).all())
        ok(f'{se} all rows have a slot', logs['slot'].notna().all() and (logs['slot']!='').all())
        # --- independent DvP recompute, EVERY cell ---
        ind = independent_weekly(logs, dst)
        w_se = wdf[wdf.season==se]
        ok(f'{se} dvp_weekly rows = 544', len(w_se)==544, str(len(w_se)))
        bad = 0; checked = 0
        for _, row in w_se.iterrows():
            r2 = ind.get((row['defense'], row['week']))
            for c in STAT_COLS:
                checked += 1
                if abs(float(row[c]) - float(r2[c])) > 0.001: bad += 1
        ok(f'{se} independent recompute of all {checked} weekly cells', bad==0, f'{bad} mismatches')
        # --- season table: averages + ranks ---
        st = pd.read_csv(f'data/processed/dvp_season_{se}.csv')
        m = w_se.groupby('defense')[STAT_COLS].mean()
        st_i = st.set_index('defense')
        avg_bad = sum(1 for d in m.index for c in STAT_COLS
                      if abs(round(m.loc[d,c],2) - st_i.loc[d, c+' avg']) > 0.011)
        ok(f'{se} season averages match weekly means', avg_bad==0, f'{avg_bad} cells off')
        rank_bad = 0
        for c in STAT_COLS:
            expect = m[c].rank(ascending=False, method='average')
            got = st_i[c+' rank']
            rank_bad += int((abs(expect - got) > 0.001).sum())
            if not np.isclose(sorted(expect.values), sorted(got.values)).all(): rank_bad += 1
        ok(f'{se} ranks: descending RANK.AVG, rank1 = most allowed', rank_bad==0, f'{rank_bad} off')

    # --- combined blend ---
    comb = pd.read_csv('data/processed/dvp_combined.csv').set_index('defense')
    s24 = pd.read_csv('data/processed/dvp_season_2024.csv').set_index('defense')
    s25 = pd.read_csv('data/processed/dvp_season_2025.csv').set_index('defense')
    blend_bad = sum(1 for d in comb.index for c in STAT_COLS
        if abs((s24.loc[d,c+' avg']+s25.loc[d,c+' avg'])/2 - comb.loc[d,c+' avg']) > 0.011)
    ok('combined = equal-weight mean of 2024+2025 (every cell)', blend_bad==0, f'{blend_bad} off')
    # composite spot: QB * = mean of its 5 stat ranks
    qb_cols = ['QB PY','QB RY','QB P+R','P TD','QB TD']
    comp_bad = sum(1 for d in comb.index
        if abs(np.mean([comb.loc[d,c+' rank'] for c in qb_cols]) - comb.loc[d,'QB *']) > 0.011)
    ok('composite * = mean of group stat ranks (QB, all 32)', comp_bad==0, f'{comp_bad} off')

    # --- D/ST attribution ---
    for se in seasons:
        dst = pd.read_csv(f'data/processed/dst_tds_{se}.csv')
        raw_d = [l.split('|') for l in open(f'data/raw/box_lines_{se}.txt',encoding='utf-8') if l.startswith('D|')]
        ok(f'{se} D/ST rows match raw D lines', len(dst)==len(raw_d), f'{len(dst)} vs {len(raw_d)}')
        ok(f'{se} D/ST totals match', dst['dst_tds'].sum()==sum(int(x[3]) for x in raw_d))

    # --- dashboard payload equals CSV layer ---
    h = open('dashboard/rainman.html', encoding='utf-8').read()
    J = json.loads(re.search(r'const J = (\{.*?\});\n', h, re.S).group(1))
    pay_bad = 0
    for d in comb.index:
        for c in STAT_COLS:
            if abs(J['dvp']['combined'][d]['stats'][c]['avg'] - round(comb.loc[d,c+' avg'],2)) > 0.011: pay_bad += 1
            if abs(J['dvp']['combined'][d]['stats'][c]['rank'] - comb.loc[d,c+' rank']) > 0.001: pay_bad += 1
    ok('dashboard payload == dvp_combined.csv (2176 cells)', pay_bad==0, f'{pay_bad} off')
    ok('dashboard logs == game_logs rows', len(J['logs'])==10702, str(len(J['logs'])))
    ok('dashboard weekly == 1088 defense-weeks', len(J['weekly'])==1088, str(len(J['weekly'])))
    # weekly column order matches WCOL convention (defense,season,week,opp + STAT_COLS)
    w0 = J['weekly'][0]
    csv_row = wdf[(wdf.defense==w0[0])&(wdf.season==w0[1])&(wdf.week==w0[2])].iloc[0]
    ok('dashboard weekly column order correct',
       all(abs(w0[i+4]-round(float(csv_row[c]),1))<0.06 for i,c in enumerate(STAT_COLS)))
    # schedule payload
    ok('dashboard sched26: 32 teams x 18 wks, 32 byes',
       len(J['sched26'])==32 and sum(v.count('BYE') for v in J['sched26'].values())==32)

    date = datetime.date.today().isoformat()
    hdr = [f'# Data integrity audit — {date}', '',
           f'**{len(REPORT)-len(FAIL)}/{len(REPORT)} checks passed**', '']
    open(f'notes/data_audit_{date}.md','w',encoding='utf-8').write('\n'.join(hdr+REPORT))
    print('\n'.join(REPORT))
    print(f'\n{len(REPORT)-len(FAIL)}/{len(REPORT)} PASSED')
    if FAIL: print('FAILURES:\n' + '\n'.join(FAIL))

if __name__ == '__main__':
    main()
