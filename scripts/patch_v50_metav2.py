"""v50 — META v2 made readable: cells show the board's own number (TD rank 8, Ψ 11, H2H +6.2, TDP 48%, 1st 9.8%, META 71, ENV 26.5,
FORM +12%, SCH +9, MKT +5%) shaded by his percentile at the position, like v1 — the percentile moves to the hover; position tabs
(all · QB · RB · WR · TE) and v1's lens chips (rank the table by any board) in the controls; the data-set select (2024 · 2025 ·
2026 · combined · adjusted) and QB TD mode drive the TD and Ψ boards exactly as on META v1. Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'v50 metav2' in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

rep("  const $$=k=>$('#'+px+k),live=new Set(TD_SLOTS),on=new Set(MV_B.map(b=>b[0]));let method='avg';\n  $(root).innerHTML=`<div class=\"controls\">\n    <span class=\"chips\" id=\"${px}B\" title=\"the boards in the fold — click to drop or restore one\">${MV_B.map(b=>`<button data-b=\"${b[0]}\" class=\"on\" title=\"${esc(b[2])}\">${b[1]}</button>`).join('')}</span>\n    <select id=\"${px}M\"",
    "  const $$=k=>$('#'+px+k),live=new Set(TD_SLOTS),on=new Set(MV_B.map(b=>b[0]));let method='avg',posTab='ALL';   /* v50 metav2 */\n  const srcs=Object.keys(J.dvp);\n  $(root).innerHTML=`<div class=\"controls\">\n    <span class=\"chips\" id=\"${px}Pos\" title=\"which position the table shows\"><button data-p=\"ALL\" class=\"on\">all</button>${TPOS.map(p=>`<button data-p=\"${p}\">${p}</button>`).join('')}</span>\n    <span class=\"chips\" id=\"${px}Lens\" title=\"rank the table by — CONS folds every board; click any column header to sort it too\"><button data-l=\"cons\" class=\"on\">CONS</button>${MV_B.map(b=>`<button data-l=\"${b[0]}\" title=\"${esc(b[2])}\">${b[1]}</button>`).join('')}</span>\n    <select id=\"${px}Src\" title=\"which data set the TD and Ψ boards read\">${srcs.map(x=>`<option value=\"${x}\" ${x==='combined'?'selected':''}>${x}</option>`).join('')}</select>\n    <select id=\"${px}QB\" title=\"a QB's slot has two TD-allowed stats; pick which one his TD board reads\"><option value=\"rush\" selected>QB: rushing / receiving TD</option><option value=\"pass\">QB: passing TD</option><option value=\"both\">QB: mean of both</option></select>\n    <span class=\"chips\" id=\"${px}B\" title=\"the boards in the fold — click to drop or restore one\">${MV_B.map(b=>`<button data-b=\"${b[0]}\" class=\"on\" title=\"${esc(b[2])}\">${b[1]}</button>`).join('')}</span>\n    <select id=\"${px}M\"")
rep("    const wk=G.week,D=J.dvp.combined||J.dvp[Object.keys(J.dvp)[0]]||{};",
    "    const wk=G.week,D=J.dvp[$$('Src').value]||J.dvp.combined||J.dvp[srcs[0]]||{};")
rep("      const tdc=(LABDEF[u.pos].stats(u.grp)||[]).filter(c=>/TD/.test(c)),tdcs=tdc.length>1?tdc.filter(c=>c!=='P TD'):tdc;",
    "      const tdc=(LABDEF[u.pos].stats(u.grp)||[]).filter(c=>/TD/.test(c)),qm=$$('QB').value,tdcs=tdc.length>1?(qm==='pass'?tdc.filter(c=>c==='P TD'):qm==='both'?tdc:tdc.filter(c=>c!=='P TD')):tdc;")
# raw value in the cell, percentile in the hover
rep("  const cell=(k,x)=>{const p=x.pc[k];return p==null?'<td class=\"op\"><span class=\"dim\">·</span></td>':`<td class=\"op\" title=\"${esc(LBL[k]+': '+rawTxt(k,x)+' · '+Math.round(100*p)+'th pct of '+x.pos+'s')}\"><span class=\"badge\" style=\"${gradeStyle(eq(p))}\">${Math.round(100*p)}</span></td>`};",
    "  const rawNum=(k,x)=>{const v=x.raw[k];if(v==null)return '';switch(k){case 'td':case 'psi':return String(Math.round(v));case 'h2h':return (v>=0?'+':'')+v.toFixed(1);case 'tdp':return Math.round(100*v)+'%';case 'ftd':return (100*v).toFixed(1)+'%';case 'wk':return v.toFixed(2);case 'cat':return String(v);case 'meta':return String(Math.round(v));case 'env':return v.toFixed(1);case 'form':return (v>=0?'+':'')+Math.round(100*v)+'%';case 'sch':return (v>=0?'+':'')+Math.round(v);case 'mkt':return (v>=0?'+':'')+(+v).toFixed(0)+'%';default:return String(v)}};\n"
    "  const cell=(k,x)=>{const p=x.pc[k];return p==null?'<td class=\"op\"><span class=\"dim\">·</span></td>':`<td class=\"op\" data-v=\"${p}\" title=\"${esc(LBL[k]+': '+rawTxt(k,x)+' · '+Math.round(100*p)+'th percentile of '+x.pos+'s')}\"><span class=\"badge\" style=\"${gradeStyle(eq(p))}\">${rawNum(k,x)}</span></td>`};")
# position tab filters the one table; lens sets the sort
rep("    const R=ROWS.filter(x=>(p==='ALL'||x.pos===p)&&keep(x)).sort(cmp(st.k,st.a));\n    $$('N'+p).textContent=R.length+(R.length===1?' player':' players');$$('G'+p).textContent=`ranked by ${st.k==='cons'?'CONS':st.k==='t10'?'T10':st.k==='t25'?'T25':st.k==='nb'?'boards':LBL[st.k]||st.k}`;",
    "    const R=ROWS.filter(x=>(posTab==='ALL'||x.pos===posTab)&&keep(x)).sort(cmp(st.k,st.a));\n    $$('N'+p).textContent=R.length+(R.length===1?' player':' players')+(posTab==='ALL'?'':' · '+posTab);$$('G'+p).textContent=`ranked by ${st.k==='cons'?'CONS':st.k==='t10'?'T10':st.k==='t25'?'T25':st.k==='nb'?'boards':LBL[st.k]||st.k} · ${$$('Src').value}`;")
rep("${ks.map(k=>th(k,LBL[k],TIP[k]+' · percentile within his position','op')).join('')}</tr></thead><tbody>",
    "${ks.map(k=>th(k,LBL[k],TIP[k]+' · the board\\'s own number, shaded by his percentile at the position (hover)','op')).join('')}</tr></thead><tbody>")
rep("  $$('M').onchange=()=>{method=$$('M').value;fold();cols()};$$('Inj').onchange=cols;$$('Q').oninput=cols;",
    "  $$('M').onchange=()=>{method=$$('M').value;fold();cols()};$$('Inj').onchange=cols;$$('Q').oninput=cols;$$('Src').onchange=all;$$('QB').onchange=all;\n"
    "  $$('Pos').querySelectorAll('button').forEach(b=>b.onclick=()=>{posTab=b.dataset.p;$$('Pos').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));col('ALL')});\n"
    "  $$('Lens').querySelectorAll('button').forEach(b=>b.onclick=()=>{const k=b.dataset.l;sort.ALL={k,a:false};$$('Lens').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));col('ALL')});")
# note text
rep("    <span class=\"note\">every board that ranks this week's players, compiled. Each cell is his <b>percentile within his position on that board</b> (100 = the best spot of anyone at his position); <b>CONS</b> folds them",
    "    <span class=\"note\">every board that ranks this week's players, compiled. Each cell is <b>that board's own number</b> (TD and Ψ = rank of ${NT}, 1 = softest; TDP = chance he scores; META 0–100 …), shaded by his percentile at his position — hover for it; <b>CONS</b> folds the percentiles")
s = s.replace("Object.assign(NOTES,{v49:", "Object.assign(NOTES,{v50:['v50','META v2 reads like v1: the boards\\' own numbers in the cells (percentile in the hover), position tabs, lens chips to rank by any board, the data-set select and QB TD mode']});\nObject.assign(NOTES,{v49:", 1)
s = s.replace(" metav2:{what:'The boards compiled.',how:['every board that ranks this week\\'s players becomes a percentile within his position (100 = the best spot of anyone at his position): TD Grid, Player Board Ψ, H2H, TD Picks, First TD, Weeklies, categories, META, ENV, FORM, scheme, market edge',",
              " metav2:{what:'The boards compiled.',how:['every board that ranks this week\\'s players, side by side, each cell the board\\'s own number shaded by where he sits among his position (hover for the percentile): TD Grid, Player Board Ψ, H2H, TD Picks, First TD, Weeklies, categories, META, ENV, FORM, scheme, market edge · position tabs and lens chips re-rank the table',", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v50 applied', len(s))
