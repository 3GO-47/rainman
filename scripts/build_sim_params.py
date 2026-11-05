"""Simulation parameters — everything the game simulator needs, estimated from the data the site already keeps.

League tables (nflverse play-by-play, every season on disk, before the week being simulated):
  pass_prob   P(dropback | down, distance, field zone, score state, clock)        the play-calling baseline a coordinator shifts
  yards       empirical yardage quantiles for completions, rushes, scrambles, sacks by zone and down bucket
  comp, int, sack, scramble, fumble rates; explosive thresholds; kickoff start, punt net, FG make by distance (result inferred
  from the next play's score), 4th-down go rate by distance and zone, seconds between snaps by situation, home edge, return TDs
Team profiles (one per team, as of the week): the OFFENSE under its coordinator — pass rate over expected, neutral pass rate,
  pace, EPA/play passing and rushing, success, explosive rate, red-zone pass rate, play action, target shares by position,
  completion %, INT / sack / fumble rates, 4th-down aggressiveness; the DEFENSE under its coordinator — EPA allowed passing and
  rushing, completion % allowed, pressure / sack / INT rates, blitz, man / zone, two-high, scheme family and what that family
  concedes to each slot (scheme_slot_effects), red-zone TD rate allowed.
  Coach attachment: when a coordinator is new this season, his prior is the unit he ran last season (coaching.csv oc_from /
  dc_from); otherwise the same unit last season. Current season weight = games / (games + 5).
Players: this week's depth chart (injury -1 excluded), target / carry shares from the last five games (player_usage.csv),
  catch rate, yards per target, yards per carry from the game logs (shrunk to position means), red-zone and goal-line shares
  (redzone_players.csv), QB completion %, yards per attempt, INT rate, sack and scramble rates.
Games: the week's schedule with the posted spread / total, roof, rest (nflverse games.csv).
Usage: python3 scripts/build_sim_params.py [--week W] [--out data/processed/sim_params.json]
  --week W builds the parameters as of week W of the current season (only weeks < W are used) — the backtest calls it per week.
"""
import os, re, glob, json, argparse
import numpy as np, pandas as pd

