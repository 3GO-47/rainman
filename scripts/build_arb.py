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
import csv, glob, json, os, re
from datetime import datetime
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
def asof(path): return re.search(r'(\d{4}-\d{2}-\d{2})', path).group(1) if path else ''
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
            rows.append(row(g, 'moneyline', team, '', 'KAL', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
        elif series.endswith('SPREAD'):
            m = re.match(r'([A-Z]{2,3}) .*wins by over ([\d.]+)', sub)
            if not m: continue
            team = KAL_ABBR.get(m.group(1), m.group(1)); pt = float(m.group(2))
            if team not in (g['away'], g['home']): continue
            other = g['home'] if team == g['away'] else g['away']
            rows.append(row(g, 'spread', team, -pt, 'KAL', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            rows.append(row(g, 'spread', other, pt, 'KAL', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}'))
        elif series.endswith('TOTAL'):
            m = re.search(r'([\d.]+)', strike or sub)
            if not m: continue
            pt = float(m.group(1))
            rows.append(row(g, 'total', 'Over', pt, 'KAL', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            rows.append(row(g, 'total', 'Under', pt, 'KAL', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}'))
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
        if r['side'] not in ('Over', 'Under') or r['line'] == '': continue
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
        slug, kind, end, q, t, ln, outs, prices, bid, ask = p[1], p[2], p[3], p[5], p[6], p[7], p[8], p[9], p[10], p[11]
        m = re.match(r'([a-z]+)-([a-z0-9]+)-([a-z0-9]+)-(\d{4}-\d{2}-\d{2})', slug)
        if not m or kind != 'game' or not bid or not ask: continue
        lg = m.group(1)
        outs = outs.split(','); bid, ask = float(bid), float(ask)
        g = None
        if t == 'moneyline':
            a_t, h_t = nick.get((lg, outs[0])), nick.get((lg, outs[1]))
            if a_t and h_t: g = find_game(G, lg, a_t, h_t, m.group(4))
            if not g: continue
            # outcome order on Polymarket is away, home
            rows.append(row(g, 'moneyline', a_t, '', 'POLY', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            rows.append(row(g, 'moneyline', h_t, '', 'POLY', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}'))
        elif t == 'spreads':
            fav, dog = nick.get((lg, outs[0])), nick.get((lg, outs[1]))
            if fav and dog: g = find_game(G, lg, fav, dog, m.group(4))
            if not g or not ln: continue
            pt = float(ln)
            rows.append(row(g, 'spread', fav, pt, 'POLY', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            rows.append(row(g, 'spread', dog, -pt, 'POLY', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}'))
        elif t == 'totals':
            mm = re.match(r'(.+?) vs\. (.+?): O/U', q)
            if not mm: continue
            a_t, h_t = nick.get((lg, mm.group(1).split()[-1])), nick.get((lg, mm.group(2).split()[-1]))
            if a_t and h_t: g = find_game(G, lg, a_t, h_t, m.group(4))
            if not g or not ln: continue
            pt = float(ln)
            rows.append(row(g, 'total', 'Over', pt, 'POLY', 1 / ask, ask, a_, f'yes {bid:.2f}/{ask:.2f}'))
            rows.append(row(g, 'total', 'Under', pt, 'POLY', 1 / (1 - bid), 1 - bid, a_, f'no @ {1 - bid:.2f}'))
    return rows

# ------------------------------------------------------------------------------------------------ two-way markets, fair prices, arbs, EV
def pair_key(r):
    """Spreads pair on the AWAY team's handicap: away +3.5 ↔ home −3.5 are the two sides of one market."""
    if r['market'] == 'moneyline': return (r['event_id'], 'moneyline', '')
    if r['market'] == 'spread': return (r['event_id'], 'spread', float(r['point']) if r['selection'] == r['away'] else -float(r['point']))
    if r['market'] == 'prop': return (r['event_id'], 'prop|' + r['stat'] + '|' + r['player'], float(r['point']))
    return (r['event_id'], 'total', float(r['point']))

def side_of(r, g):
    if r['market'] in ('total', 'prop'): return 'A' if r['selection'] == 'Over' else 'B'
    return 'A' if r['selection'] == g['away'] else 'B'

def analyse(rows, G):
    by = {}
    for r in rows: by.setdefault(pair_key(r), []).append(r)
    board, arbs, evs = [], [], []
    for key, R in by.items():
        g = G[key[0]]; A = [r for r in R if side_of(r, g) == 'A']; B = [r for r in R if side_of(r, g) == 'B']
        if not A or not B: continue
        # fair probability: per source with both sides → normalize; exchanges use mid-points (no fee); average over sources
        fairs = []
        for s in SRC:
            a = next((x for x in A if x['source'] == s), None); b = next((x for x in B if x['source'] == s), None)
            if not a or not b: continue
            if KIND[s] == 'exchange':
                pa = (float(a['implied']) + (1 - float(b['implied']))) / 2    # mid of (ask for A) and (1 − ask for B)
            else:
                pa = a['implied'] / (a['implied'] + b['implied'])
            fairs.append(pa)
        if not fairs: continue
        fair_a = sum(fairs) / len(fairs); fair_b = 1 - fair_a
        bestA = max(A, key=lambda x: x['eff_dec']); bestB = max(B, key=lambda x: x['eff_dec'])
        sum_inv = 1 / bestA['eff_dec'] + 1 / bestB['eff_dec']
        selA = bestA['selection'] + (f" {bestA['point']:+g}" if bestA['market'] == 'spread' else f" {bestA['point']}" if bestA['market'] in ('total', 'prop') else '')
        selB = bestB['selection'] + (f" {bestB['point']:+g}" if bestB['market'] == 'spread' else f" {bestB['point']}" if bestB['market'] in ('total', 'prop') else '')
        mk = 'prop' if key[1].startswith('prop|') else key[1]
        rec = dict(league=g['lg'], event_id=g['id'], kickoff=g['date'], away=g['away'], home=g['home'], market=mk, line=key[2], side_a=selA, side_b=selB,
                   player=bestA.get('player', ''), stat=bestA.get('stat', ''),
                   fair_a=round(fair_a, 4), fair_b=round(fair_b, 4), sources=len(fairs),
                   best_a_src=bestA['source'], best_a_dec=bestA['eff_dec'], best_a_american=american(bestA['eff_dec']), best_b_src=bestB['source'], best_b_dec=bestB['eff_dec'], best_b_american=american(bestB['eff_dec']),
                   hold=round(sum_inv - 1, 4), ev_a=round(fair_a * bestA['eff_dec'] - 1, 4), ev_b=round(fair_b * bestB['eff_dec'] - 1, 4))
        rec['best_ev'] = max(rec['ev_a'], rec['ev_b']); board.append(rec)
        if sum_inv < 1:
            margin = 1 - sum_inv; stake_a = (1 / bestA['eff_dec']) / sum_inv * 100; stake_b = 100 - stake_a
            arbs.append(dict(**{k: rec[k] for k in ('league', 'event_id', 'kickoff', 'away', 'home', 'market', 'line', 'side_a', 'side_b', 'best_a_src', 'best_a_dec', 'best_b_src', 'best_b_dec', 'player', 'stat')},
                             margin=round(margin, 4), stake_a_per_100=round(stake_a, 2), stake_b_per_100=round(stake_b, 2), profit_per_100=round(100 * margin / sum_inv, 2)))
        for side, lst, fair in (('A', A, fair_a), ('B', B, fair_b)):
            for r in lst:
                ev = fair * r['eff_dec'] - 1
                if ev >= 0.01:
                    kelly = max(0, (fair * r['eff_dec'] - 1) / (r['eff_dec'] - 1))
                    evs.append(dict(league=g['lg'], event_id=g['id'], kickoff=g['date'], away=g['away'], home=g['home'], market=r['market'], selection=r['selection'], point=r['point'], source=r['source'], player=r.get('player', ''), stat=r.get('stat', ''),
                                    dec=r['eff_dec'], american=american(r['eff_dec']), fair=round(fair, 4), ev=round(ev, 4), kelly_quarter=round(kelly / 4, 4), sources=len(fairs)))
    board.sort(key=lambda r: -r['best_ev']); arbs.sort(key=lambda r: -r['margin']); evs.sort(key=lambda r: -r['ev'])
    return board, arbs, evs

def write_csv(path, rows):
    if not rows: open(path, 'w').write(''); return
    cols = list(rows[0].keys()) + [k for r in rows for k in r.keys() if k not in rows[0]]
    cols = list(dict.fromkeys(cols))
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

# ------------------------------------------------------------------------------------------------ page
HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">"""
CSS = """
:root{--bg:#000;--panel:#0b0b0c;--s2:#131315;--s3:#1a1a1d;--edge:#1d1e21;--edge2:#2a2b30;--fg:#e6e6e9;--dim:#8b8d94;--mute:#5c5e66;--acc:#e8b339;--green:#3fb950;--red:#f0564a;--blue:#58a6ff;--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;--sans:'Inter',system-ui,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:13px;line-height:1.45}a{color:inherit;text-decoration:none}
#hdr{display:flex;align-items:center;gap:16px;padding:10px 24px;border-bottom:1px solid var(--edge);background:#050506;position:sticky;top:0;z-index:5}.brand{font:800 15px/1 var(--mono);letter-spacing:4px}.brand i{color:var(--acc);font-style:normal;margin-right:6px}.tag{color:var(--dim);font-size:12px}#hdr .right{margin-left:auto;color:var(--mute);font:500 10.5px var(--mono);display:flex;gap:14px;align-items:center}
.hl{display:flex;gap:4px;margin-left:10px}.hl a{font:600 10px var(--mono);letter-spacing:1px;padding:3px 9px;border:1px solid var(--edge2);border-radius:4px;color:var(--dim)}.hl a:hover,.hl a.on{color:var(--fg);border-color:var(--acc)}
.wrap{max-width:1500px;margin:0 auto;padding:16px 24px 40px}h1{font:800 24px/1.15 var(--sans);letter-spacing:-.3px;margin:4px 0 2px}h1 small{display:block;font:400 12.5px/1.5 var(--sans);color:var(--dim);margin-top:5px;max-width:980px}
h2{font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin:22px 0 10px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}h2 span{font:400 11.5px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}.kpi{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:10px 12px}.kpi b{display:block;font:700 20px/1.1 var(--mono)}.kpi span{display:block;font:600 9.5px var(--mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--mute);margin-bottom:4px}.kpi small{color:var(--dim);font-size:11px}.kpi.g b{color:var(--green)}.kpi.a b{color:var(--acc)}
.pintro{display:flex;flex-direction:column;gap:5px;padding:10px 12px;margin:12px 0;background:var(--panel);border:1px solid var(--edge);border-left:3px solid var(--acc);border-radius:8px}.pintro .pw{font-size:12.5px;line-height:1.45}.pintro .pw b{color:var(--acc)}.pintro .ph{display:flex;flex-wrap:wrap;gap:4px 6px}.pintro .ph span{font:500 10.5px/1.5 var(--mono);color:var(--dim);background:var(--s2);border:1px solid var(--edge);border-radius:4px;padding:0 7px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px;align-items:center}.chips button{font:600 10.5px var(--mono);padding:4px 10px;border-radius:5px;border:1px solid var(--edge2);background:var(--panel);color:var(--dim);cursor:pointer;display:inline-flex;align-items:center;gap:6px}.chips button.on{border-color:var(--acc);color:var(--fg);background:rgba(232,179,57,.1)}.chips .sp{flex:1}.chips label{font:500 11px var(--mono);color:var(--dim)}.chips input[type=number]{width:60px;background:var(--s2);border:1px solid var(--edge2);color:var(--fg);border-radius:4px;padding:3px 6px;font:600 11px var(--mono)}
.cov{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}.card{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:12px 14px}.card h3{margin:0 0 8px;font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);display:flex;justify-content:space-between;gap:8px;align-items:baseline}.card h3 span{font:400 11px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}
.brow{display:grid;grid-template-columns:minmax(120px,1fr) 1.4fr auto;gap:8px;align-items:center;padding:4px 0;font-size:12px}.brow .bar{height:10px;background:var(--s3);border-radius:2px;position:relative}.brow .bar i{position:absolute;left:0;top:0;bottom:0;background:var(--blue);border-radius:2px}.brow .n{font:600 11.5px var(--mono);white-space:nowrap}.brow .n small{color:var(--dim);margin-left:5px;font-weight:500}
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:10px}@media (max-width:520px){.wall{grid-template-columns:1fr}}
.gc{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:10px 12px}.gc .gh{display:flex;align-items:center;gap:8px;margin-bottom:6px}.gc .gh img{width:22px;height:22px;object-fit:contain}.gc .gh b{font-size:13px}.gc .gh small{color:var(--dim);font:500 10.5px var(--mono);margin-left:auto;text-align:right}.gc .gh .edge{font:700 10.5px var(--mono);padding:1px 7px;border-radius:4px;background:rgba(63,185,80,.15);color:var(--green)}
.mk{display:grid;grid-template-columns:70px 1fr 1fr;gap:4px 8px;align-items:start;padding:5px 0;border-top:1px solid var(--edge)}.mk .ml{font:600 9.5px var(--mono);letter-spacing:1px;text-transform:uppercase;color:var(--mute);padding-top:4px}.mk .ml small{display:block;color:var(--dim);letter-spacing:0;text-transform:none;font-weight:500;margin-top:2px}
.side{display:flex;flex-direction:column;gap:3px}.side .sn{display:flex;align-items:center;gap:6px;font-size:12px}.side .sn img{width:16px;height:16px;object-fit:contain}.side .sn b{font-weight:600}.side .sn .fair{margin-left:auto;font:600 10px var(--mono);color:var(--dim)}.side .sn .fair b{color:var(--fg)}
.px{display:flex;flex-wrap:wrap;gap:4px}.p{display:inline-flex;align-items:center;gap:5px;font:600 10.5px var(--mono);padding:2px 6px;border-radius:4px;border:1px solid var(--edge2);background:var(--s2);color:var(--dim);cursor:pointer}.p i{font-style:normal;font-weight:700;color:var(--fg)}.p small{font-weight:500;font-size:9.5px}.p.best{border-color:var(--acc);background:rgba(232,179,57,.1)}.p.best i{color:var(--acc)}.p .ev{font-size:9.5px;font-weight:700}.p .ev.g{color:var(--green)}.p .ev.r{color:var(--red)}.p:hover{border-color:var(--fg)}.p.saved{border-style:dashed}
.arb{border:1px solid #274a2b;border-radius:10px;background:#0b120c;padding:10px 12px;display:grid;grid-template-columns:1fr auto;gap:6px 12px;align-items:center}.arb .legs{display:flex;flex-direction:column;gap:3px;font-size:12px}.arb .legs b{font-family:var(--mono)}.arb .m{font:800 18px var(--mono);color:var(--green);text-align:right}.arb .m small{display:block;font:500 10px var(--mono);color:var(--dim)}
table{border-collapse:collapse;width:100%;font-size:12px}th{font:600 9.5px var(--mono);letter-spacing:1px;text-transform:uppercase;color:var(--mute);text-align:left;padding:6px 8px;border-bottom:1px solid var(--edge2);cursor:pointer;white-space:nowrap}th.srt-asc::after{content:' ▲'}th.srt-desc::after{content:' ▼'}td{padding:6px 8px;border-bottom:1px solid var(--edge);white-space:nowrap;vertical-align:middle}tr:hover td{background:var(--s2)}.mono{font-family:var(--mono)}.dim{color:var(--dim)}.g{color:var(--green)}.r{color:var(--red)}.tm{display:inline-flex;align-items:center;gap:5px}.tm img{width:16px;height:16px;object-fit:contain}
.empty{color:var(--mute);padding:12px;border:1px dashed var(--edge2);border-radius:8px;text-align:center}.note{color:var(--mute);font-size:10.5px;margin:8px 0 0}
.toast{position:fixed;right:18px;bottom:18px;background:#15140f;border:1px solid var(--acc);color:var(--fg);padding:8px 12px;border-radius:8px;font:600 11px var(--mono);display:none;z-index:9}
.foot{margin-top:26px;padding-top:12px;border-top:1px solid var(--edge);color:var(--mute);font:400 11px/1.6 var(--sans)}
"""
JS = r"""
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const G=J.games,L=J.lines,B=J.board,A=J.arbs,E=J.evs,SRC=J.src;const TZ='America/Chicago';
const CT=d=>new Date(d).toLocaleString('en-US',{weekday:'short',hour:'numeric',minute:'2-digit',timeZone:TZ}).replace(':00','');
const logo=(g,t)=>{const l=t===g.away?g.away_logo:g.home_logo;return l?`<img src="https://a.espncdn.com/i/teamlogos/${l}" alt="" onerror="this.style.visibility='hidden'">`:''};
const pct=p=>(100*p).toFixed(1)+'%';const am=d=>d>=2?'+'+Math.round((d-1)*100):String(Math.round(-100/(d-1)));
let LG='all',MK='all',EVMIN=1,SORTK='ev',SORTA=false,ONE=false;
// ---- saved plays (local, per browser) — the Social tab reads the same key
const KEY='rainman.plays';const plays=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'[]')}catch(e){return []}};
function savePlay(o){const P=plays();if(P.some(p=>p.id===o.id)){toast('already saved');return}P.push(Object.assign({saved:new Date().toISOString(),status:'open'},o));try{localStorage.setItem(KEY,JSON.stringify(P))}catch(e){}toast('saved to your plays · '+P.length);render()}
function toast(m){const t=$('#toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(()=>t.style.display='none',1800)}
const lgs=[...new Set(B.map(b=>b.league))];
function kpis(){const n=L.length,ev=B.filter(b=>b.best_ev>=EVMIN/100).length;const best=B[0];
  $('#kpis').innerHTML=`<div class="kpi"><span>lines quantified</span><b>${n}</b><small>${new Set(L.map(l=>l.event_id)).size} games · ${new Set(L.map(l=>l.source)).size} sources</small></div><div class="kpi"><span>two-way markets</span><b>${B.length}</b><small>priced at ${B.filter(b=>b.sources>=2).length>0?'2+':'1'} sources: ${B.filter(b=>b.sources>=2).length}</small></div><div class="kpi ${A.length?'g':''}"><span>arbitrage</span><b>${A.length}</b><small>${A.length?'best '+pct(A[0].margin)+' guaranteed':'none after fees right now'}</small></div><div class="kpi a"><span>+EV plays ≥ ${EVMIN}%</span><b>${ev}</b><small>${best?'best '+pct(best.best_ev)+' · '+best.side_a.split(' ')[0]+'/'+best.side_b.split(' ')[0]:''}</small></div><div class="kpi"><span>pulled</span><b style="font-size:14px">${esc(J.asof)}</b><small>prices move — re-check before you bet</small></div>`}
function coverage(){const srcs=Object.keys(SRC);const mks=['moneyline','spread','total','prop'];const cnt={};L.forEach(l=>{cnt[l.source+'|'+l.market]=(cnt[l.source+'|'+l.market]||0)+1});const mx=Math.max(1,...Object.values(cnt));
  $('#cov').innerHTML=srcs.map(s=>`<div class="card"><h3>${SRC[s].name} <span>${SRC[s].kind}${SRC[s].fee?' · taker fee '+SRC[s].fee:' · no fee'}</span></h3>${mks.map(m=>`<div class="brow"><span>${m}</span><span class="bar"><i style="width:${(100*(cnt[s+'|'+m]||0)/mx).toFixed(0)}%"></i></span><span class="n">${cnt[s+'|'+m]||0}<small>lines</small></span></div>`).join('')}<p class="note">${esc(SRC[s].how)}</p></div>`).join('')}
function chips(){$('#filt').innerHTML=`<button data-l="all" class="${LG==='all'?'on':''}">all leagues</button>${lgs.map(l=>`<button data-l="${l}" class="${LG===l?'on':''}">${l.toUpperCase()} <span class="dim">${B.filter(b=>b.league===l).length}</span></button>`).join('')}<span style="width:10px"></span>${['all','moneyline','spread','total','prop'].map(m=>`<button data-m="${m}" class="${MK===m?'on':''}">${m==='prop'?'player props':m}</button>`).join('')}<span class="sp"></span><button data-o="1" class="${ONE?'on':''}">${ONE?'hiding':'show'} single-source lines</button><label>show +EV from <input id="evmin" type="number" step="0.5" value="${EVMIN}">%</label>`;
  $('#filt').querySelectorAll('button').forEach(b=>b.onclick=()=>{if(b.dataset.l)LG=b.dataset.l;if(b.dataset.m)MK=b.dataset.m;if(b.dataset.o)ONE=!ONE;render()});$('#evmin').onchange=e=>{EVMIN=+e.target.value||0;render()}}
const keep=b=>(LG==='all'||b.league===LG)&&(MK==='all'||b.market===MK);const keepW=b=>keep(b)&&b.market!=='prop'&&(ONE||b.sources>=2||b.hold<0);const keepP=b=>keep(b)&&b.market==='prop'&&(ONE||b.sources>=2||b.hold<0);
function priceChips(ev,market,line,side,fair){const sel=side.split(' ')[0];const rows=L.filter(l=>l.event_id===ev&&l.market===market&&l.selection===sel&&(market==='moneyline'||(market==='total'?Math.abs(+l.point-line)<1e-9:Math.abs((l.selection===l.away?+l.point:-+l.point)-line)<1e-9)));
  if(!rows.length)return '<span class="dim mono" style="font-size:10px">no price</span>';const best=Math.max(...rows.map(r=>r.eff_dec));const P=plays();
  return rows.sort((a,b)=>b.eff_dec-a.eff_dec).map(r=>{const e=fair*r.eff_dec-1;const id=[r.event_id,r.market,r.selection,r.point,r.source].join('|');return `<span class="p ${r.eff_dec===best?'best':''} ${P.some(p=>p.id===id)?'saved':''}" title="${SRC[r.source].name}: ${r.american} (${pct(r.implied)} implied${r.fee?' + fee '+pct(r.fee):''})${r.note?' · '+esc(r.note):''} · click to save this play" data-id="${esc(id)}"><small>${r.source}</small><i>${am(r.eff_dec)}</i><span class="ev ${e>=0?'g':'r'}">${e>=0?'+':''}${(100*e).toFixed(1)}%</span></span>`}).join('')}
function wall(){const rows=B.filter(keepW);const byG={};rows.forEach(b=>(byG[b.event_id]=byG[b.event_id]||[]).push(b));const games=Object.keys(byG).map(id=>({g:G[id],rows:byG[id],best:Math.max(...byG[id].map(b=>b.best_ev))})).sort((a,b)=>b.best-a.best);
  $('#wall').innerHTML=games.map(({g,rows,best})=>`<div class="gc"><div class="gh">${logo(g,g.away)}<b>${esc(g.away)}</b><span class="dim">@</span>${logo(g,g.home)}<b>${esc(g.home)}</b>${best>=EVMIN/100?`<span class="edge">best +${(100*best).toFixed(1)}%</span>`:''}<small>${CT(g.date)}<br>${esc(g.tv||'')}</small></div>
    ${rows.sort((a,b)=>['moneyline','spread','total'].indexOf(a.market)-['moneyline','spread','total'].indexOf(b.market)||a.line-b.line).map(b=>`<div class="mk"><div class="ml">${b.market}${b.market!=='moneyline'?`<small>${b.market==='spread'?b.away+' '+(b.line>0?'+':'')+b.line:'o/u '+b.line}</small>`:''}<small>${b.sources} src${b.hold<0?' · <b style=\"color:var(--green)\">ARB</b>':''}</small></div>
      <div class="side"><div class="sn">${b.market!=='total'?logo(g,b.side_a.split(' ')[0]):''}<b>${esc(b.side_a)}</b><span class="fair">fair <b>${pct(b.fair_a)}</b></span></div><div class="px">${priceChips(b.event_id,b.market,b.line,b.side_a,b.fair_a)}</div></div>
      <div class="side"><div class="sn">${b.market!=='total'?logo(g,b.side_b.split(' ')[0]):''}<b>${esc(b.side_b)}</b><span class="fair">fair <b>${pct(b.fair_b)}</b></span></div><div class="px">${priceChips(b.event_id,b.market,b.line,b.side_b,b.fair_b)}</div></div></div>`).join('')}</div>`).join('')||'<div class="empty">no priced markets for this filter</div>';
  $('#wall').querySelectorAll('.p[data-id]').forEach(el=>el.onclick=()=>{const [ev,market,sel,point,src]=el.dataset.id.split('|');const g=G[ev];const l=L.find(x=>x.event_id===ev&&x.market===market&&x.selection===sel&&String(x.point)===point&&x.source===src);savePlay({id:el.dataset.id,league:g.lg,game:g.away+' @ '+g.home,kickoff:g.date,market,selection:sel,point,source:src,dec:l.eff_dec,american:am(l.eff_dec),fair:null,from:'arb'})})}
let PSK='best_ev',PSA=false;
function props(){const rows=B.filter(keepP);const el=$('#props');if(!el)return;if(!rows.length){el.innerHTML=`<div class="empty">${B.some(b=>b.market==='prop')?'no player props for this filter':'no player props on file yet — the first prop pull lands once a game is inside the props window (NFL 5 days, CFB 3 days)'}</div>`;return}
  const V={best_ev:r=>r.best_ev,player:r=>r.player,stat:r=>r.stat,line:r=>r.line,game:r=>r.away+r.home,kick:r=>r.kickoff,over:r=>r.best_a_dec,under:r=>r.best_b_dec,fair:r=>r.fair_a,src:r=>r.sources,hold:r=>r.hold};rows.sort((a,b)=>{const x=V[PSK](a),y=V[PSK](b);return (x<y?-1:x>y?1:0)*(PSA?1:-1)});
  const th=(k,l)=>`<th data-k="${k}" class="${PSK===k?(PSA?'srt-asc':'srt-desc'):''}">${l}</th>`;const STAT={pass_yds:'pass yds',pass_td:'pass TD',completions:'completions',pass_att:'pass att',rush_yds:'rush yds',rush_att:'rush att',receptions:'receptions',rec_yds:'rec yds'};
  el.innerHTML=`<table><thead><tr>${th('player','player')}${th('stat','stat')}${th('line','line')}${th('game','game')}${th('kick','kick (CT)')}${th('over','best over')}${th('under','best under')}${th('fair','fair over')}${th('src','books')}${th('hold','hold')}${th('best_ev','best EV')}</tr></thead><tbody>${rows.slice(0,400).map(b=>{const g=G[b.event_id];const cell=(src,dec,ev,sel)=>`<span class="p ${ev>=0?'':''}" data-id="${esc([b.event_id,'prop',sel,b.line,src].join('|'))}" title="click to save"><small>${src}</small><i>${am(dec)}</i><span class="ev ${ev>=0?'g':'r'}">${ev>=0?'+':''}${(100*ev).toFixed(1)}%</span></span>`;
    return `<tr><td><b>${esc(b.player)}</b></td><td class="dim">${STAT[b.stat]||esc(b.stat)}</td><td class="mono">${b.line}</td><td><span class="tm">${logo(g,g.away)}${esc(g.away)}</span> <span class="dim">@</span> <span class="tm">${logo(g,g.home)}${esc(g.home)}</span></td><td class="mono dim">${CT(g.date)}</td><td>${cell(b.best_a_src,b.best_a_dec,b.ev_a,'Over')}</td><td>${cell(b.best_b_src,b.best_b_dec,b.ev_b,'Under')}</td><td class="mono dim">${pct(b.fair_a)}</td><td class="mono dim">${b.sources}</td><td class="mono ${b.hold<0?'g':'dim'}">${(100*b.hold).toFixed(1)}%</td><td class="mono ${b.best_ev>=0?'g':'r'}"><b>${b.best_ev>=0?'+':''}${(100*b.best_ev).toFixed(1)}%</b></td></tr>`}).join('')}</tbody></table>${rows.length>400?`<p class="note">showing the top 400 of ${rows.length} prop markets — narrow the filter</p>`:''}`;
  el.querySelectorAll('th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(PSK===k)PSA=!PSA;else{PSK=k;PSA=false}props()});
  el.querySelectorAll('.p[data-id]').forEach(x=>x.onclick=()=>{const [ev,market,sel,point,src]=x.dataset.id.split('|');const g=G[ev];const b=rows.find(r=>r.event_id===ev&&String(r.line)===point&&x.closest('tr').firstChild.textContent===r.player);const dec=sel==='Over'?b.best_a_dec:b.best_b_dec;savePlay({id:x.dataset.id+'|'+b.player,league:g.lg,game:g.away+' @ '+g.home,kickoff:g.date,market:'prop',selection:`${b.player} ${sel} ${b.line} ${b.stat}`,point,source:src,dec,american:am(dec),fair:sel==='Over'?b.fair_a:b.fair_b,from:'arb'})})}
function arbs(){const rows=A.filter(keep);$('#arbs').innerHTML=rows.length?rows.map(a=>{const g=G[a.event_id];return `<div class="arb"><div class="legs"><span>${logo(g,g.away)} ${esc(g.away)} @ ${logo(g,g.home)} ${esc(g.home)} · <span class="dim">${a.market==='prop'?esc(a.player)+' '+esc(a.stat)+' '+a.line:a.market+(a.market!=='moneyline'?' '+a.line:'')} · ${CT(g.date)}</span></span><span>$${a.stake_a_per_100} on <b>${esc(a.side_a)}</b> at ${SRC[a.best_a_src].name} ${am(a.best_a_dec)}</span><span>$${a.stake_b_per_100} on <b>${esc(a.side_b)}</b> at ${SRC[a.best_b_src].name} ${am(a.best_b_dec)}</span></div><div class="m">+${pct(a.margin)}<small>$${a.profit_per_100} locked per $100 · after exchange fees</small></div></div>`}).join(''):'<div class="empty">no arbitrage after fees in the current pull — the board above still shows where each side is cheapest</div>'}
function evtable(){const rows=E.filter(e=>keep({league:e.league,market:e.market})&&e.ev>=EVMIN/100);const V={ev:r=>r.ev,fair:r=>r.fair,dec:r=>r.dec,kick:r=>r.kickoff,game:r=>r.away+r.home,sel:r=>r.selection,src:r=>r.source,kelly:r=>r.kelly_quarter,market:r=>r.market};rows.sort((a,b)=>{const x=V[SORTK](a),y=V[SORTK](b);return (x<y?-1:x>y?1:0)*(SORTA?1:-1)});
  const th=(k,l)=>`<th data-k="${k}" class="${SORTK===k?(SORTA?'srt-asc':'srt-desc'):''}">${l}</th>`;
  $('#ev').innerHTML=rows.length?`<table><thead><tr>${th('kick','kick (CT)')}${th('game','game')}${th('market','market')}${th('sel','selection')}${th('src','source')}${th('dec','price')}${th('fair','fair')}${th('ev','EV')}${th('kelly','¼ kelly')}<th></th></tr></thead><tbody>${rows.map(r=>{const g=G[r.event_id];const id=[r.event_id,r.market,r.selection,r.point,r.source].join('|');return `<tr><td class="mono dim">${CT(r.kickoff)}</td><td><span class="tm">${logo(g,g.away)}${esc(g.away)}</span> <span class="dim">@</span> <span class="tm">${logo(g,g.home)}${esc(g.home)}</span></td><td class="dim">${r.market}</td><td><b>${r.market==='prop'?esc(r.player)+' '+esc(r.selection)+' '+r.point+' '+esc(r.stat):esc(r.selection)+(r.market==='spread'?' '+(+r.point>0?'+':'')+r.point:r.market==='total'?' '+r.point:'')}</b></td><td>${SRC[r.source].name}</td><td class="mono">${am(r.dec)}</td><td class="mono dim">${pct(r.fair)}</td><td class="mono g"><b>+${(100*r.ev).toFixed(1)}%</b></td><td class="mono dim">${(100*r.kelly_quarter).toFixed(1)}%</td><td><span class="p" data-id="${esc(id)}">save</span></td></tr>`}).join('')}</tbody></table>`:'<div class="empty">nothing clears the threshold — lower it or wait for the next pull</div>';
  $('#ev').querySelectorAll('th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(SORTK===k)SORTA=!SORTA;else{SORTK=k;SORTA=false}evtable()});
  $('#ev').querySelectorAll('.p[data-id]').forEach(el=>el.onclick=()=>{const r=rows.find(x=>[x.event_id,x.market,x.selection,x.point,x.source].join('|')===el.dataset.id);const g=G[r.event_id];savePlay({id:el.dataset.id,league:g.lg,game:g.away+' @ '+g.home,kickoff:g.date,market:r.market,selection:r.selection,point:r.point,source:r.source,dec:r.dec,american:am(r.dec),fair:r.fair,from:'arb'})})}
function render(){kpis();chips();wall();props();arbs();evtable();$('#plays').textContent=plays().length+' saved plays'}
coverage();render();
"""

def page(G, lines, board, arbs, evs, asof_):
    games = {k: dict(lg=g['lg'], date=g['date'], away=g['away'], home=g['home'], away_logo=g['away_logo'], home_logo=g['home_logo'], tv=(g['tv'] or '').split(',')[0]) for k, g in G.items() if any(l['event_id'] == k for l in lines)}
    used = {l['source'] for l in lines}
    src = {'DK': dict(name='DraftKings', kind='sportsbook', fee='', how='moneyline, spread and total with prices (The Odds API when a key is set, otherwise ESPN\'s DraftKings feed)'),
           'KAL': dict(name='Kalshi', kind='exchange', fee='7% × P × (1−P)', how='buy YES at the ask; the other side is NO at 1 − bid; the taker fee is added to the cost'),
           'POLY': dict(name='Polymarket', kind='exchange', fee='', how='away/favorite/Over outcome at the ask; the other side at 1 − bid; three lines nearest the main line kept')}
    for c, n in BOOKS.values():
        if c in used and c not in src: src[c] = dict(name=n, kind='sportsbook', fee='', how='moneyline, spread and total with prices from The Odds API')
    src = {k: v for k, v in src.items() if k in used or k in ('DK', 'KAL', 'POLY')}
    J = dict(games=games, lines=lines, board=board, arbs=arbs, evs=evs, src=src, asof=asof_)
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · Arb Engine</title>{HEAD}<style>{CSS}</style></head><body>
<div id="hdr"><a class="brand" href="index.html"><i>◍</i> RAINMAN</a><span class="tag">Arb Engine · every line, every source</span><span class="hl"><a href="index.html">all sports</a><a class="on" href="arb.html">Arb Engine</a><a href="social.html">Social</a></span><span class="right"><span id="plays"></span><span>pulled {asof_} · built {built}</span></span></div>
<div class="wrap">
<h1>Every line, every source, one number.<small>The same bet priced at every book we can reach — DraftKings, FanDuel, BetMGM, Caesars and more through The Odds API — beside the Kalshi and Polymarket exchanges. Each side gets a fair probability from the consensus of all sources (exchange mid-points, de-vigged book prices), so every price turns into an expected value. When the two sides of one market pay out more than 100% combined across sources, that's an arbitrage and the stake split is shown. Exchange fees are already in the prices.</small></h1>
<div class="pintro"><div class="pw"><b>How to read it</b> — gold chip = the best price for that side · the % on a chip = expected value at that price (green = you are paid more than fair, red = less) · fair = the consensus probability · click any chip to save it as a play.</div><div class="ph"><span>prices in American odds, fees included</span><span>Kalshi: YES at the ask, NO at 1 − bid, 7% × P × (1−P) taker fee</span><span>Polymarket: outcome at the ask, other side at 1 − bid</span><span>spreads and totals compare only at the same number</span><span>a pull is a snapshot — prices move</span></div></div>
<div id="kpis" class="kpis"></div>
<h2>coverage <span>how many lines each source contributes, by market — the quantification layer every other number is built on</span></h2><div id="cov" class="cov"></div>
<h2>arbitrage <span>both sides covered across sources for a guaranteed return, fees included · stake split per $100</span></h2><div id="arbs" style="display:grid;gap:8px"></div>
<h2>the board <span>every market priced at two or more sources, best price per side in gold, EV on every chip · sorted by the best edge in the game · single-source lines behind the toggle</span></h2><div id="filt" class="chips"></div><div id="wall" class="wall"></div>
<h2>player props <span>main markets at every book, Over and Under paired at the same line · best price per side, fair = consensus, hold &lt; 0 = arbitrage · sortable</span></h2><div id="props"></div>
<h2>+EV plays <span>every price that beats the consensus by the threshold · sortable · ¼ Kelly = suggested stake as a share of bankroll</span></h2><div id="ev"></div>
<div class="foot">RAINMAN · Arb Engine · lines from the US books via The Odds API (plus DraftKings via ESPN when no key is set), Kalshi (public trade API) and Polymarket (Gamma API), pulled {asof_}; no account, no key. Fair probabilities are a consensus, not a model — they move with the market. This is information, not advice; check the live price and your book's rules before placing anything.</div></div>
<div id="toast" class="toast"></div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script><script>{JS}</script></body></html>"""

def main():
    G = slate()
    oa, has_dk = load_oddsapi(G)
    lines = (load_dk(G) if not has_dk else []) + oa + load_props(G) + load_kalshi(G) + load_poly(G)
    board, arbs, evs = analyse(lines, G)
    os.makedirs('data/processed', exist_ok=True)
    write_csv('data/processed/lines_all.csv', lines); write_csv('data/processed/arb_board.csv', board); write_csv('data/processed/arb_opps.csv', arbs); write_csv('data/processed/ev_opps.csv', evs)
    asof_ = max([asof(latest(p)) for p in ('draftkings', 'kalshi', 'polymarket') if latest(p)] or [''])
    open('dashboard/arb.html', 'w', encoding='utf-8').write(page(G, lines, board, arbs, evs, asof_))
    by = {}
    for l in lines: by[l['source']] = by.get(l['source'], 0) + 1
    print(f'arb: {len(lines)} lines {by} · {len(board)} two-way markets · {len(arbs)} arbs · {len(evs)} +EV ≥1% · dashboard/arb.html {os.path.getsize("dashboard/arb.html")//1024} KB')

if __name__ == '__main__':
    main()
