"""QB target preference — where each quarterback throws by POSITION (RB · TE · WR1 · WR2 · WR3+), how deep, and how much he runs,
beyond any one receiver's target share. From every nflverse pass since 2024 (passer_id → receiver_id → roster position; WR tier =
the receiver's rank by targets among his team's wide receivers that season).

Outputs data/processed/qb_targets.json:
  league      the league mix (shares by position, aDOT, deep %, scramble rate) over the same seasons
  qbs         one row per passer per season plus a career ("all") row: dropbacks, games, shares by position, aDOT, short / deep %,
              scramble rate, designed runs / g, rush yds / g, sack rate, INT rate, and his tilt vs the league (shrunk toward the league
              with 300 dropbacks of prior so 40 throws do not make a profile)
  study       first start with a NEW team: for every passer-team pair whose first game (≥ 15 dropbacks) in the window had no earlier
              game for that team, how his first start and his first three starts differed from the rest of his own games —
              TE / RB / WR1 share, aDOT, scramble rate, sack rate — pooled (mean shift, n, how many moved the same way) and case by case
  starters    this week: each team's QB1 from the depth chart (the games.csv named starter when it has one), his profile, whether this is
              his first game with the team, and the implied shift for the team's targets by position — the QB's own tilt (shrunk by his
              sample) laid over the team's season mix, plus the new-team pattern when it applies
"""
import os, json, glob, re
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
NV = 'data/raw/nflverse'; SEASONS = [2024, 2025, 2026]
PRIOR = 300; MIN_DB = 15

