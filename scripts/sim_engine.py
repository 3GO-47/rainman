"""RAINMAN game simulator — a play-by-play Monte Carlo of one NFL game, vectorised over N simulations.

Every number it draws comes from data/processed/sim_params.json (scripts/build_sim_params.py): league play-calling and yardage
tables from the nflverse play-by-play, each coordinator's tendencies (pass rate over expected, pace, red-zone calls, 4th-down
nerve, EPA passing / rushing, explosive rate, pressure, coverage family), and this week's depth chart with each man's target
and carry share, catch rate, yards per target / carry and red-zone role. Nothing is hand-set except the small clock rules
noted inline (kneel-downs, overtime).

How a snap goes: the situation (down, distance, zone, score, clock) sets the league dropback probability → the offensive
coordinator shifts it by his pass rate over expected (red-zone calls use his red-zone pass rate) → a dropback is a sack,
a scramble or a throw; a throw picks a target by share × what the defense's coverage family concedes to that slot, is
completed at the league rate for the spot shifted by the QB, the defense and the receiver, or picked off at the matchup's
rate → yards come from the league quantiles for the spot, scaled by offense EPA vs defense EPA allowed and the player's
own efficiency, with explosive plays drawn at the matchup's explosive rate → clock, downs, first downs, fumbles, 4th-down
decisions (league go rate × the coach's aggressiveness), field goals by distance, punts, kickoffs, halftime, two-point
tries when the score calls for one, kneel-downs, overtime.
The JavaScript engine in the Simulations page (scripts/sim_engine.js) is the same model, snap for snap, so a visitor's
own run matches the pre-run numbers up to Monte Carlo noise.
"""
import numpy as np

ZONES = ['own', 'mid', 'plus', 'rz']; TGS = ['s', 'm', 'l', 'x']; SDS = ['T2', 'T1', 'E', 'L1', 'L2']; TS = ['H1', 'H1late', 'H2', 'late']
GRP = {'QB1': 'QB', 'QB2': 'QB', 'RB1': 'RB1', 'RB2': 'RB2', 'RB3': 'RB2', 'TE1': 'TE1', 'TE2': 'TE2', 'TE3': 'TE2', 'TE4': 'TE2', 'WR1': 'WR1', 'WR2': 'WR2', 'WR3': 'WR3', 'WR4+': 'WR4+'}
def _tail(L): return int(round(100 - 100 * L['explosive_pass'])), int(round(100 - 100 * L['explosive_rush']))   # quantile index where the explosive tail starts: completions of 20+, rushes of 12+

def _tables(L):
    PP = np.zeros((5, 4, 4, 5, 4))
    for d in range(1, 5):
        for a, tg in enumerate(TGS):
            for b, z in enumerate(ZONES):
                for c, sd in enumerate(SDS):
                    for e, t in enumerate(TS):
                        PP[d, a, b, c, e] = L['pass_prob'].get(f'{d}|{tg}|{z}|{sd}|{t}', L['pass_by_down'][str(d)] if str(d) in L['pass_by_down'] else L['pass_by_down'].get(d, L['pass_rate']))
    Y = np.zeros((2, 4, 2, 101))
    for i, k in enumerate(('pass', 'rush')):
        for b, z in enumerate(ZONES):
            for dn, nm in enumerate(('early', 'late')): Y[i, b, dn] = L['yards'][f'{k}|{z}|{nm}']
    C = np.array([[L['comp'][f'{z}|{nm}'] for nm in ('early', 'late')] for z in ZONES])
    F4 = np.array([[L['fourth_go'].get(f'{tg}|{z}', .05) for z in ZONES] for tg in TGS])
    return PP, Y, C, F4, np.array(L['yards']['scramble']), np.array(L['yards']['sack']), np.array(L['punt_net']), np.array(L['ko_start'])

def _rzb(yl): return np.where(yl <= 3, 0, np.where(yl <= 6, 1, np.where(yl <= 10, 2, np.where(yl <= 15, 3, 4))))
def _zone(yl): return np.where(yl <= 20, 3, np.where(yl <= 49, 2, np.where(yl <= 79, 1, 0)))
def _tg(t): return np.where(t <= 2, 0, np.where(t <= 6, 1, np.where(t <= 10, 2, 3)))
def _sd(d): return np.where(d <= -9, 0, np.where(d < 0, 1, np.where(d == 0, 2, np.where(d <= 8, 3, 4))))
def _t(s): return np.where(s > 2100, 0, np.where(s > 1800, 1, np.where(s > 300, 2, 3)))
def _fg(L, dist):
    p = np.full(dist.shape, L['fg']['60+'], float)
    for lo, hi, k in ((0, 30, '<30'), (30, 40, '30-39'), (40, 50, '40-49'), (50, 55, '50-54'), (55, 60, '55-59')): p[(dist >= lo) & (dist < hi)] = L['fg'][k]
    return p

def _logit(p): p = np.clip(p, 1e-4, 1 - 1e-4); return np.log(p / (1 - p))
def _sig(x): return 1 / (1 + np.exp(-x))

