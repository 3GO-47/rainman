# -*- coding: utf-8 -*-
"""v20 — Weeklies, built out from a three-season study of what predicts an anytime TD:
new pre-game signals (volume, team TD share, career TD rate, a defense that just gave his slot TDs, big underdog, deep threat, stacked pairs),
grouped bars, a 'what to trust' board across every season, the stacking chart, best signal per position, and a forward list for the current
week of who carries the signals that hold up (model price beside it, ✓ once he scores)."""
T='scripts/dashboard_template.html'
s=open(T,encoding='utf-8').read()
def once(old,new):
    global s
    assert s.count(old)==1,(old[:90],s.count(old));s=s.replace(old,new)
def span(start,end_marker):
    a=s.index(start);b=s.index(end_marker,a)+len(end_marker);return a,b

# ---- core signals: the eight that held up across 2024-26 (stacking, surprises, near misses, the forward list)
once("const WK_KEY=['td10','ppr10','h2htd','last','hot','rate','imp','lead'];",
     "const WK_KEY=['rate','hot','career','share','vol','imp','lead','slothot'];\nconst WK_AB={rate:'TD ½',hot:'2 of 3',career:'career ½',share:'TD share',vol:'18+ tch',imp:'imp 24+',lead:'lead',slothot:'slot-hot D'};")

