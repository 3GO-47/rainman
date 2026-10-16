# -*- coding: utf-8 -*-
"""v16 — F6 TEST › META: every board's best signal on one grid (TD Board / TD Grid, Player Grid, H2H Grid, Scheme, anytime-TD model),
laid out exactly like the TD Grid — every position together, then QB, RB, WR, TE — with the data-set picker driving the ranks."""
def patch(path,pairs):
    s=open(path,encoding='utf-8').read()
    for old,new in pairs:
        assert s.count(old)==1,(path,old[:80],s.count(old))
        s=s.replace(old,new)
    open(path,'w',encoding='utf-8').write(s)

META_JS = r"""
/* ---------------- META (F6 TEST) — every board's best signal on one grid ----------------
   One row per slot owner, in the TD Grid's five columns (every position together, then QB, RB, WR, TE). Each row carries the
   number every other board ranks on, read from the data set picked:
     TD  = touchdowns this week's opponent allows to his slot, rank of NT (the TD Board / TD Grid number, QB mode included)
     ATD = the anytime-TD model's chance he scores (the TD Board column), shaded within his own position
     Ψ   = mean of the opponent's ranks across every stat of his slot (the Player Grid number)
     H2H = his own PPR per game in prior meetings with this opponent, ▲ / ▼ against his norm (the H2H Grid number)
     SCH = what the opponent's defensive family gives up to his slot vs league, plus 0.6 × the lift from its missing men (Scheme)
   META folds them into one 0–100 score. Each signal becomes a 0–1 softness: TD and Ψ on their own 1..NT scale, the rest as
   percentiles among this week's slot owners (ATD within position; H2H shrunk toward zero under three meetings). Weights
   Ψ .30 · TD .25 · SCH .15 · H2H .15 · ATD .15; a missing signal drops out and the score is pulled toward 50 by the share of
   weight that was missing, so a row built on one signal can't outrank a row that is soft on all five. Nothing is entered by
   hand: every input is a game log or a table another board already shows. */
const META_W={psi:.30,td:.25,sch:.15,h2h:.15,atd:.15};
const META_L=[['meta','META','everything together · 0–100, 100 = the softest spot on every signal'],['td','TD','touchdowns the opponent allows to his slot · rank, 1 = the most'],['atd','ATD','the anytime-TD model\'s chance he scores'],['psi','Ψ','the softest field across every stat of his slot · 1 = softest'],['h2h','H2H','his own PPR in prior meetings with this opponent vs his norm'],['sch','SCH','the opponent\'s defensive style for his slot, plus its missing men']];
function metaGrid(root='#meta',px='mt'){
  const srcs=Object.keys(J.dvp),$$=k=>$('#'+px+k),live=new Set(TD_SLOTS);
  const LBL=Object.fromEntries(META_L.map(([k,l])=>[k,l])),DESC=new Set(['meta','atd','h2h','sch']);
  let lens='meta';
  $(root).innerHTML=`<div class="controls">
    <span class="chips" id="${px}Lens" title="what every column is ranked by — META folds all of them together; click any column header to re-sort just that column">${META_L.map(([k,l,t])=>`<button data-l="${k}" class="${k==='meta'?'on':''}" title="${esc(t)}">${l}</button>`).join('')}</span>
    <span class="chips" id="${px}Slots" title="which depth slots the board covers — click to toggle, ALL for every body on the chart">
      <button data-s="">all</button>${TD_SLOTS.map(s=>`<button data-s="${s}" class="on">${s}</button>`).join('')}</span>
    <select id="${px}Src" title="which data set the TD and Ψ ranks read — and with them META">${srcs.map(s=>`<option value="${s}" ${s==='combined'?'selected':''}>${s}</option>`).join('')}<option value="mu">μ every set</option></select>
    <select id="${px}QB" title="a QB's slot has two TD-allowed stats; pick which one his TD column reads"><option value="rush" selected>QB: rushing / receiving TD</option><option value="pass">QB: passing TD</option><option value="both">QB: mean of both</option></select>
    <select id="${px}Se" title="which seasons of head-to-head history count"><option value="">H2H: all seasons (${ALL_SE[0]}–${String(ALL_SE[ALL_SE.length-1]).slice(2)})</option>${ALL_SE.slice().reverse().map(s=>`<option value="${s}">H2H: ${s} only</option>`).join('')}</select>
    <select id="${px}Inj"><option value="x" selected>hide OUT</option><option value="">incl. OUT</option></select>
    <input id="${px}Q" placeholder="search player..." size="15">
    <span class="note">every board at once. <b>META</b> folds the other five into one score, 0–100 (100 = the softest spot on every signal) &middot; <b>TD</b> = touchdowns this week's opponent allows to his slot, rank of ${NT} (1 = the most) &middot; <b>ATD</b> = the anytime-TD model's chance he scores, shaded within his position &middot; <b>Ψ</b> = the opponent's mean rank across every stat of his slot &middot; <b>H2H</b> = his own PPR per game in past meetings with this opponent, ▲ / ▼ against his norm &middot; <b>SCH</b> = what that defense's style gives up to his slot vs league, plus its missing men &middot; the data-set select drives TD, Ψ and META; hover META for the breakdown &middot; the lens chips re-rank every column at once, a header click re-sorts one &middot; click a name for his card</span>
  </div>
  <div class="mlead" id="${px}Lead"></div>
  <div class="lgrid td5 wide full meta">${['ALL'].concat(TPOS).map(p=>`<section class="lgcol"><h3>${p==='ALL'?'◉ all':posIcon(p,12)+' '+p} <span class="gl" id="${px}G${p}"></span> <span class="f" id="${px}N${p}"></span></h3><div id="${px}B${p}"></div></section>`).join('')}</div>`;
  const sort={};['ALL'].concat(TPOS).forEach(p=>sort[p]={k:'meta',a:false});
  const avg=a=>{const g=a.filter(v=>v!=null);return g.length?g.reduce((s,v)=>s+v,0)/g.length:null};
  /* mid-rank percentile of v in a pool: share below + half the ties */
  const pct=arr=>{const s=arr.filter(v=>v!=null).sort((a,b)=>a-b),n=s.length;
    const lb=v=>{let lo=0,hi=n;while(lo<hi){const m=(lo+hi)>>1;if(s[m]<v)lo=m+1;else hi=m}return lo};
    const ub=v=>{let lo=0,hi=n;while(lo<hi){const m=(lo+hi)>>1;if(s[m]<=v)lo=m+1;else hi=m}return lo};
    return v=>v==null||!n?null:(lb(v)+(ub(v)-lb(v))/2)/n};
  const eq=p=>1+(1-p)*(NT-1);  /* a 0–1 softness back onto the rank scale, so it shades like every other rank pill */
  const clamp=v=>Math.max(0,Math.min(1,v));
  const tdCols=(grp,pos)=>{const st=LABDEF[pos].stats(grp).filter(c=>/TD/.test(c));if(st.length<2)return st;
    const m=$$('QB').value,pass=st.find(c=>c==='P TD'),rush=st.find(c=>c!=='P TD');return m==='pass'?[pass]:m==='both'?st:[rush]};
  let ROWS=[];
  function build(){
    const wk=G.week,v=$$('Src').value,S=v==='mu'?srcs:[v],se=$$('Se').value;
    const T=((J.betting||{}).td||[]).filter(r=>+r.week===wk);
    const tdOf=u=>T.find(r=>r.player===u.player&&r.team===u.team)||T.find(r=>r.player===u.player);
    const R=UNIVERSE.filter(u=>TPOS.includes(u.pos)&&u.grp).map(u=>{
      const oppRaw=(J.sched26[u.team]||[])[wk-1]||'',opp=oppRaw&&oppRaw!=='BYE'?oppRaw.replace('@',''):'';
      const pos=u.pos,tdc=tdCols(u.grp,pos);
      const dOf=s=>opp&&J.dvp[s]&&J.dvp[s][opp]?J.dvp[s][opp]:null;
      const tdBy=S.map(s=>{const d=dOf(s);if(!d)return null;return avg(tdc.map(c=>d.stats[c]?d.stats[c].rank:null))});
      const psiBy=S.map(s=>{const d=dOf(s);return d&&d.comps&&d.comps[u.grp]!=null?d.comps[u.grp]:null});
      const L=PLOGS[u.ln||u.player]||[];
      const vs=opp?L.filter(l=>l[LOG.opp]===opp&&(!se||l[LOG.season]===+se)):[];
      const all=se?L.filter(l=>l[LOG.season]===+se):L;
      const mf=(a,f)=>a.length?a.reduce((t,l)=>t+f(l),0)/a.length:null;
      const hp=mf(vs,l=>l[LOG.fppr]),hb=mf(all,l=>l[LOG.fppr]);
      const hd=hp!=null&&hb!=null&&hb>0?hp/hb-1:null;
      let e=null,lift=0;if(opp){try{e=schemeEdge(opp,u.grp)}catch(_){}try{lift=(injLift(opp)[u.grp]||{}).pct||0}catch(_){}}
      const t=tdOf(u),atd=t&&t.p_model!=null&&t.p_model!==''?+t.p_model:null;
      return {u,pos,oppRaw,opp,td:avg(tdBy),psi:avg(psiBy),S,n:vs.length,hp,hb,hd,hS:hd==null?null:hd*Math.min(vs.length,3)/3,
        gpAll:all.length,last:vs.length?vs[vs.length-1]:null,e,lift,sch:e?(e.idx-100)+lift*.6:null,atd,t,
        pool:TD_SLOTS.includes(u.dslot||u.slot)}});
    /* percentiles come from this week's slot owners only, so a filter or a search never moves a score */
    const P=R.filter(x=>x.pool&&x.opp),pH=pct(P.map(x=>x.hS)),pS=pct(P.map(x=>x.sch)),pA={};
    TPOS.forEach(p=>pA[p]=pct(P.filter(x=>x.pos===p).map(x=>x.atd)));
    const W=Object.values(META_W).reduce((a,b)=>a+b,0);
    R.forEach(x=>{const c={psi:x.psi==null?null:clamp((NT-x.psi)/(NT-1)),td:x.td==null?null:clamp((NT-x.td)/(NT-1)),h2h:pH(x.hS),sch:pS(x.sch),atd:pA[x.pos](x.atd)};
      let s=0,w=0;Object.entries(META_W).forEach(([k,wt])=>{if(c[k]!=null){s+=wt*c[k];w+=wt}});
      x.c=c;x.cov=w/W;x.meta=w&&x.opp?50+(100*s/w-50)*(.6+.4*w/W):null});
    ROWS=R}
  const keep=x=>{const q=$$('Q').value.toLowerCase();return inU(x.u)&&(!live.size||live.has(x.u.dslot||x.u.slot))&&($$('Inj').value!=='x'||x.u.inj!=='-1')&&(!q||x.u.player.toLowerCase().includes(q))};
  const sv=(x,k)=>k==='meta'?x.meta:k==='td'?x.td:k==='atd'?x.atd:k==='psi'?x.psi:k==='h2h'?x.hS:k==='sch'?x.sch:k==='player'?x.u.player:k==='opp'?(x.opp||null):k==='pos'?TPOS.indexOf(x.pos):null;
  const cmp=(k,asc)=>(a,b)=>{const x=sv(a,k),y=sv(b,k);
    if(x==null||y==null){if(x==null&&y==null)return (b.meta??-1)-(a.meta??-1);return x==null?1:-1}
    return (x<y?-1:x>y?1:0)*(asc?1:-1)||(k==='td'?(b.atd??-1)-(a.atd??-1):0)||(b.meta??-1)-(a.meta??-1)};
  const f1=v=>v==null?'—':(+v).toFixed(1);
  const why=x=>[`META ${x.meta==null?'—':Math.round(x.meta)} of 100 · ${Math.round(100*x.cov)}% of the weight has data`,
    `Ψ ${f1(x.psi)} of ${NT} → ${x.c.psi==null?'—':Math.round(100*x.c.psi)} (weight ${META_W.psi})`,
    `TD rank ${f1(x.td)} of ${NT} → ${x.c.td==null?'—':Math.round(100*x.c.td)} (weight ${META_W.td})`,
    `scheme ${x.sch==null?'—':(x.sch>=0?'+':'')+x.sch.toFixed(1)} → ${x.c.sch==null?'—':Math.round(100*x.c.sch)} (weight ${META_W.sch})`,
    `H2H ${x.hd==null?'no prior meeting':(x.hd>=0?'+':'')+Math.round(100*x.hd)+'% vs his norm over '+x.n+' game'+(x.n===1?'':'s')} → ${x.c.h2h==null?'—':Math.round(100*x.c.h2h)} (weight ${META_W.h2h})`,
    `ATD ${x.atd==null?'no model':Math.round(100*x.atd)+'%'} → ${x.c.atd==null?'—':Math.round(100*x.c.atd)} (weight ${META_W.atd})`].join('\n');
  const setL=()=>{const v=$$('Src').value;return v==='mu'?'μ every set':v};
  const schC=v=>v>=6?'#00c853':v>=2?'#8bc34a':v<=-6?'#ff5252':v<=-2?'#ff8a65':'var(--dim)';
  const cells=x=>{
    const meta=x.meta==null?'<td class="md gs"><span class="dim">·</span></td>'
      :`<td class="md gs" title="${esc(why(x))}"><span class="badge" style="${gradeStyle(eq(x.meta/100))}">${Math.round(x.meta)}</span></td>`;
    const td=x.td==null?'<td class="op gs"><span class="dim">·</span></td>'
      :`<td class="op gs" title="${esc(`touchdowns ${x.opp} allows to ${x.u.grp} · ${setL()} · rank ${f1(x.td)} of ${NT}`)}"><span class="badge" style="${gradeStyle(x.td)}">${Math.round(x.td)}</span></td>`;
    const atd=x.atd==null?'<td class="op"><span class="dim">·</span></td>'
      :`<td class="op" title="${esc(`anytime-TD model ${(100*x.atd).toFixed(0)}%${x.t&&x.t.fair!=null?' · fair '+mlTxt(+x.t.fair):''}${x.t&&x.t.price!=null?' · best price '+mlTxt(+x.t.price)+(x.t.book?' ('+x.t.book+')':''):''}${x.t&&x.t.ev!=null?' · EV '+(+x.t.ev).toFixed(1)+'%':''} · shaded within ${x.pos}s`)}"><span class="badge" style="${x.c.atd==null?'':gradeStyle(eq(x.c.atd))}">${Math.round(100*x.atd)}</span></td>`;
    const psi=x.psi==null?'<td class="op"><span class="dim">·</span></td>'
      :`<td class="op" title="${esc(`mean of ${x.opp}'s ranks across every ${x.u.grp} stat · ${setL()} · 1 = softest`)}"><span class="psi" style="color:${gradeColor(x.psi)}">${Math.round(x.psi)}</span></td>`;
    let h2h='<td class="md hp"><span class="dim">·</span></td>';
    if(x.hp!=null){const cls=x.hd==null?'':x.hd>=.1?'rise':x.hd<=-.1?'fall':'';
      h2h=`<td class="md hp ${cls}" title="${esc(`${x.hp.toFixed(1)} PPR per game vs ${x.opp} over ${x.n} game${x.n===1?'':'s'}${x.hb!=null?` · his average over all ${x.gpAll} logged games: ${x.hb.toFixed(1)}`:''}${x.last?` · last meeting ${x.last[LOG.season]} wk ${x.last[LOG.week]}`:''}`)}"><b>${x.hp.toFixed(1)}</b>${x.hd==null?'':`<i>${x.hd>=0?'▲':'▼'}</i>`}</td>`}
    const sch=x.sch==null?'<td class="md sch"><span class="dim">·</span></td>'
      :`<td class="md sch" style="color:${schC(x.sch)}" title="${esc(`${x.e.fam}: ${(+x.e.ppr).toFixed(1)} PPR/g to ${x.u.grp} vs ${(+x.e.lg).toFixed(1)} league (${x.e.idx>=100?'+':''}${(x.e.idx-100).toFixed(0)}%)${x.lift>=1?` · missing men lift +${x.lift.toFixed(0)}%`:''}`)}">${x.sch>=0?'+':''}${Math.round(x.sch)}</td>`;
    return meta+td+atd+psi+h2h+sch};
  function col(p){
    const st=sort[p];
    const R=ROWS.filter(x=>(p==='ALL'||x.pos===p)&&keep(x)).sort(cmp(st.k,st.a));
    $$('N'+p).textContent=R.length+(R.length===1?' player':' players');
    $$('G'+p).textContent=`ranked by ${LBL[st.k]||st.k} · ${setL()}`;
    const th=(k,l,tip,cls)=>`<th class="${cls||''}" data-k="${k}" title="${esc(tip||'')}">${l}${st.k===k?(st.a?' ▲':' ▼'):''}</th>`;
    const wname=p==='ALL'?23:27,wpos=p==='ALL'?6:0,wopp=p==='ALL'?14:16,wnum=((100-wname-wpos-wopp)/6).toFixed(2);
    $$('B'+p).innerHTML=`<table class="lgt"><colgroup><col style="width:${wname}%">${p==='ALL'?`<col style="width:${wpos}%">`:''}<col style="width:${wopp}%">${Array.from({length:6},()=>`<col style="width:${wnum}%">`).join('')}</colgroup><thead>
      <tr class="hd">${th('player','Player')}${p==='ALL'?th('pos',''):''}${th('opp','Opp',"this week's opponent")}
      ${th('meta','META','every signal folded into one score · 0–100, 100 = softest on all of them · hover a cell for the breakdown','md gs')}
      ${th('td','TD','touchdowns the opponent allows to his slot · rank of '+NT+' · 1 = the most','op gs')}
      ${th('atd','ATD','anytime-TD model: % chance he scores · shaded within his position','op')}
      ${th('psi','Ψ','mean of the opponent\'s ranks across every stat of his slot · 1 = softest','op')}
      ${th('h2h','H2H','his own PPR per game in past meetings with this opponent · ▲ 10%+ above his norm, ▼ 10%+ below','md')}
      ${th('sch','SCH','what the opponent\'s defensive style gives up to his slot vs league, % · plus 0.6 × the lift from its missing men','md')}</tr></thead><tbody>
      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.u.player)}" title="${esc(x.u.player)} · ${esc(x.u.dslot||x.u.slot)} · ${esc(x.u.team)}${x.meta==null?'':' · META '+Math.round(x.meta)}">${esc(pshort(x.u.player))}${x.u.inj==='0'?' <span class="inj0">Q</span>':x.u.inj==='-1'?' <span class="injm1">OUT</span>':''}</td>
        ${p==='ALL'?`<td style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</td>`:''}<td>${x.opp?oppcell(x.oppRaw):'<span class="dim">bye</span>'}</td>${cells(x)}</tr>`).join('')
        ||`<tr><td colspan="${p==='ALL'?9:8}" class="dim">nothing matches</td></tr>`}</tbody></table>`;
    $$('B'+p).querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=h.dataset.k;
      if(st.k===k)st.a=!st.a;else{st.k=k;st.a=!DESC.has(k)}col(p)});
    tWire($$('B'+p));
    const sec=$$('B'+p).closest('.lgcol'),h=sec&&sec.querySelector('h3');if(h)sec.style.setProperty('--h3h',h.offsetHeight+'px');
  }
  /* the week's best on each signal, from whatever the board is showing */
  function lead(){
    const R=ROWS.filter(keep),top=(f,k,asc,n=3)=>R.filter(x=>sv(x,k)!=null&&(!f||f(x))).sort(cmp(k,asc)).slice(0,n);
    const nm=x=>`<span class="plink" data-p="${esc(x.u.player)}" title="${esc(x.u.player)} · ${esc(x.u.dslot||x.u.slot)} · ${esc(x.u.team)}">${esc(pshort(x.u.player))}</span>`;
    const line=(x,val)=>`<div class="mlr"><span style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</span>${nm(x)}<span class="mini">${x.opp?oppcell(x.oppRaw):''}</span>${val}</div>`;
    const B=(r,s)=>`<span class="badge" style="${s}">${r}</span>`;
    const cards=[
      ['best spots · META','g',top(null,'meta',false),x=>B(Math.round(x.meta),gradeStyle(eq(x.meta/100)))],
      ['TD spots','',top(null,'td',true),x=>B(Math.round(x.td),gradeStyle(x.td))],
      ['anytime-TD model','',top(null,'atd',false),x=>B(Math.round(100*x.atd)+'%',x.c.atd==null?'':gradeStyle(eq(x.c.atd)))],
      ['softest field · Ψ','',top(null,'psi',true),x=>`<span class="psi" style="color:${gradeColor(x.psi)}">${Math.round(x.psi)}</span>`],
      ['head to head','',top(x=>x.n>0,'h2h',false),x=>`<b class="${x.hd>=.1?'rise':x.hd<=-.1?'fall':''}">${x.hp.toFixed(1)}</b><span class="mini">${x.n}g</span>`],
      ['scheme edge','',top(null,'sch',false),x=>`<b style="color:${schC(x.sch)}">${x.sch>=0?'+':''}${Math.round(x.sch)}</b>`],
      ['avoid · META','r',top(null,'meta',true),x=>B(Math.round(x.meta),gradeStyle(eq(x.meta/100)))]];
    $$('Lead').innerHTML=cards.map(([t,tone,L,val])=>`<div class="mlc ${tone}"><div class="mlh">${t}</div>${L.map(x=>line(x,val(x))).join('')||'<div class="mini dim">nothing on the board</div>'}</div>`).join('');
    tWire($$('Lead'))}
  const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead()};
  const all=()=>{build();cols()};
  ['Src','QB','Se','Inj'].forEach(i=>$$(i).onchange=all);$$('Q').oninput=cols;
  $$('Slots').querySelectorAll('button').forEach(b=>b.onclick=()=>{const v=b.dataset.s;
    if(!v)live.clear();else live.has(v)?live.delete(v):live.add(v);
    $$('Slots').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.s?live.has(x.dataset.s):live.size===0));cols()});
  $$('Lens').querySelectorAll('button').forEach(b=>b.onclick=()=>{lens=b.dataset.l;
    $$('Lens').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));
    Object.keys(sort).forEach(p=>sort[p]={k:lens,a:!DESC.has(lens)});['ALL'].concat(TPOS).forEach(col)});
  all();RR.push(all);
}
"""

