"""Compute DvP tables from game logs. Mirrors the legacy NFLLLLL.xlsx Data-tab conventions.

Usage: python3 compute_dvp.py
Reads every data/game_logs/game_logs_*.csv (+ data/processed/dst_tds_*.csv, schedule csvs).
Writes: data/processed/dvp_weekly.csv    (defense,season,week,opponent + 34 legacy stat cols)
        data/processed/dvp_season_{s}.csv (per-defense averages + ranks + composites)
        data/processed/dvp_season.csv     (= most recent completed season's table)
        data/processed/dvp_combined.csv   (multi-season blend; current season weighted 2x
                                           once >=4 weeks of current-season data exist)
Rank convention: descending -- rank 1 = MOST allowed = best fantasy matchup (RANK.AVG ties).
Slot folding (legacy): QB=all QBs, RB2 bucket = RB2+RB3+, WR4+ bucket, TE2 bucket = TE2+TE3+.
"""
import csv, glob, os
from collections import defaultdict
import pandas as pd

STAT_COLS = ['QB PY','P TD','QB RY','RB1 RY','RB2+ RY','WR RY','RB1 Recep','RB1 RecY',
 'RB2 Recep','RB2 RecY','WR1 Recep','WR1 RecY','WR2 Recep','WR2 RecY','WR3 Recep','WR3 RecY',
 'WR4+ Recep','WR4+ RecY','TE1 Recep','TE1 RecY','TE2 Recep','TE2 RecY','QB TD','RB1 TD',
 'RB2 TD','WR1 TD','WR2 TD','WR3 TD','WR4+ TD','TE1 TD','TE2 TD','D/ST TD','QB P+R','RB R+R']

COMPOSITES = {  # slot -> stat columns whose ranks are averaged into the * score
 'QB':   ['QB PY','QB RY','QB P+R','P TD','QB TD'],
 'RB1':  ['RB1 RY','RB1 Recep','RB1 RecY','RB R+R','RB1 TD'],
 'RB2':  ['RB2+ RY','RB2 Recep','RB2 RecY','RB R+R','RB2 TD'],
 'WR1':  ['WR1 Recep','WR1 RecY','WR1 TD'],
 'WR2':  ['WR2 Recep','WR2 RecY','WR2 TD'],
 'WR3':  ['WR3 Recep','WR3 RecY','WR3 TD'],
 'WR4+': ['WR4+ Recep','WR4+ RecY','WR4+ TD'],
 'TE1':  ['TE1 Recep','TE1 RecY','TE1 TD'],
 'TE2':  ['TE2 Recep','TE2 RecY','TE2 TD'],
 'D/ST': ['D/ST TD'],
}

def fold_slot(slot):
    if slot.startswith('QB'): return 'QB'
    if slot in ('RB2','RB3'): return 'RB2'
    if slot in ('TE2','TE3'): return 'TE2'
    return slot  # RB1, WR1-3, WR4+, TE1

def build_weekly(season, logs, dst):
    rows = {}
    for r in logs:
        d = r['opponent']  # defense faced
        key = (d, r['week'])
        if key not in rows:
            rows[key] = {'defense': d, 'season': season, 'week': r['week'],
                         'opponent': r['team'], **{c: 0 for c in STAT_COLS}}
        w = rows[key]
        s = fold_slot(r['slot']); pos = r['pos']
        td_total = r['pass_td'] + r['rush_td'] + r['rec_td']
        if pos == 'QB':
            w['QB PY'] += r['pass_yds']; w['P TD'] += r['pass_td']; w['QB RY'] += r['rush_yds']
            w['QB TD'] += r['rush_td'] + r['rec_td']  # non-passing TDs scored by QBs
            w['QB P+R'] += r['pass_yds'] + r['rush_yds']
        elif pos == 'RB':
            w['RB R+R'] += r['rush_yds'] + r['rec_yds']
            b = 'RB1' if s == 'RB1' else 'RB2'
            w[f'{b} RY' if b=='RB1' else 'RB2+ RY'] += r['rush_yds']
            w[f'{b} Recep'] += r['rec']; w[f'{b} RecY'] += r['rec_yds']
            w[f'{b} TD'] += r['rush_td'] + r['rec_td']
        elif pos == 'WR':
            w['WR RY'] += r['rush_yds']
            b = s if s in ('WR1','WR2','WR3') else 'WR4+'
            w[f'{b} Recep'] += r['rec']; w[f'{b} RecY'] += r['rec_yds']
            w[f'{b} TD'] += r['rush_td'] + r['rec_td']
        elif pos == 'TE':
            b = 'TE1' if s == 'TE1' else 'TE2'
            w[f'{b} Recep'] += r['rec']; w[f'{b} RecY'] += r['rec_yds']
            w[f'{b} TD'] += r['rush_td'] + r['rec_td']
    for (team, week, opp, tds) in dst:
        key = (opp, week)  # defense that ALLOWED the D/ST TD is the opponent of the scoring team
        if key in rows: rows[key]['D/ST TD'] += tds
    return list(rows.values())