def _clean(o):
    """JSON for the browser: NaN/inf → null, numpy scalars → Python"""
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if (o != o or o in (float('inf'), float('-inf'))) else float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.bool_): return bool(o)
    return o
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
NV = 'data/raw/nflverse'; SEASON = 2026
import json as _json
CFG = dict(prior_w=3.0, opp_adj=0, qb_adj=1, def_inj=1, lam=60.0)   # 2026-11-05 grid on wk 4-8: qb_adj and prior_w 3 cut margin error 9.28 -> 9.14; opponent-adjusted EPA (ridge) made it worse (9.71 at lam 60, 9.24 at 300) and stays off; CFG.update(_json.loads(os.environ.get('SIM_CFG', '{}')))   # backtest grid overrides
FIX = {'LA': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX'}
POSW = {'QB': 1, 'RB': 1, 'WR': 1, 'TE': 1}
Q = np.linspace(0, 1, 101)

def norm(n): return re.sub(r'[^a-z]', '', re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", '', str(n).lower()))
def tg_b(t): return 's' if t <= 2 else 'm' if t <= 6 else 'l' if t <= 10 else 'x'
def z_b(y): return 'rz' if y <= 20 else 'plus' if y <= 49 else 'mid' if y <= 79 else 'own'
def sd_b(d): return 'T2' if d <= -9 else 'T1' if d < 0 else 'E' if d == 0 else 'L1' if d <= 8 else 'L2'
def t_b(s): return 'H1' if s > 2100 else 'H1late' if s > 1800 else 'H2' if s > 300 else 'late'
def dn_b(d): return 'early' if d <= 2 else 'late'

def load_pbp(week):
    P = []
    for f in sorted(glob.glob(f'{NV}/pbp_slim_*.parquet')):
        s = int(re.findall(r'(\d{4})', os.path.basename(f))[0]); d = pd.read_parquet(f); d['season'] = s
        if s == SEASON: d = d[d.week < week]
        if s < SEASON or len(d): P.append(d)
    P = pd.concat(P, ignore_index=True)
    for c in ('posteam', 'defteam'): P[c] = P[c].replace(FIX)
    P = P.sort_values(['game_id', 'play_id']).reset_index(drop=True)
    return P

def league(P, week=None):
    L = {}
    S = P[(P.play_type.isin(['pass', 'run'])) & P.down.notna() & (P.two_point_attempt != 1) & (P.special_teams_play != 1)].copy()
    S['tg'] = S.ydstogo.map(tg_b); S['z'] = S.yardline_100.map(z_b); S['sd'] = S.score_differential.fillna(0).map(sd_b); S['t'] = S.game_seconds_remaining.fillna(1800).map(t_b)
    S['d'] = S.down.astype(int); S['dn'] = S.d.map(dn_b)
    # play-calling baseline: P(dropback) by situation, smoothed toward the down's marginal
    byd = S.groupby('d')['pass'].mean().to_dict()
    g = S.groupby(['d', 'tg', 'z', 'sd', 't'])['pass'].agg(['sum', 'count'])
    L['pass_prob'] = {f'{d}|{tg}|{z}|{sd}|{t}': round(float((r['sum'] + 12 * byd[d]) / (r['count'] + 12)), 4) for (d, tg, z, sd, t), r in g.iterrows()}
    L['pass_by_down'] = {int(k): round(float(v), 4) for k, v in byd.items()}
    L['pass_rate'] = round(float(S['pass'].mean()), 4)
    # yardage quantiles
    cmp_ = S[(S.complete_pass == 1)]; rush = S[(S.rush == 1) & (S.qb_scramble != 1)]; scr = S[S.qb_scramble == 1]; sack = S[S.sack == 1]
    yq = {}
    for z in ('own', 'mid', 'plus', 'rz'):
        for dn in ('early', 'late'):
            a = cmp_[(cmp_.z == z) & (cmp_.dn == dn)]; b = rush[(rush.z == z) & (rush.dn == dn)]
            if z == 'rz': a = a[a.touchdown != 1]; b = b[b.touchdown != 1]   # inside the 20 the touchdown is drawn by spot (rz_td), the yardage table is the non-scoring plays
            a = a.yards_gained.dropna(); b = b.yards_gained.dropna()
            yq[f'pass|{z}|{dn}'] = np.quantile(a if len(a) > 200 else cmp_.yards_gained.dropna(), Q).round(1).tolist()
            yq[f'rush|{z}|{dn}'] = np.quantile(b if len(b) > 200 else rush.yards_gained.dropna(), Q).round(1).tolist()
    # red zone: P(touchdown) by spot — the compressed field makes a yardage draw the wrong tool there
    rzb = lambda y: 0 if y <= 3 else 1 if y <= 6 else 2 if y <= 10 else 3 if y <= 15 else 4
    rzc = cmp_[cmp_.z == 'rz'].assign(b=lambda d: d.yardline_100.map(rzb)); rzr = rush[rush.z == 'rz'].assign(b=lambda d: d.yardline_100.map(rzb))
    L['rz_td'] = {'pass': [round(float(rzc[rzc.b == i].touchdown.mean()), 4) for i in range(5)], 'rush': [round(float(rzr[rzr.b == i].touchdown.mean()), 4) for i in range(5)]}
    yq['scramble'] = np.quantile(scr.yards_gained.dropna(), Q).round(1).tolist(); yq['sack'] = np.quantile(sack.yards_gained.dropna(), Q).round(1).tolist()
    L['yards'] = yq
    att = S[(S.pass_attempt == 1) & (S.sack != 1)]
    L['comp'] = {f'{z}|{dn}': round(float(att[(att.z == z) & (att.dn == dn)].complete_pass.mean()), 4) for z in ('own', 'mid', 'plus', 'rz') for dn in ('early', 'late')}
    L['comp_rate'] = round(float(att.complete_pass.mean()), 4)
    db = S[S['pass'] == 1]
    L['sack_rate'] = round(float(db.sack.mean()), 4); L['scramble_rate'] = round(float(db.qb_scramble.mean()), 4)
    L['int_rate'] = round(float(att.interception.mean()), 4)
    L['fum_rush'] = round(float(rush.fumble_lost.mean()), 4); L['fum_rec'] = round(float(cmp_.fumble_lost.mean()), 4); L['fum_sack'] = round(float(sack.fumble_lost.mean()), 4)
    L['int_ret_td'] = round(float(S[S.interception == 1].touchdown.mean()), 4) if (S.interception == 1).any() else .03
    L['fum_ret_td'] = round(float(S[S.fumble_lost == 1].touchdown.mean()), 4) if (S.fumble_lost == 1).any() else .02
    L['explosive_pass'] = round(float((cmp_.yards_gained >= 20).mean()), 4); L['explosive_rush'] = round(float((rush.yards_gained >= 12).mean()), 4)
    L['pass_epa'] = round(float(db.epa.mean()), 4); L['rush_epa'] = round(float(rush.epa.mean()), 4)
    L['pass_epa_sd'] = round(float(db.groupby(['season', 'posteam']).epa.mean().std()), 4); L['rush_epa_sd'] = round(float(rush.groupby(['season', 'posteam']).epa.mean().std()), 4)
    # 4th-down go rate by distance and zone
    F = P[(P.down == 4) & P.play_type.isin(['pass', 'run', 'punt', 'field_goal']) & (P.two_point_attempt != 1)].copy()
    F['go'] = F.play_type.isin(['pass', 'run']).astype(int); F['tg'] = F.ydstogo.map(tg_b); F['z'] = F.yardline_100.map(z_b)
    F = F[~((F.score_differential < -8) & (F.game_seconds_remaining < 600))]   # desperation goes are not a tendency
    g4 = F.groupby(['tg', 'z']).go.agg(['sum', 'count'])
    L['fourth_go'] = {f'{tg}|{z}': round(float((r['sum'] + 3 * F.go.mean()) / (r['count'] + 3)), 4) for (tg, z), r in g4.iterrows()}
    # field goals: result from the next play's score for the kicking team
    nxt = P.shift(-1); fg = P[(P.play_type == 'field_goal') & (nxt.game_id == P.game_id)].copy()
    made = np.zeros(len(fg), bool); sd_now = fg.score_differential.values
    for k in (1, 2):   # the next snap is usually the opponent's kickoff (differential flips sign); a no_play row can sit in between
        nk = P.shift(-k); ok = (nk.loc[fg.index, 'game_id'].values == fg.game_id.values) & nk.loc[fg.index, 'posteam'].notna().values
        same = nk.loc[fg.index, 'posteam'].values == fg.posteam.values; sdn = nk.loc[fg.index, 'score_differential'].values
        made |= ok & np.where(same, sdn - sd_now == 3, sd_now + sdn == -3)
    fg['made'] = made; fg['dist'] = fg.yardline_100 + 17
    fgb = {'<30': fg.dist < 30, '30-39': (fg.dist >= 30) & (fg.dist < 40), '40-49': (fg.dist >= 40) & (fg.dist < 50), '50-54': (fg.dist >= 50) & (fg.dist < 55), '55-59': (fg.dist >= 55) & (fg.dist < 60), '60+': fg.dist >= 60}
    L['fg'] = {k: round(float(fg[m].made.mean()), 3) if m.sum() >= 20 else None for k, m in fgb.items()}
    for k, dflt in (('<30', .97), ('30-39', .93), ('40-49', .82), ('50-54', .70), ('55-59', .58), ('60+', .35)):
        if L['fg'][k] is None: L['fg'][k] = dflt
    # punts: net = y + y2 - 100 (kicker's distance to goal before, receiver's after)
    pu = P[(P.play_type == 'punt') & (nxt.game_id == P.game_id) & (nxt.posteam != P.posteam)]
    net = (pu.yardline_100.values + nxt.loc[pu.index, 'yardline_100'].values - 100)
    net = net[(net > 0) & (net < 80)]
    L['punt_net'] = np.quantile(net, Q).round(1).tolist()
    # drive start after a kickoff
    ko = P[(P.play_type == 'kickoff') & (nxt.game_id == P.game_id)]
    st = nxt.loc[ko.index, 'yardline_100'].dropna().values; st = st[(st >= 1) & (st <= 99)]
    L['ko_start'] = np.quantile(st, Q).round(0).tolist()
    # seconds between snaps, same offense, same drive
    prv = P.shift(1); same_drive = (prv.game_id == P.game_id) & (prv.posteam == P.posteam) & (prv.fixed_drive == P.fixed_drive) & P.play_type.isin(['pass', 'run']) & prv.play_type.isin(['pass', 'run'])
    gap = (prv.game_seconds_remaining - P.game_seconds_remaining)
    ok = same_drive & (gap > 0) & (gap < 60)
    stop = (prv.complete_pass == 0) & (prv['pass'] == 1) & (prv.sack != 1) & (prv.qb_scramble != 1)   # incompletion before this snap
    hurry = (P.no_huddle == 1) | ((P.game_seconds_remaining < 240) & (P.score_differential < 0)) | ((P.half_seconds_remaining < 120) & (P.half_seconds_remaining > 0) & (P.game_seconds_remaining > 1800))
    # return touchdowns on kicks
    L['punt_ret_td'] = round(float(P[P.play_type == 'punt'].touchdown.mean()), 4); L['ko_ret_td'] = round(float(P[P.play_type == 'kickoff'].touchdown.mean()), 4)
    # league reference per team-game (last two seasons) — what the simulator is calibrated to reproduce for an average matchup
    Rf = S[S.season >= SEASON - 1]; n = Rf.groupby(['game_id', 'posteam']).ngroups
    dbf = Rf[Rf['pass'] == 1]; atf = Rf[(Rf.pass_attempt == 1) & (Rf.sack != 1)]; ruf = Rf[(Rf.rush == 1) & (Rf.qb_scramble != 1)]
    tdf = Rf[(Rf.touchdown == 1) & (Rf.interception != 1) & (Rf.fumble_lost != 1)]
    gref = pd.read_csv(f'{NV}/games.csv'); gref = gref[(gref.season >= SEASON - 1) & (gref.game_type == 'REG') & gref.total.notna()]
    if week: gref = gref[(gref.season < SEASON) | (gref.week < week)]
    L['ref'] = dict(plays=round(len(Rf) / n, 2), dropbacks=round(len(dbf) / n, 2), att=round(len(atf) / n, 2), cmp=round(float(atf.complete_pass.sum()) / n, 2), pass_yds=round(float(atf.yards_gained.sum()) / n, 1),
                    rush_att=round(len(ruf) / n, 2), rush_yds=round(float(ruf.yards_gained.sum()) / n, 1), yds=round(float(Rf.yards_gained.sum()) / n, 1), off_td=round(len(tdf) / n, 3),
                    rz_trips=round(float(Rf[Rf.yardline_100 <= 20].groupby(['game_id', 'posteam']).fixed_drive.nunique().sum()) / n, 2), pts=round(float(gref.total.mean()) / 2, 2), seasons=f'{SEASON - 1}-{SEASON}')
    L['snap_gap'] = {'run_or_complete': round(float(gap[ok & ~stop & ~hurry].median()), 1), 'incomplete': round(float(gap[ok & stop & ~hurry].median()), 1),
                     'hurry': round(float(gap[ok & hurry & ~stop].median()), 1), 'hurry_incomplete': round(float(gap[ok & hurry & stop].median()), 1)}
    return L, S


def opp_adjust(X, lam=60.0):
    """Ridge: EPA/play = offense effect + defense effect (+ home), per play type. Returns {team: (off_pass, off_rush, def_pass, def_rush)}
    as deviations from the league mean — a team's EPA with the schedule it actually faced taken out."""
    out = {}
    for kind, m in (('pass', X['pass'] == 1), ('rush', (X.rush == 1) & (X.qb_scramble != 1))):
        D = X[m & X.epa.notna()]
        if len(D) < 500: continue
        teams = sorted(set(D.posteam) | set(D.defteam)); idx = {t: i for i, t in enumerate(teams)}; n = len(teams)
        A = np.zeros((len(D), 2 * n + 1)); A[np.arange(len(D)), D.posteam.map(idx).values] = 1; A[np.arange(len(D)), n + D.defteam.map(idx).values] = 1
        A[:, 2 * n] = np.where(D.posteam.values == D.game_id.str.split('_').str[3].values, 1, -1) if 'game_id' in D else 0   # home flag from the game id
        y = D.epa.values - D.epa.mean()
        beta = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ y)
        for t in teams: out.setdefault(t, {})[f'off_{kind}'] = float(beta[idx[t]]); out[t][f'def_{kind}'] = float(beta[n + idx[t]])
    return out

def qb_epa_table(S, n0=150, repl=-0.08):
    """EPA per dropback by passer (gsis id), shrunk toward replacement level; and each team-season's usual passer"""
    db = S[(S['pass'] == 1) & S.passer_id.notna()]
    g = db.groupby('passer_id').epa.agg(['sum', 'count']); q = ((g['sum'] + n0 * repl) / (g['count'] + n0)).to_dict(); n = g['count'].to_dict()
    usual = db.groupby(['season', 'posteam']).passer_id.agg(lambda s: s.value_counts().index[0]).to_dict()
    return q, n, usual

STARTERS = {}
def team_profiles(P, S, week):
    off = pd.read_csv('data/processed/team_off_tendencies.csv'); de = pd.read_csv('data/processed/team_def_tendencies.csv')
    co = pd.read_csv('data/processed/coaching.csv'); tags = pd.read_csv('data/processed/scheme_tags.csv'); eff = pd.read_csv('data/processed/scheme_slot_effects.csv')
    rzt = pd.read_csv('data/processed/redzone_teams.csv')
    for d in (off, de, co, tags, rzt): d['team'] = d.team.replace(FIX)
    cur = S[S.season == SEASON]; prior = S[S.season == SEASON - 1]
    def rates(X, team, side):
        """rates the tendencies files do not carry, straight from the play-by-play"""
        T = X[X.posteam == team] if side == 'off' else X[X.defteam == team]
        att = T[(T.pass_attempt == 1) & (T.sack != 1)]; db = T[T['pass'] == 1]; ru = T[(T.rush == 1) & (T.qb_scramble != 1)]; cm = T[T.complete_pass == 1]
        n = T.game_id.nunique()
        return dict(games=n, comp=att.complete_pass.mean() if len(att) else np.nan, int_rate=att.interception.mean() if len(att) else np.nan,
                    sack_rate=db.sack.mean() if len(db) else np.nan, scramble=db.qb_scramble.mean() if len(db) else np.nan,
                    fum=((ru.fumble_lost.sum() + cm.fumble_lost.sum()) / max(1, len(ru) + len(cm))) if len(T) else np.nan,
                    ypa=att.yards_gained.mean() if len(att) else np.nan, ypc=ru.yards_gained.mean() if len(ru) else np.nan,
                    expl_pass=(cm.yards_gained >= 20).mean() if len(cm) else np.nan, expl_rush=(ru.yards_gained >= 12).mean() if len(ru) else np.nan,
                    pass_epa=db.epa.mean() if len(db) else np.nan, rush_epa=ru.epa.mean() if len(ru) else np.nan, success=T.success.mean() if len(T) else np.nan,
                    plays_g=len(T) / n if n else np.nan, pass_rate=T['pass'].mean() if len(T) else np.nan,
                    neutral_pass=T[(T.score_differential.abs() <= 7) & (T.game_seconds_remaining > 600) & (T.down <= 2)]['pass'].mean() if len(T) else np.nan,
                    proe=T.pass_oe.mean() if len(T) and T.pass_oe.notna().any() else np.nan,
                    rz_pass=T[T.yardline_100 <= 20]['pass'].mean() if len(T) else np.nan)
    # 4th-down aggressiveness: team go rate vs the league rate in the same spots
    F = P[(P.down == 4) & P.play_type.isin(['pass', 'run', 'punt', 'field_goal']) & (P.two_point_attempt != 1) & ~((P.score_differential < -8) & (P.game_seconds_remaining < 600))].copy()
    F['go'] = F.play_type.isin(['pass', 'run']).astype(int); F['tg'] = F.ydstogo.map(tg_b); F['z'] = F.yardline_100.map(z_b)
    lg4 = F.groupby(['tg', 'z']).go.mean(); F['exp'] = [lg4.get((a, b), F.go.mean()) for a, b in zip(F.tg, F.z)]
    def aggr(X, team):
        T = X[X.posteam == team]; T = T[T.z.isin(['plus', 'mid']) & T.tg.isin(['s', 'm'])]   # the decisions that are really decisions
        if len(T) < 8: return 1.0
        return float((T.go.sum() + 2 * T.exp.mean() * 4) / (T.exp.sum() + 2 * T.exp.mean() * 4))
    pace_l = off[off.season < SEASON].sec_per_play.mean()
    ADJ = {s: opp_adjust(S[S.season == s], CFG['lam']) for s in (SEASON - 1, SEASON)} if CFG['opp_adj'] else {}
    lg_pass, lg_rush = float(S[S['pass'] == 1].epa.mean()), float(S[(S.rush == 1) & (S.qb_scramble != 1)].epa.mean())
    QE, QN, QUSUAL = qb_epa_table(S)
    INJ = pd.read_csv('data/processed/injuries_current.csv') if CFG['def_inj'] and os.path.exists('data/processed/injuries_current.csv') else None
    teams = sorted(set(off[off.season == SEASON].team))
    out = {}
    RM = pd.concat([pd.read_parquet(f'{NV}/roster_{s}.parquet')[['gsis_id', 'full_name']] for s in (SEASON - 1, SEASON)]).dropna().drop_duplicates('gsis_id'); RM['n'] = RM.full_name.map(norm); N2G = {r.n: r.gsis_id for r in RM.itertuples()}
    co26 = co[co.season == SEASON].set_index('team'); tag26 = tags[(tags.season == SEASON)].set_index(['team', 'side'])
    def row(df, season, team): r = df[(df.season == season) & (df.team == team)]; return r.iloc[0].to_dict() if len(r) else None
    def blend(cur_d, pri_d, g, keys):
        w = g / (g + CFG['prior_w']) if g else 0.0; o = {}
        for k in keys:
            a = cur_d.get(k) if cur_d else None; b = pri_d.get(k) if pri_d else None
            a = None if a is None or (isinstance(a, float) and np.isnan(a)) else float(a); b = None if b is None or (isinstance(b, float) and np.isnan(b)) else float(b)
            o[k] = None if a is None and b is None else b if a is None else a if b is None else round(w * a + (1 - w) * b, 4)
        return o, round(w, 3)
    OK = ['pass_rate', 'neutral_pass_rate', 'early_down_pass_rate', 'proe', 'sec_per_play', 'plays_per_game', 'play_action_rate', 'rpo_rate', 'motion_rate', 'screen_rate', 'adot', 'deep_rate',
          'epa_play', 'success_rate', 'pass_epa', 'rush_epa', 'explosive_rate', 'rz_pass_rate', 'rb_tgt_share', 'te_tgt_share', 'wr_tgt_share', 'no_huddle_rate', 'shotgun_rate', 'p11', 'p12']
    DK = ['blitz_rate', 'pressure_rate', 'sack_rate', 'int_rate', 'man_rate', 'zone_rate', 'two_high', 'single_high', 'avg_box', 'light_box_rate', 'nickel_rate', 'base_rate',
          'epa_play_allowed', 'pass_epa_allowed', 'rush_epa_allowed', 'success_allowed', 'explosive_allowed', 'adot_faced']
    RK = ['comp', 'int_rate', 'sack_rate', 'scramble', 'fum', 'ypa', 'ypc', 'expl_pass', 'expl_rush', 'pass_epa', 'rush_epa', 'success', 'plays_g', 'pass_rate', 'neutral_pass', 'proe', 'rz_pass']
    for t in teams:
        c = co26.loc[t] if t in co26.index else None
        oc_from = c.oc_from if c is not None and isinstance(c.oc_from, str) and re.fullmatch(r'[A-Z]{2,3}', c.oc_from) else t
        dc_from = c.dc_from if c is not None and isinstance(c.dc_from, str) and re.fullmatch(r'[A-Z]{2,3}', c.dc_from) else t
        oc_from, dc_from = FIX.get(oc_from, oc_from), FIX.get(dc_from, dc_from)
        g = int(cur[cur.posteam == t].game_id.nunique())
        o_cur, o_pri = row(off, SEASON, t), row(off, SEASON - 1, oc_from); d_cur, d_pri = row(de, SEASON, t), row(de, SEASON - 1, dc_from)
        O, w = blend(o_cur, o_pri, g, OK); D, _ = blend(d_cur, d_pri, g, DK)
        # opponent-adjusted EPA replaces the raw season EPA when the ridge has the season (current unit this year, the coordinator's prior unit last year)
        if ADJ:
            a_cur, a_pri = ADJ.get(SEASON, {}).get(t), ADJ.get(SEASON - 1, {}).get(oc_from); d_curA, d_priA = ADJ.get(SEASON, {}).get(t), ADJ.get(SEASON - 1, {}).get(dc_from)
            ww = g / (g + CFG['prior_w']) if g else 0.0
            def bl(c, pr, k): c = None if c is None else c.get(k); pr = None if pr is None else pr.get(k); return None if c is None and pr is None else (pr if c is None else c if pr is None else ww * c + (1 - ww) * pr)
            op, orr = bl(a_cur, a_pri, 'off_pass'), bl(a_cur, a_pri, 'off_rush'); dp, dr = bl(d_curA, d_priA, 'def_pass'), bl(d_curA, d_priA, 'def_rush')
            if op is not None: O['pass_epa_raw'] = O.get('pass_epa'); O['pass_epa'] = round(lg_pass + op, 4)
            if orr is not None: O['rush_epa_raw'] = O.get('rush_epa'); O['rush_epa'] = round(lg_rush + orr, 4)
            if dp is not None: D['pass_epa_allowed_raw'] = D.get('pass_epa_allowed'); D['pass_epa_allowed'] = round(lg_pass + dp, 4)
            if dr is not None: D['rush_epa_allowed_raw'] = D.get('rush_epa_allowed'); D['rush_epa_allowed'] = round(lg_rush + dr, 4)
        # defensive starters ruled out: a missing first-string DB loosens the pass defense, a missing front-seven starter the run defense
        if INJ is not None:
            Z = INJ[(INJ.team.replace(FIX) == t) & (INJ.side == 'DEF') & (INJ.depth == 1) & INJ.status.isin(['Out', 'Injured Reserve', 'Doubtful', 'PUP', 'Suspended'])]
            db_out = int(Z.pos.isin(['CB', 'S', 'DB', 'FS', 'SS', 'NB']).sum()); f7_out = int(len(Z) - db_out)
            if db_out or f7_out:
                D['pass_epa_allowed'] = round((D.get('pass_epa_allowed') or lg_pass) + .012 * db_out + .004 * f7_out, 4); D['rush_epa_allowed'] = round((D.get('rush_epa_allowed') or lg_rush) + .008 * f7_out, 4)
                D['def_out'] = [f"{r.player} ({r.role})" for r in Z.itertuples()]
        RO, _ = blend(rates(cur, t, 'off'), rates(prior, oc_from, 'off'), g, RK); RD, _ = blend(rates(cur, t, 'def'), rates(prior, dc_from, 'def'), g, RK)
        fam = tag26.loc[(t, 'DEF')].primary_tag if (t, 'DEF') in tag26.index else None
        slot_idx = {r.grp: round(float(r['index']) / 100, 3) for _, r in eff[eff.family == fam].iterrows()} if fam else {}
        rz_o = rzt[(rzt.season == SEASON) & (rzt.side == 'off') & (rzt.scope == 'season') & (rzt.team == t)]; rz_d = rzt[(rzt.season == SEASON) & (rzt.side == 'def') & (rzt.scope == 'season') & (rzt.team == t)]
        ag = aggr(F[F.season == SEASON], t); ag_p = aggr(F[F.season == SEASON - 1], oc_from); agg = round((g / (g + 5)) * ag + (5 / (g + 5)) * ag_p, 3)
        # QB attached to the passing game: the named starter's EPA per dropback (shrunk) vs the passer this unit has mostly used
        if CFG['qb_adj']:
            st_name = STARTERS.get(t); usual = QUSUAL.get((SEASON, t)) or QUSUAL.get((SEASON - 1, oc_from))
            sid = N2G.get(norm(st_name)) if st_name else None
            if sid and usual and sid != usual:
                delta = QE.get(sid, -0.08) - QE.get(usual, 0.0)
                O['qb_delta'] = round(float(delta), 4); O['pass_epa'] = round((O.get('pass_epa') or lg_pass) + float(np.clip(delta, -.2, .15)), 4); O['qb_swap'] = f"{st_name} for the usual passer · {QN.get(sid, 0)} dropbacks on file"
        out[t] = dict(games=g, weight_current=w,
            off=dict(hc=c.hc if c is not None else None, oc=c.oc if c is not None else None, oc_prior_unit=oc_from, oc_new=bool(c.oc_changed == 1) if c is not None else False, **O, **{f'pbp_{k}': v for k, v in RO.items()},
                     pace_factor=round((O['sec_per_play'] or pace_l) / pace_l, 3), fourth_aggr=agg),
            de=dict(dc=c.dc if c is not None else None, dc_prior_unit=dc_from, dc_new=bool(c.dc_changed == 1) if c is not None else False, family=fam, slot_idx=slot_idx, **D, **{f'pbp_{k}': v for k, v in RD.items()}),
            rz=dict(off_td_rate=float(rz_o.td_rate.iloc[0]) if len(rz_o) and pd.notna(rz_o.td_rate.iloc[0]) else None, off_trips_g=round(float(rz_o.trips.iloc[0] / max(1, rz_o.games.iloc[0])), 2) if len(rz_o) else None,
                    off_trips=int(rz_o.trips.iloc[0]) if len(rz_o) else 0, def_trips=int(rz_d.trips.iloc[0]) if len(rz_d) else 0,
                    def_td_rate=float(rz_d.td_rate.iloc[0]) if len(rz_d) and pd.notna(rz_d.td_rate.iloc[0]) else None))
    return out

def players(S, week, game_dates, starters=None):
    starters = starters or {}
    """the week's depth chart with shares and efficiencies; one list per team"""
    snaps = sorted(glob.glob('data/processed/depth_charts_*.csv'))
    cutoff = min(game_dates) if game_dates else '2099'
    usable = [f for f in snaps if re.findall(r'(\d{4}-\d{2}-\d{2})', f)[0] <= cutoff] or snaps[:1]
    dc = pd.read_csv(usable[-1]); dc['team'] = dc.team.replace(FIX); dc_date = re.findall(r'(\d{4}-\d{2}-\d{2})', usable[-1])[0]
    dc['pos_row'] = dc.pos_row.astype(str).str.replace(r'^WR\d?$', 'WR', regex=True)
    dc = dc[dc.pos_row.isin(['QB', 'RB', 'WR', 'TE']) & (dc.injury.astype(str) != '-1')]
    U = pd.read_csv('data/processed/player_usage.csv'); U['team'] = U.team.replace(FIX)
    U = U[(U.season < SEASON) | (U.week < week)]
    G = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True); G['team'] = G.team.replace(FIX)
    G = G[(G.season < SEASON) | (G.week < week)]; G['n'] = G.player.map(norm)
    RZ = pd.read_csv('data/processed/redzone_players.csv'); RZ['team'] = RZ.team.replace(FIX); RZ = RZ[(RZ.season == SEASON) & (RZ.scope == 'l5')]; RZ['n'] = RZ.player.map(norm)
    # position means for shrinkage (current + prior season)
    Gc = G[G.season >= SEASON - 1]
    pm = {}
    for pos in ('RB', 'WR', 'TE', 'QB'):
        X = Gc[Gc.pos == pos]
        pm[pos] = dict(catch=X.rec.sum() / max(1, X.targets.sum()), ypt=X.rec_yds.sum() / max(1, X.targets.sum()), ypc=X.rush_yds.sum() / max(1, X.rush_att.sum()),
                       ypa=X.pass_yds.sum() / max(1, X.pass_att.sum()), comp=X.cmp.sum() / max(1, X.pass_att.sum()), int=X['int'].sum() / max(1, X.pass_att.sum()))
    DEF_T = {'WR1': .23, 'WR2': .17, 'WR3': .11, 'WR4+': .04, 'TE1': .15, 'TE2': .04, 'RB1': .11, 'RB2': .05, 'QB1': 0, 'QB2': 0}
    DEF_R = {'RB1': .60, 'RB2': .24, 'QB1': .09, 'WR1': .02, 'WR2': .01, 'WR3': .01, 'WR4+': .01, 'TE1': .01, 'TE2': 0, 'QB2': 0}
    out = {}
    for t, T in dc.groupby('team'):
        Ut = U[U.team == t]; lastw = sorted(Ut[Ut.season == SEASON].week.unique())[-5:]
        rows = []
        for _, r in T.iterrows():
            ln = r['log_name'] if 'log_name' in r.index and isinstance(r['log_name'], str) and r['log_name'] else r.player; n = norm(ln); slot = str(r.slot); pos = r.pos_row
            ug = Ut[(Ut.player.map(norm) == n) & (Ut.season == SEASON) & (Ut.week.isin(lastw))]
            if len(ug) < 2: ug2 = Ut[(Ut.player.map(norm) == n)].sort_values(['season', 'week']).tail(6); ug = ug2 if len(ug2) else ug
            tsh = float(ug.target_share.mean()) if len(ug) and ug.target_share.notna().any() else DEF_T.get(slot, .03)
            rsh = float(ug.rush_share.mean()) if len(ug) and ug.rush_share.notna().any() else DEF_R.get(slot, .01)
            gp_u = int(len(ug))
            L = G[(G.n == n)]; Lc = L[L.season == SEASON]; Lp = L[L.season == SEASON - 1]
            def eff(num, den, mean, n0):
                a = Lc[num].sum() + .5 * Lp[num].sum(); b = Lc[den].sum() + .5 * Lp[den].sum()
                return round(float((a + n0 * mean) / (b + n0)), 3), int(Lc[den].sum())
            M = pm.get(pos, pm['WR'])
            catch, ntg = eff('rec', 'targets', M['catch'], 25); ypt, _ = eff('rec_yds', 'targets', M['ypt'], 25); ypc, nru = eff('rush_yds', 'rush_att', M['ypc'], 40)
            rz = RZ[(RZ.team == t) & (RZ.n == n)]
            rzsh = float(rz.rz_opp_share.iloc[0]) if len(rz) and pd.notna(rz.rz_opp_share.iloc[0]) else None
            gl = int(rz.gl_rush.iloc[0]) if len(rz) else 0; ez = int(rz.ez_tgt.iloc[0]) if len(rz) else 0
            d = dict(name=r.player, pos=pos, slot=slot, inj=str(r.injury), tgt_share=round(tsh, 3), rush_share=round(rsh, 3), usage_games=gp_u,
                     catch=catch, ypt=ypt, ypc=ypc, targets_seen=ntg, carries_seen=nru, rz_share=rzsh, gl_rush=gl, ez_tgt=ez)
            if pos == 'QB':
                comp, natt = eff('cmp', 'pass_att', M['comp'], 120); ypa, _ = eff('pass_yds', 'pass_att', M['ypa'], 120); ir, _ = eff('int', 'pass_att', M['int'], 200)
                # sack / scramble from the play-by-play by name (roster gsis -> name)
                d.update(comp=comp, ypa=ypa, int_rate=ir, att_seen=natt)
            rows.append(d)
        # renormalise shares among the men on the chart (an injured starter's share flows to the rest)
        ts = sum(x['tgt_share'] for x in rows if x['pos'] != 'QB') or 1; rs = sum(x['rush_share'] for x in rows) or 1
        for x in rows:
            x['tgt_w'] = round(x['tgt_share'] / ts, 4) if x['pos'] != 'QB' else 0.0; x['rush_w'] = round(x['rush_share'] / rs, 4)
        # the named starter (nflverse games.csv, updated toward kickoff) leads the QB room; an OUT QB1 already fell off the chart
        want = starters.get(t)
        if want:
            qbs = [x for x in rows if x['pos'] == 'QB']; hit = next((x for x in qbs if norm(x['name']) == norm(want)), None)
            if hit and qbs and qbs[0] is not hit:
                for i, x in enumerate(qbs): x['slot'] = f'QB{i + 1}'
                hit['slot'], qbs[0]['slot'] = 'QB1', hit['slot'] if hit['slot'] != 'QB1' else 'QB2'
                rows.sort(key=lambda x: (x['pos'] != 'QB', x['slot']))
        out[t] = dict(depth_chart=dc_date, players=rows)
    # QB sack / scramble rates from pbp by passer
    R = pd.concat([pd.read_parquet(f'{NV}/roster_{s}.parquet')[['gsis_id', 'full_name']] for s in (SEASON - 1, SEASON)]).dropna().drop_duplicates('gsis_id')
    R['n'] = R.full_name.map(norm); gmap = R.set_index('gsis_id').n.to_dict()
    db = S[(S['pass'] == 1) & S.passer_id.notna()].copy(); db['n'] = db.passer_id.map(gmap)
    q = db.groupby('n').agg(sack=('sack', 'mean'), scr=('qb_scramble', 'mean'), n=('sack', 'size'))
    lg_s, lg_c = float(db.sack.mean()), float(db.qb_scramble.mean())
    for t, d in out.items():
        for x in d['players']:
            if x['pos'] != 'QB': continue
            r = q.loc[norm(x['name'])] if norm(x['name']) in q.index else None
            n = float(r.n) if r is not None else 0
            x['sack_rate'] = round((float(r.sack) * n + lg_s * 150) / (n + 150), 4) if r is not None else round(lg_s, 4)
            x['scramble'] = round((float(r.scr) * n + lg_c * 150) / (n + 150), 4) if r is not None else round(lg_c, 4)
            x['dropbacks_seen'] = int(n)
    return out, pm