class Team:
    """one side's parameters, resolved against the opponent"""
    def __init__(self, PR, team, opp, home):
        L = PR['league']; T = PR['teams'][team]; D = PR['teams'][opp]['de']; O = T['off']; self.name = team; self.home = home
        g = lambda d, k, dflt: dflt if d.get(k) is None else d[k]
        lgp, lgr = L['pass_epa'], L['rush_epa']
        self.pass_shift = _logit(np.clip(L['pass_rate'] + g(O, 'proe', 0) / 100, .3, .8)) - _logit(L['pass_rate'])
        self.rz_pass = g(O, 'rz_pass_rate', .55)
        # EPA/play is points per play vs average: a +0.14 passing offense is worth ~+8 points over a game, which is a lot more than 9% of its yards
        cfg = PR.get('cfg') or {}; KP, KR = cfg.get('kp', 1.0), cfg.get('kr', 1.1)
        self.mp = float(np.clip(1 + KP * (g(O, 'pass_epa', lgp) - lgp) + KP * (g(D, 'pass_epa_allowed', lgp) - lgp), .6, 1.5))
        self.mr = float(np.clip(1 + KR * (g(O, 'rush_epa', lgr) - lgr) + KR * (g(D, 'rush_epa_allowed', lgr) - lgr), .6, 1.5))
        edge = L['home_edge']
        if cfg.get('home_team') and L.get('home_edges'): edge = L['home_edges'].get(team if home else opp, edge)   # that stadium's own edge, shrunk toward the league
        home_mult = 1 + (edge / 2) * .013 * (1 if home else -1)   # ≈ the home edge in points, split across both offenses (calibrated: 1% of yards ≈ 0.75 pts)
        self.mp *= home_mult; self.mr *= home_mult
        self.def_comp = g(D, 'pbp_comp', L['comp_rate']); self.def_int = g(D, 'pbp_int_rate', L['int_rate']); self.def_sack = g(D, 'pbp_sack_rate', L['sack_rate'])
        self.exp_pass = L['explosive_pass'] * (g(O, 'pbp_expl_pass', L['explosive_pass']) / L['explosive_pass']) ** .6 * (g(D, 'pbp_expl_pass', L['explosive_pass']) / L['explosive_pass']) ** .6
        self.exp_rush = L['explosive_rush'] * (g(O, 'pbp_expl_rush', L['explosive_rush']) / L['explosive_rush']) ** .6 * (g(D, 'pbp_expl_rush', L['explosive_rush']) / L['explosive_rush']) ** .6
        self.pace = g(O, "pace_factor", 1.0); self.aggr = g(O, "fourth_aggr", 1.0) ** .5
        rzl = np.mean([v['rz']['off_td_rate'] for v in PR['teams'].values() if v['rz'].get('off_td_rate') is not None] or [.58])
        shr = lambda rz, k, nk: (g(rz, k, rzl) * g(rz, nk, 0) + rzl * 30) / (g(rz, nk, 0) + 30)   # red-zone rates shrunk toward league with 30 trips of prior
        self.rzf = float(np.clip(((shr(T['rz'], 'off_td_rate', 'off_trips') / rzl) ** .5) * ((shr(PR['teams'][opp]['rz'], 'def_td_rate', 'def_trips') / rzl) ** .5), .85, 1.18))
        slot_idx = D.get('slot_idx') or {}
        P = PR['players'][team]['players']; pm = L['pos_means']
        qbs = [p for p in P if p['pos'] == 'QB']; self.qb = qbs[0] if qbs else dict(name='QB', comp=L['comp_rate'], ypa=pm['QB']['ypa'], int_rate=L['int_rate'], sack_rate=L['sack_rate'], scramble=L['scramble_rate'], ypc=4.5)
        q = self.qb
        self.comp_shift = .8 * (q.get('comp', L['comp_rate']) - L['comp_rate']) + .7 * (self.def_comp - L['comp_rate'])
        self.int_rate = float(np.clip(L['int_rate'] * (q.get('int_rate', L['int_rate']) / L['int_rate']) ** .6 * (self.def_int / L['int_rate']) ** .6, .005, .06))
        self.sack_rate = float(np.clip(L['sack_rate'] * (q.get('sack_rate', L['sack_rate']) / L['sack_rate']) ** .7 * (self.def_sack / L['sack_rate']) ** .7, .02, .14))
        self.scramble = q.get('scramble', L['scramble_rate'])
        self.mp *= float(np.clip(q.get('ypa', pm['QB']['ypa']) / pm['QB']['ypa'], .8, 1.2)) ** .5
        # receivers: share × what the coverage family concedes to the slot
        R = [p for p in P if p['pos'] != 'QB' and p['tgt_w'] > 0]
        w = np.array([p['tgt_w'] * slot_idx.get(GRP.get(p['slot'], 'WR4+'), 1.0) for p in R]); w = w / w.sum() if w.sum() else w
        rz = np.array([p['rz_share'] if p.get('rz_share') is not None else w[i] for i, p in enumerate(R)]); rz = rz / rz.sum() if rz.sum() else w
        self.R = R; self.tw = np.cumsum(w); self.tw_rz = np.cumsum(.5 * w + .5 * rz)
        self.catch_adj = np.array([.8 * (p['catch'] - pm[p['pos']]['catch']) for p in R]); self.ypt_r = np.array([np.clip(p['ypt'] / pm[p['pos']]['ypt'], .7, 1.4) ** .5 for p in R])
        # man / zone: the defense's man rate against what each receiver, and the offense as a whole, has done against man vs zone
        MZ = L.get('mz') or {}
        if cfg.get('mz') and MZ:
            m = D.get('man_rate'); m = MZ.get('man_share', .4) if m is None else float(m)
            rr = np.array([(lambda z: np.clip(m * z['man'] + (1 - m) * z['zone'], .8, 1.25) ** .7 if z else 1.0)(MZ['receivers'].get(p.get('gsis') or '')) for p in R]); self.ypt_r = self.ypt_r * rr
            oz = MZ['offenses'].get(f"{max(MZ['seasons'])}|{O.get('oc_prior_unit') or team}") or MZ['offenses'].get(f"{max(MZ['seasons'])}|{team}")
            if oz: self.mp *= float(np.clip(1 + KP * (m * oz['man'] + (1 - m) * oz['zone']), .9, 1.1))
            self.man_rate = m
        # rushers: share (QB designed runs included), goal-line share from red-zone data
        # a QB's carry share in the usage file counts his scrambles; the sim draws scrambles on dropbacks, so only designed runs stay here
        U = [p for p in P if p['rush_w'] > 0]
        rw = np.array([p['rush_w'] for p in U])
        for i, p in enumerate(U):
            if p['pos'] == 'QB': rw[i] = max(0.0, rw[i] - self.scramble * 36 / 26)   # ≈ 36 dropbacks and 26 rushes a game
        rw = rw / rw.sum()
        gl = np.array([p.get('gl_rush') or 0 for p in U], float); gl = (gl / gl.sum()) if gl.sum() else rw
        self.U = U; self.rw = np.cumsum(rw); self.rw_gl = np.cumsum(.5 * rw + .5 * gl)
        self.ypc_r = np.array([np.clip(p['ypc'] / pm[p['pos']]['ypc'], .75, 1.3) ** .5 for p in U])
        self.qb_ypc = float(np.clip(q.get('ypc', 4.5) / 4.5, .7, 1.4)) ** .5

