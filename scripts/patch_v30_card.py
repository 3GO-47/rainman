"""v30 — the card: props are bet only when they pass the strategy (Josh, 2026-10-19: stop betting every prop the books post).

Rules, all on numbers frozen before kickoff (bet_ledger.csv):
  1. the model's edge at the posted price is 6% or more          (edges of 3-6% lost money; 6%+ made it)
  2. the price is between -200 and +200                           (no long-shot strikes, no heavy juice — kills the +4900 lines)
  3. the model's own chance for that side is 50% or more          (never bet a side the model thinks loses, however long the price)
  4. one bet per player per game — his biggest edge               (no stacking receptions + yards on the same man)
  5. at most 3 bets per game — the biggest edges                  (no piling into one game)
Every other prop stays in bet_ledger.csv and picks_all.csv as a lean (bet blank, 'why' says which rule it failed) — research,
never counted as a bet. The card for a game is settled at kickoff: every lean it chooses from is frozen before then.
Game picks (ML / ATS / totals), anytime-TD bets and DFS keep their own thresholds and stay bets.
Writes the 'bet' and 'why' columns of picks_all.csv; the dashboard embeds only bets. Usage: python scripts/patch_v30_card.py"""
p = 'scripts/build_picks.py'; s = open(p, encoding='utf-8').read()
if "'price', 'bet', 'why']" in s: raise SystemExit('patch_v30_card: already applied')
a = "'note', 'price']"
assert s.count(a) == 1, 'COLS'
s = s.replace(a, "'note', 'price', 'bet', 'why']")
a = "    allp = allp[COLS].sort_values(['week', 'type', 'ref']).reset_index(drop=True)"
assert s.count(a) == 1, 'write'
s = s.replace(a, """    # v30: the card — which props are actually bet (rules in scripts/patch_v30_card.py and the Backtest tab)
    CARD = dict(edge=6.0, lo=-200, hi=200, model=0.5, per_game=3)
    SPM = {}
    if os.path.exists(P + 'bet_ledger.csv'):
        for b in pd.read_csv(P + 'bet_ledger.csv').itertuples():
            SPM.setdefault((int(b.week), b.player, b.market, float(b.line), b.side), b.p_over_model if b.side == 'Over' else 1 - b.p_over_model)
    allp['bet'] = '1'; allp['why'] = ''
    pm = allp.type == 'PROP'
    def _f(v):
        try: return float(v)
        except (TypeError, ValueError): return float('nan')
    cand = []
    for i, r in allp[pm].iterrows():
        e, a_ = _f(r.edge), _f(r.price)
        try: sp = SPM.get((int(r.week), r.player, r.market, float(r.line), r.side))
        except (TypeError, ValueError): sp = None
        why = ('edge under 6%' if not e >= CARD['edge'] else
               'price outside -200..+200' if a_ == a_ and not (CARD['lo'] <= a_ <= CARD['hi']) else
               'model under 50%' if sp is None or sp != sp or sp < CARD['model'] else '')
        allp.at[i, 'why'] = why
        if not why: cand.append((e, i, int(r.week), r.player, frozenset({str(r.team), str(r.opp).replace('@', '')})))
    seen_p, per_g = set(), {}
    for e, i, w, pl, g in sorted(cand, key=lambda c: -c[0]):
        if (w, pl) in seen_p: allp.at[i, 'why'] = 'not his best edge'; continue
        if per_g.get((w, g), 0) >= CARD['per_game']: allp.at[i, 'why'] = 'game already has 3'; continue
        seen_p.add((w, pl)); per_g[(w, g)] = per_g.get((w, g), 0) + 1
    allp.loc[pm & (allp.why != ''), 'bet'] = ''
""" + a)
a = "    gr = allp[allp.result.isin(['W', 'L'])]\n"
assert s.count(a) == 1, 'record'
s = s.replace(a, "    gr = allp[allp.result.isin(['W', 'L']) & (allp.bet.astype(str) == '1')]\n")
s = s.replace("""f"{t} {int((allp[(allp.week == week) & (allp.type == t)]).shape[0])}\"""", """f"{t} {int((allp[(allp.week == week) & (allp.type == t) & (allp.bet.astype(str) == '1')]).shape[0])}\"""")
open(p, 'w', encoding='utf-8').write(s)
p = 'scripts/build_dashboard.py'; s = open(p, encoding='utf-8').read()
a = "    data['picksAll'] = rows_of('data/processed/picks_all.csv')\n    data['picksClv'] = rows_of('data/processed/picks_clv.csv')\n"
assert s.count(a) == 1, 'dashboard'
s = s.replace(a, """    # v30: only bets reach the page (props that failed the card stay in picks_all.csv as leans)
    data['picksAll'] = rows_of('data/processed/picks_all.csv', lambda r: r.get('bet', '1') in ('1', '1.0'))
    for r in data['picksAll']: r.pop('bet', None); r.pop('why', None)
    _bk = {(r['type'], r['ref'], r['side'], r['week']) for r in data['picksAll']}
    data['picksClv'] = rows_of('data/processed/picks_clv.csv', lambda r: (r['type'], r['ref'], r['side'], r['week']) in _bk)
""")
open(p, 'w', encoding='utf-8').write(s)
print('patch_v30_card: the card decides which props are bet')
