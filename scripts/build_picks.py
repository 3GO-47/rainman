"""Unified picks ledger -> data/processed/picks_all.csv : every model position in one frozen, graded file.
types: ML (moneyline), ATS (spread), TOTAL, PROP (player line), TD (anytime TD), DFS (mock lineup entry)

Usage: python3 scripts/build_picks.py [--week N]
Inputs : picks_ledger.csv (frozen game picks + model numbers), game_model.csv (scores), bet_ledger.csv (frozen prop leans, graded),
         bet_td.csv (anytime-TD model), kalshi_implied.csv (exchange prices: ML prob, anytime-TD prob, implied lines),
         dfs_summary.csv (mock entries), game_logs (grading)
Rules (all frozen the first time a week is built, graded later, never rewritten):
  ML    model win prob vs the Kalshi mid (fallback: the book's fair prob). Edge >= 6 points of probability -> pick that side.
  ATS / TOTAL  the game model's frozen picks (model vs market >= 3 pts), carried over as-is.
  PROP  bet_ledger leans carried over (prop model vs posted line; side + EV), already graded there.
  TD    model P(anytime TD) vs the Kalshi anytime price: model − market >= .08 and model >= .30 -> YES; market − model >= .12 and
        market >= .35 -> NO. Graded from the box score (rush + rec TD >= 1).
  DFS   one row per slate entry: projected points vs the real DK points once the slate has played.
Each row carries the market reference it was judged against so the record can be audited pick by pick.
"""
import os, sys, glob
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
P = 'data/processed/'
TODAY = str(pd.Timestamp.today().date())
COLS = ['type', 'week', 'frozen_on', 'ref', 'player', 'team', 'opp', 'market', 'side', 'line', 'model', 'market_ref', 'market_src', 'edge', 'result', 'actual', 'note']

