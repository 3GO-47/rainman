"""Live Categories — every way of grouping this week's players that has a track record, ranked by how often its members OUTPERFORM.

A category is a rule applied before kickoff (position, usage tier, opponent, game environment, form, head-to-head, a few combinations).
A member HITS when his PPR points beat his own baseline (the mean of his previous six games) by 15% or 3 points, whichever is more;
he SCORES when he has a rushing or receiving touchdown. Every category is graded week by week against the FIELD that week (every player
with a baseline), so a category's lift is its hit rate over the field's. The current week is graded live: members whose games are in the
logs count, the rest wait — so the order on the page rearranges as the week plays out.

Inputs: data/game_logs/*.csv · player_usage.csv · dvp_weekly.csv · game_lines.csv · team_def_tendencies.csv · nflverse pbp (red-zone shares) · rosters
Output: data/processed/categories.json
"""
import os, json, glob, re
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
NV = 'data/raw/nflverse'; SEASONS = [2025, 2026]; CUR = 2026
TEAMFIX = {'LA': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX'}
norm = lambda s: re.sub(r'[^a-z]', '', str(s).lower().replace(' jr', '').replace(' sr', '').replace(' iii', '').replace(' ii', ''))
SLOTSTAT = {'QB': ['QB PY', 'QB RY', 'P TD', 'QB TD'], 'RB1': ['RB1 RY', 'RB1 Recep', 'RB1 RecY', 'RB1 TD'], 'RB2': ['RB2+ RY', 'RB2 Recep', 'RB2 RecY', 'RB2 TD'], 'WR1': ['WR1 Recep', 'WR1 RecY', 'WR1 TD'], 'WR2': ['WR2 Recep', 'WR2 RecY', 'WR2 TD'], 'WR3': ['WR3 Recep', 'WR3 RecY', 'WR3 TD'], 'WR4+': ['WR4+ Recep', 'WR4+ RecY', 'WR4+ TD'], 'TE1': ['TE1 Recep', 'TE1 RecY', 'TE1 TD'], 'TE2': ['TE2 Recep', 'TE2 RecY', 'TE2 TD']}
TDSTAT = {'QB': 'QB TD', 'RB1': 'RB1 TD', 'RB2': 'RB2 TD', 'WR1': 'WR1 TD', 'WR2': 'WR2 TD', 'WR3': 'WR3 TD', 'WR4+': 'WR4+ TD', 'TE1': 'TE1 TD', 'TE2': 'TE2 TD'}

def load():
    L = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
    L = L[L.season.isin([2024] + SEASONS)].copy(); L['team'] = L.team.replace(TEAMFIX); L['opponent'] = L.opponent.replace(TEAMFIX); L['n'] = L.player.map(norm)
    L['slot'] = L.slot.fillna('').astype(str); L['slotk'] = L.slot.map(lambda s: 'QB' if s.startswith('QB') else s if s in SLOTSTAT else ('WR4+' if s.startswith('WR') else 'RB2' if s.startswith('RB') else 'TE2' if s.startswith('TE') else s))
    L['td'] = L.rush_td.fillna(0) + L.rec_td.fillna(0)
    U = pd.read_csv('data/processed/player_usage.csv'); U['team'] = U.team.replace(TEAMFIX); U['n'] = U.player.map(norm)
    D = pd.read_csv('data/processed/dvp_weekly.csv'); D['defense'] = D.defense.replace(TEAMFIX)
    G = pd.read_csv('data/processed/game_lines.csv')
    for c in ('away_team', 'home_team'): G[c] = G[c].replace(TEAMFIX)
    TD = pd.read_csv('data/processed/team_def_tendencies.csv') if os.path.exists('data/processed/team_def_tendencies.csv') else pd.DataFrame()
    return L, U, D, G, TD

def rz_shares():
    """red-zone touches (targets + carries inside the 20) by player and game, from the play-by-play, keyed by normalized name"""
    out = {}
    for s in SEASONS:
        f = f'{NV}/pbp_slim_{s}.parquet'; rf = f'{NV}/roster_{s}.parquet'
        if not (os.path.exists(f) and os.path.exists(rf)): continue
        P = pd.read_parquet(f, columns=['game_id', 'season', 'week', 'posteam', 'yardline_100', 'receiver_id', 'rusher_id', 'pass_attempt', 'rush_attempt'])
        R = pd.read_parquet(rf, columns=['gsis_id', 'full_name']).dropna().drop_duplicates('gsis_id'); nm = dict(zip(R.gsis_id, R.full_name.map(norm)))
        P = P[(P.yardline_100 <= 20) & P.posteam.notna()]
        P['pid'] = np.where(P.pass_attempt == 1, P.receiver_id, np.where(P.rush_attempt == 1, P.rusher_id, None)); P = P[P.pid.notna()]
        tot = P.groupby(['season', 'week', 'posteam']).size()
        for (se, w, t, pid), k in P.groupby(['season', 'week', 'posteam', 'pid']).size().items():
            out[(se, w, t.replace('LA', 'LAR') if t == 'LA' else t, nm.get(pid))] = k / tot[(se, w, t)]
    return out

def dvp_rank_asof(D):
    """season-to-date composite rank of every defense for every slot AS OF each week (weeks 1..n use games before them; week 1 uses the prior season)"""
    out = {}   # (season, week, defense, slotk) -> (rank 1 = allows the most, n)
    def comp(df, slk):
        cols = [c for c in SLOTSTAT[slk] if c in df.columns]
        if not cols: return None
        x = df[cols].astype(float); return (x.fillna(0) * np.array([6 if c.endswith('TD') else 1 if 'Recep' in c else .1 for c in cols])).sum(axis=1)
    for se in SEASONS:
        prev = D[D.season == se - 1]; cur = D[D.season == se]
        for w in sorted(set(int(x) for x in cur.week.unique()) | ({int(cur.week.max()) + 1} if len(cur) else set())):   # + the week ahead, so the live week has ranks
            sofar = cur[cur.week < w]
            for slk in SLOTSTAT:
                src = sofar if len(sofar) and sofar.groupby('defense').size().min() >= 2 else prev
                if not len(src): continue
                c = comp(src, slk)
                if c is None: continue
                m = pd.Series(c.values, index=src.defense.values).groupby(level=0).mean().sort_values(ascending=False)
                for i, (d, v) in enumerate(m.items()): out[(se, int(w), d, slk)] = (i + 1, len(m))
                # TD-only rank
                tc = TDSTAT[slk]
                if tc in src.columns:
                    mt = src.groupby('defense')[tc].mean().sort_values(ascending=False)
                    for i, (d, v) in enumerate(mt.items()): out[(se, int(w), d, slk, 'td')] = (i + 1, len(mt))
    return out

def main():
    L, U, D, G, TD = load(); RZ = rz_shares(); RK = dvp_rank_asof(D)
    tend = {r.team.replace('LA', 'LAR') if r.team == 'LA' else r.team: r for r in TD.itertuples()} if len(TD) else {}
    blitz = {t: float(getattr(r, 'blitz_rate', np.nan)) for t, r in tend.items()}; man = {t: float(getattr(r, 'man_rate', np.nan)) for t, r in tend.items()}
    # game context per (season, week, team)
    ctx = {}
    for r in G.itertuples():
        if r.season not in SEASONS: continue
        sp = r.spread_line if r.spread_line == r.spread_line else None; tl = r.total_line if r.total_line == r.total_line else None
        late = isinstance(r.gametime, str) and r.gametime >= '20:00'; div = int(r.div_game) if r.div_game == r.div_game else 0
        for team, home in ((r.away_team, False), (r.home_team, True)):
            fav = None if sp is None else (sp if home else -sp)            # positive = this team favoured by that much
            imp = None if (sp is None or tl is None) else tl / 2 + fav / 2
            ctx[(int(r.season), int(r.week), team)] = dict(home=home, fav=fav, imp=imp, tot=tl, late=late, div=bool(div), opp=r.home_team if not home else r.away_team)
    # baselines and outcomes
    L = L.sort_values(['n', 'season', 'week']).reset_index(drop=True)
    L['base'] = L.groupby('n').fantasy_pts_ppr.transform(lambda s: s.shift(1).rolling(6, min_periods=3).mean())
    L['hit'] = (L.fantasy_pts_ppr >= np.maximum(1.15 * L.base, L.base + 3)).where(L.base.notna())
    L['prev_hit'] = L.groupby('n').hit.shift(1); L['prev2_hit'] = L.groupby('n').hit.shift(2)
    # usage season-to-date (before the week) and last two
    U = U.sort_values(['n', 'season', 'week'])
    for c in ('target_share', 'rush_share', 'snap_pct', 'adot', 'wopr'):
        U[c + '_std'] = U.groupby(['n', 'season'])[c].transform(lambda s: s.shift(1).expanding(min_periods=2).mean())
        U[c + '_l2'] = U.groupby(['n', 'season'])[c].transform(lambda s: s.shift(1).rolling(2, min_periods=2).mean())
    U['g_prior'] = U.groupby(['n', 'season']).cumcount()
    uk = {(r.season, r.week, r.n): r for r in U.itertuples()}
    # team TD share season-to-date (before the week)
    L['team_td'] = L.groupby(['season', 'week', 'team']).td.transform('sum')
    L['ptd_cum'] = L.groupby(['n', 'season']).td.cumsum() - L.td; L['ttd_cum'] = L.groupby(['n', 'season']).team_td.cumsum() - L.team_td
    L['g_cum'] = L.groupby(['n', 'season']).cumcount()
    # rz share last 4 (before the week)
    L['rz'] = [RZ.get((se, w, t, n), 0.0) for se, w, t, n in zip(L.season, L.week, L.team, L.n)]
    L['rz_l4'] = L.groupby('n').rz.transform(lambda s: s.shift(1).rolling(4, min_periods=2).mean())
    # head to head: last meeting outcome
    L['h2h_prev_td'] = L.groupby(['n', 'opponent']).td.shift(1); L['h2h_prev_hit'] = L.groupby(['n', 'opponent']).hit.shift(1)
    # categories
    def rk(r, td=False):
        k = (r.season, r.week, r.opponent, r.slotk) + (('td',) if td else ()); return RK.get(k)
    def soft(r, k=8, td=False):
        x = rk(r, td); return x is not None and x[0] <= k
    def hard(r, k=8):
        x = rk(r); return x is not None and x[0] > x[1] - k
    def usage(r): return uk.get((r.season, r.week, r.n))
    def ug(r, c, l2=False):
        u = usage(r); v = getattr(u, c + ('_l2' if l2 else '_std'), np.nan) if u is not None else np.nan; return None if v != v else float(v)
    def cx(r): return ctx.get((r.season, r.week, r.team))
    CATS = [
        ('QB1', 'QB1', 'position', 'the starting quarterback', lambda r: r.slot == 'QB1'),
        ('RB1', 'RB1', 'position', 'the lead back', lambda r: r.slot == 'RB1'), ('RB2', 'RB2', 'position', 'the second back', lambda r: r.slot == 'RB2'),
        ('WR1', 'WR1', 'position', 'the top wide receiver on the chart', lambda r: r.slot == 'WR1'), ('WR2', 'WR2', 'position', 'the second receiver', lambda r: r.slot == 'WR2'), ('WR3', 'WR3', 'position', 'the third receiver', lambda r: r.slot == 'WR3'),
        ('TE1', 'TE1', 'position', 'the starting tight end', lambda r: r.slot == 'TE1'),
        ('tgt25', 'target share 25%+', 'usage', 'season-to-date target share of 25% or more (receivers and backs)', lambda r: r.pos != 'QB' and (ug(r, 'target_share') or 0) >= .25),
        ('tgt20', 'target share 20–25%', 'usage', 'season-to-date target share between 20 and 25%', lambda r: r.pos != 'QB' and .20 <= (ug(r, 'target_share') or 0) < .25),
        ('touch60', 'RB with 60%+ of the carries', 'usage', 'a back with 60% or more of his team\'s carries, season to date', lambda r: r.pos == 'RB' and (ug(r, 'rush_share') or 0) >= .60),
        ('snap85', 'snap share 85%+', 'usage', 'on the field for 85% or more of the offensive snaps, season to date', lambda r: r.pos != 'QB' and (ug(r, 'snap_pct') or 0) >= .85),
        ('wopr60', 'WOPR 0.60+', 'usage', 'weighted opportunity (targets + air yards) of 0.60 or more', lambda r: r.pos in ('WR', 'TE') and (ug(r, 'wopr') or 0) >= .60),
        ('rz30', 'red-zone share 30%+ (last 4)', 'usage', '30% or more of his team\'s red-zone targets and carries over the last four games', lambda r: r.pos != 'QB' and (r.rz_l4 or 0) >= .30),
        ('tdsh25', 'TD share 25%+', 'usage', 'has scored 25% or more of his team\'s touchdowns this season (3+ games in)', lambda r: r.pos != 'QB' and r.g_cum >= 3 and r.ttd_cum >= 4 and r.ptd_cum / r.ttd_cum >= .25),
        ('rising', 'target share rising', 'form', 'target share over the last two games at least 25% above his season rate', lambda r: r.pos != 'QB' and (ug(r, 'target_share') or 0) >= .12 and (ug(r, 'target_share', True) or 0) >= 1.25 * (ug(r, 'target_share') or 9)),
        ('adot12', 'deep threat (aDOT 12+)', 'usage', 'average depth of target of 12 yards or more', lambda r: r.pos in ('WR', 'TE') and (ug(r, 'adot') or 0) >= 12),
        ('adot6', 'short game (aDOT ≤ 6)', 'usage', 'average depth of target of 6 yards or less', lambda r: r.pos in ('WR', 'TE', 'RB') and ug(r, 'adot') is not None and ug(r, 'adot') <= 6 and (ug(r, 'target_share') or 0) >= .10),
        ('soft8', 'vs a bottom-8 defense for his slot', 'opponent', 'the opponent ranks in the eight that allow the most to his slot, season to date (prior season in the first weeks)', lambda r: soft(r, 8)),
        ('soft4', 'vs a bottom-4 defense for his slot', 'opponent', 'the opponent ranks in the four softest for his slot', lambda r: soft(r, 4)),
        ('hard8', 'vs a top-8 defense for his slot', 'opponent', 'the opponent ranks in the eight stingiest for his slot', lambda r: hard(r, 8)),
        ('softTD', 'vs a defense allowing the most TDs to his slot', 'opponent', 'the opponent ranks bottom-8 in touchdowns allowed to his slot', lambda r: soft(r, 8, td=True)),
        ('blitz', 'vs a blitz-heavy defense', 'opponent', 'the opponent blitzes on 30% or more of dropbacks (QB, WR, TE)', lambda r: r.pos in ('QB', 'WR', 'TE') and (blitz.get(r.opponent) or 0) >= .30),
        ('man', 'WR vs a man-heavy defense', 'opponent', 'a wide receiver against a defense in man coverage 35% or more of the time', lambda r: r.pos == 'WR' and (man.get(r.opponent) or 0) >= .35),
        ('imp26', 'team implied 26+', 'environment', 'his team\'s implied points from the spread and total are 26 or more', lambda r: cx(r) is not None and cx(r)['imp'] is not None and cx(r)['imp'] >= 26),
        ('imp18', 'team implied 18 or less', 'environment', 'his team is implied for 18 points or fewer', lambda r: cx(r) is not None and cx(r)['imp'] is not None and cx(r)['imp'] <= 18),
        ('fav7', 'favorite by 7+', 'environment', 'his team is favoured by a touchdown or more', lambda r: cx(r) is not None and cx(r)['fav'] is not None and cx(r)['fav'] >= 7),
        ('dog7', 'underdog by 7+', 'environment', 'his team is a touchdown-or-more underdog', lambda r: cx(r) is not None and cx(r)['fav'] is not None and cx(r)['fav'] <= -7),
        ('tot48', 'total 48+', 'environment', 'the game total is 48 or higher', lambda r: cx(r) is not None and cx(r)['tot'] is not None and cx(r)['tot'] >= 48),
        ('home', 'at home', 'environment', 'playing at home', lambda r: cx(r) is not None and cx(r)['home']),
        ('late', 'night game', 'environment', 'a game kicking off at 8 pm ET or later', lambda r: cx(r) is not None and cx(r)['late']),
        ('div', 'division game', 'environment', 'a divisional opponent', lambda r: cx(r) is not None and cx(r)['div']),
        ('h2hTD', 'scored on them last time', 'head to head', 'had a touchdown in his last game against this opponent', lambda r: r.h2h_prev_td == r.h2h_prev_td and r.h2h_prev_td >= 1),
        ('h2hBeat', 'beat his baseline on them last time', 'head to head', 'outperformed his baseline in his last game against this opponent', lambda r: r.h2h_prev_hit == 1),
        ('hot2', 'hot: beat his baseline the last two', 'form', 'outperformed his baseline in each of his last two games', lambda r: r.prev_hit == 1 and r.prev2_hit == 1),
        ('cold2', 'cold: missed the last two', 'form', 'fell short of his baseline in each of his last two games', lambda r: r.prev_hit == 0 and r.prev2_hit == 0),
        ('wr1soft', 'WR1 vs a bottom-8 pass defense', 'combo', 'the top receiver against a defense that gives up the most to WR1s', lambda r: r.slot == 'WR1' and soft(r, 8)),
        ('rb1imp26', 'RB1 on a team implied 26+', 'combo', 'the lead back in a high-scoring game script', lambda r: r.slot == 'RB1' and cx(r) is not None and cx(r)['imp'] is not None and cx(r)['imp'] >= 26),
        ('te1soft', 'TE1 vs a bottom-8 TE defense', 'combo', 'the starting tight end against a defense soft to tight ends', lambda r: r.slot == 'TE1' and soft(r, 8)),
        ('tgt25soft', 'target share 25%+ vs a bottom-8 defense', 'combo', 'a high-usage target against a soft slot matchup', lambda r: r.pos != 'QB' and (ug(r, 'target_share') or 0) >= .25 and soft(r, 8)),
        ('rz30softTD', 'red-zone share 30%+ vs a TD-soft defense', 'combo', 'the red-zone man against a defense that allows touchdowns to his slot', lambda r: r.pos != 'QB' and (r.rz_l4 or 0) >= .30 and soft(r, 8, td=True)),
    ]
    # eligible player-games: a baseline exists; only players with real usage (≥ 4 PPR baseline) so the field is not bench noise
    E = L[(L.season.isin(SEASONS)) & L.base.notna() & (L.base >= 4)].copy()
    weeks = {se: sorted(E[E.season == se].week.unique()) for se in SEASONS}
    # the current week (games not all played): from games.csv
    games = pd.read_csv(f'{NV}/games.csv'); cur = games[(games.season == CUR) & (games.game_type == 'REG')]
    today = pd.Timestamp.today().normalize(); last = pd.to_datetime(cur.groupby('week').gameday.max())
    wk = int(last[last >= today].index.min()) if (last >= today).any() else int(cur.week.max()) + 1
    # the current week's candidates: this week's matchups (every rostered player with a baseline), with pre-game attributes computed as of now
    M = pd.read_csv('data/processed/matchups_current.csv') if os.path.exists('data/processed/matchups_current.csv') else pd.DataFrame()
    cur_rows = []
    if len(M) and int(M.week.iloc[0]) == wk:
        Lp = L[~((L.season == CUR) & (L.week == wk))]          # everything BEFORE this week: live state never sees this week's results
        base_now = Lp.groupby('n').fantasy_pts_ppr.apply(lambda s: s.tail(6).mean() if len(s) >= 3 else np.nan)
        hist_now = Lp.groupby('n').hit.apply(lambda s: list(s.tail(2)))
        ures = {}
        for n, grp in U[(U.season == CUR) & (U.week < wk)].groupby('n'):
            g2 = grp.sort_values('week'); ures[n] = dict(target_share=g2.target_share.mean(), rush_share=g2.rush_share.mean(), snap_pct=g2.snap_pct.mean(), adot=g2.adot.mean(), wopr=g2.wopr.mean(), target_share_l2=g2.target_share.tail(2).mean(), g=len(g2))
        rz_now = {}
        for n, grp in Lp[Lp.season == CUR].groupby('n'): rz_now[n] = grp.sort_values('week').rz.tail(4).mean() if len(grp) >= 2 else 0
        tdsh = {}
        for n, grp in Lp[Lp.season == CUR].groupby('n'):
            tt = grp.team_td.sum(); tdsh[n] = (grp.td.sum() / tt if tt >= 4 else 0, len(grp))
        played = {(r.team, r.n): r for r in L[(L.season == CUR) & (L.week == wk)].itertuples()}
        for m in M.itertuples():
            n = norm(m.player); t = TEAMFIX.get(m.team, m.team); oppraw = str(m.opponent); opp = oppraw.replace('@', '') if oppraw and oppraw != 'BYE' else None
            if not opp or opp == 'nan' or n not in base_now.index or base_now[n] != base_now[n] or base_now[n] < 4 or int(getattr(m, 'injury', 1)) == -1: continue
            slot = str(m.slot); pos = str(m.pos) if hasattr(m, 'pos') else slot[:2]; slotk = 'QB' if slot.startswith('QB') else slot if slot in SLOTSTAT else ('WR4+' if slot.startswith('WR') else 'RB2' if slot.startswith('RB') else 'TE2')
            u = ures.get(n, {}); h = hist_now.get(n, []); ctxr = ctx.get((CUR, wk, t))
            r = dict(season=CUR, week=wk, n=n, player=m.player, team=t, opponent=opp, slot=slot, slotk=slotk, pos=pos, base=float(base_now[n]), rz_l4=rz_now.get(n, 0),
                     g_cum=tdsh.get(n, (0, 0))[1], ptd_cum=0, ttd_cum=0, prev_hit=h[-1] if len(h) >= 1 else None, prev2_hit=h[-2] if len(h) >= 2 else None, h2h_prev_td=None, h2h_prev_hit=None, inj=getattr(m, 'injury', 1))
            hh = Lp[(Lp.n == n) & (Lp.opponent == opp)].sort_values(['season', 'week']).tail(1)
            if len(hh): r['h2h_prev_td'] = float(hh.td.iloc[0]); r['h2h_prev_hit'] = hh.hit.iloc[0]
            r['tdshare'] = tdsh.get(n, (0, 0))[0]
            class R: pass
            rr = R(); rr.__dict__.update(r)
            # usage accessors for the live row
            ukey = (CUR, wk, n)
            class UU: pass
            uu = UU(); uu.target_share_std = u.get('target_share', np.nan); uu.rush_share_std = u.get('rush_share', np.nan); uu.snap_pct_std = u.get('snap_pct', np.nan); uu.adot_std = u.get('adot', np.nan); uu.wopr_std = u.get('wopr', np.nan); uu.target_share_l2 = u.get('target_share_l2', np.nan)
            uk[ukey] = uu
            rr.ttd_cum = 4 if r['tdshare'] else 0; rr.ptd_cum = r['tdshare'] * 4
            pl = played.get((t, n)); rr.ppr = float(pl.fantasy_pts_ppr) if pl is not None else None; rr.td = float(pl.td) if pl is not None else None
            rr.hit = (rr.ppr >= max(1.15 * rr.base, rr.base + 3)) if rr.ppr is not None else None
            cur_rows.append(rr)
    # ---- grade every category by week
    out_cats = []; week_base = {}
    for se in SEASONS:
        for w in weeks[se]:
            Ew = E[(E.season == se) & (E.week == w)]; week_base[f'{se}-{w}'] = dict(n=int(len(Ew)), hr=round(float(Ew.hit.mean()), 3), tdr=round(float((Ew.td >= 1).mean()), 3))
    for cid, label, group, desc, f in CATS:
        wk_rows = {}; n_all = h_all = t_all = 0; n26 = h26 = 0; l4 = []
        for se in SEASONS:
            for w in weeks[se]:
                Ew = E[(E.season == se) & (E.week == w)]
                mem = Ew[[bool(f(r)) for r in Ew.itertuples()]]
                if not len(mem): continue
                k = int(mem.hit.sum()); n = int(len(mem)); kt = int((mem.td >= 1).sum()); base = week_base[f'{se}-{w}']['hr']
                wk_rows[f'{se}-{w}'] = dict(n=n, hits=k, hr=round(k / n, 3), td=kt, base=base, members=[[p, t, s, round(float(x), 1), int(hh)] for p, t, s, x, hh in zip(mem.player, mem.team, mem.slot, mem.fantasy_pts_ppr, mem.hit.astype(int))] if se == CUR else None)
                n_all += n; h_all += k; t_all += kt
                if se == CUR: n26 += n; h26 += k; l4.append((w, n, k, base))
        if n_all < 20: continue
        l4 = sorted(l4)[-4:]; n4 = sum(x[1] for x in l4); k4 = sum(x[2] for x in l4)
        base_all = sum(week_base[kk]['hr'] * wk_rows[kk]['n'] for kk in wk_rows) / max(1, sum(wk_rows[kk]['n'] for kk in wk_rows))
        beat = sum(1 for kk, v in wk_rows.items() if v['hr'] >= v['base'] * 1.1); qw = len(wk_rows)
        members = []
        for rr in cur_rows:
            try: ok = bool(f(rr))
            except Exception: ok = False
            if ok: members.append(dict(player=rr.player, team=rr.team, opp=rr.opponent, slot=rr.slot, pos=rr.pos, base=round(rr.base, 1), ppr=rr.ppr, hit=None if rr.hit is None else int(rr.hit), td=None if rr.td is None else int(rr.td >= 1), inj=rr.inj))
        pl = [m for m in members if m['hit'] is not None]
        out_cats.append(dict(id=cid, label=label, group=group, desc=desc, n=n_all, hits=h_all, hr=round(h_all / n_all, 3), base=round(base_all, 3), lift=round((h_all / n_all) / base_all, 3) if base_all else None,
                             td=t_all, tdr=round(t_all / n_all, 3), n26=n26, hr26=round(h26 / n26, 3) if n26 else None, n4=n4, hr4=round(k4 / n4, 3) if n4 else None, beat=beat, qw=qw, weeks=wk_rows,
                             cur=dict(n=len(members), played=len(pl), hits=sum(m['hit'] for m in pl), hr=round(sum(m['hit'] for m in pl) / len(pl), 3) if pl else None, members=members)))
    out_cats.sort(key=lambda c: -(c['lift'] or 0))
    # compact the member lists: a player table + slot table, members as short arrays (the dashboard expands them)
    PLI = {}; SLI = {}
    def pi(p, t):
        k = (p, t)
        if k not in PLI: PLI[k] = len(PLI)
        return PLI[k]
    def si(sl):
        if sl not in SLI: SLI[sl] = len(SLI)
        return SLI[sl]
    for c in out_cats:
        for w in c['weeks'].values():
            if w['members']: w['members'] = [[pi(p, t), si(sl), x, hh] for p, t, sl, x, hh in w['members']]
        c['cur']['members'] = [[pi(m['player'], m['team']), si(m['slot']), m['opp'], m['pos'], m['base'], m['ppr'], m['hit'], m['td'], m['inj']] for m in c['cur']['members']]
    players = [list(k) for k, _ in sorted(PLI.items(), key=lambda kv: kv[1])]; slots = [k for k, _ in sorted(SLI.items(), key=lambda kv: kv[1])]
    field = dict(n=sum(1 for _ in cur_rows), played=sum(1 for r in cur_rows if r.hit is not None), hits=sum(1 for r in cur_rows if r.hit))
    out = dict(built=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), week=wk, seasons=SEASONS, cats=out_cats, week_base=week_base, field=field, players=players, slots=slots,
               defs=dict(hit='PPR points at least 15% or 3 points above his baseline (the mean of his previous six games; needs three)', field='every player with a baseline of 4+ points that week', lift='the category\'s hit rate divided by the field\'s hit rate in the same weeks'))
    def clean(o):
        if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, list): return [clean(v) for v in o]
        if isinstance(o, float) and (np.isnan(o) or np.isinf(o)): return None
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
        if isinstance(o, (np.bool_,)): return bool(o)
        return o
    json.dump(clean(out), open('data/processed/categories.json', 'w'), separators=(',', ':'))
    print(f"categories.json: {len(out_cats)} categories · week {wk} · {field['n']} candidates, {field['played']} played · top by lift: " + ', '.join(f"{c['label']} {c['lift']:.2f}× ({c['hr']:.0%}, n {c['n']})" for c in out_cats[:6]))

if __name__ == '__main__':
    main()
