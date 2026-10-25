"""v44 — META v2 (F2 Matchups): the boards compiled. Every board that ranks this week's players — TD Grid, Player Board (Ψ),
H2H, TD Picks model, First TD, Weeklies signals, reliable categories, META v1, ENV, FORM, scheme, market edge — becomes a 0–100
percentile within his position; CONSENSUS = the mean across the boards he appears on (shrunk toward 50 when few boards have
him), with how many boards put him in their top 10% / top quarter. Board chips drop any board from the fold; three fold rules
(mean · top-10 count · geometric mean). Players who sit high across many boards rise; one loud board cannot carry a player
alone. META v1 stays as is. Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function metaV2(' in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

rep("   {id:'metaprop',nfl:true,label:'METAPROP',desc:",
    "   {id:'metav2',nfl:true,label:'META v2',desc:'the boards compiled: every board that ranks this week\\'s players (TD Grid, Player Board, H2H, TD Picks, First TD, Weeklies, categories, META, ENV, FORM, scheme, market) as a percentile within his position, folded into one CONSENSUS score with how many boards put him in their top 10% \\u2014 the players high everywhere rise',c:'test',sub:'metav2'},\n   {id:'metaprop',nfl:true,label:'METAPROP',desc:")
rep('<div id="test" hidden><div id="wkres" hidden></div>', '<div id="test" hidden><div id="wkres" hidden></div><div id="metav2" hidden></div>')
rep("if(it.c==='test'){['wkres','meta',", "if(it.c==='test'){['wkres','metav2','meta',")
rep("['test',metaGrid],['test',metaProp],", "['test',metaGrid],['test',metaV2],['test',metaProp],")
# expose META v1 rows
rep("    ROWS=R;HAS={meta:1,td:R.some(x=>x.td!=null),atd:R.some(x=>x.atd!=null),psi:R.some(x=>x.psi!=null),h2h:R.some(x=>x.hp!=null),sch:R.some(x=>x.sch!=null),env:R.some(x=>x.env!=null),form:R.some(x=>x.form!=null)};",
    "    ROWS=R;window.META_LAST=R;HAS={meta:1,td:R.some(x=>x.td!=null),atd:R.some(x=>x.atd!=null),psi:R.some(x=>x.psi!=null),h2h:R.some(x=>x.hp!=null),sch:R.some(x=>x.sch!=null),env:R.some(x=>x.env!=null),form:R.some(x=>x.form!=null)};")

view = r'''
/* ---------------- v44: META v2 — the boards compiled ---------------- */
const MV_B=[
  ['td','TD','TD Grid: touchdowns the opponent allows to his slot · rank, 1 = the most',true],
  ['psi','Ψ','Player Board: the opponent\'s mean rank across every stat of his slot · 1 = softest',true],
  ['h2h','H2H','H2H Board: his PPR in past meetings with this opponent vs his norm (discounted under three meetings)',false],
  ['tdp','TDP','TD Picks: the anytime-TD model\'s chance he scores',false],
  ['ftd','1st','First TD: the model\'s chance he scores the game\'s first touchdown',false],
  ['wk','WKL','Weeklies: his lift-weighted score across the eight core signals he carries into the game',false],
  ['cat','CAT','Category Grid: how many reliable (trust / lean) categories he carries in',false],
  ['meta','META','META v1: Ψ + FORM + ENV, the backtested recipe',false],
  ['env','ENV','his team\'s implied points from the line',false],
  ['form','FORM','opportunities over his last two games vs his season rate',false],
  ['sch','SCH','scheme edge: what the opponent\'s defensive style gives his slot vs league, plus its missing men',false],
  ['mkt','MKT','market: the TD Picks model\'s edge over the best posted anytime-TD price',false]];
function metaV2(root='#metav2',px='mv'){
  const $$=k=>$('#'+px+k),live=new Set(TD_SLOTS),on=new Set(MV_B.map(b=>b[0]));let method='avg';
  $(root).innerHTML=`<div class="controls">
    <span class="chips" id="${px}B" title="the boards in the fold — click to drop or restore one">${MV_B.map(b=>`<button data-b="${b[0]}" class="on" title="${esc(b[2])}">${b[1]}</button>`).join('')}</span>
    <select id="${px}M" title="how the boards fold into CONSENSUS"><option value="avg">mean percentile</option><option value="top">boards in the top 10%</option><option value="geo">geometric mean (one weak board hurts)</option></select>
    <span class="chips" id="${px}Slots" title="which depth slots the board covers"><button data-s="">all</button>${TD_SLOTS.map(s=>`<button data-s="${s}" class="on">${s}</button>`).join('')}</span>
    <select id="${px}Inj"><option value="x" selected>hide OUT</option><option value="">incl. OUT</option></select>
    <input id="${px}Q" placeholder="search player..." size="15">
    <span class="note">every board that ranks this week's players, compiled. Each cell is his <b>percentile within his position on that board</b> (100 = the best spot of anyone at his position); <b>CONS</b> folds them &middot; <b>T10</b> = how many boards put him in their top 10%, <b>T25</b> their top quarter &middot; hover a cell for the raw number, a CONS cell for every board</span>
  </div>
  <div class="mlead" id="${px}Lead" data-mg="1"></div>
  <div class="panel"><h3>the boards compiled <span class="gl" id="${px}GALL"></span> <span class="f" id="${px}NALL"></span></h3><div id="${px}BALL" class="tscroll"></div></div>`;
  const sort={ALL:{k:'cons',a:false}};
  const pct=arr=>{const s=arr.filter(v=>v!=null).sort((a,b)=>a-b),n=s.length;const lb=v=>{let lo=0,hi=n;while(lo<hi){const m=(lo+hi)>>1;if(s[m]<v)lo=m+1;else hi=m}return lo};const ub=v=>{let lo=0,hi=n;while(lo<hi){const m=(lo+hi)>>1;if(s[m]<=v)lo=m+1;else hi=m}return lo};return v=>v==null||!n?null:(lb(v)+(ub(v)-lb(v))/2)/n};
  const eq=p=>1+(1-p)*(NT-1);
  let ROWS=[],HAS={};
  function build(){
    const wk=G.week,D=J.dvp.combined||J.dvp[Object.keys(J.dvp)[0]]||{};
    const TP=((J.tdpicks||{}).week===wk?(J.tdpicks.picks||[]):[]),FT=((J.firstTd||{}).week===wk?(J.firstTd.board||[]):[]);
    const M1={};(window.META_LAST||[]).forEach(x=>M1[x.u.player+'|'+x.u.team]=x);
    let WA={},TR=null;try{const SG=wkSigs();TR=wkTrust(x=>true,SG,'card38');const ok=new Set(TR.sig.filter(z=>z.kind==='pos'&&(z.tier==='trust'||z.tier==='lean')).map(z=>z.id));
      wkAhead(u=>true,TR,wk).forEach(x=>{WA[x.name+'|'+x.team]={score:x.score,cs:x.cs,cat:SG.filter(z=>ok.has(z.id)&&z.f(x)).length,on:x.on}})}catch(e){}
    const R=UNIVERSE.filter(u=>TPOS.includes(u.pos)&&u.grp).map(u=>{
      const oppRaw=(J.sched26[u.team]||[])[wk-1]||'',opp=oppRaw&&oppRaw!=='BYE'?oppRaw.replace('@',''):'';const d=opp&&D[opp]?D[opp]:null;
      const tdc=(LABDEF[u.pos].stats(u.grp)||[]).filter(c=>/TD/.test(c)),tdcs=tdc.length>1?tdc.filter(c=>c!=='P TD'):tdc;
      const td=d?(tdcs.map(c=>d.stats[c]?d.stats[c].rank:null).filter(v=>v!=null).reduce((a,b,i,arr)=>a+b/arr.length,0)||null):null;
      const psi=d&&d.comps&&d.comps[u.grp]!=null?d.comps[u.grp]:null;
      const L=PLOGS[u.ln||u.player]||[],vs=opp?L.filter(l=>l[LOG.opp]===opp):[],mf=(a,f)=>a.length?a.reduce((t,l)=>t+f(l),0)/a.length:null;
      const hp=mf(vs,l=>l[LOG.fppr]),hb=mf(L,l=>l[LOG.fppr]),h2h=hp==null||hb==null?null:(hp-hb)*Math.min(vs.length,3)/3;
      const tp=TP.find(r=>r.n===u.player&&r.t===u.team)||TP.find(r=>r.n===u.player),ft=FT.find(r=>r.player===u.player&&r.team===u.team)||FT.find(r=>r.player===u.player);
      const m1=M1[u.player+'|'+u.team],wa=WA[u.player+'|'+u.team];
      let e=null,lift=0;if(opp){try{e=schemeEdge(opp,u.grp)}catch(_){}try{lift=(injLift(opp)[u.grp]||{}).pct||0}catch(_){}}
      const raw={td,psi,h2h,tdp:tp&&tp.p!=null?+tp.p:null,ftd:ft&&ft.p_first!=null?+ft.p_first:null,wk:wa?wa.score:null,cat:wa?wa.cat:null,meta:m1&&m1.meta!=null?m1.meta:null,
        env:m1&&m1.env!=null?m1.env:null,form:m1&&m1.form!=null?m1.form:null,sch:e?(e.idx-100)+lift*.6:null,mkt:tp&&tp.ev!=null&&tp.price!=null?+tp.ev:null};
      return {u,pos:u.pos,oppRaw,opp,raw,tp,ft,wa,n:vs.length,hp,pool:TD_SLOTS.includes(u.dslot||u.slot)&&!!opp&&u.inj!=='-1'}});
    /* percentiles within position from this week's pool — a filter or a search never moves a score */
    const P={};TPOS.forEach(p=>{const Q=R.filter(x=>x.pool&&x.pos===p);P[p]={};MV_B.forEach(([k,,,lo])=>{P[p][k]=pct(Q.map(x=>x.raw[k]==null?null:(lo?-x.raw[k]:x.raw[k])))})});
    R.forEach(x=>{x.pc={};MV_B.forEach(([k,,,lo])=>{const v=x.raw[k];x.pc[k]=v==null?null:P[x.pos][k](lo?-v:v)})});
    ROWS=R;HAS={};MV_B.forEach(([k])=>HAS[k]=R.some(x=>x.pc[k]!=null));
    $$('B').querySelectorAll('button').forEach(b=>b.hidden=!HAS[b.dataset.b]);fold()}
  function fold(){const ks=MV_B.map(b=>b[0]).filter(k=>on.has(k)&&HAS[k]);
    ROWS.forEach(x=>{const v=ks.map(k=>x.pc[k]).filter(p=>p!=null);x.nb=v.length;x.t10=v.filter(p=>p>=.9).length;x.t25=v.filter(p=>p>=.75).length;x.low=v.length?Math.min(...v):null;
      if(!v.length||!x.opp){x.cons=null;return}const cov=v.length/Math.max(ks.length,1);
      const mean=v.reduce((a,b)=>a+b,0)/v.length,geo=Math.exp(v.reduce((a,b)=>a+Math.log(Math.max(b,.02)),0)/v.length);
      x.cons=method==='top'?100*(x.t10+.5*(x.t25-x.t10))/Math.max(ks.length,1)+mean*.01:50+(100*(method==='geo'?geo:mean)-50)*(.5+.5*cov)})}
  const keep=x=>{const q=$$('Q').value.toLowerCase();return inU(x.u)&&(!live.size||live.has(x.u.dslot||x.u.slot))&&($$('Inj').value!=='x'||x.u.inj!=='-1')&&(!q||x.u.player.toLowerCase().includes(q))};
  const LBL=Object.fromEntries(MV_B.map(b=>[b[0],b[1]])),TIP=Object.fromEntries(MV_B.map(b=>[b[0],b[2]]));
  const rawTxt=(k,x)=>{const v=x.raw[k];if(v==null)return '—';switch(k){case 'td':case 'psi':return `rank ${Math.round(v)} of ${NT}`;case 'h2h':return `${(x.hp||0).toFixed(1)} PPR vs them over ${x.n} game${x.n===1?'':'s'} (${v>=0?'+':''}${v.toFixed(1)} vs his norm, discounted)`;
    case 'tdp':return `${Math.round(100*v)}% to score${x.tp&&x.tp.price!=null?' · best '+mlTxt(+x.tp.price)+(x.tp.book?' ('+x.tp.book+')':''):''}`;case 'ftd':return `${(100*v).toFixed(1)}% first TD${x.ft&&x.ft.fair!=null?' · fair '+mlTxt(+x.ft.fair):''}`;
    case 'wk':return `${v.toFixed(2)} lift score · ${x.wa.cs} of 8 core signals${x.wa.on&&x.wa.on.length?' · '+x.wa.on.map(z=>z.lbl).join(', '):''}`;case 'cat':return `${v} reliable categor${v===1?'y':'ies'}`;case 'meta':return `META ${Math.round(v)}`;
    case 'env':return `${v.toFixed(1)} implied points`;case 'form':return `${v>=0?'+':''}${Math.round(100*v)}% opps last 2 vs season`;case 'sch':return `${v>=0?'+':''}${v.toFixed(0)}% vs league`;case 'mkt':return `EV ${v>=0?'+':''}${(+v).toFixed(1)}% at ${mlTxt(+x.tp.price)}`;default:return String(v)}};
  const why=x=>[`CONSENSUS ${x.cons==null?'—':Math.round(x.cons)} · ${x.nb} board${x.nb===1?'':'s'} · top 10% on ${x.t10}, top quarter on ${x.t25}${x.low!=null?' · weakest board '+Math.round(100*x.low):''}`].concat(MV_B.filter(b=>on.has(b[0])&&HAS[b[0]]).map(([k,l])=>`${l}: ${x.pc[k]==null?'—':Math.round(100*x.pc[k])} · ${rawTxt(k,x)}`)).join('\n');
  const sv=(x,k)=>k==='cons'?x.cons:k==='t10'?x.t10:k==='t25'?x.t25:k==='nb'?x.nb:k==='player'?x.u.player:k==='opp'?(x.opp||null):k==='pos'?TPOS.indexOf(x.pos):x.pc[k];
  const cmp=(k,asc)=>(a,b)=>{const x=sv(a,k),y=sv(b,k);if(x==null||y==null){if(x==null&&y==null)return (b.cons??-1)-(a.cons??-1);return x==null?1:-1}return (x<y?-1:x>y?1:0)*(asc?1:-1)||(b.cons??-1)-(a.cons??-1)};
  const cell=(k,x)=>{const p=x.pc[k];return p==null?'<td class="op"><span class="dim">·</span></td>':`<td class="op" title="${esc(LBL[k]+': '+rawTxt(k,x)+' · '+Math.round(100*p)+'th pct of '+x.pos+'s')}"><span class="badge" style="${gradeStyle(eq(p))}">${Math.round(100*p)}</span></td>`};
  function col(p){const st=sort[p],ks=MV_B.map(b=>b[0]).filter(k=>on.has(k)&&HAS[k]);
    const R=ROWS.filter(x=>(p==='ALL'||x.pos===p)&&keep(x)).sort(cmp(st.k,st.a));
    $$('N'+p).textContent=R.length+(R.length===1?' player':' players');$$('G'+p).textContent=`ranked by ${st.k==='cons'?'CONS':st.k==='t10'?'T10':st.k==='t25'?'T25':st.k==='nb'?'boards':LBL[st.k]||st.k}`;
    const th=(k,l,tip,cls)=>`<th class="${cls||''}" data-k="${k}" title="${esc(tip||'')}">${l}${st.k===k?(st.a?' ▲':' ▼'):''}</th>`;
    const wname=14,wpos=5,wopp=8,wc=6,wt=4,wn=((100-wname-wpos-wopp-wc-2*wt)/Math.max(ks.length,1)).toFixed(2);
    $$('B'+p).innerHTML=`<table class="lgt mvt"><colgroup><col style="width:${wname}%">${p==='ALL'?`<col style="width:${wpos}%">`:''}<col style="width:${wopp}%"><col style="width:${wc}%"><col style="width:${wt}%"><col style="width:${wt}%">${ks.map(()=>`<col style="width:${wn}%">`).join('')}</colgroup><thead>
      <tr class="hd">${th('player','Player')}${p==='ALL'?th('pos',''):''}${th('opp','Opp',"this week's opponent")}${th('cons','CONS','the boards folded · 0–100 · hover for every board','md gs')}${th('t10','T10','boards where he is in the top 10% of his position','md')}${th('t25','T25','boards where he is in the top quarter of his position','md')}${ks.map(k=>th(k,LBL[k],TIP[k]+' · percentile within his position','op')).join('')}</tr></thead><tbody>
      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.u.player)}" title="${esc(x.u.player)} · ${esc(x.u.dslot||x.u.slot)} · ${esc(x.u.team)}">${esc(pshort(x.u.player))}${x.u.inj==='0'?' <span class="inj0">Q</span>':x.u.inj==='-1'?' <span class="injm1">OUT</span>':''}</td>
        ${p==='ALL'?`<td>${posIcon(x.pos,10,x.u.dslot||x.u.slot)}</td>`:''}<td>${x.opp?oppcell(x.oppRaw):'<span class="dim">bye</span>'}</td>
        ${x.cons==null?'<td class="md gs"><span class="dim">·</span></td>':`<td class="md gs" title="${esc(why(x))}"><span class="badge" style="${gradeStyle(eq(Math.max(0,Math.min(1,x.cons/100))))}">${Math.round(x.cons)}</span></td>`}
        <td class="md" title="top 10% on ${x.t10} of ${x.nb} boards"><b style="color:${x.t10>=4?'#00c853':x.t10>=2?'#8bc34a':'var(--dim)'}">${x.t10||''}</b></td><td class="md" title="top quarter on ${x.t25} of ${x.nb} boards">${x.t25||''}</td>
        ${ks.map(k=>cell(k,x)).join('')}</tr>`).join('')||`<tr><td colspan="${ks.length+6}" class="dim">nothing matches</td></tr>`}</tbody></table>`;
    $$('B'+p).querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=h.dataset.k;if(st.k===k)st.a=!st.a;else{st.k=k;st.a=k==='player'||k==='opp'||k==='pos'}col(p)});
    tWire($$('B'+p))}
  function lead(){const R=ROWS.filter(x=>keep(x)&&x.cons!=null);const B=(r,s)=>`<span class="badge" style="${s}">${r}</span>`;
    const nm=x=>`<span class="plink" data-p="${esc(x.u.player)}" title="${esc(why(x))}">${esc(pshort(x.u.player))}</span>`;
    const line=x=>`<div class="mlr">${posIcon(x.pos,10,x.u.dslot||x.u.slot)} ${nm(x)}<span class="mini">${x.opp?oppcell(x.oppRaw):''}</span>${B(Math.round(x.cons),gradeStyle(eq(Math.max(0,Math.min(1,x.cons/100)))))}<span class="mini" title="boards in the top 10% / top quarter">${x.t10}·${x.t25}</span></div>`;
    const cards=[['everywhere at once · CONS','g',R.slice().sort(cmp('cons',false))]].concat(TPOS.map(p=>[p,'',R.filter(x=>x.pos===p).sort(cmp('cons',false))])).concat([['most top-10 boards','',R.slice().sort((a,b)=>b.t10-a.t10||(b.cons??0)-(a.cons??0))],['avoid · lowest CONS','r',R.slice().sort(cmp('cons',true))]]);
    $$('Lead').innerHTML=cards.map(([t,tone,L])=>thSeq(`<div class="mlc ${tone}"><div class="mlh">${t}</div>${L.slice(0,3).map(line).join('')||'<div class="mini dim">nothing on the board</div>'}</div>`,[()=>({title:t,sub:`week ${G.week} · ${L.length} players`,html:`<div class="mlc ${tone}" style="max-width:560px">${L.slice(0,60).map(line).join('')}</div>`})])).join('');tWire($$('Lead'))}
  const cols=()=>{col('ALL');lead()};const all=()=>{build();cols()};
  $$('B').querySelectorAll('button').forEach(b=>b.onclick=()=>{const k=b.dataset.b;on.has(k)?on.delete(k):on.add(k);if(!on.size)on.add(k);b.classList.toggle('on',on.has(k));fold();cols()});
  $$('M').onchange=()=>{method=$$('M').value;fold();cols()};$$('Inj').onchange=cols;$$('Q').oninput=cols;
  $$('Slots').querySelectorAll('button').forEach(b=>b.onclick=()=>{const v=b.dataset.s;if(!v)live.clear();else live.has(v)?live.delete(v):live.add(v);$$('Slots').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.s?live.has(x.dataset.s):live.size===0));cols()});
  all();RR.push(all);
}
'''
rep("/* v43 results */", "/* v44 */.mvt{min-width:1180px}.mvt th,.mvt td{font-size:11px}\n/* v43 results */")
rep("/* ---------------- METAPROP (F6 TEST, v23) — META for player props ----------------", view + "/* ---------------- METAPROP (F6 TEST, v23) — META for player props ----------------")
rep(" meta:{what:'Every board at once.',", " metav2:{what:'The boards compiled.',how:['every board that ranks this week\\'s players becomes a percentile within his position (100 = the best spot of anyone at his position): TD Grid, Player Board Ψ, H2H, TD Picks, First TD, Weeklies, categories, META, ENV, FORM, scheme, market edge','CONS folds them (mean · top-10 count · geometric) and shrinks toward 50 when few boards have him · T10 / T25 = how many boards put him in their top 10% / top quarter — the players high everywhere rise, one loud board cannot carry a man alone','board chips drop a board from the fold; hover a CONS cell for every board, a board cell for the raw number']},\n meta:{what:'Every board at once.',")
s = s.replace("Object.assign(NOTES,{v43:", "Object.assign(NOTES,{v44:['v44','META v2 on F2 Matchups: every board that ranks the week\\'s players compiled into one CONSENSUS percentile per position, with how many boards put him in their top 10% \\u2014 board chips, three fold rules, META v1 untouched']});\nObject.assign(NOTES,{v43:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v44 applied', len(s))