SIGS = r"""function wkSigs(){const [T1,t1,B1,b1]=wkTier();return [
 /* scoring form */
 {id:'rate',g:'form',lbl:'TD every other game',long:'players averaging a TD every other game or better this season',kind:'pos',f:x=>x.rate!=null&&x.rate>=.5},
 {id:'hot',g:'form',lbl:'TD in 2 of last 3',long:'players with a TD in two of their last three games',kind:'pos',f:x=>x.l3!=null&&x.l3>=2},
 {id:'career',g:'form',lbl:'Career TD every other game',long:'players averaging a TD every other game across every logged game (6+)',kind:'pos',f:x=>x.crate!=null&&x.crate>=.5},
 {id:'last',g:'form',lbl:'Scored last game',long:'last game\'s scorers',kind:'pos',f:x=>x.last===true},
 /* role and volume */
 {id:'share',g:'role',lbl:'25%+ of team TDs',long:'players who have scored a quarter or more of their team\'s skill touchdowns this season',kind:'pos',f:x=>x.share!=null&&x.share>=.25},
 {id:'vol',g:'role',lbl:'18+ touches a game',long:'players averaging 18+ carries and targets a game',kind:'pos',f:x=>x.touch!=null&&x.touch>=18},
 {id:'tgt',g:'role',lbl:'8+ targets a game',long:'pass-catchers averaging 8+ targets a game',kind:'pos',f:x=>x.tgt!=null&&x.tgt>=8},
 {id:'lead',g:'role',lbl:'Lead role',long:'lead roles (RB1 · WR1 · TE1)',kind:'pos',f:x=>x.grp==='RB1'||x.grp==='WR1'||x.grp==='TE1'},
 {id:'snap',g:'role',lbl:'70%+ snaps',long:'every-down players (70%+ of snaps)',kind:'pos',f:x=>x.snp!=null&&x.snp>=.7},
 {id:'tsh',g:'role',lbl:'20%+ target share',long:'pass-catchers drawing 20%+ of the targets',kind:'pos',f:x=>x.tsh!=null&&x.tsh>=.2},
 /* game script */
 {id:'imp',g:'game',lbl:'Implied 24+',long:'players on a team implied for 24+ points',kind:'pos',f:x=>x.imp!=null&&x.imp>=24},
 {id:'imp27',g:'game',lbl:'Implied 27+',long:'players on a team implied for 27+ points',kind:'pos',f:x=>x.imp!=null&&x.imp>=27},
 {id:'fav',g:'game',lbl:'Team favored',long:'players on the favored team',kind:'pos',f:x=>x.fav===true},
 {id:'home',g:'game',lbl:'Home',long:'players at home',kind:'pos',f:x=>x.home},
 /* matchup */
 {id:'slothot',g:'matchup',lbl:'Defense gave his slot TDs lately',long:'players whose opponent allowed a TD to his slot in two of its last three games',kind:'pos',f:x=>x.slothot===true},
 {id:'td10',g:'matchup',lbl:`${T1} TD matchup`,long:`players facing a ${t1} TD defense for their slot (season-long)`,kind:'pos',f:x=>x.tdR!=null&&x.tdR<=x.K},
 {id:'ppr10',g:'matchup',lbl:`${T1} fantasy matchup`,long:`players facing a ${t1} fantasy defense for their slot`,kind:'pos',f:x=>x.pprR!=null&&x.pprR<=x.K},
 {id:'h2htd',g:'matchup',lbl:'Scored vs them before',long:'players who had scored against this opponent before',kind:'pos',f:x=>x.hTD>0},
 /* stacked pairs */
 {id:'shareimp',g:'stack',lbl:'TD share + implied 24+',long:'25%+ of his team\'s TDs on a team implied for 24+',kind:'pos',f:x=>x.share!=null&&x.share>=.25&&x.imp!=null&&x.imp>=24},
 {id:'rateimp',g:'stack',lbl:'TD every other game + implied 24+',long:'a TD every other game on a team implied for 24+',kind:'pos',f:x=>x.rate!=null&&x.rate>=.5&&x.imp!=null&&x.imp>=24},
 {id:'leadimp',g:'stack',lbl:'Lead role + implied 24+',long:'a lead role on a team implied for 24+',kind:'pos',f:x=>(x.grp==='RB1'||x.grp==='WR1'||x.grp==='TE1')&&x.imp!=null&&x.imp>=24},
 {id:'combo1',g:'stack',lbl:`${T1} TD + implied 24+`,long:`a ${t1} TD matchup on a team implied for 24+ points`,kind:'pos',f:x=>x.tdR!=null&&x.tdR<=x.K&&x.imp!=null&&x.imp>=24},
 /* fades */
 {id:'dog7',g:'fade',lbl:'Underdog by 7+',long:'players on a team getting 7 or more points',kind:'neg',f:x=>x.sp!=null&&x.sp<=-7},
 {id:'deep',g:'fade',lbl:'Deep threat (aDOT 12+)',long:'receivers whose average target travels 12+ yards',kind:'neg',f:x=>x.adot!=null&&x.adot>=12},
 {id:'tdbot',g:'fade',lbl:`${B1} TD matchup`,long:`players facing a ${b1} TD defense for their slot`,kind:'neg',f:x=>x.tdR!=null&&x.nD>x.K&&x.tdR>x.nD-x.K},
 {id:'h2hno',g:'fade',lbl:'Blanked vs them before',long:'players who had faced this opponent and never scored',kind:'neg',f:x=>x.hN>0&&x.hTD===0},
 {id:'dry',g:'fade',lbl:'No TD yet (3+ games)',long:'players still looking for a first TD after three or more games',kind:'neg',f:x=>x.gpS>=3&&x.tdS===0}]}
const WK_GL={form:'scoring form',role:'role & volume',game:'game script',matchup:'matchup',stack:'stacked pairs',fade:'fades — expected to score less · green = they did'};"""
a,b=span("function wkSigs(){","x.gpS>=3&&x.tdS===0}]}")
s=s[:a]+SIGS+s[b:]