def main(week=None):
    gm = pd.read_csv(P + 'game_model.csv'); gm = gm[gm.season == 2026]
    if week is None: week = int(gm[gm.result.isna()].week.min()) if gm.result.isna().any() else int(gm.week.max())
    old = pd.read_csv(P + 'picks_all.csv') if os.path.exists(P + 'picks_all.csv') else pd.DataFrame(columns=COLS)
    keys = set(zip(old.type, old.week, old.ref, old.market, old.side)) if len(old) else set()
    kal = pd.read_csv(P + 'kalshi_implied.csv') if os.path.exists(P + 'kalshi_implied.csv') else pd.DataFrame()
    new = []
    def add(row):
        k = (row['type'], row['week'], row['ref'], row['market'], row['side'])
        if k in keys: return
        keys.add(k); new.append({**{c: '' for c in COLS}, 'frozen_on': TODAY, **row})
    # ---- game picks: ATS / TOTAL from the frozen ledger; ML vs Kalshi ----
    led = pd.read_csv(P + 'picks_ledger.csv')
    for r in led[led.week == week].itertuples():
        gid = r.game_id; g = f'{r.away_team}@{r.home_team}'
        if isinstance(r.pick_ats, str) and r.pick_ats:
            add({'type': 'ATS', 'week': week, 'ref': gid, 'team': g, 'market': 'spread', 'side': r.pick_ats, 'line': r.spread_line, 'model': r.model_spread,
                 'market_ref': r.spread_line, 'market_src': 'DK', 'edge': r.edge_spread, 'note': 'model spread vs market, home perspective'})
        if isinstance(r.pick_total, str) and r.pick_total:
            add({'type': 'TOTAL', 'week': week, 'ref': gid, 'team': g, 'market': 'total', 'side': r.pick_total, 'line': r.total_line, 'model': r.model_total,
                 'market_ref': r.total_line, 'market_src': 'DK', 'edge': r.edge_total})
        # moneyline: model home win prob vs Kalshi mid for the home team (fallback: book fair prob)
        kh = kal[(kal.market == 'moneyline') & (kal.week == week) & (kal.team == r.home_team) & (kal.away == r.away_team)] if len(kal) else pd.DataFrame()
        mkt, src = (float(kh.p_mid.iloc[0]), 'Kalshi') if len(kh) else ((float(r.imp_home_fair), 'DK fair') if r.imp_home_fair == r.imp_home_fair else (None, ''))
        if mkt is not None and r.win_prob_home == r.win_prob_home:
            edge = r.win_prob_home - mkt
            if abs(edge) >= 0.06:
                side = r.home_team if edge > 0 else r.away_team
                add({'type': 'ML', 'week': week, 'ref': gid, 'team': g, 'market': 'moneyline', 'side': side, 'line': '', 'model': round(r.win_prob_home if edge > 0 else 1 - r.win_prob_home, 3),
                     'market_ref': round(mkt if edge > 0 else 1 - mkt, 3), 'market_src': src, 'edge': round(abs(edge), 3), 'note': 'win probability, model vs exchange'})
    # ---- props: carry the frozen leans ----
    bl = pd.read_csv(P + 'bet_ledger.csv') if os.path.exists(P + 'bet_ledger.csv') else pd.DataFrame()
    for r in bl.itertuples():
        add({'type': 'PROP', 'week': int(r.week), 'frozen_on': r.frozen_on, 'ref': f'{r.player}|{r.market}|{r.line}', 'player': r.player, 'team': r.team, 'opp': r.opp, 'market': r.market,
             'side': r.side, 'line': r.line, 'model': r.p_over if r.side == 'Over' else round(1 - r.p_over, 3), 'market_ref': 0.5, 'market_src': r.book, 'edge': r.ev,
             'result': r.result if isinstance(r.result, str) else '', 'actual': r.actual if r.actual == r.actual else '', 'note': 'EV at -110 vs posted line'})
    # ---- anytime TD vs Kalshi ----
    td = pd.read_csv(P + 'bet_td.csv'); td = td[td.week == week]
    if len(kal):
        kt = kal[(kal.market == 'anytime_td') & (kal.week == week)]
        for r in td.itertuples():
            k = kt[(kt.player == r.player) & (kt.team == r.team)]
            if not len(k): continue
            mkt = float(k.p_mid.iloc[0]); pm = float(r.p_model)
            if pm - mkt >= 0.08 and pm >= 0.30: side = 'YES'
            elif mkt - pm >= 0.12 and mkt >= 0.35: side = 'NO'
            else: continue
            add({'type': 'TD', 'week': week, 'ref': f'{r.player}|td', 'player': r.player, 'team': r.team, 'opp': r.opp, 'market': 'anytime_td', 'side': side, 'line': 0.5,
                 'model': round(pm, 3), 'market_ref': round(mkt, 3), 'market_src': 'Kalshi', 'edge': round(abs(pm - mkt), 3), 'note': f'bid {k.p_bid.iloc[0]} ask {k.p_ask.iloc[0]}'})
    # ---- DFS entries ----
    if os.path.exists(P + 'dfs_summary.csv'):
        for r in pd.read_csv(P + 'dfs_summary.csv').itertuples():
            add({'type': 'DFS', 'week': int(r.week), 'frozen_on': r.frozen_on, 'ref': f'dfs|{r.slate}', 'market': 'dk_classic', 'side': r.slate, 'line': r.salary if r.salary == r.salary else '',
                 'model': r.proj_total, 'market_ref': '', 'market_src': 'DK' if r.capped else 'uncapped', 'edge': '', 'note': 'projected DK points; graded = actual DK points'})
    allp = pd.concat([old, pd.DataFrame(new)], ignore_index=True) if new else old.copy()
    # ---- grading ----
    scores = {r.game_id: r for r in gm.itertuples() if r.result == r.result}
    logs = pd.read_csv('data/game_logs/game_logs_2026.csv')
    dcs = sorted(glob.glob(P + 'depth_charts_*.csv')); ln = {}
    if dcs:
        import csv
        for r in csv.DictReader(open(dcs[-1], encoding='utf-8')): ln[(r['player'], r['team'])] = r.get('log_name') or r['player']
    dfs = pd.read_csv(P + 'dfs_summary.csv') if os.path.exists(P + 'dfs_summary.csv') else pd.DataFrame()
    bl_res = {f'{r.player}|{r.market}|{r.line}': (r.result, r.actual) for r in bl.itertuples()} if len(bl) else {}
    for i, r in allp.iterrows():
        if isinstance(r.result, str) and r.result in ('W', 'L', 'P'): continue
        t = r.type
        if t in ('ML', 'ATS', 'TOTAL'):
            g = scores.get(r.ref)
            if not g: continue
            margin = float(g.result)  # home − away
            if t == 'ML':
                winner = g.home_team if margin > 0 else g.away_team if margin < 0 else None
                allp.at[i, 'result'] = 'P' if winner is None else ('W' if winner == r.side else 'L'); allp.at[i, 'actual'] = f'{g.away_score:g}-{g.home_score:g}'
            elif t == 'ATS':
                res = g.res_ats if isinstance(g.res_ats, str) else ''
                if res: allp.at[i, 'result'] = {'PUSH': 'P'}.get(res, res); allp.at[i, 'actual'] = margin
            else:
                res = g.res_total if isinstance(g.res_total, str) else ''
                if res: allp.at[i, 'result'] = {'PUSH': 'P'}.get(res, res); allp.at[i, 'actual'] = g.total
        elif t == 'PROP':
            res, act = bl_res.get(r.ref, ('', ''))
            if isinstance(res, str) and res: allp.at[i, 'result'] = res; allp.at[i, 'actual'] = act
        elif t == 'TD':
            name = ln.get((r.player, r.team), r.player)
            g = logs[(logs.week == r.week) & (logs.team == r.team) & (logs.player == name)]
            played = ((logs.week == r.week) & (logs.team == r.team)).any()
            if len(g) or played:
                scored = int(len(g) and (g.rush_td.iloc[0] + g.rec_td.iloc[0]) >= 1)
                allp.at[i, 'actual'] = scored; allp.at[i, 'result'] = 'W' if (scored == 1) == (r.side == 'YES') else 'L'
        elif t == 'DFS' and len(dfs):
            s = dfs[(dfs.week == r.week) & (dfs.slate == r.side)]
            if len(s) and str(s.actual_total.iloc[0]) not in ('', 'nan'):
                allp.at[i, 'actual'] = s.actual_total.iloc[0]; allp.at[i, 'result'] = 'G'   # graded; DFS has no W/L without a contest cash line
    allp = allp[COLS].sort_values(['week', 'type', 'ref']).reset_index(drop=True)
    allp.to_csv(P + 'picks_all.csv', index=False)
    gr = allp[allp.result.isin(['W', 'L'])]
    rec = {t: f"{(gr[gr.type == t].result == 'W').sum()}-{(gr[gr.type == t].result == 'L').sum()}" for t in ['ML', 'ATS', 'TOTAL', 'PROP', 'TD']}
    print(f'picks_all.csv: {len(allp)} positions ({len(new)} new this run) · wk {week}: ' + ', '.join(f"{t} {int((allp[(allp.week == week) & (allp.type == t)]).shape[0])}" for t in ['ML', 'ATS', 'TOTAL', 'PROP', 'TD', 'DFS']) + f' · record {rec}')

if __name__ == '__main__':
    wk = int(sys.argv[sys.argv.index('--week') + 1]) if '--week' in sys.argv else None
    main(wk)
