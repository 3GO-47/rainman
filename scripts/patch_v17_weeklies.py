# -*- coding: utf-8 -*-
"""v17 — F6 TEST › Weeklies: the touchdown lookback. For every week whose games are all played and logged: who scored a rushing or
receiving TD, which pre-game signals pointed at them (rebuilt as they stood before kickoff), a written read of the week, the
week-by-week headline trends and the season grid of which signals keep producing scorers."""
def patch(path,pairs):
    s=open(path,encoding='utf-8').read()
    for old,new in pairs:
        assert s.count(old)==1,(path,old[:80],s.count(old))
        s=s.replace(old,new)
    open(path,'w',encoding='utf-8').write(s)

WK_JS = r"""
/* ---------------- Weeklies (F6 TEST) — the touchdown lookback ----------------
   Once every game of a week is played and logged, this asks one thing of it: who scored a rushing or receiving touchdown,
   and which of the signals the site shows BEFORE kickoff pointed at them. Every signal is rebuilt as it stood going into
   that week, from the game logs alone — nothing that happened in or after the game leaks into it:
     TD / fantasy matchup  the opponent's rank in TDs (or PPR) allowed per game to his slot, from the games before that week:
                           the prior season alone until four weeks of the current one exist, then current ×2 + prior (the
                           dvp_combined rule) · rank 1 = allows the most
     scored vs them before a TD in any earlier logged meeting with this opponent (the H2H boards)
     form                  his own earlier games this season: last game, two of the last three, TD rate, snap and target share
     game                  home, favored, implied team total — from the closing spread and total (betting.glh)
   A signal's hit rate is the share of players carrying it who scored; × is that rate over the whole pool's rate that week. */
const WK_GRPS=['QB','RB1','RB2','WR1','WR2','WR3','WR4+','TE1','TE2'];
const WK_CORE=new Set(['QB1','RB1','RB2','WR1','WR2','WR3','TE1']);
const WK_KEY=['td10','ppr10','h2htd','last','hot','rate','imp','lead'];
const WKC={};
const wkTD=l=>(+l[LOG.rtd]||0)+(+l[LOG.rectd]||0);
const wkPos=g=>g==='QB'?'QB':g.slice(0,2);
const wkK=()=>Math.max(1,Math.round(NT*10/32));
function wkSigs(){const K=wkK();return [
 {id:'td10',lbl:`Top-${K} TD matchup`,long:`players facing a top-${K} TD defense for their slot`,kind:'pos',f:x=>x.tdR!=null&&x.tdR<=K},
 {id:'ppr10',lbl:`Top-${K} fantasy matchup`,long:`players facing a top-${K} fantasy defense for their slot`,kind:'pos',f:x=>x.pprR!=null&&x.pprR<=K},
 {id:'combo1',lbl:`Top-${K} TD + implied 24+`,long:`a top-${K} TD matchup on a team implied for 24+ points`,kind:'pos',f:x=>x.tdR!=null&&x.tdR<=K&&x.imp!=null&&x.imp>=24},
 {id:'combo2',lbl:`Top-${K} TD + scored vs them`,long:`a top-${K} TD matchup against a defense they had already scored on`,kind:'pos',f:x=>x.tdR!=null&&x.tdR<=K&&x.hTD>0},
 {id:'h2htd',lbl:'Scored vs them before',long:'players who had scored against this opponent before',kind:'pos',f:x=>x.hTD>0},
 {id:'last',lbl:'Scored last game',long:'last game\'s scorers',kind:'pos',f:x=>x.last===true},
 {id:'hot',lbl:'TD in 2 of last 3',long:'players with a TD in two of their last three games',kind:'pos',f:x=>x.l3!=null&&x.l3>=2},
 {id:'rate',lbl:'TD every other game',long:'players averaging a TD every other game or better',kind:'pos',f:x=>x.rate!=null&&x.rate>=.5},
 {id:'lead',lbl:'Lead role',long:'lead roles (RB1 · WR1 · TE1)',kind:'pos',f:x=>x.grp==='RB1'||x.grp==='WR1'||x.grp==='TE1'},
 {id:'snap',lbl:'70%+ snaps',long:'every-down players (70%+ of snaps)',kind:'pos',f:x=>x.snp!=null&&x.snp>=.7},
 {id:'tsh',lbl:'20%+ target share',long:'pass-catchers drawing 20%+ of the targets',kind:'pos',f:x=>x.tsh!=null&&x.tsh>=.2},
 {id:'imp',lbl:'Implied 24+',long:'players on a team implied for 24+ points',kind:'pos',f:x=>x.imp!=null&&x.imp>=24},
 {id:'fav',lbl:'Team favored',long:'players on the favored team',kind:'pos',f:x=>x.fav===true},
 {id:'home',lbl:'Home',long:'players at home',kind:'pos',f:x=>x.home},
 {id:'tdbot',lbl:`Bottom-${K} TD matchup`,long:`players facing a bottom-${K} TD defense for their slot`,kind:'neg',f:x=>x.tdR!=null&&x.nD>K&&x.tdR>x.nD-K},
 {id:'h2hno',lbl:'Blanked vs them before',long:'players who had faced this opponent and never scored',kind:'neg',f:x=>x.hN>0&&x.hTD===0},
 {id:'dry',lbl:'No TD yet (3+ games)',long:'players still looking for a first TD after three or more games',kind:'neg',f:x=>x.gpS>=3&&x.tdS===0}]}
function wkAgg(S){const a={},g={};J.logs.forEach(l=>{if(l[LOG.season]!==S||l[LOG.week]>18)return;const d=l[LOG.opp],gr=SLOTG(l[LOG.slot]);if(!d||!gr)return;const w=l[LOG.week];
  (g[d]=g[d]||new Set()).add(w);const x=((a[d]=a[d]||{})[gr]=a[d][gr]||{});const c=x[w]=x[w]||{td:0,ppr:0};c.td+=wkTD(l);c.ppr+=+l[LOG.fppr]||0});return {a,g}}
function wkFeat(S){if(WKC[S])return WKC[S];
  const A=wkAgg(S),P=ALL_SE.includes(S-1)?wkAgg(S-1):null;
  const per=(X,d,gr,k,W)=>{const gs=[...(X.g[d]||[])].filter(w=>w<W);if(!gs.length)return null;const x=(X.a[d]||{})[gr]||{};let s=0;gs.forEach(w=>{if(x[w])s+=x[w][k]});return {v:s/gs.length,n:gs.length}};
  const blend=(W,d,gr,k)=>{const c=per(A,d,gr,k,W),p=P?per(P,d,gr,k,99):null;if(c&&c.n>=4)return p?(2*c.v+p.v)/3:c.v;return p?p.v:c?c.v:null};
  const RK={},defs=[...new Set(Object.keys(A.g).concat(P?Object.keys(P.g):[]))];
  const ranks=W=>{if(RK[W])return RK[W];const out={};WK_GRPS.forEach(gr=>{const o=out[gr]={n:0};['td','ppr'].forEach(k=>{const v={};defs.forEach(d=>{const r=blend(W,d,gr,k);if(r!=null)v[d]=r});
      const vals=Object.values(v);o[k]={};Object.entries(v).forEach(([d,x])=>{o[k][d]=1+vals.filter(y=>y>x).length});o.n=Math.max(o.n,vals.length)})});return RK[W]=out};
  /* closing lines: [season, week, away, home, away pts, home pts, spread (+ = home favored), total, roof, ...] */
  const LN={};((J.betting||{}).glh||[]).forEach(r=>{if(r[0]!==S)return;const w=r[1],a=r[2],h=r[3],sp=r[6],tot=r[7];if(sp==null||tot==null||sp===''||tot==='')return;
    LN[w+'|'+h]={fav:+sp>0,imp:+tot/2+(+sp)/2};LN[w+'|'+a]={fav:+sp<0,imp:+tot/2-(+sp)/2}});
  const mn=(a,f)=>{const v=a.map(f).filter(x=>x!=null&&x!==''&&!isNaN(x));return v.length?v.reduce((s,x)=>s+(+x),0)/v.length:null};
  const rows=[];
  Object.values(PLOGS).forEach(L=>L.forEach((l,i)=>{if(l[LOG.season]!==S||l[LOG.week]>18)return;const grp=SLOTG(l[LOG.slot]);if(!grp)return;
    const w=l[LOG.week],opp=l[LOG.opp],prev=L.slice(0,i),cur=prev.filter(p=>p[LOG.season]===S),vs=prev.filter(p=>p[LOG.opp]===opp);
    const R=ranks(w)[grp]||{n:0},ln=LN[w+'|'+l[LOG.team]],pos=wkPos(grp),tdS=cur.reduce((s,p)=>s+wkTD(p),0);
    rows.push({l,name:l[LOG.player],team:l[LOG.team],opp,w,grp,slot:l[LOG.slot],pos,home:l[LOG.ha]==='H',
      td:wkTD(l),rtd:+l[LOG.rtd]||0,rectd:+l[LOG.rectd]||0,ppr:+l[LOG.fppr]||0,
      tdR:R.td&&R.td[opp]!=null?R.td[opp]:null,pprR:R.ppr&&R.ppr[opp]!=null?R.ppr[opp]:null,nD:R.n,
      hN:vs.length,hTD:vs.reduce((s,p)=>s+wkTD(p),0),
      last:cur.length?wkTD(cur[cur.length-1])>0:null,l3:cur.length>=2?cur.slice(-3).filter(p=>wkTD(p)>0).length:null,
      gpS:cur.length,tdS,rate:cur.length>=2?tdS/cur.length:null,
      snp:mn(cur,p=>p[LOG.snp]),tsh:pos==='QB'?null:mn(cur,p=>p[LOG.tsh]),
      imp:ln?ln.imp:null,fav:ln?ln.fav:null,core:WK_CORE.has(l[LOG.slot])})}));
  const have=[...new Set(rows.map(x=>x.w))].sort((a,b)=>a-b);let weeks=have,pending=[];
  if(S===LAST_SE){const G26=Array.isArray(J.games26)&&J.games26.length&&Array.isArray(J.games26[0])&&typeof J.games26[0][1]==='string'?J.games26:null;
    const got={};rows.forEach(x=>{(got[x.w]=got[x.w]||new Set()).add(x.team)});
    weeks=have.filter(w=>{if(G26){const exp=new Set();G26.filter(g=>+g[0]===w).forEach(g=>{exp.add(g[1]);exp.add(g[2])});if(exp.size)return [...exp].every(t=>got[w].has(t))}return w<(J.week||99)});
    pending=have.filter(w=>!weeks.includes(w))}
  return WKC[S]={rows,weeks,pending}}
function wkStats(F,w,keep,SG){const P=F.rows.filter(x=>x.w===w&&keep(x)),sc=P.filter(x=>x.td>0),base=P.length?sc.length/P.length:null;
  const sig=SG.map(s=>{const m=P.filter(s.f),k=m.filter(x=>x.td>0).length;return Object.assign({},s,{n:m.length,k,hr:m.length?k/m.length:null,lift:m.length&&base?(k/m.length)/base:null,share:sc.length?k/sc.length:null})});
  P.forEach(x=>{x.cs=WK_KEY.reduce((c,id)=>c+(SG.find(s=>s.id===id).f(x)?1:0),0)});
  return {w,P,sc,base,sig,tds:P.reduce((s,x)=>s+x.td,0),minN:Math.max(6,Math.round(P.length*.04))}}
const wkPct=v=>v==null?'—':Math.round(100*v)+'%',wkX=v=>v==null?'—':v.toFixed(1)+'×';
/* hit-rate shading: 2× the field = the greenest pill, the field = neutral, half the field = the reddest */
const wkLiftS=l=>l==null?'':gradeStyle(1+(1-Math.max(0,Math.min(1,(Math.log2(Math.max(l,.01))+1)/2)))*(NT-1));
const wkVerdict=(s,minN)=>s.n<minN?['thin sample','dim']:s.kind==='neg'?(s.lift<=.8?['fade held','g']:s.lift>=1.1?['fade failed','r']:['flat','dim']):(s.lift>=1.2?['held','g']:s.lift<=.9?['missed','r']:['flat','dim']);
function wkNames(a,n){return a.slice(0,n).map(x=>pn(x.name,x.team,true)+(x.td>1?` <span class="mini">×${x.td}</span>`:'')).join(', ')+(a.length>n?` and ${a.length-n} more`:'')}
/* the written read of one week */
function wkStory(st,poolL){const q=st.sig.filter(s=>s.n>=st.minN&&s.hr!=null),pos=q.filter(s=>s.kind==='pos'),neg=q.filter(s=>s.kind==='neg'),out=[];
  if(!st.P.length)return ['<li>nobody in this pool played this week</li>'];
  out.push(`<b>Week ${st.w}:</b> ${st.tds} rushing and receiving touchdowns from ${poolL}. ${st.sc.length} of the ${st.P.length} who played found the end zone — a ${wkPct(st.base)} field rate, the bar every signal below is measured against.`);
  const held=pos.filter(s=>s.lift>=1.1).sort((a,b)=>b.hr-a.hr||b.lift-a.lift);
  if(held.length){const b=held[0];out.push(`<b>Most consistent:</b> ${b.long} — ${b.k} of ${b.n} scored (${wkPct(b.hr)}), ${wkX(b.lift)} the field rate.`);
    const more=held.slice(1,3);if(more.length)out.push(`<b>Also held:</b> ${more.map(s=>`${s.long} (${s.k} of ${s.n}, ${wkPct(s.hr)}, ${wkX(s.lift)})`).join('; ')}.`)}
  else out.push(`<b>No signal stood out:</b> nothing carried by ${st.minN}+ players beat the ${wkPct(st.base)} field rate by 10% or more.`);
  const miss=pos.filter(s=>s.lift<=.9).sort((a,b)=>a.lift-b.lift).slice(0,2);
  if(miss.length)out.push(`<b>Didn't hold:</b> ${miss.map(s=>`${s.long} scored at ${wkPct(s.hr)} (${s.k} of ${s.n}) — ${s.lift<1?'below':'no better than'} the field`).join('; ')}.`);
  neg.forEach(s=>{if(s.lift<=.8)out.push(`<b>Fade held:</b> ${s.long} scored just ${wkPct(s.hr)} (${s.k} of ${s.n}).`);else if(s.lift>=1.1)out.push(`<b>Fade failed:</b> ${s.long} still scored at ${wkPct(s.hr)} (${s.k} of ${s.n}).`)});
  const bySlot={};st.P.forEach(x=>{const o=bySlot[x.grp]=bySlot[x.grp]||{g:x.grp,n:0,k:0};o.n++;if(x.td>0)o.k++});
  const sl=Object.values(bySlot).filter(o=>o.n>=5).map(o=>Object.assign(o,{r:o.k/o.n})).sort((a,b)=>b.r-a.r);
  if(sl.length>1){const a=sl[0],z=sl[sl.length-1];out.push(`<b>By slot:</b> ${slotchip(a.g)} scored most often (${a.k} of ${a.n}, ${wkPct(a.r)}); ${slotchip(z.g)} least (${z.k} of ${z.n}, ${wkPct(z.r)}).`)}
  const multi=st.sc.filter(x=>x.td>1).sort((a,b)=>b.td-a.td);
  if(multi.length)out.push(`<b>Multi-TD days:</b> ${wkNames(multi,8)}.`);
  const sur=st.sc.filter(x=>x.cs<=1).sort((a,b)=>b.td-a.td||a.cs-b.cs);
  if(sur.length)out.push(`<b>Out of nowhere:</b> ${sur.length} of the ${st.sc.length} scorers carried one of the core signals or none going in — ${wkNames(sur,6)}.`);
  const nm=st.P.filter(x=>x.td===0&&x.cs>=5).sort((a,b)=>b.cs-a.cs);
  if(nm.length)out.push(`<b>Everything lined up, no score:</b> ${nm.slice(0,5).map(x=>`${pn(x.name,x.team,true)} <span class="mini">(${x.cs} signals)</span>`).join(', ')}${nm.length>5?` and ${nm.length-5} more`:''}.`);
  const dv={};st.P.forEach(x=>{if(x.td>0){const o=dv[x.opp]=dv[x.opp]||{d:x.opp,n:0,who:[]};o.n+=x.td;o.who.push(x)}});
  const lk=Object.values(dv).sort((a,b)=>b.n-a.n).slice(0,2);
  if(lk.length&&lk[0].n>=3)out.push(`<b>Leakiest end zones:</b> ${lk.map(o=>`${tcell(o.d)} gave up ${o.n} (${wkNames(o.who,3)})`).join('; ')}.`);
  return out.map(t=>`<li>${t}</li>`)}
/* the season read: which signals keep producing scorers week after week */
function wkSeasonStory(AL,SG){if(AL.length<2)return '';const out=[];const tot={n:0,k:0};AL.forEach(st=>{tot.n+=st.P.length;tot.k+=st.sc.length});const base=tot.n?tot.k/tot.n:0;
  const rows=SG.map(s=>{let n=0,k=0,qw=0,bw=0;AL.forEach(st=>{const x=st.sig.find(y=>y.id===s.id);n+=x.n;k+=x.k;if(x.n>=st.minN){qw++;if(s.kind==='pos'?x.lift>=1.1:x.lift<=.9)bw++}});
    return Object.assign({},s,{n,k,hr:n?k/n:null,lift:n&&base?(k/n)/base:null,qw,bw})});
  const pos=rows.filter(r=>r.kind==='pos'&&r.qw>=Math.max(2,Math.ceil(AL.length/2))),neg=rows.filter(r=>r.kind==='neg'&&r.qw>=2);
  const last=AL[AL.length-1].w,first=AL[0].w;
  const st=pos.slice().sort((a,b)=>b.bw/b.qw-a.bw/a.qw||b.lift-a.lift)[0];
  if(st)out.push(`Weeks ${first}–${last}: the steadiest touchdown signal is <b>${st.lbl}</b> — it beat the field in ${st.bw} of ${st.qw} weeks and has hit ${wkPct(st.hr)} overall (${st.k} of ${st.n}), ${wkX(st.lift)} the ${wkPct(base)} field.`);
  const bp=pos.slice().sort((a,b)=>b.hr-a.hr)[0];if(bp&&bp!==st)out.push(`The best pooled hit rate belongs to <b>${bp.lbl}</b>: ${wkPct(bp.hr)} (${bp.k} of ${bp.n}), ${wkX(bp.lift)}.`);
  const wk=pos.slice().sort((a,b)=>a.bw/a.qw-b.bw/b.qw||a.lift-b.lift)[0];if(wk&&wk!==st&&wk!==bp)out.push(`Least reliable: <b>${wk.lbl}</b> — it beat the field in only ${wk.bw} of ${wk.qw} weeks (${wkPct(wk.hr)} overall, ${wkX(wk.lift)}).`);
  const fd=neg.slice().sort((a,b)=>a.lift-b.lift)[0];if(fd&&fd.lift<1)out.push(`Best fade: <b>${fd.lbl}</b> — ${wkPct(fd.hr)} all season against a ${wkPct(base)} field.`);
  return out.join(' ')}
function weeklies(){
  const el=$('#weeklies');if(!el)return;
  const SES=ALL_SE.slice().reverse();let S=SES[0];if(!wkFeat(S).weeks.length&&SES[1])S=SES[1];
  let W=null,show='sc';const posSet=new Set();
  el.innerHTML=`<div class="controls">
    <select id="wkSe" title="which season to look back on">${SES.map(s=>`<option value="${s}" ${s===S?'selected':''}>${s} season</option>`).join('')}</select>
    <span class="chips" id="wkW" title="every week whose games are all played and logged"></span>
    <select id="wkPool" title="who counts"><option value="core" selected>starters: QB1 · RB1-2 · WR1-3 · TE1</option><option value="all">every slot that played</option></select>
    <span class="chips" id="wkPos" title="narrow the pool to one or more positions — click to toggle"><button data-p="" class="on">all</button>${TPOS.map(p=>`<button data-p="${p}">${posIcon(p,11)} ${p}</button>`).join('')}</span>
    <span class="note">the touchdown lookback. A week appears once every game is played and logged. Every signal is rebuilt <b>as it stood before that week kicked off</b> — the defense ranks from the games before it, his earlier meetings with the opponent, his form to that point, the closing line — then checked against who actually scored a rushing or receiving touchdown. <b>hit rate</b> = share of the players carrying a signal who scored &middot; <b>×</b> = that rate over the whole pool's rate that week &middot; a TD / fantasy matchup rank of 1 = the defense allowing the most to his slot &middot; "core signals" for the surprise and near-miss lines are the TD and fantasy matchups, a TD vs them before, last game, two of the last three, a TD every other game, implied 24+ and a lead role</span>
  </div>
  <div class="kpis" id="wkKpi"></div>
  <div class="wk2"><div class="panel"><h3 id="wkTh"></h3><ul class="wkstory" id="wkStory"></ul></div>
    <div class="panel"><h3 id="wkSh"></h3><div id="wkSig"></div></div></div>
  <div class="panel"><h3 id="wkTlh">week by week — what produced the scorers</h3><p class="wkss" id="wkSS"></p><div class="wktl" id="wkTl"></div></div>
  <div class="panel"><h3 id="wkMh"></h3><div id="wkMx"></div></div>
  <div class="panel"><h3 id="wkPh"></h3><div class="controls" style="margin:0 0 6px"><span class="chips" id="wkShow"><button data-s="sc" class="on">every scorer</button><button data-s="nm">near misses</button><button data-s="all">everyone in the pool</button></span></div><div id="wkPl"></div></div>`;
  const keep=x=>($('#wkPool').value==='all'||x.core)&&(!posSet.size||posSet.has(x.pos));
  const poolL=()=>{const p=posSet.size?[...posSet].join(' / ')+' ':'';return $('#wkPool').value==='all'?`every ${p}player who played`:`the ${p}starters`};
  function chipsW(F){const box=$('#wkW');box.innerHTML=F.weeks.map(w=>`<button data-w="${w}" class="${w===W?'on':''}">wk ${w}</button>`).join('')+(F.pending.length?`<span class="mini" style="margin-left:6px" title="a week appears once every game is logged">wk ${F.pending.join(', ')} in progress</span>`:'');
    box.querySelectorAll('button').forEach(b=>b.onclick=()=>{W=+b.dataset.w;render()})}
  function render(){
    S=+$('#wkSe').value;const F=wkFeat(S),SG=wkSigs();
    if(!F.weeks.length){$('#wkW').innerHTML='';['wkKpi','wkStory','wkSig','wkTl','wkMx','wkPl','wkSS'].forEach(i=>$('#'+i).innerHTML='');$('#wkTh').textContent=`no completed week in ${S} yet`;return}
    if(W==null||!F.weeks.includes(W))W=F.weeks[F.weeks.length-1];
    chipsW(F);
    const AL=F.weeks.filter(w=>w<=W).map(w=>wkStats(F,w,keep,SG)),st=AL[AL.length-1];
    /* signals no week has a sample for (no lines in the data, a first season with no prior) leave the tables */
    const live=SG.filter(s=>AL.some(a=>a.sig.find(y=>y.id===s.id).n>0)).map(s=>s.id);
    const q=st.sig.filter(s=>live.includes(s.id)),held=q.filter(s=>s.kind==='pos'&&s.n>=st.minN&&s.lift>=1.1).sort((a,b)=>b.hr-a.hr);
    const sur=st.sc.filter(x=>x.cs<=1);const dv={};st.P.forEach(x=>{if(x.td>0)dv[x.opp]=(dv[x.opp]||0)+x.td});const lk=Object.entries(dv).sort((a,b)=>b[1]-a[1])[0];
    $('#wkKpi').innerHTML=kpi('touchdowns',String(st.tds),`rushing + receiving · wk ${W} ${S}`)+kpi('scorers',`${st.sc.length} / ${st.P.length}`,`${wkPct(st.base)} of the pool scored`)
      +kpi('multi-TD',String(st.sc.filter(x=>x.td>1).length),'players with 2+')+(held[0]?kpi('most consistent',held[0].lbl,`${wkPct(held[0].hr)} · ${wkX(held[0].lift)} the field`,'g'):kpi('most consistent','—','no signal beat the field'))
      +kpi('out of nowhere',String(sur.length),'scorers with ≤1 core signal')+(lk?kpi('leakiest defense',lk[0],`${lk[1]} TDs allowed to this pool`,'r'):'');
    $('#wkTh').innerHTML=`week ${W} — the read <span class="f">${S} · ${poolL()}</span>`;
    $('#wkStory').innerHTML=wkStory(st,poolL()).join('');
    $('#wkSh').innerHTML=`week ${W} — every signal <span class="f">pool ${st.P.length} · field ${wkPct(st.base)} · a verdict needs ${st.minN}+ players</span>`;
    $('#wkSig').innerHTML=`<table class="fx wks"><thead><tr><th>signal</th><th title="players carrying it going in">players</th><th title="of those, how many scored">scored</th><th title="share of them who scored">hit rate</th><th title="hit rate over the field rate">× field</th><th title="share of all the week's scorers who carried it">of scorers</th><th>verdict</th></tr></thead><tbody>
      ${q.map(s=>{const v=wkVerdict(s,st.minN);return `<tr class="${s.kind==='neg'?'neg':''}"><td title="${esc(s.long)}">${s.kind==='neg'?'<span class="dim">fade · </span>':''}${s.lbl}</td><td class="n" data-v="${s.n}">${s.n||'<span class="dim">0</span>'}</td><td class="n" data-v="${s.k}">${s.k}</td>
        <td class="n" data-v="${s.hr??''}">${s.hr==null?'<span class="dim">·</span>':`<span class="badge" style="${s.n>=st.minN?wkLiftS(s.lift):''}">${wkPct(s.hr)}</span>`}</td>
        <td class="n" data-v="${s.lift??''}">${s.lift==null?'<span class="dim">·</span>':`<b style="color:${s.n<st.minN?'var(--dim)':s.lift>=1.1?'var(--green)':s.lift<=.9?'var(--red)':'var(--dim)'}">${wkX(s.lift)}</b>`}</td>
        <td class="n" data-v="${s.share??''}">${wkPct(s.share)}</td><td><span class="wkv ${v[1]}">${v[0]}</span></td></tr>`}).join('')}</tbody></table>`;
    /* week-by-week cards, newest first */
    $('#wkSS').innerHTML=wkSeasonStory(AL,SG.filter(s=>live.includes(s.id)));
    $('#wkTl').innerHTML=AL.slice().reverse().map(a=>{const qq=a.sig.filter(s=>live.includes(s.id)&&s.n>=a.minN&&s.hr!=null);
      const h=qq.filter(s=>s.kind==='pos'&&s.lift>=1.1).sort((x,y)=>y.hr-x.hr).slice(0,2),m=qq.filter(s=>s.kind==='pos'&&s.lift<=.9).sort((x,y)=>x.lift-y.lift)[0],f=qq.filter(s=>s.kind==='neg'&&s.lift<=.8).sort((x,y)=>x.lift-y.lift)[0];
      const ln=(ic,c,s)=>`<div class="l"><i style="color:${c}">${ic}</i><span>${s.lbl} <span class="mini">${wkPct(s.hr)} · ${s.k}/${s.n} · ${wkX(s.lift)}</span></span></div>`;
      return `<div class="wkc${a.w===W?' on':''}" data-w="${a.w}"><h4>week ${a.w} <span class="mini">${a.tds} TDs · ${a.sc.length}/${a.P.length} scored · field ${wkPct(a.base)}</span></h4>
        ${h.length?(h[0]?ln('▲','var(--green)',h[0]).replace('<span>','<span><b>most consistent</b> · '):'')+(h[1]?ln('▲','var(--green)',h[1]):''):'<div class="l mini dim">no signal beat the field</div>'}
        ${m?ln('▼','var(--red)',m).replace('<span>','<span><b>didn\'t hold</b> · '):''}${f?ln('↓','var(--cyan)',f).replace('<span>','<span><b>fade held</b> · '):''}</div>`}).join('');
    $('#wkTl').querySelectorAll('.wkc').forEach(c=>c.onclick=e=>{if(e.target.closest('.plink'))return;W=+c.dataset.w;render()});
    /* the season grid: every signal × every week, shaded by how far its hit rate sat from the field */
    const tot={n:0,k:0};AL.forEach(a=>{tot.n+=a.P.length;tot.k+=a.sc.length});const base=tot.n?tot.k/tot.n:null;
    $('#wkMh').innerHTML=`signal × week <span class="f">${S} · weeks ${AL[0].w}–${W} · each cell = hit rate that week, shaded by × the field (green = scored more often than everyone, red = less) · faded cells = under the sample bar · last columns pool every week</span>`;
    $('#wkMx').innerHTML=`<table class="fx wkm"><thead><tr><th>signal</th>${AL.map(a=>`<th class="c${a.w===W?' on':''}">wk ${a.w}</th>`).join('')}<th class="c gs" title="every week pooled">season</th><th class="c" title="pooled hit rate over the pooled field rate">× field</th><th class="c" title="weeks it beat the field by 10%+ (fades: stayed 10%+ under) / weeks with a usable sample">beat field</th></tr></thead><tbody>
      <tr class="fld"><td><b>the field</b> <span class="mini">everyone in the pool</span></td>${AL.map(a=>`<td class="c" data-v="${a.base??''}">${wkPct(a.base)}</td>`).join('')}<td class="c gs" data-v="${base??''}"><b>${wkPct(base)}</b></td><td class="c"></td><td class="c"></td></tr>
      ${SG.filter(s=>live.includes(s.id)).map(s=>{let n=0,k=0,qw=0,bw=0;
        const cells=AL.map(a=>{const x=a.sig.find(y=>y.id===s.id);n+=x.n;k+=x.k;const ok=x.n>=a.minN;if(ok){qw++;if(s.kind==='pos'?x.lift>=1.1:x.lift<=.9)bw++}
          return `<td class="c${ok?'':' thin'}" data-v="${x.hr??''}" title="${esc(`${s.lbl} · wk ${a.w}: ${x.k} of ${x.n} scored${x.lift!=null?' · '+wkX(x.lift)+' the field':''}${ok?'':' · under the sample bar'}`)}">${x.hr==null?'<span class="dim">·</span>':`<span class="hc" style="${wkLiftS(x.lift)}">${wkPct(x.hr)}</span>`}</td>`}).join('');
        const hr=n?k/n:null,lift=hr!=null&&base?hr/base:null;
        return `<tr class="${s.kind==='neg'?'neg':''}"><td title="${esc(s.long)}">${s.kind==='neg'?'<span class="dim">fade · </span>':''}${s.lbl}</td>${cells}
          <td class="c gs" data-v="${hr??''}" title="${k} of ${n}">${hr==null?'<span class="dim">·</span>':`<span class="hc" style="${wkLiftS(lift)}">${wkPct(hr)}</span>`}</td>
          <td class="c" data-v="${lift??''}"><b style="color:${lift==null?'var(--dim)':lift>=1.1?'var(--green)':lift<=.9?'var(--red)':'var(--dim)'}">${wkX(lift)}</b></td>
          <td class="c" data-v="${qw?bw/qw:''}"><b style="color:${!qw?'var(--dim)':bw/qw>=.6?'var(--green)':bw/qw<=.3?'var(--red)':'var(--amber)'}">${bw} / ${qw}</b></td></tr>`}).join('')}</tbody></table>`;
    /* the players: every scorer with his pre-game profile (or the near misses, or the whole pool) */
    const SH={sc:'every touchdown scorer',nm:'near misses — 4+ core signals, no touchdown',all:'everyone in the pool'};
    let P=show==='sc'?st.sc:show==='nm'?st.P.filter(x=>x.td===0&&x.cs>=4):st.P;
    P=P.slice().sort((a,b)=>b.td-a.td||b.cs-a.cs||b.ppr-a.ppr);
    const ck=v=>v===true?'<b style="color:var(--green)">✓</b>':v===false?'<span class="dim">·</span>':'<span class="dim">—</span>';
    const rk=(r,n)=>r==null?'<span class="dim">·</span>':`<span class="badge" style="${gradeStyle(r,n||NT)}">${r}</span>`;
    $('#wkPh').innerHTML=`week ${W} — ${SH[show]} <span class="f">${P.length} players · every column is what was known before kickoff except TD and PPR · click a name for his card</span>`;
    $('#wkPl').innerHTML=`<table class="fx wkp"><thead><tr><th>player</th><th>slot</th><th>opp</th><th title="rushing + receiving touchdowns this week">TD</th><th title="PPR points this week">PPR</th>
      <th title="the opponent's rank in TDs allowed per game to his slot going into the week · 1 = the most">TD rk</th><th title="the opponent's rank in PPR allowed per game to his slot going into the week">PPR rk</th>
      <th title="his touchdowns in earlier meetings with this opponent · games">vs them</th><th title="scored in his previous game this season">last</th><th title="games with a TD in his last three this season">L3</th><th title="TDs per game this season before this week">TD/g</th>
      <th title="snap share this season before this week">snap</th><th title="team implied total from the closing line">implied</th><th title="core signals he carried going in (of 8)">signals</th></tr></thead><tbody>
      ${P.map(x=>`<tr><td>${pn(x.name,x.team,true)}</td><td>${slotchip(x.grp)}</td><td>${x.home?'':'@'}${tcell(x.opp)}</td>
        <td class="n" data-v="${x.td}" title="${x.rtd} rushing · ${x.rectd} receiving">${x.td?`<b style="color:var(--green)">${x.td}</b>`:'<span class="dim">0</span>'}</td><td class="n" data-v="${x.ppr}">${x.ppr.toFixed(1)}</td>
        <td class="n" data-v="${x.tdR??''}">${rk(x.tdR,x.nD)}</td><td class="n" data-v="${x.pprR??''}">${rk(x.pprR,x.nD)}</td>
        <td class="n" data-v="${x.hN?x.hTD:''}">${x.hN?`<b style="color:${x.hTD?'var(--green)':'var(--dim)'}">${x.hTD}</b><span class="mini"> in ${x.hN}</span>`:'<span class="dim">—</span>'}</td>
        <td class="c">${ck(x.last)}</td><td class="n" data-v="${x.l3??''}">${x.l3==null?'<span class="dim">—</span>':`<b style="color:${x.l3>=2?'var(--green)':x.l3===0?'var(--dim)':'var(--txt)'}">${x.l3}</b>`}</td>
        <td class="n" data-v="${x.rate??''}">${x.rate==null?'<span class="dim">—</span>':x.rate.toFixed(2)}</td><td class="n" data-v="${x.snp??''}">${x.snp==null?'<span class="dim">—</span>':Math.round(100*x.snp)+'%'}</td>
        <td class="n" data-v="${x.imp??''}">${x.imp==null?'<span class="dim">—</span>':`<span style="color:${x.imp>=24?'var(--green)':x.imp<18?'var(--red)':'var(--txt)'}">${x.imp.toFixed(1)}</span>`}</td>
        <td class="n" data-v="${x.cs}"><span class="badge" style="${gradeStyle(1+(1-x.cs/8)*(NT-1))}">${x.cs}</span></td></tr>`).join('')||'<tr><td colspan="14" class="dim">nobody here</td></tr>'}</tbody></table>`;
    tWire(el)}
  $('#wkSe').onchange=()=>{W=null;render()};$('#wkPool').onchange=render;
  $('#wkPos').querySelectorAll('button').forEach(b=>b.onclick=()=>{const p=b.dataset.p;if(!p)posSet.clear();else posSet.has(p)?posSet.delete(p):posSet.add(p);
    $('#wkPos').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.p?posSet.has(x.dataset.p):posSet.size===0));render()});
  $('#wkShow').querySelectorAll('button').forEach(b=>b.onclick=()=>{show=b.dataset.s;$('#wkShow').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render()});
  render();
}
"""

