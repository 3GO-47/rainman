"""Player prop lines (DraftKings via ESPN's public odds API, scraped in Chrome — recipe in notes/scrape_recipe.md)
joined to RAINMAN's own per-stat projections.

Input : data/raw/props_{season}_wk{W}_{date}.txt   lines  GM|eventId|away|home|kickoffUTC|spread text|total
                                                          PB|eventId|espnAthleteId|typeId|market|line|openLine|updated
Output: data/processed/props_current.csv  — one row per player-market: line, open, move, our projection, edge, last-10
                                             over rate, DvP rank of the opponent for that stat, lean
        data/processed/props_ledger.csv   — frozen leans (first time a market is seen for a week), graded from game logs

Per-stat projection = player's own weighted mean of the stat (2026 games ×2, last 8 of 2025 ×1, shrunk toward the
slot mean with k=3 games) × matchup factor, where matchup = 1 + (opp allowed for that stat / league − 1) × w_pos ×
(0.4 + 0.6·trust) — the same DvP shrinkage the Big Board backtest settled on (QB .35 · RB .15 · WR .05 · TE .25).
Lines have no prices in the feed, so edges assume standard -110 juice; a lean needs |edge| ≥ 8% of the line AND the
player's last-10 over-rate on that line to agree (≥ 60% for OVER, ≤ 40% for UNDER); 6+ games of history; line > 1.5.
"""
import os, sys, glob, re, datetime
import pandas as pd, numpy as np
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
W_POS = {'QB': .35, 'RB': .15, 'WR': .05, 'TE': .25}
MARKET = {  # market -> (game_log columns to sum, DvP stat for the player's slot group (None = no DvP column))
    'Total Passing Yards': (['pass_yds'], 'QB PY'), 'Total Pass Completions': (['cmp'], None), 'Total Passing Touchdowns': (['pass_td'], 'P TD'),
    'Total Passing Attempts': (['pass_att'], None), 'Total Passing Interceptions': (['int'], None),
    'Total Passing Plus Rushing Yards': (['pass_yds', 'rush_yds'], 'QB P+R'),
    'Total Carries': (['rush_att'], None), 'Total Rushing Yards': (['rush_yds'], '{g} RY'),
    'Total Receiving Yards': (['rec_yds'], '{g} RecY'), 'Total Receptions': (['rec'], '{g} Recep'),
    'Total Rushing Plus Receiving Yards': (['rush_yds', 'rec_yds'], 'RB R+R'),
}
files = sorted(glob.glob('data/raw/props_2026_wk*_*.txt'))
if not files: print('no props files'); sys.exit()
src = files[-1]; week = int(re.search(r'wk(\d+)', src).group(1))
games, props = {}, []
for line in open(src, encoding='utf-8'):
    f = line.rstrip('\n').split('|')
    if f[0] == 'GM': games[f[1]] = dict(away=f[2].replace('WSH', 'WAS'), home=f[3].replace('WSH', 'WAS'), kick=f[4], spread=f[5], total=f[6])
    elif f[0] == 'PB': props.append(dict(event=f[1], espn_id=f[2], type_id=f[3], market=f[4], line=float(f[5]), open=float(f[6]) if f[6] else np.nan, updated=f[7]))
P = pd.DataFrame(props)
ros = pd.read_parquet('data/raw/nflverse/roster_2026.parquet', columns=['full_name', 'team', 'position', 'espn_id', 'pfr_id'])
ros = ros[ros.espn_id.notna()].drop_duplicates('espn_id')
P = P.merge(ros, on='espn_id', how='left')
P['team'] = P.team.replace({'LA': 'LAR'})
P['away'] = P.event.map(lambda e: games[e]['away']); P['home'] = P.event.map(lambda e: games[e]['home'])
P['opp'] = np.where(P.team == P.home, P.away, P.home)
P['kick'] = P.event.map(lambda e: games[e]['kick'])
# player history from game logs (by pfr id)
L = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))])
L = L.sort_values(['season', 'week'])
dc = pd.read_csv(sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1])
slot_by_name = {r.player: r.slot for r in dc.itertuples()}
# slot by PFR id: the player's slot in his most recent 2026 game log (the depth-chart snapshot of that week), else by name
last26 = L[L.season == 2026].groupby('player_id').tail(1)
slot_by_id = dict(zip(last26.player_id, last26.slot))
norm = lambda n: re.sub(r'[^a-z]', '', str(n).lower().replace(' jr', '').replace(' sr', '').replace(' iii', '').replace(' ii', ''))
slot_by_norm = {norm(k): v for k, v in slot_by_name.items()}
D = pd.read_csv('data/processed/dvp_combined.csv').set_index('defense')
to = pd.read_csv('data/processed/starter_turnover.csv'); co = pd.read_csv('data/processed/coaching.csv')
WK = pd.read_csv('data/processed/dvp_weekly.csv'); wk26 = WK[WK.season == 2026].groupby('defense').week.nunique().to_dict()
def trust(d):
    t = to[(to.season == 2026) & (to.team == d) & (to.side == 'DEF')]; c = co[(co.season == 2026) & (co.team == d)]
    ret = float(t.prev_snaps_returning_pct.iloc[0]) if len(t) else .7; new = len(c) and c.dc_changed.iloc[0] == 1
    return max(0, min(100, 100 - (1 - ret) * 70 - (18 if new else 0) + min(wk26.get(d, 0), 6) * 3))
