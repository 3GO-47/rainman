"""v59 — dash-wide refinement pass (rerunnable; guarded by the /* v59 */ marker).

  1. H2H Board + H2H Grid: conditional formatting on every statistic — a "vs this opponent" cell is tinted green / red by how far
     the player's average in those meetings sits above / below his own average (±60% saturates; thin samples are paler:
     1 game = half strength, 4+ = full); the player-average block is tinted by rank within his position among the rows shown
     (same green → red scale every rank badge uses); PPR vs / Δ PPR carry the same tint.  College column dropped from the
     H2H Board so the edge block fits at 1440 px (search still matches college names).
  2. Floating headers: every lgrid / lgt layout (TD Grid, Lab Grid, H2H Grid, METAPROP, lineups…) now has static section
     titles and column headers, like META / META v2 since v58.
  3. Projection band: a floor above the ceiling drew a negative-width bar (SVG error) — clamped.
  4. Injury chips: a missing status drew a "NAN" pill — hidden; the practice chip alone stands.
  5. Reading-key notes for both H2H views.
"""
import re, sys, os
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_template.html')
s = open(P, encoding='utf-8').read()
if '/* v59 */' in s: print('v59 already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, f'expected {n} got {c}: {old[:80]!r}'
    s = s.replace(old, new)

# ---- helpers (after H2H_VIS) ------------------------------------------------------------------------------------------------
rep("const H2H_VIS={QB:[0,1,2,6]",
    "/* v59 */const h2hHeat=(v,b,n=1)=>{if(v==null||b==null||!(b>0||v>0))return '';const r=Math.max(-.6,Math.min(.6,(v-b)/Math.max(Math.abs(b),.5)));"
    "const a=(Math.abs(r)/.6)*.42*Math.sqrt(Math.min(Math.max(n,1),4)/4);if(a<.03)return '';return (r>0?'background:rgba(46,204,113,':'background:rgba(231,76,60,')+a.toFixed(2)+')'};\n"
    "const h2hRankBg=(v,arr)=>{if(v==null)return '';const S=arr.filter(x=>x!=null);if(S.length<3)return '';const rank=1+S.filter(x=>x>v).length;const h=gradeH(gradeT(rank,S.length));return `background:hsla(${h},${h>100?45:62}%,45%,.2)`};\n"
    "const H2H_VIS={QB:[0,1,2,6]")

# ---- H2H Board (h2hLab) — scoped slice ----------------------------------------------------------------------------------------
a = s.index('function h2hLab(){'); b = s.index('function h2hGrid(')
blk = s[a:b]
def brep(old, new, n=1):
    global blk
    c = blk.count(old); assert c == n, f'[h2hLab] expected {n} got {c}: {old[:80]!r}'
    blk = blk.replace(old, new)
brep("""${IS_NFL?'<th data-k="college" title="final college · logo, conference badge; tint = tier (gold power-4 · teal G5 · slate FCS · magenta small school)">College</th>':''}""", "")
brep("${IS_NFL?`<td>${ccell(u.player)}</td>`:''}${single?'':`<td style=\"color:${POSC[u.pos]}\">", "${single?'':`<td style=\"color:${POSC[u.pos]}\">")
brep("const nCommon=(single?7:8)-(IS_NFL?0:3);", "const nCommon=(single?6:7)-(IS_NFL?0:2);")
brep("${VIS.map(i=>`<td class=\"op\">${vsCell(u,i)}</td>`).join('')}<td class=\"op\">${pprVs(u)}</td>",
     "${VIS.map(i=>`<td class=\"op\" style=\"${na(u,i)?'':h2hHeat(u.vals[i],big(u,i),u.n)}\">${vsCell(u,i)}</td>`).join('')}<td class=\"op\" style=\"${h2hHeat(u.ppr,AV==='S'?(u.pprS??u.pprC):u.pprC,u.n)}\">${pprVs(u)}</td>")
brep("${VIS.map((i,k)=>`<td class=\"pa${k===0?' gs':''}\">${avgCell(u,i)}</td>`).join('')}<td class=\"pa\">${pprAvg(u)}</td><td class=\"pa\">${gpCell(u)}</td><td class=\"md\">${dpCell(u)}</td>",
     "${VIS.map((i,k)=>`<td class=\"pa${k===0?' gs':''}\" style=\"${na(u,i)?'':h2hRankBg(big(u,i),PEER[u.pos].map(x=>na(x,i)?null:big(x,i)))}\">${avgCell(u,i)}</td>`).join('')}<td class=\"pa\" style=\"${h2hRankBg(AV==='S'?(u.pprS??u.pprC):u.pprC,PEER[u.pos].map(x=>AV==='S'?(x.pprS??x.pprC):x.pprC))}\">${pprAvg(u)}</td><td class=\"pa\">${gpCell(u)}</td><td class=\"md\" style=\"${h2hHeat(u.ppr,AV==='S'?(u.pprS??u.pprC):u.pprC,u.n)}\">${dpCell(u)}</td>")
# PEER: rows of the same position among those shown (rank base) — built once per render, before the html
brep("    const html=`<table class=\"lab2\"><thead><tr class=\"grp\">",
     "    const PEER={};R.forEach(x=>(PEER[x.pos]=PEER[x.pos]||[]).push(x));\n    const html=`<table class=\"lab2\"><thead><tr class=\"grp\">")
brep("three blocks per row: the player (who, where, usage) ·", "three blocks per row: the player (who, where, usage) · <b>colour</b>: vs-cells green / red by how far above / below his own average (paler = fewer meetings), average cells by rank within his position among the rows shown ·")
s = s[:a] + blk + s[b:]

# ---- H2H Grid (h2hGrid) --------------------------------------------------------------------------------------------------------
rep("return Object.assign({},x,{n:vs.length,vals:S.map(([,f])=>mean(vs,f)),ppr:mean(vs,l=>l[LOG.fppr]),base:mean(all,l=>l[LOG.fppr]),gpAll:all.length,",
    "return Object.assign({},x,{n:vs.length,vals:S.map(([,f])=>mean(vs,f)),bases:S.map(([,f])=>mean(all,f)),ppr:mean(vs,l=>l[LOG.fppr]),base:mean(all,l=>l[LOG.fppr]),gpAll:all.length,")
rep("${x.vals.map((v,i)=>`<td class=\"op${i===0?' gs':''}\" title=\"",
    "${x.vals.map((v,i)=>`<td class=\"op${i===0?' gs':''}\" style=\"${h2hHeat(v,x.bases[i],x.n)}\" title=\"")
rep("return `<td class=\"md hp ${cls}\" title=\"${esc(tip)}\"><b>${x.ppr.toFixed(1)}</b>",
    "return `<td class=\"md hp ${cls}\" style=\"${h2hHeat(x.ppr,x.base,x.n)}\" title=\"${esc(tip)}\"><b>${x.ppr.toFixed(1)}</b>")
rep("PPR carries ▲ / ▼ against his average over every logged game, so a row says",
    "every cell is tinted green / red by how far it sits above / below his own average over every logged game (paler = fewer meetings); PPR also carries ▲ / ▼, so a row says")

# ---- static headers on every lgrid / lgt layout ------------------------------------------------------------------------------
rep(".lgrid.full .lgcol>h3{border-radius:9px 9px 0 0;position:sticky;top:var(--sticky,33px);z-index:6}",
    ".lgrid.full .lgcol>h3{border-radius:9px 9px 0 0;position:sticky;top:var(--sticky,33px);z-index:6}\n"
    "/* v59 */.lgrid .lgcol>h3,table.lgt tr.grp th,table.lgt tr.hd th,table.lgt thead th{position:static!important}")

# ---- projection band: never a negative width -------------------------------------------------------------------------------------
rep('width="${(x(pr.ceil)-x(pr.floor)).toFixed(1)}"', 'width="${Math.max(0,x(pr.ceil)-x(pr.floor)).toFixed(1)}"')

# ---- injury chip: no NAN pill ------------------------------------------------------------------------------------------------------
rep("const injChip=(s,extra='')=>`<span class=\"injc\"", "const injChip=(s,extra='')=>(s==null||/^(nan|none|)$/i.test(String(s).trim()))?(extra||''):`<span class=\"injc\"")

# ---- notes ------------------------------------------------------------------------------------------------------------------------
rep("h2hp:['v18','slot chips replace the depth dropdown — the same player filter as the TD Grid and H2H Grid']",
    "h2hp:['v59','conditional formatting on every statistic: vs-cells green / red against his own average (paler = fewer meetings), average cells by rank within his position among the rows shown, PPR and Δ PPR tinted the same way · college column dropped so the edge block fits at 1440']")
s = s.replace("Object.assign(NOTES,{backtest:", "Object.assign(NOTES,{h2hgridp:['v59','every statistic tinted green / red against the player\\'s own average over every logged game (paler = fewer meetings); PPR tinted the same way']});Object.assign(NOTES,{backtest:", 1)

open(P, 'w', encoding='utf-8').write(s)
print('v59 applied')