META_CSS = r"""
/* ---- v16 META: the TD Grid's columns, one more block of signals ---- */
.lgrid.meta th.op,.lgrid.meta th.md{letter-spacing:0}
.lgrid.meta td.hp{text-align:right;white-space:nowrap}.lgrid.meta td.hp b{font:700 11px var(--mono);color:var(--txt)}
.lgrid.meta td.hp i{font-style:normal;font-size:9.5px;margin-left:2px}.lgrid.meta td.hp.rise b,.lgrid.meta td.hp.rise i{color:var(--green)}.lgrid.meta td.hp.fall b,.lgrid.meta td.hp.fall i{color:var(--red)}
.lgrid.meta td.sch{text-align:right;font:600 10.5px var(--mono);font-variant-numeric:tabular-nums}
.lgrid.meta td .psi{font:700 11px var(--mono)}
.mlead{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px;margin:0 0 10px}
@media(max-width:1500px){.mlead{grid-template-columns:repeat(4,minmax(0,1fr))}}@media(max-width:760px){.mlead{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
.mlc{background:var(--panel);border:1px solid var(--edge);border-top:2px solid var(--edge2);border-radius:8px;padding:6px 8px;min-width:0}
.mlc.g{border-top-color:var(--green)}.mlc.r{border-top-color:var(--red)}
.mlh{font:600 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2);margin-bottom:3px}
.mlr{display:grid;grid-template-columns:14px minmax(0,1fr) auto auto;gap:5px;align-items:center;font-size:11.5px;padding:2px 0;border-bottom:1px dashed var(--edge)}
.mlr:last-child{border-bottom:0}.mlr .plink{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.mlr b{font:700 11px var(--mono)}.mlr .mini{white-space:nowrap}.mlr .badge{min-width:24px;text-align:center}"""

