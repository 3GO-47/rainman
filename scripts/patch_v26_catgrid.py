"""v26 — F6 TEST > Category Grid: the Weeklies categories as one composite board, in the TD Grid's five columns.

Every recorded week together. The categories that beat the field most consistently across the weeks logged so far are the
columns (chips add or drop one); every player on the slate of the week picked up top is a row. A cell is that player's own record in the
category over the recorded weeks — scored in k of the n weeks he carried it — shaded green when he carries it into the next
game too. CAT = consistent categories he carries in, REC = scored in k of n weeks carrying any of them, TD % = TD Picks /
the anytime-TD model, FADE = consistent fades he carries. The slate / game / team / position filters at the top apply.
Leader cards: each category's record (week pips) and its best carriers; a category name opens the Weeklies pane.

Usage: python scripts/patch_v26_catgrid.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v26: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# ---------------- registration
rep(r'''c:'test',sub:'weeklies'},''', r'''c:'test',sub:'weeklies'},
   {id:'wkgrid',label:'Category Grid',desc:'the Weeklies categories as one composite board: the categories that beat the field most consistently across every recorded week as the columns, every player on the slate of the week picked up top as a row — his own record in each, what he carries into that week, his TD chance — in the TD Grid\'s five columns',c:'test',sub:'wkgrid'},''')
rep(r'''<div id="weeklies" hidden></div>''', r'''<div id="weeklies" hidden></div><div id="wkgrid" hidden></div>''')
rep("'weeklies','tdpicks'", "'weeklies','wkgrid','tdpicks'")
rep(r'''['test',weeklies],''', r'''['test',weeklies],['test',wkGrid],''')
rep(r''' metaprop:{what:'META for player props.',''', r''' wkgrid:{what:'The Weeklies categories, every recorded week at once.',how:['chips = the categories that beat the field most consistently across the recorded weeks before the week picked (click to add or drop one) · CARRIES = one square per category in chip order = he carries it into the week picked up top','CAT = consistent categories he carries in · REC = scored in k of n weeks carrying any of them · TD % = the TD Picks chance · red square = a consistent fade he carries · hover a square for his own record in it','the week, slate, game, team and position filters at the top all apply (consistency counts only the recorded weeks before the week picked); click a category for its pane, a name for his card']},
 metaprop:{what:'META for player props.',''')
rep(r'''const BOOT=[''', r'''Object.assign(NOTES,{wkgrid:['v26','new tab: the Weeklies categories as one composite board — the most consistent categories across every recorded week as columns, every player on the week\'s slate as a row with his own record in each, CAT / REC / TD % and a square per category, a best-picks card, the TD Grid\'s five columns; follows the week, slate, game, team and position filters up top']});
const BOOT=[''')
# the Weeklies pane, callable from the grid
rep(r'''  el.addEventListener('click',e=>{const t=e.target.closest('[data-sig],[data-stack]');if(!t||!el.contains(t))return;''',
    r'''  window.wkSigPopG=id=>wkSigPop(id);
  el.addEventListener('click',e=>{const t=e.target.closest('[data-sig],[data-stack]');if(!t||!el.contains(t))return;''')

# ---------------- CSS
rep(r'''.wksig{cursor:pointer;''', r'''.lgrid.wg td.wgc{text-align:center;font:600 10.5px var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}.lgrid.wg td.wgc.now{background:color-mix(in srgb,var(--green) 20%,transparent);box-shadow:inset 0 0 0 1px #00c85355}
.lgrid.wg td.wgc .h{color:var(--green)}.lgrid.wg td.wgc .z{color:var(--red)}.lgrid.wg td.wgc .m{color:var(--txt)}.lgrid.wg td.wrec{text-align:right;font:600 10.5px var(--mono);white-space:nowrap}.lgrid.wg td.wfd{text-align:center;font:700 10.5px var(--mono);color:var(--red)}
.lgrid.wg th.wgh{letter-spacing:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.mlc .wgs{font-size:10.5px;color:var(--dim);margin:-2px 0 4px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}.mlc .wgs .pip{margin:0}
#wgCat button i{font-style:normal;font:600 9.5px var(--mono);color:var(--dim2);margin-left:4px}#wgCat button.on i{color:inherit;opacity:.8}
.wksig{cursor:pointer;''')

# ---------------- CSS for the Weeklies forward view
rep(r'''.wksig{cursor:pointer;''', r'''.wgpk{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:8px}.wgpc{border:1px solid var(--edge);border-top:2px solid #00c85366;border-radius:8px;padding:6px 9px;background:var(--panel);min-width:0}
.wgpc .h{display:flex;align-items:center;gap:6px;font-size:12px;min-width:0}.wgpc .h .rk{font:700 10px var(--mono);color:var(--dim2);min-width:14px}.wgpc .h .plink{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}.wgpc .h .mini{margin-left:auto;white-space:nowrap}
.wgpc .t{display:flex;flex-wrap:wrap;gap:4px;margin:5px 0 4px}.wgpc .t i{font-style:normal;font:600 9.5px var(--mono);color:var(--green);border:1px solid #00c85355;border-radius:3px;padding:0 4px}
.wgpc .m{display:flex;gap:12px;font-size:10.5px;color:var(--dim)}.wgpc .m b{color:var(--txt);font-family:var(--mono)}#wkW button.nx{border-style:dashed}.pip.l{background:var(--red)}
.lgrid.wg td.wsq{white-space:nowrap;overflow:hidden}.wq{display:inline-block;width:7px;height:11px;margin:0 1px 0 0;border-radius:2px;background:#232a33;vertical-align:middle}.wq.h{box-shadow:inset 0 0 0 1px #00c853aa}.wq.n{background:var(--green)}.wq.f{background:var(--red);margin-left:3px}#weeklies [data-nx]{display:none!important}
.wksig{cursor:pointer;''')

# ---------------- shared: the composite (used by the Category Grid and the Weeklies forward view)
rep(r'''
/* ---------------- Weeklies (F6 TEST) — the touchdown lookback ----------------''', r'''
/* ---------------- Category Grid (F6 TEST, v26) — the Weeklies categories, every recorded week at once ----------------
   wgData(slots, window, picked categories, week W0): how consistently each Weeklies category beat the field over the
   recorded weeks before W0 (week by week), the most consistent ones (or the picked ones), and every player on week W0's
   slate with his own record in each, what he carries into W0, his TD chance (tdP) and the consistent fades he carries.
   The Category Grid shows it for the week picked up top; the Weeklies tab's 'wk N ▸' chips show it for the week ahead. */
const WG_AB={rate:'TD ½',hot:'2 of 3',career:'career ½',last:'last gm',share:'TD shr',vol:'18+ tch',tgt:'8+ tgt',lead:'lead',snap:'70% snp',tsh:'20% tsh',imp:'imp 24',imp27:'imp 27',fav:'fav',home:'home',slothot:'hot D',td10:'TD D',ppr10:'fant D',h2htd:'H2H TD',shareimp:'shr+imp',rateimp:'½+imp',leadimp:'lead+imp',combo1:'TD D+imp',dog7:'dog 7+',deep:'deep',tdbot:'tough D',h2hno:'H2H 0',dry:'no TD'};
const wgTpc=v=>v>=.5?'var(--green)':v>=.4?'#7dd87d':v>=.3?'var(--amber)':v>=.2?'#6db3e8':'var(--dim)';
const wgTp=x=>x.tp?x.tp.p:null,wgRec=x=>x.hn?x.hk/x.hn:null;
const wgRank=(a,b)=>(b.qw?b.bw/b.qw:-1)-(a.qw?a.bw/a.qw:-1)||b.bw-a.bw||(b.lift||0)-(a.lift||0);
function wgData(live,win,pick,W0){
  const SG=wkSigs(),keep=x=>slotOK(live,x.slot==='WR4+'?'WR4':x.slot)&&inP(x.pos),key=[...live].sort().join(',')+'|'+[...(G.pos||[])].sort().join(',');
  const TR=wkTrust(keep,SG,key),F=wkFeat(LAST_SE),Wk=F.weeks.filter(w=>w<W0);let rows,base,lbl;
  if(!Wk.length)win='all';
  if(win==='all'){rows=TR.sig.map(t=>({s:SG.find(z=>z.id===t.id),n:t.n,k:t.k,hr:t.hr,lift:t.lift,bw:t.bw,qw:t.qw,pips:null})).filter(r=>r.s);base=TR.base;lbl=`every season ${ALL_SE[0]}–${String(LAST_SE).slice(2)}`}
  else{const AL=Wk.map(w=>wkStats(F,w,keep,SG));let tn=0,tk=0;AL.forEach(a=>{tn+=a.P.length;tk+=a.sc.length});base=tn?tk/tn:null;
    rows=SG.map(sg=>{let n=0,k=0,qw=0,bw=0;const pips=AL.map(a=>{const x=a.sig.find(y=>y.id===sg.id);n+=x.n;k+=x.k;if(x.n<a.minN||x.hr==null)return 0;qw++;const won=sg.kind==='pos'?wkR(x.lift)>=1.1:wkR(x.lift)<=.9;if(won)bw++;return won?1:-1});
      return {s:sg,n,k,hr:n?k/n:null,lift:n&&base?(k/n)/base:null,bw,qw,pips}});
    lbl=Wk.length===1?`${LAST_SE} week ${Wk[0]}`:`${LAST_SE} weeks ${Wk[0]}–${Wk[Wk.length-1]}`}
  const need=win==='all'?3:Math.max(2,Math.ceil(Wk.length*.6));
  const POSR=rows.filter(r=>r.s.kind==='pos').sort(wgRank),fades=rows.filter(r=>r.s.kind==='neg'&&r.qw>=need&&r.bw/r.qw>=.6&&wkR(r.lift)<=.9).sort(wgRank);
  let pk=pick&&pick.length?pick.filter(id=>POSR.some(r=>r.s.id===id)):[];if(!pk.length)pk=POSR.filter(r=>r.qw>=need).slice(0,6).map(r=>r.s.id);if(!pk.length)pk=POSR.slice(0,6).map(r=>r.s.id);
  const PK=pk.map(id=>rows.find(r=>r.s.id===id)).filter(Boolean);
  const AH=wkAhead(u=>slotOK(live,u.dslot||u.slot)&&inP(u.pos),TR,W0);
  const hist={};F.rows.forEach(x=>{if(Wk.includes(x.w))(hist[x.name]=hist[x.name]||[]).push(x)});
  const R=AH.map(x=>{const H=hist[x.u.ln||x.name]||hist[x.name]||[],cells={};let cn=0,an=0,ak=0;
    PK.forEach(r=>{const now=!!r.s.f(x),hs=H.filter(h=>r.s.f(h));cells[r.s.id]={now,n:hs.length,k:hs.filter(h=>h.td>0).length};if(now)cn++});
    H.forEach(h=>{if(PK.some(r=>r.s.f(h))){an++;if(h.td>0)ak++}});
    return Object.assign(x,{cells,cat:cn,hn:an,hk:ak,gp:H.length,fd:fades.filter(r=>r.s.f(x)),tp:tdP(x.name,x.team,W0)})});
  const best=R.filter(x=>x.cat>0).sort((a,b)=>b.cat-a.cat||(wgTp(b)??-1)-(wgTp(a)??-1)||(wgRec(b)??-1)-(wgRec(a)??-1));
  return {rows,base,lbl,POSR,fades,PK,pick:pk,W0,R,Wk,need,win,best}}
const wgName=x=>`<span class="plink" data-p="${esc(x.name)}" title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${esc(pshort(x.name))}${x.done?(x.done.td>0?' <b style="color:var(--green)">✓</b>':' <b style="color:var(--red)">✗</b>'):''}</span>`;
function wgCatCard(r,tone,L){const pip=v=>`<i class="pip ${v>0?'w':v<0?'l':'o'}"></i>`;
  return `<div class="mlc ${tone}"><div class="mlh"><span class="wksig" data-sig="${r.s.id}" title="click for the Weeklies pane">${esc(r.s.lbl)}</span></div>
    <div class="wgs">${r.pips?r.pips.map(pip).join(''):''}<span>beat the field <b>${r.bw}/${r.qw}</b> · ${wkX(r.lift)} · ${r.k}/${r.n} scored</span></div>
    ${L.slice(0,3).map(x=>`<div class="mlr"><span style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</span>${wgName(x)}<span class="mini">${x.opp?oppcell(x.raw):''}</span>${x.tp?`<b style="color:${wgTpc(x.tp.p)}">${Math.round(100*x.tp.p)}%</b>`:'<span class="dim">·</span>'}</div>`).join('')||'<div class="mini dim">nobody carries it in</div>'}</div>`}
function wgBestCard(L,W0){return `<div class="mlc g"><div class="mlh">best picks · week ${W0}</div><div class="wgs"><span>most consistent categories carried in, then TD chance</span></div>
    ${L.slice(0,5).map(x=>`<div class="mlr"><span style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</span>${wgName(x)}<span class="mini">${x.opp?oppcell(x.raw):''}</span><span class="mv"><b title="consistent categories he carries in">${x.cat}</b> ${x.tp?`<b style="color:${wgTpc(x.tp.p)}">${Math.round(100*x.tp.p)}%</b>`:'<span class="dim">·</span>'}</span></div>`).join('')||'<div class="mini dim">nobody carries one in</div>'}</div>`}
function wgPickCards(L,PK){return `<div class="wgpk">${L.map((x,i)=>`<div class="wgpc"><div class="h"><span class="rk">${i+1}</span><span style="color:${POSC[x.pos]}">${posIcon(x.pos,11)}</span>${wgName(x)}<span class="mini">${x.opp?oppcell(x.raw):'bye'}</span></div>
    <div class="t">${PK.filter(r=>x.cells[r.s.id]&&x.cells[r.s.id].now).map(r=>`<i title="${esc(r.s.lbl)}">${esc(WG_AB[r.s.id]||r.s.lbl)}</i>`).join('')}</div>
    <div class="m"><span><b>${x.cat}</b> carried</span><span>TD <b style="color:${x.tp?wgTpc(x.tp.p):'var(--dim)'}">${x.tp?Math.round(100*x.tp.p)+'%':'—'}</b></span><span title="scored in k of the n recorded games he carried any of them">REC <b>${x.hn?x.hk+'/'+x.hn:'—'}</b></span>${x.fd.length?`<span title="${esc(x.fd.map(r=>r.s.lbl).join(' · '))}" style="color:var(--red)">fade ${x.fd.length}</span>`:''}</div></div>`).join('')}</div>`}
function wkGrid(root='#wkgrid',px='wg'){
  const el=$(root);if(!el)return;
  const live=new Set(['QB1','RB1','RB2','WR1','WR2','WR3','TE1']),$$=k=>$('#'+px+k);
  let win='cur',pick=null,CS=null;const sort={};['ALL'].concat(TPOS).forEach(p=>sort[p]={k:'cat',a:false});
  el.innerHTML=`<div class="controls">
    <span class="chips" id="${px}Cat" title="the categories on the board, most consistent first — click to add or drop one (up to 8) · the number = weeks it beat the field / weeks with a usable sample"></span>
    ${slotChipsHTML(px+'Slots',live)}
    <select id="${px}Win" title="which weeks decide how consistent a category is"><option value="cur" selected>consistency: every recorded week of ${LAST_SE} before the week picked</option><option value="all">consistency: every season ${ALL_SE[0]}–${String(LAST_SE).slice(2)}</option></select>
    <select id="${px}Only"><option value="1" selected>players carrying a category</option><option value="">everyone on the slate</option></select>
    <input id="${px}Q" placeholder="search player..." size="15">
    <span class="note">every recorded week at once, for the week picked up top. Columns = the Weeklies categories that beat the field most consistently across the recorded weeks before it, most consistent first &middot; a cell = that player's own record in the category: scored in <b>k</b> of the <b>n</b> weeks he carried it &middot; <b style="color:var(--green)">green</b> = he carries it into the week picked &middot; <b>CAT</b> = consistent categories he carries in &middot; <b>REC</b> = scored in k of n weeks carrying any of them &middot; <b>TD %</b> = the TD Picks chance for that week &middot; <b>FADE</b> = consistent fades he carries &middot; ✓ / ✗ once his game is logged &middot; the week, slate, game, team and position filters at the top apply &middot; click a category for its pane, a name for his card</span>
  </div>
  <div class="mlead" id="${px}Lead" data-mg="1"></div>
  <div class="lgrid td5 wide full meta wg">${['ALL'].concat(TPOS).map(p=>`<section class="lgcol"><h3>${p==='ALL'?'◉ all':posIcon(p,12)+' '+p} <span class="gl" id="${px}G${p}"></span> <span class="f" id="${px}N${p}"></span></h3><div id="${px}B${p}"></div></section>`).join('')}</div>`;
  function build(){
    CS=wgData(live,win,pick,G.week);pick=CS.pick;
    $$('Cat').innerHTML=CS.POSR.map(r=>`<button data-c="${r.s.id}" class="${pick.includes(r.s.id)?'on':''}" title="${esc(`${r.s.long||r.s.lbl} · beat the field ${r.bw} of ${r.qw} weeks · ${wkX(r.lift)} · ${r.k} of ${r.n} scored · ${CS.lbl}`)}">${WG_AB[r.s.id]||r.s.lbl}<i>${r.bw}/${r.qw}</i></button>`).join('');
    $$('Cat').querySelectorAll('button').forEach(b=>b.onclick=()=>{const id=b.dataset.c,i=pick.indexOf(id);if(i>=0){if(pick.length>1)pick.splice(i,1)}else if(pick.length<8)pick.push(id);all()})}
  const keepR=x=>{const q=$$('Q').value.toLowerCase();return inU(x.u)&&inP(x.pos)&&(!$$('Only').value||x.cat>0||x.hn>=2)&&(!q||x.name.toLowerCase().includes(q))};
  const sv=(x,k)=>k==='cat'?x.cat:k==='tp'?wgTp(x):k==='rec'?wgRec(x):k==='fd'?x.fd.length:k==='player'?x.name:k==='opp'?x.opp:k==='pos'?TPOS.indexOf(x.pos):k.startsWith('c:')?(c=>c?(c.now?1:0)+(c.n?c.k/c.n:0)/2+(c.n?.001:0):null)(x.cells[k.slice(2)]):null;
  const DESC=k=>!['player','opp','pos','fd'].includes(k);
  const cmp=(k,asc)=>(a,b)=>{const x=sv(a,k),y=sv(b,k);if(x==null||y==null){if(x==null&&y==null)return 0;return x==null?1:-1}
    return (x<y?-1:x>y?1:0)*(asc?1:-1)||b.cat-a.cat||(wgRec(b)??-1)-(wgRec(a)??-1)||(wgTp(b)??-1)-(wgTp(a)??-1)};
  const LB={cat:'CAT',tp:'TD %',rec:'REC',fd:'fades',player:'name',opp:'opp',pos:'pos'};
  function col(p){
    const st=sort[p],PK=CS.PK,R=CS.R.filter(x=>(p==='ALL'||x.pos===p)&&keepR(x)).sort(cmp(st.k,st.a));
    $$('N'+p).textContent=R.length+(R.length===1?' player':' players');
    $$('G'+p).textContent=`wk ${CS.W0} · by ${LB[st.k]||st.k}`;
    const th=(k,l,tip,cls)=>`<th class="${cls||''}" data-k="${k}" title="${esc(tip||'')}">${l}${st.k===k?(st.a?' ▲':' ▼'):''}</th>`;
    const W=p==='ALL'?[26,5,19,8,11,8,23]:[31,0,20,8,11,8,22];
    const sq=(x,r)=>{const c=x.cells[r.s.id];return `<i class="wq${c.now?' n':''}${c.n&&c.k/c.n>=.5?' h':''}" title="${esc(`${r.s.lbl}: ${c.now?'carries it into week '+CS.W0:'does not carry it in'} · carried it in ${c.n} of his ${x.gp} recorded games, scored in ${c.k}`)}"></i>`};
    $$('B'+p).innerHTML=`<table class="lgt"><colgroup>${W.map(w=>w?`<col style="width:${w}%">`:'').join('')}</colgroup><thead>
      <tr class="hd">${th('player','Player')}${p==='ALL'?th('pos',''):''}${th('opp','Opp',`week ${CS.W0} opponent`)}${th('cat','CAT',`consistent categories he carries into week ${CS.W0}`,'md gs')}${th('rec','REC','scored in k of the n recorded games he carried any of these categories','md')}${th('tp','TD %',`TD Picks: his chance to score in week ${CS.W0}`,'op')}${th('fd','CARRIES',`one square per category, in chip order (${PK.map(r=>WG_AB[r.s.id]||r.s.lbl).join(' · ')}) · green = carries it into week ${CS.W0} · outlined = scored in half or more of the games he carried it · red = a consistent fade he carries · sorts by fades`,'wgh')}</tr></thead><tbody>
      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.name)}" title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${esc(pshort(x.name))}${x.done?(x.done.td>0?' <b style="color:var(--green)">✓</b>':' <b style="color:var(--red)">✗</b>'):''}</td>
        ${p==='ALL'?`<td style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</td>`:''}<td>${x.opp?oppcell(x.raw):'<span class="dim">bye</span>'}</td>
        <td class="md gs" data-v="${x.cat}"><span class="badge" style="${gradeStyle(1+(1-x.cat/Math.max(1,PK.length))*(NT-1))}">${x.cat}</span></td>
        <td class="wrec" data-v="${wgRec(x)??''}" title="${esc(`scored in ${x.hk} of the ${x.hn} recorded games he carried any of these categories (${x.gp} games logged)`)}">${x.hn?`<span style="color:${x.hk/x.hn>=.5?'var(--green)':x.hk?'var(--txt)':'var(--red)'}">${x.hk}/${x.hn}</span>`:'<span class="dim">·</span>'}</td>
        <td class="op" data-v="${wgTp(x)??''}">${x.tp?`<b style="color:${wgTpc(x.tp.p)}">${Math.round(100*x.tp.p)}</b>`:'<span class="dim">·</span>'}</td>
        <td class="wsq" data-v="${x.fd.length}">${PK.map(r=>sq(x,r)).join('')}${x.fd.map(r=>`<i class="wq f" title="${esc('fade: '+r.s.lbl)}"></i>`).join('')}</td></tr>`).join('')||`<tr><td colspan="${p==='ALL'?7:6}" class="dim">nothing matches</td></tr>`}</tbody></table>`;
    $$('B'+p).querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=h.dataset.k;if(st.k===k)st.a=!st.a;else{st.k=k;st.a=!DESC(k)}col(p)});
    tWire($$('B'+p));const sec=$$('B'+p).closest('.lgcol'),h=sec&&sec.querySelector('h3');if(h)sec.style.setProperty('--h3h',h.offsetHeight+'px')}
  function lead(){
    const R=CS.R.filter(x=>inU(x.u)&&inP(x.pos)),by=r=>R.filter(x=>r.s.f(x)).sort((a,b)=>(wgTp(b)??-1)-(wgTp(a)??-1));
    $$('Lead').innerHTML=wgBestCard(CS.best.filter(x=>inU(x.u)&&inP(x.pos)),CS.W0)+CS.PK.map(r=>wgCatCard(r,'g',by(r))).join('')+CS.fades.slice(0,2).map(r=>wgCatCard(r,'r',by(r))).join('');
    tWire($$('Lead'))}
  const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead()};
  const all=()=>{build();cols()};
  el.addEventListener('click',e=>{const t=e.target.closest('[data-sig]');if(!t||!el.contains(t)||!window.wkSigPopG)return;e.preventDefault();e.stopPropagation();window.wkSigPopG(t.dataset.sig)});
  slotChipsWire(px+'Slots',live,all);$$('Win').onchange=()=>{win=$$('Win').value;pick=null;all()};$$('Only').onchange=cols;$$('Q').oninput=cols;
  all();RR.push(all);
}

/* ---------------- Weeklies (F6 TEST) — the touchdown lookback ----------------''')

# ---------------- Weeklies: 'wk N ▸' chips open the week ahead (best picks + the consistent categories); follows the week picked up top
rep(r'''  <div class="wktiles" id="wkTiles" data-mg="1"></div>
  <div class="panel" id="wkMdP" hidden>''', r'''  <div class="wktiles" id="wkTiles" data-mg="1"></div>
  <div id="wkNX" hidden></div>
  <div class="panel" id="wkMdP" hidden>''')
rep(r'''  let W=null,show='sc';const CORE7=''', r'''  let W=null,show='sc',NX=null,gw=G.week;const CORE7=''')
i0 = s.index("  function chipsW(F){const box=$('#wkW');")
i1 = s.index("render()})}", i0) + len("render()})}")
s = s[:i0] + r'''  const wkNxList=F=>{const L=new Set(),mx=F.weeks.length?Math.max(...F.weeks):0;F.pending.forEach(w=>L.add(w));if(!F.pending.length)L.add(mx+1);if(J.tdpicks&&J.tdpicks.week>mx)L.add(J.tdpicks.week);if(G.week>mx)L.add(G.week);if(NX)L.add(NX);return [...L].filter(w=>w>=1&&w<=NWK).sort((a,b)=>a-b)};
  function chipsW(F){const box=$('#wkW'),nx=S===LAST_SE?wkNxList(F):[];
    box.innerHTML=F.weeks.map(w=>`<button data-w="${w}" class="${w===W?'on':''}">wk ${w}</button>`).join('')+nx.map(w=>`<button data-n="${w}" class="nx${W==='next'&&NX===w?' on':''}" title="week ${w} ahead: the best picks and the most consistent categories carried into it${F.pending.includes(w)?' — graded as its box scores import':''}">wk ${w} ▸</button>`).join('')+(F.pending.length?`<span class="mini" style="margin-left:6px" title="a week appears once every game is logged">wk ${F.pending.join(', ')} in progress</span>`:'');
    box.querySelectorAll('button').forEach(b=>b.onclick=()=>{if(b.dataset.n){W='next';NX=+b.dataset.n}else W=+b.dataset.w;render()})}
  function wkNext(F){const box=$('#wkNX');box.hidden=false;
    const D=wgData(wkLive,'cur',null,NX),R=D.R.filter(x=>inU(x.u)&&inP(x.pos)),B=D.best.filter(x=>inU(x.u)&&inP(x.pos)),gr=R.filter(x=>x.done),gk=gr.filter(x=>x.done.td>0).length,c3=R.filter(x=>x.cat>=3).length,top=D.PK[0];
    $('#wkTiles').innerHTML=wkTile(`week ${NX}${gr.length?' · grading':' · ahead'}`,String(R.length),`on the slate · from ${esc(D.lbl.replace(LAST_SE+' ',''))}`)
      +(top?wkTile('most consistent',esc(WG_AB[top.s.id]||top.s.lbl),`beat the field ${top.bw}/${top.qw} wks · ${wkX(top.lift)}`,'g',true):'')
      +wkTile('carry 3+',String(c3),'carrying 3+ of them in',c3?'g':'')
      +(B[0]?wkTile('top pick',esc(pshort(B[0].name)),`${B[0].cat} carried${B[0].tp?' · TD '+Math.round(100*B[0].tp.p)+'%':''}`,'g',true):'')
      +wkTile('graded',gr.length?`${gk}<span class="dim"> / ${gr.length}</span>`:'—',gr.length?`scored so far · ${wkPct(gk/gr.length)}`:'✓ / ✗ as box scores import',gr.length&&D.base?(gk/gr.length>=D.base*1.1?'g':gk/gr.length<=D.base*.9?'r':''):'');
    const by=r=>R.filter(x=>r.s.f(x)).sort((a,b)=>(wgTp(b)??-1)-(wgTp(a)??-1));
    box.innerHTML=`<div class="panel"><h3>week ${NX} — the best picks <span class="f">players carrying the most consistent categories into week ${NX} (consistency over ${esc(D.lbl)}), most carried first, then the TD chance · tags = the categories he carries · REC = scored in k of the n recorded games he carried any of them · ✓ / ✗ once his game is logged</span><button class="lk" data-go="wkgrid" title="every player, every category">Category Grid →</button></h3>${B.length?wgPickCards(B.slice(0,12),D.PK):'<p class="mini dim">nobody in view carries a consistent category into this week</p>'}</div>
      <div class="panel"><h3>the categories — most consistent over ${esc(D.lbl)} <span class="f">pips = week by week: green beat the field, red didn't · top three carriers by TD chance · click a category for its pane</span></h3><div class="mlead">${D.PK.map(r=>wgCatCard(r,'g',by(r))).join('')}${D.fades.slice(0,2).map(r=>wgCatCard(r,'r',by(r))).join('')}</div></div>`;
    box.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));tWire(box)}''' + s[i1:]
rep(r'''    S=+$('#wkSe').value;const F=wkFeat(S),SG=wkSigs();''', r'''    S=+$('#wkSe').value;const F=wkFeat(S),SG=wkSigs();
    if(S===LAST_SE&&G.week!==gw){gw=G.week;const mx=F.weeks.length?Math.max(...F.weeks):0;if(F.weeks.includes(G.week))W=G.week;else if(G.week>mx){W='next';NX=G.week}}
    if(W==='next'&&S!==LAST_SE)W=null;
    {const SEC=[...el.children].filter(c=>!c.classList.contains('controls')&&c.id!=='wkTiles'&&c.id!=='wkNX');
      if(W==='next'){SEC.forEach(c=>{if(!c.hidden){c.hidden=true;c.dataset.nx='1'}});chipsW(F);wkNext(F);return}
      $('#wkNX').hidden=true;el.querySelectorAll('[data-nx]').forEach(c=>{c.hidden=false;delete c.dataset.nx})}''')
rep(" weeklies:['v25','", " weeklies:['v26','the wk N ▸ chips open the week ahead — its best picks (most consistent categories carried in, then the TD chance) and the categories themselves, graded ✓ / ✗ as box scores import; the week picked up top moves the tab · ")
open(P, 'w', encoding='utf-8').write(s)
print('patch_v26: Category Grid + Weeklies week-ahead view')
