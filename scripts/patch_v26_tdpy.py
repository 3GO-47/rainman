"""v26 — TD Picks for every week, not just the one being picked.

build_td_picks.py now writes a board for each week of the season beside the live one (td_picks.json 'wk'):
  * a finished week: every player who played, scored by the walk-forward model refit on earlier weeks only (graded);
  * a week still importing: the model built from games before it, run on the depth chart of that week, graded as box scores land;
  * a week still to come: an early look with today's depth chart and form, that week's opponent and line (implied total
    estimated from each team's average this season until the books post one) — it becomes the live board when it is next up.
Rows are compact (reasons as feature codes the page turns into words); 'base' holds the season stats every early week shares.

Usage: python scripts/patch_v26_tdpy.py [path/to/build_td_picks.py]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/build_td_picks.py'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v26_tdpy: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

rep("""        rows.append((r['s'], r['w'], [f[k] for k in FEATS], int(r['td'] > 0), BUCKET[r['slot']], name, r['team']))""",
    """        rows.append((r['s'], r['w'], [f[k] for k in FEATS], int(r['td'] > 0), BUCKET[r['slot']], name, r['team'], r['td'], r['opp'], r['home'],
                     d if r['s'] == SEASON else None, r['slot']))""")
rep("""bt_weeks, allp, ally, allb, allk, bt_top = [], [], [], [], [], []""",
    """bt_weeks, allp, ally, allb, allk, bt_top = [], [], [], [], [], []
MODELS = {}                                                         # this season's walk-forward models by week key (the week boards' reasons)""")
rep("""    m = fit(Xall[tr], yall[tr]); p = predict(m, Xall[te]); y = yall[te]; bb = bk[te]""",
    """    m = fit(Xall[tr], yall[tr]); p = predict(m, Xall[te]); y = yall[te]; bb = bk[te]
    if ek // 100 == SEASON: MODELS[int(ek)] = m""")

# the reasons: one place decides which features explain a pick (codes) and how they read (words)
rep("""def norm(n): return re.sub(r'[^a-z]', '', re.sub(r'\\b(jr|sr|ii|iii|iv|v)\\b\\.?', '', n.lower()))""",
    """def why_codes(contrib, d):
    out = []
    for j in np.argsort(-contrib):
        k = FEATS[j]
        if contrib[j] <= .05 or k.startswith('b_') or k == 'home' or (k == 'ra' and d['b'] == 'QB1'): continue
        out.append(int(j))
        if len(out) == 3: break
    return out
def why_text(k, d, opp):
    if k == 'ra_qb': return f"{d['ra']:.1f} carries a game"
    if k == 'form': return f"TD in {d['hitS']} of {d['gpS']} — below his career norm" if d['gpS'] else 'scoring history'
    if k == 'l3': return f"TD in {d['l3k']} of his last {d['l3n']}" if d['l3n'] else 'no games yet this season'
    if k == 'crate': return f"career: TD in {d['hitC']} of {d['gC']}"
    if k == 'share': return f"{d['mine']} of his team's {d['tt']} TDs"
    if k == 'touch': return f"{d['touch']:.1f} touches a game"
    if k == 'tgt': return f"{d['tgt']:.1f} targets a game"
    if k == 'ra': return f"{d['ra']:.1f} carries a game"
    if k == 'snp': return f"{d['snp']:.0%} of snaps" if d['snp'] is not None else 'every-down role'
    if k == 'imp': return f"team implied {d['imp']:.1f}" if d['imp'] is not None else 'team total'
    if k == 'sp': return f"favored by {d['sp']:g}" if d['sp'] and d['sp'] > 0 else 'spread'
    if k == 'def': return f"{opp} allows {d['dr']:.2f} TD/g to {d['g']}s" if d['dr'] is not None else 'soft defense'
    if k == 'def_l3': return f"{opp} gave {d['g']}s {d['dl3']:.1f} TD/g lately" if d['dl3'] is not None else 'defense trend'
    if k == 'h2h': return f"scored vs {opp} before"
    return LBL.get(k, k)
def risk_of(contrib, d, opp):
    for j in np.argsort(contrib):
        k = FEATS[j]
        if contrib[j] >= -.12: break
        risk = None
        if k == 'sp' and d['sp'] is not None and d['sp'] < 0: risk = f"underdog by {abs(d['sp']):g}"
        elif k == 'imp' and d['imp'] is not None and d['imp'] < 21.5: risk = f"team implied only {d['imp']:.1f}"
        elif k == 'def' and d['dr'] is not None: risk = f"{opp} allows just {d['dr']:.2f} TD/g to {d['g']}s"
        elif k == 'def_l3' and d['dl3'] is not None: risk = f"{opp} has held {d['g']}s to {d['dl3']:.1f} TD/g lately"
        elif k == 'l3' and d['l3n'] >= 2 and d['l3k'] == 0: risk = f"no TD in his last {d['l3n']}"
        elif k == 'touch' and d['b'] != 'QB1' and d['touch'] < STOUCH[d['b']]: risk = f"only {d['touch']:.1f} touches a game"
        elif k == 'snp' and d['snp'] is not None and d['snp'] < .6: risk = f"plays {d['snp']:.0%} of snaps"
        if risk: return int(j), risk
    return -1, None

def norm(n): return re.sub(r'[^a-z]', '', re.sub(r'\\b(jr|sr|ii|iii|iv|v)\\b\\.?', '', n.lower()))""")

