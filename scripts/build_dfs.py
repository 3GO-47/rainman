"""DFS mock entries — one DraftKings Classic lineup per slate, built from RAINMAN's stat projections, frozen, then graded
against the real box scores. -> data/processed/dfs_entries.csv (players) + dfs_summary.csv (one row per week x slate)

Usage: python3 scripts/build_dfs.py [--week N]
Inputs : prop_projections.csv (per-market projections + q10/q90), bet_td.csv (expected TDs, lam), bet_lines.csv (team implied),
         kickoffs_2026.csv (slates), data/raw/dk_salaries_wk{N}.csv  — DraftKings salaries, see below.
DK Classic scoring: pass yds .04 (+3 at 300), pass TD 4, INT -1, rush/rec yds .1 (+3 at 100), rush/rec TD 6, reception 1, fumble lost -1.
Projected points = expected value under the model's distribution (bonus probabilities from the q10-q90 band).

Roster: QB · RB RB · WR WR WR · TE · FLEX (RB/WR/TE) · DST, $50,000 cap.
Lineup rules ENFORCED whenever a salary file is present: exactly those nine spots, FLEX from RB/WR/TE, no player twice,
total salary <= $50,000, and players from at least two different games. The lineup is the EXACT optimum under those rules
(per-position "pick exactly n, spend at most s" knapsack over $100 salary buckets, one pass per FLEX type, folded
together), not a greedy approximation — and it is re-checked against every rule before it is allowed to freeze.

Salaries: DraftKings' own DFS endpoints are blocked for the sandbox, the device VM and the Chrome bridge alike, so the
salary file is produced by the Chrome route in scripts/local/pull_dk_salaries.md (FullTime Fantasy publishes DK's posted
salary for every player on every DK slate) and lands at data/raw/dk_salaries_wk{N}.csv in DraftKings' own export schema —
so a real "Export to CSV" from the DK lobby drops in at the same path and takes precedence with no code change. Names are
joined on a normalised key (accents, punctuation and generational suffixes stripped), preferring an exact (name, team)
hit and falling back to an unambiguous name when DK and RAINMAN disagree on a player's team. Without the file the entry
is built UNCAPPED (best projection at every roster spot, no DST) and labeled as such — still graded, so the projections
themselves are on the record either way.

Slates: main (Sun 1 PM + 4 PM), early (Sun 1 PM), afternoon (Sun 4 PM), primetime (SNF + MNF), full (every game of the week).
Entries are frozen the first time a week x slate is built; later runs only grade them. Reproducible from processed data.
"""
import os, sys, csv, glob, math, re, unicodedata
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
P = 'data/processed/'
CAP = 50000
STEP = 100
CAPB = CAP // STEP
SLATES = {'main': ['EARLY', 'LATE'], 'early': ['EARLY'], 'afternoon': ['LATE'], 'primetime': ['SNF', 'MNF'], 'full': None}
POS_OF = lambda slot: 'QB' if slot.startswith('QB') else 'RB' if slot.startswith('RB') else 'WR' if slot.startswith('WR') else 'TE' if slot.startswith('TE') else 'DST'
TEAMFIX = {'JAC': 'JAX', 'WSH': 'WAS', 'LVR': 'LV', 'OAK': 'LV', 'SD': 'LAC', 'SL': 'LAR', 'ARZ': 'ARI', 'BLT': 'BAL', 'CLV': 'CLE', 'HST': 'HOU'}
_SUFFIX = re.compile(r'\s+(?:jr|sr|ii|iii|iv|v)$')

