"""v60 — META / META v2: one composite column, then the MARKETS separated by position (rerunnable; guarded by /* v60 */).

Every row keeps its single META (or CONS) number and then shows, for the markets of his position, what to expect and how it prices:
  bold = the model's expected stat line this week (prop model projection) · small = the posted line (best of the books) and the
  model's lean: O 58 = 58% to go over, U 61 = 61% to go under · cell tint green for an over lean, red for an under lean, nothing
  when no line is posted. Hover: the 10–90 range, the book, the price, how many books post it.
  QB  → PASS YDS · PASS TD · RUSH YDS · CMP          RB → RUSH YDS · CARRIES · REC · REC YDS
  WR  → REC · REC YDS · RUSH YDS                     TE → REC · REC YDS
  ALL → BEST MARKET (his strongest posted line: market, expectation, line, lean)
  every section ends with TD: anytime-TD model % with the best posted price and the EV against it.
Every new column sorts (market columns by over %, BEST MARKET by the size of the lean, TD by the model %).
"""
import sys, os
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_template.html')
s = open(P, encoding='utf-8').read()
if '/* v60 */' in s: print('v60 already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, f'expected {n} got {c}: {old[:90]!r}'
    s = s.replace(old, new)

# ---------------------------------------------------------------- shared helpers, defined once before metaGrid
rep("function metaGrid(root='#meta',px='mt'){",
r"""/* v60 */const MK_POS={QB:['pass_yds','pass_td','rush_yds','completions'],RB:['rush_yds','rush_att','receptions','rec_yds'],WR:['receptions','rec_yds','rush_yds'],TE:['receptions','rec_yds']};
const MK_LBL={pass_yds:'PASS YDS',pass_td:'PASS TD',rush_yds:'RUSH YDS',rush_att:'CARRIES',receptions:'REC',rec_yds:'REC YDS',completions:'CMP',rush_rec_yds:'RUSH+REC',pass_att:'ATT',interceptions:'INT'};
let MKX=null,MKW=null;
function mkIndex(wk){if(MKX&&MKW===wk)return MKX;const B=J.betting||{},nk=s=>String(s||'').toLowerCase().replace(/[^a-z]/g,''),Pm={},Lm={};
  (B.proj||[]).forEach(r=>{const k=r[1]+'|'+nk(r[0]);(Pm[k]=Pm[k]||{})[r[4]]={proj:r[5],q10:r[6],q50:r[7],q90:r[8],n:r[9]}});
  (B.lines||[]).forEach(r=>{if(+r.week!==wk||r.line==null||r.line==='')return;const k=r.team+'|'+nk(r.player);const o=(Lm[k]=Lm[k]||{});(o[r.market]=o[r.market]||[]).push(r)});
  MKX={P:Pm,L:Lm,nk};MKW=wk;return MKX}
function mkOf(u,wk){const X=mkIndex(wk),k=u.team+'|'+X.nk(u.player),Pm=X.P[k]||{},Lm=X.L[k]||{},out={};
  Object.keys(MK_LBL).forEach(m=>{const pj=Pm[m],ls=Lm[m]||[];if(!pj&&!ls.length)return;let best=null;
    ls.forEach(r=>{const po=r.p_over_model!=null&&r.p_over_model!==''?+r.p_over_model:null;if(po==null||isNaN(po))return;const lean=Math.abs(po-.5);if(!best||lean>best.lean)best={line:+r.line,po,lean,book:r.book,op:r.over_price,up:r.under_price,n:ls.length}});
    out[m]={proj:pj&&pj.proj!=null?+pj.proj:(ls.length&&ls[0].proj!=null&&ls[0].proj!==''?+ls[0].proj:null),q10:pj?pj.q10:null,q90:pj?pj.q90:null,best}});
  let top=null;Object.entries(out).forEach(([m,v])=>{if(v.best&&(!top||v.best.lean>top.lean))top=Object.assign({m,proj:v.proj},v.best)});out.__best=top;return out}
const mkHeat=po=>{if(po==null)return '';const t=Math.max(-1,Math.min(1,(po-.5)/.22)),a=Math.abs(t)*.42;return a<.04?'':`background:rgba(${t>0?'0,200,83':'255,82,82'},${a.toFixed(2)})`};
const mkNum=v=>v==null?'—':Math.abs(v)>=10?String(Math.round(v)):(+v).toFixed(1);
function mkCell(v,m){if(!v||(v.proj==null&&!v.best))return '<td class="md mk"><span class="dim">·</span></td>';const b=v.best,pr=v.proj;
  const side=b?(b.po>=.5?'O':'U'):'',p=b?(b.po>=.5?b.po:1-b.po):null;
  const tip=`${MK_LBL[m]} · model expects ${pr==null?'—':(+pr).toFixed(1)}${v.q10!=null&&v.q90!=null?' · likely range '+(+v.q10).toFixed(0)+'–'+(+v.q90).toFixed(0):''}${b?` · line ${b.line} at ${b.book}${b.op!=null&&b.op!==''?' '+mlTxt(+b.op)+' over':''}${b.up!=null&&b.up!==''?' / '+mlTxt(+b.up)+' under':''}${b.n>1?' · best of '+b.n+' books':''} · model ${Math.round(100*b.po)}% over, ${Math.round(100*(1-b.po))}% under`:' · no line posted this week'}`;
  return `<td class="md mk" style="${b?mkHeat(b.po):''}" title="${esc(tip)}"><b>${mkNum(pr)}</b><small>${b?`${b.line} <i class="${side==='O'?'ov':'un'}">${side}${Math.round(100*p)}</i>`:'<span class="dim">no line</span>'}</small></td>`}
function mkBestCell(x){const b=x.mk&&x.mk.__best;if(!b)return '<td class="md mk"><span class="dim">no posted line</span></td>';const side=b.po>=.5?'O':'U',p=b.po>=.5?b.po:1-b.po;
  return `<td class="md mk" style="${mkHeat(b.po)}" title="${esc(`${MK_LBL[b.m]} · model expects ${b.proj==null?'—':(+b.proj).toFixed(1)} · line ${b.line} at ${b.book}${b.op!=null&&b.op!==''?' '+mlTxt(+b.op):''} · model ${Math.round(100*b.po)}% over, ${Math.round(100*(1-b.po))}% under`)}"><b>${MK_LBL[b.m].toLowerCase()} ${mkNum(b.proj)}</b><small>${b.line} <i class="${side==='O'?'ov':'un'}">${side}${Math.round(100*p)}</i></small></td>`}
function mkTdCell(x){if(x.atd==null)return '<td class="md mk"><span class="dim">·</span></td>';const t=x.t||{};const pr=t.price!=null&&t.price!==''?+t.price:null,ev=t.ev!=null&&t.ev!==''?+t.ev:null;
  return `<td class="md mk" title="${esc(`anytime-TD model ${(100*x.atd).toFixed(0)}%${t.fair!=null?' · fair '+mlTxt(+t.fair):''}${pr!=null?' · best price '+mlTxt(pr)+(t.book?' ('+t.book+')':''):''}${ev!=null?' · EV '+(ev>=0?'+':'')+ev.toFixed(1)+'%':''}`)}"><b><span class="badge" style="${x.c&&x.c.atd!=null?gradeStyle(1+(1-x.c.atd)*(NT-1)):''}">${Math.round(100*x.atd)}%</span></b><small>${pr!=null?mlTxt(pr):'<span class="dim">no price</span>'}${ev!=null?` <i class="${ev>=0?'ov':'un'}">${ev>=0?'+':''}${ev.toFixed(0)}%</i>`:''}</small></td>`}
const mkTH=(th,p)=>{const MS=p==='ALL'?['best']:(MK_POS[p]||[]);return MS.map(m=>m==='best'?th('best','BEST MARKET','his strongest posted line this week — the market, what the model expects, the line and the lean · sorts by the size of the lean','md'):th('m:'+m,MK_LBL[m],MK_LBL[m].toLowerCase()+' · bold = what the model expects this week · small = the posted line and the model\'s lean (O = over, U = under, with its %) · green over, red under · sorts by over %','md')).join('')+th('tdk','TD','anytime-TD model % (shaded within his position) · the best posted price and the EV against it · sorts by the model %','md')};
const mkSV=(x,k)=>k.startsWith('m:')?(x.mk&&x.mk[k.slice(2)]&&x.mk[k.slice(2)].best?x.mk[k.slice(2)].best.po:null):k==='best'?(x.mk&&x.mk.__best?x.mk.__best.lean:null):k==='tdk'?x.atd:undefined;
function metaGrid(root='#meta',px='mt'){""")

# ---------------------------------------------------------------- metaGrid (scoped: METAPROP shares some of these lines verbatim)
_a=s.index("function metaGrid(root='#meta',px='mt'){");_b=s.index("function metaV2(root='#metav2',px='mv'){");_blk=s[_a:_b]
def grep_(old,new,n=1):
    global _blk
    c=_blk.count(old); assert c==n, f'[metaGrid] expected {n} got {c}: {old[:90]!r}'
    _blk=_blk.replace(old,new)
grep_("        pool:TD_SLOTS.includes(u.dslot||u.slot)}});",
    "        pool:TD_SLOTS.includes(u.dslot||u.slot),mk:opp?mkOf(u,wk):null}});")
grep_("  const sv=(x,k)=>k==='meta'?x.meta:k==='env'?x.env:",
    "  const sv=(x,k)=>mkSV(x,k)!==undefined?mkSV(x,k):k==='meta'?x.meta:k==='env'?x.env:")
grep_("  const cells=x=>{\n    const meta=x.meta==null?'<td class=\"md gs\"><span class=\"dim\">·</span></td>'",
    "  const cells=(x,p)=>{\n    const meta=x.meta==null?'<td class=\"md gs\"><span class=\"dim\">·</span></td>'")
grep_("    const o={meta,env,td,atd,psi,form,h2h,sch,rz,snp,mkt,ftd};return sigs().map(k=>o[k]).join('')};",
    "    const o={meta,env,td,atd,psi,form,h2h,sch,rz,snp,mkt,ftd};const MS=p==='ALL'?[]:(MK_POS[p]||[]);return meta+(p==='ALL'?mkBestCell(x):MS.map(m=>mkCell(x.mk&&x.mk[m],m)).join(''))+mkTdCell(x)};")
grep_("    const S=sigs(),wname=p==='ALL'?46:56,wpos=p==='ALL'?10:0,wopp=22,ws=S.reduce((a,k)=>a+SIGW[k],0),wk=k=>((100-wname-wpos-wopp)*SIGW[k]/ws).toFixed(2);",
    "    const S=sigs(),MS=p==='ALL'?['best']:(MK_POS[p]||[]),wname=p==='ALL'?20:24,wpos=p==='ALL'?4:0,wopp=9,wmeta=9,wtd=11,wm=((100-wname-wpos-wopp-wmeta-wtd)/Math.max(1,MS.length)).toFixed(2);")
grep_("<col style=\"width:${wopp}%\">${S.map(k=>`<col style=\"width:${wk(k)}%\">`).join('')}</colgroup><thead>\n      <tr class=\"hd\">${th('player','Player')}${p==='ALL'?th('pos',''):''}${th('opp','Opp',\"this week's opponent\")}\n      ${S.map(k=>TH[k]).join('')}</tr></thead><tbody>",
    "<col style=\"width:${wopp}%\"><col style=\"width:${wmeta}%\">${MS.map(()=>`<col style=\"width:${wm}%\">`).join('')}<col style=\"width:${wtd}%\"></colgroup><thead>\n      <tr class=\"hd\">${th('player','Player')}${p==='ALL'?th('pos',''):''}${th('opp','Opp',\"this week's opponent\")}\n      ${TH.meta}${mkTH(th,p)}</tr></thead><tbody>")
grep_("<td>${x.opp?oppcell(x.oppRaw):'<span class=\"dim\">bye</span>'}</td>${cells(x)}</tr>`).join('')\n        ||`<tr><td colspan=\"${S.length+(p==='ALL'?3:2)}\" class=\"dim\">nothing matches</td></tr>`}",
    "<td>${x.opp?oppcell(x.oppRaw):'<span class=\"dim\">bye</span>'}</td>${cells(x,p)}</tr>`).join('')\n        ||`<tr><td colspan=\"${MS.length+(p==='ALL'?5:4)}\" class=\"dim\">nothing matches</td></tr>`}")
grep_("      if(st.k===k)st.a=!st.a;else{st.k=k;st.a=!DESC.has(k)}col(p)});",
    "      if(st.k===k)st.a=!st.a;else{st.k=k;st.a=/^(m:|best|tdk)/.test(k)?false:!DESC.has(k)}col(p)});")

s=s[:_a]+_blk+s[_b:]

# ---------------------------------------------------------------- metaV2: CONS, then the same market columns
rep("  const sv=(x,k)=>k==='cons'?x.cons:k==='t10'?x.t10:k==='t25'?x.t25:k==='nb'?x.nb:k==='player'?x.u.player:k==='opp'?(x.opp||null):k==='pos'?TPOS.indexOf(x.pos):x.pc[k];",
    "  const sv=(x,k)=>mkSV(x,k)!==undefined?mkSV(x,k):k==='cons'?x.cons:k==='t10'?x.t10:k==='t25'?x.t25:k==='nb'?x.nb:k==='player'?x.u.player:k==='opp'?(x.opp||null):k==='pos'?TPOS.indexOf(x.pos):x.pc[k];")
rep("""    const wname=p==='ALL'?46:56,wpos=p==='ALL'?10:0,wopp=22;
    $$('B'+p).innerHTML=`<table class="lgt"><colgroup><col style="width:${wname}%">${p==='ALL'?`<col style="width:${wpos}%">`:''}<col style="width:${wopp}%"><col style="width:${100-wname-wpos-wopp}%"></colgroup><thead>
      <tr class="hd">${th('player','Player')}${p==='ALL'?th('pos',''):''}${th('opp','Opp',"this week's opponent")}${th('cons','CONS','every board folded into one · 0–100 · hover for every board, his percentile on each, and his top-10% / top-quarter counts','md gs')}</tr></thead><tbody>""",
    """    const MS=p==='ALL'?['best']:(MK_POS[p]||[]),wname=p==='ALL'?20:24,wpos=p==='ALL'?4:0,wopp=9,wmeta=9,wtd=11,wm=((100-wname-wpos-wopp-wmeta-wtd)/Math.max(1,MS.length)).toFixed(2);
    R.forEach(x=>{if(x.mk===undefined)x.mk=x.opp?mkOf(x.u,G.week):null;if(x.atd===undefined){const t=((J.betting||{}).td||[]).find(r=>+r.week===G.week&&r.player===x.u.player&&r.team===x.u.team);x.t=t||null;x.atd=t&&t.p_model!=null&&t.p_model!==''?+t.p_model:null;x.c=x.c||{};if(x.c.atd===undefined)x.c.atd=null}});
    $$('B'+p).innerHTML=`<table class="lgt"><colgroup><col style="width:${wname}%">${p==='ALL'?`<col style="width:${wpos}%">`:''}<col style="width:${wopp}%"><col style="width:${wmeta}%">${MS.map(()=>`<col style="width:${wm}%">`).join('')}<col style="width:${wtd}%"></colgroup><thead>
      <tr class="hd">${th('player','Player')}${p==='ALL'?th('pos',''):''}${th('opp','Opp',"this week's opponent")}${th('cons','CONS','every board folded into one · 0–100 · hover for every board, his percentile on each, and his top-10% / top-quarter counts','md gs')}${mkTH(th,p)}</tr></thead><tbody>""")
rep("""        ${x.cons==null?'<td class="md gs"><span class="dim">·</span></td>':`<td class="md gs" title="${esc(why(x))}"><span class="badge" style="${gradeStyle(eq(Math.max(0,Math.min(1,x.cons/100))))}">${Math.round(x.cons)}</span></td>`}
        </tr>`}).join('')||`<tr><td colspan="${p==='ALL'?4:3}" class="dim">nothing matches</td></tr>`}</tbody></table>`;""",
    """        ${x.cons==null?'<td class="md gs"><span class="dim">·</span></td>':`<td class="md gs" title="${esc(why(x))}"><span class="badge" style="${gradeStyle(eq(Math.max(0,Math.min(1,x.cons/100))))}">${Math.round(x.cons)}</span></td>`}${p==='ALL'?mkBestCell(x):MS.map(m=>mkCell(x.mk&&x.mk[m],m)).join('')}${mkTdCell(x)}
        </tr>`}).join('')||`<tr><td colspan="${MS.length+(p==='ALL'?5:4)}" class="dim">nothing matches</td></tr>`}</tbody></table>`;""")
rep("    $$('B'+p).querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=h.dataset.k;if(st.k===k)st.a=!st.a;else{st.k=k;st.a=k==='player'||k==='opp'||k==='pos'}col(p)});\n    tWire($$('B'+p));const sec=$$('B'+p).closest('.lgcol'),h=sec&&sec.querySelector('h3');if(h)sec.style.setProperty('--h3h',h.offsetHeight+'px')}",
    "    $$('B'+p).querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=h.dataset.k;if(st.k===k)st.a=!st.a;else{st.k=k;st.a=k==='player'||k==='opp'||k==='pos'}col(p)});\n    tWire($$('B'+p));const sec=$$('B'+p).closest('.lgcol'),h=sec&&sec.querySelector('h3');if(h)sec.style.setProperty('--h3h',h.offsetHeight+'px')}")

# ---------------------------------------------------------------- CSS for the market cells
rep(".lgt td{padding:2px 5px;border-bottom:1px solid var(--edge);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    ".lgt td{padding:2px 5px;border-bottom:1px solid var(--edge);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n"
    "/* v60 */#meta .lgrid,#metav2 .lgrid{grid-template-columns:1fr!important;display:grid;gap:14px}#meta .lgrid .lgcol,#metav2 .lgrid .lgcol{min-width:0}#meta .lgt,#metav2 .lgt{table-layout:fixed;width:100%}\n.lgt td.mk{text-align:center;line-height:1.1;padding-top:3px;padding-bottom:3px}.lgt td.mk b{font:700 12.5px var(--mono)}.lgt td.mk small{display:block;font:500 9.5px var(--mono);color:var(--dim);margin-top:1px}.lgt td.mk i{font-style:normal;font-weight:700}.lgt td.mk i.ov{color:#00c853}.lgt td.mk i.un{color:#ff5252}")

# ---------------------------------------------------------------- reading key + notes
rep("One column: META. Hover any META cell for the full breakdown, every signal and its weight · every position together, then QB, RB, WR, TE · click a name for his card</span>",
    "One composite column: META. Then his <b>markets</b>, by position — bold = what the model expects this week, small = the posted line (best of the books) and the model's lean (O 58 = 58% over, U 61 = 61% under); green = over lean, red = under lean, blank = no line posted · QB: pass yds · pass TD · rush yds · cmp — RB: rush yds · carries · rec · rec yds — WR: rec · rec yds · rush yds — TE: rec · rec yds — every section ends with TD (anytime-TD model %, best price, EV) · the all-positions section shows each man's single strongest posted line · hover any cell for the range, book and prices · every column sorts · click a name for his card</span>")
s = s.replace("Object.assign(NOTES,{h2hgridp:['v59',", "Object.assign(NOTES,{meta:['v60','the markets are back beside the composite: for every position, what the model expects in each of his markets, the posted line and the over / under lean, tinted — one META column, the rest by position'],metav2:['v60','market columns (expectation · line · lean) and TD beside the single CONS column, by position']});Object.assign(NOTES,{h2hgridp:['v59',", 1)

open(P, 'w', encoding='utf-8').write(s)
print('v60 applied')
