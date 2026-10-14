"""Build matchups_current.csv: every player on the effective depth chart (QB / RB / WR / TE / FB) plus one D/ST per
team, joined to his slot, injury flag, this week's opponent and the opponent's combined DvP ranks for his slot.

The universe used to come from the preseason Fantasy Master Key workbook (a 300-player draft sheet with league owners);
that left every player who emerged after the draft out of the file and carried 30 retired / moved names. The depth
chart IS the universe now — the same rule the NCAA layer has always used. Columns are unchanged (mk_name = player,
owner = '' — the roster/owner filter was retired with the workbook).

Usage: python3 build_matchups.py <depth_chart_csv> <week>
"""
import os, sys, csv, re, unicodedata
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

def main(dc_path, week):
    dc = list(csv.DictReader(open(dc_path, encoding='utf-8')))
    sched = {r['team']: r for r in csv.DictReader(open('data/processed/schedule_2026.csv'))}
    dvp = pd.read_csv('data/processed/dvp_combined.csv').set_index('defense')
    out = []
    def row_for(player, team, pos, slot, inj):
        grp = SLOT_GROUP.get(slot, '')
        cell = sched.get(team, {}).get(f'week_{week}', '')
        opp = cell.lstrip('@') if cell and cell != 'BYE' else cell
        row = {'player': player, 'mk_name': player, 'team': team, 'pos': pos, 'slot': slot, 'slot_group': grp,
               'injury': inj, 'owner': '', 'week': week, 'opponent': cell, 'composite': '', 'stat_ranks': ''}
        if grp and opp in dvp.index:
            row['composite'] = dvp.loc[opp, COMP_COL[grp]]
            row['stat_ranks'] = ';'.join(f"{c}={dvp.loc[opp, c+' rank']:g}" for c in GROUP_STATS[grp])
        return row
    seen = set()
    for r in dc:
        pos = r['pos_row'].rstrip('0123456789+')
        if pos == 'FB': pos = 'RB'
        if pos not in ('QB', 'RB', 'WR', 'TE'): continue
        key = (r['player'], r['team'])
        if key in seen: continue
        seen.add(key)
        out.append(row_for(r['player'], r['team'], pos, r['slot'], r['injury']))
    for team in sorted(sched):
        if team in dvp.index or team in {r['team'] for r in dc}:
            out.append(row_for(f'{team} D/ST', team, 'D/ST', '', '1'))
    with open('data/processed/matchups_current.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    byes = sorted({r['team'] for r in out if r['opponent'] == 'BYE'})
    print(f'matchups_current.csv: {len(out)} depth-chart players + D/ST · week {week} · byes {", ".join(byes) or "none"}')
    if os.path.exists('notes/matchup_unmatched.md'): os.remove('notes/matchup_unmatched.md')   # the Master Key join is gone

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if sys.argv[2].isdigit() else sys.argv[2])
