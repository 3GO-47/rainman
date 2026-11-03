"""Run the game simulator for the week and backtest it on the weeks already played.

  python3 scripts/build_simulations.py                 the coming week × N sims (default 10,000) → data/processed/sim_games.json
  python3 scripts/build_simulations.py --backtest      every 2026 week already played, parameters rebuilt as of that week
                                                       (only earlier weeks' play-by-play, usage and depth charts) → sim_backtest.json
Backtest grades the simulation's mean margin / total against the actual result and against the market's closing line, straight-up
and against the spread, and reports calibration (how often the favourite the sim gave p% actually won).
"""
import os, sys, json, argparse, subprocess, time
import numpy as np

def _clean(o):
    """JSON for the browser: NaN/inf → null, numpy scalars → Python"""
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if (o != o or o in (float('inf'), float('-inf'))) else float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.bool_): return bool(o)
    return o
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, 'scripts')
from sim_engine import simulate

def params(week=None, out='data/processed/sim_params.json'):
    cmd = [sys.executable, 'scripts/build_sim_params.py', '--out', out] + (['--week', str(week)] if week else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr[-2000:])
    return json.load(open(out))

def run_week(PR, n, seed=11):
    out = []
    for i, g in enumerate(PR['games']):
        t = time.time(); r = simulate(PR, g, n=n, seed=seed + i); r['secs'] = round(time.time() - t, 1); out.append(r)
        print(f"  {g['away']} @ {g['home']}: {r['mean_away']:.1f}–{r['mean_home']:.1f} · home {r['p_home']:.0%} · likely {r['likely'][0]['away']}-{r['likely'][0]['home']} ({r['likely'][0]['p']:.1%}) · total {r['mean_total']:.1f} vs {g.get('total')} · {r['secs']}s")
    return out

def calibrate(PR, n=2500, rounds=3):
    """League-level calibration: every team plays once in synthetic pairings; the league-average dropback share, yards per play and
    offensive touchdowns are pushed onto the reference (last two seasons' play-by-play) with three scalars stored in the params."""
    ref = PR['league']['ref']; teams = sorted(PR['teams']); cb = dict(PR.get('calib') or dict(pass_logit=0.0, yard_scale=1.0, td_mult=1.0))
    mk = lambda a, h: dict(game_id=f'cal_{a}_{h}', week=0, date='', time='', away=a, home=h, spread=None, total=None)
    pairs = [mk(a, h) for a, h in zip(teams[:16], teams[16:][::-1])] + [mk(a, h) for a, h in zip(teams[16:], teams[:16][::-1])]
    for it in range(rounds):
        PR['calib'] = cb; acc = dict(plays=0, db=0, yds=0, otd=0, pts=0, k=0)
        for i, g in enumerate(pairs):
            r = simulate(PR, g, n=n, seed=900 + i)
            for b in r['box']:
                ts = b['team_stats']; q = b['qb']
                acc['plays'] += ts['plays']; acc['db'] += q['att'] + q['sacks'] + q['car']; acc['yds'] += ts['yds']; acc['otd'] += ts['otd']; acc['pts'] += ts['pts']; acc['k'] += 1
        k = acc['k']; sim = dict(plays=acc['plays'] / k, db_share=acc['db'] / acc['plays'], ypp=acc['yds'] / acc['plays'], otd=acc['otd'] / k, pts=acc['pts'] / k)
        tgt = dict(db_share=ref['dropbacks'] / ref['plays'], ypp=ref['yds'] / ref['plays'], otd=ref['off_td'])
        print(f"  calib round {it + 1}: plays {sim['plays']:.1f} · dropback share {sim['db_share']:.3f} (ref {tgt['db_share']:.3f}) · yds/play {sim['ypp']:.2f} (ref {tgt['ypp']:.2f}) · off TD {sim['otd']:.2f} (ref {tgt['otd']:.2f}) · pts {sim['pts']:.1f} (ref {ref['pts']}) · {cb}")
        lg = lambda p: np.log(p / (1 - p))
        cb = dict(pass_logit=round(float(cb['pass_logit'] + (lg(tgt['db_share']) - lg(sim['db_share']))), 4), yard_scale=round(cb['yard_scale'] * (tgt['ypp'] / sim['ypp']) ** .8, 4), td_mult=round(cb['td_mult'] * (tgt['otd'] / sim['otd']) ** .8, 4))
    PR['calib'] = cb; return cb

