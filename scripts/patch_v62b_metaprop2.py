"""v62b — METAPROP v2: a copy of METAPROP (the original function and tab are untouched) with the market read added to every line:
PROJ (model median and its gap to the line), PRICE (best over / best under across the books), EV (the model's side at the best
price), AGREE (how many of the five signals side with the lean) — plus two lead cards (model edge, agreement). Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v62b */' in s:
    print('v62b already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:100])
    s = s.replace(old, new)

a = s.index("function metaProp(root='#metaprop',px='mp'){"); b = s.index("\n}\n", a) + 3
src = s[a:b]
def crep(old, new, n=1):
    global src
    assert src.count(old) == n, ('copy', src.count(old), old[:100])
    src = src.replace(old, new)

crep("function metaProp(root='#metaprop',px='mp'){", "/* v62b */function metaProp2(root='#metaprop2',px='mq'){")
# row fields: projection, gap, best prices, EV of the model's side, agreement
crep("      return {u,pos,grp,m,line,oppRaw,opp,A,at,bo,bu,ref,kD,proxy:!!kD&&!DIRECT[m],dvp,pm,l10,l10n:l10s.length,l10k,av,avN:base.length,avCur:cur.length>=3,ea,ha,hn:vs.length,eh,last:vs.length?vs[vs.length-1]:null}});",
     """      const proj=ref&&ref.q50!=null&&ref.q50!==''?+ref.q50:(ref&&ref.proj!=null&&ref.proj!==''?+ref.proj:null),gap=proj==null?null:(proj-line)/den;
      const dO=bo?dec(bo.over_price):null,dU=bu?dec(bu.under_price):null,evO=pm!=null&&dO?pm*dO-1:null,evU=pm!=null&&dU?(1-pm)*dU-1:null;
      const ev=evO==null&&evU==null?null:(evO==null?evU:evU==null?evO:Math.max(evO,evU)),evSide=ev==null?null:(evO!=null&&ev===evO?'O':'U');
      return {u,pos,grp,m,line,oppRaw,opp,A,at,bo,bu,ref,kD,proxy:!!kD&&!DIRECT[m],dvp,pm,l10,l10n:l10s.length,l10k,av,avN:base.length,avCur:cur.length>=3,ea,ha,hn:vs.length,eh,last:vs.length?vs[vs.length-1]:null,proj,gap,dO,dU,evO,evU,ev,evSide}});""")
crep("      x.c=c;x.cov=w/W;x.meta=w?50+(100*t/w-50)*(.6+.4*w/W):null});",
     """      x.c=c;x.cov=w/W;x.meta=w?50+(100*t/w-50)*(.6+.4*w/W):null;
      const vals=['dvp','mdl','l10','avg','h2h'].map(k=>c[k]).filter(v=>v!=null);x.agN=vals.length;x.agO=vals.filter(v=>v>=.55).length;x.agU=vals.filter(v=>v<=.45).length;
      x.agSide=x.agO>x.agU?'O':x.agU>x.agO?'U':null;x.ag=x.agN?(x.agO-x.agU)/x.agN:null});""")
# signals list + widths
crep("const SIGS=['meta','dvp','mdl','l10','avg','h2h'],SIGW={meta:8,dvp:7,mdl:7,l10:7,avg:11,h2h:11},sigs=()=>SIGS.filter(k=>HAS[k]);",
     "const SIGS=['meta','proj','price','ev','agree','dvp','mdl','l10','avg','h2h'],SIGW={meta:7,proj:9,price:11,ev:8,agree:8,dvp:6,mdl:6,l10:6,avg:9,h2h:9},sigs=()=>SIGS.filter(k=>HAS[k]);")
crep("let ROWS=[],HAS={meta:1,dvp:1,mdl:1,l10:1,avg:1,h2h:1},WK=G.week;", "let ROWS=[],HAS={meta:1,proj:1,price:1,ev:1,agree:1,dvp:1,mdl:1,l10:1,avg:1,h2h:1},WK=G.week;")
crep("ROWS=R;HAS={meta:1,dvp:R.some(x=>x.dvp!=null),", "ROWS=R;HAS={meta:1,proj:R.some(x=>x.proj!=null),price:R.some(x=>x.dO||x.dU),ev:R.some(x=>x.ev!=null),agree:R.some(x=>x.agN>0),dvp:R.some(x=>x.dvp!=null),")
# sort values
crep("const sv=(x,k)=>k==='meta'?x.meta:k==='dvp'?x.dvp:", "const sv=(x,k)=>k==='meta'?x.meta:k==='proj'?x.gap:k==='price'?(x.dO!=null?x.dO:(x.dU!=null?-x.dU:null)):k==='ev'?x.ev:k==='agree'?x.ag:k==='dvp'?x.dvp:")
crep("const LBL=Object.fromEntries(MP_L.map(([k,l])=>[k,l])),DESC=new Set(['meta','mdl','l10','avg','h2h']);",
     "const LBL=Object.assign(Object.fromEntries(MP_L.map(([k,l])=>[k,l])),{proj:'PROJ',price:'PRICE',ev:'EV',agree:'AGREE'}),DESC=new Set(['meta','mdl','l10','avg','h2h','proj','ev','agree','price']);")
# cells
crep("    const o={meta,dvp,mdl,l10,avg:av,h2h};return sigs().map(k=>o[k]).join('')};",
     """    const evHeat=v=>v==null?'':`background:rgba(${v>=0?'0,200,83':'255,82,82'},${Math.min(.45,Math.abs(v)*2.2).toFixed(2)})`;
    const proj=x.proj==null?'<td class="md hp"><span class="dim">·</span></td>'
      :`<td class="md hp ${ud(x.gap,.1)}" title="${esc(`model median ${fv(x.proj,x.m)} vs the ${x.line} line (${gp(x.proj,x)})${x.ref&&x.ref.proj!=null&&x.ref.proj!==''?' · mean '+x.ref.proj:''}${x.ref&&x.ref.q10!=null&&x.ref.q10!==''?' · likely range '+x.ref.q10+'–'+x.ref.q90:''}${x.ref&&x.ref.n_eff!=null&&x.ref.n_eff!==''?' · '+x.ref.n_eff+' games of weight':''}`)}"><b>${fc(x.proj,x.m)}</b><i class="mini"> ${gp(x.proj,x)}</i></td>`;
    const price=!x.dO&&!x.dU?'<td class="md"><span class="dim">·</span></td>'
      :`<td class="md" title="${esc(`best over ${x.bo?mlTxt(+x.bo.over_price)+' at '+x.bo.book:'—'} · best under ${x.bu?mlTxt(+x.bu.under_price)+' at '+x.bu.book:'—'} · at the ${x.line} line, ${x.at.length} book${x.at.length===1?'':'s'}`)}"><span class="ov">${x.bo?mlTxt(+x.bo.over_price):'—'}</span><span class="dim"> / </span><span class="un">${x.bu?mlTxt(+x.bu.under_price):'—'}</span></td>`;
    const ev=x.ev==null?'<td class="md"><span class="dim">·</span></td>'
      :`<td class="md" style="${evHeat(x.ev)}" title="${esc(`the model's side: ${x.evSide==='O'?'OVER':'UNDER'} ${x.line} at ${x.evSide==='O'?(x.bo?mlTxt(+x.bo.over_price)+' ('+x.bo.book+')':'—'):(x.bu?mlTxt(+x.bu.under_price)+' ('+x.bu.book+')':'—')} · model ${Math.round(100*(x.evSide==='O'?x.pm:1-x.pm))}% · EV ${x.ev>=0?'+':''}${(100*x.ev).toFixed(1)}% per unit${x.evO!=null&&x.evU!=null?` (over ${x.evO>=0?'+':''}${(100*x.evO).toFixed(1)}% · under ${x.evU>=0?'+':''}${(100*x.evU).toFixed(1)}%)`:''}`)}"><b class="${x.evSide==='O'?'ov':'un'}">${x.evSide}</b> <b>${x.ev>=0?'+':''}${(100*x.ev).toFixed(0)}%</b></td>`;
    const agree=!x.agN?'<td class="md"><span class="dim">·</span></td>'
      :`<td class="md" title="${esc(`of ${x.agN} signals with data: ${x.agO} say over, ${x.agU} say under, ${x.agN-x.agO-x.agU} neutral`)}"><span class="badge" style="${gradeStyle(eq(clamp(.5+(x.ag||0)/2)))}">${x.agSide?x.agSide+' ':''}${Math.max(x.agO,x.agU)}/${x.agN}</span></td>`;
    const o={meta,proj,price,ev,agree,dvp,mdl,l10,avg:av,h2h};return sigs().map(k=>o[k]).join('')};""")
# headers
crep("    const TH={meta:th('meta','META','every signal folded into one score · 0–100, 100 = all say OVER, 0 = all say UNDER · hover a cell for the breakdown','md gs'),",
     """    const TH={meta:th('meta','META','every signal folded into one score · 0–100, 100 = all say OVER, 0 = all say UNDER · hover a cell for the breakdown','md gs'),
      proj:th('proj','PROJ','the prop model\\'s median for this stat (the 50 / 50 number) and its gap to the line · green above, red below · sorts on the gap','md'),
      price:th('price','PRICE','best over / best under price across the books at this line · hover for the books','md'),
      ev:th('ev','EV','the model\\'s side (O / U) and its expected value per unit at the best price · green positive, red negative','md'),
      agree:th('agree','AGREE','how many of the five signals (DVP, model, L10, AVG, H2H) side with the lean · O 4/5 = four of five say over','md'),""")
# lead cards
crep("      ['softest stat · DVP','',top(null,'dvp',true),x=>B(Math.round(x.dvp),gradeStyle(x.dvp)),'dvp'],",
     """      ['model edge · EV at the best price','g',top(x=>x.ev!=null&&x.ev>0,'ev',false),x=>`<b class="rise">${x.evSide} ${x.ev>=0?'+':''}${(100*x.ev).toFixed(0)}%</b>`,'ev'],
      ['signals agree · over','',top(x=>x.agSide==='O'&&x.agN>=4,'agree',false),x=>B(`O ${x.agO}/${x.agN}`,gradeStyle(eq(clamp(.5+(x.ag||0)/2)))),'agree'],
      ['signals agree · under','',top(x=>x.agSide==='U'&&x.agN>=4,'agree',true),x=>B(`U ${x.agU}/${x.agN}`,gradeStyle(eq(clamp(.5-(x.ag||0)/2)))),'agree'],
      ['softest stat · DVP','',top(null,'dvp',true),x=>B(Math.round(x.dvp),gradeStyle(x.dvp)),'dvp'],""")
# the note
crep("<span class=\"note\">META for player props. One row per posted line (the line most books post).", "<span class=\"note\">METAPROP v2 — METAPROP with the market read on every line: <b>PROJ</b> = the prop model's median and its gap to the line &middot; <b>PRICE</b> = best over / best under across the books &middot; <b>EV</b> = the model's side and its expected value at that price &middot; <b>AGREE</b> = how many of the five signals side with the lean. One row per posted line (the line most books post).")
# lens chips: add the new ones
crep("${MP_L.map(([k,l,t])=>`<button data-l=\"${k}\" class=\"${k==='meta'?'on':''}\" title=\"${esc(t)}\">${l}</button>`).join('')}",
     "${MP_L.concat([['proj','PROJ','the model\\'s median vs the line'],['price','PRICE','best over price'],['ev','EV','the model\\'s side at the best price'],['agree','AGREE','signals siding with the lean']]).map(([k,l,t])=>`<button data-l=\"${k}\" class=\"${k==='meta'?'on':''}\" title=\"${esc(t)}\">${l}</button>`).join('')}")

s = s[:b] + "\n" + src + s[b:]

# ---- wiring: tab after METAPROP, div, id list, BOOT, INTRO, NOTES
rep("   {id:'metaprop',nfl:true,label:'METAPROP',desc:", "   {id:'metaprop2',nfl:true,label:'METAPROP v2',desc:'METAPROP with the market read on every line: the model\\'s median and its gap to the line, the best over / under price, the EV of the model\\'s side at that price, and how many signals agree \\u2014 the original METAPROP is unchanged beside it',c:'test',sub:'metaprop2'},\n   {id:'metaprop',nfl:true,label:'METAPROP',desc:")
rep('<div id="qbtargets" hidden></div>', '<div id="qbtargets" hidden></div><div id="metaprop2" hidden></div>')
rep("'api','injuries','qbtargets','catlive','dev','backtest'].forEach(k=>{const e=$('#'+k);if(e)e.hidden=k!==it.sub})", "'api','injuries','qbtargets','catlive','metaprop2','dev','backtest'].forEach(k=>{const e=$('#'+k);if(e)e.hidden=k!==it.sub})")
rep("['test',qbTargetsView],['test',catLiveView],", "['test',qbTargetsView],['test',catLiveView],['test',metaProp2],")
rep("const INTRO={\n", "const INTRO={\n metaprop2:{what:'METAPROP, with the market read.',how:['same rows and same META as METAPROP · PROJ = the model\\'s median and its gap to the line · PRICE = best over / best under across the books','EV = the model\\'s side at the best price, per unit · AGREE = how many of DVP, model, L10, AVG and H2H side with the lean','lead cards: model edge and the lines where the signals agree · every column sorts · the data-set select drives DVP and META as before']},\n")
rep("const NOTES={\n", "const NOTES={\n metaprop2:['v62','new tab beside METAPROP: the same board plus PROJ, PRICE, EV and AGREE columns and two lead cards (model edge, signals agree) · METAPROP itself is untouched'],\n")
open(P, 'w', encoding='utf-8').write(s)
print('v62b applied')
