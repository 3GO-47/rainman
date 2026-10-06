"""NCAA game lines -> ncaa/data/processed/game_lines.csv + game_model.csv (market columns only; the dashboard's game cards,
implied totals, ATS / O-U records and team trend charts read these — there is no college pick model).

Usage: python3 scripts/ncaa/build_lines.py
Inputs : ncaa/data/raw/line_odds.parquet         CFBD closing + opening lines by book, 2024-25 (DraftKings > ESPN Bet > Bovada)
         ncaa/data/raw/espn_lines_{season}_*.txt  ESPN scoreboard / summary odds pulled in Chrome (see notes/scrape_recipe.md):
                                                  GL|season|week|event|away_id|home_id|away|home|home_spread_close|home_spread_open|
                                                  total_close|total_open|home_ml|away_ml|provider|kick|status   (later files win)
         ncaa/data/processed/games_{season}.csv   scores, kickoff, teams
Conventions follow nflverse: spread_line > 0 = home favored by that much; result = home - away; total = points scored.
"""
import os, csv, glob, re
import pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
P, RAW = 'ncaa/data/processed/', 'ncaa/data/raw/'
BOOK_PREF = {'DraftKings': 0, 'Draft Kings': 0, 'ESPN Bet': 1, 'ESPN BET': 1, 'Bovada': 2}

def num(v):
    try:
        f = float(str(v).replace('+', ''))
        return None if f != f else f
    except (TypeError, ValueError): return None

def main():
    teams = {int(r['team_id']): r['code'] for r in csv.DictReader(open(P + 'teams.csv', encoding='utf-8'))}
    lines = {}   # game_id -> dict(spread_line, total_line, home_ml, away_ml, open_spread, open_total, book)
    if os.path.exists(RAW + 'line_odds.parquet'):
        L = pd.read_parquet(RAW + 'line_odds.parquet')
        L = L[L.season >= 2024].copy(); L['pref'] = L.book.map(BOOK_PREF).fillna(9)
        for gid, g in L.groupby('game_id'):
            g = g[g.pref == g.pref.min()]
            d = {'book': g.book.iloc[0], 'spread_line': None, 'total_line': None, 'home_ml': None, 'away_ml': None, 'open_spread': None, 'open_total': None}
            if g.home_team_id.isna().all(): continue
            hid = int(g.home_team_id.dropna().iloc[0]); hcode = teams.get(hid)
            for r in g.itertuples():
                if r.market_type == 'spread' and str(r.abbr) == hcode and num(r.lines) is not None:
                    d['spread_line'] = -num(r.lines); d['open_spread'] = -num(r.opening_lines) if num(r.opening_lines) is not None else None
                elif r.market_type == 'total' and str(r.abbr) == 'over':
                    d['total_line'] = num(r.lines); d['open_total'] = num(r.opening_lines)
                elif r.market_type == 'money_line':
                    if str(r.abbr) == hcode: d['home_ml'] = num(r.odds)
                    else: d['away_ml'] = num(r.odds)
            if d['spread_line'] is None and d['total_line'] is None: continue
            lines[int(gid)] = d
    for f in sorted(glob.glob(RAW + 'espn_lines_*.txt')):
        for line in open(f, encoding='utf-8'):
            if not line.startswith('GL|'): continue
            x = line.rstrip('\n').split('|')
            if len(x) < 15: continue
            gid = int(x[3]); hs, ho, tc, to, hml, aml = (num(v) for v in x[8:14])
            if hs is None and tc is None: continue
            lines[gid] = {'book': x[14] or 'ESPN', 'spread_line': -hs if hs is not None else None, 'open_spread': -ho if ho is not None else None,
                          'total_line': tc, 'open_total': to, 'home_ml': hml, 'away_ml': aml}
    out = []
    for gf in sorted(glob.glob(P + 'games_[0-9]*.csv')):
        season = int(re.findall(r'(\d{4})', gf)[-1])
        for g in csv.DictReader(open(gf, encoding='utf-8')):
            gid = int(g['boxscore']); d = lines.get(gid, {})
            hp, ap = num(g['home_pts']), num(g['vis_pts'])
            done = g['completed'] == '1' and hp is not None
            k = g['kick_utc']
            out.append({'game_id': gid, 'season': season, 'week': int(g['week']), 'gameday': g['date'], 'weekday': '', 'gametime': k[11:16],
                        'away_team': g['vis'], 'home_team': g['home'], 'away_score': int(ap) if done else '', 'home_score': int(hp) if done else '',
                        'result': int(hp - ap) if done else '', 'total': int(hp + ap) if done else '',
                        'spread_line': d.get('spread_line', ''), 'total_line': d.get('total_line', ''), 'open_spread': d.get('open_spread', ''), 'open_total': d.get('open_total', ''),
                        'away_moneyline': int(d['away_ml']) if d.get('away_ml') is not None else '', 'home_moneyline': int(d['home_ml']) if d.get('home_ml') is not None else '',
                        'book': d.get('book', ''), 'neutral': g['neutral'], 'roof': '', 'away_qb_name': '', 'home_qb_name': '', 'away_rest': '', 'home_rest': ''})
    cols = list(out[0].keys())
    with open(P + 'game_lines.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
    # game_model.csv: the shape the dashboard's bets payload reads (model columns blank — no NCAA pick model)
    mcols = ['game_id', 'season', 'week', 'gameday', 'away_team', 'home_team', 'away_score', 'home_score', 'result', 'total', 'spread_line', 'total_line',
             'away_moneyline', 'home_moneyline', 'model_spread', 'model_total', 'win_prob_home', 'pick_ats', 'pick_total', 'pick_ml', 'res_ats', 'res_total', 'res_ml',
             'away_rest', 'home_rest', 'roof', 'away_qb_name', 'home_qb_name', 'book', 'open_spread', 'open_total', 'neutral']
    with open(P + 'game_model.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=mcols, extrasaction='ignore'); w.writeheader()
        for r in out: w.writerow({**{c: '' for c in mcols}, **r})
    n = sum(1 for r in out if r['spread_line'] != '')
    by = {}
    for r in out:
        if r['spread_line'] != '': by[r['season']] = by.get(r['season'], 0) + 1
    print(f'game_lines.csv: {len(out)} games · {n} with a spread · by season {by}')

if __name__ == '__main__':
    main()