rep("raw = allp.copy()", "raw = allp.copy(); RAWP = raw                  # (the target loop reuses the name raw)")
i0 = s.index("    why = []\n    for j in np.argsort(-contrib):")
i1 = s.index("    pr = price.get(norm(dr['player']))")
s = s[:i0] + "    why = [why_text(FEATS[j], d, opp) for j in why_codes(contrib, d)]\n    risk = risk_of(contrib, d, opp)[1]\n" + s[i1:]

# the week boards
rep("""out = dict(built=str(TODAY),""",
    """# ---------------- every other week of the season ----------------
def r1(v): return None if v is None else round(float(v), 1)
def r2(v): return None if v is None else round(float(v), 2)
def stats(d): return [d['hitS'], d['gpS'], d['l3k'], d['l3n'], d['hitC'], d['gC'], d['mine'], d['tt'], r1(d['touch']), r1(d['tgt']), r1(d['ra']),
                      None if d['snp'] is None else int(round(100 * d['snp']))]
def ostats(d, est=False): return [r1(d['imp']), d['sp'], r2(d['dr']), r2(d['dl3']), d['h2h'], int(est)]
td_of = {(r['s'], r['w'], r['player']): r['td'] for r in logs}
logged_teams = collections.defaultdict(set)
for r in logs: logged_teams[(r['s'], r['w'])].add(r['team'])
def complete(w): return bool(by_wk.get(w)) and all({g['vis'], g['home']} <= logged_teams.get((SEASON, w), set()) for g in by_wk[w])
DSNAP = sorted(glob.glob(P + 'depth_charts_*.csv'))
def depth_for(w):
    \"\"\"the last depth-chart snapshot taken before the week's first game (the latest one for a week still to come).\"\"\"
    first = min(g['date'] for g in by_wk[w]); c = [f for f in DSNAP if f.split('_')[-1][:10] < first]
    f = c[-1] if c else DSNAP[-1]
    return list(csv.DictReader(open(f, encoding='utf-8')))
# implied total / spread estimate for a week with no line yet: each team's average this season, scored and allowed
AVI, AVA = collections.defaultdict(list), collections.defaultdict(list)
for w_ in sorted(by_wk):
    if w_ >= target: continue
    for g in by_wk[w_]:
        h_, a_ = g['home'], g['vis']
        if (SEASON, w_, h_) in LN and (SEASON, w_, a_) in LN:
            hi, ai = LN[(SEASON, w_, h_)][0], LN[(SEASON, w_, a_)][0]
            AVI[h_].append(hi); AVI[a_].append(ai); AVA[h_].append(ai); AVA[a_].append(hi)
avg = lambda L, dflt=22.0: sum(L) / len(L) if L else dflt
def inj_future(team, nm, gd):
    v = INJR.get((team, norm(nm)))
    if not v: return '1'
    st, ret = v
    if ret: return '-1' if ret > gd else '1'
    if st in ('Injured Reserve', 'Suspension', 'Physically Unable to Perform', 'PUP', 'Reserve'): return '-1'
    return '0' if st in ('Out', 'Doubtful') else '1'
INJR = {}
for r in csv.DictReader(open(P + 'injuries_current.csv', encoding='utf-8')):
    st = (r.get('status') or '').strip(); ret = (r.get('ret') or '').strip(); ret = '' if ret in ('nan', 'None') else ret[:10]
    if st and st not in ('Active', 'nan'): INJR[(r.get('team'), norm(r['player']))] = (st, ret)
FIELD_MIN = .15                                                    # the board lists players rated 15%+ (the ledger's floor)
BASE, BIDX = [], {}
def model_board(w, m, cal, cut, rows_depth, future):
    mu_, sd_, be_ = m; out_r = []; seen = set()
    for dr in rows_depth:
        slot = dr['slot']
        if slot not in BUCKET or dr['team'] not in sched: continue
        raw_ = sched[dr['team']].get(f'week_{w}', '')
        if not raw_ or raw_ == 'BYE': continue
        opp, home = raw_.replace('@', ''), not raw_.startswith('@')
        nm = dr.get('log_name') or dr['player']
        if (dr['team'], nm) in seen: continue
        seen.add((dr['team'], nm))
        est = (SEASON, w, dr['team']) not in LN
        if est:
            ti = avg(AVI[dr['team']])
            LN[(SEASON, w, dr['team'])] = (round((ti + avg(AVA[opp])) / 2, 1), round((ti - avg(AVI[opp]) + (1.5 if home else -1.5)) * 2) / 2)
        prev = [r for r in byname.get(nm, []) if (r['s'], r['w']) < cut]
        f, d = profile(prev, SEASON, w, dr['team'], opp, slot, home)
        if est: del LN[(SEASON, w, dr['team'])]
        x = np.array([f[k] for k in FEATS], float); contrib = be_[1:] * ((x - mu_) / sd_)
        p = float(cal(np.array([float(1 / (1 + np.exp(-(be_[0] + contrib.sum()))))]))[0])
        if future:
            gd = next((g['date'] for g in by_wk[w] if dr['team'] in (g['vis'], g['home'])), '9999')
            inj = inj_future(dr['team'], dr['player'], gd)
        else: inj = str(iflag(dr.get('injury', '1')))
        if p < FIELD_MIN: continue
        res = td_of.get((SEASON, w, nm))
        if future:                                                  # an early week: the season stats sit once in BASE, the row points at them
            key_ = dr['player'] + '|' + dr['team']
            if key_ not in BIDX: BIDX[key_] = len(BASE); BASE.append([dr['player'], dr['team'], slot, d['b']] + stats(d))
            out_r.append([BIDX[key_], opp, int(home), int(round(1000 * p)), why_codes(contrib, d), risk_of(contrib, d, opp)[0], inj, ostats(d, est)])
        else:
            out_r.append([dr['player'], dr['team'], opp, int(home), slot, int(round(1000 * p)), res, why_codes(contrib, d), risk_of(contrib, d, opp)[0], inj,
                          stats(d), ostats(d, est), d['b']])
    out_r.sort(key=lambda r: -r[3] if future else -r[5])
    return out_r
WK = {}
ident = lambda q: q
for w in sorted(by_wk):
    if w == target: continue
    ek = SEASON * 100 + w; ng = len(by_wk[w]); dts = sorted(g['date'] for g in by_wk[w])
    if w < target and complete(w) and ek in MODELS:
        mu_, sd_, be_ = MODELS[ek]; R = []
        ent = next(e for e in bt_top if e[0] == ek); off, gidx = ent[1], ent[3]
        for j, g in enumerate(gidx):
            p = float(allp[off + j]); r_ = rows[int(g)]; d = r_[10]
            if p < FIELD_MIN or d is None: continue
            contrib = be_[1:] * ((Xall[int(g)] - mu_) / sd_)
            R.append([r_[5], r_[6], r_[8], int(r_[9]), r_[11], int(round(1000 * p)), r_[7], why_codes(contrib, d), risk_of(contrib, d, r_[8])[0], '1', stats(d), ostats(d), r_[4]])
        R.sort(key=lambda r: -r[5]); WK[str(w)] = dict(m='wf', g=ng, d=[dts[0], dts[-1]], r=R)
    elif w < target:
        tr = key < ek; pri = allk < ek
        m_ = fit(Xall[tr], yall[tr]); cal_ = pav(RAWP[pri], ally[pri]) if pri.sum() >= 2000 else ident
        R = model_board(w, m_, cal_, (SEASON, w), depth_for(w), False)
        WK[str(w)] = dict(m='pre', g=ng, d=[dts[0], dts[-1]], r=R)
    else:
        R = model_board(w, (mu, sd, beta), CAL, (SEASON, target), depth, True)
        WK[str(w)] = dict(m='early', g=ng, d=[dts[0], dts[-1]], r=R, ln=sum(1 for g in by_wk[w] if (SEASON, w, g['home']) in LN))
print('  week boards: ' + ' · '.join(f"{w} {v['m']} {len(v['r'])}" for w, v in WK.items()))

out = dict(built=str(TODAY),""")
rep("""           bt=bt, picks=picks, record=rec)""",
    """           bt=bt, picks=picks, record=rec, wk=WK, base=BASE, grp=GRP)""")
open(P, 'w', encoding='utf-8').write(s)
print('patch_v26_tdpy: TD Picks boards for every week')
