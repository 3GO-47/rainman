"""v64b — Def Trends: solid, readable strip colours (bright green = top of the league in allowed, bright red = bottom, the
middle fades), one key line instead of two, and the version note corrected. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v64b */' in s:
    print('v64b already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:100])
    s = s.replace(old, new)
rep("  const strip=r=>`<span class=\"dts\"", "  /* v64b */const chip=(rk,nr)=>{const mid=(nr+1)/2;return `background:hsla(${Math.round(gradeH(gradeT(rk,nr)))},78%,46%,${(.14+.86*Math.pow(Math.abs(rk-mid)/Math.max(1,mid-1),1.15)).toFixed(2)})`};\n  const strip=r=>`<span class=\"dts\"")
rep("${ORD.map(n=>`<i style=\"${gradeStyle(r.rk[n],r.nr)}\"></i>`).join('')}</span>`;", "${ORD.map(n=>`<i style=\"${chip(r.rk[n],r.nr)}\"></i>`).join('')}</span>`;")
i = s.index("      <p class=\"note mini dtkey\">"); j = s.index("</p>`;", i) + 6
s = s[:i] + "      <p class=\"note mini dtkey\"><span class=\"mini dim\">allows the least</span><span class=\"dts\">${[NT,Math.round(NT*.8),Math.round(NT*.62),Math.round(NT*.5),Math.round(NT*.38),Math.round(NT*.2),1].map(k=>`<i style=\"${chip(k,NT)}\"></i>`).join('')}</span><span class=\"mini dim\">the most · green on the right end of a strip = a hole open right now</span></p>`;" + s[j:]
i = s.index(" deftrends64:['v64',"); j = s.index("\n", i) + 1; s = s[:i] + s[j:]
i = s.index(" deftrends:['v63',"); j = s.index("\n", i)
s = s[:i] + " deftrends:['v64','every defense × slot as a colour strip over its last 10 · 7 · 5 · 3 · 1 games (green = allows the most): three short lists — biggest holes, opening, closing, with who draws each this week — and one 32 × 7 map; the numbers and the who-did-it game log are in the click-through']," + s[j:]
open(P, 'w', encoding='utf-8').write(s); print('v64b applied')
