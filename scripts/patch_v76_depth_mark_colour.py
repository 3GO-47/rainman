"""v76 — the depth marks on the Player Grid get a colour each: 1 blue, 2 violet, 3 pink, 4 slate. None of them is on the
green-to-red matchup scale, so a mark never reads as a grade. Nothing else changes. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v76 */' in s:
    print('v76 already applied'); sys.exit(0)
old = ".dsl.d1{background:#e6e6e8;color:#000}.dsl.d2{background:#6b7280;color:#fff}.dsl.d3{box-shadow:inset 0 0 0 1px #9aa3ad;color:#c5cbd3}.dsl.d4,.dsl.d5{box-shadow:inset 0 0 0 1px #4b5563;color:#8b98a5}"
assert s.count(old) == 1, s.count(old)
s = s.replace(old, "/* v76 */.dsl{color:#fff}.dsl.d1{background:#2f7df6}.dsl.d2{background:#8b5cf6}.dsl.d3{background:#e0489a}.dsl.d4,.dsl.d5{background:#5b6675}")
open(P, 'w', encoding='utf-8').write(s); print('v76 applied')