def games(week):
    g = pd.read_csv(f'{NV}/games.csv'); g = g[(g.season == SEASON) & (g.week == week) & (g.game_type == 'REG')].copy()
    for c in ('away_team', 'home_team'): g[c] = g[c].replace(FIX)
    rows = []
    for _, r in g.iterrows():
        rows.append(dict(game_id=r.game_id, week=int(r.week), date=str(r.gameday), time=str(r.gametime), away=r.away_team, home=r.home_team,
                         spread=None if pd.isna(r.spread_line) else float(r.spread_line), total=None if pd.isna(r.total_line) else float(r.total_line),
                         roof=r.roof if isinstance(r.roof, str) else None, away_rest=int(r.away_rest) if pd.notna(r.away_rest) else 7, home_rest=int(r.home_rest) if pd.notna(r.home_rest) else 7,
                         away_qb=r.away_qb_name if isinstance(r.away_qb_name, str) else None, home_qb=r.home_qb_name if isinstance(r.home_qb_name, str) else None,
                         away_score=None if pd.isna(r.away_score) else float(r.away_score), home_score=None if pd.isna(r.home_score) else float(r.home_score)))
    return rows

def home_edge():
    g = pd.read_csv(f'{NV}/games.csv'); g = g[(g.season.isin([SEASON - 2, SEASON - 1])) & (g.game_type == 'REG') & g.result.notna() & (g.location == 'Home')]
    return round(float(g.result.mean()), 2)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--week', type=int); ap.add_argument('--out', default='data/processed/sim_params.json'); a = ap.parse_args()
    g = pd.read_csv(f'{NV}/games.csv'); cur = g[(g.season == SEASON) & (g.game_type == 'REG')]
    today = pd.Timestamp.now().strftime('%Y-%m-%d'); last = cur.groupby('week').gameday.max()
    if a.week: week = a.week
    elif (last >= today).any(): week = int(last[last >= today].index.min())   # the first week with a game still to be played
    else: week = int(cur.week.max()) + 1
    P = load_pbp(week); L, S = league(P, week)
    GM = games(week)
    st = {}
    for x in GM:
        if x.get('away_qb'): st[x['away']] = x['away_qb']
        if x.get('home_qb'): st[x['home']] = x['home_qb']
    STARTERS.update(st)
    T = team_profiles(P, S, week)
    PL, pm = players(S, week, [x['date'] for x in GM], st)
    L['home_edge'] = home_edge(); L['rows'] = int(len(P)); L['pos_means'] = {k: {kk: round(float(vv), 4) for kk, vv in v.items()} for k, v in pm.items()}
    out = dict(built=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), season=SEASON, week=week, pbp_through=f'{SEASON} wk {int(P[P.season == SEASON].week.max()) if (P.season == SEASON).any() else 0}', league=L, teams=T, players=PL, games=GM)
    os.makedirs(os.path.dirname(a.out), exist_ok=True); json.dump(_clean(out), open(a.out, 'w'), separators=(',', ':'))
    print(f'{a.out}: season {SEASON} week {week} · {len(GM)} games · {len(T)} teams · {sum(len(v["players"]) for v in PL.values())} players · pbp rows {len(P)} · home edge {L["home_edge"]}')

if __name__ == '__main__':
    main()
