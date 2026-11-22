"""v74 — the rank subscript beside each figure is coloured by the same scale as the figure: green = favourable (the defense
allows the most), red = unfavourable. Nothing else changes. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v74 */' in s:
    print('v74 already applied'); sys.exit(0)
old = '<sub class="rks">${Math.floor(+r)}</sub>`}</td>`;/* v68 */'
assert s.count(old) == 1, s.count(old)
s = s.replace(old, '<sub class="rks" style="color:${gradeColor(+r)}">${Math.floor(+r)}</sub>`}</td>`;/* v68 *//* v74 */')
open(P, 'w', encoding='utf-8').write(s); print('v74 applied')
