"""NCAA DvP: the NFL compute_dvp functions (same 34 legacy stat columns, same rank convention: 1 = most allowed)
applied to ncaa/data/game_logs/, restricted to FBS defenses.

Usage: python3 scripts/ncaa/compute_dvp.py
Reads  ncaa/data/game_logs/game_logs_*.csv + ncaa/data/processed/teams.csv
Writes ncaa/data/processed/dvp_weekly.csv, dvp_season_{s}.csv, dvp_season.csv, dvp_combined.csv
Every offense that faced an FBS defense counts toward what that defense allowed (FCS opponents included — a 60-point
cupcake is part of the season average, exactly as the per-game legacy convention treats it); FCS defenses get no row
because they are never a matchup for an FBS skill player. Blend: current season weighted 2x once >= 4 weeks exist.
"""
import os, sys, csv, glob
import pandas as pd
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from compute_dvp import STAT_COLS, COMPOSITES, build_weekly, season_table
os.chdir(ROOT)
P = 'ncaa/data/processed/'
CURRENT = 2026

def main():
    fbs = {r['code'] for r in csv.DictReader(open(P + 'teams.csv', encoding='utf-8')) if r['classification'] == 'fbs'}
    all_weekly, seasons = [], []
    for f in sorted(glob.glob('ncaa/data/game_logs/game_logs_*.csv')):
        season = int(f.split('_')[-1].split('.')[0]); seasons.append(season)
        logs = []
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r['opponent'] not in fbs: continue
            for k in ('week', 'pass_yds', 'pass_td', 'rush_yds', 'rush_td', 'rec', 'rec_yds', 'rec_td'): r[k] = int(r[k])
            logs.append(r)
        all_weekly += build_weekly(season, logs, [])
    wdf = pd.DataFrame(all_weekly).sort_values(['season', 'defense', 'week'])
    wdf.to_csv(P + 'dvp_weekly.csv', index=False)
    per = {}
    for s in seasons:
        t = season_table(wdf[wdf.season == s]); t.insert(0, 'season', s)
        t.to_csv(P + f'dvp_season_{s}.csv', index=False); per[s] = t
    per[max(seasons)].to_csv(P + 'dvp_season.csv', index=False)
    frames, used = [], []
    for s, t in per.items():
        weight = 2 if (s == CURRENT and wdf[wdf.season == s].week.nunique() >= 4) else 1
        if s == CURRENT and weight == 1 and len(per) > 1: continue
        a = t.set_index('defense')[[c + ' avg' for c in STAT_COLS]]
        used.append(f'{s}x2' if weight == 2 else str(s))
        for _ in range(weight): frames.append(a)
    # defenses that did not exist in every season (new FBS members) blend over the seasons they have
    comb_avg = pd.concat(frames).groupby(level=0).mean(); comb_avg.columns = STAT_COLS
    ranks = comb_avg.rank(ascending=False, method='average')
    comb = comb_avg.round(2).add_suffix(' avg').join(ranks.add_suffix(' rank'))
    for slot, cols in COMPOSITES.items(): comb[f'{slot} *'] = ranks[cols].mean(axis=1).round(2)
    comb.insert(0, 'seasons_blended', '+'.join(used))
    comb.reset_index().to_csv(P + 'dvp_combined.csv', index=False)
    print(f'dvp_weekly: {len(wdf)} rows · defenses: ' + ', '.join(f'{s}={per[s].shape[0]}' for s in seasons) + f' · combined blends {"+".join(used)} ({len(comb)} defenses)')

if __name__ == '__main__':
    main()
