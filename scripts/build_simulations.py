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

def params(week=None, out='data/processed/sim_params.json', env_extra=None):
    cmd = [sys.executable, 'scripts/build_sim_params.py', '--out', out] + (['--week', str(week)] if week else [])
    env = dict(os.environ); env.update(env_extra or {})
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode: raise SystemExit(r.stderr[-2000:])
    return json.load(open(out))

def run_week(PR, n, seed=11):
    out = []
    for i, g in enumerate(PR['games']):
        t = time.time(); r = simulate(PR, g, n=n, seed=seed + i); r['secs'] = round(time.time() - t, 1); out.append(r)
        print(f"  {g['away']} @ {g['home']}: {r['mean_away']:.1f}–{r['mean_home']:.1f} · home {r['p_home']:.0%} · likely {r['likely'][0]['away']}-{r['likely'][0]['home']} ({r['likely'][0]['p']:.1%}) · total {r['mean_total']:.1f} vs {g.get('total')} · {r['secs']}s")
    return out

def calibrate(PR, n=2500, rounds=5):
    """League-level calibration: every team plays once in synthetic pairings; the league-average dropback share, yards per play and
    offensive touchdowns are pushed onto the reference (last two seasons' play-by-play) with three scalars stored in the params."""
    ref = PR['league']['ref']; teams = sorted(PR['teams']); cb = dict(pass_logit=0.0, yard_scale=1.0, td_mult=1.0, pass_scale=1.0, rush_scale=1.0, pace_scale=1.0); cb.update(PR.get('calib') or {})
    rounds = max(rounds, 4)
    mk = lambda a, h: dict(game_id=f'cal_{a}_{h}', week=0, date='', time='', away=a, home=h, spread=None, total=None)
    pairs = [mk(a, h) for a, h in zip(teams[:16], teams[16:][::-1])] + [mk(a, h) for a, h in zip(teams[16:], teams[:16][::-1])]
    for it in range(rounds):
        PR['calib'] = cb; acc = dict(plays=0, db=0, yds=0, otd=0, pts=0, k=0, py=0, ry=0)
        for i, g in enumerate(pairs):
            r = simulate(PR, g, n=n, seed=900 + i)
            for b in r['box']:
                ts = b['team_stats']; q = b['qb']
                acc['plays'] += ts['plays'] - ts['fga'] - ts['punts']; acc['db'] += q['att'] + q['sacks'] + q['car']; acc['yds'] += ts['yds']; acc['otd'] += ts['otd']; acc['pts'] += ts['pts']; acc['k'] += 1; acc['py'] += ts['pass_yds']; acc['ry'] += ts['rush_yds']   # scrimmage plays, like the reference (kicks and punts are not plays there)
        k = acc['k']; sim = dict(plays=acc['plays'] / k, db_share=acc['db'] / acc['plays'], ypp=acc['yds'] / acc['plays'], otd=acc['otd'] / k, pts=acc['pts'] / k, py=acc['py'] / k, ry=acc['ry'] / k)
        tgt = dict(db_share=ref['dropbacks'] / ref['plays'], ypp=ref['yds'] / ref['plays'], otd=ref['off_td'], plays=ref['plays'], py=ref['pass_yds'], ry=ref['rush_yds'])
        print(f"  calib round {it + 1}: plays {sim['plays']:.1f} (ref {tgt['plays']}) · dropback share {sim['db_share']:.3f} (ref {tgt['db_share']:.3f}) · pass yds {sim['py']:.0f} (ref {tgt['py']}) · rush yds {sim['ry']:.0f} (ref {tgt['ry']}) · off TD {sim['otd']:.2f} (ref {tgt['otd']:.2f}) · pts {sim['pts']:.1f} (ref {ref['pts']}) · {cb}")
        lg = lambda p: np.log(p / (1 - p))
        # v4: six scalars — the clock sets plays per game, the dropback share sets the pass/run call mix, the pass/rush scales set the
        # yardage split, yards overall are scaled so an average game scores the league's points (the sim moves the chains a little less
        # efficiently than real offenses — no designed plays to the sticks, no penalties beyond the league rate — so its yards run ~5% high),
        # and the touchdown scalar keeps the TD / field-goal mix on the reference
        r_ref = tgt['py'] / (tgt['py'] + tgt['ry']); r_sim = sim['py'] / (sim['py'] + sim['ry'])
        cb = dict(pass_logit=round(float(cb['pass_logit'] + (lg(tgt['db_share']) - lg(sim['db_share']))), 4), yard_scale=round(cb['yard_scale'] * (ref['pts'] / sim['pts']) ** .9, 4), td_mult=round(cb['td_mult'] * (tgt['otd'] / sim['otd']) ** .8, 4),
                  pass_scale=round(cb['pass_scale'] * (r_ref / r_sim) ** .8, 4), rush_scale=round(cb['rush_scale'] * ((1 - r_ref) / (1 - r_sim)) ** .8, 4), pace_scale=round(cb['pace_scale'] * (sim['plays'] / tgt['plays']) ** .8, 4))
    PR['calib'] = cb; return cb

