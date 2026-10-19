"""The books' current spread and total for NFL games that haven't kicked off.

lines_all.csv (built by scripts/build_arb.py from every pull the loop makes: DraftKings via ESPN, The Odds API's US books,
the exchanges) is refreshed every few hours; nflverse's games.csv carries a single line that updates about once a day and
can trail the market by a field goal. For games still to play the site uses the median across books; once a game kicks off
its line freezes and the closing line stays nflverse's (game_lines.csv)."""
import csv, datetime, os, statistics

FIX = {'WSH': 'WAS', 'JAC': 'JAX', 'LA': 'LAR', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}

def consensus(path='data/processed/lines_all.csv', now=None):
    """{(away, home): (spread, total, n_books)} for games not yet started; spread in nflverse's convention (+ = home favoured)."""
    if not os.path.exists(path): return {}
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    sp, to = {}, {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        if r.get('league') != 'nfl' or r.get('market') not in ('spread', 'total') or r.get('point') in ('', None): continue
        k = (r.get('kickoff') or '')[:16]
        try:
            if k and datetime.datetime.strptime(k, '%Y-%m-%dT%H:%M') <= now: continue
        except ValueError: pass
        a, h = FIX.get(r['away'], r['away']), FIX.get(r['home'], r['home']); sel = FIX.get(r['selection'], r['selection'])
        src = r.get('source') or ''
        try: pt = float(r['point'])
        except ValueError: continue
        if r['market'] == 'spread' and sel == h: sp.setdefault((a, h), {})[src] = -pt
        elif r['market'] == 'total' and str(sel).lower().startswith('o'): to.setdefault((a, h), {})[src] = pt
    return {k: (float(statistics.median(sp[k].values())), float(statistics.median(to[k].values())), min(len(sp[k]), len(to[k]))) for k in sp if k in to}

if __name__ == '__main__':
    for k, v in sorted(consensus().items()): print(k, v)
