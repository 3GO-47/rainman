"""Tennis layer -> dashboard/tennis.html (+ data/processed/tennis_matches.csv, tennis_elo.csv).

Inputs (scripts/local/pull_tennis.py): data/raw/tennis/{atp,wta}_matches_{year}.csv, {tour}_rankings_current.csv, {tour}_players.csv (the Sackmann archive mirror),
        data/raw/tennis/espn_results.csv (completed matches since the mirror stops — same Elo treatment, no serve stats),
        data/raw/tennis/espn_<date>.txt (the week's singles matches), data/raw/tennis/markets_<date>.txt (Kalshi + Polymarket match prices).
Model : Elo in the FiveThirtyEight style — K = 250 / (matches + 5)^0.4, one overall rating and one per surface, updated match by match in date order
        across every cached season; a match-up probability uses the 50/50 blend of overall and surface Elo:  P(A) = 1 / (1 + 10^((Elo_B − Elo_A)/400)).
Page  : MATCHES (this week, by tournament: time, both players with rank / Elo / last-10 form / 12-month surface record, H2H, model P, market P from
        Kalshi and Polymarket, edge) and PLAYERS (search any player: profile, Elo by surface, serve & return rates vs tour, last 20 matches).
Every number traces to the Sackmann match rows, ESPN's scoreboard and the two exchanges; nothing is typed in.
"""
import csv, glob, json, math, os, re, unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
RAW = 'data/raw/tennis'
TOURS = ('atp', 'wta')
SURFACES = ('Hard', 'Clay', 'Grass')
LEVEL_W = {'G': 1.1, 'M': 1.0, 'F': 1.0, 'A': 0.95, 'D': 0.85, 'C': 0.8, 'S': 0.8, 'PM': 1.0, 'P': 0.95, 'I': 0.9, 'T1': 1.0, 'T2': 0.95, 'W': 1.0}

