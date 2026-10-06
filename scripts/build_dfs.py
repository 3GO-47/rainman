"""DFS mock entries — one DraftKings Classic lineup per slate, built from RAINMAN's stat projections, frozen, then graded
against the real box scores. -> data/processed/dfs_entries.csv (players) + dfs_summary.csv (one row per week × slate)

Usage: python3 scripts/build_dfs.py [--week N]
Inputs : prop_projections.csv (per-market projections + q10/q90), bet_td.csv (expected TDs, lam), bet_lines.csv (team implied),
         kickoffs_2026.csv (slates), data/raw/dk_salaries_wk{N}.csv  — DraftKings lobby "Export to CSV" (optional, see below)
DK Classic scoring: pass yds .04 (+3 at 300), pass TD 4, INT −1, rush/rec yds .1 (+3 at 100), rush/rec TD 6, reception 1, fumble lost −1.
Projected points = expected value under the model's distribution (bonus probabilities from the q10–q90 band).
Roster: QB · RB RB · WR WR WR · TE · FLEX (RB/WR/TE) · DST, $50,000 cap.
Salaries: DraftKings' DFS endpoints are blocked for both this sandbox and the Chrome bridge, so salaries come from the CSV
DraftKings itself exports from any contest lobby (drop it at data/raw/dk_salaries_wk{N}.csv). Without that file the entry
is built UNCAPPED (best projection at every roster spot, no DST) and labeled as such — still graded, so the projections
themselves are on the record either way.
Slates: main (Sun 1 PM + 4 PM), early (Sun 1 PM), afternoon (Sun 4 PM), primetime (SNF + MNF), full (every game of the week).
Entries are frozen the first time a week × slate is built; later runs only grade them. Reproducible from processed data.
"""
import os, sys, csv, glob, math
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
P = 'data/processed/'
CAP = 50000
SLATES = {'main': ['EARLY', 'LATE'], 'early': ['EARLY'], 'afternoon': ['LATE'], 'primetime': ['SNF', 'MNF'], 'full': None}
POS_OF = lambda slot: 'QB' if slot.startswith('QB') else 'RB' if slot.startswith('RB') else 'WR' if slot.startswith('WR') else 'TE' if slot.startswith('TE') else 'DST'

def pnorm(x, mu, sd):
    if sd <= 0: return 1.0 if mu >= x else 0.0
    return 0.5 * (1 + math.erf((mu - x) / (sd * math.sqrt(2))))

