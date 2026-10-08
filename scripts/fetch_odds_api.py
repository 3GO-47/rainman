"""Priced lines from every US book via The Odds API (https://the-odds-api.com), pulled on a cadence instead of a clock.

Setup (once): put a key in .env at the repo root — scripts\\local\\set_key.ps1 writes it:   ODDS_API_KEY=...
(.env is git-ignored; the key never reaches the repo or the site.)

What is pulled (per league, PLAN below): moneyline + spread + total for the whole league in one call (3 credits), and the MAIN
player-prop markets per game (1 credit per market per game). No alternate lines unless PLAN[lg]['alts'] is on.
When it is pulled (CADENCE below, state in notes/odds_state.json):
  game lines  — every LINES_H hours while the league has games in the next 8 days, plus a pregame snapshot inside PREGAME_H
  player props — first pull once a game is within PROPS_OPEN_D days of kickoff (when books post them), then every PROPS_H hours,
                 plus one pregame snapshot inside PREGAME_H; never after kickoff.
Every call's real cost comes back in the x-requests-last header and is written to notes/odds_usage.log, so the spend is measured,
not estimated. Cost = markets × regions per request (one region, "us").

Usage: python3 scripts/fetch_odds_api.py              # whatever is due (what loop.py runs)
       python3 scripts/fetch_odds_api.py --force      # ignore the cadence, pull everything for the active leagues now
       python3 scripts/fetch_odds_api.py --leagues nfl --dry   # show what would be pulled and the credit cost, pull nothing
Writes data/raw/markets/oddsapi_current.csv  (league, home, away, commence, book, market, side, point, price, updated) → build_arb.py
       data/raw/odds_api/props_current.csv    (league, home, away, commence, player, market, book, side, line, price, event, updated) → build_arb.py, build_bets.py
Both are merged snapshots: a pull replaces that game's rows, games that have kicked off are dropped.
"""
import os, sys, csv, glob, json, datetime, urllib.request, urllib.parse
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
UTC = datetime.timezone.utc
NOW = datetime.datetime.now(UTC)
SPORT = {'nfl': 'americanfootball_nfl', 'cfb': 'americanfootball_ncaaf', 'nba': 'basketball_nba', 'wnba': 'basketball_wnba', 'nhl': 'icehockey_nhl', 'mlb': 'baseball_mlb', 'ncaab': 'basketball_ncaab'}
BOOKS = 'fanduel,draftkings,betmgm,caesars,fanatics,espnbet,betrivers,bet365'
MAIN = {'player_pass_yds': 'pass_yds', 'player_pass_tds': 'pass_td', 'player_pass_completions': 'completions', 'player_pass_attempts': 'pass_att',
        'player_rush_yds': 'rush_yds', 'player_rush_attempts': 'rush_att', 'player_receptions': 'receptions', 'player_reception_yds': 'rec_yds', 'player_anytime_td': 'anytime_td'}
ALT = {'player_pass_yds_alternate': 'pass_yds', 'player_pass_tds_alternate': 'pass_td', 'player_rush_yds_alternate': 'rush_yds', 'player_reception_yds_alternate': 'rec_yds',
       'player_receptions_alternate': 'receptions', 'player_rush_attempts_alternate': 'rush_att'}
# ---- the plan: which leagues, which markets, no alternates (Josh, 2026-10-08: CFB never; NFL main lines only to start)
PLAN = {'nfl': dict(lines=True, props=MAIN, alts=False),
        'cfb': dict(lines=True, props={k: v for k, v in MAIN.items() if k in ('player_pass_yds', 'player_pass_tds', 'player_rush_yds', 'player_reception_yds', 'player_receptions', 'player_anytime_td')}, alts=False)}
CADENCE = dict(LINES_H=20, PROPS_OPEN_D={'nfl': 5, 'cfb': 3}, PROPS_H=30, PREGAME_H=6, PREGAME_GAP_H=4)
RESERVE = 40          # stop pulling props when the plan has fewer credits than this left (lines, 3 credits, still run)
STATE = 'notes/odds_state.json'; USAGE = 'notes/odds_usage.log'
LINES_F = 'data/raw/markets/oddsapi_current.csv'; PROPS_F = 'data/raw/odds_api/props_current.csv'
LINES_COLS = ['league', 'home', 'away', 'commence', 'book', 'market', 'side', 'point', 'price', 'updated']
HIST_L = 'data/raw/odds_api/lines_history.csv'; HIST_P = 'data/raw/odds_api/props_history.csv'   # one consensus row per market per pull → line movement
PROPS_COLS = ['league', 'home', 'away', 'commence', 'player', 'market', 'book', 'side', 'line', 'price', 'event', 'updated']

