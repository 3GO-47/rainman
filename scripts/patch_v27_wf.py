"""v27 — build_td_picks.py also writes every walk-forward prediction (data/processed/td_picks_wf.csv) for the Backtest tab.

One row per logged skill player-game since 2025 week 1: the calibrated chance the walk-forward model gave him before kickoff
(refit on earlier weeks only) and whether he scored. Usage: python scripts/patch_v27_wf.py [path/to/build_td_picks.py]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/build_td_picks.py'
s = open(P, encoding='utf-8').read()
old = "def auc(p, y):"
if s.count(old) != 1: raise SystemExit('patch_v27_wf: anchor not found once')
if 'td_picks_wf.csv' in s: raise SystemExit('patch_v27_wf: already applied')
s = s.replace(old, """# every walk-forward prediction, for the Backtest tab (scripts/build_backtest.py)
with open(P + 'td_picks_wf.csv', 'w', newline='', encoding='utf-8') as fh:
    _w = csv.writer(fh); _w.writerow(['season', 'week', 'player', 'team', 'bucket', 'p', 'scored'])
    for ek, off, sel, gidx in bt_top:
        for j, g in enumerate(gidx): _w.writerow([ek // 100, ek % 100, nm_all[g], tm_all[g], bk[g], round(float(allp[off + j]), 4), int(yall[g])])
""" + old, 1)
open(P, 'w', encoding='utf-8').write(s)
print('patch_v27_wf: walk-forward predictions -> td_picks_wf.csv')
