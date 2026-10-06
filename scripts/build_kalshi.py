"""Kalshi NFL markets -> data/processed/kalshi_markets.csv (every ladder rung) + kalshi_implied.csv (one implied line /
probability per subject × market). Kalshi is an exchange, so these are real two-sided prices (yes bid / yes ask in dollars =
probability), not a book's juiced line.

Usage: python3 scripts/build_kalshi.py
Input : data/raw/kalshi_YYYY-MM-DD.txt  (latest file wins; see notes/scrape_recipe.md — pulled in Chrome from kalshi.com)
        K|series|event|subject|rungs(strike:yes_bid/yes_ask/volume;...)|close_date
Series: GAME (team wins), SPREAD (team wins by over X), TOTAL (over X points), PASSYDS, PASSATT, PASSTDS, PASSCOMP, PASSINT,
        RSHYDS, RSHATT, REC, RECYDS, TD (player scores X+ TDs; 0.5 = anytime), FIRSTTD
Implied line = the strike where P(yes) crosses .50, linearly interpolated between rungs (a ladder is a CDF).
"""
import os, re, csv, glob, datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
P = 'data/processed/'
CODES = ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','LV','MIA','MIN','NE','NO','NYG','NYJ','PHI','PIT','SEA','SF','TB','TEN','WAS']
ALIAS = {'JAC': 'JAX', 'WSH': 'WAS', 'LA': 'LAR'}
NAMES = {'Arizona': 'ARI', 'Atlanta': 'ATL', 'Baltimore': 'BAL', 'Buffalo': 'BUF', 'Carolina': 'CAR', 'Chicago': 'CHI', 'Cincinnati': 'CIN',
         'Cleveland': 'CLE', 'Dallas': 'DAL', 'Denver': 'DEN', 'Detroit': 'DET', 'Green Bay': 'GB', 'Houston': 'HOU', 'Indianapolis': 'IND',
         'Jacksonville': 'JAX', 'Kansas City': 'KC', 'Los Angeles C': 'LAC', 'Los Angeles R': 'LAR', 'Las Vegas': 'LV', 'Miami': 'MIA',
         'Minnesota': 'MIN', 'New England': 'NE', 'New Orleans': 'NO', 'New York G': 'NYG', 'New York J': 'NYJ', 'Philadelphia': 'PHI',
         'Pittsburgh': 'PIT', 'Seattle': 'SEA', 'San Francisco': 'SF', 'Tampa Bay': 'TB', 'Tennessee': 'TEN', 'Washington': 'WAS'}
NICK = {'Cardinals': 'ARI', 'Falcons': 'ATL', 'Ravens': 'BAL', 'Bills': 'BUF', 'Panthers': 'CAR', 'Bears': 'CHI', 'Bengals': 'CIN', 'Browns': 'CLE',
        'Cowboys': 'DAL', 'Broncos': 'DEN', 'Lions': 'DET', 'Packers': 'GB', 'Texans': 'HOU', 'Colts': 'IND', 'Jaguars': 'JAX', 'Chiefs': 'KC',
        'Chargers': 'LAC', 'Rams': 'LAR', 'Raiders': 'LV', 'Dolphins': 'MIA', 'Vikings': 'MIN', 'Patriots': 'NE', 'Saints': 'NO', 'Giants': 'NYG',
        'Jets': 'NYJ', 'Eagles': 'PHI', 'Steelers': 'PIT', 'Seahawks': 'SEA', '49ers': 'SF', 'Buccaneers': 'TB', 'Titans': 'TEN', 'Commanders': 'WAS'}
MARKET = {'GAME': 'moneyline', 'SPREAD': 'spread', 'TOTAL': 'total', 'PASSYDS': 'pass_yds', 'PASSATT': 'pass_att', 'PASSTDS': 'pass_td',
          'PASSCOMP': 'completions', 'PASSINT': 'interceptions', 'RSHYDS': 'rush_yds', 'RSHATT': 'rush_att', 'REC': 'receptions',
          'RECYDS': 'rec_yds', 'TD': 'anytime_td', 'FIRSTTD': 'first_td'}
MON = {m: i for i, m in enumerate(['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'], 1)}

def norm(n):
    import unicodedata
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode()
    n = re.sub(r"[.'\-]", '', n).lower()
    return re.sub(r'\s+(jr|sr|ii|iii|iv|v)$', '', n.strip())

def split_event(ev):
    """26OCT08TBDAL -> (date, away, home)"""
    m = re.match(r'(\d\d)([A-Z]{3})(\d\d)([A-Z]+)$', ev)
    if not m: return None, None, None
    yy, mon, dd, teams = m.groups()
    date = datetime.date(2000 + int(yy), MON[mon], int(dd))
    for i in range(2, 4):
        a, h = teams[:i], teams[i:]
        a, h = ALIAS.get(a, a), ALIAS.get(h, h)
        if a in CODES and h in CODES: return date, a, h
    return date, None, None

def team_of(subject):
    if subject in NAMES: return NAMES[subject]
    for nick, code in NICK.items():
        if subject.endswith(nick): return code
    m = re.match(r'^([A-Z]{2,4}) ', subject)
    if m and ALIAS.get(m.group(1), m.group(1)) in CODES: return ALIAS.get(m.group(1), m.group(1))
    return ''