def norm(n):
    n = unicodedata.normalize('NFKD', str(n or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z ]', '', n).strip()
def key(n): return norm(n).replace(' ', '')
def lastkey(n):
    p = norm(n).split(); return (p[0][:1] + p[-1]) if p else ''

def latest(prefix):
    f = sorted(glob.glob(f'{RAW}/{prefix}_*.txt')); return f[-1] if f else None

# ------------------------------------------------------------------------------------------------ Sackmann -> Elo + profiles
def load_matches(tour):
    rows = []
    for f in sorted(glob.glob(f'{RAW}/{tour}_matches_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if not r.get('winner_id') or not r.get('loser_id') or not r.get('tourney_date'): continue
            r['_tour'] = tour; r['_src'] = 'archive'; rows.append(r)
    last = max((r['tourney_date'] for r in rows), default='00000000')
    # ESPN's own completed results carry the history past the mirror's last date; ESPN ids are not Sackmann ids,
    # so a player is keyed by his name here and the two id spaces are reconciled by name in profiles()
    f = f'{RAW}/espn_results.csv'
    seen = {(r['tourney_date'], norm(r['winner_name']), norm(r['loser_name'])) for r in rows}
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r.get('tour') != tour or not r.get('winner') or not r.get('loser'): continue
            d = r['date']
            if d <= last or (d, norm(r['winner']), norm(r['loser'])) in seen: continue
            rows.append({'tourney_date': d, 'match_num': r['compId'], 'tourney_name': r['tournament'], 'tourney_level': 'A', 'surface': '',
                         'winner_id': 'E' + r['winner_id'], 'winner_name': r['winner'], 'winner_ioc': '', 'loser_id': 'E' + r['loser_id'], 'loser_name': r['loser'], 'loser_ioc': '',
                         'round': r['round'], 'score': r['score'], '_tour': tour, '_src': 'espn', '_court': r.get('court', '')})
    ids = {}
    for r in rows:
        if r.get('_src') == 'archive':
            ids.setdefault(key(r['winner_name']), r['winner_id']); ids.setdefault(key(r['loser_name']), r['loser_id'])
    for r in rows:
        if r.get('_src') != 'espn': continue
        for side in ('winner', 'loser'):
            a = ids.get(key(r[side + '_name']))
            if a: r[side + '_id'] = a
            else: ids.setdefault(key(r[side + '_name']), r[side + '_id'])
    rows.sort(key=lambda r: (r['tourney_date'], str(r.get('match_num') or '')))
    return rows

def elo_run(rows):
    """Chronological Elo. Returns per-player dict(elo, surf{S: elo}, n, surf_n{S: n}) and the pre-match Elo on each row (for calibration)."""
    P = defaultdict(lambda: dict(elo=1500.0, surf={s: 1500.0 for s in SURFACES}, n=0, surf_n={s: 0 for s in SURFACES}))
    E = lambda a, b: 1 / (1 + 10 ** ((b - a) / 400))
    K = lambda n: 250 / ((n + 5) ** 0.4)
    SURF_BY = {}
    for r in rows:
        if r.get('surface') in SURFACES: SURF_BY.setdefault(norm(r['tourney_name']), r['surface'])
    for r in rows:
        w, l = P[r['winner_id']], P[r['loser_id']]; s = r.get('surface') or ''
        if s not in SURFACES:
            toks = {t for t in norm(r['tourney_name']).split() if len(t) > 3}
            s = next((v for k, v in SURF_BY.items() if toks & set(k.split())), 'Hard')
            r['surface'] = s
        lw = LEVEL_W.get(r.get('tourney_level', ''), 0.9)
        r['_pw'] = 0.5 * E(w['elo'], l['elo']) + 0.5 * E(w['surf'][s], l['surf'][s]); r['_s'] = s
        ew = E(w['elo'], l['elo']); w['elo'] += K(w['n']) * lw * (1 - ew); l['elo'] -= K(l['n']) * lw * ew
        es = E(w['surf'][s], l['surf'][s]); w['surf'][s] += K(w['surf_n'][s]) * lw * (1 - es); l['surf'][s] -= K(l['surf_n'][s]) * lw * es
        w['n'] += 1; l['n'] += 1; w['surf_n'][s] += 1; l['surf_n'][s] += 1
    return P

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def profiles(rows, P, rank, players, since):
    """Per player: name, ioc, hand, rank, Elo set, 12-month records (overall / surface), serve & return rates, last 20 matches."""
    by = defaultdict(list)
    for r in rows:
        by[r['winner_id']].append((r, True)); by[r['loser_id']].append((r, False))
    out = {}
    for pid, L in by.items():
        name = next((r['winner_name'] if w else r['loser_name']) for r, w in L[::-1])
        rec = dict(w=0, l=0); srec = {s: dict(w=0, l=0) for s in SURFACES}; sv = defaultdict(float)
        for r, w in L:
            if r['tourney_date'] < since: continue
            rec['w' if w else 'l'] += 1; srec[r['_s']]['w' if w else 'l'] += 1
            pre = 'w_' if w else 'l_'; opp = 'l_' if w else 'w_'
            for k in ('ace', 'df', 'svpt', '1stIn', '1stWon', '2ndWon', 'SvGms', 'bpSaved', 'bpFaced'):
                v = num(r.get(pre + k)); sv[k] += v or 0
            for k in ('svpt', '1stIn', '1stWon', '2ndWon', 'bpFaced', 'bpSaved'):
                v = num(r.get(opp + k)); sv['o_' + k] += v or 0
        last = [(r, w) for r, w in L[-20:]]
        p = P[pid]
        out[pid] = dict(id=pid, name=name, tour=L[-1][0]['_tour'], ioc=(L[-1][0]['winner_ioc'] if L[-1][1] else L[-1][0]['loser_ioc']), hand=(players.get(pid) or {}).get('hand', ''),
                        rank=rank.get(pid, ''), elo=round(p['elo']), surf={s: round(p['surf'][s]) for s in SURFACES}, n=p['n'],
                        rec=rec, srec=srec,
                        serve=dict(ace=sv['ace'] / sv['svpt'] if sv['svpt'] else None, df=sv['df'] / sv['svpt'] if sv['svpt'] else None, first_in=sv['1stIn'] / sv['svpt'] if sv['svpt'] else None,
                                   first_won=sv['1stWon'] / sv['1stIn'] if sv['1stIn'] else None, second_won=sv['2ndWon'] / (sv['svpt'] - sv['1stIn']) if sv['svpt'] - sv['1stIn'] > 0 else None,
                                   bp_saved=sv['bpSaved'] / sv['bpFaced'] if sv['bpFaced'] else None, spw=(sv['1stWon'] + sv['2ndWon']) / sv['svpt'] if sv['svpt'] else None,
                                   rpw=1 - (sv['o_1stWon'] + sv['o_2ndWon']) / sv['o_svpt'] if sv['o_svpt'] else None, bp_conv=1 - sv['o_bpSaved'] / sv['o_bpFaced'] if sv['o_bpFaced'] else None),
                        last=[dict(d=r['tourney_date'], t=r['tourney_name'], rd=r['round'], s=r['_s'], w=int(w), opp=(r['loser_name'] if w else r['winner_name']), opp_id=(r['loser_id'] if w else r['winner_id']),
                                   opp_rank=(r.get('loser_rank') if w else r.get('winner_rank')) or '', score=r.get('score', ''), pw=round(r['_pw'] if w else 1 - r['_pw'], 3)) for r, w in last])
    return out

def tour_avg(prof):
    keys = ('ace', 'df', 'first_in', 'first_won', 'second_won', 'bp_saved', 'spw', 'rpw', 'bp_conv'); acc = {k: [] for k in keys}
    for p in prof.values():
        if p['rec']['w'] + p['rec']['l'] < 10: continue
        for k in keys:
            if p['serve'][k] is not None: acc[k].append(p['serve'][k])
    return {k: (sum(v) / len(v) if v else None) for k, v in acc.items()}

# ------------------------------------------------------------------------------------------------ the week's matches + markets
def load_espn():
    f = latest('espn'); M = []
    if not f: return M, ''
    for line in open(f, encoding='utf-8'):
        if not line.startswith('M|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 18: continue
        M.append(dict(tour=p[1], id=p[2], tourney=p[3], tourney_id=p[4], round=p[5], date=p[6], status=p[7], city=p[8], court=p[9],
                      p1=dict(id=p[10], name=p[11], flag=p[12]), p2=dict(id=p[13], name=p[14], flag=p[15]), winner=p[16], score=p[17]))
    return M, re.search(r'(\d{4}-\d{2}-\d{2})', f).group(1)

def load_markets():
    f = latest('markets'); K = defaultdict(dict); PM = []
    if not f: return K, PM
    for line in open(f, encoding='utf-8'):
        p = line.rstrip('\n').split('|')
        if p[0] == 'K' and len(p) >= 8:
            bid, ask = num(p[5]), num(p[6])
            if bid is None and ask is None: continue
            K[(p[1], p[3])][key(p[4])] = dict(name=p[4], bid=bid, ask=ask, vol=p[7], ticker=p[2])
        elif p[0] == 'P' and len(p) >= 10:
            outs = [x.strip() for x in p[5].split(',')]
            if len(outs) != 2: continue
            PM.append(dict(tour=p[1], slug=p[2], a=outs[0], b=outs[1], bid=num(p[7]), ask=num(p[8]), liq=p[9], start=p[10] if len(p) > 10 else ''))
    return K, PM

def surface_for(m, rows_by_tour):
    """Surface of an upcoming match: the Sackmann tournament this season whose name shares a city word with ESPN's name; default Hard."""
    toks = {t for t in norm(m['tourney']).split() if len(t) > 3 and t not in ('open', 'masters', 'rolex', 'championships', 'international', 'tennis', 'cup')}
    best = None
    for r in rows_by_tour.get(m['tour'], [])[::-1]:
        tn = set(norm(r['tourney_name']).split())
        if toks & tn: best = r.get('surface') or 'Hard'; break
    return best if best in SURFACES else 'Hard'

def match_player(p, idx, idx_last):
    k = key(p['name'])
    if k in idx: return idx[k]
    lk = lastkey(p['name'])
    c = idx_last.get(lk)
    return c if c and len(c) == 1 else None

def build():
    now = datetime.now(timezone.utc); since = (now - timedelta(days=365)).strftime('%Y%m%d')
    rows_by_tour, PROF, AVG, RANKN = {}, {}, {}, {}
    for tour in TOURS:
        rows = load_matches(tour)
        if not rows: continue
        rows_by_tour[tour] = rows
        P = elo_run(rows)
        rank = {}
        f = f'{RAW}/{tour}_rankings_current.csv'
        if os.path.exists(f):
            first = open(f, encoding='utf-8').readline()
            hdr = None if 'rank' in first else ['ranking_date', 'rank', 'player', 'points']      # older Sackmann ranking files carry no header
            R = list(csv.DictReader(open(f, encoding='utf-8'), fieldnames=hdr))
            latest_d = max((r.get('ranking_date') or '') for r in R) if R else ''
            for r in R:
                if (r.get('ranking_date') or '') == latest_d and r.get('player') and r.get('rank'):
                    try: rank[r['player']] = int(float(r['rank']))
                    except ValueError: pass
        players = {}
        f = f'{RAW}/{tour}_players.csv'
        if os.path.exists(f):
            for r in csv.DictReader(open(f, encoding='utf-8')): players[r.get('player_id', '')] = dict(hand=r.get('hand', ''), ioc=r.get('ioc', ''))
        prof = profiles(rows, P, rank, players, since)
        PROF[tour] = prof; AVG[tour] = tour_avg(prof); RANKN[tour] = rank
    M, pulled = load_espn(); K, PM = load_markets()
    out = []
    cal = defaultdict(lambda: [0, 0])
    for tour, rows in rows_by_tour.items():
        for r in rows:
            if r['tourney_date'] >= since: b = min(9, int(r['_pw'] * 10)); cal[b][0] += 1; cal[b][1] += 1   # winner's pre-match p
        for r in rows:
            if r['tourney_date'] >= since: b = min(9, int((1 - r['_pw']) * 10)); cal[b][0] += 1          # loser's pre-match p
    calib = [dict(lo=b / 10, n=v[0], hit=round(v[1] / v[0], 3) if v[0] else None) for b, v in sorted(cal.items())]
    for tour in TOURS:
        prof = PROF.get(tour, {}); idx = {key(p['name']): pid for pid, p in prof.items()}
        idx_last = defaultdict(list)
        for pid, p in prof.items(): idx_last[lastkey(p['name'])].append(pid)
        idx_last = {k: v for k, v in idx_last.items()}
        H2H = defaultdict(lambda: [0, 0])
        for r in rows_by_tour.get(tour, []): H2H[(r['winner_id'], r['loser_id'])][0] += 1; H2H[(r['loser_id'], r['winner_id'])][1] += 1
        for m in M:
            if m['tour'] != tour or m['status'] not in ('STATUS_SCHEDULED', 'STATUS_IN_PROGRESS', 'STATUS_SUSPENDED', 'STATUS_DELAYED'): continue
            s = surface_for(m, rows_by_tour); a = match_player(m['p1'], idx, idx_last); b = match_player(m['p2'], idx, idx_last)
            pa = prof.get(a); pb = prof.get(b)
            ea = (0.5 * pa['elo'] + 0.5 * pa['surf'][s]) if pa else None; eb = (0.5 * pb['elo'] + 0.5 * pb['surf'][s]) if pb else None
            model = 1 / (1 + 10 ** ((eb - ea) / 400)) if ea is not None and eb is not None else None
            # markets
            k1, k2 = key(m['p1']['name']), key(m['p2']['name']); l1, l2 = lastkey(m['p1']['name']), lastkey(m['p2']['name'])
            kal = None
            for (t, ev), mk in K.items():
                if t != tour: continue
                names = list(mk.keys())
                if any(k1 == n or lastkey(mk[n]['name']) == l1 for n in names) and any(k2 == n or lastkey(mk[n]['name']) == l2 for n in names):
                    q1 = next(mk[n] for n in names if k1 == n or lastkey(mk[n]['name']) == l1); q2 = next(mk[n] for n in names if k2 == n or lastkey(mk[n]['name']) == l2)
                    kal = dict(ask1=q1['ask'], bid1=q1['bid'], ask2=q2['ask'], bid2=q2['bid'], vol=q1['vol'], ev=ev); break
            poly = None
            for e in PM:
                if e['tour'] != tour: continue
                ka, kb = key(e['a']), key(e['b'])
                if (ka == k1 or lastkey(e['a']) == l1) and (kb == k2 or lastkey(e['b']) == l2): poly = dict(bid1=e['bid'], ask1=e['ask'], flip=False, liq=e['liq'], slug=e['slug']); break
                if (ka == k2 or lastkey(e['a']) == l2) and (kb == k1 or lastkey(e['b']) == l1): poly = dict(bid1=(1 - e['ask']) if e['ask'] is not None else None, ask1=(1 - e['bid']) if e['bid'] is not None else None, flip=True, liq=e['liq'], slug=e['slug']); break
            mids = []
            if kal and kal['ask1'] is not None and kal['bid2'] is not None: mids.append(((kal['ask1'] + (1 - kal['ask2'])) / 2) if kal['ask2'] is not None else kal['ask1'])
            if poly and poly['bid1'] is not None and poly['ask1'] is not None: mids.append((poly['bid1'] + poly['ask1']) / 2)
            market = sum(mids) / len(mids) if mids else None
            h = H2H.get((a, b), [0, 0]) if a and b else [0, 0]
            def side(p, pr, e):
                rec12 = pr['rec'] if pr else None; sr = pr['srec'][s] if pr else None
                return dict(id=p['id'], name=p['name'], flag=p['flag'], pid=pr['id'] if pr else '', rank=pr['rank'] if pr else '', elo=round(e) if e else '', elo_all=pr['elo'] if pr else '', elo_s=pr['surf'][s] if pr else '',
                            form=''.join('W' if x['w'] else 'L' for x in pr['last'][-10:]) if pr else '', rec12=f"{rec12['w']}-{rec12['l']}" if rec12 else '', srec12=f"{sr['w']}-{sr['l']}" if sr else '')
            out.append(dict(tour=tour, id=m['id'], tourney=m['tourney'], round=m['round'], date=m['date'], status=m['status'], city=m['city'], court=m['court'], surface=s,
                            a=side(m['p1'], pa, ea), b=side(m['p2'], pb, eb), model=round(model, 4) if model is not None else '', market=round(market, 4) if market is not None else '',
                            kal=kal, poly=poly, h2h=f'{h[0]}-{h[1]}' if a and b else '', edge=round(model - market, 4) if model is not None and market is not None else ''))
    out.sort(key=lambda m: m['date'])
    # players payload: everyone on the slate + top 150 by rank per tour (profile + last 20)
    keep = {}
    for tour, prof in PROF.items():
        ranked = sorted((p for p in prof.values() if p['rank'] != ''), key=lambda p: p['rank'])[:150]
        for p in ranked: keep[p['id']] = p
    for m in out:
        for sd in ('a', 'b'):
            pid = m[sd]['pid']
            if pid:
                for prof in PROF.values():
                    if pid in prof: keep[pid] = prof[pid]
    # H2H detail for slate pairs
    h2h_detail = {}
    for m in out:
        a, b = m['a']['pid'], m['b']['pid']
        if a and b:
            L = [dict(d=r['tourney_date'], t=r['tourney_name'], rd=r['round'], s=r['_s'], w=r['winner_name'], score=r.get('score', '')) for r in rows_by_tour[m['tour']] if {r['winner_id'], r['loser_id']} == {a, b}]
            if L: h2h_detail[a + '|' + b] = L[-8:]
    os.makedirs('data/processed', exist_ok=True)
    with open('data/processed/tennis_matches.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['tour', 'id', 'tourney', 'round', 'date', 'status', 'surface', 'p1', 'p1_rank', 'p1_elo', 'p2', 'p2_rank', 'p2_elo', 'model_p1', 'market_p1', 'edge_p1', 'h2h'])
        for m in out: w.writerow([m['tour'], m['id'], m['tourney'], m['round'], m['date'], m['status'], m['surface'], m['a']['name'], m['a']['rank'], m['a']['elo'], m['b']['name'], m['b']['rank'], m['b']['elo'], m['model'], m['market'], m['edge'], m['h2h']])
    with open('data/processed/tennis_elo.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['tour', 'player_id', 'player', 'rank', 'elo', 'elo_hard', 'elo_clay', 'elo_grass', 'matches'])
        for tour, prof in PROF.items():
            for p in sorted(prof.values(), key=lambda p: -p['elo']): w.writerow([tour, p['id'], p['name'], p['rank'], p['elo'], p['surf']['Hard'], p['surf']['Clay'], p['surf']['Grass'], p['n']])
    J = dict(matches=out, players=keep, h2h=h2h_detail, avg=AVG, calib=calib, pulled=pulled, built=datetime.now().strftime('%Y-%m-%d %H:%M'),
             seasons={t: sorted({r['tourney_date'][:4] for r in rows}) for t, rows in rows_by_tour.items()}, nmatch={t: len(r) for t, r in rows_by_tour.items()})
    open('dashboard/tennis.html', 'w', encoding='utf-8').write(page(J))
    print(f"tennis: {sum(J['nmatch'].values())} historical matches · {len(out)} on the slate ({sum(1 for m in out if m['model'] != '')} with model, {sum(1 for m in out if m['market'] != '')} with a market) · {len(keep)} player profiles · dashboard/tennis.html {os.path.getsize('dashboard/tennis.html') // 1024} KB")

# ------------------------------------------------------------------------------------------------ page
HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">"""
CSS = r"""
:root{--bg:#000;--p:#0a0a0b;--p2:#111113;--p3:#17171a;--e:#1c1c20;--e2:#2a2a30;--fg:#e7e7ea;--dim:#8a8c93;--mute:#55575f;--acc:#e8b339;--g:#3fb950;--r:#f0564a;--b:#58a6ff;--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;--sans:Inter,system-ui,-apple-system,Segoe UI,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.4 var(--sans)}a{color:inherit;text-decoration:none}button,input,select{font:inherit;color:inherit}
#hdr{display:flex;align-items:center;gap:14px;padding:0 18px;height:44px;border-bottom:1px solid var(--e);background:#050506;position:sticky;top:0;z-index:9}
.brand{font:800 14px/1 var(--mono);letter-spacing:4px}.brand i{color:var(--acc);font-style:normal;margin-right:6px}.brand small{font:500 10px var(--mono);letter-spacing:2px;color:var(--dim);margin-left:8px}
.tabs{display:flex;gap:2px;margin-left:10px}.tabs button{background:none;border:0;border-bottom:2px solid transparent;padding:0 12px;height:44px;font:600 11px var(--mono);letter-spacing:1.5px;color:var(--dim);cursor:pointer}.tabs button.on{color:var(--fg);border-bottom-color:var(--acc)}.tabs button b{color:var(--acc);font-weight:600;margin-left:5px}
.lg{display:flex;gap:2px;margin-left:auto}.lg button,.hl a{background:var(--p);border:1px solid var(--e2);padding:3px 9px;border-radius:3px;font:600 10px var(--mono);letter-spacing:1px;color:var(--dim);cursor:pointer}.lg button.on{color:#000;background:var(--acc);border-color:var(--acc)}.hl{display:flex;gap:4px}.hl a:hover{color:var(--fg)}
.meta{font:500 10px var(--mono);color:var(--mute)}.q{width:22px;height:22px;border-radius:50%;border:1px solid var(--e2);background:var(--p);color:var(--dim);font:700 11px var(--mono);cursor:pointer}
main{padding:12px 18px 60px;max-width:1600px;margin:0 auto}
.strip{display:flex;flex-wrap:wrap;border:1px solid var(--e);border-radius:6px;background:var(--p);margin-bottom:10px;overflow:hidden}.strip>div{padding:8px 14px;border-right:1px solid var(--e);min-width:120px}.strip>div:last-child{border-right:0;margin-left:auto}.strip span{display:block;font:600 9px var(--mono);letter-spacing:1.5px;color:var(--mute);text-transform:uppercase}.strip b{font:700 17px/1.2 var(--mono)}.strip small{font:500 10px var(--mono);color:var(--dim);margin-left:6px}
.ctl{display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;margin:0 0 10px;font:500 10.5px var(--mono);color:var(--dim)}.ctl input[type=search],.ctl input[type=text]{background:var(--p2);border:1px solid var(--e2);border-radius:3px;padding:4px 8px;font:500 11px var(--mono);color:var(--fg);width:240px}
.seg{display:inline-flex;border:1px solid var(--e2);border-radius:4px;overflow:hidden}.seg button{background:var(--p);border:0;border-right:1px solid var(--e2);padding:3px 9px;font:600 10px var(--mono);color:var(--dim);cursor:pointer}.seg button:last-child{border-right:0}.seg button.on{background:var(--p3);color:var(--fg)}
h2{font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin:16px 0 6px;display:flex;gap:10px;align-items:baseline}h2 b{color:var(--fg)}h2 span{font:500 10px var(--mono);letter-spacing:0;text-transform:none;color:var(--mute)}
table{border-collapse:collapse;width:100%;font-size:12px}th{font:600 9.5px var(--mono);letter-spacing:1.2px;text-transform:uppercase;color:var(--mute);text-align:left;padding:6px 8px;border-bottom:1px solid var(--e2);cursor:pointer;white-space:nowrap;position:sticky;top:44px;background:var(--bg);z-index:2}th.srt-asc::after{content:' ▲';color:var(--acc)}th.srt-desc::after{content:' ▼';color:var(--acc)}
td{padding:6px 8px;border-bottom:1px solid var(--e);vertical-align:middle;white-space:nowrap}tr.x{cursor:pointer}tr.x:hover td{background:var(--p)}tr.open td{background:var(--p)}
.mono{font-family:var(--mono)}.dim{color:var(--dim)}.mute{color:var(--mute)}.g{color:var(--g)}.r{color:var(--r)}.b{color:var(--b)}.acc{color:var(--acc)}.num{font-family:var(--mono);text-align:right}th.num{text-align:right}
.pl{display:inline-flex;align-items:center;gap:6px;font-weight:600}.pl img{width:16px;height:11px;object-fit:cover;border-radius:1px}.pl small{font:500 10px var(--mono);color:var(--dim);font-weight:500}.pl.w{color:var(--fg)}.pl.l{color:var(--dim)}
.form{font:600 10px var(--mono);letter-spacing:1px}.form i{font-style:normal}.form .W{color:var(--g)}.form .L{color:var(--mute)}
.pbar{display:inline-flex;align-items:center;gap:6px;font:600 11px var(--mono)}.pbar .t{width:72px;height:6px;background:var(--p3);border-radius:2px;overflow:hidden;display:flex}.pbar .t i{display:block;height:100%;background:var(--b)}.pbar .t i.m{background:var(--acc)}
.edge{font:700 11px var(--mono)}.src{display:inline-block;font:700 9.5px var(--mono);padding:1px 5px;border-radius:3px;border:1px solid #2b3a4f;color:var(--b);margin-left:4px}
.save{background:var(--p2);border:1px solid var(--e2);border-radius:3px;padding:2px 8px;font:600 10px var(--mono);color:var(--dim);cursor:pointer}.save:hover{color:var(--fg);border-color:var(--acc)}.save.on{color:var(--acc);border-color:var(--acc)}
.drawer td{padding:0;background:#060607}.dr{padding:10px 12px 12px 30px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;align-items:start}.dr h4{margin:0 0 6px;font:600 9.5px var(--mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--mute)}.dr table th{position:static;top:auto;padding:3px 6px}.dr td{padding:3px 6px;border-bottom:1px solid #121214}
.surf{display:inline-block;font:600 9px var(--mono);letter-spacing:1px;padding:1px 6px;border-radius:3px;text-transform:uppercase}.surf.Hard{background:#12304a;color:#8fc3ff}.surf.Clay{background:#4a2a12;color:#f0a86a}.surf.Grass{background:#143a1c;color:#8fe39a}
.empty{color:var(--mute);padding:28px 12px;border:1px dashed var(--e2);border-radius:6px;text-align:center;font:500 11px var(--mono)}
.prof{display:grid;grid-template-columns:minmax(300px,1fr) minmax(320px,1.2fr) minmax(360px,1.4fr);gap:14px;align-items:start}.card{border:1px solid var(--e);border-radius:6px;background:var(--p);padding:10px 12px}.card h4{margin:0 0 8px;font:600 9.5px var(--mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--mute)}.card table th{position:static;top:auto;padding:3px 6px}.card td{padding:3px 6px;border-bottom:1px solid #121214}
.big{font:800 22px/1.1 var(--sans)}.kv{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font:500 11px var(--mono);color:var(--dim)}.kv b{color:var(--fg);font-weight:600}
.rb{display:flex;align-items:center;gap:8px;font:500 11px var(--mono)}.rb .t{flex:1;height:6px;background:var(--p3);border-radius:2px;position:relative}.rb .t i{position:absolute;top:0;bottom:0;background:var(--b)}.rb .t em{position:absolute;top:-2px;width:2px;height:10px;background:var(--acc)}.rb .v{width:48px;text-align:right;color:var(--fg)}.rb .k{width:120px;color:var(--dim)}
.sugg{position:absolute;background:var(--p2);border:1px solid var(--e2);border-radius:4px;z-index:5;max-height:260px;overflow:auto;min-width:240px}.sugg div{padding:5px 10px;cursor:pointer;font-size:12px}.sugg div:hover{background:var(--p3)}
.foot{margin-top:22px;padding-top:10px;border-top:1px solid var(--e);color:var(--mute);font:500 10px/1.7 var(--mono)}.foot b{color:var(--dim);font-weight:500}
#how{display:none;position:fixed;inset:44px 0 0;background:rgba(0,0,0,.72);z-index:8}#how .box{max-width:720px;margin:30px auto;background:var(--p);border:1px solid var(--e2);border-radius:8px;padding:18px 22px;font-size:12.5px;line-height:1.55}#how h3{margin:0 0 10px;font:700 15px var(--sans)}#how h5{margin:14px 0 4px;font:600 10px var(--mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--acc)}#how p{margin:0 0 6px;color:#cfd0d5}
.toast{position:fixed;right:18px;bottom:18px;background:#15140f;border:1px solid var(--acc);color:var(--fg);padding:8px 12px;border-radius:6px;font:600 11px var(--mono);display:none;z-index:9}
@media (max-width:1000px){.prof,.dr{grid-template-columns:1fr}.brand small{display:none}}
"""
JS = r"""
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const M=J.matches,PL=J.players,TZ='America/Chicago';const CT=d=>new Date(d).toLocaleString('en-US',{weekday:'short',hour:'numeric',minute:'2-digit',timeZone:TZ}).replace(':00','');
const pct=p=>(100*p).toFixed(0)+'%';const pct1=p=>(100*p).toFixed(1)+'%';const am=p=>p>=0.5?String(Math.round(-100*p/(1-p))):'+'+Math.round(100*(1-p)/p);const num=v=>v===''||v==null?null:+v;
const LS=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}},SV=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};const plays=()=>LS('rainman.plays',[]);
let VIEW=location.hash.replace('#','').split('/')[0]||'matches',TOUR='all',OPEN=null,SK='date',SA=true,PID=location.hash.includes('/')?location.hash.split('/')[1]:null,Q='',ONLYM=false;
function toast(m){const t=$('#toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(()=>t.style.display='none',1800)}
const flag=f=>f?`<img src="https://a.espncdn.com/i/teamlogos/countries/500/${f}.png" alt="" onerror="this.style.display='none'">`:'';
const who=(s,cls)=>`<span class="pl ${cls||''}">${flag(s.flag)}<a href="#players/${s.pid}" data-p="${s.pid}">${esc(s.name)}</a>${s.rank!==''?`<small>#${s.rank}</small>`:''}</span>`;
const form=f=>f?`<span class="form">${[...f].map(c=>`<i class="${c}">${c}</i>`).join('')}</span>`:'<span class="mute">—</span>';
const inT=m=>TOUR==='all'||m.tour===TOUR;
function header(){const live=M.filter(inT);$('#tabs').innerHTML=`<button data-v="matches" class="${VIEW==='matches'?'on':''}">MATCHES<b>${live.length}</b></button><button data-v="players" class="${VIEW==='players'?'on':''}">PLAYERS</button>`;
  $('#lgs').innerHTML=['all','atp','wta'].map(t=>`<button data-l="${t}" class="${TOUR===t?'on':''}">${t.toUpperCase()}</button>`).join('');
  $$('#tabs button').forEach(b=>b.onclick=()=>{VIEW=b.dataset.v;location.hash=VIEW;render()});$$('#lgs button').forEach(b=>b.onclick=()=>{TOUR=b.dataset.l;OPEN=null;render()})}
function playId(m,side){return ['tennis',m.id,side.pid||side.name].join('|')}
function savePlay(m,side,p,src){const P=plays();const id=playId(m,side)+'|'+src;if(P.some(x=>x.id===id)){toast('already saved');return}const dec=1/p;
  P.push({id,league:m.tour,game:m.a.name+' vs '+m.b.name,kickoff:m.date,market:'moneyline',selection:side.name,point:'',source:src,dec:+dec.toFixed(3),american:am(p),fair:m.model!==''?(side===m.a?+m.model:1-+m.model):null,saved:new Date().toISOString(),status:'open',from:'tennis'});SV('rainman.plays',P);toast('saved · '+P.length+' plays')}
// ---------------------------------------------------------------- matches
function matches(){let rows=M.filter(inT).filter(m=>!ONLYM||m.market!=='');const V={date:m=>m.date,t:m=>m.tourney+m.round,a:m=>m.a.name,b:m=>m.b.name,model:m=>num(m.model)??-1,market:m=>num(m.market)??-1,edge:m=>Math.abs(num(m.edge)??0),rk:m=>Math.min(num(m.a.rank)??999,num(m.b.rank)??999)};
  rows.sort((x,y)=>{const a=V[SK](x),b=V[SK](y);return (a<b?-1:a>b?1:0)*(SA?1:-1)});
  const nE=rows.filter(m=>m.edge!==''&&Math.abs(+m.edge)>=0.05).length;const th=(k,l,c,t)=>`<th data-k="${k}" class="${c||''} ${SK===k?(SA?'srt-asc':'srt-desc'):''}" title="${t||''}">${l}</th>`;
  $('#view').innerHTML=`<div class="strip"><div><span>matches</span><b>${rows.length}</b><small>${[...new Set(rows.map(m=>m.tourney))].length} tournaments</small></div><div><span>with a market</span><b>${rows.filter(m=>m.market!=='').length}</b><small>Kalshi · Polymarket</small></div><div><span>model vs market ≥ 5 pts</span><b class="${nE?'acc':''}">${nE}</b><small>Elo disagrees with the price</small></div><div><span>elo history</span><b>${Object.values(J.nmatch).reduce((s,n)=>s+n,0).toLocaleString()}</b><small>matches · ${Object.values(J.seasons).flat().filter((v,i,a)=>a.indexOf(v)===i).join('–')}</small></div><div><span>pulled</span><b style="font-size:13px">${esc(J.pulled||'—')}</b><small>ESPN schedule · exchanges</small></div></div>
  <div class="ctl"><span class="seg"><button id="allm" class="${ONLYM?'':'on'}">every match</button><button id="mkt" class="${ONLYM?'on':''}">priced only</button></span><span class="mute">model = Elo (50% overall · 50% surface) from ${Object.values(J.nmatch).reduce((s,n)=>s+n,0).toLocaleString()} tour matches · market = exchange mid · click a match for H2H, form and the prices</span></div>
  ${rows.length?`<table id="mt"><thead><tr>${th('date','time')}${th('t','tournament · round')}<th>surf</th>${th('a','player')}${th('b','opponent')}<th>form · 12 mo</th>${th('rk','rank','num')}${th('model','model','num','Elo probability the first-listed player wins')}${th('market','market','num','exchange mid-point, same side')}${th('edge','Δ','num','model − market, first-listed player')}<th></th></tr></thead><tbody>${rows.map((m,i)=>{const mp=num(m.model),kp=num(m.market),e=num(m.edge);const fav=mp!=null?(mp>=0.5?'a':'b'):null;
    return `<tr class="x ${OPEN===i?'open':''}" data-i="${i}"><td class="mono dim">${CT(m.date)}${m.status!=='STATUS_SCHEDULED'?` <span class="acc">${m.status.replace('STATUS_','').toLowerCase()}</span>`:''}</td><td><b>${esc(m.tourney)}</b> <span class="dim">${esc(m.round)}</span></td><td><span class="surf ${m.surface}">${m.surface}</span></td><td>${who(m.a,fav==='a'?'w':'')}</td><td>${who(m.b,fav==='b'?'w':'')}</td><td class="mono"><span class="dim">${esc(m.a.name.split(' ').pop())}</span> ${form(m.a.form)} <span class="mute">${m.a.srec12}</span><br><span class="dim">${esc(m.b.name.split(' ').pop())}</span> ${form(m.b.form)} <span class="mute">${m.b.srec12}</span></td><td class="num dim">${m.a.rank!==''?'#'+m.a.rank:'—'} · ${m.b.rank!==''?'#'+m.b.rank:'—'}</td><td class="num">${mp==null?'<span class="mute">—</span>':`<span class="pbar"><span class="t"><i class="m" style="width:${100*mp}%"></i></span>${pct(mp)}</span>`}</td><td class="num">${kp==null?'<span class="mute">—</span>':`<span class="pbar"><span class="t"><i style="width:${100*kp}%"></i></span>${pct(kp)}</span>`}</td><td class="num">${e==null?'<span class="mute">—</span>':`<span class="edge ${Math.abs(e)>=0.05?(e>0?'g':'r'):'dim'}">${e>0?'+':''}${(100*e).toFixed(1)}</span>`}</td><td>${kp!=null?`<button class="save" data-i="${i}">save</button>`:''}</td></tr>${OPEN===i?`<tr class="drawer"><td colspan="11">${drawer(m)}</td></tr>`:''}`}).join('')}</tbody></table>`:`<div class="empty">no ${TOUR==='all'?'':TOUR.toUpperCase()+' '}singles on the schedule file${J.pulled?' pulled '+J.pulled:''} — the local loop refreshes it daily</div>`}`;
  $('#allm').onclick=()=>{ONLYM=false;matches()};$('#mkt').onclick=()=>{ONLYM=true;matches()};
  $$('#mt th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(SK===k)SA=!SA;else{SK=k;SA=!(k==='model'||k==='market'||k==='edge')}OPEN=null;matches()});
  $$('#mt tr.x').forEach(tr=>tr.onclick=e=>{if(e.target.closest('button,a'))return;const i=+tr.dataset.i;OPEN=OPEN===i?null:i;matches()});
  $$('#mt .save').forEach(b=>b.onclick=()=>{const m=rows[+b.dataset.i];const mp=num(m.model),kp=num(m.market);const side=(mp!=null?mp:0.5)>=kp?m.a:m.b;const p=side===m.a?kp:1-kp;savePlay(m,side,p,m.kal?'KAL':'POLY')});
  $$('#mt a[data-p]').forEach(a=>a.onclick=e=>{e.preventDefault();PID=a.dataset.p;VIEW='players';location.hash='players/'+PID;render()})}
function prices(m){const rows=[];const pa=(p)=>p==null?'—':`${pct1(p)} <span class="mute">${am(p)}</span>`;
  if(m.kal)rows.push(`<tr><td><span class="src">KAL</span></td><td class="num">${pa(m.kal.ask1)}<span class="mute"> ask</span></td><td class="num">${pa(m.kal.ask2)}<span class="mute"> ask</span></td><td class="num dim">${m.kal.ask1!=null&&m.kal.ask2!=null?pct1(m.kal.ask1+m.kal.ask2-1)+' hold':''}</td></tr>`);
  if(m.poly)rows.push(`<tr><td><span class="src">POLY</span></td><td class="num">${pa(m.poly.ask1)}<span class="mute"> ask</span></td><td class="num">${pa(m.poly.bid1!=null?1-m.poly.bid1:null)}<span class="mute"> ask</span></td><td class="num dim">${m.poly.ask1!=null&&m.poly.bid1!=null?pct1(m.poly.ask1-m.poly.bid1)+' spread':''} ${m.poly.liq?'· liq '+m.poly.liq:''}</td></tr>`);
  if(m.model!=='')rows.push(`<tr><td class="acc">model</td><td class="num acc">${pct1(+m.model)}</td><td class="num acc">${pct1(1-+m.model)}</td><td class="num mute">Elo ${m.a.elo} v ${m.b.elo} on ${m.surface}</td></tr>`);
  return rows.length?`<table><thead><tr><th>source</th><th class="num">${esc(m.a.name)}</th><th class="num">${esc(m.b.name)}</th><th></th></tr></thead><tbody>${rows.join('')}</tbody></table>`:'<div class="mute mono" style="font-size:10px">no exchange price yet</div>'}
function lastTable(p,n){const L=(p&&p.last||[]).slice(-n).reverse();return L.length?`<table><thead><tr><th>date</th><th>event · rd</th><th></th><th>opp</th><th>score</th></tr></thead><tbody>${L.map(x=>`<tr><td class="mono dim">${x.d.slice(0,4)}-${x.d.slice(4,6)}-${x.d.slice(6)}</td><td>${esc(x.t)} <span class="dim">${esc(x.rd)}</span> <span class="surf ${x.s}">${x.s[0]}</span></td><td class="${x.w?'g':'r'} mono"><b>${x.w?'W':'L'}</b></td><td>${esc(x.opp)}${x.opp_rank?` <span class="mute">#${x.opp_rank}</span>`:''}</td><td class="mono dim">${esc(x.score)}</td></tr>`).join('')}</tbody></table>`:'<div class="mute mono" style="font-size:10px">no tour-level history on file</div>'}
function drawer(m){const pa=PL[m.a.pid],pb=PL[m.b.pid];const h=J.h2h[m.a.pid+'|'+m.b.pid]||J.h2h[m.b.pid+'|'+m.a.pid]||[];
  return `<div class="dr"><div><h4>prices · ${esc(m.city)}${m.court?' · '+esc(m.court):''}</h4>${prices(m)}<h4 style="margin-top:10px">head to head ${m.h2h?'· '+m.h2h:''}</h4>${h.length?`<table><tbody>${h.slice().reverse().map(x=>`<tr><td class="mono dim">${x.d.slice(0,4)}</td><td>${esc(x.t)} <span class="dim">${esc(x.rd)}</span> <span class="surf ${x.s}">${x.s[0]}</span></td><td><b>${esc(x.w)}</b></td><td class="mono dim">${esc(x.score)}</td></tr>`).join('')}</tbody></table>`:'<div class="mute mono" style="font-size:10px">never met on tour (in the seasons on file)</div>'}</div>
  <div><h4>${esc(m.a.name)} · last 10 · Elo ${m.a.elo_all||'—'} / ${m.surface.toLowerCase()} ${m.a.elo_s||'—'}</h4>${lastTable(pa,10)}</div><div><h4>${esc(m.b.name)} · last 10 · Elo ${m.b.elo_all||'—'} / ${m.surface.toLowerCase()} ${m.b.elo_s||'—'}</h4>${lastTable(pb,10)}</div></div>`}
// ---------------------------------------------------------------- players
function players(){const list=Object.values(PL).filter(p=>TOUR==='all'||p.tour===TOUR);
  $('#view').innerHTML=`<div class="ctl" style="position:relative"><input type="search" id="pq" placeholder="search a player…" value="${esc(Q)}" autocomplete="off"><div id="sg" class="sugg" style="display:none;top:30px;left:0"></div><span class="mute">${list.length} profiles on file (everyone on this week's schedule + the top 150 of each tour) · Elo and records from ${Object.values(J.nmatch).reduce((s,n)=>s+n,0).toLocaleString()} tour matches</span></div><div id="pp"></div>`;
  const inp=$('#pq'),sg=$('#sg');const sugg=()=>{const q=inp.value.trim().toLowerCase();if(!q){sg.style.display='none';return}const hits=list.filter(p=>p.name.toLowerCase().includes(q)).sort((a,b)=>(num(a.rank)??9999)-(num(b.rank)??9999)).slice(0,12);sg.innerHTML=hits.map(p=>`<div data-p="${p.id}">${esc(p.name)} <span class="mute">${p.tour.toUpperCase()}${p.rank!==''?' #'+p.rank:''} · Elo ${p.elo}</span></div>`).join('')||'<div class="mute">no match</div>';sg.style.display='block';$$('#sg div[data-p]').forEach(d=>d.onclick=()=>{PID=d.dataset.p;Q=inp.value;location.hash='players/'+PID;sg.style.display='none';profile()})};
  inp.oninput=sugg;inp.onfocus=sugg;document.addEventListener('click',e=>{if(!e.target.closest('.ctl'))sg.style.display='none'});
  if(!PID){const top=list.filter(p=>p.rank!=='').sort((a,b)=>a.rank-b.rank).slice(0,40);$('#pp').innerHTML=`<h2>top of the rankings <span>click a name · sorted by rank; Elo is the model's view</span></h2><table><thead><tr><th>#</th><th>player</th><th>tour</th><th class="num">elo</th><th class="num">hard</th><th class="num">clay</th><th class="num">grass</th><th>12 mo</th><th>form</th></tr></thead><tbody>${top.map(p=>`<tr class="x" data-p="${p.id}"><td class="mono dim">${p.rank}</td><td><b>${esc(p.name)}</b> <span class="mute">${esc(p.ioc)}</span></td><td class="dim">${p.tour.toUpperCase()}</td><td class="num"><b>${p.elo}</b></td><td class="num dim">${p.surf.Hard}</td><td class="num dim">${p.surf.Clay}</td><td class="num dim">${p.surf.Grass}</td><td class="mono dim">${p.rec.w}-${p.rec.l}</td><td>${form(p.last.slice(-10).map(x=>x.w?'W':'L').join(''))}</td></tr>`).join('')}</tbody></table>`;$$('#pp tr.x').forEach(tr=>tr.onclick=()=>{PID=tr.dataset.p;location.hash='players/'+PID;profile()});return}
  profile()}
function profile(){const p=PL[PID];const el=$('#pp');if(!p){el.innerHTML='<div class="empty">no profile for that player</div>';return}const A=J.avg[p.tour]||{};const next=M.find(m=>m.a.pid===p.id||m.b.pid===p.id);
  const rate=(k,l,inv)=>{const v=p.serve[k],a=A[k];if(v==null)return '';const lo=inv?0:Math.max(0,(a||0)*0.5),hi=inv?(a||0.1)*2:Math.min(1,(a||0.5)*1.5);const x=v=>Math.max(0,Math.min(100,100*(v-lo)/(hi-lo)));return `<div class="rb"><span class="k">${l}</span><span class="t"><i style="left:0;width:${x(v)}%"></i>${a!=null?`<em style="left:${x(a)}%" title="tour average ${pct1(a)}"></em>`:''}</span><span class="v ${a!=null?((inv?v<a:v>a)?'g':'r'):''}">${pct1(v)}</span></div>`};
  el.innerHTML=`<div class="prof"><div class="card"><div class="big">${esc(p.name)}</div><div class="kv" style="margin-top:8px"><span>tour</span><b>${p.tour.toUpperCase()} ${p.ioc?'· '+esc(p.ioc):''}${p.hand?' · '+esc(p.hand)+'-handed':''}</b><span>rank</span><b>${p.rank!==''?'#'+p.rank:'unranked / not in the current file'}</b><span>elo</span><b>${p.elo} <span class="dim">overall</span></b><span></span><b><span class="surf Hard">hard</span> ${p.surf.Hard} &nbsp; <span class="surf Clay">clay</span> ${p.surf.Clay} &nbsp; <span class="surf Grass">grass</span> ${p.surf.Grass}</b><span>12 months</span><b>${p.rec.w}-${p.rec.l} <span class="dim">· hard ${p.srec.Hard.w}-${p.srec.Hard.l} · clay ${p.srec.Clay.w}-${p.srec.Clay.l} · grass ${p.srec.Grass.w}-${p.srec.Grass.l}</span></b><span>form</span><b>${form(p.last.slice(-10).map(x=>x.w?'W':'L').join(''))}</b><span>history</span><b>${p.n} <span class="dim">tour matches rated</span></b>${next?`<span>next</span><b>${esc(next.tourney)} ${esc(next.round)} · vs ${esc(next.a.pid===p.id?next.b.name:next.a.name)} · <span class="dim">${CT(next.date)}</span>${next.model!==''?` · model ${pct(next.a.pid===p.id?+next.model:1-+next.model)}`:''}</b>`:''}</div></div>
  <div class="card"><h4>serve &amp; return · last 12 months · gold tick = tour average</h4>${rate('first_in','1st serve in')}${rate('first_won','1st serve won')}${rate('second_won','2nd serve won')}${rate('ace','ace rate')}${rate('df','double faults',true)}${rate('bp_saved','break pts saved')}${rate('spw','serve pts won')}${rate('rpw','return pts won')}${rate('bp_conv','break pts converted')}</div>
  <div class="card"><h4>last 20 matches</h4>${lastTable(p,20)}</div></div>`}
function foot(){$('#foot').innerHTML=`<b>history</b> Jeff Sackmann's open ATP / WTA match files (${Object.entries(J.seasons).map(([t,s])=>t.toUpperCase()+' '+s.join('–')).join(' · ')}) · <b>schedule</b> ESPN tennis scoreboard · <b>markets</b> Kalshi KXATPMATCH / KXWTAMATCH and Polymarket ATP / WTA, exchange mid-points · <b>model</b> Elo, K = 250/(n+5)^0.4, 50/50 overall and surface · pulled ${esc(J.pulled||'—')} · built ${esc(J.built)} · information, not advice`}
function render(){header();(VIEW==='players'?players:matches)()}
$('#q').onclick=()=>{$('#how').style.display='block'};$('#how').onclick=e=>{if(e.target.id==='how')$('#how').style.display='none'};
window.addEventListener('hashchange',()=>{const [v,id]=location.hash.replace('#','').split('/');if(v&&(v!==VIEW||id!==PID)){VIEW=v;PID=id||null;render()}});
foot();render();
"""

def page(J):
    cal = ''.join(f"<tr><td class='mono dim'>{int(c['lo']*100)}–{int(c['lo']*100)+10}%</td><td class='num'>{c['n']}</td><td class='num'>{'' if c['hit'] is None else str(round(100*c['hit']))+'%'}</td></tr>" for c in J['calib'])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · Tennis</title>{HEAD}<style>{CSS}</style></head><body>
<div id="hdr"><a class="brand" href="index.html"><i>◍</i>RAINMAN<small>TENNIS</small></a><div class="tabs" id="tabs"></div><div class="lg" id="lgs"></div><span class="hl"><a href="index.html">all sports</a><a href="arb.html">arb engine</a><a href="social.html">social</a></span><button class="q" id="q" title="how it works">?</button></div>
<main><div id="view"></div><div class="foot" id="foot"></div></main>
<div id="how"><div class="box"><h3>How the tennis page is built</h3>
<h5>History</h5><p>Every tour-level singles match from Jeff Sackmann's open ATP and WTA files for the seasons on file, with serve statistics, rankings and surface.</p>
<h5>Model</h5><p>Elo, updated match by match in date order: K = 250 / (matches + 5)^0.4 so new players move fast and established ones slowly; Grand Slams weigh 1.1×, Challengers / ITF-level rows 0.8×. One overall rating and one per surface. A match-up probability uses the 50/50 blend of overall and surface Elo. Calibration over the last 12 months (pre-match probability bucket → actual win rate):</p>
<table style="max-width:360px"><thead><tr><th>bucket</th><th class="num">n</th><th class="num">won</th></tr></thead><tbody>{cal}</tbody></table>
<h5>Market</h5><p>Kalshi (one YES market per player; the ask is the price to buy) and Polymarket (one moneyline market per match). Market = the average of the exchange mid-points for the first-listed player. Δ = model − market: positive means Elo likes the first player more than the exchanges do. 5 points or more is worth a look; Elo knows nothing about injuries, fatigue or a retirement risk, so check the news before you act.</p>
<h5>Form and records</h5><p>Form = the last ten tour matches, newest on the right; 12-month records overall and on the match surface; serve and return rates are the player's last 12 months against the tour average (gold tick).</p></div></div>
<div id="toast" class="toast"></div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script><script>{JS}</script></body></html>"""

if __name__ == '__main__':
    build()