def load():
    P = pd.concat([pd.read_parquet(f'{NV}/pbp_slim_{s}.parquet') for s in SEASONS if os.path.exists(f'{NV}/pbp_slim_{s}.parquet')], ignore_index=True)
    P = P[P.posteam.notna() & (P.two_point_attempt != 1)].copy(); P['posteam'] = P.posteam.replace({'LA': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX'})
    R = pd.concat([pd.read_parquet(f'{NV}/roster_{s}.parquet', columns=['season', 'gsis_id', 'full_name', 'position', 'team']).assign(season=s) for s in SEASONS if os.path.exists(f'{NV}/roster_{s}.parquet')], ignore_index=True)
    R = R.dropna(subset=['gsis_id']).drop_duplicates(['season', 'gsis_id'])
    pos = {(r.season, r.gsis_id): r.position for r in R.itertuples()}; name = {}
    for r in R.itertuples(): name[r.gsis_id] = r.full_name
    return P, pos, name

def enrich(P, pos):
    """pass plays with the receiver's position group and WR tier; dropbacks with scramble / sack flags; designed QB runs"""
    T = P[(P.pass_attempt == 1) & P.receiver_id.notna() & P.passer_id.notna()].copy()
    T['rpos'] = [pos.get((s, r), None) for s, r in zip(T.season, T.receiver_id)]
    T['grp'] = T.rpos.map(lambda x: 'RB' if x in ('RB', 'FB', 'HB') else 'TE' if x == 'TE' else 'WR' if x == 'WR' else 'OTH')
    # WR tier by season target volume within the team
    wr = T[T.grp == 'WR'].groupby(['season', 'posteam', 'receiver_id']).size().rename('n').reset_index()
    wr['tier'] = wr.sort_values('n', ascending=False).groupby(['season', 'posteam']).cumcount() + 1
    tier = {(r.season, r.posteam, r.receiver_id): ('WR1' if r.tier == 1 else 'WR2' if r.tier == 2 else 'WR3+') for r in wr.itertuples()}
    T['slot'] = [tier.get((s, t, r), 'WR3+') if g == 'WR' else g for s, t, r, g in zip(T.season, T.posteam, T.receiver_id, T.grp)]
    T = T[T.slot != 'OTH']
    D = P[(P.qb_dropback == 1) & P.passer_id.notna()].copy()
    # designed QB runs: rush attempts by the passer that are not scrambles (rusher_id == a QB's id)
    QB_IDS = set(T.passer_id.unique()) | set(D.passer_id.unique())
    RU = P[(P.rush_attempt == 1) & P.rusher_id.isin(QB_IDS) & (P.qb_scramble != 1)].copy()
    SC = P[(P.qb_scramble == 1) & P.rusher_id.notna()].copy()
    return T, D, RU, SC

SLOTS = ['RB', 'TE', 'WR1', 'WR2', 'WR3+']
def profile(T, D, RU, SC, key_cols):
    """per key: dropbacks, games, shares by slot, aDOT, short/deep, scramble rate, sack rate, INT rate, designed runs / g, rush yds / g"""
    out = []
    g_db = D.groupby(key_cols); g_t = T.groupby(key_cols)
    for k, d in g_db:
        k = k if isinstance(k, tuple) else (k,)
        t = None
        for kk in (k, k[0] if len(k) == 1 else k):
            try: t = g_t.get_group(kk); break
            except (KeyError, ValueError): continue
        if t is None: t = T.iloc[0:0]
        n = len(d); games = d.game_id.nunique()
        if n < MIN_DB: continue
        sh = {s: round(float((t.slot == s).mean()), 4) if len(t) else None for s in SLOTS}
        air = t.air_yards.dropna()
        pid = d.passer_id.iloc[0]
        ru = RU[(RU.rusher_id == pid) & RU.game_id.isin(d.game_id.unique())]; sc = SC[(SC.rusher_id == pid) & SC.game_id.isin(d.game_id.unique())]
        out.append(dict(zip(key_cols, k)) | dict(dropbacks=int(n), games=int(games), att=int(len(t)), **{f'sh_{s.replace("+", "p")}': sh[s] for s in SLOTS},
                        adot=round(float(air.mean()), 2) if len(air) else None, short=round(float((air < 5).mean()), 3) if len(air) else None, deep=round(float((air >= 20).mean()), 3) if len(air) else None,
                        scr=round(float(d.qb_scramble.fillna(0).mean()), 4), sack=round(float(d.sack.fillna(0).mean()), 4), int_rate=round(float(d.interception.fillna(0).mean()), 4),
                        drun_g=round(len(ru) / max(games, 1), 2), rush_yds_g=round(float(ru.yards_gained.fillna(0).sum() + sc.yards_gained.fillna(0).sum()) / max(games, 1), 1),
                        epa_db=round(float(d.epa.mean()), 3) if 'epa' in d else None))
    return out

def main():
    P, pos, name = load(); T, D, RU, SC = enrich(P, pos)
    lg = profile(T.assign(k=1), D.assign(k=1), RU, SC, ['k'])[0]; del lg['k']
    by_season = profile(T, D, RU, SC, ['passer_id', 'season'])
    career = profile(T, D, RU, SC, ['passer_id'])
    rows = []
    for r in by_season + [dict(c, season='all') for c in career]:
        r['name'] = name.get(r['passer_id'], r['passer_id'])
        teams = D[(D.passer_id == r['passer_id']) & ((D.season == r['season']) if r['season'] != 'all' else True)].posteam.value_counts()
        r['teams'] = list(teams.index[:3]); r['team'] = teams.index[0] if len(teams) else None
        w = r['dropbacks'] / (r['dropbacks'] + PRIOR)   # shrink toward the league
        for s in SLOTS:
            k = f'sh_{s.replace("+", "p")}'
            r[f'tilt_{s.replace("+", "p")}'] = None if r[k] is None else round(w * (r[k] - lg[k]), 4)
        r['tilt_scr'] = round(w * (r['scr'] - lg['scr']), 4); r['tilt_adot'] = None if r['adot'] is None else round(w * (r['adot'] - lg['adot']), 2); r['w'] = round(w, 3)
        rows.append(r)
    # ---- first start with a new team
    firsts = []
    G = D.groupby(['passer_id', 'posteam', 'game_id']).size().rename('n').reset_index()
    gdate = P.groupby('game_id').agg(season=('season', 'first'), week=('week', 'first')).reset_index()
    G = G.merge(gdate, on='game_id').sort_values(['passer_id', 'season', 'week'])
    for pid, gp in G.groupby('passer_id'):
        seen = set(); order = list(gp.itertuples())
        for i, g in enumerate(order):
            if g.posteam in seen: continue
            seen.add(g.posteam)
            if g.n < MIN_DB: continue
            prior_games = {x.game_id for x in order[:i]}
            if i == 0 and g.season == SEASONS[0]: continue   # the window starts here: not a known first start
            first3 = [x.game_id for x in order[i:] if x.posteam == g.posteam][:3]
            rest = [x.game_id for x in order if x.game_id not in first3 and x.n >= MIN_DB]
            if len(rest) < 3: continue
            def mix(gids):
                t = T[(T.passer_id == pid) & T.game_id.isin(gids)]; d = D[(D.passer_id == pid) & D.game_id.isin(gids)]
                if len(d) < MIN_DB: return None
                air = t.air_yards.dropna()
                return dict(te=float((t.slot == 'TE').mean()), rb=float((t.slot == 'RB').mean()), wr1=float((t.slot == 'WR1').mean()), adot=float(air.mean()) if len(air) else None, scr=float(d.qb_scramble.fillna(0).mean()), sack=float(d.sack.fillna(0).mean()), n=int(len(d)))
            m1, m3, mr = mix([g.game_id]), mix(first3), mix(rest)
            if not m1 or not mr: continue
            firsts.append(dict(passer_id=pid, name=name.get(pid, pid), team=g.posteam, season=int(g.season), week=int(g.week), game_id=g.game_id, first=m1, first3=m3, rest=mr,
                               d1={k: (None if m1[k] is None or mr[k] is None else round(m1[k] - mr[k], 4)) for k in ('te', 'rb', 'wr1', 'adot', 'scr', 'sack')},
                               d3={k: (None if not m3 or m3[k] is None or mr[k] is None else round(m3[k] - mr[k], 4)) for k in ('te', 'rb', 'wr1', 'adot', 'scr', 'sack')}))
    pooled = {}
    for k in ('te', 'rb', 'wr1', 'adot', 'scr', 'sack'):
        v1 = [f['d1'][k] for f in firsts if f['d1'][k] is not None]; v3 = [f['d3'][k] for f in firsts if f['d3'][k] is not None]
        pooled[k] = dict(n=len(v1), first=round(float(np.mean(v1)), 4) if v1 else None, first_up=int(sum(1 for v in v1 if v > 0)), first3=round(float(np.mean(v3)), 4) if v3 else None, first3_up=int(sum(1 for v in v3 if v > 0)),
                         median_first=round(float(np.median(v1)), 4) if v1 else None)
    # ---- this week's starters
    games = pd.read_csv(f'{NV}/games.csv'); cur = games[(games.season == 2026) & (games.game_type == 'REG')].copy()
    for _c in ('home_team', 'away_team'): cur[_c] = cur[_c].replace({'LA': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX'})
    today = pd.Timestamp.today().normalize(); last = pd.to_datetime(cur.groupby('week').gameday.max())
    wk = int(last[last >= today].index.min()) if (last >= today).any() else int(cur.week.max()) + 1
    dcs = sorted(glob.glob('data/processed/depth_charts_*.csv')); dc = pd.read_csv(dcs[-1]) if dcs else pd.DataFrame()
    norm = lambda s: re.sub(r'[^a-z]', '', str(s).lower().replace(' jr', '').replace(' sr', '').replace(' iii', '').replace(' ii', ''))
    byname = {}
    for pid, nm in name.items(): byname.setdefault(norm(nm), pid)
    car = {r['passer_id']: r for r in rows if r['season'] == 'all'}
    Tm = T[T.season == 2026].groupby('posteam').slot.value_counts(normalize=True).unstack().fillna(0)   # team season mix, all passers
    teams = sorted(set(cur.home_team) | set(cur.away_team))
    def starters_for(w):
        named = {}; opp = {}
        for r in cur[cur.week == w].itertuples():
            if isinstance(r.away_qb_name, str): named[r.away_team] = r.away_qb_name
            if isinstance(r.home_qb_name, str): named[r.home_team] = r.home_qb_name
            opp[r.away_team] = '@' + r.home_team; opp[r.home_team] = r.away_team
        out = []
        for t in teams:
            if t not in opp: continue
            # the depth chart is the authority (its QB1 is the man listed, with injuries applied); the schedule's named starter is the fallback
            d1 = dc[(dc.team == t) & (dc.slot == 'QB1')] if len(dc) else dc
            qb = None; src = 'depth chart'
            if len(d1) and int(d1.injury.iloc[0]) != -1: qb = d1.player.iloc[0]
            if not qb and named.get(t): qb = named[t]; src = 'schedule'
            if not qb: continue
            pid = byname.get(norm(qb)); pr = car.get(pid)
            with_team = int(len(D[(D.passer_id == pid) & (D.posteam == t)])) if pid else 0
            new_team = with_team == 0
            tm = {s_: round(float(Tm.loc[t, s_]), 4) if t in Tm.index and s_ in Tm.columns else None for s_ in SLOTS}
            implied = {}
            for s_ in SLOTS:
                k = f'tilt_{s_.replace("+", "p")}'; tilt = pr[k] if pr and pr.get(k) is not None else 0.0
                newfx = (pooled['te']['first3'] if s_ == 'TE' else pooled['rb']['first3'] if s_ == 'RB' else pooled['wr1']['first3'] if s_ == 'WR1' else 0.0) if new_team else 0.0
                implied[s_] = None if tm[s_] is None else round(tm[s_] + tilt + (newfx or 0.0), 4)
            out.append(dict(week=w, team=t, opp=opp[t], qb=qb, src=src, passer_id=pid, dropbacks=pr['dropbacks'] if pr else 0, games=pr['games'] if pr else 0, new_team=new_team, with_team=with_team,
                            profile={k: pr.get(k) for k in ('sh_RB', 'sh_TE', 'sh_WR1', 'sh_WR2', 'sh_WR3p', 'adot', 'short', 'deep', 'scr', 'sack', 'int_rate', 'drun_g', 'rush_yds_g', 'w')} if pr else None,
                            tilt={k: pr.get(k) for k in ('tilt_RB', 'tilt_TE', 'tilt_WR1', 'tilt_WR2', 'tilt_WR3p', 'tilt_scr', 'tilt_adot')} if pr else None,
                            team_mix=tm, implied=implied, teams=pr['teams'] if pr else []))
        return out
    starters = starters_for(wk); starters_next = starters_for(wk + 1)
    out = dict(built=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), seasons=SEASONS, week=wk, prior=PRIOR, league=lg, qbs=rows, study=dict(cases=firsts, pooled=pooled), starters=starters, starters_next=starters_next,
               notes=['WR1 / WR2 / WR3+ = the receiver\'s rank by targets among his team\'s wide receivers that season', f'tilt = (his share − league share) × dropbacks / (dropbacks + {PRIOR}); a 40-throw sample barely moves the needle', 'first-start study: a passer\'s first game (15+ dropbacks) for a team he had no earlier game with in 2024–26, against the rest of his own games'])
    def clean(o):
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list): return [clean(v) for v in o]
        if isinstance(o, float) and (np.isnan(o) or np.isinf(o)): return None
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
        return o
    json.dump(clean(out), open('data/processed/qb_targets.json', 'w'), separators=(',', ':'))
    print(f"qb_targets.json: {len(rows)} passer-season rows · {len(firsts)} first starts with a new team · week {wk}: {len(starters)} starters, new to team: {[s['qb'] for s in starters if s['new_team']]}")
    print('  league mix', {k: lg[k] for k in ('sh_RB', 'sh_TE', 'sh_WR1', 'sh_WR2', 'sh_WR3p', 'adot', 'scr')})
    print('  new-team pooled (first start vs his norm):', {k: (v['first'], f"{v['first_up']}/{v['n']} up") for k, v in pooled.items()})

if __name__ == '__main__':
    main()