T='scripts/dashboard_template.html'
patch(T,[
 # nav item: first in F6 TEST
 ("""{id:'test',fk:'F6',label:'TEST',items:[
   {id:'labgrid',""",
  """{id:'test',fk:'F6',label:'TEST',items:[
   {id:'meta',label:'META',desc:'every board at once: the TD Board, Player Grid, H2H Grid, Scheme and the anytime-TD model folded into one score per starter, in the TD Grid\\'s five columns \\u2014 every position together, then QB, RB, WR and TE \\u2014 with the week\\'s best spot on each signal across the top',c:'test',sub:'meta'},
   {id:'labgrid',"""),
 # container
 ("""<div id="test" hidden><div id="dev" hidden></div>""","""<div id="test" hidden><div id="meta" hidden></div><div id="dev" hidden></div>"""),
 # sub switch
 ("""if(it.c==='test'){['labgrid','gameview',""","""if(it.c==='test'){['meta','labgrid','gameview',"""),
 # renderer, right before the Game View block
 ("""/* ---------------- Game View — one game, everything the site knows about it ----------------""",
  META_JS + """
/* ---------------- Game View — one game, everything the site knows about it ----------------"""),
 # boot
 ("""['test',labGrid],""","""['test',labGrid],['test',metaGrid],"""),
 # css
 (""".lgrid.hh table.lgt td.op{text-align:right;font:500 11px var(--mono)}""",
  """.lgrid.hh table.lgt td.op{text-align:right;font:500 11px var(--mono)}""" + META_CSS),
 # notes
 (""" overview:['v15',""",""" meta:['v16','new tab: every board at once — TD, anytime-TD model, Ψ, head to head and scheme folded into one META score per starter, five columns like the TD Grid, every data set selectable, the week\\'s best on each signal across the top'],
 overview:['v15',"""),
])
# intro: the reading key under the tab name
s=open(T,encoding='utf-8').read()
old="const INTRO={\n"
assert s.count(old)==1
s=s.replace(old,old+""" meta:{what:'Every board at once.',how:['META = every signal in one score, 0–100 — 100 = the softest spot on all of them; hover a META cell for the breakdown','TD and Ψ = the opponent\\'s rank of 32, 1 = allows the most · ATD = the model\\'s chance he scores · H2H = his own PPR vs this opponent, ▲ / ▼ vs his norm · SCH = the defense\\'s style edge for his slot','lens chips re-rank every column at once; the data-set select (2024 · 2025 · 2026 · combined · adjusted · μ) drives TD, Ψ and META']},
""",1)
open(T,'w',encoding='utf-8').write(s)
print('v16 META patched')