def simulate(PR, game, n=10000, seed=7):
    L = PR['league']; rng = np.random.default_rng(seed)
    PP, Y, C, F4, YSCR, YSACK, PUNT, KO = _tables(L); TAILP, TAILR = _tail(L); RZP, RZR = np.array(L['rz_td']['pass']), np.array(L['rz_td']['rush'])
    PACE2 = None
    if (PR.get('cfg') or {}).get('pace2') and L.get('snap_gap_state'):
        PACE2 = np.array([[L['snap_gap_state'].get(f'{s}|{h}', L['snap_gap']['run_or_complete']) for h in (0, 1)] for s in ('T2', 'T1', 'E', 'L1', 'L2')])
    CB = PR.get('calib') or {}; c_pass, c_yard, c_td = CB.get('pass_logit', 0.0), CB.get('yard_scale', 1.0), CB.get('td_mult', 1.0)   # league-level calibration (build_simulations.py --calibrate)
    A, H = game['away'], game['home']; TM = [Team(PR, A, H, False), Team(PR, H, A, True)]
    if (PR.get('cfg') or {}).get('dome') and str(game.get('roof') or '') in ('dome', 'closed'):
        for tm in TM: tm.mp *= 1.02
    if (PR.get('cfg') or {}).get('rest'):   # short week / off a bye: a small yardage shade, tested on the backtest
        for tm, rk in ((TM[0], 'away_rest'), (TM[1], 'home_rest')):
            rd = game.get(rk) or 7; m = .985 if rd <= 5 else 1.015 if rd >= 10 else 1.0; tm.mp *= m; tm.mr *= m
    N = n; sc = np.zeros((2, N)); poss = rng.integers(0, 2, N); recv2 = 1 - poss   # the team that kicks off first receives the second half
    clock = np.full(N, 3600.0); yl = KO[rng.integers(0, 101, N)].astype(float); down = np.ones(N, int); togo = np.full(N, 10.0)
    done = np.zeros(N, bool); ot = np.zeros(N, bool); ot_first = np.full(N, -1); ot_possd = np.zeros((2, N), bool); half2 = np.zeros(N, bool)
    # box score accumulators
    box = []
    for t in TM:
        box.append(dict(tgt=np.zeros((len(t.R), N)), rec=np.zeros((len(t.R), N)), recyd=np.zeros((len(t.R), N)), rectd=np.zeros((len(t.R), N)),
                        car=np.zeros((len(t.U), N)), ruyd=np.zeros((len(t.U), N)), rutd=np.zeros((len(t.U), N)),
                        att=np.zeros(N), cmp=np.zeros(N), pyd=np.zeros(N), ptd=np.zeros(N), int=np.zeros(N), sk=np.zeros(N), qbru=np.zeros(N), qbryd=np.zeros(N), qbrtd=np.zeros(N),
                        plays=np.zeros(N), yds=np.zeros(N), to=np.zeros(N), drives=np.zeros(N), rzt=np.zeros(N), fga=np.zeros(N), fgm=np.zeros(N), punts=np.zeros(N), top=np.zeros(N), third=np.zeros(N), thirdc=np.zeros(N), fd=np.zeros(N), downs=np.zeros(N), go4=np.zeros(N), otd=np.zeros(N), ltd=np.zeros(N)))
    for o in (0, 1): box[o]['drives'] += (poss == o)
    in_rz = np.zeros(N, bool)
    pace = np.array([t.pace for t in TM]); aggr = np.array([t.aggr for t in TM]); pshift = np.array([t.pass_shift for t in TM]) + c_pass; rzp = np.array([t.rz_pass for t in TM])
    mp = np.array([t.mp for t in TM]) * c_yard; mr = np.array([t.mr for t in TM]) * c_yard; rzf = np.array([t.rzf for t in TM]) * c_td; cshift = np.array([t.comp_shift for t in TM])
    irate = np.array([t.int_rate for t in TM]); srate = np.array([t.sack_rate for t in TM]); scr = np.array([t.scramble for t in TM]); ep = np.array([t.exp_pass for t in TM]); er = np.array([t.exp_rush for t in TM]); qbypc = np.array([t.qb_ypc for t in TM])

    def change(idx, new_yl, kick=False):
        """possession flips for sims idx; new_yl is from the new offense's view"""
        poss[idx] = 1 - poss[idx]; yl[idx] = np.clip(new_yl, 1, 99); down[idx] = 1; togo[idx] = np.minimum(10, yl[idx])
        for o in (0, 1): box[o]['drives'][idx[poss[idx] == o]] += 1
        in_rz[idx] = False
        if ot.any(): ot_possd[poss[idx], idx] = True

    def score(idx, pts):
        o = poss[idx]; sc[o, idx] += pts

    for it in range(600):
        act = ~done
        if not act.any(): break
        ix = np.where(act)[0]; o = poss[ix]; d = 1 - o
        sd = sc[o, ix] - sc[d, ix]
        z = _zone(yl[ix]); tgb = _tg(togo[ix]); sdb = _sd(sd); tb = _t(clock[ix]); dn = (down[ix] >= 3).astype(int)
        # kneel: leading inside the final 70 s with a fresh set of downs — the game is over
        kneel = (sd > 0) & (clock[ix] <= 70) & (down[ix] == 1) & ~ot[ix]
        # 4th down
        is4 = down[ix] == 4
        go_p = np.clip(F4[tgb, z] * aggr[o], 0, .95)
        dist = yl[ix] + 17
        desperate = (sd < 0) & ((clock[ix] < 150) | ((sd <= -4) & (clock[ix] < 300)) | ((sd <= -9) & (clock[ix] < 600)))
        go_p = np.where(desperate & ((dist > 55) | (sd < -3)), .95, go_p)   # trailing late: down more than a field goal, or out of range, you go
        fg_ok = (dist <= 55) | ((dist <= 62) & (sd >= -3) & (sd <= 0) & (clock[ix] < 120))
        u = rng.random(len(ix))
        go = is4 & (u < go_p); fgt = is4 & ~go & fg_ok; punt = is4 & ~go & ~fg_ok
        # end-of-half field goal: ball in range with the clock about to die
        last = ((clock[ix] <= 40) & (clock[ix] > 0) & ~half2[ix] & (dist <= 58)) | ((clock[ix] <= 40) & half2[ix] & (dist <= 58) & (sd >= -3) & (sd <= 0))
        fgt = fgt | (last & ~is4 & ~go); punt = punt & ~last
        normal = ~fgt & ~punt & ~kneel
        # play call
        p = PP[np.clip(down[ix], 1, 4), tgb, z, sdb, tb]
        p = _sig(_logit(p) + pshift[o]); p = np.where(z == 3, .5 * p + .5 * rzp[o], p)
        ispass = normal & (rng.random(len(ix)) < p); isrush = normal & ~ispass
        yards = np.zeros(len(ix)); turnover = np.zeros(len(ix), bool); incomplete = np.zeros(len(ix), bool); td_ret = np.zeros(len(ix), bool); spot = np.zeros(len(ix)); fg_made = np.zeros(len(ix), bool)
        for side in (0, 1):
            T = TM[side]; B = box[side]; m = (o == side)
            # --- dropbacks ---
            pm_ = ispass & m; k = np.where(pm_)[0]; sims = ix[k]
            if len(k):
                B['plays'][sims] += 1
                r = rng.random(len(k)); sack = r < srate[side]; scrm = (~sack) & (r < srate[side] + scr[side]); thr = ~sack & ~scrm
                # sacks
                ks = k[sack]; ys = YSACK[rng.integers(0, 101, len(ks))]; yards[ks] = np.maximum(ys, -(99 - yl[ix[ks]])); B['sk'][ix[ks]] += 1
                fs = rng.random(len(ks)) < L['fum_sack']; turnover[ks[fs]] = True
                # scrambles
                kc = k[scrm]; q = rng.integers(0, 101, len(kc)); yv = np.round(YSCR[q] * qbypc[side])
                inrz = z[kc] == 3; rzb = _rzb(yl[ix[kc]]); rztd = inrz & (rng.random(len(kc)) < np.clip(RZR[rzb] * rzf[side], 0, .97))
                yards[kc] = np.where(rztd, yl[ix[kc]], np.where(inrz, np.minimum(yv, yl[ix[kc]] - 1), np.minimum(yv, yl[ix[kc]])))
                B['qbru'][ix[kc]] += 1; B['qbryd'][ix[kc]] += yards[kc]; B['qbrtd'][ix[kc]] += (yards[kc] >= yl[ix[kc]])
                # throws
                kt = k[thr]; st = ix[kt]
                if len(kt):
                    B['att'][st] += 1
                    uu = rng.random(len(kt)); inrz = z[kt] == 3
                    tgt = np.where(inrz, np.searchsorted(T.tw_rz, uu), np.searchsorted(T.tw, uu)); tgt = np.clip(tgt, 0, len(T.R) - 1)
                    np.add.at(B['tgt'], (tgt, st), 1)
                    cp = np.clip(C[z[kt], dn[kt]] + cshift[side] + T.catch_adj[tgt], .25, .9)
                    v = rng.random(len(kt)); picked = v < irate[side]; comp = (~picked) & (v < irate[side] + cp)
                    # yards on completions: league quantile for the spot × matchup × receiver, explosive tail at the matchup rate
                    tail = rng.random(len(kt)) < ep[side]; qi = np.where(tail, rng.integers(TAILP, 101, len(kt)), rng.integers(0, TAILP, len(kt)))
                    yv = np.round(Y[0, z[kt], dn[kt], qi] * mp[side] * T.ypt_r[tgt])
                    # inside the 20 the touchdown is drawn by spot: league P(TD | completion from here) × the red-zone matchup
                    rzb = _rzb(yl[st]); ptd = np.clip(RZP[rzb] * rzf[side] * mp[side] ** .3, 0, .97)
                    rztd = inrz & (rng.random(len(kt)) < ptd)
                    yv = np.where(rztd, yl[st], np.where(inrz, np.minimum(yv, yl[st] - 1), np.minimum(yv, yl[st]))); yv = np.where(comp, yv, 0)
                    yards[kt] = yv; incomplete[kt] = ~comp & ~picked
                    kc_ = kt[comp]; tg_c = tgt[comp]; sc_ = st[comp]
                    np.add.at(B['rec'], (tg_c, sc_), 1); np.add.at(B['recyd'], (tg_c, sc_), yv[comp]); B['cmp'][sc_] += 1; B['pyd'][sc_] += yv[comp]
                    istd = yv[comp] >= yl[sc_]; np.add.at(B['rectd'], (tg_c[istd], sc_[istd]), 1); B['ptd'][sc_[istd]] += 1
                    fm = rng.random(len(kc_)) < L['fum_rec']; turnover[kc_[fm & ~istd]] = True
                    # interceptions: spot ≈ 8 yards downfield from the line, returned ~5
                    kp = kt[picked]; turnover[kp] = True; B['int'][ix[kp]] += 1; spot[kp] = np.clip(yl[ix[kp]] - 3, 1, 99)
                    td_ret[kp[rng.random(len(kp)) < L['int_ret_td']]] = True
            # --- rushes ---
            rm_ = isrush & m; k = np.where(rm_)[0]; sims = ix[k]
            if len(k):
                B['plays'][sims] += 1
                uu = rng.random(len(k)); gl = yl[sims] <= 5
                ru = np.where(gl, np.searchsorted(T.rw_gl, uu), np.searchsorted(T.rw, uu)); ru = np.clip(ru, 0, len(T.U) - 1)
                np.add.at(B['car'], (ru, sims), 1)
                tail = rng.random(len(k)) < er[side]; qi = np.where(tail, rng.integers(TAILR, 101, len(k)), rng.integers(0, TAILR, len(k)))
                yv = np.round(Y[1, z[k], dn[k], qi] * mr[side] * T.ypc_r[ru])
                inrz = z[k] == 3; rzb = _rzb(yl[sims]); ptd = np.clip(RZR[rzb] * rzf[side] * mr[side] ** .3, 0, .97); rztd = inrz & (rng.random(len(k)) < ptd)
                yv = np.where(rztd, yl[sims], np.where(inrz, np.minimum(yv, yl[sims] - 1), np.minimum(yv, yl[sims])))
                yards[k] = yv; np.add.at(B['ruyd'], (ru, sims), yv); istd = yv >= yl[sims]; np.add.at(B['rutd'], (ru[istd], sims[istd]), 1)
                fm = rng.random(len(k)) < L['fum_rush']; turnover[k[fm & ~istd]] = True
            # --- kicks ---
            fk = np.where(fgt & m)[0]
            if len(fk):
                B['fga'][ix[fk]] += 1; made = rng.random(len(fk)) < _fg(L, dist[fk]); B['fgm'][ix[fk][made]] += 1; B['plays'][ix[fk]] += 1
                fg_made[fk[made]] = True; sc[side, ix[fk[made]]] += 3
            pk = np.where(punt & m)[0]
            if len(pk): B['punts'][ix[pk]] += 1; B['plays'][ix[pk]] += 1
        # third-down bookkeeping and yards
        for side in (0, 1):
            m = (o == side) & normal; box[side]['yds'][ix[m]] += yards[m]
            th = m & (down[ix] == 3); box[side]['third'][ix[th]] += 1; box[side]['thirdc'][ix[th & (yards >= togo[ix]) & ~turnover]] += 1
        # ---- resolve ----
        # scoring plays
        td = normal & (yards >= yl[ix]) & ~turnover
        for side in (0, 1): box[side]["otd"][ix[td & (o == side)]] += 1; box[side]["ltd"][ix[td & (o == side) & (z > 0) & (z < 3)]] += 1
        # defensive return touchdowns
        for side in (0, 1):
            m = td_ret & (d == side); sc[side, ix[m]] += 7   # return TD + the kick
        # offensive TD: points + XP / two-point try
        tsims = ix[td]; to_ = o[td]
        if len(tsims):
            sd_after = sd[td] + 6; two = (sd_after == -2) | (sd_after == -5)   # trailing by 2 or 5 after the six: go for two
            xp = np.where(two, rng.random(len(tsims)) < .48, rng.random(len(tsims)) < .94)
            sc[to_, tsims] += 6 + np.where(two, 2, 1) * xp
        # clock
        if PACE2 is not None: base_gap = PACE2[sdb, (clock[ix] <= 1800).astype(int)]
        else: base_gap = L['snap_gap']['run_or_complete']
        gap = np.where(incomplete, L['snap_gap']['incomplete'], base_gap)
        hurry = ((sd < 0) & (clock[ix] < 240)) | ((clock[ix] > 1800) & (clock[ix] < 1920))
        gap = np.where(hurry, np.where(incomplete, L['snap_gap']['hurry_incomplete'], L['snap_gap']['hurry']), gap) * pace[o]
        gap = np.where(fgt | punt, 6.0, gap); gap = np.where(td | turnover | td_ret, np.where(incomplete, 5, 12), gap)
        gap = np.where(kneel, clock[ix] + 1, gap)
        for side in (0, 1): box[side]['top'][ix[o == side]] += gap[o == side]
        before = clock[ix].copy(); clock[ix] = np.maximum(0, clock[ix] - gap)
        # scoring / turnover / downs → new possession (field goals were decided and scored above)
        new_poss = np.zeros(len(ix), bool); new_yl = np.zeros(len(ix))
        kick = td | td_ret | fg_made
        new_poss |= kick; new_yl = np.where(kick, KO[rng.integers(0, 101, len(ix))], new_yl)
        # missed FG: opponent takes over at the spot (or the 20)
        miss = fgt & ~fg_made; new_poss |= miss; new_yl = np.where(miss, 100 - np.maximum(yl[ix] + 7, 20), new_yl)
        # punt (a return touchdown hands the kicking team the kickoff)
        if punt.any():
            pk = np.where(punt)[0]; net = PUNT[rng.integers(0, 101, len(pk))]; land = yl[ix[pk]] - net
            ny = np.where(land <= 0, 80, 100 - land); new_poss[pk] = True; new_yl[pk] = ny
            prt = pk[rng.random(len(pk)) < L['punt_ret_td']]
            if len(prt): sc[d[prt], ix[prt]] += 7; new_poss[prt] = False; yl[ix[prt]] = KO[rng.integers(0, 101, len(prt))]; down[ix[prt]] = 1; togo[ix[prt]] = 10; in_rz[ix[prt]] = False
        # kickoff return touchdown: the receiving side scores and kicks back
        if kick.any():
            kk = np.where(kick)[0]; krt = kk[rng.random(len(kk)) < L['ko_ret_td']]
            if len(krt): sc[d[krt], ix[krt]] += 7; new_poss[krt] = False; yl[ix[krt]] = KO[rng.integers(0, 101, len(krt))]; down[ix[krt]] = 1; togo[ix[krt]] = 10; in_rz[ix[krt]] = False
        # turnovers (not return TDs: those kicked off already)
        tov = turnover & ~td_ret
        new_poss |= tov; new_yl = np.where(tov, 100 - np.clip(np.where(spot > 0, spot, yl[ix] - yards), 1, 99), new_yl)
        for side in (0, 1): box[side]['to'][ix[(o == side) & turnover]] += 1
        # ordinary plays: move the ball, downs
        plain = normal & ~td & ~turnover
        yl_new = yl[ix] - yards
        first = plain & (yards >= togo[ix])
        for side in (0, 1): box[side]['fd'][ix[first & (o == side)]] += 1
        nd = np.where(first, 1, down[ix] + 1)
        on_downs = plain & (nd > 4)
        new_poss |= on_downs; new_yl = np.where(on_downs, 100 - yl_new, new_yl)
        for side in (0, 1): box[side]['downs'][ix[on_downs & (o == side)]] += 1; box[side]['go4'][ix[go & (o == side)]] += 1
        keep = plain & ~on_downs
        yl[ix[keep]] = np.clip(yl_new[keep], 1, 99); down[ix[keep]] = nd[keep]; togo[ix[keep]] = np.where(first[keep], np.minimum(10, yl[ix[keep]]), togo[ix[keep]] - yards[keep])
        # red-zone trips
        for side in (0, 1):
            m = keep & (o == side) & (yl[ix] <= 20) & ~in_rz[ix]; box[side]['rzt'][ix[m]] += 1
        in_rz[ix[keep]] |= yl[ix[keep]] <= 20
        # halftime: whoever is due receives
        half = (before > 1800) & (clock[ix] <= 1800) & ~ot[ix]
        if half.any():
            hs = ix[half]; clock[hs] = 1800; half2[hs] = True
            poss[hs] = recv2[hs]; yl[hs] = KO[rng.integers(0, 101, len(hs))]; down[hs] = 1; togo[hs] = 10; in_rz[hs] = False
            for side in (0, 1): box[side]['drives'][hs[poss[hs] == side]] += 1
            new_poss[half] = False
        # possession changes
        if new_poss.any():
            idx = ix[new_poss]; change(idx, new_yl[new_poss])
        # end of regulation / overtime
        over = (clock[ix] <= 0) & ~ot[ix]
        if over.any():
            os_ = ix[over]; tie = sc[0, os_] == sc[1, os_]
            done[os_[~tie]] = True
            ots = os_[tie]
            if len(ots):
                ot[ots] = True; clock[ots] = 600; poss[ots] = rng.integers(0, 2, len(ots)); ot_first[ots] = poss[ots]; ot_possd[:, ots] = False; ot_possd[poss[ots], ots] = True
                yl[ots] = KO[rng.integers(0, 101, len(ots))]; down[ots] = 1; togo[ots] = 10; in_rz[ots] = False
        # overtime ends: a TD, or any lead once both have had the ball, or the clock
        o_ix = ix[ot[ix]]
        if len(o_ix):
            diff = sc[0, o_ix] - sc[1, o_ix]; both = ot_possd[0, o_ix] & ot_possd[1, o_ix]
            tdnow = np.isin(o_ix, ix[td | td_ret])
            end = tdnow | ((diff != 0) & both) | (clock[o_ix] <= 0)
            done[o_ix[end]] = True
    return _summary(game, TM, sc, box, N, ot)

