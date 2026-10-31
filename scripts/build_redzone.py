"""Red-zone usage layer from nflverse play-by-play (pbp_slim) + snap counts.

Per player (every season on disk, full season and the team's last five games):
  rz_rush   rushes from the 20 in          gl_rush   rushes from the 10 in
  rz_tgt    targets from the 20 in         ez_tgt    targets thrown into the end zone (air yards >= yardline)
  rz_opp_share  his RZ rushes + targets / his team's RZ pass+run plays (the closest thing to a red-zone snap share
                without participation data, which nflverse stopped carrying after 2025)
  snap_pct  offensive snap share (snap_counts), same window
  xtd       expected touchdowns: every rush and target he had, anywhere on the field, weighted by the league TD rate
            for that play type at that yard line (rates fit on every season on disk)   ·   td = actual rushing + receiving TDs
  rz_td     TDs scored from the 20 in
Per team: RZ plays, pass %, run %, PROE (pass_oe, nflverse's pass rate over expected), trips (drives that reached the 20),
  TD trips, TD rate — as an offense (posteam) and as a defense (defteam, "allowed").
TD usage score (0-100): percentile blend within the window of xTD per game (.35), RZ opportunity share (.20),
  goal-line carries + end-zone targets per game (.20), the opponent's RZ TD rate allowed (.15), his team's RZ trips per
  game (.10); the opponent is this week's from matchups_current.csv.
Writes data/processed/redzone_players.csv, redzone_teams.csv. Usage: python3 scripts/build_redzone.py
"""
import os, glob, re, csv
import pandas as pd, numpy as np

NV = 'data/raw/nflverse'
OUT = 'data/processed'
SEASONS = sorted(int(re.findall(r'(\d{4})', os.path.basename(f))[0]) for f in glob.glob(f'{NV}/pbp_slim_*.parquet'))
WINDOW = 5

def load(name, s):
    p = f'{NV}/{name}_{s}.parquet'
    return pd.read_parquet(p) if os.path.exists(p) else None