def implied(rungs):
    """rungs: list of (strike, p_mid) for 'over strike' markets -> strike where p crosses .5 (interpolated)."""
    r = sorted([(s, p) for s, p in rungs if s is not None], key=lambda x: x[0])
    if not r: return None
    if r[0][1] <= .5: return r[0][0] - (0.5 if r[0][0] % 1 else 0.0)   # even the lowest rung is < 50%: line sits below it
    if r[-1][1] >= .5: return r[-1][0] + 0.5
    for (s1, p1), (s2, p2) in zip(r, r[1:]):
        if p1 >= .5 >= p2:
            if p1 == p2: return (s1 + s2) / 2
            return round(s1 + (p1 - .5) / (p1 - p2) * (s2 - s1), 1)
    return None

def main():
    files = sorted(glob.glob('data/raw/kalshi_*.txt'))
    if not files: print('no kalshi raw files'); return
    raw = files[-1]; pulled = re.findall(r'(\d{4}-\d\d-\d\d)', raw)[-1]
    games = list(csv.DictReader(open(P + 'games_2026.csv', encoding='utf-8')))
    def week_of(date, a, h):
        for g in games:
            if {g['vis'], g['home']} == {a, h}:
                d = datetime.date.fromisoformat(g['date'])
                if abs((d - date).days) <= 1: return int(g['week'])
        return ''
    dc = list(csv.DictReader(open(sorted(glob.glob(P + 'depth_charts_*.csv'))[-1], encoding='utf-8')))
    by_team = {}
    for r in dc: by_team.setdefault(r['team'], []).append(r)
    def player_of(name, teams):
        n = norm(name); last = norm(name.split()[-1]); fi = name[0].lower()
        for t in teams:
            for r in by_team.get(t, []):
                if norm(r['player']) == n: return r['player'], r.get('log_name') or r['player'], t, r['slot']
        for t in teams:
            hit = [r for r in by_team.get(t, []) if norm(r['player'].split()[-1]) == last and r['player'][0].lower() == fi]
            if len(hit) == 1: return hit[0]['player'], hit[0].get('log_name') or hit[0]['player'], t, hit[0]['slot']
        return name, name, '', ''
    rows, imp = [], []
    for line in open(raw, encoding='utf-8'):
        if not line.startswith('K|'): continue
        _, series, ev, subject, rungs, close = line.rstrip('\n').split('|')
        date, away, home = split_event(ev)
        if not away: continue
        week = week_of(date, away, home)
        market = MARKET.get(series, series.lower())
        team, player, log_name, slot = '', '', '', ''
        if series in ('GAME', 'SPREAD'): team = team_of(subject)
        elif series == 'TOTAL': team = ''
        elif subject.endswith('D/ST'): team = team_of(subject.replace(' D/ST', '')); player = team + ' D/ST'
        else: player, log_name, team, slot = player_of(subject, [away, home])
        pts = []
        for rung in rungs.split(';'):
            if not rung: continue
            s, rest = rung.split(':', 1); bid, ask, vol = rest.split('/')
            strike = float(s) if s else None; bid, ask = float(bid), float(ask); mid = round((bid + ask) / 2, 3)
            rows.append({'pulled': pulled, 'week': week, 'date': date.isoformat(), 'away': away, 'home': home, 'series': series, 'market': market,
                         'subject': subject, 'team': team, 'player': player, 'log_name': log_name, 'slot': slot, 'strike': '' if strike is None else strike,
                         'p_bid': bid, 'p_ask': ask, 'p_mid': mid, 'volume': vol, 'close': close})
            pts.append((strike, mid, bid, ask, float(vol)))
        if not pts: continue
        base = {'pulled': pulled, 'week': week, 'date': date.isoformat(), 'away': away, 'home': home, 'market': market, 'subject': subject,
                'team': team, 'player': player, 'log_name': log_name, 'slot': slot, 'volume': round(sum(p[4] for p in pts)), 'close': close}
        if series == 'GAME':
            imp.append({**base, 'kind': 'prob', 'line': '', 'p_mid': pts[0][1], 'p_bid': pts[0][2], 'p_ask': pts[0][3]})
        elif series in ('TD', 'FIRSTTD'):
            for s, mid, bid, ask, v in pts:
                imp.append({**base, 'market': market if s == 0.5 else f'{market}_{int(s + 0.5)}plus', 'kind': 'prob', 'line': s, 'p_mid': mid, 'p_bid': bid, 'p_ask': ask})
        else:
            ln = implied([(s, m) for s, m, *_ in pts])
            near = min(pts, key=lambda p: abs(p[1] - .5))
            imp.append({**base, 'kind': 'line', 'line': ln, 'p_mid': near[1], 'p_bid': near[2], 'p_ask': near[3], 'near_strike': near[0]})
    with open(P + 'kalshi_markets.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    cols = ['pulled', 'week', 'date', 'away', 'home', 'market', 'kind', 'subject', 'team', 'player', 'log_name', 'slot', 'line', 'near_strike', 'p_mid', 'p_bid', 'p_ask', 'volume', 'close']
    with open(P + 'kalshi_implied.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader()
        for r in imp: w.writerow({**{c: '' for c in cols}, **r})
    by = {}
    for r in imp: by[r['market']] = by.get(r['market'], 0) + 1
    unmatched = sorted({r['subject'] for r in imp if r['market'] not in ('moneyline', 'spread', 'total') and not r['slot'] and not r['player'].endswith('D/ST')})
    print(f'kalshi_markets.csv: {len(rows)} rungs · kalshi_implied.csv: {len(imp)} subjects · {by}')
    if unmatched: print('  players not on a depth chart: ' + ', '.join(unmatched[:20]))

if __name__ == '__main__':
    main()