WK_CSS = r"""
/* ---- v17 Weeklies: the touchdown lookback ---- */
.wk2{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:12px;align-items:start}@media(max-width:1250px){.wk2{grid-template-columns:1fr}}
.wkstory{margin:0;padding:0;list-style:none;font-size:12.5px;line-height:1.6}.wkstory li{padding:6px 2px;border-bottom:1px dashed var(--edge)}.wkstory li:last-child{border-bottom:0}.wkstory b{color:var(--txt)}
.wkss{margin:0 0 8px;font-size:12.5px;line-height:1.6;color:var(--dim)}.wkss b{color:var(--txt)}
.wktl{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.wkc{background:var(--s2,#0b0c0e);border:1px solid var(--edge);border-top:2px solid var(--edge2);border-radius:8px;padding:7px 9px;cursor:pointer;min-width:0}.wkc:hover{border-color:var(--edge2)}.wkc.on{border-top-color:var(--amber)}
.wkc h4{margin:0 0 4px;font:600 11px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--txt);display:flex;justify-content:space-between;gap:6px;flex-wrap:wrap}.wkc h4 .mini{text-transform:none;letter-spacing:0;font-weight:500}
.wkc .l{display:grid;grid-template-columns:12px minmax(0,1fr);gap:5px;font-size:11.5px;line-height:1.5;padding:1px 0}.wkc .l i{font-style:normal}.wkc .l b{font-weight:600;color:var(--dim2);font-size:10px;text-transform:uppercase;letter-spacing:.05em}
table.wks td.n,table.wkp td.n{text-align:right;font-family:var(--mono)}table.wks tr.neg td,table.wkm tr.neg td{background:rgba(255,255,255,.015)}
.wkv{font:600 9.5px var(--ui);letter-spacing:.06em;text-transform:uppercase;padding:1px 6px;border-radius:3px;border:1px solid var(--edge2);color:var(--dim);white-space:nowrap}.wkv.g{color:var(--green);border-color:#00c85366}.wkv.r{color:var(--red);border-color:#ff525266}
table.wkm th.c,table.wkm td.c{text-align:center}table.wkm th.on{color:var(--amber)}table.wkm td.gs,table.wkm th.gs{border-left:1px solid var(--edge2)}
table.wkm .hc{display:inline-block;min-width:36px;padding:1px 4px;border-radius:3px;font:600 10.5px var(--mono)}table.wkm td.thin .hc{opacity:.45}table.wkm tr.fld td{border-bottom:1px solid var(--edge2);font-family:var(--mono)}
table.wkp td.c{text-align:center}"""