FEAT = r"""/* everything a game's pre-kickoff profile needs, built once per season */
const WKX={};
function wkCtx(S){if(WKX[S])return WKX[S];
  const A=wkAgg(S),P=ALL_SE.includes(S-1)?wkAgg(S-1):null;
  const per=(X,d,gr,k,W)=>{const gs=[...(X.g[d]||[])].filter(w=>w<W);if(!gs.length)return null;const x=(X.a[d]||{})[gr]||{};let s=0;gs.forEach(w=>{if(x[w])s+=x[w][k]});return {v:s/gs.length,n:gs.length}};
  const blend=(W,d,gr,k)=>{const c=per(A,d,gr,k,W),p=P?per(P,d,gr,k,99):null;if(c&&c.n>=4)return p?(2*c.v+p.v)/3:c.v;return p?p.v:c?c.v:null};
  const RK={},defs=[...new Set(Object.keys(A.g).concat(P?Object.keys(P.g):[]))];
  const ranks=W=>{if(RK[W])return RK[W];const out={};WK_GRPS.forEach(gr=>{const o=out[gr]={n:0};['td','ppr'].forEach(k=>{const v={};defs.forEach(d=>{const r=blend(W,d,gr,k);if(r!=null)v[d]=r});
      const vals=Object.values(v);o[k]={};Object.entries(v).forEach(([d,x])=>{o[k][d]=1+vals.filter(y=>y>x).length});o.n=Math.max(o.n,vals.length)})});return RK[W]=out};
  /* closing lines: [season, week, away, home, away pts, home pts, spread (+ = home favored), total, roof, ...] */
  const LN={};((J.betting||{}).glh||[]).forEach(r=>{if(r[0]!==S)return;const w=r[1],a=r[2],h=r[3],sp=r[6],tot=r[7];if(sp==null||tot==null||sp===''||tot==='')return;
    LN[w+'|'+h]={fav:+sp>0,imp:+tot/2+(+sp)/2,sp:+sp};LN[w+'|'+a]={fav:+sp<0,imp:+tot/2-(+sp)/2,sp:-sp}});
  /* every team's skill touchdowns per week — the denominator of a player's TD share */
  const TT={};J.logs.forEach(l=>{if(l[LOG.season]!==S)return;const t=l[LOG.team],w=l[LOG.week];(TT[t]=TT[t]||{})[w]=(TT[t][w]||0)+wkTD(l)});
  return WKX[S]={A,ranks,LN,TT}}
const wkMn=(a,f)=>{const v=a.map(f).filter(x=>x!=null&&x!==''&&!isNaN(x));return v.length?v.reduce((s,x)=>s+(+x),0)/v.length:null};
/* one player's pre-game profile for season S week w, from his earlier games only */
function wkPre(prev,S,w,team,opp,grp,home,cx){
  const cur=prev.filter(p=>p[LOG.season]===S),vs=prev.filter(p=>p[LOG.opp]===opp),pos=wkPos(grp),R=cx.ranks(w)[grp]||{n:0},ln=cx.LN[w+'|'+team],tdS=cur.reduce((s,p)=>s+wkTD(p),0);
  const tw=Object.keys(cx.TT[team]||{}).map(Number).filter(x=>x<w),tt=tw.reduce((s,x)=>s+cx.TT[team][x],0),mine=cur.filter(p=>p[LOG.team]===team).reduce((s,p)=>s+wkTD(p),0);
  const dg=[...(cx.A.g[opp]||[])].filter(x=>x<w).sort((a,b)=>a-b).slice(-3),xa=((cx.A.a[opp]||{})[grp])||{};
  return {opp,w,grp,pos,home,
    tdR:R.td&&R.td[opp]!=null?R.td[opp]:null,pprR:R.ppr&&R.ppr[opp]!=null?R.ppr[opp]:null,nD:R.n,K:Math.max(1,Math.round(R.n*10/32)),
    hN:vs.length,hTD:vs.reduce((s,p)=>s+wkTD(p),0),
    last:cur.length?wkTD(cur[cur.length-1])>0:null,l3:cur.length>=2?cur.slice(-3).filter(p=>wkTD(p)>0).length:null,
    gpS:cur.length,tdS,rate:cur.length>=2?tdS/cur.length:null,crate:prev.length>=6?prev.reduce((s,p)=>s+wkTD(p),0)/prev.length:null,
    share:tt>=4?mine/tt:null,touch:cur.length?wkMn(cur,p=>(+p[LOG.ra]||0)+(+p[LOG.tgt]||0)):null,tgt:cur.length&&pos!=='QB'?wkMn(cur,p=>+p[LOG.tgt]||0):null,
    adot:pos==='QB'?null:wkMn(cur.filter(p=>(+p[LOG.tgt]||0)>0),p=>p[LOG.adot]),
    slothot:dg.length>=2?dg.filter(x=>xa[x]&&xa[x].td>0).length>=2:null,
    snp:wkMn(cur,p=>p[LOG.snp]),tsh:pos==='QB'?null:wkMn(cur,p=>p[LOG.tsh]),
    imp:ln?ln.imp:null,fav:ln?ln.fav:null,sp:ln?ln.sp:null}}
function wkFeat(S){if(WKC[S])return WKC[S];
  const cx=wkCtx(S),rows=[];
  Object.values(PLOGS).forEach(L=>L.forEach((l,i)=>{if(l[LOG.season]!==S||l[LOG.week]>18)return;const grp=SLOTG(l[LOG.slot]);if(!grp)return;
    const x=wkPre(L.slice(0,i),S,l[LOG.week],l[LOG.team],l[LOG.opp],grp,l[LOG.ha]==='H',cx);
    rows.push(Object.assign(x,{l,name:l[LOG.player],team:l[LOG.team],slot:l[LOG.slot],td:wkTD(l),rtd:+l[LOG.rtd]||0,rectd:+l[LOG.rectd]||0,ppr:+l[LOG.fppr]||0,core:WK_CORE.has(l[LOG.slot])}))}));
  const have=[...new Set(rows.map(x=>x.w))].sort((a,b)=>a-b);let weeks=have,pending=[];
  if(S===LAST_SE){const G26=Array.isArray(J.games26)&&J.games26.length&&Array.isArray(J.games26[0])&&typeof J.games26[0][1]==='string'?J.games26:null;
    const got={};rows.forEach(x=>{(got[x.w]=got[x.w]||new Set()).add(x.team)});
    weeks=have.filter(w=>{if(G26){const exp=new Set();G26.filter(g=>+g[0]===w).forEach(g=>{exp.add(g[1]);exp.add(g[2])});if(exp.size)return [...exp].every(t=>got[w].has(t))}return w<(J.week||99)});
    pending=have.filter(w=>!weeks.includes(w))}
  return WKC[S]={rows,weeks,pending}}"""