def key():
    k = os.environ.get('ODDS_API_KEY')
    if not k and os.path.exists('.env'):
        for line in open('.env'):
            if line.strip().startswith('ODDS_API_KEY='): k = line.split('=', 1)[1].strip().strip('"').strip("'")
    if not k: sys.exit('ODDS_API_KEY missing — see the setup note at the top of this file')
    return k

def get(sport, path, what, **params):
    params['apiKey'] = key()
    url = f'https://api.the-odds-api.com/v4/sports/{sport}{path}?{urllib.parse.urlencode(params)}'
    with urllib.request.urlopen(url, timeout=30) as r:
        h = r.headers; data = json.loads(r.read())
    last, used, left = h.get('x-requests-last', '?'), h.get('x-requests-used', '?'), h.get('x-requests-remaining', '?')
    with open(USAGE, 'a', encoding='utf-8') as f: f.write(f'{NOW.strftime("%Y-%m-%dT%H:%MZ")}\t{what}\tcost={last}\tused={used}\tleft={left}\n')
    return data, left

def slate():
    files = sorted(glob.glob('data/raw/slate_all_*.txt')); names, games = {}, []
    if not files: return names, games
    for line in open(files[-1], encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 26 or p[22] == '1': continue
        names.setdefault(p[1], {})[p[7]] = p[6]; names[p[1]][p[13]] = p[12]
        games.append(dict(lg=p[1], id=p[2], date=p[3], away=p[6], home=p[12]))
    return names, games

def load_state():
    try: return json.load(open(STATE))
    except Exception: return {}
def parse_ts(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')) if s else None
def hours_since(s): return 1e9 if not s else (NOW - parse_ts(s)).total_seconds() / 3600
def read_csv(path, cols):
    if not os.path.exists(path): return []
    return [r for r in csv.DictReader(open(path, encoding='utf-8'))]
def write_csv(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def _imp(price):
    a = float(price); return 100 / (a + 100) if a > 0 else -a / (-a + 100)

def _median(v): v = sorted(v); n = len(v); return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2

def snapshot(lines_rows, props_rows, pulled_lg, pulled_events):
    """Append one consensus row per game-market (and per player-stat) for what this run pulled: the line-movement history.
    lines: p = home win / home cover / Over probability, de-vigged per book then averaged; point = median book line (home handicap, total).
    props: line = median book line; p = de-vigged P(Over) averaged over books quoting both sides (anytime TD: mean implied YES, not de-vigged)."""
    ts = NOW.strftime('%Y-%m-%dT%H:%MZ')
    def append(path, cols, rows):
        if not rows: return
        new = not os.path.exists(path); os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if new: w.writeheader()
            w.writerows(rows)
    out = []; by = {}
    for r in lines_rows:
        if r['league'] not in pulled_lg: continue
        by.setdefault((r['league'], r['away'], r['home'], r['commence'], r['market'], r['book']), []).append(r)
    agg = {}
    for (lg, a, h, c, m, b), R in by.items():
        if m == 'h2h':
            ph = next((_imp(x['price']) for x in R if x['side'] == h), None); pa = next((_imp(x['price']) for x in R if x['side'] == a), None)
            if ph is None or pa is None: continue
            agg.setdefault((lg, a, h, c, m), []).append(('', ph / (ph + pa)))
        elif m == 'spreads':
            hr = next((x for x in R if x['side'] == h), None); ar = next((x for x in R if x['side'] == a), None)
            if not hr or not ar or hr['point'] == '': continue
            ph, pa = _imp(hr['price']), _imp(ar['price']); agg.setdefault((lg, a, h, c, m), []).append((float(hr['point']), ph / (ph + pa)))
        elif m == 'totals':
            o = next((x for x in R if x['side'] == 'Over'), None); u = next((x for x in R if x['side'] == 'Under'), None)
            if not o or not u or o['point'] == '': continue
            po, pu = _imp(o['price']), _imp(u['price']); agg.setdefault((lg, a, h, c, m), []).append((float(o['point']), po / (po + pu)))
    for (lg, a, h, c, m), v in agg.items():
        out.append(dict(ts=ts, league=lg, away=a, home=h, commence=c, market={'h2h': 'moneyline', 'spreads': 'spread', 'totals': 'total'}[m], point='' if m == 'h2h' else _median([x[0] for x in v]), p=round(sum(x[1] for x in v) / len(v), 4), n_books=len(v)))
    append(HIST_L, ['ts', 'league', 'away', 'home', 'commence', 'market', 'point', 'p', 'n_books'], out)
    outp = []; byp = {}
    for r in props_rows:
        if r['event'] not in pulled_events: continue
        byp.setdefault((r['league'], r['away'], r['home'], r['commence'], r['player'], r['market'], r['book']), []).append(r)
    aggp = {}
    for (lg, a, h, c, pl, st, b), R in byp.items():
        if st == 'anytime_td':
            y = next((x for x in R if x['side'] == 'Yes'), None)
            if y: aggp.setdefault((lg, a, h, c, pl, st), []).append((0.5, _imp(y['price'])))
            continue
        o = next((x for x in R if x['side'] == 'Over' and x['line'] != ''), None); u = next((x for x in R if x['side'] == 'Under' and x['line'] == (o['line'] if o else None)), None)
        if not o: continue
        po = _imp(o['price']); pu = _imp(u['price']) if u else None
        aggp.setdefault((lg, a, h, c, pl, st), []).append((float(o['line']), po / (po + pu) if pu else None))
    for (lg, a, h, c, pl, st), v in aggp.items():
        ps = [x[1] for x in v if x[1] is not None]
        outp.append(dict(ts=ts, league=lg, away=a, home=h, commence=c, player=pl, stat=st, line=_median([x[0] for x in v]), p=round(sum(ps) / len(ps), 4) if ps else '', n_books=len(v)))
    append(HIST_P, ['ts', 'league', 'away', 'home', 'commence', 'player', 'stat', 'line', 'p', 'n_books'], outp)
    return len(out), len(outp)

def main():
    force, dry = '--force' in sys.argv, '--dry' in sys.argv
    only = sys.argv[sys.argv.index('--leagues') + 1].split(',') if '--leagues' in sys.argv else None
    names, games = slate(); st = load_state(); st.setdefault('lines', {}); st.setdefault('props', {})
    cutoff = NOW.isoformat()
    lines_rows = [r for r in read_csv(LINES_F, LINES_COLS) if r['commence'] > cutoff]      # drop games that have started
    props_rows = [r for r in read_csv(PROPS_F, PROPS_COLS) if r['commence'] > cutoff]
    left = '?'; plan_cost = 0; did = []; stop = False; pulled_lg = set(); pulled_events = set()
    def low(): return str(left).isdigit() and int(left) < RESERVE
    for lg, plan in PLAN.items():
        if only and lg not in only: continue
        sport = SPORT[lg]; tm = names.get(lg, {})
        upcoming = [g for g in games if g['lg'] == lg and NOW.isoformat() < g['date'].replace('Z', '+00:00') <= (NOW + datetime.timedelta(days=8)).isoformat()]
        if not upcoming: continue
        kick = lambda g: parse_ts(g['date'])
        # ---------- game lines: one call per league
        soon = any((kick(g) - NOW).total_seconds() / 3600 <= CADENCE['PREGAME_H'] for g in upcoming)
        age = hours_since(st['lines'].get(lg))
        due = force or age >= CADENCE['LINES_H'] or (soon and age >= CADENCE['PREGAME_GAP_H'])
        if plan['lines'] and due:
            plan_cost += 3
            if not dry:
                try:
                    data, left = get(sport, '/odds', f'{lg} lines', regions='us', markets='h2h,spreads,totals', bookmakers=BOOKS, oddsFormat='american')
                    keys = {(tm.get(e['home_team'], e['home_team']), tm.get(e['away_team'], e['away_team'])) for e in data}
                    lines_rows = [r for r in lines_rows if not (r['league'] == lg and (r['home'], r['away']) in keys)]
                    for e in data:
                        if e['commence_time'] <= cutoff: continue                    # in-play: the API returns live prices for started games — not ours
                        h, a = tm.get(e['home_team'], e['home_team']), tm.get(e['away_team'], e['away_team'])
                        for b in e.get('bookmakers', []):
                            for m in b['markets']:
                                for o in m['outcomes']:
                                    lines_rows.append(dict(league=lg, home=h, away=a, commence=e['commence_time'], book=b['key'], market=m['key'], side=tm.get(o['name'], o['name']), point=o.get('point', ''), price=o['price'], updated=m.get('last_update', '')))
                    st['lines'][lg] = NOW.isoformat(); did.append(f'{lg} lines ({len(data)} games)'); pulled_lg.add(lg)
                except Exception as ex: print(f'  {lg} lines: {ex}')
            else: did.append(f'{lg} lines (3 credits)')
        # ---------- props: one call per game, on the game's own clock
        markets = dict(plan['props']); markets.update(ALT if plan['alts'] else {})
        if not markets: continue
        events = None
        for g in sorted(upcoming, key=lambda g: g['date']):                # nearest kickoffs first when credits run short
            if stop: break
            hrs = (kick(g) - NOW).total_seconds() / 3600
            if hrs > CADENCE['PROPS_OPEN_D'][lg] * 24: continue
            k = f"{lg}|{g['away']}@{g['home']}|{g['date'][:10]}"; last = hours_since(st['props'].get(k, {}).get('at'))
            due = force or last >= CADENCE['PROPS_H'] or (hrs <= CADENCE['PREGAME_H'] and last >= CADENCE['PREGAME_GAP_H'] and not st['props'].get(k, {}).get('snapped'))
            if not due: continue
            plan_cost += len(markets)
            if dry: did.append(f'{k} props ({len(markets)} credits)'); continue
            if events is None:
                try: events, left = get(sport, '/events', f'{lg} events')
                except Exception as ex: print(f'  {lg} events: {ex}'); break
            ev = next((e for e in events if tm.get(e['home_team'], e['home_team']) == g['home'] and tm.get(e['away_team'], e['away_team']) == g['away']), None)
            if not ev: continue
            if low(): print(f'  credits left {left} < reserve {RESERVE} — props paused until the plan renews'); stop = True; break
            try: data, left = get(sport, f"/events/{ev['id']}/odds", f'{k} props', regions='us', markets=','.join(markets), bookmakers=BOOKS, oddsFormat='american')
            except Exception as ex: print(f'  {k} props: {ex}'); continue
            props_rows = [r for r in props_rows if r['event'] != ev['id']]
            n = 0
            for b in data.get('bookmakers', []):
                for m in b['markets']:
                    for o in m['outcomes']:
                        side = o['name']; player = o.get('description', '')
                        if m['key'] == 'player_anytime_td': side, player = (o['name'] if o['name'] in ('Yes', 'No') else 'Yes'), o.get('description', o['name'])
                        props_rows.append(dict(league=lg, home=g['home'], away=g['away'], commence=ev['commence_time'], player=player, market=markets[m['key']], book=b['key'], side=side, line=o.get('point', ''), price=o['price'], event=ev['id'], updated=m.get('last_update', ''))); n += 1
            st['props'][k] = dict(at=NOW.isoformat(), snapped=hrs <= CADENCE['PREGAME_H'], n=n); did.append(f'{k} props ({n})'); pulled_events.add(ev['id'])
    if dry:
        print(f'dry run — would spend about {plan_cost} credits:\n  ' + '\n  '.join(did) if did else 'dry run — nothing due'); return 0
    write_csv(LINES_F, LINES_COLS, lines_rows); write_csv(PROPS_F, PROPS_COLS, props_rows)
    hl, hp = snapshot(lines_rows, props_rows, pulled_lg, pulled_events)
    st['last_run'] = NOW.isoformat(); json.dump(st, open(STATE, 'w'), indent=1)
    print(f'odds_api: {len(did)} pulls · {len(lines_rows)} line rows · {len(props_rows)} prop rows on file · history +{hl}/+{hp} · credits left {left}' + (f' · {"; ".join(did[:6])}{" …" if len(did) > 6 else ""}' if did else ' · nothing due'))
    return len(did)

if __name__ == '__main__':
    main()
