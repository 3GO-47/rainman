"""NCAA: usage-derived depth chart snapshot + this week's matchup table for every FBS skill player.

Usage: python3 scripts/ncaa/build_depth_matchups.py [--week N]
Outputs: ncaa/data/processed/depth_charts_{today}.csv   player, team, slot, injury, pos_row, depth
         ncaa/data/processed/matchups_current.csv       same columns as the NFL table (owner / mk_name blank — no fantasy league)

Depth chart: there is no public college depth-chart feed, so the chart is the team's own usage — each player's carries +
receptions (RB), receptions (WR / TE) or pass attempts (QB) over the team's last three games, the most recent game counted
twice, ranked within position. Kept: 2 QB, 3 RB, 5 WR, 2 TE. Injury flags are unknown (1 = assumed active); a starter who
missed the latest game drops in the ranking naturally. Snapshot date = run date, like the ESPN snapshots on the NFL side.
Week: the first week of the current season with an unplayed game (CFBD `completed`), overridable with --week.
"""
import os, sys, csv, datetime, glob
from collections import defaultdict
import pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
P = 'ncaa/data/processed/'
SEASON = 2026
SLOT_GROUP = {'QB1': 'QB', 'QB2': 'QB', 'RB1': 'RB1', 'RB2': 'RB2', 'RB3': 'RB2', 'WR1': 'WR1', 'WR2': 'WR2', 'WR3': 'WR3', 'WR4+': 'WR4+', 'TE1': 'TE1', 'TE2': 'TE2'}
COMP_COL = {'QB': 'QB *', 'RB1': 'RB1 *', 'RB2': 'RB2 *', 'WR1': 'WR1 *', 'WR2': 'WR2 *', 'WR3': 'WR3 *', 'WR4+': 'WR4+ *', 'TE1': 'TE1 *', 'TE2': 'TE2 *'}
GROUP_STATS = {'QB': ['QB PY', 'QB RY', 'QB P+R', 'P TD', 'QB TD'], 'RB1': ['RB1 RY', 'RB1 Recep', 'RB1 RecY', 'RB R+R', 'RB1 TD'],
               'RB2': ['RB2+ RY', 'RB2 Recep', 'RB2 RecY', 'RB R+R', 'RB2 TD'], 'WR1': ['WR1 Recep', 'WR1 RecY', 'WR1 TD'], 'WR2': ['WR2 Recep', 'WR2 RecY', 'WR2 TD'],
               'WR3': ['WR3 Recep', 'WR3 RecY', 'WR3 TD'], 'WR4+': ['WR4+ Recep', 'WR4+ RecY', 'WR4+ TD'], 'TE1': ['TE1 Recep', 'TE1 RecY', 'TE1 TD'], 'TE2': ['TE2 Recep', 'TE2 RecY', 'TE2 TD']}
KEEP = {'QB': 2, 'RB': 3, 'WR': 5, 'TE': 2}

def main():
    week = int(sys.argv[sys.argv.index('--week') + 1]) if '--week' in sys.argv else None
    games = list(csv.DictReader(open(P + f'games_{SEASON}.csv', encoding='utf-8')))
    if week is None:
        pend = [int(g['week']) for g in games if g['completed'] != '1' and int(g['week']) >= 1]
        week = min(pend) if pend else max(int(g['week']) for g in games)
    teams = {r['code']: r for r in csv.DictReader(open(P + 'teams.csv', encoding='utf-8'))}
    fbs = sorted(c for c, r in teams.items() if r['classification'] == 'fbs')
    L = pd.read_csv(f'ncaa/data/game_logs/game_logs_{SEASON}.csv')
    L = L[L.team.isin(fbs)]
    L['usage'] = L.apply(lambda r: r.pass_att if r.pos == 'QB' else (r.rush_att + r.rec if r.pos == 'RB' else r.rec), axis=1)
    depth = []
    for t, g in L.groupby('team'):
        wks = sorted(g.week.unique())[-3:]
        g = g[g.week.isin(wks)].copy()
        g['w'] = g.week.map(lambda w: 2.0 if w == wks[-1] else 1.0)
        u = (g.usage * g.w).groupby([g.player_id, g.player, g.pos]).sum().reset_index(name='u')
        for pos, grp in u.groupby('pos'):
            grp = grp.sort_values(['u', 'player'], ascending=[False, True]).head(KEEP[pos])
            for i, r in enumerate(grp.itertuples(), 1):
                slot = f'{pos}{i}' if not (pos == 'WR' and i > 3) else 'WR4+'
                depth.append({'player': r.player, 'team': t, 'slot': slot, 'injury': '1', 'pos_row': pos if pos != 'WR' else f'WR{min(i, 4)}', 'depth': i, 'player_id': r.player_id})
    today = str(datetime.date.today())
    with open(P + f'depth_charts_{today}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['player', 'team', 'slot', 'injury', 'pos_row', 'depth', 'player_id']); w.writeheader(); w.writerows(depth)
    for old in glob.glob(P + 'depth_charts_*.csv'):
        if old != P + f'depth_charts_{today}.csv': os.remove(old)   # usage snapshots are fully reproducible from the logs
    sched = {r['team']: r for r in csv.DictReader(open(P + f'schedule_{SEASON}.csv', encoding='utf-8'))}
    dvp = pd.read_csv(P + 'dvp_combined.csv').set_index('defense')
    out = []
    for d in depth:
        grp = SLOT_GROUP.get(d['slot'], '')
        cell = sched.get(d['team'], {}).get(f'week_{week}', '')
        opp = cell.lstrip('@') if cell and cell != 'BYE' else cell
        row = {'player': d['player'], 'mk_name': d['player'], 'team': d['team'], 'pos': d['slot'][:2], 'slot': d['slot'], 'slot_group': grp,
               'injury': '1', 'owner': '', 'week': week, 'opponent': cell, 'composite': '', 'stat_ranks': ''}
        if grp and opp in dvp.index:
            row['composite'] = dvp.loc[opp, COMP_COL[grp]]
            row['stat_ranks'] = ';'.join(f"{c}={dvp.loc[opp, c + ' rank']:g}" for c in GROUP_STATS[grp])
        out.append(row)
    with open(P + 'matchups_current.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    nb = sum(1 for r in out if r['opponent'] == 'BYE') // 12
    print(f'depth_charts_{today}.csv: {len(depth)} players on {len(fbs)} FBS teams · matchups_current.csv: {len(out)} rows · week {week} · ~{nb} teams on bye')

if __name__ == '__main__':
    main()
