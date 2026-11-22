"""v75 — Player Grid: a small depth-chart number in front of each RB / WR / TE name (1, 2, 3, 4) so RB1 vs RB2, WR1..WR4 and
TE1 vs TE2 read at a glance. 1 is solid, 2 is grey, 3 and 4 are outlined. Hover gives the slot. Nothing else changes. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v75 */' in s:
    print('v75 already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:110])
    s = s.replace(old, new)
rep("""      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.u.player)}">${esc(pshort(x.u.player))}${x.u.inj===""",
    """      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.u.player)}">${p==='QB'?'':lgDepth(x.u)}${esc(pshort(x.u.player))}${x.u.inj===""")
rep("function labGrid(){", """/* v75 */const lgDepth=u=>{const sl=String(u.dslot||u.slot||''),m=sl.match(/\\d/);return m?`<i class="dsl d${m[0]}" title="${esc(sl)} on the depth chart">${m[0]}</i>`:''};
function labGrid(){""")
rep("</style>", """/* v75 */.dsl{display:inline-block;width:12px;height:12px;margin-right:4px;border-radius:3px;font:700 9px/12px var(--mono);font-style:normal;text-align:center;vertical-align:1px;box-sizing:border-box}
.dsl.d1{background:#e6e6e8;color:#000}.dsl.d2{background:#6b7280;color:#fff}.dsl.d3{box-shadow:inset 0 0 0 1px #9aa3ad;color:#c5cbd3}.dsl.d4,.dsl.d5{box-shadow:inset 0 0 0 1px #4b5563;color:#8b98a5}
</style>""")
open(P, 'w', encoding='utf-8').write(s); print('v75 applied')