a,b=span("function wkFeat(S){","return WKC[S]={rows,weeks,pending}}")
s=s[:a]+FEAT+s[b:]

HELP = r"""/* every season at once: which signals keep producing scorers (the 'what to trust' board, stacking, positions) */
const WKT={};
function wkTrust(keep,SG,key){if(WKT[key])return WKT[key];
  const R=[];ALL_SE.forEach(se=>{const F=wkFeat(se),ws=new Set(F.weeks);F.rows.forEach(x=>{if(ws.has(x.w)&&keep(x))R.push(x)})});
  const KF=WK_KEY.map(id=>SG.find(s=>s.id===id).f);R.forEach(x=>{x.cs=KF.reduce((c,f)=>c+(f(x)?1:0),0)});
  const hit=a=>a.filter(x=>x.td>0).length,byW={};R.forEach(x=>{const k=x.l[LOG.season]+'|'+x.w;(byW[k]=byW[k]||[]).push(x)});
  const base=R.length?hit(R)/R.length:null,seB={};ALL_SE.forEach(se=>{const r=R.filter(x=>x.l[LOG.season]===se);seB[se]=r.length?hit(r)/r.length:null});
  const posB={};TPOS.forEach(p=>{const r=R.filter(x=>x.pos===p);posB[p]={n:r.length,hr:r.length?hit(r)/r.length:null}});
  const sig=SG.map(sg=>{const m=R.filter(sg.f),k=hit(m),hr=m.length?k/m.length:null,per={},pp={};
    ALL_SE.forEach(se=>{const ms=m.filter(x=>x.l[LOG.season]===se),kk=hit(ms);per[se]={n:ms.length,k:kk,lift:ms.length&&seB[se]?(kk/ms.length)/seB[se]:null}});
    TPOS.forEach(p=>{const mp=m.filter(x=>x.pos===p);pp[p]={n:mp.length,hr:mp.length?hit(mp)/mp.length:null}});
    let qw=0,bw=0;Object.values(byW).forEach(rs=>{const b=hit(rs)/rs.length,mm=rs.filter(sg.f);if(!b||mm.length<Math.max(6,Math.round(rs.length*.04)))return;qw++;const lf=wkR((hit(mm)/mm.length)/b);if(sg.kind==='pos'?lf>=1.1:lf<=.9)bw++});
    const lift=hr!=null&&base?hr/base:null,share=qw?bw/qw:0,lifts=ALL_SE.map(se=>per[se]).filter(p=>p.n>=30).map(p=>p.lift);
    const tier=sg.kind==='pos'?(lift>=1.3&&share>=.75&&lifts.every(v=>v>=1.15)?'trust':lift>=1.1&&share>=.5?'lean':'noise'):(lift<=.85&&share>=.6?'fade':'noise');
    return Object.assign({},sg,{n:m.length,k,hr,lift,per,pp,qw,bw,share,tier})});
  const stack=[0,1,2,3,4,5,6].map(c=>{const m=R.filter(x=>c<6?x.cs===c:x.cs>=6);return {c,n:m.length,k:hit(m),hr:m.length?hit(m)/m.length:null}});
  return WKT[key]={R,sig,base,seB,posB,stack}}
/* the current week, before (or while) it is played: every slot owner's profile, scored by the signals that hold up */
function wkAhead(keepU,TR){const S=LAST_SE,W0=J.week;if(!W0)return [];const cx=wkCtx(S),SG=wkSigs(),KS=WK_KEY.map(id=>SG.find(s=>s.id===id)),TL={};TR.sig.forEach(x=>TL[x.id]=x.lift||1);
  const T=((J.betting||{}).td||[]).filter(r=>+r.week===W0),tdOf=u=>T.find(r=>r.player===u.player&&r.team===u.team)||T.find(r=>r.player===u.player);
  const out=[];UNIVERSE.forEach(u=>{if(!u.grp||!TPOS.includes(u.pos)||u.inj==='-1'||!keepU(u))return;const raw=(J.sched26[u.team]||[])[W0-1]||'';if(!raw||raw==='BYE')return;const opp=raw.replace('@','');
    const L=PLOGS[u.ln||u.player]||[],prev=L.filter(l=>l[LOG.season]<S||(l[LOG.season]===S&&l[LOG.week]<W0)),done=L.find(l=>l[LOG.season]===S&&l[LOG.week]===W0);
    const x=wkPre(prev,S,W0,u.team,opp,u.grp,raw[0]!=='@',cx),on=KS.filter(k=>k.f(x));
    out.push(Object.assign(x,{u,name:u.player,team:u.team,slot:u.dslot||u.slot,raw,on,cs:on.length,score:on.reduce((s,k)=>s+Math.max(0,(TL[k.id]||1)-1),0),t:tdOf(u),done:done?{td:wkTD(done)}:null}))});
  return out.sort((a,b)=>b.score-a.score||b.cs-a.cs)}
function weeklies(){"""
once("function weeklies(){",HELP)