def backtest(n, only=None):
    """only = list of weeks to (re)run; each week's rows are cached in data/processed/sim_bt_parts/w{W}.json so the run can be split"""
    import pandas as pd
    g = pd.read_csv('data/raw/nflverse/games.csv'); cur = g[(g.season == 2026) & (g.game_type == 'REG') & g.home_score.notna()]
    weeks = sorted(int(w) for w in cur.week.unique()); rows = []; os.makedirs('data/processed/sim_bt_parts', exist_ok=True)
    for w in weeks:
        part = f'data/processed/sim_bt_parts/w{w}.json'
        if (only and w not in only) or (not only and os.path.exists(part)):
            if os.path.exists(part): rows += json.load(open(part))
            continue
        wrows = []
        PR = params(w, out='data/processed/_sim_params_bt.json')
        played = [x for x in PR['games'] if x.get('home_score') is not None]
        if not played: continue
        calibrate(PR, n=1500, rounds=2)
        print(f'week {w}: {len(played)} games (pbp through wk {w - 1}, depth chart {next(iter(PR["players"].values()))["depth_chart"]})')
        for i, gm in enumerate(played):
            r = simulate(PR, gm, n=n, seed=100 * w + i)
            am, hm = gm['away_score'], gm['home_score']; margin = hm - am; total = am + hm
            wrows.append(dict(week=w, game=f"{gm['away']}@{gm['home']}", away=gm['away'], home=gm['home'], actual_away=am, actual_home=hm,
                             sim_away=round(r['mean_away'], 1), sim_home=round(r['mean_home'], 1), sim_margin=round(r['mean_margin'], 1), sim_total=round(r['mean_total'], 1), p_home=round(r['p_home'], 3),
                             likely=f"{r['headline']['away']}-{r['headline']['home']}", spread=gm.get('spread'), total_line=gm.get('total'), margin=margin, total=total,
                             err_margin=round(abs(r['mean_margin'] - margin), 1), err_total=round(abs(r['mean_total'] - total), 1),
                             mkt_err_margin=None if gm.get('spread') is None else round(abs(gm['spread'] - margin), 1), mkt_err_total=None if gm.get('total') is None else round(abs(gm['total'] - total), 1),
                             su=int((r['p_home'] > .5) == (margin > 0)) if margin != 0 else None,
                             ats=None if gm.get('spread') is None or margin == gm['spread'] else int((r['mean_margin'] > gm['spread']) == (margin > gm['spread'])),
                             ou=None if gm.get('total') is None or total == gm['total'] else int((r['mean_total'] > gm['total']) == (total > gm['total']))))
        json.dump(_clean(wrows), open(part, 'w')); rows += wrows
    rows.sort(key=lambda x: (x['week'], x['game']))
    R = rows; m = lambda k: round(float(np.mean([x[k] for x in R if x[k] is not None])), 2) if any(x[k] is not None for x in R) else None
    # calibration: favourite's win probability bucket vs actual
    cal = {}
    for x in R:
        if x['su'] is None: continue
        p = max(x['p_home'], 1 - x['p_home']); b = f'{int(p * 10) * 10}-{int(p * 10) * 10 + 9}'
        c = cal.setdefault(b, dict(n=0, won=0, p=0.0)); c['n'] += 1; c['won'] += x['su']; c['p'] += p
    cal = {k: dict(n=v['n'], won=v['won'], hit=round(v['won'] / v['n'], 3), mean_p=round(v['p'] / v['n'], 3)) for k, v in sorted(cal.items())}
    def block(S):
        mm = lambda k: round(float(np.mean([x[k] for x in S if x[k] is not None])), 2) if any(x[k] is not None for x in S) else None
        return dict(games=len(S), mae_margin=mm('err_margin'), mkt_mae_margin=mm('mkt_err_margin'), mae_total=mm('err_total'), mkt_mae_total=mm('mkt_err_total'), su=mm('su'), ats=mm('ats'), ou=mm('ou'))
    by_week = {int(w): block([x for x in R if x['week'] == w]) for w in weeks}
    settled = block([x for x in R if x['week'] >= 4])   # once the season's own games carry real weight in the coordinator profiles
    summ = dict(games=len(R), weeks=weeks, n=n, by_week=by_week, settled=settled, mae_margin=m('err_margin'), mae_total=m('err_total'), mkt_mae_margin=m('mkt_err_margin'), mkt_mae_total=m('mkt_err_total'),
                su=m('su'), ats=m('ats'), ou=m('ou'), bias_margin=round(float(np.mean([x['sim_margin'] - x['margin'] for x in R])), 2), bias_total=round(float(np.mean([x['sim_total'] - x['total'] for x in R])), 2),
                calibration=cal)
    print(json.dumps(summ, indent=1))
    return dict(summary=summ, rows=R)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=10000); ap.add_argument('--week', type=int); ap.add_argument('--backtest', action='store_true'); ap.add_argument('--bt-n', type=int, default=4000); ap.add_argument('--no-calib', action='store_true'); ap.add_argument('--bt-weeks', help='e.g. 1-3 or 4,5'); a = ap.parse_args()
    if a.backtest:
        only = None
        if a.bt_weeks: only = [w for part in a.bt_weeks.split(',') for w in (range(int(part.split('-')[0]), int(part.split('-')[-1]) + 1))]
        bt = backtest(a.bt_n, only); bt['built'] = time.strftime('%Y-%m-%d %H:%M'); json.dump(_clean(bt), open('data/processed/sim_backtest.json', 'w'), separators=(',', ':')); return
    PR = params(a.week)
    if not a.no_calib:
        cb = calibrate(PR); json.dump(_clean(PR), open('data/processed/sim_params.json', 'w'), separators=(',', ':')); print('  calibration', cb)
    print(f"week {PR['week']} · {len(PR['games'])} games · {a.n:,} sims each · pbp through {PR['pbp_through']}")
    res = run_week(PR, a.n)
    json.dump(_clean(dict(built=time.strftime('%Y-%m-%d %H:%M'), season=PR['season'], week=PR['week'], n=a.n, pbp_through=PR['pbp_through'], calib=PR.get('calib'), games=res)), open('data/processed/sim_games.json', 'w'), separators=(',', ':'))
    print('data/processed/sim_games.json written')

if __name__ == '__main__':
    main()
