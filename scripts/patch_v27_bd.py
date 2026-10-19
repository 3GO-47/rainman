"""v27 — embed data/processed/backtest.json as J.backtest (build_dashboard.py) and rebuild it on every refresh (refresh.py).
Usage: python scripts/patch_v27_bd.py   (run from the repo root)"""
p = 'scripts/build_dashboard.py'; s = open(p, encoding='utf-8').read()
a = "        data['tdpicks'] = json.load(open('data/processed/td_picks.json'))\n"
if 'backtest.json' not in s:
    assert s.count(a) == 1, 'build_dashboard anchor'
    s = s.replace(a, a + "    if LEAGUE == 'nfl' and os.path.exists('data/processed/backtest.json'):\n        data['backtest'] = json.load(open('data/processed/backtest.json'))\n")
    open(p, 'w', encoding='utf-8').write(s)
p = 'scripts/refresh.py'; s = open(p, encoding='utf-8').read()
a = "    try: run(['scripts/build_td_picks.py'])"
if 'build_backtest.py' not in s:
    assert s.count(a) == 1, 'refresh anchor'
    i = s.index(a); j = s.index('\n', s.index('\n', i) + 1)          # the try line and its except line
    s = s[:j + 1] + "    try: run(['scripts/build_backtest.py'])\n    except SystemExit as e: print('!! build_backtest failed — the Backtest tab keeps its last build:', e)\n" + s[j + 1:]
    open(p, 'w', encoding='utf-8').write(s)
print('patch_v27_bd: J.backtest embedded; refresh.py rebuilds it')
