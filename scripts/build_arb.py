"""Arb Engine — quantify every line across every source, then find arbitrage and +EV.

Inputs (latest file of each in data/raw/markets/, see scripts/local/pull_markets.py):
  draftkings_<date>.txt  D|espnEventId|homeSpread|overUnder|homeML|awayML|homeSpreadOdds|awaySpreadOdds|overOdds|underOdds[|league]
  kalshi_<date>.txt      K2|series|ticker|event_ticker|title|yes_sub_title|strike|strike_type|yes_bid|yes_ask|last|volume|close_time
  polymarket_<date>.txt  P|eventSlug|kind|endDateUTC|marketId|question|sportsMarketType|line|outcomes|outcomePrices|bestBid|bestAsk|liquidity|volume
  data/raw/slate_all_<date>.txt (ESPN scoreboard) for the event universe.

Outputs: data/processed/lines_all.csv (one row per source × event × market × selection, decimal / implied / fee-adjusted),
         data/processed/arb_board.csv (one row per two-way market: best price per side, fair probability, edge),
         data/processed/arb_opps.csv, data/processed/ev_opps.csv, dashboard/arb.html.

Price conventions: American → decimal; exchanges: buying YES costs the ask, buying the other side costs (1 − bid); Kalshi taker fee
0.07·P·(1−P) per contract is added to the cost (effective price), Polymarket fee 0 (configurable). Fair probability per two-way market =
the average of each source's de-vigged (proportionally normalized) two-sided probabilities, exchanges using bid/ask mid-points.
Arb = 1/best_dec(side A) + 1/best_dec(side B) < 1. EV% = fair · dec − 1 at that source's price.
"""
import math, csv, glob, json, os, re
from datetime import datetime, timezone
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
KALSHI_FEE, POLY_FEE = 0.07, 0.0
BOOKS = {'fanduel': ('FD', 'FanDuel'), 'draftkings': ('DK', 'DraftKings'), 'betmgm': ('MGM', 'BetMGM'), 'caesars': ('CZR', 'Caesars'), 'fanatics': ('FAN', 'Fanatics'),
         'espnbet': ('ESPN', 'ESPN BET'), 'betrivers': ('BR', 'BetRivers'), 'bet365': ('B365', 'bet365'), 'pinnacle': ('PIN', 'Pinnacle'), 'bovada': ('BOV', 'Bovada')}
SRC = {'DK': 'DraftKings', 'KAL': 'Kalshi', 'POLY': 'Polymarket', **{c: n for c, n in BOOKS.values()}}
KIND = {s: ('exchange' if s in ('KAL', 'POLY') else 'book') for s in SRC}
KAL_ABBR = {'JAC': 'JAX', 'WAS': 'WSH', 'LAR': 'LAR', 'LAC': 'LAC', 'LV': 'LV'}          # Kalshi event abbreviations → ESPN slate abbreviations
KAL_CITY = {'Washington': 'WSH', 'San Francisco': 'SF', 'Green Bay': 'GB', 'Dallas': 'DAL', 'Los Angeles C': 'LAC', 'Kansas City': 'KC', 'Las Vegas': 'LV', 'Buffalo': 'BUF',
            'Los Angeles R': 'LAR', 'Arizona': 'ARI', 'Tampa Bay': 'TB', 'Pittsburgh': 'PIT', 'Philadelphia': 'PHI', 'Carolina': 'CAR', 'New York G': 'NYG', 'New Orleans': 'NO',
            'New York J': 'NYJ', 'New England': 'NE', 'Tennessee': 'TEN', 'Indianapolis': 'IND', 'Cleveland': 'CLE', 'Baltimore': 'BAL', 'Chicago': 'CHI', 'Atlanta': 'ATL',
            'Jacksonville': 'JAX', 'Houston': 'HOU', 'Seattle': 'SEA', 'Denver': 'DEN', 'Detroit': 'DET', 'Minnesota': 'MIN', 'Miami': 'MIA', 'Cincinnati': 'CIN'}