def grade_players(pdir, weeks):
    """the sim's player means / bands against what the men actually did (data/game_logs): MAE, bias, correlation and band coverage by position"""
    import pandas as pd, glob, re
    P = []
    for w in weeks:
        f = f'{pdir}/p{w}.json'
        if os.path.exists(f): P += json.load(open(f))
    if not P: return None
    G = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_2026.csv'))], ignore_index=True)
    norm = lambda x: re.sub(r'[^a-z]', '', str(x).lower().replace(' jr', '').replace(' sr', '').replace(' iii', '').replace(' ii', ''))
    G['n'] = G.player.map(norm); G['team'] = G.team.replace({'LA': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX'})
    key = {(int(r.week), r.team, r.n): r for r in G.itertuples()}
    out = {}; rows = []
    for p in P:
        a = key.get((p['week'], p['team'], norm(p['name'])))
        act = float(a.fantasy_pts_ppr) if a is not None else 0.0   # not in the logs = did not record a stat (or did not play): 0 points
        rows.append(dict(pos=p['pos'] if p['pos'] in ('QB', 'RB', 'WR', 'TE') else 'WR', mean=p['mean'], act=act, p10=p['p10'], p90=p['p90'], p25=p['p25'], p75=p['p75'], sd=p['sd'], played=a is not None, tgt=p.get('tgt') or 0, car=p.get('car') or 0))
    def blk(S):
        if len(S) < 5: return None
        m = np.array([x['mean'] for x in S]); a = np.array([x['act'] for x in S])
        return dict(n=len(S), mae=round(float(np.abs(m - a).mean()), 2), bias=round(float((m - a).mean()), 2), r=round(float(np.corrcoef(m, a)[0, 1]), 3),
                    cov80=round(float(np.mean([x['p10'] <= x['act'] <= x['p90'] for x in S])), 3), cov50=round(float(np.mean([x['p25'] <= x['act'] <= x['p75'] for x in S])), 3),
                    z_sd=round(float(np.std([(x['act'] - x['mean']) / max(x['sd'], .5) for x in S])), 3), mean_sim=round(float(m.mean()), 2), mean_act=round(float(a.mean()), 2))
    for pos in ('QB', 'RB', 'WR', 'TE'): out[pos] = blk([x for x in rows if x['pos'] == pos])
    out['ALL'] = blk(rows); out['starters'] = blk([x for x in rows if x['mean'] >= 8])
    return out

def backtest(n, only=None):
    """only = list of weeks to (re)run; each week's rows are cached in data/processed/sim_bt_parts/w{W}.json so the run can be split"""
    import pandas as pd
    g = pd.read_csv('data/raw/nflverse/games.csv'); cur = g[(g.season == 2026) & (g.game_type == 'REG') & g.home_score.notna()]
    # the backtest never sees today's injury report (it has no history) — def_inj is forced off; a config grid gets its own parts folder
    cfg = json.loads(os.environ.get('SIM_CFG', '{}')); cfg['def_inj'] = 0; tag = '' if not os.environ.get('SIM_CFG') else '_' + '_'.join(f'{k}{v}' for k, v in sorted(cfg.items()))
    pdir = f'data/processed/sim_bt_parts{tag}'; weeks = sorted(int(w) for w in cur.week.unique()); rows = []; os.makedirs(pdir, exist_ok=True)
    for w in weeks:
        part = f'{pdir}/w{w}.json'
        # a cached week is reused only while it still covers every finished game of that week (a Thursday-only part must not stand for the whole week)
        cached = json.load(open(part)) if os.path.exists(part) else None
        if cached is not None and len(cached) < int((cur.week == w).sum()): cached = None
        if (only and w not in only) or (not only and cached is not None):
            if cached is not None: rows += cached
            continue
        wrows = []; prows = []
        PR = params(w, out=f'data/processed/_sim_params_bt{tag}.json', env_extra={'SIM_CFG': json.dumps(cfg)})
        played = [x for x in PR['games'] if x.get('home_score') is not None]
        if not played: continue
        calibrate(PR, n=1500, rounds=2)
        print(f'week {w}: {len(played)} games (pbp through wk {w - 1}, depth chart {next(iter(PR["players"].values()))["depth_chart"]})')
        for i, gm in enumerate(played):
            r = simulate(PR, gm, n=n, seed=100 * w + i)
            am, hm = gm['away_score'], gm['home_score']; margin = hm - am; total = am + hm
            for b in r['box']:
                for p in [b['qb']] + b['players']:
                    f = (p.get('fan') or {}).get('ppr')
                    if not f or (p.get('pos') != 'QB' and p.get('tgt', 0) + (p.get('car') or 0) < 1.0): continue
                    prows.append(dict(week=w, game=f"{gm['away']}@{gm['home']}", team=b['team'], name=p['name'], pos=p.get('pos', ''), slot=p.get('slot', ''), mean=f['mean'], sd=f['sd'], p10=f['p10'], p25=f['p25'], p50=f['p50'], p75=f['p75'], p90=f['p90'],
                                      tgt=p.get('tgt'), rec=p.get('rec'), rec_yds=p.get('rec_yds'), car=p.get('car'), rush_yds=p.get('rush_yds'), pass_yds=p.get('pass_yds')))
            wrows.append(dict(week=w, game=f"{gm['away']}@{gm['home']}", away=gm['away'], home=gm['home'], actual_away=am, actual_home=hm,
                             sim_away=round(r['mean_away'], 1), sim_home=round(r['mean_home'], 1), sim_margin=round(r['mean_margin'], 1), sim_total=round(r['mean_total'], 1), p_home=round(r['p_home'], 3),
                             likely=f"{r['headline']['away']}-{r['headline']['home']}", spread=gm.get('spread'), total_line=gm.get('total'), margin=margin, total=total,
                             err_margin=round(abs(r['mean_margin'] - margin), 1), err_total=round(abs(r['mean_total'] - total), 1),
                             mkt_err_margin=None if gm.get('spread') is None else round(abs(gm['spread'] - margin), 1), mkt_err_total=None if gm.get('total') is None else round(abs(gm['total'] - total), 1),
                             sd_margin=round(r['sd_margin'], 1), sd_total=round(r['sd_total'], 1), m10=r['margin_q']['p10'], m90=r['margin_q']['p90'], t10=r['total_q']['p10'], t90=r['total_q']['p90'], m25=r['margin_q']['p25'], m75=r['margin_q']['p75'], t25=r['total_q']['p25'], t75=r['total_q']['p75'],
                             p_over=r.get('p_over'), p_home_cover=r.get('p_home_cover'), p_one_score=r.get('p_one_score'), one_score=int(abs(margin) <= 8),
                             su=int((r['p_home'] > .5) == (margin > 0)) if margin != 0 else None,
                             ats=None if gm.get('spread') is None or margin == gm['spread'] else int((r['mean_margin'] > gm['spread']) == (margin > gm['spread'])),
                             ou=None if gm.get('total') is None or total == gm['total'] else int((r['mean_total'] > gm['total']) == (total > gm['total']))))
        json.dump(_clean(wrows), open(part, 'w')); rows += wrows; json.dump(_clean(prows), open(f'{pdir}/p{w}.json', 'w'))
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
        d = dict(games=len(S), mae_margin=mm('err_margin'), mkt_mae_margin=mm('mkt_err_margin'), mae_total=mm('err_total'), mkt_mae_total=mm('mkt_err_total'), su=mm('su'), ats=mm('ats'), ou=mm('ou'))
        # spread of outcomes: did the actual land inside the sim's 10–90 and 25–75 bands (80% / 50% if the sim's variance is right)? and the z-score sd (1.0 if right)
        H = [x for x in S if x.get('m10') is not None]
        if H:
            d['cov80_margin'] = round(float(np.mean([x['m10'] <= x['margin'] <= x['m90'] for x in H])), 3); d['cov50_margin'] = round(float(np.mean([x['m25'] <= x['margin'] <= x['m75'] for x in H])), 3)
            d['cov80_total'] = round(float(np.mean([x['t10'] <= x['total'] <= x['t90'] for x in H])), 3); d['cov50_total'] = round(float(np.mean([x['t25'] <= x['total'] <= x['t75'] for x in H])), 3)
            d['z_sd_margin'] = round(float(np.std([(x['margin'] - x['sim_margin']) / x['sd_margin'] for x in H])), 3); d['z_sd_total'] = round(float(np.std([(x['total'] - x['sim_total']) / x['sd_total'] for x in H])), 3)
            d['one_score_sim'] = round(float(np.mean([x['p_one_score'] for x in H])), 3); d['one_score_act'] = round(float(np.mean([x['one_score'] for x in H])), 3)
            ms = [x for x in H if x['margin'] != 0]
            d['r_margin'] = round(float(np.corrcoef([x['sim_margin'] for x in ms], [x['margin'] for x in ms])[0, 1]), 3) if len(ms) > 3 else None
            d['r_total'] = round(float(np.corrcoef([x['sim_total'] for x in H], [x['total'] for x in H])[0, 1]), 3) if len(H) > 3 else None
            mk = [x for x in H if x.get('spread') is not None]
            d['r_margin_mkt'] = round(float(np.corrcoef([x['spread'] for x in mk], [x['margin'] for x in mk])[0, 1]), 3) if len(mk) > 3 else None
            tk = [x for x in H if x.get('total_line') is not None]
            d['r_total_mkt'] = round(float(np.corrcoef([x['total_line'] for x in tk], [x['total'] for x in tk])[0, 1]), 3) if len(tk) > 3 else None
        return d
    by_week = {int(w): block([x for x in R if x['week'] == w]) for w in weeks}
    settled = block([x for x in R if x['week'] >= 4])   # once the season's own games carry real weight in the coordinator profiles
    players = grade_players(pdir, [w for w in weeks if w >= 4])
    summ = dict(games=len(R), weeks=weeks, n=n, by_week=by_week, settled=settled, players=players, mae_margin=m('err_margin'), mae_total=m('err_total'), mkt_mae_margin=m('mkt_err_margin'), mkt_mae_total=m('mkt_err_total'),
                su=m('su'), ats=m('ats'), ou=m('ou'), bias_margin=round(float(np.mean([x['sim_margin'] - x['margin'] for x in R])), 2), bias_total=round(float(np.mean([x['sim_total'] - x['total'] for x in R])), 2),
                calibration=cal)
    print(json.dumps({k: v for k, v in summ.items() if k not in ('calibration', 'by_week')}))
    if os.environ.get('SIM_CFG'): print('GRID', os.environ['SIM_CFG'], json.dumps(summ['settled'])); return dict(summary=summ, rows=R, grid=True)
    return dict(summary=summ, rows=R)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=10000); ap.add_argument('--week', type=int); ap.add_argument('--backtest', action='store_true'); ap.add_argument('--bt-n', type=int, default=4000); ap.add_argument('--no-calib', action='store_true'); ap.add_argument('--bt-weeks', help='e.g. 1-3 or 4,5'); a = ap.parse_args()
    if a.backtest:
        only = None
        if a.bt_weeks: only = [w for part in a.bt_weeks.split(',') for w in (range(int(part.split('-')[0]), int(part.split('-')[-1]) + 1))]
        bt = backtest(a.bt_n, only); bt['built'] = time.strftime('%Y-%m-%d %H:%M')
        if not bt.get('grid'): json.dump(_clean(bt), open('data/processed/sim_backtest.json', 'w'), separators=(',', ':'))
        return
    PR = params(a.week)
    if not a.no_calib:
        cb = calibrate(PR); json.dump(_clean(PR), open('data/processed/sim_params.json', 'w'), separators=(',', ':')); print('  calibration', cb)
    print(f"week {PR['week']} · {len(PR['games'])} games · {a.n:,} sims each · pbp through {PR['pbp_through']}")
    res = run_week(PR, a.n)
    json.dump(_clean(dict(built=time.strftime('%Y-%m-%d %H:%M'), season=PR['season'], week=PR['week'], n=a.n, pbp_through=PR['pbp_through'], calib=PR.get('calib'), games=res)), open('data/processed/sim_games.json', 'w'), separators=(',', ':'))
    print('data/processed/sim_games.json written')

if __name__ == '__main__':
    main()
