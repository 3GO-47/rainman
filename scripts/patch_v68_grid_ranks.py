"""v68 — Player Grid: every allowed-per-game figure carries its rank among the defenses as a small subscript (1 = allows the
most), so the rank no longer needs a hover. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v68 */' in s:
    print('v68 already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:110])
    s = s.replace(old, new)
rep("""   +`<span class="badge" style="${r==null?'':gradeStyle(+r)}">${tNum(v)}</span></td>`;""",
    """   +`<span class="badge" style="${r==null?'':gradeStyle(+r)}">${tNum(v)}</span>${r==null?'':`<sub class="trk">${Math.floor(+r)}</sub>`}</td>`;/* v68 */""")
rep("green = allows the most = the best matchup, red = the least. Hover any cell for the exact rank &middot;", "green = allows the most = the best matchup, red = the least. The small number beside each figure is its rank of ${NT} (1 = allows the most) &middot;")
rep("</style>", "/* v68 */sub.trk{font:600 9px/1 var(--mono);color:var(--dim);margin-left:2px;vertical-align:-3px;letter-spacing:-.3px}\n</style>")
open(P, 'w', encoding='utf-8').write(s); print('v68 applied')