def nkey(name):
    """DK's spelling -> RAINMAN's: strip accents, punctuation and generational suffixes."""
    s = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r"[.'`’\-]", '', s)
    return _SUFFIX.sub('', re.sub(r'\s+', ' ', s).strip())

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
    slate_of, kick_at = {}, {}
    for r in kick.itertuples():
        slate_of[r.vis] = slate_of[r.home] = r.slate
        try: t = pd.Timestamp(f'{r.date} {r.time_et}', tz='America/New_York')
        except Exception: t = pd.NaT
        if pd.notna(t): kick_at[r.slate] = min(kick_at.get(r.slate, t), t)
    NOW = pd.Timestamp.now(tz='America/New_York')
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

    # ---- salaries -----------------------------------------------------------------------------
    sal_file = f'data/raw/dk_salaries_wk{week}.csv'
    by_nt, by_n, dup_n = {}, {}, set()
    if os.path.exists(sal_file):
        for r in csv.DictReader(open(sal_file, encoding='utf-8')):
            nm = (r.get('Name') or '').strip()
            tm = (r.get('TeamAbbrev') or '').strip()
            tm = TEAMFIX.get(tm, tm)
            if (r.get('Position') or '').upper() in ('DST', 'DEF', 'D/ST'): nm = f'{tm} D/ST'
            try: sal = int(str(r['Salary']).replace('$', '').replace(',', ''))
            except (KeyError, ValueError, TypeError): continue
            k = nkey(nm)
            by_nt[(k, tm)] = sal
            if k in by_n and by_n[k] != sal: dup_n.add(k)
            by_n[k] = sal
    def lookup(player, team):
        k = nkey(player)
        if (k, team) in by_nt: return by_nt[(k, team)]
        if k in by_n and k not in dup_n: return by_n[k]   # DK and RAINMAN disagree on his team; the name is unambiguous
        return None
    df['salary'] = [lookup(r.player, r.team) for r in df.itertuples()]
    capped = bool(by_nt)
    if capped:
        print(f'  salaries: {len(by_nt)} priced in {sal_file} -> {int(df.salary.notna().sum())} of {len(df)} projected players matched')
    ROSTER = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX'] + (['DST'] if capped else [])

    # ---- exact DK Classic optimiser -----------------------------------------------------------
    def pos_table(rws, need):
        """best[n][s] = (points, (index,...)) for exactly n of one position, total salary <= s * $100."""
        NEG = (-1.0, None)
        dp = [[NEG] * (CAPB + 1) for _ in range(need + 1)]
        dp[0] = [(0.0, ())] * (CAPB + 1)
        for idx, pts, cost in rws:
            for n in range(need, 0, -1):
                prev, cur = dp[n - 1], dp[n]
                for b in range(CAPB, cost - 1, -1):
                    pp, pk = prev[b - cost]
                    if pk is None: continue
                    if pp + pts > cur[b][0]: cur[b] = (pp + pts, pk + (idx,))
        for n in range(need + 1):                      # prefix-max: the table now reads "salary <= s"
            best = NEG
            for b in range(CAPB + 1):
                if dp[n][b][0] > best[0]: best = dp[n][b]
                dp[n][b] = best
        return dp

    def optimal(pool):
        pool = pool.reset_index(drop=True)
        rows_by_pos = {}
        for pos in ('QB', 'RB', 'WR', 'TE', 'DST'):
            sub = pool[pool.pos == pos]
            rows_by_pos[pos] = [(int(i), float(r.proj_pts), int(round(r.salary / STEP))) for i, r in zip(sub.index, sub.itertuples())]
        best_overall = None
        for flex in ('RB', 'WR', 'TE'):
            need = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'DST': 1}
            need[flex] += 1
            if any(len(rows_by_pos[p]) < n for p, n in need.items()): continue
            tabs = [pos_table(rows_by_pos[p], n)[n] for p, n in need.items()]
            acc = tabs[0]
            for t in tabs[1:]:
                nxt = [(-1.0, None)] * (CAPB + 1)
                for b in range(CAPB + 1):
                    bp, bk = -1.0, None
                    for b1 in range(b + 1):
                        ap, ak = acc[b1]
                        if ak is None: continue
                        tp, tk = t[b - b1]
                        if tk is None: continue
                        if ap + tp > bp: bp, bk = ap + tp, ak + tk
                    nxt[b] = (bp, bk)
                acc = nxt
            pts, keys = acc[CAPB]
            if keys is None: continue
            if best_overall is None or pts > best_overall[0]: best_overall = (pts, keys)
        if best_overall is None: return None
        chosen = [pool.loc[k].to_dict() for k in best_overall[1]]
        by_pos = {}
        for c in chosen: by_pos.setdefault(c['pos'], []).append(c)
        for v in by_pos.values(): v.sort(key=lambda x: -x['proj_pts'])
        out = []
        for slot in ROSTER:
            if slot == 'FLEX':
                out.append(None)                             # placeholder, filled below, so the CSV reads in DK's order
                continue
            out.append({**by_pos[slot].pop(0), 'roster': slot})
        left = [c for v in by_pos.values() for c in v]       # whatever the doubled position left over
        out[out.index(None)] = {**left[0], 'roster': 'FLEX'}
        return out

    def build(pool):
        pool = pool[pool.proj_pts > 0].copy()
        if capped: pool = pool[pool.salary.notna()]
        if pool.empty: return None
        if capped: return optimal(pool)
        pick = []
        for slot in ROSTER:
            ok = pool[~pool.player.isin([x['player'] for x in pick])]
            ok = ok[ok.pos.isin(['RB', 'WR', 'TE'])] if slot == 'FLEX' else ok[ok.pos == slot]
            if ok.empty: return None
            b = ok.sort_values('proj_pts', ascending=False).iloc[0]; pick.append({**b.to_dict(), 'roster': slot})
        return pick

    def dk_illegal(lineup):
        """Every DraftKings Classic rule, re-checked on the built lineup rather than assumed."""
        why = []
        if sorted(x['roster'] for x in lineup) != sorted(ROSTER): why.append('roster spots wrong')
        if len({x['player'] for x in lineup}) != len(lineup): why.append('duplicate player')
        spend = sum(int(x['salary']) for x in lineup)
        if spend > CAP: why.append(f'over cap (${spend:,})')
        flex = [x for x in lineup if x['roster'] == 'FLEX']
        if flex and flex[0]['pos'] not in ('RB', 'WR', 'TE'): why.append('FLEX not RB/WR/TE')
        if len({tuple(sorted((x['team'], str(x['opp']).replace('@', '')))) for x in lineup}) < 2: why.append('one game only')
        return why

    # ---- freeze / grade -----------------------------------------------------------------------
    ent_path, sum_path = P + 'dfs_entries.csv', P + 'dfs_summary.csv'
    ent = pd.read_csv(ent_path) if os.path.exists(ent_path) else pd.DataFrame()
    smm = pd.read_csv(sum_path) if os.path.exists(sum_path) else pd.DataFrame()
    new_e, new_s = [], []
    for name, slates in SLATES.items():
        if len(ent) and ((ent.week == week) & (ent.slate == name)).any(): continue
        pool = df if slates is None else df[df.slate.isin(slates)]
        if pool.empty: continue
        # a DK slate locks at its first kickoff; freezing one afterwards would be hindsight, not a submission
        windows = slates if slates is not None else [w for w in kick_at]
        first = min([kick_at[w] for w in windows if w in kick_at], default=None)
        if first is not None and first <= NOW:
            print(f'  -- {name}: already locked (first kickoff {first:%a %-d %b %-I:%M %p} ET) — not frozen'); continue
        lineup = build(pool)
        if not lineup: continue
        if capped:
            why = dk_illegal(lineup)
            if why:
                print(f'  !! {name}: lineup rejected ({"; ".join(why)}) — not frozen'); continue
        for x in lineup:
            new_e.append({'week': week, 'slate': name, 'roster': x['roster'], 'player': x['player'], 'team': x['team'], 'opp': x['opp'], 'slot': x['slot'],
                          'salary': x['salary'] if x['salary'] == x['salary'] else '', 'proj_pts': x['proj_pts'], 'actual_pts': '', 'frozen_on': str(pd.Timestamp.today().date())})
        new_s.append({'week': week, 'slate': name, 'games': int(len({tuple(sorted((x['team'], str(x['opp']).replace('@', '')))) for x in lineup})),
                      'capped': capped, 'salary': sum(int(x['salary']) for x in lineup) if capped else '',
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
            if POS_OF(str(r.slot)) == 'DST': continue
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
    for s in new_s: print(f"  {s['slate']:10} proj {s['proj_total']:6.1f}  games {s['games']}" + (f"  ${s['salary']:,}" if capped else ''))

if __name__ == '__main__':
    wk = int(sys.argv[sys.argv.index('--week') + 1]) if '--week' in sys.argv else None
    main(wk)
