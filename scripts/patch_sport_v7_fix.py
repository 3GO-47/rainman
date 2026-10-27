"""sport template v7: (1) rotation() treated every basketball G as a hockey goalie and kept one guard per team — guards
were missing from the cards, the boards, the grids and META; (2) the four-column grids overflowed their columns — two
columns per row, scroll inside a column when it is still too wide, tighter cells. Rerunnable (guarded)."""
import os, sys
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sport_template.html')
s = open(P, encoding='utf-8').read()
if 'GOALIE_SLOT' in s:
    print('already applied'); sys.exit()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep("const sk=ps.filter(p=>p.slot!=='G').sort((a,b)=>v(b)-v(a)),gk=ps.filter(p=>p.slot==='G').sort((a,b)=>v(b)-v(a)).slice(0,1);return sk.concat(gk)};",
    "const GOALIE_SLOT=J.sport==='hockey'?'G':null;const sk=ps.filter(p=>p.slot!==GOALIE_SLOT).sort((a,b)=>v(b)-v(a)),gk=GOALIE_SLOT?ps.filter(p=>p.slot===GOALIE_SLOT).sort((a,b)=>v(b)-v(a)).slice(0,1):[];return sk.concat(gk)};")
rep(".lgrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;align-items:start;margin:10px 0}.lgcol{min-width:0;background:var(--panel);border:1px solid var(--edge);border-radius:9px;padding:8px 10px}",
    ".lgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;align-items:start;margin:10px 0}.lgcol{min-width:0;overflow-x:auto;background:var(--panel);border:1px solid var(--edge);border-radius:9px;padding:8px 10px}.lgt{font-size:11px;border-collapse:collapse}.lgt th{font-size:9.5px;white-space:nowrap}.lgt td{white-space:nowrap}.lgt .badge{min-width:22px;padding:0 3px;font-size:10px}.lgt td.op2,.lgt td.pn{padding-right:6px}")
rep("@media(max-width:1100px){.lgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}", "@media(max-width:1100px){.lgrid{grid-template-columns:1fr}}")
open(P, 'w', encoding='utf-8').write(s)
print('applied')
