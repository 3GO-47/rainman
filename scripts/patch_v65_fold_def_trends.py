"""v65 — no new tab: Def Trends is folded into the existing Intel > Defenses tab (strips on top, the rankings table under it).
The 'Def Trends' nav entry is removed. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v65 */' in s:
    print('v65 already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:100])
    s = s.replace(old, new)
i = s.index("   {id:'deftrends',nfl:true,label:'Def Trends',"); j = s.index("\n", i) + 1
s = s[:i] + s[j:]
rep("   {id:'ranks',label:'Defenses',desc:'rank + allowed per game, per slot and stat',c:'defenses',sub:'ranks'},",
    "   {id:'ranks',label:'Defenses',desc:'where every defense is leaking: each slot as a colour strip over its last 10 / 7 / 5 / 3 / 1 games, the biggest, opening and closing holes with who draws them this week \\u2014 then rank + allowed per game, per slot and stat',c:'defenses',sub:'ranks'},")
rep('<div id="qbtargets" hidden></div><div id="deftrends" hidden></div>', '<div id="qbtargets" hidden></div>')
rep('<div id="ranks"></div><div id="matrix" hidden></div><div id="defense" hidden></div></div>', '<div id="deftrends"></div><div id="ranks"></div><div id="matrix" hidden></div><div id="defense" hidden></div></div>')
rep("  ['ranks','matrix','defense'].forEach(t=>$('#'+t).hidden=t!==b.dataset.t)});", "  ['ranks','matrix','defense'].forEach(t=>$('#'+t).hidden=t!==b.dataset.t);/* v65 */const dt=$('#deftrends');if(dt)dt.hidden=b.dataset.t!=='ranks'});")
rep("'api','injuries','qbtargets','deftrends',", "'api','injuries','qbtargets',")
rep("['test',qbTargetsView],['test',defTrendsView],", "['test',qbTargetsView],['defenses',defTrendsView],")
rep("</style>", "/* v65 */#defenses #deftrends{margin-bottom:14px}\n</style>")
open(P, 'w', encoding='utf-8').write(s); print('v65 applied')