# ---- the page: new sections
once("""  <div class="panel"><h3 id="wkMh"></h3><div id="wkMx"></div></div>
  <details class="panel wkdet">""","""  <div class="panel"><h3 id="wkTrh"></h3><div class="wktrust" id="wkTrust" data-mg="1"></div></div>
  <div class="wk2b"><div class="panel"><h3 id="wkStkh"></h3><div id="wkStack"></div></div><div class="panel"><h3 id="wkPosh"></h3><div class="wkpos4" id="wkPos4" data-mg="1"></div></div></div>
  <div class="panel"><h3 id="wkAh"></h3><div class="wkahead" id="wkAhead"></div></div>
  <div class="panel"><h3 id="wkMh"></h3><div id="wkMx"></div></div>
  <details class="panel wkdet">""")
once("['wkTiles','wkBars','wkPlay','wkSeason','wkMx','wkPl'].forEach(i=>$('#'+i).innerHTML='')","['wkTiles','wkBars','wkPlay','wkSeason','wkMx','wkPl','wkTrust','wkStack','wkPos4','wkAhead'].forEach(i=>$('#'+i).innerHTML='')")
# grouped bars
once("""    const pos=q.filter(s=>s.kind==='pos').sort((a,b)=>(b.n>=st.minN)-(a.n>=st.minN)||b.hr-a.hr),neg=q.filter(s=>s.kind==='neg').sort((a,b)=>a.hr-b.hr);""",
     """    const GO=['form','role','game','matchup','stack','fade'],byG=g=>q.filter(s=>s.g===g).sort((a,b)=>(b.n>=st.minN)-(a.n>=st.minN)||(g==='fade'?a.hr-b.hr:b.hr-a.hr));""")