T='scripts/dashboard_template.html'
patch(T,[
 ("""   {id:'labgrid',label:'Lab Grid',""",
  """   {id:'weeklies',label:'Weeklies',desc:'the touchdown lookback: once a week\\'s games are all played and logged, who scored, which pre-game signals pointed at them \\u2014 TD and fantasy matchup ranks, a TD against the same opponent before, form, usage, the line \\u2014 a written read of the week, the week-by-week trends and the season grid of which signals keep producing scorers',c:'test',sub:'weeklies'},
   {id:'labgrid',label:'Lab Grid',"""),
 ("""<div id="test" hidden><div id="meta" hidden></div>""","""<div id="test" hidden><div id="meta" hidden></div><div id="weeklies" hidden></div>"""),
 ("""if(it.c==='test'){['meta','labgrid',""","""if(it.c==='test'){['meta','weeklies','labgrid',"""),
 ("""/* ---------------- Game View — one game, everything the site knows about it ----------------""",
  WK_JS + """
/* ---------------- Game View — one game, everything the site knows about it ----------------"""),
 ("""['test',metaGrid],""","""['test',metaGrid],['test',weeklies],"""),
 (""".mlr b{font:700 11px var(--mono)}""", WK_CSS.strip()+"\n.mlr b{font:700 11px var(--mono)}"),
 (""" meta:['v16',""",""" weeklies:['v17','new tab: the touchdown lookback — each finished week\\'s scorers against every pre-game signal (TD and fantasy matchup ranks as they stood that week, a TD vs the same opponent before, form, usage, the line), a written read, week-by-week trends and the season grid'],
 meta:['v16',"""),
])
s=open(T,encoding='utf-8').read()
old="const INTRO={\n"
assert s.count(old)==1
s=s.replace(old,old+""" weeklies:{what:'The touchdown lookback.',how:['every signal is pre-game: the defense ranks, his form and his history with the opponent as they stood before that week kicked off — then checked against who actually scored','hit rate = share of the players carrying a signal who scored a rushing or receiving TD · × = against everyone in the pool that week · green = scored more often than the field','a week appears once every game is played and logged · click a week card to read it']},
""",1)
open(T,'w',encoding='utf-8').write(s)
print('v17 Weeklies patched')
