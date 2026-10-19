"""v29 — every card and bar on Backtest opens its proof.

  signal bar / verdict card -> week by week (picked right, TD rate softest vs toughest third, soft vs tough points) and the players it
                               rated highest and lowest each week with what happened (TD, PPR, vs his own average);
  data-set bar / trust card -> week by week (overall, yards, catches, TDs), every stat it called best to worst, the other tables;
  strategy card              -> every frozen pick graded (J.picksAll + closing line J.picksClv): record, units, week by week with a
                               running total, by market and by edge for props, the full pick list with week / result filters;
  TD Picks card              -> each week's top ten, every name with ✓ / ✗.
Usage: python scripts/patch_v29_backtest_pops.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v29: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# ---------------- hooks on every card / row
rep('''      bd?`<div class="c"><div class="k">trust these tables</div>''', '''      bd?`<div class="c" data-bds="${bd.k}"><div class="k">trust these tables</div>''')
rep('''      best?`<div class="c"><div class="k">best touchdown picker</div>''', '''      best?`<div class="c" data-bsg="${best.k}"><div class="k">best touchdown picker</div>''')
rep('''      bm?`<div class="c"><div class="k">best matchup number</div>''', '''      bm?`<div class="c" data-bsg="${bm.k}"><div class="k">best matchup number</div>''')
rep('''      `<div class="c r"><div class="k">ignore</div>''', '''      `<div class="c r"${junk.length?` data-bsg="${junk[0].k}"`:''}><div class="k">ignore</div>''')
rep('''`<div class="btr${x.v.auc<.51?' bad':''}">''', '''`<div class="btr${x.v.auc<.51?' bad':''}" data-bsg="${x.k}" title="click for the week-by-week history and the players it rated">''')
rep('''`<div class="btr d">''', '''`<div class="btr d" data-bds="${r.k}" title="click for the week-by-week history and every stat">''')
rep('''    const card=(name,rec,hit,need,note,n)=>{''', '''    const card=(name,rec,hit,need,note,n,key)=>{''')
rep('''      return `<div class="c ${few?'a':win?'g':'r'}"><div class="k">${esc(name)}</div>''', '''      return `<div class="c ${few?'a':win?'g':'r'}" data-bst="${key}"><div class="k">${esc(name)}</div>''')
rep(''':'',r.w+r.l)}).join('')''', ''':'',r.w+r.l,r.k)}).join('')''')
rep('''<div class="c g"><div class="k">TD Picks — each week's top 10</div>''', '''<div class="c g" data-btp="1"><div class="k">TD Picks — each week's top 10</div>''')

# ---------------- the pop-ups
rep('''  const wire=(id,a,f)=>$('#'+id).querySelectorAll('button').forEach(b=>b.onclick=()=>{f(b.dataset[a]);''', r'''  /* ---------------- the proof behind every card ---------------- */
  const modal=(title,sub,body)=>{const o=document.getElementById('ppModal');if(o)o.remove();
    document.body.insertAdjacentHTML('beforeend',`<div class="modal" id="ppModal"><div class="modalbox wide"><button class="mclose" id="ppX">ESC &#10005;</button><h3>${title} <span class="f">${sub}</span></h3>${body}</div></div>`);wireModal()};
  const kpi=(k,v,s,t)=>`<div class="kpi ${t||''}"><span class="k">${k}</span><b class="v">${v}</b><span class="s">${s}</span></div>`;
  const ok=v=>v==null?'':v>=.54?'g':v<.51?'r':'';
  const STN=c=>c.replace('P+R','pass + rush yds').replace('R+R','rush + rec yds').replace('RecY','receiving yds').replace('Recep','catches').replace(/\bRY\b/,'rushing yds').replace(/\bPY\b/,'passing yds').replace('P TD','passing TDs').replace(/\bTD\b/,'TDs').replace('QB TDs','QB rushing TDs').replace('WR RY','WR rushing yds');
  function sigPop(k){const SG=B.sigs[S],v=DEP.has(k)?k+'@'+tab:k,H=(SG.hist||{})[v]||{},E=(SG.ex||{})[v]||{},o=sv(k),wks=Object.keys(H).map(Number).sort((a,b)=>a-b);
    const ex=L=>`<table class="fx btex"><tbody>${(L||[]).map(r=>`<tr><td>${pn(r[0],r[1],true)}</td><td>${slotchip(r[3])}</td><td class="mini">vs ${tcell(r[2])}</td><td class="mini">${esc(r[4])}</td><td>${r[5]?'<b style="color:var(--green)">✓ TD</b>':'<span style="color:var(--red)">✗</span>'}</td><td class="n">${(+r[6]).toFixed(1)}</td><td class="n" style="color:${r[7]>=0?'var(--green)':'var(--red)'}">${r[7]>=0?'+':''}${(+r[7]).toFixed(1)}</td></tr>`).join('')}</tbody></table>`;
    const tally=L=>{const n=(L||[]).length,t=(L||[]).filter(r=>r[5]).length;return n?`${t} of ${n} scored`:''};
    modal(esc(NAME[k]),`${esc(WHAT[k])}${DEP.has(k)?` · ${tab==='adj'?'Adjusted':'Combined'} tables`:''} · ${S}${pos!=='ALL'?' · '+pos:''}`,
      `<div class="kpis">${kpi('picked the right player',pc(o.auc),'two players, same slot, same week — one scored, one didn\'t · coin flip = 50%',ok(o.auc))}${kpi('TD rate, its softest third',pc(o.tdt),`its toughest third: ${pc(o.tdb)}`,(o.tdt||0)>(o.tdb||0)?'g':'r')}${kpi('soft vs tough',pts(o.edge),'fantasy points over his own average, softest third minus toughest',(o.edge||0)>0?'g':'r')}${kpi('players graded',o.n??'—',`${pc(o.cov)} of slot owners had this number`)}</div>
      ${DEP.has(k)?`<p class="mini" style="margin:2px 0 8px">same number through the other tables: Combined ${pc(sv(k,'comb').auc)} · Adjusted ${pc(sv(k,'adj').auc)}</p>`:''}
      <div class="panel"><h3>week by week <span class="f">every position</span></h3><table class="fx bt"><thead><tr><th>week</th><th>players</th><th>picked right</th><th>TD rate · softest third</th><th>TD rate · toughest third</th><th>soft vs tough</th></tr></thead><tbody>
        ${wks.map(w=>{const h=H[w];return `<tr><td>${w}</td><td>${h[0]??'—'}</td><td data-v="${h[1]??''}"><b style="color:${col(h[1])}">${pc(h[1])}</b></td><td data-v="${h[2]??''}">${pc(h[2])}</td><td data-v="${h[3]??''}">${pc(h[3])}</td><td data-v="${h[4]??''}" style="color:${(h[4]||0)>=0?'var(--green)':'var(--red)'}">${pts(h[4])}</td></tr>`}).join('')}</tbody></table></div>
      <div class="panel"><h3>who it rated highest and lowest each week — and what happened <span class="f">the top of each slot that week · ✓ = scored a TD · then his PPR and PPR against his own average · click a name for his card</span></h3>
        ${wks.slice().reverse().filter(w=>E[w]).map(w=>`<div class="btwk"><h4>week ${w} <span class="mini">· picked right ${pc(H[w][1])}</span></h4><div class="btx2"><div><div class="mini btlh g">rated highest · ${tally(E[w].top)}</div>${ex(E[w].top)}</div><div><div class="mini btlh r">rated lowest · ${tally(E[w].bot)}</div>${ex(E[w].bot)}</div></div></div>`).join('')||'<p class="mini dim">no examples for this season</p>'}</div>`)}
  function dsPop(k){const r=(B.dsets[S].rows||[]).find(x=>x.k===k);if(!r)return;const wk=Object.keys(r.prw||{}).map(Number).sort((a,b)=>a-b),pr=Object.entries(r.prc||{}).sort((a,b)=>b[1]-a[1]);
    modal(esc(cap(r.lbl))+' tables',`${esc(r.role)} · ${S} · how often it called the softer defense right the next week, stat by stat`,
      `<div class="kpis">${kpi('called it right',pc(r.pr),'coin flip = 50%',ok(r.pr)?'g':'')}${kpi('yards',pc((r.prf||{}).Yds),'rushing, receiving, passing')}${kpi('catches',pc((r.prf||{}).Rec),'receptions by slot')}${kpi('touchdowns',pc((r.prf||{}).TD),'the noisiest stat')}</div>
      <div class="btx2"><div class="panel"><h3>week by week</h3><table class="fx bt"><thead><tr><th>week</th><th>all stats</th><th>yards</th><th>catches</th><th>TDs</th></tr></thead><tbody>
        ${wk.map(w=>{const f=(r.prwf||{})[w]||{};return `<tr><td>${w}</td><td data-v="${r.prw[w]}"><b style="color:${col(r.prw[w])}">${pc(r.prw[w])}</b></td>${['Yds','Rec','TD'].map(x=>`<td data-v="${f[x]??''}" style="color:${col(f[x])}">${pc(f[x])}</td>`).join('')}</tr>`}).join('')}</tbody></table>
        <h3 style="margin-top:12px">against the other tables</h3><table class="fx bt"><tbody>${(B.dsets[S].rows||[]).map(x=>`<tr${x.k===k?' class="best"':''}><td>${esc(cap(x.lbl))}</td><td data-v="${x.pr}" style="color:${col(x.pr)}">${pc(x.pr)}</td></tr>`).join('')}</tbody></table></div>
        <div class="panel"><h3>every stat, best to worst <span class="f">how often it called the softer defense for that stat</span></h3><table class="fx bt"><thead><tr><th>stat</th><th>called right</th></tr></thead><tbody>${pr.map(([c,v])=>`<tr><td>${esc(STN(c))}</td><td data-v="${v}">${bar(v)}<b style="color:${col(v)};margin-left:8px">${pc(v)}</b></td></tr>`).join('')}</tbody></table></div></div>`)}
  function stPop(t){const R0=(J.picksAll||[]).filter(p=>p.type===t),r=(B.strat||[]).find(x=>x.k===t)||{};
    const CL={};(J.picksClv||[]).forEach(c=>{if(c.type===t)CL[c.ref+'|'+c.side+'|'+c.week]=c});
    const m110=['PROP','ATS','TOTAL'].includes(t),unit=p=>p.result==='W'?(m110?100/110:(+p.market_ref>0?1/(+p.market_ref)-1:100/110)):p.result==='L'?-1:0;
    const cl=p=>CL[p.ref+'|'+p.side+'|'+p.week]||{},beat=p=>{const b=String(cl(p).beat||'').toLowerCase();return b===''?null:['true','1','1.0'].includes(b)};
    const G=R0.filter(p=>p.result==='W'||p.result==='L'||p.result==='P'),wks=[...new Set(R0.map(p=>+p.week))].sort((a,b)=>a-b);
    let run=0;const WK=wks.map(w=>{const x=G.filter(p=>+p.week===w),u=x.reduce((s,p)=>s+unit(p),0);run+=u;const cb=x.map(beat).filter(v=>v!=null);
      return {w,n:R0.filter(p=>+p.week===w).length,W:x.filter(p=>p.result==='W').length,L:x.filter(p=>p.result==='L').length,P:x.filter(p=>p.result==='P').length,u,run,cb:cb.length?cb.filter(Boolean).length/cb.length:null}});
    const U=G.reduce((s,p)=>s+unit(p),0),cbs=G.map(beat).filter(v=>v!=null),hit=r.hit,need=r.be;
    const grp=(f,lab)=>{const M={};G.filter(p=>p.result!=='P').forEach(p=>{const k=f(p);if(k==null)return;const o=M[k]=M[k]||{k,w:0,l:0,u:0};p.result==='W'?o.w++:o.l++;o.u+=unit(p)});
      return `<table class="fx bt"><thead><tr><th>${lab}</th><th>record</th><th>hit</th><th>units</th></tr></thead><tbody>${Object.values(M).sort((a,b)=>(b.w+b.l)-(a.w+a.l)).map(o=>`<tr><td>${esc(String(o.k))}</td><td>${o.w}-${o.l}</td><td data-v="${o.w/(o.w+o.l)}" style="color:${o.w/(o.w+o.l)>(need||.5)?'var(--green)':'var(--red)'}"><b>${pc(o.w/(o.w+o.l))}</b></td><td data-v="${o.u}" style="color:${o.u>=0?'var(--green)':'var(--red)'}">${o.u>=0?'+':''}${o.u.toFixed(1)}</td></tr>`).join('')}</tbody></table>`};
    const eb=p=>{const e=+p.edge;return isNaN(e)?null:e>=6?'edge 6+':e>=3?'edge 3–6':'edge under 3'};
    const pick=p=>t==='PROP'||t==='TD'?`${pn(p.player,p.team,true)}`:`${esc(p.player||p.team||'')}`;
    const fmtp=v=>v===''||v==null||isNaN(+v)?'—':(+v<=1?Math.round(100*+v)+'%':(+v).toFixed(1));
    const rowsHtml=w=>R0.filter(p=>w==='all'||+p.week===+w).sort((a,b)=>+b.week-+a.week||(+b.edge||0)-(+a.edge||0)).map(p=>{const c=cl(p),b=beat(p);
      return `<tr><td>${p.week}</td><td>${pick(p)}</td><td class="mini">${esc(p.opp||'')}</td><td>${esc((p.market||'').replace(/_/g,' '))}</td><td>${esc(p.side||'')}</td><td class="n">${esc(p.line||'')}</td><td class="n" data-v="${p.model||''}">${fmtp(p.model)}</td><td class="n" data-v="${p.market_ref||''}">${fmtp(p.market_ref)}</td><td class="n" data-v="${p.edge||''}">${p.edge!==''&&p.edge!=null?(+p.edge).toFixed(1):'—'}</td>
        <td data-v="${p.result||''}">${p.result==='W'?'<b style="color:var(--green)">✓ won</b>':p.result==='L'?'<b style="color:var(--red)">✗ lost</b>':p.result==='P'?'push':p.result?esc(p.result):'<span class="dim">open</span>'}</td><td class="n">${esc(p.actual||'')}</td><td class="n">${esc(c.close_line||'')}</td><td>${b==null?'<span class="dim">—</span>':b?'<span style="color:var(--green)">yes</span>':'<span style="color:var(--red)">no</span>'}</td></tr>`}).join('');
    modal(esc(r.lbl||t),`every pick frozen before kickoff and graded from the box scores · ${R0.length} picks · ${G.length} graded`,
      `<div class="kpis">${kpi('record',`${r.w??0}-${r.l??0}${r.p?'-'+r.p:''}`,`${R0.length-G.length} still open`)}${kpi('hit rate',pc(hit),`needs ${pc(need)} to profit`,hit>need?'g':'r')}${kpi('units',`${U>=0?'+':''}${U.toFixed(1)}`,m110?'1 unit a pick at −110':'1 unit a pick at the market\'s price',U>=0?'g':'r')}${kpi('beat the closing line',pc(cbs.length?cbs.filter(Boolean).length/cbs.length:null),`${cbs.length} picks with a closing line`)}</div>
      <div class="panel"><h3>week by week <span class="f">running units = the total after that week</span></h3><table class="fx bt"><thead><tr><th>week</th><th>picks</th><th>record</th><th>hit</th><th>units</th><th>running</th><th>beat the close</th></tr></thead><tbody>
        ${WK.map(x=>`<tr><td>${x.w}</td><td>${x.n}</td><td>${x.W}-${x.L}${x.P?'-'+x.P:''}</td><td data-v="${x.W+x.L?x.W/(x.W+x.L):''}"><b style="color:${x.W+x.L?(x.W/(x.W+x.L)>(need||.5)?'var(--green)':'var(--red)'):'var(--dim)'}">${x.W+x.L?pc(x.W/(x.W+x.L)):'—'}</b></td><td data-v="${x.u}" style="color:${x.u>=0?'var(--green)':'var(--red)'}">${x.u>=0?'+':''}${x.u.toFixed(1)}</td><td data-v="${x.run}"><b style="color:${x.run>=0?'var(--green)':'var(--red)'}">${x.run>=0?'+':''}${x.run.toFixed(1)}</b></td><td>${pc(x.cb)}</td></tr>`).join('')}</tbody></table></div>
      ${t==='PROP'?`<div class="btx2"><div class="panel"><h3>by market</h3>${grp(p=>(p.market||'').replace(/_/g,' '),'market')}</div><div class="panel"><h3>by the model's edge</h3>${grp(eb,'edge')}</div></div>`:''}
      <div class="panel"><h3>every pick <span class="chips" id="btPW" style="margin-left:8px"><button data-w="all" class="on">all weeks</button>${wks.slice().reverse().map(w=>`<button data-w="${w}">wk ${w}</button>`).join('')}</span><span class="f">model / market = chance of the pick hitting · edge = the model over the market · close = the closing line · every column sorts</span></h3>
        <table class="fx bt" id="btPT"><thead><tr><th>wk</th><th>pick</th><th>opp</th><th>market</th><th>side</th><th>line</th><th>model</th><th>market</th><th>edge</th><th>result</th><th>actual</th><th>close</th><th>beat close</th></tr></thead><tbody>${rowsHtml('all')}</tbody></table></div>`);
    const PW=document.getElementById('btPW');if(PW)PW.querySelectorAll('button').forEach(b=>b.onclick=()=>{PW.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));document.querySelector('#btPT tbody').innerHTML=rowsHtml(b.dataset.w)})}
  function tdpPop(){const T=J.tdpicks;if(!T||!T.bt)return;const BW=(T.bt.weeks||[]).slice().reverse(),TOP=T.bt.top||{};
    modal('TD Picks — each week\'s top 10',`picked before kickoff by a model refit on earlier weeks only, then graded · ${(T.bt.top10||[])[0]} of ${(T.bt.top10||[])[1]} scored`,
      `<div class="kpis">${kpi('top 10 scored',pc(T.bt.top10?T.bt.top10[0]/T.bt.top10[1]:null),'every week since 2025','g')}${kpi('locks (50%+)',T.bt.tiers&&T.bt.tiers.lock?pc(T.bt.tiers.lock[1]/T.bt.tiers.lock[0]):'—',T.bt.tiers&&T.bt.tiers.lock?`${T.bt.tiers.lock[1]} of ${T.bt.tiers.lock[0]}`:'','g')}${kpi('everyone',pc(BW.length?BW.reduce((s,w)=>s+w[3],0)/BW.reduce((s,w)=>s+w[2],0):null),'how often any slot owner scored')}</div>
      <div class="panel"><h3>every week's ten <span class="f">✓ scored · ✗ didn't · the model's chance before kickoff</span></h3>${BW.map(w=>{const L=(TOP[w[0]+'-'+w[1]]||[]).slice(0,10);return `<div class="btwk"><h4>${w[0]} week ${w[1]} <span class="mini">· ${w[4]} of ${w[5]} scored · everyone ${pc(w[2]?w[3]/w[2]:null)}</span></h4><div class="wkpcs">${L.map(x=>`<span class="wkpc ${x[4]?'w':'l'}">${pn(x[0],x[1],true)}<i>${pc(x[3]).replace('.0%','%')}</i><b>${x[4]?'✓':'✗'}</b></span>`).join('')}</div></div>`}).join('')}</div>`)}
  el.addEventListener('click',e=>{if(e.target.closest('.plink,a,button'))return;const t=e.target.closest('[data-bsg],[data-bds],[data-bst],[data-btp]');if(!t||!el.contains(t))return;
    if(t.dataset.bsg)sigPop(t.dataset.bsg);else if(t.dataset.bds)dsPop(t.dataset.bds);else if(t.dataset.bst)stPop(t.dataset.bst);else tdpPop()});
  const wire=(id,a,f)=>$('#'+id).querySelectorAll('button').forEach(b=>b.onclick=()=>{f(b.dataset[a]);''')

# ---------------- CSS
rep('''.btb{position:relative;display:block;height:12px;''', '''.btv .c,.btsc .c,.btr{cursor:pointer}.btv .c:hover,.btsc .c:hover{border-color:var(--edge2);background:#ffffff05}.btr:hover{background:#ffffff07}
.btv .c::after,.btsc .c::after{content:'history ›';display:block;margin-top:7px;font:600 9.5px var(--mono);letter-spacing:.06em;color:var(--acc)}
#ppModal .btx2{display:grid;grid-template-columns:1fr 1fr;gap:12px}#ppModal .btwk{margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid var(--edge)}#ppModal .btwk h4{margin:2px 0 6px;font-size:13px}
#ppModal .btlh{font-weight:700;margin:0 0 3px}#ppModal .btlh.g{color:var(--green)}#ppModal .btlh.r{color:var(--red)}#ppModal table.btex{width:100%}#ppModal table.btex td{padding:2px 6px;font-size:11.5px}
#ppModal table.bt td,#ppModal table.bt th{text-align:right;white-space:nowrap}#ppModal table.bt td:first-child,#ppModal table.bt th:first-child,#ppModal table.bt td:nth-child(2),#ppModal table.bt th:nth-child(2){text-align:left}
@media(max-width:840px){#ppModal .btx2{grid-template-columns:1fr}}
.btb{position:relative;display:block;height:12px;''')
rep("Object.assign(NOTES,{backtest:['v28','", "Object.assign(NOTES,{backtest:['v29','every card and bar now opens its proof: week by week, the players each number rated highest and lowest with what happened, every stat a table called, and every graded pick behind each strategy (with units, running total and the closing line) · ")
open(P, 'w', encoding='utf-8').write(s)
print('patch_v29: Backtest pop-ups')