once("""    $('#wkBars').innerHTML=pos.map(bar).join('')+(neg.length?`<div class="wkgap">fades — players expected to score less · green = they did</div>${neg.map(bar).join('')}`:'');""",
     """    $('#wkBars').innerHTML=GO.map(g=>{const L=byG(g);return L.length?`<div class="wkgap">${WK_GL[g]}</div>${L.map(bar).join('')}`:''}).join('');""")
# the new sections, right before the heatmap
once("""    const rows=SS.filter(r=>r.kind==='pos').sort((a,b)=>(b.hr??-1)-(a.hr??-1))""","""    /* ---- what to trust: every season at once ---- */
    const TR=wkTrust(keep,SG,[...wkLive].sort().join(',')+'|'+[...(G.pos||[])].sort().join(','));
    const TS=TR.sig.filter(x=>x.n>=30),dot=v=>`<i class="sd" style="background:${v==null?'var(--edge2)':wkR(v)>=1.1?'var(--green)':wkR(v)<=.9?'var(--red)':'#8b98a5'}"></i>`;
    const TCOL=[['trust','trust','beat the field in 75%+ of weeks, 1.3×+ overall','g'],['lean','lean on','helps more often than not','a'],['fade','fade','players carrying it score less — reliably','c'],['noise','ignore','no better than the field','d']];
    $('#wkTrh').innerHTML=`what to trust — every season <span class="f">${ALL_SE[0]}–${ALL_SE[ALL_SE.length-1]} · ${TR.R.length.toLocaleString()} player-games · field ${wkPct(TR.base)} · dots = each season (green beat the field) · hover a chip for the detail</span>`;
    $('#wkTrust').innerHTML=TCOL.map(([t,lbl,tip,c])=>{const L=TS.filter(x=>x.tier===t).sort((a,b)=>t==='fade'?a.lift-b.lift:b.lift-a.lift);
      return `<div class="wktcol ${c}"><h4 title="${esc(tip)}">${lbl} <b>${L.length}</b></h4>${L.map(x=>`<div class="wktc" title="${esc(`${x.long} · ${x.k.toLocaleString()} of ${x.n.toLocaleString()} scored (${wkPct(x.hr)}) · beat the field ${x.bw} of ${x.qw} weeks · `+ALL_SE.map(se=>`${se} ${wkX(x.per[se].lift)}`).join(' · '))}"><span class="l">${x.lbl}</span><b style="color:${col(x,x.lift)}">${wkX(x.lift)}</b><span class="sds">${ALL_SE.map(se=>dot(x.per[se].n>=30?x.per[se].lift:null)).join('')}</span></div>`).join('')||'<span class="mini dim">none</span>'}</div>`}).join('');
    /* ---- stacking: hit rate by how many core signals a player carried ---- */
    const smx=Math.max(.5,...TR.stack.map(x=>x.hr||0))*1.08;
    $('#wkStkh').innerHTML=`the more signals, the more touchdowns <span class="f">all seasons · core signals carried going in</span>`;
    $('#wkStack').innerHTML=TR.stack.filter(x=>x.n).map(x=>{const l=TR.base&&x.hr!=null?x.hr/TR.base:null,c=l==null?'#8b98a5':wkR(l)>=1.1?'var(--green)':wkR(l)<=.9?'var(--red)':'#8b98a5';
      return `<div class="wkb" title="${x.k} of ${x.n} scored"><span class="l">${x.c}${x.c===6?'+':''} signal${x.c===1?'':'s'}</span><span class="t"><i style="width:${(100*(x.hr||0)/smx).toFixed(1)}%;background:${c}"></i><u style="left:${(100*TR.base/smx).toFixed(1)}%"></u></span><span class="r"><b style="color:${c}">${wkPct(x.hr)}</b><span class="mini"> ${x.n.toLocaleString()}</span></span></div>`}).join('')
      +`<div class="wkcore">core: ${WK_KEY.map(id=>`<span>${(SG.find(z=>z.id===id)||{}).lbl}</span>`).join('')}</div>`;
    /* ---- best signal per position ---- */
    $('#wkPosh').innerHTML=`what works by position <span class="f">all seasons · the signal with the best hit rate (40+ players)</span>`;
    $('#wkPos4').innerHTML=TPOS.map(p=>{const b=TR.posB[p];const best=TR.sig.filter(x=>x.kind==='pos'&&x.pp[p].n>=40).sort((a,c)=>c.pp[p].hr-a.pp[p].hr)[0];
      return best&&b.hr?wkTile(`${posIcon(p,11)} ${p} · field ${wkPct(b.hr)}`,best.lbl,`<b style="color:var(--green)">${wkPct(best.pp[p].hr)}</b> scored · ${wkX(best.pp[p].hr/b.hr)} · ${best.pp[p].n} players`,'g',true):wkTile(`${p}`,'—','not enough games')}).join('');
    /* ---- the current week: who carries what works ---- */
    const AH=wkAhead(u=>slotOK(wkLive,u.dslot||u.slot)&&inP(u.pos),TR),W0=J.week,dn=AH.filter(x=>x.done).length;
    $('#wkAh').innerHTML=`week ${W0} — who carries what works <span class="f">ranked by the core signals each player carries, weighted by how well each held up · model = anytime-TD chance · ✓ / ✗ once his game is logged${dn?` (${dn} so far)`:''}</span>`;
    $('#wkAhead').innerHTML=AH.slice(0,18).map(x=>{const t=x.t,mp=t&&t.p_model!=null&&t.p_model!==''?+t.p_model:null;
      return `<div class="wka${x.done?(x.done.td>0?' hit':' miss'):''}"><div class="h">${pn(x.name,x.team,true)} ${slotchip(x.u.grp)} <span class="mini">${x.raw[0]==='@'?'@':'vs'} ${tcell(x.opp)}</span>${x.done?`<span class="res">${x.done.td>0?'✓ '+x.done.td+' TD':'✗'}</span>`:''}</div>
        <div class="m"><b class="n">${x.cs}<span>/8</span></b><span class="tags">${x.on.map(k=>`<i title="${esc(k.long)}">${WK_AB[k.id]||k.lbl}</i>`).join('')}</span></div>
        <div class="f2">${mp!=null?`model <b>${Math.round(100*mp)}%</b>`:'<span class="dim">no model line</span>'}${t&&t.price!=null?` · ${mlTxt(+t.price)}${t.book?' <span class="mini">'+esc(t.book)+'</span>':''}`:''}${x.imp!=null?` · implied <b style="color:${x.imp>=24?'var(--green)':x.imp<18?'var(--red)':'var(--txt)'}">${x.imp.toFixed(1)}</b>`:''}</div></div>`}).join('')||'<p class="mini dim">no schedule for the current week</p>';
    const rows=SS.filter(r=>r.kind==='pos').sort((a,b)=>(b.hr??-1)-(a.hr??-1))""")