def main(week=None):
    pj = pd.read_csv(P + 'prop_projections.csv')
    if week is None: week = int(pj.week.max())
    pj = pj[pj.week == week]
    td = pd.read_csv(P + 'bet_td.csv'); td = td[td.week == week]
    lines = pd.read_csv(P + 'bet_lines.csv')
    kick = pd.read_csv(P + 'kickoffs_2026.csv'); kick = kick[kick.week == week]
    slate_of = {}
    for r in kick.itertuples(): slate_of[r.vis] = slate_of[r.home] = r.slate
    # expected DK points per player
    rows = {}
    for (p, t, o, s), g in pj.groupby(['player', 'team', 'opp', 'slot']):
        m = {r.market: r for r in g.itertuples()}
        def ev(mk, mult, bonus_at=None):
            r = m.get(mk)
            if r is None: return 0.0
            pts = r.proj * mult
            if bonus_at: pts += 3 * pnorm(bonus_at, r.proj, max(1e-6, (r.q90 - r.q10) / 2.563))
            return pts
        pts = ev('pass_yds', .04, 300) + ev('pass_td', 4) - ev('interceptions', 1) + ev('rush_yds', .1, 100) + ev('rec_yds', .1, 100) + ev('receptions', 1)
        lam = td[(td.player == p) & (td.team == t)].lam
        pts += 6 * float(lam.iloc[0]) if len(lam) else 0.0
        rows[(p, t)] = {'week': week, 'player': p, 'team': t, 'opp': o, 'slot': s, 'pos': POS_OF(s), 'proj_pts': round(pts, 2), 'slate': slate_of.get(t, '')}
    df = pd.DataFrame(rows.values())
    # DST: points fall with the opponent's implied total (no sack/turnover model yet — this is the honest, simple version)
    imp = lines.groupby('team').team_implied.first() if len(lines) else pd.Series(dtype=float)
    dst = []
    for r in kick.itertuples():
        for t, o in ((r.vis, r.home), (r.home, r.vis)):
            oi = float(imp.get(o, 22.0))
            dst.append({'week': week, 'player': f'{t} D/ST', 'team': t, 'opp': o, 'slot': 'DST', 'pos': 'DST', 'proj_pts': round(max(1.0, min(12.0, 9.0 - 0.4 * (oi - 21))), 2), 'slate': r.slate})
    df = pd.concat([df, pd.DataFrame(dst)], ignore_index=True)
    # salaries (optional)
    sal_file = f'data/raw/dk_salaries_wk{week}.csv'
    salaries = {}
    if os.path.exists(sal_file):
        for r in csv.DictReader(open(sal_file, encoding='utf-8')):
            nm = r.get('Name', '').strip(); tm = r.get('TeamAbbrev', '').strip().replace('JAC', 'JAX').replace('WSH', 'WAS')
            if r.get('Position') == 'DST': nm = f'{tm} D/ST'
            try: salaries[(nm, tm)] = int(r['Salary'])
            except (KeyError, ValueError): pass
    df['salary'] = [salaries.get((r.player, r.team)) for r in df.itertuples()]
    capped = bool(salaries)
    ROSTER = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX'] + (['DST'] if capped else [])
    def build(pool):
        pool = pool[pool.proj_pts > 0].copy()
        if capped: pool = pool[pool.salary.notna()]
        if pool.empty: return None
        if not capped:
            pick = []
            for slot in ROSTER:
                ok = pool[~pool.player.isin([x['player'] for x in pick])]
                ok = ok[ok.pos.isin(['RB', 'WR', 'TE'])] if slot == 'FLEX' else ok[ok.pos == slot]
                if ok.empty: return None
                b = ok.sort_values('proj_pts', ascending=False).iloc[0]; pick.append({**b.to_dict(), 'roster': slot})
            return pick
        # capped: greedy by points-per-dollar with a value floor, then 2-opt swaps that raise projected points under the cap
        pool['val'] = pool.proj_pts / pool.salary * 1000
        def fill(order):
            pick, spend = [], 0
            for slot in ROSTER:
                ok = order[~order.player.isin([x['player'] for x in pick])]
                ok = ok[ok.pos.isin(['RB', 'WR', 'TE'])] if slot == 'FLEX' else ok[ok.pos == slot]
                remaining = len(ROSTER) - len(pick) - 1
                ok = ok[ok.salary <= CAP - spend - remaining * 3000]
                if ok.empty: return None
                b = ok.iloc[0]; pick.append({**b.to_dict(), 'roster': slot}); spend += int(b.salary)
            return pick
        best = None
        for key in ('val', 'proj_pts'):
            cand = fill(pool.sort_values(key, ascending=False))
            if cand and (best is None or sum(x['proj_pts'] for x in cand) > sum(x['proj_pts'] for x in best)): best = cand
        if not best: return None
        improved = True
        while improved:
            improved = False
            total = sum(x['proj_pts'] for x in best); spend = sum(x['salary'] for x in best)
            for i, x in enumerate(best):
                elig = pool[(pool.pos == x['pos']) if x['roster'] != 'FLEX' else pool.pos.isin(['RB', 'WR', 'TE'])]
                elig = elig[~elig.player.isin([y['player'] for y in best])]
                elig = elig[(elig.salary <= x['salary'] + (CAP - spend)) & (elig.proj_pts > x['proj_pts'])]
                if elig.empty: continue
                b = elig.sort_values('proj_pts', ascending=False).iloc[0]
                best[i] = {**b.to_dict(), 'roster': x['roster']}; improved = True; break
        return best
    # freeze / grade
    ent_path, sum_path = P + 'dfs_entries.csv', P + 'dfs_summary.csv'
    ent = pd.read_csv(ent_path) if os.path.exists(ent_path) else pd.DataFrame()
    smm = pd.read_csv(sum_path) if os.path.exists(sum_path) else pd.DataFrame()
    new_e, new_s = [], []
    for name, slates in SLATES.items():
        if len(ent) and ((ent.week == week) & (ent.slate == name)).any(): continue
        pool = df if slates is None else df[df.slate.isin(slates)]
        if pool.empty: continue
        lineup = build(pool)
        if not lineup: continue
        for x in lineup:
            new_e.append({'week': week, 'slate': name, 'roster': x['roster'], 'player': x['player'], 'team': x['team'], 'opp': x['opp'], 'slot': x['slot'],
                          'salary': x['salary'] if x['salary'] == x['salary'] else '', 'proj_pts': x['proj_pts'], 'actual_pts': '', 'frozen_on': str(pd.Timestamp.today().date())})
        new_s.append({'week': week, 'slate': name, 'games': int(len({x['team'] for x in lineup})), 'capped': capped, 'salary': sum(int(x['salary']) for x in lineup) if capped else '',
                      'proj_total': round(sum(x['proj_pts'] for x in lineup), 2), 'actual_total': '', 'frozen_on': str(pd.Timestamp.today().date())})
    ent = pd.concat([ent, pd.DataFrame(new_e)], ignore_index=True) if new_e else ent
    smm = pd.concat([smm, pd.DataFrame(new_s)], ignore_index=True) if new_s else smm
    # grade with real box scores (DK scoring) for every frozen entry whose games have logs
    logs = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_2026.csv'))], ignore_index=True)
    def dk(r):
        return (r.pass_yds * .04 + (3 if r.pass_yds >= 300 else 0) + r.pass_td * 4 - r['int'] + r.rush_yds * .1 + (3 if r.rush_yds >= 100 else 0) + r.rush_td * 6
                + r.rec + r.rec_yds * .1 + (3 if r.rec_yds >= 100 else 0) + r.rec_td * 6 - r.fumbles_lost)
    dcs = sorted(glob.glob(P + 'depth_charts_*.csv'))
    log_name = {}
    if dcs:
        for r in csv.DictReader(open(dcs[-1], encoding='utf-8')): log_name[(r['player'], r['team'])] = r.get('log_name') or r['player']
    if len(ent):
        for i, r in ent.iterrows():
            if r.actual_pts == r.actual_pts and str(r.actual_pts) != '': continue
            if r.pos if 'pos' in ent.columns else POS_OF(str(r.slot)) == 'DST': continue
            ln = log_name.get((r.player, r.team), r.player)
            g = logs[(logs.week == r.week) & (logs.team == r.team) & (logs.player == ln)]
            played = ((logs.week == r.week) & (logs.team == r.team)).any()
            if len(g): ent.at[i, 'actual_pts'] = round(float(dk(g.iloc[0])), 2)
            elif played: ent.at[i, 'actual_pts'] = 0.0
        for i, s in smm.iterrows():
            e = ent[(ent.week == s.week) & (ent.slate == s.slate)]
            if len(e) and e.actual_pts.astype(str).ne('').all() and e.actual_pts.notna().all():
                smm.at[i, 'actual_total'] = round(float(pd.to_numeric(e.actual_pts).sum()), 2)
    ent.to_csv(ent_path, index=False); smm.to_csv(sum_path, index=False)
    print(f"dfs: wk {week} · {len(new_s)} new entries ({'capped — DK salaries found' if capped else 'UNCAPPED — no data/raw/dk_salaries_wk%d.csv' % week}) · {len(smm)} entries on record")
    for s in new_s: print(f"  {s['slate']:10} proj {s['proj_total']:6.1f}" + (f"  ${s['salary']}" if capped else ''))

if __name__ == '__main__':
    wk = int(sys.argv[sys.argv.index('--week') + 1]) if '--week' in sys.argv else None
    main(wk)