def main():
    P = pd.concat([load('pbp_slim', s).assign(season=s) for s in SEASONS], ignore_index=True)
    P = P.replace({'posteam': {'LA': 'LAR', 'WSH': 'WAS'}, 'defteam': {'LA': 'LAR', 'WSH': 'WAS'}})
    P = P[(P.special_teams_play != 1) & (P.two_point_attempt != 1) & P.play_type.isin(['pass', 'run']) & P.posteam.notna()].copy()
    P['yl'] = P.yardline_100.clip(1, 99)
    P['is_rush'] = (P.rush_attempt == 1) & P.rusher_id.notna()
    P['is_tgt'] = (P.pass_attempt == 1) & P.receiver_id.notna()
    P['ez'] = P.is_tgt & (P.air_yards >= P.yl)
    # league TD rate by play type x yard line (smoothed by 5-yard bucket, pooled over every season on disk)
    P['bucket'] = ((P.yl - 1) // 5).astype(int)
    rt = {}
    for kind, mask in (('rush', P.is_rush), ('tgt', P.is_tgt)):
        g = P[mask].groupby('bucket').agg(n=('touchdown', 'size'), td=('touchdown', 'sum'))
        g['rate'] = (g.td + 1) / (g.n + 10)
        rt[kind] = g.rate.to_dict()
    P['xtd'] = np.where(P.is_rush, P.bucket.map(rt['rush']), np.where(P.is_tgt, P.bucket.map(rt['tgt']), 0.0))
    P['pid'] = np.where(P.is_rush, P.rusher_id, np.where(P.is_tgt, P.receiver_id, None))
    P['rz'] = P.yl <= 20; P['gl'] = P.yl <= 10
    # rosters: gsis -> name / pfr / position / team
    R = pd.concat([load('roster', s)[['season', 'gsis_id', 'full_name', 'pfr_id', 'position', 'team']] for s in SEASONS]).replace({'team': {'LA': 'LAR', 'WSH': 'WAS'}}).dropna(subset=['gsis_id']).drop_duplicates(['season', 'gsis_id'], keep='last')
    R = R.set_index(['season', 'gsis_id'])
    # snap counts
    S = pd.concat([load('snap_counts', s) for s in SEASONS if load('snap_counts', s) is not None], ignore_index=True)
    S = S[S.game_type == 'REG'] if 'game_type' in S.columns else S
    S = S.replace({'team': {'LA': 'LAR', 'WSH': 'WAS'}})
    # team game index: the team's last WINDOW games per season
    tg = P.groupby(['season', 'posteam']).week.apply(lambda w: sorted(set(w))).to_dict()
    def last_weeks(season, team): return set((tg.get((season, team)) or [])[-WINDOW:])
    rows = []
    for (season, team), G in P.groupby(['season', 'posteam']):
        for scope in ('season', 'l5'):
            W = last_weeks(season, team) if scope == 'l5' else set(G.week)
            Gs = G[G.week.isin(W)]
            team_rz = int(Gs.rz.sum()); games = Gs.week.nunique()
            for pid, X in Gs[Gs.pid.notna()].groupby('pid'):
                meta = R.loc[(season, pid)] if (season, pid) in R.index else None
                name = meta.full_name if meta is not None else pid
                pfr = meta.pfr_id if meta is not None else None
                sn = S[(S.season == season) & (S.team == team) & ((S.pfr_player_id == pfr) if pfr else (S.player == name)) & (S.week.isin(W))].offense_pct if len(S) else pd.Series(dtype=float)
                rows.append(dict(season=season, scope=scope, team=team, pid=pid, player=name, pfr=meta.pfr_id if meta is not None else '', pos=meta.position if meta is not None else '',
                    games=int(X.week.nunique()), team_games=games,
                    rz_rush=int((X.is_rush & X.rz).sum()), gl_rush=int((X.is_rush & X.gl).sum()), rz_tgt=int((X.is_tgt & X.rz).sum()), ez_tgt=int(X.ez.sum()),
                    rush=int(X.is_rush.sum()), tgt=int(X.is_tgt.sum()), rz_opp=int(((X.is_rush | X.is_tgt) & X.rz).sum()), team_rz=team_rz,
                    rz_opp_share=round(((X.is_rush | X.is_tgt) & X.rz).sum() / team_rz, 3) if team_rz else None,
                    snap_pct=round(float(sn.mean()), 3) if len(sn) else None,
                    xtd=round(float(X.xtd.sum()), 2), td=int(X.touchdown.sum()), rz_td=int((X.touchdown.astype(bool) & X.rz).sum())))
    PL = pd.DataFrame(rows)
    # teams: offense and defense, season and l5
    trows = []
    for side, col in (('off', 'posteam'), ('def', 'defteam')):
        for (season, team), G in P.groupby(['season', col]):
            for scope in ('season', 'l5'):
                W = set((tg.get((season, team)) or [])[-WINDOW:]) if scope == 'l5' else set(G.week)
                Gs = G[G.week.isin(W)]; Z = Gs[Gs.rz]
                trips = Z.groupby(['game_id', 'fixed_drive']).size().shape[0]
                td_trips = Z[Z.touchdown == 1].groupby(['game_id', 'fixed_drive']).size().shape[0]
                trows.append(dict(season=season, side=side, scope=scope, team=team, games=int(Gs.week.nunique()), rz_plays=int(len(Z)),
                    pass_pct=round(float(Z['pass'].mean()), 3) if len(Z) else None, run_pct=round(float(Z['rush'].mean()), 3) if len(Z) else None,
                    proe=round(float(Z.pass_oe.mean()), 2) if len(Z) and Z.pass_oe.notna().any() else None,
                    trips=int(trips), td_trips=int(td_trips), td_rate=round(td_trips / trips, 3) if trips else None,
                    rz_td=int(Z.touchdown.sum()), xtd=round(float(Gs.xtd.sum()), 2), td=int(Gs.touchdown.sum())))
    TM = pd.DataFrame(trows)
    os.makedirs(OUT, exist_ok=True)
    PL.to_csv(f'{OUT}/redzone_players.csv', index=False); TM.to_csv(f'{OUT}/redzone_teams.csv', index=False)
    cur = max(SEASONS)
    print(f'redzone_players.csv: {len(PL)} rows · seasons {SEASONS} · {cur}: {PL[(PL.season==cur)&(PL.scope=="season")].pid.nunique()} players · redzone_teams.csv: {len(TM)} rows')
    print('TD rate by bucket (rush):', {k: round(v, 3) for k, v in sorted(rt['rush'].items())[:5]}, '(tgt):', {k: round(v, 3) for k, v in sorted(rt['tgt'].items())[:5]})

if __name__ == '__main__':
    main()
