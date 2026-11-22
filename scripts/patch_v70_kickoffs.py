"""v70 — the dashboard build corrects kickoff times from the newest ESPN scoreboard pull before it reads them
(scripts/update_kickoffs.py), so a flexed game lands in the right slate. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
B = 'scripts/build_dashboard.py'; b = open(B, encoding='utf-8').read()
if 'update_kickoffs' in b:
    print('v70 already applied'); sys.exit(0)
old = "    kick = {}\n    if os.path.exists('data/processed/kickoffs_2026.csv'):"
assert b.count(old) == 1
new = ("    try:   # v70: flexed games — take the real kickoff from the newest ESPN scoreboard pull\n"
       "        import update_kickoffs; update_kickoffs.main()\n"
       "    except Exception as e: print('  update_kickoffs skipped:', e)\n" + old)
open(B, 'w', encoding='utf-8').write(b.replace(old, new)); print('v70 applied')