def season_table(weekly_df):
    avg = weekly_df.groupby('defense')[STAT_COLS].mean()
    ranks = avg.rank(ascending=False, method='average')
    out = avg.round(2).add_suffix(' avg').join(ranks.add_suffix(' rank'))
    for slot, cols in COMPOSITES.items():
        out[f'{slot} *'] = ranks[cols].mean(axis=1).round(2)
    return out.reset_index()

def main():
    all_weekly = []
    seasons = []
    for f in sorted(glob.glob('data/game_logs/game_logs_*.csv')):
        season = int(f.split('_')[-1].split('.')[0])
        seasons.append(season)
        logs = []
        for r in csv.DictReader(open(f, encoding='utf-8')):
            for k in ('week','pass_yds','pass_td','rush_yds','rush_td','rec','rec_yds','rec_td'):
                r[k] = int(r[k])
            logs.append(r)
        dst = []
        dp = f'data/processed/dst_tds_{season}.csv'
        if os.path.exists(dp):
            for r in csv.DictReader(open(dp)):
                dst.append((r['team'], int(r['week']), r['opponent'], int(r['dst_tds'])))
        all_weekly += build_weekly(season, logs, dst)

    wdf = pd.DataFrame(all_weekly).sort_values(['season','defense','week'])
    wdf.to_csv('data/processed/dvp_weekly.csv', index=False)

    per_season = {}
    for s in seasons:
        t = season_table(wdf[wdf.season == s])
        t.insert(0, 'season', s)
        t.to_csv(f'data/processed/dvp_season_{s}.csv', index=False)
        per_season[s] = t

    latest = max(seasons)
    per_season[latest].to_csv('data/processed/dvp_season.csv', index=False)

    # combined: average per-season AVG stats, then re-rank. Current (2026) weighted 2x if >=4 wks.
    CURRENT = 2026
    frames = []
    for s, t in per_season.items():
        weight = 2 if (s == CURRENT and (wdf[wdf.season == s].week.nunique() >= 4)) else 1
        if s == CURRENT and weight == 1 and len(per_season) > 1:
            continue  # <4 weeks of current season: prior seasons only
        a = t.set_index('defense')[[c + ' avg' for c in STAT_COLS]]
        for _ in range(weight): frames.append(a)
    comb_avg = sum(frames) / len(frames)
    comb_avg.columns = STAT_COLS
    ranks = comb_avg.rank(ascending=False, method='average')
    comb = comb_avg.round(2).add_suffix(' avg').join(ranks.add_suffix(' rank'))
    for slot, cols in COMPOSITES.items():
        comb[f'{slot} *'] = ranks[cols].mean(axis=1).round(2)
    comb.insert(0, 'seasons_blended', '+'.join(map(str, sorted(per_season))))
    comb.reset_index().to_csv('data/processed/dvp_combined.csv', index=False)

    print('dvp_weekly:', len(wdf), 'rows | seasons:', seasons)
    for s in seasons: print(f'dvp_season_{s}: 32 defenses')
    print('combined blends:', sorted(per_season))

if __name__ == '__main__':
    main()
