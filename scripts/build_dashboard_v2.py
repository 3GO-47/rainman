"""RAINMAN v2 — the redesigned shell/skin over the v1 engine (same payload, same formulas, same numbers).
Reads the built v1 dashboard (dashboard/rainman.html) and layers scripts/v2/skin.css + scripts/v2/skin.js on top:
sidebar rail with a spring indicator, glass filter strip, card design system, view transitions, count-up numbers,
card tilt. Output: dashboard/v2/index.html (served at /v2/ by .github/workflows/pages.yml)."""
import os
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
html = open('dashboard/rainman.html', encoding='utf-8').read()
css = open('scripts/v2/skin.css', encoding='utf-8').read()
js = open('scripts/v2/skin.js', encoding='utf-8').read()
fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;450;500;600;650;700&display=swap" rel="stylesheet">')
assert html.count('</head>') == 1 and html.rfind('</body>') > 0
html = html.replace('<title>RAINMAN — Defense-vs-Position Field Theory</title>', '<title>RAINMAN</title>')
html = html.replace('</head>', fonts + '<style id="v2css">' + css + '</style></head>', 1)
i = html.rfind('</body>')
html = html[:i] + '<script id="v2js">' + js + '</script>' + html[i:]
os.makedirs('dashboard/v2', exist_ok=True)
open('dashboard/v2/index.html', 'w', encoding='utf-8').write(html)
print(f'dashboard/v2/index.html written: {len(html)//1024} KB')