SLOTG = lambda s: 'QB' if s.startswith('QB') else ('RB1' if s == 'RB1' else 'RB2') if s.startswith('RB') else (s if s in ('WR1', 'WR2', 'WR3') else 'WR4+') if s.startswith('WR') else ('TE1' if s == 'TE1' else 'TE2') if s.startswith('TE') else ''
rows = []
for r in P.itertuples():
    if r.market not in MARKET or pd.isna(r.pfr_id): continue
    cols, dvp_stat = MARKET[r.market]
    h = L[L.player_id == r.pfr_id]; h = h.assign(v=h[cols].sum(axis=1))
    l26 = h[h.season == 2026]; l25 = h[h.season == 2025].tail(8)
    sw = 2 * len(l26) + len(l25); sv = 2 * l26.v.sum() + l25.v.sum()
    own = sv / sw if sw else np.nan
    slot = slot_by_id.get(r.pfr_id) or slot_by_name.get(r.full_name) or slot_by_norm.get(norm(r.full_name), ''); g = SLOTG(slot) if slot else ''
    # slot-mean prior for the stat from the DvP league average (what an average defense allows to this slot)
    prior = None
    if dvp_stat and g and g != 'WR4+':
        col = dvp_stat.format(g=g) + ' avg'
        if col in D.columns: prior = float(D[col].mean())
    base = (own * sw + (prior if prior is not None else own) * 3) / (sw + 3) if sw else prior
    if base is None or pd.isna(base): continue
    m = 1.0; rk = ''
    if dvp_stat and g and r.opp in D.index:
        col = dvp_stat.format(g=g) + ' avg'
        if col in D.columns and prior:
            raw = float(D.loc[r.opp, col]) / prior
            tw = .4 + .6 * trust(r.opp) / 100
            m = 1 + (raw - 1) * W_POS.get(r.position, .1) * tw
            rkc = dvp_stat.format(g=g) + ' rank'
            rk = int(D.loc[r.opp, rkc]) if rkc in D.columns else ''
    proj = base * m
    last10 = h.tail(10).v
    over_rate = float((last10 > r.line).mean()) if len(last10) else np.nan
    edge = (proj - r.line) / r.line if r.line else np.nan
    lean = ''
    # a lean needs 6+ games of history, a line that is not a coin-flip count market (≤1.5), a 10% projection gap and last-10 agreement
    if pd.notna(edge) and pd.notna(over_rate) and len(last10) >= 6 and r.line > 1.5:
        if edge >= .10 and over_rate >= .6: lean = 'OVER'
        elif edge <= -.10 and over_rate <= .4: lean = 'UNDER'
    rows.append(dict(week=week, event=r.event, player=r.full_name, pfr_id=r.pfr_id, team=r.team, pos=r.position, slot=slot, opp=r.opp, kick=r.kick,
                     market=r.market.replace('Total ', ''), line=r.line, open=r.open, move=round(r.line - r.open, 1) if pd.notna(r.open) else np.nan,
                     own_avg=round(own, 1) if pd.notna(own) else np.nan, n_games=len(l26) + len(l25), base=round(base, 1), matchup_x=round(m, 3),
                     proj=round(proj, 1), edge_pct=round(100 * edge, 1) if pd.notna(edge) else np.nan, l10_over=round(over_rate, 2) if pd.notna(over_rate) else np.nan,
                     dvp_rank=rk, lean=lean, stat_cols='+'.join(cols), updated=r.updated))
out = pd.DataFrame(rows).sort_values(['kick', 'event', 'team', 'player', 'market'])
out.to_csv('data/processed/props_current.csv', index=False)
# frozen ledger of leans
LP = 'data/processed/props_ledger.csv'
led = pd.read_csv(LP) if os.path.exists(LP) else pd.DataFrame(columns=['frozen_on', 'result', 'actual'] + list(out.columns))
leans = out[out.lean != '']
key = lambda d: d.week.astype(str) + '|' + d.pfr_id + '|' + d.market
new = leans[~key(leans).isin(key(led) if len(led) else [])].copy()
if len(new): new.insert(0, 'frozen_on', str(datetime.date.today())); new.insert(1, 'result', ''); new.insert(2, 'actual', np.nan); led = pd.concat([led, new], ignore_index=True)
# grade from game logs
for i, r in led.iterrows():
    if isinstance(r.result, str) and r.result: continue
    g = L[(L.player_id == r.pfr_id) & (L.season == 2026) & (L.week == r.week)]
    if len(g):
        act = float(g[r.stat_cols.split('+')].sum(axis=1).iloc[0]); led.at[i, 'actual'] = act
        led.at[i, 'result'] = 'PUSH' if act == r.line else ('W' if (act > r.line) == (r.lean == 'OVER') else 'L')
led.to_csv(LP, index=False)
rec = led.result.value_counts() if len(led) else {}
print(f"props_current.csv: {len(out)} markets from {src} · {out.player.nunique()} players · {len(games)} games listed, "
      f"{out.event.nunique()} with main props posted · leans: {(out.lean=='OVER').sum()} over / {(out.lean=='UNDER').sum()} under")
print(f"props_ledger.csv: {len(led)} frozen leans · record W {rec.get('W',0)} L {rec.get('L',0)} P {rec.get('PUSH',0)} · {len(new)} new this run")
unmatched = P[P.pfr_id.isna()].espn_id.nunique()
if unmatched: print(f"  {unmatched} ESPN athlete ids not in the nflverse roster crosswalk (kickers / practice squad)")