def _summary(game, TM, sc, box, N, ot):
    A, H = TM[0].name, TM[1].name; sa, sh = sc[0], sc[1]; margin = sh - sa; total = sa + sh
    pairs = {}
    for a, h in zip(np.round(sa).astype(int), np.round(sh).astype(int)): pairs[(a, h)] = pairs.get((a, h), 0) + 1
    top = sorted(pairs.items(), key=lambda kv: -kv[1])[:8]
    # the headline score: the most frequent exact final among the games the likelier winner wins (the raw mode can sit on the other side at ~1%)
    hw = (sh > sa).mean() >= (sa > sh).mean()
    side = [(k, c) for k, c in pairs.items() if (k[1] > k[0]) == hw and k[0] != k[1]]
    head = max(side, key=lambda kv: kv[1]) if side else top[0]
    spread, tot = game.get('spread'), game.get('total')
    def dist(x, lo, hi): h = np.bincount(np.clip(np.round(x).astype(int) - lo, 0, hi - lo), minlength=hi - lo + 1); return {'lo': lo, 'counts': h.tolist()}
    def team_box(side, T, B):
        pl = []
        for i, p in enumerate(T.R):
            tg, rc, yd, td_ = B['tgt'][i], B['rec'][i], B['recyd'][i], B['rectd'][i]
            car = ruyd = rutd = None
            j = next((k for k, q in enumerate(T.U) if q['name'] == p['name']), None)
            if j is not None: car, ruyd, rutd = B['car'][j], B['ruyd'][j], B['rutd'][j]
            pl.append(dict(name=p['name'], pos=p['pos'], slot=p['slot'], inj=p['inj'],
                tgt=float(tg.mean()), rec=float(rc.mean()), rec_yds=float(yd.mean()), rec_yds_med=float(np.median(yd)), rec_yds_p25=float(np.percentile(yd, 25)), rec_yds_p75=float(np.percentile(yd, 75)), rec_td=float(td_.mean()),
                car=None if car is None else float(car.mean()), rush_yds=None if car is None else float(ruyd.mean()), rush_yds_med=None if car is None else float(np.median(ruyd)), rush_yds_p25=None if car is None else float(np.percentile(ruyd, 25)), rush_yds_p75=None if car is None else float(np.percentile(ruyd, 75)), rush_td=None if car is None else float(rutd.mean()),
                p_td=float(((td_ + (rutd if car is not None else 0)) >= 1).mean()), p_100=float(((yd + (ruyd if car is not None else 0)) >= 100).mean()),
                share=round(float(T.tw[i] - (T.tw[i - 1] if i else 0)), 3)))
        for j, q in enumerate(T.U):
            if q['pos'] == 'QB' or any(x['name'] == q['name'] for x in pl): continue
            car, ruyd, rutd = B['car'][j], B['ruyd'][j], B['rutd'][j]
            pl.append(dict(name=q['name'], pos=q['pos'], slot=q['slot'], inj=q['inj'], tgt=0, rec=0, rec_yds=0, rec_yds_med=0, rec_yds_p25=0, rec_yds_p75=0, rec_td=0,
                car=float(car.mean()), rush_yds=float(ruyd.mean()), rush_yds_med=float(np.median(ruyd)), rush_yds_p25=float(np.percentile(ruyd, 25)), rush_yds_p75=float(np.percentile(ruyd, 75)), rush_td=float(rutd.mean()),
                p_td=float((rutd >= 1).mean()), p_100=float((ruyd >= 100).mean()), share=0))
        q = T.qb
        qb = dict(name=q['name'], att=float(B['att'].mean()), cmp=float(B['cmp'].mean()), pass_yds=float(B['pyd'].mean()), pass_yds_med=float(np.median(B['pyd'])), pass_yds_p25=float(np.percentile(B['pyd'], 25)), pass_yds_p75=float(np.percentile(B['pyd'], 75)),
                  pass_td=float(B['ptd'].mean()), int=float(B['int'].mean()), sacks=float(B['sk'].mean()), car=float(B['qbru'].mean()), rush_yds=float(B['qbryd'].mean()), rush_td=float(B['qbrtd'].mean()),
                  p_300=float((B['pyd'] >= 300).mean()), p_2td=float((B['ptd'] >= 2).mean()), p_int=float((B['int'] >= 1).mean()))
        # designed QB runs are in the rusher list too: fold them into the QB line
        j = next((k for k, u in enumerate(T.U) if u['pos'] == 'QB'), None)
        if j is not None: qb['car'] += float(B['car'][j].mean()); qb['rush_yds'] += float(B['ruyd'][j].mean()); qb['rush_td'] += float(B['rutd'][j].mean())
        team = dict(plays=float(B['plays'].mean()), pass_att=float(B['att'].mean()), rush_att=float(sum(B['car'][k].mean() for k in range(len(T.U))) + B['qbru'].mean()), yds=float(B['yds'].mean()),
                    to=float(B['to'].mean()), drives=float(B['drives'].mean()), rz_trips=float(B['rzt'].mean()), fga=float(B['fga'].mean()), fgm=float(B['fgm'].mean()), punts=float(B['punts'].mean()),
                    top=float(B['top'].mean()), third=float(B['third'].mean()), downs=float(B['downs'].mean()), go4=float(B['go4'].mean()), otd=float(B['otd'].mean()), ltd=float(B['ltd'].mean()), third_conv=float((B['thirdc'].sum() / max(1, B['third'].sum()))), first_downs=float(B['fd'].mean()),
                    pts=float(sc[side].mean()), pts_med=float(np.median(sc[side])), pts_p10=float(np.percentile(sc[side], 10)), pts_p90=float(np.percentile(sc[side], 90)))
        return dict(team=T.name, qb=qb, players=sorted(pl, key=lambda x: -(x['tgt'] + (x['car'] or 0))), team_stats=team)
    out = dict(game_id=game['game_id'], week=game['week'], away=A, home=H, date=game['date'], time=game['time'], n=N, spread=spread, total=tot, roof=game.get('roof'),
               away_qb=TM[0].qb['name'], home_qb=TM[1].qb['name'],
               p_home=float((sh > sa).mean()), p_away=float((sa > sh).mean()), p_tie=float((sa == sh).mean()), p_ot=float(ot.mean()),
               mean_away=float(sa.mean()), mean_home=float(sh.mean()), med_away=float(np.median(sa)), med_home=float(np.median(sh)), mean_margin=float(margin.mean()), sd_margin=float(margin.std()), mean_total=float(total.mean()), sd_total=float(total.std()),
               likely=[dict(away=int(a), home=int(h), p=c / N) for (a, h), c in top], headline=dict(away=int(head[0][0]), home=int(head[0][1]), p=head[1] / N),
               p_home_cover=None, p_push=None, p_over=None if tot is None else float((total > tot).mean()), p_total_push=None if tot is None else float((total == tot).mean()),
               margin_dist=dist(margin, -45, 45), total_dist=dist(total, 10, 90),
               box=[team_box(0, TM[0], box[0]), team_box(1, TM[1], box[1])],
               actual=None if game.get('home_score') is None else dict(away=game['away_score'], home=game['home_score']))
    # nflverse spread_line = the home team's expected margin (positive = home favourite): the home side covers when margin > spread_line
    if spread is not None: out['p_home_cover'] = float((margin > spread).mean()); out['p_push'] = float((margin == spread).mean())
    return out