MON = {m: i for i, m in enumerate(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'], 1)}

def latest(prefix):
    f = sorted(glob.glob(f'data/raw/markets/{prefix}_*.txt'))
    return f[-1] if f else None
def asof(path):
    m = re.search(r'(\d{4}-\d{2}-\d{2})', path or '')
    return m.group(1) if m else ''
def dec_from_american(a):
    a = float(a); return 1 + a / 100 if a > 0 else 1 + 100 / -a
def american(dec):
    return f'+{round((dec - 1) * 100)}' if dec >= 2 else f'{round(-100 / (dec - 1))}'

def slate():
    files = sorted(glob.glob('data/raw/slate_all_*.txt'))
    G = {}
    for line in open(files[-1], encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 26 or p[22] == '1': continue
        G[p[2]] = dict(lg=p[1], id=p[2], date=p[3], away=p[6], home=p[12], away_name=p[7], home_name=p[13], away_logo=p[9], home_logo=p[15], tv=p[18])
    return G

POLY_STAT = {'receiving_yards': 'rec_yds', 'receptions': 'receptions', 'rushing_yards': 'rush_yds', 'passing_yards': 'pass_yds', 'passing_touchdowns': 'pass_td',
             'anytime_touchdowns': 'anytime_td', 'passing_attempts': 'pass_att', 'passing_completions': 'completions', 'rushing_attempts': 'rush_att'}

def game_by_date(G, lg, a, h, date):
    """Fallback when an exchange abbreviation differs from ESPN's (WAS/WSH, JAX/JAC…): same league, same UTC date ±1, one team matches."""
    for g in G.values():
        if g['lg'] != lg or abs((datetime.fromisoformat(g['date'][:10]) - datetime.fromisoformat(date)).days) > 1: continue
        if a in (g['away'], g['home']) or h in (g['away'], g['home']): return g
    return None

def find_game(G, lg, away, home, date=None):
    """Match a slate game by league + team abbreviations (+ UTC date when known)."""
    for g in G.values():
        if g['lg'] != lg: continue
        if {g['away'], g['home']} == {away, home}:
            if date and g['date'][:10] != date and abs((datetime.fromisoformat(g['date'][:10]) - datetime.fromisoformat(date)).days) > 1: continue
            return g
    return None

# ------------------------------------------------------------------------------------------------ sources → normalized rows
def row(g, market, sel, point, src, dec, cost=None, asof_='', note=''):
    """cost = probability-like price actually paid on an exchange (before fee); for books cost = 1/dec."""
    cost = 1 / dec if cost is None else cost
    fee = KALSHI_FEE * cost * (1 - cost) if src == 'KAL' else POLY_FEE * cost * (1 - cost)
    eff = cost + fee
    return dict(league=g['lg'], event_id=g['id'], kickoff=g['date'], away=g['away'], home=g['home'], market=market, selection=sel, point=point,
                source=src, kind=KIND[src], dec=round(dec, 4), american=american(dec), implied=round(cost, 4), fee=round(fee, 4), eff_dec=round(1 / eff, 4), eff_implied=round(eff, 4), asof=asof_, note=note)

def load_dk(G):
    f = latest('draftkings'); rows = []
    if not f: return rows
    a_ = asof(f)
    for line in open(f, encoding='utf-8'):
        if not line.startswith('D|'): continue
        p = line.rstrip('\n').split('|'); g = G.get(p[1])
        if not g: continue
        hs, ou, hml, aml, hso, aso, oo, uo = p[2:10]
        if hml and aml:
            rows.append(row(g, 'moneyline', g['home'], '', 'DK', dec_from_american(hml), asof_=a_)); rows.append(row(g, 'moneyline', g['away'], '', 'DK', dec_from_american(aml), asof_=a_))
        if hs and hso and aso:
            rows.append(row(g, 'spread', g['home'], float(hs), 'DK', dec_from_american(hso), asof_=a_)); rows.append(row(g, 'spread', g['away'], -float(hs), 'DK', dec_from_american(aso), asof_=a_))
        if ou and oo and uo:
            rows.append(row(g, 'total', 'Over', float(ou), 'DK', dec_from_american(oo), asof_=a_)); rows.append(row(g, 'total', 'Under', float(ou), 'DK', dec_from_american(uo), asof_=a_))
    return rows

def kal_event(ev):
    """KXNFLGAME-26OCT08TBDAL → (league, date, away, home). Kalshi writes AWAYHOME in the event code."""
    m = re.match(r'KX([A-Z]+?)(GAME|SPREAD|TOTAL)-(\d\d)([A-Z]{3})(\d\d)([A-Z]+)$', ev)
    if not m: return None
    lg = {'NFL': 'nfl', 'NHL': 'nhl', 'NBA': 'nba', 'MLB': 'mlb', 'NCAAF': 'cfb', 'WNBA': 'wnba'}.get(m.group(1))
    date = f'20{m.group(3)}-{MON[m.group(4)]:02d}-{m.group(5)}'
    return lg, date, m.group(6)

def split_teams(code, teams):
    """'TBDAL' → ('TB','DAL') using the league's abbreviation set (Kalshi: JAC, WAS, …)."""
    norm = lambda x: KAL_ABBR.get(x, x)
    for i in range(2, len(code) - 1):
        a, h = code[:i], code[i:]
        if norm(a) in teams and norm(h) in teams: return norm(a), norm(h)
    return None

def load_kalshi(G):
    f = latest('kalshi'); rows = []
    if not f: return rows
    a_ = asof(f); teams = {}
    for g in G.values(): teams.setdefault(g['lg'], set()).update([g['away'], g['home']])
    for line in open(f, encoding='utf-8'):
        if not line.startswith('K2|'): continue
        p = line.rstrip('\n').split('|')
        series, ticker, ev, title, sub, strike, stype, bid, ask = p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]
        ke = kal_event(ev)
        if not ke or not bid or not ask: continue
        lg, date, code = ke; tt = split_teams(code, teams.get(lg, set()))
        if not tt: continue
        g = find_game(G, lg, tt[0], tt[1], date)
        if not g: continue
        bid, ask = float(bid), float(ask); mid = (bid + ask) / 2
        if series.endswith('GAME'):
            team = KAL_CITY.get(sub.strip()) or (ticker.split('-')[-1] if ticker.split('-')[-1] in teams.get(lg, set()) else KAL_ABBR.get(ticker.split('-')[-1]))
            if team not in (g['away'], g['home']): continue
            rows.append(row(g, 'moneyline', team, '', 'KAL', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}')); rows[-1]['liq'] = p[11]
        elif series.endswith('SPREAD'):
            m = re.match(r'([A-Z]{2,3}) .*wins by over ([\d.]+)', sub)
            if not m: continue
            team = KAL_ABBR.get(m.group(1), m.group(1)); pt = float(m.group(2))
            if team not in (g['away'], g['home']): continue
            other = g['home'] if team == g['away'] else g['away']
            rows.append(row(g, 'spread', team, -pt, 'KAL', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            rows.append(row(g, 'spread', other, pt, 'KAL', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}')); rows[-1]['liq'] = rows[-2]['liq'] = p[11]
        elif series.endswith('TOTAL'):
            m = re.search(r'([\d.]+)', strike or sub)
            if not m: continue
            pt = float(m.group(1))
            rows.append(row(g, 'total', 'Over', pt, 'KAL', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            rows.append(row(g, 'total', 'Under', pt, 'KAL', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}')); rows[-1]['liq'] = rows[-2]['liq'] = p[11]
    return rows

def load_oddsapi(G):
    """The Odds API game lines (FanDuel, BetMGM, Caesars, … and DraftKings) → rows; when it carries DraftKings, the ESPN DK rows are replaced by it."""
    f = ['data/raw/markets/oddsapi_current.csv'] if os.path.exists('data/raw/markets/oddsapi_current.csv') else sorted(glob.glob('data/raw/markets/oddsapi_*.csv')); rows = []
    if not f: return rows, False
    f = f[-1]; a_ = asof(f) or datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d'); has_dk = False
    by_lg = {}
    for g in G.values(): by_lg.setdefault(g['lg'], []).append(g)
    for r in csv.DictReader(open(f, encoding='utf-8')):
        code = BOOKS.get(r['book'], (r['book'].upper()[:4], r['book']))[0]
        if code not in SRC: SRC[code] = BOOKS.get(r['book'], (code, r['book']))[1]; KIND[code] = 'book'
        g = find_game(G, r['league'], r['away'], r['home'], r['commence'][:10])
        if not g: continue
        try: dec = dec_from_american(r['price'])
        except ValueError: continue
        if code == 'DK': has_dk = True
        if r['market'] == 'h2h':
            if r['side'] in (g['away'], g['home']): rows.append(row(g, 'moneyline', r['side'], '', code, dec, asof_=a_))
        elif r['market'] == 'spreads':
            if r['side'] in (g['away'], g['home']) and r['point'] != '': rows.append(row(g, 'spread', r['side'], float(r['point']), code, dec, asof_=a_))
        elif r['market'] == 'totals':
            if r['side'] in ('Over', 'Under') and r['point'] != '': rows.append(row(g, 'total', r['side'], float(r['point']), code, dec, asof_=a_))
    return rows, has_dk

def load_props(G):
    """The Odds API main player props (props_current.csv): Over/Under per player, stat and line at every book → market 'prop'."""
    f = 'data/raw/odds_api/props_current.csv'; rows = []
    if not os.path.exists(f): return rows
    a_ = datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d')
    for r in csv.DictReader(open(f, encoding='utf-8')):
        if r['market'] == 'anytime_td':
            if r['side'] not in ('Yes', 'No'): continue
            r = dict(r, line='0.5')
        elif r['side'] not in ('Over', 'Under') or r['line'] == '': continue
        code = BOOKS.get(r['book'], (r['book'].upper()[:4], r['book']))[0]
        if code not in SRC: SRC[code] = BOOKS.get(r['book'], (code, r['book']))[1]; KIND[code] = 'book'
        g = find_game(G, r['league'], r['away'], r['home'], r['commence'][:10])
        if not g: continue
        try: x = row(g, 'prop', r['side'], float(r['line']), code, dec_from_american(r['price']), asof_=a_)
        except ValueError: continue
        x['player'] = r['player']; x['stat'] = r['market']; rows.append(x)
    return rows

def load_poly(G):
    f = latest('polymarket'); rows = []
    if not f: return rows
    a_ = asof(f)
    nick = {}
    for g in G.values():
        nick[(g['lg'], g['away_name'].split()[-1])] = g['away']; nick[(g['lg'], g['home_name'].split()[-1])] = g['home']
    for line in open(f, encoding='utf-8'):
        if not line.startswith('P|'): continue
        p = line.rstrip('\n').split('|')
        add = lambda x: (x.__setitem__('liq', p[12] if len(p) > 12 else ''), rows.append(x))
        slug, kind, end, q, t, ln, outs, prices, bid, ask = p[1], p[2], p[3], p[5], p[6], p[7], p[8], p[9], p[10], p[11]
        m = re.match(r'([a-z]+)-([a-z0-9]+)-([a-z0-9]+)-(\d{4}-\d{2}-\d{2})', slug)
        if not m or kind not in ('game', 'props') or not bid or not ask: continue
        lg = m.group(1)
        outs = outs.split(','); bid, ask = float(bid), float(ask)
        g = None
        if kind == 'props':
            st = POLY_STAT.get(t)
            if not st or ':' not in q: continue
            g = find_game(G, lg, m.group(2).upper(), m.group(3).upper(), m.group(4)) or game_by_date(G, lg, m.group(2).upper(), m.group(3).upper(), m.group(4))
            if not g: continue
            player = q.split(':')[0].strip()
            if st == 'anytime_td':
                pt, sa, sb = 0.5, 'Yes', 'No'
            else:
                if not ln: continue
                pt, sa, sb = float(ln), 'Over', 'Under'
            for sel, dec, cost, note in ((sa, 1 / ask, ask, f'yes {bid:.2f}/{ask:.2f}'), (sb, 1 / (1 - bid), 1 - bid, f'no @ {1 - bid:.2f}')):
                x = row(g, 'prop', sel, pt, 'POLY', dec, cost, a_, note); x['player'] = player; x['stat'] = st; add(x)
            continue
        if t == 'moneyline':
            a_t, h_t = nick.get((lg, outs[0])), nick.get((lg, outs[1]))
            if a_t and h_t: g = find_game(G, lg, a_t, h_t, m.group(4))
            if not g: continue
            # outcome order on Polymarket is away, home
            add(row(g, 'moneyline', a_t, '', 'POLY', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            add(row(g, 'moneyline', h_t, '', 'POLY', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}'))
        elif t == 'spreads':
            fav, dog = nick.get((lg, outs[0])), nick.get((lg, outs[1]))
            if fav and dog: g = find_game(G, lg, fav, dog, m.group(4))
            if not g or not ln: continue
            pt = float(ln)
            add(row(g, 'spread', fav, pt, 'POLY', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            add(row(g, 'spread', dog, -pt, 'POLY', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}'))
        elif t == 'totals':
            mm = re.match(r'(.+?) vs\. (.+?): O/U', q)
            if not mm: continue
            a_t, h_t = nick.get((lg, mm.group(1).split()[-1])), nick.get((lg, mm.group(2).split()[-1]))
            if a_t and h_t: g = find_game(G, lg, a_t, h_t, m.group(4))
            if not g or not ln: continue
            pt = float(ln)
            add(row(g, 'total', 'Over', pt, 'POLY', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            add(row(g, 'total', 'Under', pt, 'POLY', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}'))
    return rows

# ------------------------------------------------------------------------------------------------ two-way markets, fair prices, arbs, EV
# ------------------------------------------------------------------------------------------------ the model (NFL prop model, current week)
def _norm_name(n): return re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n.lower()))

def load_model():
    """data/processed/prop_projections.csv (scripts/build_prop_model.py): per player-market projection + q10/q90 band (O/U markets) and p_yes (anytime TD)."""
    f = 'data/processed/prop_projections.csv'
    if not os.path.exists(f): return {}
    R = list(csv.DictReader(open(f, encoding='utf-8')))
    if not R: return {}
    wk = max(int(r['week']) for r in R); M = {}
    for r in R:
        if int(r['week']) != wk: continue
        M[(_norm_name(r['player']), r['market'])] = dict(proj=float(r['proj'] or 0), q10=float(r['q10']) if r['q10'] else None, q90=float(r['q90']) if r['q90'] else None, p_yes=float(r['p_yes']) if r['p_yes'] else None, n_eff=float(r['n_eff'] or 0), team=r['team'], opp=r['opp'])
    return M

def model_p(M, player, stat, line):
    """Model probability of the A side: P(Over line) from a normal fit to the q10-q90 band, or P(anytime TD)."""
    m = M.get((_norm_name(player), stat))
    if not m or m['n_eff'] < 3: return None          # slot-prior only (no real usage behind it) → no opinion
    if stat == 'anytime_td': return m['p_yes']
    if m['q10'] is None or m['q90'] is None: return None
    sd = max(1e-6, (m['q90'] - m['q10']) / 2.563); z = (m['proj'] - float(line)) / sd
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))

# ------------------------------------------------------------------------------------------------ anytime TD de-vig (books quote only YES)
def scorers_per_game():
    """Distinct offensive TD scorers per team-game this season, from the game logs (NFL and FBS)."""
    out = {}
    for f, lg in (('data/game_logs/game_logs_2026.csv', 'nfl'), ('ncaa/data/game_logs/game_logs_2026.csv', 'cfb')):
        if not os.path.exists(f): continue
        sc, games = {}, set()
        for r in csv.DictReader(open(f, encoding='utf-8')):
            k = (r['team'], r['week']); games.add(k)
            if float(r.get('rush_td') or 0) + float(r.get('rec_td') or 0) > 0: sc.setdefault(k, set()).add(r['player'])
        if games: out[lg] = sum(len(sc.get(g, ())) for g in games) / len(games)
    return out

TEAM_ALIAS = {'WAS': 'WSH', 'JAC': 'JAX', 'LA': 'LAR', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR', 'ARZ': 'ARI', 'BLT': 'BAL', 'CLV': 'CLE', 'HST': 'HOU'}
canon = lambda t: TEAM_ALIAS.get(t, t)

def player_teams():
    """name → teams, from the latest depth charts (NFL + FBS), the matchup tables and the prop model."""
    m = {}
    files = ['data/processed/matchups_current.csv', 'ncaa/data/processed/matchups_current.csv', 'data/processed/prop_projections.csv']
    for d in ('data/processed', 'ncaa/data/processed'):
        dc = sorted(glob.glob(f'{d}/depth_charts_*.csv'))
        if dc: files.append(dc[-1])
    for f in files:
        if not os.path.exists(f): continue
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r.get('player') and r.get('team'): m.setdefault(_norm_name(r['player']), set()).add(canon(r['team']))
    return m

def td_fair(rows, G):
    """Market fair P(anytime TD) per (event, player): the mean implied YES across books, scaled so a team's probabilities sum to its expected
    number of distinct scorers (season average from the game logs × team implied total / slate average). Books hold 20-40% on these; this removes it."""
    SPG = scorers_per_game(); PT = player_teams()
    tot, spr = {}, {}
    for r in rows:
        if r['source'] not in ('DK', 'FD', 'MGM', 'BR', 'ESPN', 'CZR', 'FAN', 'B365'): continue
        if r['market'] == 'total' and r['selection'] == 'Over': tot.setdefault(r['event_id'], []).append(float(r['point']))
        if r['market'] == 'spread' and r['selection'] == r['home']: spr.setdefault(r['event_id'], []).append(float(r['point']))
    med = lambda v: sorted(v)[len(v) // 2]
    imp = {}
    for ev, g in G.items():
        if ev in tot and ev in spr:
            T, S = med(tot[ev]), med(spr[ev]); imp[(ev, g['home'])] = (T - S) / 2; imp[(ev, g['away'])] = (T + S) / 2
    base = {lg: (sum(v for (e, t), v in imp.items() if G[e]['lg'] == lg) / max(1, sum(1 for (e, t) in imp if G[e]['lg'] == lg))) for lg in SPG}
    yes = {}
    for r in rows:
        if r['market'] == 'prop' and r.get('stat') == 'anytime_td' and r['selection'] == 'Yes' and KIND[r['source']] == 'book':
            yes.setdefault((r['event_id'], r['player']), []).append(float(r['implied']))
    team_of = {}
    for (ev, pl) in yes:
        g = G[ev]; cands = PT.get(_norm_name(pl), set()) & {canon(g['away']), canon(g['home'])}
        team_of[(ev, pl)] = next(iter(cands)) if len(cands) == 1 else None
    sums = {}
    for k, v in yes.items():
        if team_of[k]: team_of[k] = next(t for t in (G[k[0]]['away'], G[k[0]]['home']) if canon(t) == team_of[k]); sums[(k[0], team_of[k])] = sums.get((k[0], team_of[k]), 0) + sum(v) / len(v)
    out = {}
    for k, v in yes.items():
        t = team_of[k]; g = G[k[0]]; lg = g['lg']
        if not t or lg not in SPG or (k[0], t) not in imp or not sums.get((k[0], t)): continue
        lam = SPG[lg] * imp[(k[0], t)] / base[lg]
        out[k] = (sum(v) / len(v)) * min(1.0, lam / sums[(k[0], t)])      # only ever removes hold; a team missing players (Σ too small) is left at implied
    return out

def pair_key(r):
    """Spreads pair on the AWAY team's handicap: away +3.5 ↔ home −3.5 are the two sides of one market."""
    if r['market'] == 'moneyline': return (r['event_id'], 'moneyline', '')
    if r['market'] == 'spread': return (r['event_id'], 'spread', float(r['point']) if r['selection'] == r['away'] else -float(r['point']))
    if r['market'] == 'prop': return (r['event_id'], 'prop|' + r['stat'] + '|' + r['player'], float(r['point']))
    return (r['event_id'], 'total', float(r['point']))

def side_of(r, g):
    if r['market'] in ('total', 'prop'): return 'A' if r['selection'] in ('Over', 'Yes') else 'B'
    return 'A' if r['selection'] == g['away'] else 'B'

def hist_key(lg, away, home, date10, market, player='', stat=''):
    return f'{lg}|{away}|{home}|{date10}|{market}|{player}|{stat}'

def history(G):
    """Odds API consensus snapshots → {key: [(ts, point, p), …]} for games on the slate. p = home / Over / YES probability."""
    H = {}
    for f, is_prop in (('data/raw/odds_api/lines_history.csv', False), ('data/raw/odds_api/props_history.csv', True)):
        if not os.path.exists(f): continue
        for r in csv.DictReader(open(f, encoding='utf-8')):
            k = hist_key(r['league'], r['away'], r['home'], r['commence'][:10], 'prop' if is_prop else r['market'], r.get('player', ''), r.get('stat', ''))
            pt = r['line'] if is_prop else r['point']
            H.setdefault(k, []).append((r['ts'], float(pt) if pt != '' else None, float(r['p']) if r['p'] != '' else None))
    for v in H.values(): v.sort()
    return H

def steam_for(H, g, market, player='', stat=''):
    """(Δp toward home/Over/YES since the opener, Δline, n snapshots, series) or None."""
    v = H.get(hist_key(g['lg'], g['away'], g['home'], g['date'][:10], market, player, stat))
    if not v or len(v) < 2: return None
    o, n = v[0], v[-1]
    dp = (n[2] - o[2]) if o[2] is not None and n[2] is not None else 0.0
    dl = (n[1] - o[1]) if o[1] is not None and n[1] is not None else 0.0
    return dict(dp=round(dp, 4), dl=round(dl, 1), n=len(v), series=[[x[0][5:16], x[1], x[2]] for x in v])

def conf_score(n_src, disp, has_exch, ev, steam_dp, one_sided):
    """0-100 confidence that an edge is real: how many independent two-sided sources set the fair, how tightly they agree,
    whether a liquid exchange is among them, whether the line has been moving toward the bet, and a stale-line penalty for edges too good to be true."""
    c = {0: 15, 1: 30, 2: 52, 3: 66, 4: 76}.get(n_src, 84)
    if disp is not None: c -= min(30, 1000 * disp)          # sd of the sources' fair probabilities: 1 pt of sd = −1
    if has_exch: c += 8
    if steam_dp is not None: c += max(-10, min(10, 400 * steam_dp))
    if ev > 0.15: c -= 25
    elif ev > 0.08: c -= 10
    if one_sided: c = min(c, 60)
    return int(max(0, min(100, round(c))))

def tier(c): return 'A' if c >= 70 else 'B' if c >= 50 else 'C'

def analyse(rows, G, M=None):
    M = M or {}; by = {}; TDF = td_fair(rows, G); H = history(G)
    for r in rows: by.setdefault(pair_key(r), []).append(r)
    board, arbs, evs = [], [], []
    EXW = 1.5                                                                  # exchange mid-points weigh more than one book's de-vigged price
    for key, R in by.items():
        g = G[key[0]]; A = [r for r in R if side_of(r, g) == 'A']; B = [r for r in R if side_of(r, g) == 'B']
        one_sided = key[1].startswith('prop|anytime_td|')
        if not A or (not B and not one_sided): continue
        player, stat = A[0].get('player', ''), A[0].get('stat', '')
        mp = model_p(M, player, stat, key[2]) if key[1].startswith('prop|') else None
        mk = 'prop' if key[1].startswith('prop|') else key[1]
        # ---- fair per source (two-sided only): books de-vigged, exchanges at the mid
        F = {}; W = {}
        for s_ in SRC:
            a = next((x for x in A if x['source'] == s_), None); b = next((x for x in B if x['source'] == s_), None)
            if not a or not b: continue
            if KIND[s_] == 'exchange': F[s_] = (float(a['implied']) + (1 - float(b['implied']))) / 2; W[s_] = EXW
            else: F[s_] = a['implied'] / (a['implied'] + b['implied']); W[s_] = 1.0
        if one_sided and (key[0], player) in TDF: F['_td'] = TDF[(key[0], player)]; W['_td'] = 1.0
        if not F and mp is None and not one_sided: continue
        wsum = sum(W.values()); fair_a = sum(F[k] * W[k] for k in F) / wsum if F else mp if mp is not None else None
        basis = 'market' if F else 'model' if mp is not None else 'none'
        n_src = len([k for k in F if k != '_td']); vals = list(F.values())
        disp = (sum((v - fair_a) ** 2 for v in vals) / len(vals)) ** 0.5 if len(vals) >= 2 else None
        has_exch = any(KIND.get(k) == 'exchange' for k in F)
        st = steam_for(H, g, mk, player, stat)
        def loo(src):
            """fair with the priced source left out — a book cannot vouch for its own price"""
            if src not in F or len(F) < 2: return fair_a
            ws = sum(W[k] for k in F if k != src); return sum(F[k] * W[k] for k in F if k != src) / ws
        bestA = max(A, key=lambda x: x['eff_dec']); bestB = max(B, key=lambda x: x['eff_dec']) if B else None
        sum_inv = 1 / bestA['eff_dec'] + (1 / bestB['eff_dec'] if bestB else 9)
        lab = lambda r: r['selection'] + (f" {r['point']:+g}" if r['market'] == 'spread' else f" {r['point']}" if r['market'] == 'total' or (r['market'] == 'prop' and stat != 'anytime_td') else '')
        ev_of = lambda f, r: round(f * r['eff_dec'] - 1, 4) if f is not None and r else ''
        fa_A = loo(bestA['source']) if fair_a is not None else None; fa_B = (1 - loo(bestB['source'])) if (fair_a is not None and bestB) else None
        rec = dict(league=g['lg'], event_id=g['id'], kickoff=g['date'], away=g['away'], home=g['home'], market=mk, line=key[2], side_a=lab(bestA), side_b=lab(bestB) if bestB else '',
                   player=player, stat=stat, fair_a=round(fair_a, 4) if fair_a is not None else '', fair_b=round(1 - fair_a, 4) if fair_a is not None else '',
                   sources=n_src, disp=round(disp, 4) if disp is not None else '', exch=int(has_exch), basis=basis,
                   best_a_src=bestA['source'], best_a_dec=bestA['eff_dec'], best_a_american=american(bestA['eff_dec']),
                   best_b_src=bestB['source'] if bestB else '', best_b_dec=bestB['eff_dec'] if bestB else '', best_b_american=american(bestB['eff_dec']) if bestB else '',
                   hold=round(sum_inv - 1, 4) if bestB else '', ev_a=ev_of(fa_A, bestA), ev_b=ev_of(fa_B, bestB),
                   model_p=round(mp, 4) if mp is not None else '', ev_model_a=round(mp * bestA['eff_dec'] - 1, 4) if mp is not None else '', ev_model_b=round((1 - mp) * bestB['eff_dec'] - 1, 4) if mp is not None and bestB else '',
                   steam_dp=st['dp'] if st else '', steam_dl=st['dl'] if st else '', snaps=st['n'] if st else 0)
        rec['best_ev'] = max([x for x in (rec['ev_a'], rec['ev_b']) if x != ''] or [-9]); board.append(rec)
        if fair_a is None: continue
        if bestB and sum_inv < 1:
            margin = 1 - sum_inv; stake_a = (1 / bestA['eff_dec']) / sum_inv * 100; stake_b = 100 - stake_a
            arbs.append(dict(**{k: rec[k] for k in ('league', 'event_id', 'kickoff', 'away', 'home', 'market', 'line', 'side_a', 'side_b', 'best_a_src', 'best_a_dec', 'best_b_src', 'best_b_dec', 'player', 'stat')},
                             margin=round(margin, 4), stake_a_per_100=round(stake_a, 2), stake_b_per_100=round(stake_b, 2), profit_per_100=round(100 * margin / sum_inv, 2)))
        for side, lst in (('A', A), ('B', B)):
            for r in lst:
                f_loo = loo(r['source']); fair = f_loo if side == 'A' else 1 - f_loo
                ev = fair * r['eff_dec'] - 1; mpe = (mp if side == 'A' else 1 - mp) if mp is not None else None
                if one_sided and (fair < 0.10 or basis != 'market'): continue
                if ev < 0.01 and not (mpe is not None and mpe * r['eff_dec'] - 1 >= 0.03 and F): continue
                sdp = (st['dp'] if side == 'A' else -st['dp']) if st else None
                if mk == 'moneyline' or mk == 'spread': sdp = (-st['dp'] if side == 'A' else st['dp']) if st else None   # history p is the HOME side; side A is the away team
                c = conf_score(n_src, disp, has_exch, ev, sdp, one_sided)
                kelly = max(0, (fair * r['eff_dec'] - 1) / (r['eff_dec'] - 1))
                evs.append(dict(league=g['lg'], event_id=g['id'], kickoff=g['date'], away=g['away'], home=g['home'], market=r['market'], selection=r['selection'], point=r['point'], source=r['source'], player=player, stat=stat,
                                dec=r['eff_dec'], american=american(r['eff_dec']), fair=round(fair, 4), ev=round(ev, 4), kelly_quarter=round(kelly / 4, 4), sources=n_src, disp=round(disp, 4) if disp is not None else '', exch=int(has_exch), basis=basis,
                                model_p=round(mpe, 4) if mpe is not None else '', ev_model=round(mpe * r['eff_dec'] - 1, 4) if mpe is not None else '',
                                steam=round(sdp, 4) if sdp is not None else '', conf=c, tier=tier(c), liq=r.get('liq', ''), note=r.get('note', ''), key=key[1] + '|' + str(key[2])))
    board.sort(key=lambda r: -r['best_ev']); arbs.sort(key=lambda r: -r['margin']); evs.sort(key=lambda r: (-r['conf'] * 0.004 - r['ev']))
    return board, arbs, evs, H

def movers(G, H):
    """Line movement: first snapshot (open) vs latest per game-market and per player-stat, games still on the slate; carries the series for sparklines."""
    out = []
    for k, v in H.items():
        if len(v) < 2: continue
        lg, away, home, d10, market, player, stat = k.split('|')
        g = find_game(G, lg, away, home, d10)
        if not g: continue
        o, n = v[0], v[-1]
        dp = (n[2] - o[2]) if o[2] is not None and n[2] is not None else None
        dl = (n[1] - o[1]) if o[1] is not None and n[1] is not None else None
        if not dp and not dl: continue
        out.append(dict(league=lg, event_id=g['id'], kickoff=g['date'], away=away, home=home, market=market, player=player, stat=stat, open_ts=o[0], last_ts=n[0], snaps=len(v),
                        open_line='' if o[1] is None else o[1], line='' if n[1] is None else n[1], d_line=round(dl, 1) if dl is not None else '', open_p='' if o[2] is None else o[2], p='' if n[2] is None else n[2],
                        d_p=round(dp, 4) if dp is not None else '', series=[[x[0][5:16], x[1], x[2]] for x in v]))
    out.sort(key=lambda r: -(abs(r['d_p'] or 0) + abs(r['d_line'] or 0) / 20))
    return out

def closes(G, H, now):
    """Latest consensus per market key (the close, for started games; the current number otherwise) — the CLV reference for saved plays."""
    out = {}
    for k, v in H.items():
        lg, away, home, d10 = k.split('|')[:4]
        g = find_game(G, lg, away, home, d10)
        last = v[-1]
        out[k] = dict(ts=last[0], point=last[1], p=last[2], closed=bool(g and g['date'] <= now))
    return out

def write_csv(path, rows):
    if not rows: open(path, 'w').write(''); return
    cols = list(rows[0].keys()) + [k for r in rows for k in r.keys() if k not in rows[0]]
    cols = list(dict.fromkeys(cols))
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

# ------------------------------------------------------------------------------------------------ page
HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">"""
CSS = r"""
:root{--bg:#000;--p:#0a0a0b;--p2:#111113;--p3:#17171a;--e:#1c1c20;--e2:#2a2a30;--fg:#e7e7ea;--dim:#8a8c93;--mute:#55575f;--acc:#e8b339;--g:#3fb950;--r:#f0564a;--b:#58a6ff;--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;--sans:Inter,system-ui,-apple-system,Segoe UI,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.4 var(--sans)}a{color:inherit;text-decoration:none}button,input,select{font:inherit;color:inherit}
#hdr{display:flex;align-items:center;gap:14px;padding:0 18px;height:44px;border-bottom:1px solid var(--e);background:#050506;position:sticky;top:0;z-index:9}
.brand{font:800 14px/1 var(--mono);letter-spacing:4px}.brand i{color:var(--acc);font-style:normal;margin-right:6px}.brand small{font:500 10px var(--mono);letter-spacing:2px;color:var(--dim);margin-left:8px}
.tabs{display:flex;gap:2px;margin-left:10px}.tabs button{background:none;border:0;border-bottom:2px solid transparent;padding:0 12px;height:44px;font:600 11px var(--mono);letter-spacing:1.5px;color:var(--dim);cursor:pointer}.tabs button.on{color:var(--fg);border-bottom-color:var(--acc)}.tabs button b{color:var(--acc);font-weight:600;margin-left:5px}
.lg{display:flex;gap:2px;margin-left:auto}.lg button,.hl a{background:var(--p);border:1px solid var(--e2);padding:3px 9px;border-radius:3px;font:600 10px var(--mono);letter-spacing:1px;color:var(--dim);cursor:pointer}.lg button.on{color:#000;background:var(--acc);border-color:var(--acc)}
.hl{display:flex;gap:4px}.hl a:hover{color:var(--fg)}.meta{font:500 10px var(--mono);color:var(--mute);letter-spacing:.5px}.meta b{color:var(--dim);font-weight:500}
.bk{display:flex;align-items:center;gap:5px;font:500 10px var(--mono);color:var(--dim)}.bk input{width:72px;background:var(--p2);border:1px solid var(--e2);border-radius:3px;padding:3px 6px;font:600 11px var(--mono);color:var(--fg);text-align:right}
.q{width:22px;height:22px;border-radius:50%;border:1px solid var(--e2);background:var(--p);color:var(--dim);font:700 11px var(--mono);cursor:pointer}
main{padding:12px 18px 60px;max-width:1600px;margin:0 auto}
.strip{display:flex;flex-wrap:wrap;gap:0;border:1px solid var(--e);border-radius:6px;background:var(--p);margin-bottom:10px;overflow:hidden}.strip>div{padding:8px 14px;border-right:1px solid var(--e);min-width:120px}.strip>div:last-child{border-right:0;margin-left:auto}.strip span{display:block;font:600 9px var(--mono);letter-spacing:1.5px;color:var(--mute);text-transform:uppercase}.strip b{font:700 17px/1.2 var(--mono)}.strip small{font:500 10px var(--mono);color:var(--dim);margin-left:6px}.strip .g{color:var(--g)}.strip .a{color:var(--acc)}
.ctl{display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;margin:0 0 10px;font:500 10.5px var(--mono);color:var(--dim)}.ctl label{display:flex;align-items:center;gap:6px}.ctl input[type=range]{width:110px;accent-color:var(--acc)}.ctl .v{color:var(--fg);font-weight:600;min-width:34px}
.seg{display:inline-flex;border:1px solid var(--e2);border-radius:4px;overflow:hidden}.seg button{background:var(--p);border:0;border-right:1px solid var(--e2);padding:3px 9px;font:600 10px var(--mono);color:var(--dim);cursor:pointer}.seg button:last-child{border-right:0}.seg button.on{background:var(--p3);color:var(--fg)}
table{border-collapse:collapse;width:100%;font-size:12px}th{font:600 9.5px var(--mono);letter-spacing:1.2px;text-transform:uppercase;color:var(--mute);text-align:left;padding:6px 8px;border-bottom:1px solid var(--e2);cursor:pointer;white-space:nowrap;position:sticky;top:44px;background:var(--bg);z-index:2}th.srt-asc::after{content:' ▲';color:var(--acc)}th.srt-desc::after{content:' ▼';color:var(--acc)}
td{padding:6px 8px;border-bottom:1px solid var(--e);vertical-align:middle;white-space:nowrap}tr.x{cursor:pointer}tr.x:hover td{background:var(--p)}tr.open td{background:var(--p)}
.mono{font-family:var(--mono)}.dim{color:var(--dim)}.mute{color:var(--mute)}.g{color:var(--g)}.r{color:var(--r)}.b{color:var(--b)}.acc{color:var(--acc)}.num{font-family:var(--mono);text-align:right}th.num{text-align:right}
.tm{display:inline-flex;align-items:center;gap:4px;font-weight:600}.tm img{width:16px;height:16px;object-fit:contain}
.tier{display:inline-flex;align-items:center;gap:6px;font:700 11px var(--mono)}.tier i{display:inline-block;width:18px;height:18px;border-radius:3px;text-align:center;line-height:18px;font-style:normal;color:#000}.tier.A i{background:var(--g)}.tier.B i{background:var(--acc)}.tier.C i{background:var(--mute);color:var(--fg)}.tier .cb{width:46px;height:4px;background:var(--p3);border-radius:2px;overflow:hidden}.tier .cb i{display:block;height:100%;width:0;border-radius:0;background:var(--dim)}.tier.A .cb i{background:var(--g)}.tier.B .cb i{background:var(--acc)}
.bet b{font-weight:700}.bet small{display:block;font:500 10px var(--mono);color:var(--dim);margin-top:1px}
.src{display:inline-block;font:700 10px var(--mono);letter-spacing:.5px;padding:2px 6px;border-radius:3px;border:1px solid var(--e2);background:var(--p2)}.src.ex{border-color:#2b3a4f;color:var(--b)}
.edge{display:inline-flex;align-items:center;gap:6px;font:700 12px var(--mono)}.edge .eb{width:54px;height:5px;background:var(--p3);border-radius:2px;overflow:hidden}.edge .eb i{display:block;height:100%;background:var(--g)}
.steam{font:600 11px var(--mono)}.steam.up{color:var(--g)}.steam.dn{color:var(--r)}
.save{background:var(--p2);border:1px solid var(--e2);border-radius:3px;padding:2px 8px;font:600 10px var(--mono);color:var(--dim);cursor:pointer}.save:hover{color:var(--fg);border-color:var(--acc)}.save.on{color:var(--acc);border-color:var(--acc)}
.drawer td{padding:0;background:#060607}.dr{padding:10px 12px 12px 36px;display:grid;grid-template-columns:minmax(360px,1fr) minmax(260px,.8fr);gap:16px;align-items:start}.dr h4{margin:0 0 6px;font:600 9.5px var(--mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--mute)}.dr table th{position:static;top:auto}.dr .best{color:var(--acc);font-weight:700}
.spark{width:100%;height:46px;display:block}.spark path{fill:none;stroke:var(--b);stroke-width:1.5}.spark circle{fill:var(--b)}.spark text{font:500 9px var(--mono);fill:var(--dim)}
.arbrow td{background:#07110a}.arbrow .src{border-color:#274a2b}
.empty{color:var(--mute);padding:28px 12px;border:1px dashed var(--e2);border-radius:6px;text-align:center;font:500 11px var(--mono)}
/* shop */
.shop{display:grid;grid-template-columns:300px minmax(0,1fr);gap:14px;align-items:start}.glist{border:1px solid var(--e);border-radius:6px;background:var(--p);max-height:calc(100vh - 140px);overflow:auto}.glist input{width:100%;background:var(--p2);border:0;border-bottom:1px solid var(--e);padding:8px 10px;font:500 11px var(--mono);color:var(--fg)}.gi{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:7px 10px;border-bottom:1px solid var(--e);cursor:pointer}.gi:hover,.gi.on{background:var(--p3)}.gi .t{font-weight:600;display:flex;gap:6px;align-items:center}.gi .t img{width:14px;height:14px}.gi small{font:500 9.5px var(--mono);color:var(--dim)}.gi .n{font:600 10px var(--mono);color:var(--acc);align-self:center}
.mkt{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:10px;align-items:center}.mkt button{background:var(--p);border:1px solid var(--e2);border-radius:3px;padding:4px 10px;font:600 10px var(--mono);letter-spacing:1px;color:var(--dim);cursor:pointer}.mkt button.on{color:var(--fg);border-color:var(--acc)}.mkt input{background:var(--p2);border:1px solid var(--e2);border-radius:3px;padding:4px 8px;font:500 11px var(--mono);color:var(--fg);width:200px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:10px}.card{border:1px solid var(--e);border-radius:6px;background:var(--p);padding:8px 10px}.card h4{margin:0 0 6px;font:600 10px var(--mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--dim);display:flex;gap:8px;align-items:baseline}.card h4 b{color:var(--fg)}.card h4 small{margin-left:auto;font-weight:500;letter-spacing:0;text-transform:none;color:var(--mute)}.card table th{position:static;top:auto;padding:3px 6px}.card td{padding:3px 6px;border-bottom:1px solid #121214}.card .best{color:var(--acc);font-weight:700}
/* clv */
.clvsum{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-bottom:12px}.clvsum>div{border:1px solid var(--e);border-radius:6px;background:var(--p);padding:9px 12px}.clvsum span{display:block;font:600 9px var(--mono);letter-spacing:1.5px;color:var(--mute);text-transform:uppercase}.clvsum b{font:700 18px/1.25 var(--mono)}.clvsum small{display:block;font:500 10px var(--mono);color:var(--dim)}
.foot{margin-top:22px;padding-top:10px;border-top:1px solid var(--e);color:var(--mute);font:500 10px/1.7 var(--mono)}.foot b{color:var(--dim);font-weight:500}
#how{display:none;position:fixed;inset:44px 0 0;background:rgba(0,0,0,.72);z-index:8}#how .box{max-width:760px;margin:30px auto;background:var(--p);border:1px solid var(--e2);border-radius:8px;padding:18px 22px;font-size:12.5px;line-height:1.55;max-height:calc(100vh - 110px);overflow:auto}#how h3{margin:0 0 10px;font:700 15px var(--sans)}#how h5{margin:14px 0 4px;font:600 10px var(--mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--acc)}#how p{margin:0 0 6px;color:#cfd0d5}
.toast{position:fixed;right:18px;bottom:18px;background:#15140f;border:1px solid var(--acc);color:var(--fg);padding:8px 12px;border-radius:6px;font:600 11px var(--mono);display:none;z-index:9}
@media (max-width:900px){.shop{grid-template-columns:1fr}.glist{max-height:260px}.dr{grid-template-columns:1fr}.tabs button{padding:0 8px}.brand small{display:none}}
"""
JS = r"""
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const G=J.games,L=J.lines,B=J.board,A=J.arbs,E=J.evs,MV=J.moves,CL=J.close,SRC=J.src;const TZ='America/Chicago';const NOW=Date.now();
const CT=d=>new Date(d).toLocaleString('en-US',{weekday:'short',hour:'numeric',minute:'2-digit',timeZone:TZ}).replace(':00','');const num=v=>v===''||v==null?null:+v;
const pct=p=>(100*p).toFixed(1)+'%';const am=d=>d>=2?'+'+Math.round((d-1)*100):String(Math.round(-100/(d-1)));const sgn=v=>(v>=0?'+':'')+v;
const logo=(g,t)=>{const l=t===g.away?g.away_logo:g.home_logo;return l?`<img src="https://a.espncdn.com/i/teamlogos/${l}" alt="" onerror="this.style.display='none'">`:''};
const gm=(g)=>`<span class="tm">${logo(g,g.away)}${esc(g.away)}</span> <span class="mute">@</span> <span class="tm">${logo(g,g.home)}${esc(g.home)}</span>`;
const STAT={pass_yds:'pass yds',pass_td:'pass TD',completions:'completions',pass_att:'pass att',rush_yds:'rush yds',rush_att:'rush att',receptions:'receptions',rec_yds:'rec yds',anytime_td:'anytime TD'};
const LS=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}},SV=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let VIEW=location.hash.replace('#','')||'edges',LG='all',MINEV=2,TIER='AB',KINDS={lines:true,props:true,td:true},BANK=LS('rainman.bankroll',1000),OPEN=null,SK='rank',SA=true;
const plays=()=>LS('rainman.plays',[]);function toast(m){const t=$('#toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(()=>t.style.display='none',1800)}
const srcTag=s=>`<span class="src ${SRC[s]&&SRC[s].kind==='exchange'?'ex':''}" title="${SRC[s]?SRC[s].name:s}">${s}</span>`;
const betLabel=r=>r.market==='prop'?(r.stat==='anytime_td'?`${esc(r.player)} <span class="dim">anytime TD</span> ${r.selection}`:`${esc(r.player)} ${r.selection} ${r.point} <span class="dim">${STAT[r.stat]||r.stat}</span>`):r.market==='spread'?`${esc(r.selection)} ${(+r.point>0?'+':'')+r.point}`:r.market==='total'?`${r.selection} ${r.point}`:`${esc(r.selection)} <span class="dim">ML</span>`;
const kindOf=r=>r.market!=='prop'?'lines':r.stat==='anytime_td'?'td':'props';
const inLG=r=>LG==='all'||r.league===LG;
const playId=r=>[r.event_id,r.market,r.selection,r.point,r.source,r.player||''].join('|');
function savePlay(r){const P=plays();const id=playId(r);if(P.some(p=>p.id===id)){toast('already saved');return}const g=G[r.event_id];
  P.push({id,league:g.lg,game:g.away+' @ '+g.home,kickoff:g.date,market:r.market,selection:r.market==='prop'?(r.stat==='anytime_td'?`${r.player} anytime TD ${r.selection}`:`${r.player} ${r.selection} ${r.point} ${STAT[r.stat]||r.stat}`):r.selection,point:r.point,player:r.player||'',stat:r.stat||'',side:r.market==='prop'?r.selection:'',source:r.source,dec:r.dec,american:am(r.dec),fair:r.fair??null,ev:r.ev??null,conf:r.conf??null,tier:r.tier||'',saved:new Date().toISOString(),status:'open',from:'arb'});
  SV('rainman.plays',P);toast(`saved · ${P.length} plays`);render()}
// ---------------------------------------------------------------- header
function header(){const lgs=[...new Set(E.map(e=>e.league).concat(B.map(b=>b.league)))].sort();const n=feedRows().length;
  $('#tabs').innerHTML=['edges','shop','steam','clv'].map(v=>`<button data-v="${v}" class="${VIEW===v?'on':''}">${v.toUpperCase()}${v==='edges'?`<b>${n}</b>`:v==='steam'?`<b>${MV.filter(inLG).length}</b>`:v==='clv'?`<b>${plays().length}</b>`:''}</button>`).join('');
  $('#lgs').innerHTML=`<button data-l="all" class="${LG==='all'?'on':''}">ALL</button>`+lgs.map(l=>`<button data-l="${l}" class="${LG===l?'on':''}">${l.toUpperCase()}</button>`).join('');
  $$('#tabs button').forEach(b=>b.onclick=()=>{VIEW=b.dataset.v;location.hash=VIEW;render()});$$('#lgs button').forEach(b=>b.onclick=()=>{LG=b.dataset.l;render()});
  $('#bank').value=BANK;$('#bank').onchange=e=>{BANK=+e.target.value||0;SV('rainman.bankroll',BANK);render()};$('#plays').textContent=plays().length+' saved'}
// ---------------------------------------------------------------- edges
function feedRows(){return E.filter(e=>inLG(e)&&e.ev>=MINEV/100&&(TIER==='all'||TIER.includes(e.tier))&&KINDS[kindOf(e)]&&e.basis==='market')}
function edges(){const rows=feedRows();const V={rank:r=>-(r.conf*0.004+r.ev),kick:r=>r.kickoff,game:r=>r.away+r.home,bet:r=>(r.player||r.selection),src:r=>r.source,price:r=>r.dec,fair:r=>r.fair,ev:r=>r.ev,conf:r=>r.conf,n:r=>r.sources,steam:r=>num(r.steam)??0,stake:r=>r.kelly_quarter};
  rows.sort((a,b)=>{const x=V[SK](a),y=V[SK](b);return (x<y?-1:x>y?1:0)*(SA?1:-1)});
  const arbs=A.filter(inLG);const tA=rows.filter(r=>r.tier==='A').length;
  const th=(k,l,c,t)=>`<th data-k="${k}" class="${c||''} ${SK===k?(SA?'srt-asc':'srt-desc'):''}" title="${t||''}">${l}</th>`;
  $('#view').innerHTML=`<div class="strip"><div><span>edges ≥ ${MINEV}%</span><b>${rows.length}</b><small>${tA} tier A</small></div><div><span>arbitrage</span><b class="${arbs.length?'g':''}">${arbs.length}</b><small>${arbs.length?'best +'+pct(arbs[0].margin):'none after fees'}</small></div><div><span>markets priced</span><b>${B.filter(inLG).length}</b><small>${B.filter(b=>inLG(b)&&b.sources>=2).length} at 2+ sources</small></div><div><span>lines</span><b>${L.filter(l=>LG==='all'||l.league===LG).length}</b><small>${Object.keys(SRC).length} sources</small></div><div><span>pulled</span><b style="font-size:13px">${esc(J.asof)}</b><small>prices move — confirm at the book</small></div></div>
  <div class="ctl"><label>min edge <input type="range" id="minev" min="1" max="10" step="0.5" value="${MINEV}"><span class="v">${MINEV}%</span></label><label>confidence <span class="seg" id="tier"><button data-t="A" class="${TIER==='A'?'on':''}">A only</button><button data-t="AB" class="${TIER==='AB'?'on':''}">A + B</button><button data-t="all" class="${TIER==='all'?'on':''}">all</button></span></label><label>markets <span class="seg" id="kinds"><button data-k="lines" class="${KINDS.lines?'on':''}">game lines</button><button data-k="props" class="${KINDS.props?'on':''}">props</button><button data-k="td" class="${KINDS.td?'on':''}">anytime TD</button></span></label><span class="mute">stake = ¼ Kelly on $${BANK.toLocaleString()} · click a row for every price on that market</span></div>
  ${arbs.length?`<table class="mono" style="margin-bottom:10px"><thead><tr><th>arb</th><th>game</th><th>market</th><th>leg 1</th><th>leg 2</th><th class="num">margin</th><th class="num">per $100</th></tr></thead><tbody>${arbs.map(a=>{const g=G[a.event_id];return `<tr class="arbrow"><td><span class="tier A"><i>$</i></span></td><td>${gm(g)} <span class="mute">${CT(g.date)}</span></td><td class="dim">${a.market==='prop'?esc(a.player)+' '+(STAT[a.stat]||a.stat):a.market}${a.market!=='moneyline'&&a.stat!=='anytime_td'?' '+a.line:''}</td><td>$${a.stake_a_per_100} <b>${esc(a.side_a)}</b> ${srcTag(a.best_a_src)} ${am(a.best_a_dec)}</td><td>$${a.stake_b_per_100} <b>${esc(a.side_b)}</b> ${srcTag(a.best_b_src)} ${am(a.best_b_dec)}</td><td class="num g"><b>+${pct(a.margin)}</b></td><td class="num g">$${a.profit_per_100}</td></tr>`}).join('')}</tbody></table>`:''}
  ${rows.length?`<table id="feed"><thead><tr>${th('conf','conf','', 'confidence the edge is real: sources behind the fair, how tightly they agree, exchange presence, steam, stale-line penalty')}${th('kick','kick')}${th('game','game')}${th('bet','bet')}${th('src','book')}${th('price','price','num')}${th('fair','fair','num','consensus probability with this book left out')}${th('ev','edge','num')}${th('n','src','num','two-sided sources behind the fair · ± = how far they disagree')}${th('steam','steam','num','consensus move toward this side since the opener')}${th('stake','stake','num')}<th></th></tr></thead><tbody>${rows.map((r,i)=>{const g=G[r.event_id];const P=plays().some(p=>p.id===playId(r));const st=num(r.steam);const liq=r.liq?` <span class="mute">· liq ${r.liq}</span>`:'';
    return `<tr class="x ${OPEN===i?'open':''}" data-i="${i}"><td><span class="tier ${r.tier}"><i>${r.tier}</i><span class="cb"><i style="width:${r.conf}%"></i></span><span class="dim" style="font-weight:500">${r.conf}</span></span></td><td class="mono dim">${CT(r.kickoff)}</td><td>${gm(g)}</td><td class="bet"><b>${betLabel(r)}</b>${r.market==='prop'?'':`<small>${r.market}</small>`}</td><td>${srcTag(r.source)}${liq}</td><td class="num"><b>${am(r.dec)}</b></td><td class="num dim">${pct(r.fair)}${r.model_p!==''?`<span class="mute" title="RAINMAN model"> · m ${pct(+r.model_p)}</span>`:''}</td><td class="num"><span class="edge g">+${(100*r.ev).toFixed(1)}%<span class="eb"><i style="width:${Math.min(100,r.ev*600)}%"></i></span></span></td><td class="num dim">${r.sources}${r.exch?'<span class="b" title="exchange among the sources">·x</span>':''}${r.disp!==''?` <span class="mute">±${(100*r.disp).toFixed(1)}</span>`:''}</td><td class="num"><span class="steam ${st>0.004?'up':st<-0.004?'dn':'mute'}">${st==null?'—':(st>0.004?'▲ ':st<-0.004?'▼ ':'· ')+(100*Math.abs(st)).toFixed(1)}</span></td><td class="num">$${Math.round(r.kelly_quarter*BANK)}</td><td><button class="save ${P?'on':''}" data-i="${i}">${P?'saved':'save'}</button></td></tr>${OPEN===i?`<tr class="drawer"><td colspan="12">${drawer(r)}</td></tr>`:''}`}).join('')}</tbody></table>`:`<div class="empty">nothing clears ${MINEV}% at this confidence${LG!=='all'?' in '+LG.toUpperCase():''} — lower the bar, or wait for the next pull (${esc(J.asof)} is the latest)</div>`}`;
  $('#minev').oninput=e=>{MINEV=+e.target.value;OPEN=null;edges();header()};$$('#tier button').forEach(b=>b.onclick=()=>{TIER=b.dataset.t;OPEN=null;render()});$$('#kinds button').forEach(b=>b.onclick=()=>{KINDS[b.dataset.k]=!KINDS[b.dataset.k];OPEN=null;render()});
  $$('#feed th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(SK===k)SA=!SA;else{SK=k;SA=k==='rank'||k==='kick'||k==='game'||k==='bet'||k==='src'}OPEN=null;edges()});
  $$('#feed tr.x').forEach(tr=>tr.onclick=e=>{if(e.target.closest('button'))return;const i=+tr.dataset.i;OPEN=OPEN===i?null:i;edges()});
  $$('#feed .save').forEach(b=>b.onclick=()=>savePlay(rows[+b.dataset.i]))}
// every price on one market, both sides, every source — the line-shop table used by the drawer and the SHOP view
function marketRows(ev,market,line,player,stat){const g=G[ev];const isA=l=>market==='moneyline'?l.selection===g.away:market==='spread'?l.selection===g.away:(l.selection==='Over'||l.selection==='Yes');
  const same=l=>market==='moneyline'?true:market==='spread'?Math.abs((l.selection===g.away?+l.point:-+l.point)-line)<1e-9:Math.abs(+l.point-line)<1e-9;
  const rows=L.filter(l=>l.event_id===ev&&l.market===market&&(market!=='prop'||(l.player===player&&l.stat===stat))&&same(l));const by={};rows.forEach(l=>{const o=by[l.source]=by[l.source]||{src:l.source};o[isA(l)?'a':'b']=l});
  return Object.values(by).sort((x,y)=>Math.max(y.a?y.a.eff_dec:0,y.b?y.b.eff_dec:0)-Math.max(x.a?x.a.eff_dec:0,x.b?x.b.eff_dec:0))}
function shopTable(ev,market,line,player,stat,brd){const g=G[ev];const R=marketRows(ev,market,line,player,stat);if(!R.length)return '<div class="empty">no prices</div>';
  const bA=Math.max(...R.map(r=>r.a?r.a.eff_dec:0)),bB=Math.max(...R.map(r=>r.b?r.b.eff_dec:0));const la=market==='moneyline'?g.away+' ML':market==='spread'?`${g.away} ${sgn(line)}`:market==='total'?'Over '+line:stat==='anytime_td'?'YES':'Over '+line;const lb=market==='moneyline'?g.home+' ML':market==='spread'?`${g.home} ${sgn(-line)}`:market==='total'?'Under '+line:stat==='anytime_td'?'NO':'Under '+line;
  const fa=brd&&brd.fair_a!==''?+brd.fair_a:null;const cell=(l,best,f)=>l?`<td class="num ${l.eff_dec===best?'best':''}" title="${pct(l.implied)} implied${l.fee?' + fee '+pct(l.fee):''}${l.note?' · '+esc(l.note):''}">${am(l.eff_dec)}${f!=null?`<span class="mute" style="font-weight:400"> ${sgn((100*(f*l.eff_dec-1)).toFixed(1))}%</span>`:''}</td>`:'<td class="num mute">—</td>';
  return `<table><thead><tr><th>source</th><th class="num">${esc(la)}</th><th class="num">${esc(lb)}</th><th class="num">hold</th></tr></thead><tbody>${R.map(r=>`<tr><td>${srcTag(r.src)}${r.a&&r.a.liq?` <span class="mute">liq ${r.a.liq}</span>`:''}</td>${cell(r.a,bA,fa)}${cell(r.b,bB,fa!=null?1-fa:null)}<td class="num dim">${r.a&&r.b?pct(1/r.a.eff_dec+1/r.b.eff_dec-1):'—'}</td></tr>`).join('')}<tr><td class="dim">best of all</td><td class="num best">${bA?am(bA):'—'}</td><td class="num best">${bB?am(bB):'—'}</td><td class="num ${bA&&bB&&1/bA+1/bB<1?'g':'dim'}">${bA&&bB?pct(1/bA+1/bB-1):'—'}</td></tr>${fa!=null?`<tr><td class="dim">fair · all sources</td><td class="num dim">${pct(fa)}</td><td class="num dim">${pct(1-fa)}</td><td class="num mute">${brd.sources} src${brd.model_p!==''?' · model '+pct(+brd.model_p):''}</td></tr>`:''}</tbody></table>`}
function spark(series,sideHome){if(!series||series.length<2)return '<div class="mute mono" style="font-size:10px">one snapshot so far — movement shows after the next pull</div>';const W=260,H=46,P=series.map(s=>s[2]==null?null:(sideHome?s[2]:1-s[2]));const ys=P.filter(v=>v!=null);if(ys.length<2)return '';const lo=Math.min(...ys)-.01,hi=Math.max(...ys)+.01;const X=i=>6+i*(W-12)/(series.length-1),Y=v=>H-8-(v-lo)/(hi-lo)*(H-18);
  return `<svg class="spark" viewBox="0 0 ${W} ${H}"><path d="${P.map((v,i)=>v==null?'':`${i===0?'M':'L'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ')}"/>${P.map((v,i)=>v==null?'':`<circle cx="${X(i).toFixed(1)}" cy="${Y(v).toFixed(1)}" r="2"/>`).join('')}<text x="6" y="${H-1}">${series[0][0]}Z · ${pct(P[0])}${series[0][1]!=null?' @ '+series[0][1]:''}</text><text x="${W-6}" y="${H-1}" text-anchor="end">${series[series.length-1][0]}Z · ${pct(P[P.length-1])}${series[series.length-1][1]!=null?' @ '+series[series.length-1][1]:''}</text></svg>`}
function drawer(r){const g=G[r.event_id];const brd=B.find(b=>b.event_id===r.event_id&&b.market===r.market&&+b.line===(r.market==='moneyline'?'':+r.point)&&(r.market!=='prop'||(b.player===r.player&&b.stat===r.stat)))||B.find(b=>b.event_id===r.event_id&&b.market===r.market&&(r.market==='moneyline'||Math.abs(+b.line-(r.market==='spread'?(r.selection===g.away?+r.point:-+r.point):+r.point))<1e-9)&&(r.market!=='prop'||(b.player===r.player&&b.stat===r.stat)));
  const line=r.market==='moneyline'?'':r.market==='spread'?(r.selection===g.away?+r.point:-+r.point):+r.point;const mv=MV.find(m=>m.event_id===r.event_id&&m.market===r.market&&(r.market!=='prop'||(m.player===r.player&&m.stat===r.stat)));
  const sideHome=r.market==='total'||r.market==='prop'?(r.selection==='Over'||r.selection==='Yes'):r.selection===g.home;
  return `<div class="dr"><div><h4>every price · ${esc(g.away)} @ ${esc(g.home)} · ${r.market==='prop'?esc(r.player)+' '+(STAT[r.stat]||r.stat):r.market}${line!==''&&r.stat!=='anytime_td'?' '+line:''}</h4>${shopTable(r.event_id,r.market,line,r.player,r.stat,brd)}</div><div><h4>why ${r.conf}/100</h4><div class="mono dim" style="font-size:11px;line-height:1.7">${r.sources} two-sided source${r.sources===1?'':'s'} set the fair${r.exch?' (an exchange among them)':''}${r.disp!==''?` · they disagree by ±${(100*r.disp).toFixed(1)} pts`:''}<br>${r.source} is left out of its own fair · edge +${(100*r.ev).toFixed(1)}% at ${am(r.dec)}${r.model_p!==''?`<br>RAINMAN model says ${pct(+r.model_p)} → ${sgn((100*+r.ev_model).toFixed(1))}% at this price`:''}${r.ev>0.08?'<br><span class="r">edge this large usually means a stale or limited line — check it is still up</span>':''}${r.stat==='anytime_td'?'<br>anytime TD fair = YES prices scaled to the team\'s expected scorers (coarse)':''}</div><h4 style="margin-top:10px">consensus for ${esc(r.market==='prop'?r.selection:r.selection)} since the opener</h4>${spark(mv&&mv.series,sideHome)}</div></div>`}
// ---------------------------------------------------------------- shop
let SG=null,SM='moneyline',SQ='';
function shop(){const games=Object.values(G).filter(g=>(LG==='all'||g.lg===LG)&&L.some(l=>l.event_id===g.id)).sort((a,b)=>a.date<b.date?-1:1);if(!SG||!games.some(g=>g.id===SG))SG=games.length?games[0].id:null;
  const nE=id=>E.filter(e=>e.event_id===id&&e.ev>=0.02&&e.tier!=='C').length;
  $('#view').innerHTML=`<div class="shop"><div class="glist"><input id="gq" placeholder="find a game…" value="${esc(SQ)}">${games.filter(g=>!SQ||(g.away+g.home+(g.tv||'')).toLowerCase().includes(SQ.toLowerCase())).map(g=>`<div class="gi ${g.id===SG?'on':''}" data-id="${g.id}"><span class="t">${logo(g,g.away)}${esc(g.away)} <span class="mute">@</span> ${logo(g,g.home)}${esc(g.home)}</span><span class="n">${nE(g.id)?nE(g.id)+' edge'+(nE(g.id)>1?'s':''):''}</span><small>${g.lg.toUpperCase()} · ${CT(g.date)}</small><small class="mute">${L.filter(l=>l.event_id===g.id).length} prices</small></div>`).join('')}</div><div id="sr"></div></div>`;
  $('#gq').oninput=e=>{SQ=e.target.value;shop();$('#gq').focus();$('#gq').setSelectionRange(SQ.length,SQ.length)};$$('.gi').forEach(d=>d.onclick=()=>{SG=d.dataset.id;shop()});shopRight()}
function shopRight(){const el=$('#sr');if(!SG){el.innerHTML='<div class="empty">no games</div>';return}const g=G[SG];const have=k=>L.some(l=>l.event_id===SG&&l.market===k);
  el.innerHTML=`<div class="mkt"><span class="mono dim" style="margin-right:8px">${gm(g)} <span class="mute">${CT(g.date)}${g.tv?' · '+esc(g.tv):''}</span></span>${[['moneyline','ML'],['spread','SPREAD'],['total','TOTAL'],['prop','PROPS']].map(([k,l])=>`<button data-m="${k}" class="${SM===k?'on':''}" ${have(k)?'':'disabled'}>${l}</button>`).join('')}${SM==='prop'?`<input id="pq" placeholder="player / stat…" value="${esc(SQP)}">`:''}</div><div id="sm"></div>`;
  $$('.mkt button').forEach(b=>b.onclick=()=>{SM=b.dataset.m;shopRight()});if($('#pq'))$('#pq').oninput=e=>{SQP=e.target.value;shopMarket();};shopMarket()}
let SQP='';
function shopMarket(){const el=$('#sm');const g=G[SG];let keys;
  if(SM==='moneyline')keys=[{line:'',player:'',stat:''}];
  else if(SM==='spread'||SM==='total'){const pts={};L.filter(l=>l.event_id===SG&&l.market===SM).forEach(l=>{const k=SM==='spread'?(l.selection===g.away?+l.point:-+l.point):+l.point;pts[k]=(pts[k]||0)+1});keys=Object.keys(pts).map(k=>({line:+k,n:pts[k],player:'',stat:''})).sort((a,b)=>b.n-a.n||a.line-b.line).slice(0,6)}
  else{const m={};L.filter(l=>l.event_id===SG&&l.market==='prop').forEach(l=>{const k=l.player+'|'+l.stat+'|'+l.point;m[k]=m[k]||{line:+l.point,player:l.player,stat:l.stat,n:0};m[k].n++});keys=Object.values(m).filter(k=>!SQP||(k.player+' '+(STAT[k.stat]||k.stat)).toLowerCase().includes(SQP.toLowerCase())).sort((a,b)=>b.n-a.n||a.player.localeCompare(b.player)).slice(0,60)}
  if(!keys.length){el.innerHTML='<div class="empty">nothing priced here</div>';return}
  el.innerHTML=`<div class="grid">${keys.map(k=>{const brd=B.find(b=>b.event_id===SG&&b.market===SM&&(SM==='moneyline'||Math.abs(+b.line-k.line)<1e-9)&&(SM!=='prop'||(b.player===k.player&&b.stat===k.stat)));const best=brd&&brd.best_ev!==''&&+brd.best_ev>=0.02?`<small class="g">best edge +${(100*brd.best_ev).toFixed(1)}%</small>`:'<small></small>';
    return `<div class="card"><h4>${SM==='prop'?`<b>${esc(k.player)}</b> ${STAT[k.stat]||k.stat}${k.stat==='anytime_td'?'':' '+k.line}`:SM==='moneyline'?'<b>moneyline</b>':`<b>${SM}</b> ${g.away} ${SM==='spread'?sgn(k.line):'o/u '+k.line}`}${best}</h4>${shopTable(SG,SM,k.line,k.player,k.stat,brd)}</div>`}).join('')}</div>`}
// ---------------------------------------------------------------- steam
let STK='move';
function steam(){const rows=MV.filter(inLG);if(!rows.length){$('#view').innerHTML=`<div class="empty">one snapshot on file (${esc(J.asof)}) — the opener is saved; the first move shows after the next Odds API pull (every ~20 h, then every 4 h inside 6 h of kickoff)</div>`;return}
  const V={move:r=>-(Math.abs(num(r.d_p)||0)+Math.abs(num(r.d_line)||0)/20),kick:r=>r.kickoff,game:r=>r.away+r.home,mk:r=>r.market+r.player,dl:r=>num(r.d_line)||0,dp:r=>num(r.d_p)||0,n:r=>r.snaps};rows.sort((a,b)=>{const x=V[STK](a),y=V[STK](b);return x<y?-1:x>y?1:0});
  const th=(k,l,c)=>`<th data-k="${k}" class="${c||''} ${STK===k?'srt-asc':''}">${l}</th>`;
  $('#view').innerHTML=`<div class="ctl"><span class="mute">consensus across the books, opener → latest · prob = home side / Over / YES · a line moving toward a side is the market agreeing with it</span></div><table id="st"><thead><tr>${th('kick','kick')}${th('game','game')}${th('mk','market')}${th('dl','line','num')}${th('dp','prob','num')}<th>path</th>${th('n','snaps','num')}</tr></thead><tbody>${rows.slice(0,150).map(m=>{const g=G[m.event_id]||{};const dp=num(m.d_p),dl=num(m.d_line);const ln=v=>v===''?'':(m.market==='spread'?sgn(v):v);
    return `<tr><td class="mono dim">${g.date?CT(g.date):''}</td><td>${g.away?gm(g):esc(m.away+' @ '+m.home)}</td><td>${m.player?`<b>${esc(m.player)}</b> <span class="dim">${STAT[m.stat]||m.stat}</span>`:`<b>${m.market}</b>`}</td><td class="num">${m.open_line!==''?`<span class="dim">${ln(m.open_line)}</span> → <b>${ln(m.line)}</b>${dl?` <span class="${dl>0?'g':'r'}">${sgn(dl)}</span>`:''}`:'—'}</td><td class="num">${dp==null?'—':`<span class="dim">${pct(+m.open_p)}</span> → <b>${pct(+m.p)}</b> <span class="steam ${dp>0?'up':'dn'}">${dp>0?'▲':'▼'} ${(100*Math.abs(dp)).toFixed(1)}</span>`}</td><td style="width:280px">${spark(m.series,true)}</td><td class="num dim">${m.snaps}</td></tr>`}).join('')}</tbody></table>`;
  $$('#st th[data-k]').forEach(t=>t.onclick=()=>{STK=t.dataset.k;steam()})}
// ---------------------------------------------------------------- CLV
function clvOf(p){const d10=p.kickoff.slice(0,10);const [away,home]=p.game.split(' @ ');const k=[p.league,away,home,d10,p.market,p.player||'',p.stat||''].join('|');const c=CL[k];if(!c)return null;
  const mine=1/p.dec;const homeSide=p.market==='total'||p.market==='prop'?(p.side==='Over'||p.side==='Yes'||/\bOver\b|\bYes\b/.test(p.selection)):p.selection===home;
  const pt=p.market==='moneyline'?null:+p.point;const cpt=c.point;const sameLine=pt==null||cpt==null||Math.abs((p.market==='spread'?(homeSide?-pt:pt):pt)-cpt)<1e-9;   // history line = home handicap / total / prop line
  const pc=c.p==null?null:(homeSide?c.p:1-c.p);const lineEdge=pt==null||cpt==null?null:(p.market==='spread'?((homeSide?-pt:pt)-cpt)*(homeSide?-1:1):p.market==='total'||p.market==='prop'?(homeSide?cpt-pt:pt-cpt):null);
  return {closed:c.closed,ts:c.ts,close_p:pc,mine,clv:sameLine&&pc!=null?pc-mine:null,lineEdge:sameLine?null:lineEdge,cpt}}
function clv(){const P=plays().filter(p=>LG==='all'||p.league===LG);if(!P.length){$('#view').innerHTML='<div class="empty">no saved plays yet — save a row on EDGES (or any price in SHOP) and it is scored here against the closing consensus: positive CLV = you beat the market\'s final number, the one thing that predicts long-run profit</div>';return}
  const rows=P.map(p=>({p,c:clvOf(p)}));const sc=rows.filter(r=>r.c&&r.c.clv!=null);const closed=sc.filter(r=>r.c.closed);const avg=a=>a.length?a.reduce((s,r)=>s+r.c.clv,0)/a.length:null;const beat=a=>a.length?a.filter(r=>r.c.clv>0).length/a.length:null;
  const byT={};sc.forEach(r=>{const t=r.p.tier||'?';(byT[t]=byT[t]||[]).push(r)});
  $('#view').innerHTML=`<div class="clvsum"><div><span>saved plays</span><b>${P.length}</b><small>${closed.length} closed · ${sc.length} scoreable</small></div><div><span>avg CLV · closed</span><b class="${avg(closed)>0?'g':avg(closed)<0?'r':''}">${avg(closed)==null?'—':sgn((100*avg(closed)).toFixed(2))+' pts'}</b><small>closing prob − your implied</small></div><div><span>beat the close</span><b>${beat(closed)==null?'—':pct(beat(closed))}</b><small>share of closed plays with CLV &gt; 0</small></div><div><span>avg CLV · all vs latest</span><b class="${avg(sc)>0?'g':avg(sc)<0?'r':''}">${avg(sc)==null?'—':sgn((100*avg(sc)).toFixed(2))+' pts'}</b><small>open plays scored against the latest pull</small></div>${Object.keys(byT).sort().map(t=>`<div><span>tier ${t}</span><b class="${avg(byT[t])>0?'g':avg(byT[t])<0?'r':''}">${sgn((100*avg(byT[t])).toFixed(2))}</b><small>${byT[t].length} plays · beat ${pct(beat(byT[t]))}</small></div>`).join('')}</div>
  <table><thead><tr><th>saved</th><th>kick</th><th>game</th><th>bet</th><th>book</th><th class="num">price</th><th class="num">implied</th><th class="num">fair then</th><th class="num">consensus now/close</th><th class="num">CLV</th><th>tier</th><th></th></tr></thead><tbody>${rows.sort((a,b)=>a.p.saved<b.p.saved?1:-1).map(({p,c})=>`<tr><td class="mono dim">${new Date(p.saved).toLocaleDateString('en-US',{month:'short',day:'numeric'})}</td><td class="mono dim">${CT(p.kickoff)}</td><td class="mono">${esc(p.game)} <span class="mute">${p.league.toUpperCase()}</span></td><td><b>${esc(p.selection)}</b>${p.market==='spread'?' '+sgn(+p.point):p.market==='total'?' '+p.point:''}</td><td>${srcTag(p.source)}</td><td class="num">${esc(p.american)}</td><td class="num dim">${pct(1/p.dec)}</td><td class="num dim">${p.fair!=null?pct(p.fair):'—'}</td><td class="num">${c&&c.close_p!=null?`${pct(c.close_p)} <span class="mute">${c.closed?'close':c.ts.slice(5,16)+'Z'}</span>`:'<span class="mute">no snapshot</span>'}</td><td class="num">${c&&c.clv!=null?`<b class="${c.clv>0?'g':c.clv<0?'r':''}">${sgn((100*c.clv).toFixed(1))}</b>`:c&&c.lineEdge!=null?`<span class="${c.lineEdge>0?'g':'r'}" title="the market line moved; CLV in points of line">${sgn(c.lineEdge)} pts of line</span>`:'<span class="mute">—</span>'}</td><td>${p.tier?`<span class="tier ${p.tier}"><i>${p.tier}</i></span>`:''}</td><td><button class="save" data-id="${esc(p.id)}">drop</button></td></tr>`).join('')}</tbody></table><p class="foot" style="border:0;margin-top:8px">CLV = the market's final (or latest) de-vigged probability for your side minus the probability your price implied. Beating the close consistently is the only durable evidence an edge is real; a single result is noise. Plays live in this browser (localStorage) and feed the Social tab.</p>`;
  $$('#view .save').forEach(b=>b.onclick=()=>{SV('rainman.plays',plays().filter(x=>x.id!==b.dataset.id));render()})}
// ---------------------------------------------------------------- shell
function foot(){const cnt={};L.forEach(l=>{cnt[l.source]=(cnt[l.source]||0)+1});$('#foot').innerHTML=`<b>sources</b> ${Object.keys(SRC).map(s=>`${SRC[s].name} ${cnt[s]||0}`).join(' · ')} · <b>fair</b> leave-one-out consensus of two-sided sources (books de-vigged, exchanges at the mid ×1.5) · <b>anytime TD</b> YES prices scaled to the team's expected scorers from the game logs · <b>model</b> RAINMAN prop model on ${J.n_model} NFL player-markets · pulled ${esc(J.asof)} · built ${esc(J.built)} · information, not advice — confirm the price and your book's rules`}
function render(){header();({edges,shop,steam,clv}[VIEW]||edges)()}
$('#q').onclick=()=>{$('#how').style.display='block'};$('#how').onclick=e=>{if(e.target.id==='how')$('#how').style.display='none'};window.addEventListener('hashchange',()=>{const v=location.hash.replace('#','');if(v&&v!==VIEW){VIEW=v;render()}});
foot();render();
"""

def page(G, lines, board, arbs, evs, mv, close, asof_, n_model):
    games = {k: dict(id=k, lg=g['lg'], date=g['date'], away=g['away'], home=g['home'], away_logo=g['away_logo'], home_logo=g['home_logo'], tv=(g['tv'] or '').split(',')[0]) for k, g in G.items() if any(l['event_id'] == k for l in lines)}
    used = {l['source'] for l in lines}
    src = {'DK': dict(name='DraftKings', kind='sportsbook'), 'KAL': dict(name='Kalshi', kind='exchange'), 'POLY': dict(name='Polymarket', kind='exchange')}
    for c, n in BOOKS.values():
        if c in used and c not in src: src[c] = dict(name=n, kind='sportsbook')
    src = {k: v for k, v in src.items() if k in used}
    slim = [{k: l[k] for k in ('league', 'event_id', 'market', 'selection', 'point', 'source', 'eff_dec', 'implied', 'fee', 'note', 'player', 'stat', 'liq') if k in l} for l in lines]
    J = dict(games=games, lines=slim, board=board, arbs=arbs, evs=evs, moves=mv[:300], close=close, src=src, asof=asof_, n_model=n_model, built=datetime.now().strftime('%Y-%m-%d %H:%M'))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · Arb Engine</title>{HEAD}<style>{CSS}</style></head><body>
<div id="hdr"><a class="brand" href="index.html"><i>◍</i>RAINMAN<small>ARB ENGINE</small></a><div class="tabs" id="tabs"></div><div class="lg" id="lgs"></div><span class="bk">bankroll $<input id="bank" type="number" step="100"></span><span class="meta" id="plays"></span><span class="hl"><a href="index.html">all sports</a><a href="social.html">social</a></span><button class="q" id="q" title="how it works">?</button></div>
<main><div id="view"></div><div class="foot" id="foot"></div></main>
<div id="how"><div class="box"><h3>How the Arb Engine prices a bet</h3>
<h5>Sources</h5><p>Every main line (moneyline, spread, total) and main player prop at DraftKings, FanDuel, BetMGM, BetRivers and ESPN BET through The Odds API, plus the Kalshi and Polymarket exchanges (YES at the ask, the other side at 1 − bid; Kalshi's 7% × P × (1−P) taker fee is added to the cost). Started games are dropped — live prices are not a market we price.</p>
<h5>Fair probability</h5><p>Each source that quotes both sides gives one fair: books are de-vigged proportionally, exchanges use the mid-point (weighted 1.5×). The fair for a price at book X is the consensus of every source <i>except X</i> — a book cannot vouch for its own number. Anytime TD is quoted YES-only, so each team's YES prices are scaled to the team's expected number of distinct scorers (season average from the game logs × team implied total); anything under 10% is shown but never called an edge.</p>
<h5>Edge and stake</h5><p>Edge = fair × decimal price − 1. Stake = ¼ Kelly of the bankroll in the header. The RAINMAN prop model (NFL, players with real usage) is shown beside the market as an independent opinion, never mixed into the fair.</p>
<h5>Confidence A / B / C</h5><p>0–100 from: how many two-sided sources set the fair (1 → 30, 2 → 52, 3 → 66, 4 → 76, 5+ → 84), minus how much they disagree (−1 per point of spread in their fairs), +8 when an exchange is among them, ±10 for the consensus moving toward or away from the bet since the opener, −10/−25 when the edge is over 8% / 15% (usually a stale or limited line), capped at 60 for YES-only markets. A ≥ 70, B ≥ 50.</p>
<h5>Steam and CLV</h5><p>Every Odds API pull saves one consensus snapshot per market. STEAM shows the opener → latest path. CLV scores each saved play against the latest (or closing) consensus for its side: positive means you beat the market's final number — the only durable evidence an edge is real.</p></div></div>
<div id="toast" class="toast"></div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script><script>{JS}</script></body></html>"""

def main():
    G = slate()
    oa, has_dk = load_oddsapi(G)
    lines = (load_dk(G) if not has_dk else []) + oa + load_props(G) + load_kalshi(G) + load_poly(G)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    lines = [l for l in lines if l['kickoff'] > now]                     # pre-game only: a started game's prices are live, not a market we price
    M = load_model()
    board, arbs, evs, H = analyse(lines, G, M); mv = movers(G, H); CL = closes(G, H, now)
    os.makedirs('data/processed', exist_ok=True)
    write_csv('data/processed/lines_all.csv', lines); write_csv('data/processed/arb_board.csv', board); write_csv('data/processed/arb_opps.csv', arbs); write_csv('data/processed/ev_opps.csv', evs); (write_csv('data/processed/line_moves.csv', mv) if mv else open('data/processed/line_moves.csv', 'w').write('league,event_id,kickoff,away,home,market,player,stat,open_ts,last_ts,snaps,open_line,line,d_line,open_p,p,d_p,n_books\n'))
    asof_ = max([asof(latest(p)) for p in ('draftkings', 'kalshi', 'polymarket') if latest(p)] or [''])
    open('dashboard/arb.html', 'w', encoding='utf-8').write(page(G, lines, board, arbs, evs, mv, CL, asof_, len(M)))
    by = {}
    for l in lines: by[l['source']] = by.get(l['source'], 0) + 1
    print(f'arb: {len(lines)} lines {by} · {len(board)} markets ({sum(1 for b in board if b["stat"] == "anytime_td")} anytime TD, model on {sum(1 for b in board if b["model_p"] != "")}) · {len(arbs)} arbs · {len(evs)} edges ({sum(1 for e in evs if e["tier"] == "A" and e["ev"] >= 0.02)} A ≥2%) · {len(mv)} movers · dashboard/arb.html {os.path.getsize("dashboard/arb.html")//1024} KB')

if __name__ == '__main__':
    main()