CSS = """
/* ---- v20 Weeklies: what to trust · stacking · positions · the week ahead ---- */
.wktrust{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}@media(max-width:1100px){.wktrust{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:760px){.wktrust{grid-template-columns:1fr!important}}
.wktcol{background:rgba(255,255,255,.015);border:1px solid var(--edge);border-top:2px solid var(--edge2);border-radius:8px;padding:8px;min-width:0}
.wktcol.g{border-top-color:var(--green)}.wktcol.a{border-top-color:var(--amber)}.wktcol.c{border-top-color:var(--cyan,#61dcff)}.wktcol.d{border-top-color:#55606a}
.wktcol h4{margin:0 0 6px;font:600 10px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2);display:flex;gap:6px}.wktcol h4 b{font:700 11px var(--mono);color:var(--txt)}
.wktc{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px;align-items:center;padding:4px 2px;border-bottom:1px dashed var(--edge);font-size:12px}.wktc:last-child{border-bottom:0}
.wktc .l{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--txt)}.wktc b{font:700 11.5px var(--mono)}
.sds{display:inline-flex;gap:3px}.sd{display:inline-block;width:8px;height:8px;border-radius:50%}
.wk2b{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;align-items:start}@media(max-width:1150px){.wk2b{grid-template-columns:1fr}}.wk2b>.panel{margin:0 0 12px}
.wkpos4{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.wkcore{margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;align-items:center;font:600 9.5px var(--ui);letter-spacing:.06em;text-transform:uppercase;color:var(--dim2)}.wkcore span{font:500 10.5px var(--ui);letter-spacing:0;text-transform:none;color:var(--dim);border:1px solid var(--edge2);border-radius:10px;padding:1px 7px}
.wkahead{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:8px}
.wka{background:rgba(255,255,255,.02);border:1px solid var(--edge);border-left:3px solid var(--edge2);border-radius:7px;padding:7px 9px;min-width:0;display:flex;flex-direction:column;gap:5px}
.wka.hit{border-left-color:var(--green)}.wka.miss{border-left-color:var(--red);opacity:.75}
.wka .h{display:flex;align-items:center;gap:5px;font-size:12.5px;white-space:nowrap;overflow:hidden}.wka .h .pp{font-weight:600}.wka .res{margin-left:auto;font:700 11px var(--mono)}.wka.hit .res{color:var(--green)}.wka.miss .res{color:var(--red)}
.wka .m{display:flex;align-items:center;gap:8px}.wka .n{font:700 20px/1 var(--mono);color:var(--green)}.wka .n span{font-size:11px;color:var(--dim2);font-weight:500}
.wka .tags{display:flex;flex-wrap:wrap;gap:3px}.wka .tags i{font-style:normal;font:600 9.5px var(--mono);color:var(--green);border:1px solid #00c85355;border-radius:3px;padding:0 4px;line-height:15px}
.wka .f2{font-size:11px;color:var(--dim)}.wka .f2 b{font-family:var(--mono);color:var(--txt)}"""
once("@media(max-width:760px){.wkb{grid-template-columns:118px minmax(0,1fr) 72px;gap:6px;font-size:11.5px}.wklg{margin-left:6px}}",
     "@media(max-width:760px){.wkb{grid-template-columns:118px minmax(0,1fr) 72px;gap:6px;font-size:11.5px}.wklg{margin-left:6px}}"+CSS)
# the bar chart's first group header shouldn't carry the divider line
once(".wkgap{font:600 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2);margin:10px 0 4px;border-top:1px dashed var(--edge);padding-top:9px}",
     ".wkgap{font:600 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2);margin:10px 0 4px;border-top:1px dashed var(--edge);padding-top:9px}#wkBars>.wkgap:first-child{border-top:0;margin-top:0;padding-top:0}")
# note
i=s.index(" weeklies:['v19',");j=s.index("\n",i);line=s[i:j];tail='});' if line.rstrip().endswith('});') else ''
s=s[:i]+" weeklies:['v20','built out from a three-season study: new signals (volume, team TD share, career TD rate, a defense that just gave his slot TDs, big underdogs), a what-to-trust board, the stacking chart, best signal by position and this week\\'s players who carry what works']"+tail+s[j:]
open(T,'w',encoding='utf-8').write(s)
print('v20 weeklies patched')
