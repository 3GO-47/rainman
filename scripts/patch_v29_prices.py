"""v29 — props carry the price they were posted at. picks_all.csv gains a 'price' column (American odds of the side, from
bet_ledger.csv — the first time that line and side were frozen); for props market_ref becomes that price's break-even and the
note says so. Older rows are backfilled the same way (results untouched). Units anywhere on the site then use the real price
instead of assuming −110. Usage: python scripts/patch_v29_prices.py   (from the repo root)"""
p = 'scripts/build_picks.py'; s = open(p, encoding='utf-8').read()
if "'note', 'price']" in s: raise SystemExit('patch_v29_prices: already applied')
a = "'edge', 'result', 'actual', 'note']"
assert s.count(a) == 1, 'COLS'
s = s.replace(a, "'edge', 'result', 'actual', 'note', 'price']")
a = "    allp = allp[COLS].sort_values(['week', 'type', 'ref']).reset_index(drop=True)"
assert s.count(a) == 1, 'write'
s = s.replace(a, """    # v29: every prop carries the price it was posted at (bet_ledger: that side's price the first time the line was frozen) —
    # units and break-even use it instead of assuming -110; older rows are backfilled the same way, results untouched
    if 'price' not in allp: allp['price'] = ''
    allp['price'] = allp['price'].astype(object)
    BLP = {}
    if os.path.exists(P + 'bet_ledger.csv'):
        for b in pd.read_csv(P + 'bet_ledger.csv').itertuples():
            pr = b.over_price if b.side == 'Over' else b.under_price
            if pr == pr: BLP.setdefault((int(b.week), b.player, b.market, float(b.line), b.side), int(pr))
    for i, r in allp[allp.type == 'PROP'].iterrows():
        try: k = (int(r.week), r.player, r.market, float(r.line), r.side)
        except Exception: continue
        if k in BLP and str(r.price) in ('', 'nan', 'None'):
            a_ = BLP[k]; allp.at[i, 'price'] = a_
            allp.at[i, 'market_ref'] = round(100 / (a_ + 100) if a_ > 0 else -a_ / (-a_ + 100), 3)
            allp.at[i, 'note'] = 'at its posted price'
""" + a)
open(p, 'w', encoding='utf-8').write(s)
print('patch_v29_prices: picks_all carries the posted price')
