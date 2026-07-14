"""Build matchups_current.csv: every rostered player (Fantasy Master Key) joined to
current depth-chart slot, injury, next opponent (2026 week 1), and opponent DvP for his slot.

Usage: python3 build_matchups.py <depth_chart_csv> <week>
"""
import sys, csv, re, unicodedata
import pandas as pd

SLOT_GROUP = {'QB1':'QB','QB2':'QB','QB3':'QB','QB4':'QB','RB1':'RB1','RB2':'RB2','RB3':'RB2','RB4':'RB2',
 'WR1':'WR1','WR2':'WR2','WR3':'WR3','WR4+':'WR4+','TE1':'TE1','TE2':'TE2','TE3':'TE2','TE4':'TE2',
 'FB1':'RB2','FB2':'RB2','FB3':'RB2'}
COMP_COL = {'QB':'QB *','RB1':'RB1 *','RB2':'RB2 *','WR1':'WR1 *','WR2':'WR2 *','WR3':'WR3 *',
            'WR4+':'WR4+ *','TE1':'TE1 *','TE2':'TE2 *'}
GROUP_STATS = {'QB':['QB PY','QB RY','QB P+R','P TD','QB TD'],
 'RB1':['RB1 RY','RB1 Recep','RB1 RecY','RB R+R','RB1 TD'],
 'RB2':['RB2+ RY','RB2 Recep','RB2 RecY','RB R+R','RB2 TD'],
 'WR1':['WR1 Recep','WR1 RecY','WR1 TD'],'WR2':['WR2 Recep','WR2 RecY','WR2 TD'],
 'WR3':['WR3 Recep','WR3 RecY','WR3 TD'],'WR4+':['WR4+ Recep','WR4+ RecY','WR4+ TD'],
 'TE1':['TE1 Recep','TE1 RecY','TE1 TD'],'TE2':['TE2 Recep','TE2 RecY','TE2 TD']}

def norm(n):
    n = unicodedata.normalize('NFKD', str(n)).encode('ascii','ignore').decode()
    n = re.sub(r"[.'\-]", '', n).lower()
    return re.sub(r'\s+(jr|sr|ii|iii|iv|v)$', '', n.strip())

def main(dc_path, week):
    dc = list(csv.DictReader(open(dc_path, encoding='utf-8')))
    mk = pd.read_excel('Fantasy Master Key 2026 2027.xlsx', sheet_name='Overall Rankings', header=1)
    mk = mk.dropna(subset=['Player'])
    mk['Team'] = mk['Team'].astype(str).str.upper().str.strip()
    sched = {r['team']: r for r in csv.DictReader(open('data/processed/schedule_2026.csv'))}
    dvp = pd.read_csv('data/processed/dvp_combined.csv').set_index('defense')

    # index depth chart by (lastname_norm, first_initial, team) and (lastname_norm, team)
    ix = {}
    for r in dc:
        parts = r['player'].split()
        last = norm(parts[-1]); first = parts[0][0].lower()
        for k in [(last, first, r['team']), (last, r['team'])]:
            ix.setdefault(k, r)
        if len(parts) > 2:  # suffix names: index second-to-last token too
            ix.setdefault((norm(parts[-2]), first, r['team']), r)

    out, unmatched = [], []
    for _, m in mk.iterrows():
        pos = str(m.get('Pos.','')).upper().strip()
        if pos not in ('QB','RB','WR','TE','D/ST','DST','K'): continue
        team = m['Team']; nm = str(m['Player']).strip()
        owner = m.get('Owner'); owner = '' if pd.isna(owner) else str(owner)
        parts = nm.replace('.',' ').split()
        last = norm(parts[-1]); first = parts[0][0].lower() if parts else ''
        d = ix.get((last, first, team)) or ix.get((last, team))
        slot = d['slot'] if d else ''
        inj = d['injury'] if d else ''
        full = d['player'] if d else nm
        if not d and pos in ('QB','RB','WR','TE'): unmatched.append(f'{nm} ({team} {pos})')
        grp = SLOT_GROUP.get(slot, '')
        opp_cell = sched.get(team, {}).get(f'week_{week}', '')
        opp = opp_cell.lstrip('@') if opp_cell and opp_cell != 'BYE' else opp_cell
        row = {'player': full, 'mk_name': nm, 'team': team, 'pos': pos, 'slot': slot,
               'slot_group': grp, 'injury': inj, 'owner': owner, 'week': week,
               'opponent': opp_cell, 'composite': '', 'stat_ranks': ''}
        dkey = opp
        if grp and dkey in dvp.index:
            row['composite'] = dvp.loc[dkey, COMP_COL[grp]]
            row['stat_ranks'] = ';'.join(f"{c}={dvp.loc[dkey, c+' rank']:g}" for c in GROUP_STATS[grp])
        out.append(row)
    with open('data/processed/matchups_current.csv','w',newline='',encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    print(f'matchups_current.csv: {len(out)} rostered/ranked players, {len(unmatched)} unmatched vs depth chart')
    if unmatched:
        open('notes/matchup_unmatched.md','w',encoding='utf-8').write(
            '# Master Key players not matched to ESPN depth chart\n\n' +
            '\n'.join(f'- {u}' for u in unmatched))

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1)
