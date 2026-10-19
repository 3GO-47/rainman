"""v22 — refine Weeklies + TD Picks, player card at a glance.

  * Player pop-up: a block at the top of every player card — tiles (projection, this week's TD chance, how soft the opponent is
    for his slot, his season, his role) + one table: this season / last 3 / every scraped game / head-to-head vs this week's
    opponent / what the opponent allows his slot this season and in the site's blend, colour-graded, + his next four opponents.
  * Weeklies: the week ahead now comes from the TD Picks model (one ranking on the site, not two) with the core-signal tags kept;
    the lookback grades the model's own top ten for the chosen week (backtest weeks, then live locked picks).
  * TD Picks: equal-length position columns with show more, locked / ✓ / ✗ on each card, live weeks in the track record
    (outlined) with counts and season marks, the record reworded for lock-at-kickoff, a warning when a game has no line yet.

Usage: python scripts/patch_v22.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v22: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# ------------------------------------------------------------------ CSS
rep(r'''.tpled{margin:0 0 10px}''', r'''.tpc .rs{font:700 10.5px var(--mono);margin-left:6px}.tpc .rs.w{color:var(--green)}.tpc .rs.l{color:var(--red)}.tpc .rs.k{color:var(--dim2);font-weight:500;border:1px solid var(--edge2);border-radius:3px;padding:0 4px}
.tpmore{display:flex;justify-content:center;margin-top:8px}.tpmore button{font-size:11px;padding:3px 14px}
.tpwk .b s{text-decoration:none;font:600 8.5px var(--mono);color:var(--dim);text-align:center;margin-bottom:1px}.tpwk .b.ns{border-left:1px dashed var(--edge2);padding-left:2px}.tpwk .b em.se{top:-3px;bottom:auto;left:4px;right:auto;text-align:left;font:600 8.5px var(--mono);color:var(--dim2)}.tpwk .b.lv i{outline:1px solid var(--txt);outline-offset:-1px}
.wkpc.k{border-style:dashed;border-color:var(--dim)}
.wkmd{display:grid;grid-template-columns:minmax(0,600px) minmax(0,1fr);gap:10px;align-items:center}.wkmdk{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}@media(max-width:1200px){.wkmd{grid-template-columns:1fr}}@media(max-width:760px){.wkmdk{grid-template-columns:repeat(2,minmax(0,1fr))}}
h3 .lk[data-go]{margin-left:8px;font:600 10.5px var(--ui);padding:1px 9px;vertical-align:1px}
.ppg{margin:4px 0 10px}.ppk{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:6px;margin:6px 0}.ppk .wkt{padding:7px 9px}.ppk .wkt .v{font-size:19px}
.ppwhy{display:flex;flex-wrap:wrap;gap:3px;margin:0 0 6px}.ppwhy i{font-style:normal;font-size:10.5px;color:var(--dim);border:1px solid var(--edge2);border-radius:3px;padding:0 5px;line-height:16px}.ppwhy i.risk{color:var(--red);border-color:#ff525255}
#ppModal table.ppgt{width:100%;margin-top:2px}#ppModal table.ppgt td,#ppModal table.ppgt th{text-align:right}#ppModal table.ppgt td:first-child,#ppModal table.ppgt th:first-child{text-align:left;white-space:nowrap}
#ppModal table.ppgt td.up{color:var(--green);font-weight:700;background:color-mix(in srgb,var(--green) 10%,transparent)}#ppModal table.ppgt td.dn{color:var(--red);background:color-mix(in srgb,var(--red) 8%,transparent)}
#ppModal table.ppgt tr.all td{color:var(--dim)}#ppModal table.ppgt tr.h2h td:first-child{color:#4dd0e1;font-weight:600}#ppModal table.ppgt tr.opp td{background:rgba(77,208,225,.05)}#ppModal table.ppgt .badge{font-size:9.5px;margin-left:2px}
.ppnx{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin:0 0 6px}.ppnx0{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--edge2);border-radius:12px;padding:1px 8px;font-size:11px}
.tpled{margin:0 0 10px}''')

# ------------------------------------------------------------------ player pop-up: the at-a-glance block
rep(r'''window.playerPop=function(n){''', r'''/* ---------- player card, at a glance (v22): season · last 3 · every game · head-to-head · what this defense allows his slot ---------- */
const PPG_CACHE={};
function ppOppTable(grp,C,val){const se=LAST_SE,key=se+'|'+grp+'|'+C.map(c=>c[0]).join();if(PPG_CACHE[key])return PPG_CACHE[key];
  const games={},sums={};J.logs.forEach(l=>{if(l[LOG.season]!==se)return;const d=l[LOG.opp];(games[d]=games[d]||new Set()).add(l[LOG.week]);
    if(SLOTG(l[LOG.slot])!==grp)return;const o=sums[d]=sums[d]||{};C.forEach(([k])=>o[k]=(o[k]||0)+val(l,k))});
  const A={};Object.keys(games).forEach(d=>{const g=games[d].size,o=sums[d]||{};A[d]={g};C.forEach(([k])=>A[d][k]=g?(o[k]||0)/g:null)});
  const ds=Object.keys(A),rk={};ds.forEach(d=>rk[d]={});C.forEach(([k])=>ds.slice().sort((a,b)=>(A[b][k]??-1)-(A[a][k]??-1)).forEach((d,i)=>rk[d][k]=i+1));
  return PPG_CACHE[key]={A,rk,nD:ds.length,se}}
function ppGlance(n,team,slot,grp,opp,oppRaw,L){
  if(!grp||grp==='D/ST')return '';
  const pos=grp==='QB'?'QB':grp.slice(0,2);
  const C=pos==='QB'?[['py','pass yds'],['ptd','pass TD'],['ry','rush yds'],['rtd','rush TD'],['pr','pass+rush'],['ppr','PPR']]
    :pos==='RB'?[['ra','carries'],['ry','rush yds'],['tgt','targets'],['rec','rec'],['recy','rec yds'],['rr','rush+rec'],['td','TD'],['ppr','PPR']]
    :[['tgt','targets'],['rec','rec'],['recy','rec yds'],['td','TD'],['ppr','PPR']];
  const IX={py:LOG.py,ptd:LOG.ptd,ra:LOG.ra,ry:LOG.ry,rtd:LOG.rtd,tgt:LOG.tgt,rec:LOG.rec,recy:LOG.recy,ppr:LOG.fppr},nz=v=>+v||0;
  const val=(l,k)=>k==='pr'?nz(l[LOG.py])+nz(l[LOG.ry]):k==='rr'?nz(l[LOG.ry])+nz(l[LOG.recy]):k==='td'?(pos==='QB'?nz(l[LOG.ptd])+nz(l[LOG.rtd]):nz(l[LOG.rtd])+nz(l[LOG.rectd])):nz(l[IX[k]]);
  const avg=(A,k)=>A.length?A.reduce((s2,l)=>s2+val(l,k),0)/A.length:null;
  const TDK={td:1,ptd:1,rtd:1},fmt=(v,k)=>v==null?'<span class="dim">—</span>':(TDK[k]?v.toFixed(2):v.toFixed(1));
  const CS=L.length?Math.max(...L.map(l=>l[LOG.season])):LAST_SE,SEA=L.filter(l=>l[LOG.season]===CS),L3=SEA.slice(-3),VS=opp?L.filter(l=>l[LOG.opp]===opp):[];
  const span=`${ALL_SE[0]}–${String(CS).slice(2)}`,base={};C.forEach(([k])=>base[k]=avg(L,k));
  const tone=(v,b)=>v==null||b==null?'':b<.05?(v>=.1?'up':''):v>=b*1.15?'up':v<=b*.85?'dn':'';
  const prow=(lab,A,cls,tip)=>A.length?`<tr class="${cls||''}"><td title="${esc(tip||'')}">${lab}</td><td class="n" data-v="${A.length}">${A.length}</td>${C.map(([k])=>{const v=avg(A,k);return `<td class="n ${cls==='all'?'':tone(v,base[k])}" data-v="${v??''}">${fmt(v,k)}</td>`}).join('')}</tr>`:'';
  const O=opp?ppOppTable(grp,C,val):null,oa=O&&O.A[opp];
  const D=opp&&J.dvp&&J.dvp.combined&&J.dvp.combined[opp],SK={};(J.groupStats[grp]||[]).forEach(st=>{if(grp!=='QB'&&!st.startsWith(grp))return;const k=/P\+R$/.test(st)?'pr':/ PY$/.test(st)?'py':st==='P TD'?'ptd':st==='QB TD'?'rtd':/ RY$/.test(st)?'ry':/RecY$/.test(st)?'recy':/Recep$/.test(st)?'rec':/TD$/.test(st)?'td':null;if(k&&C.some(c=>c[0]===k))SK[k]=st});
  const orow=oa?`<tr class="opp"><td title="what ${opp} has given up per game to the ${grp} slot in ${O.se} · badge = its rank among ${O.nD} defenses, 1 = gives up the most">${opp} allows · ${O.se}</td><td class="n" data-v="${oa.g}">${oa.g}</td>${C.map(([k])=>`<td class="n" data-v="${oa[k]??''}">${fmt(oa[k],k)} ${badge(O.rk[opp][k])}</td>`).join('')}</tr>`:'';
  const brow=D&&Object.keys(SK).length?`<tr class="opp"><td title="the site's blended DvP (${J.blend||''}) — the numbers the Matchups and DvP tabs rank on">${opp} allows · blend</td><td class="n dim">—</td>${C.map(([k])=>{const st=SK[k]&&D.stats[SK[k]];return `<td class="n" data-v="${st?st.avg:''}">${st?(+st.avg).toFixed(TDK[k]?2:1)+' '+badge(st.rank):'<span class="dim">—</span>'}</td>`}).join('')}</tr>`:'';
  const tbl=L.length||oa?`<table class="fx ppgt"><thead><tr><th>per game</th><th>G</th>${C.map(c=>`<th>${c[1]}</th>`).join('')}</tr></thead><tbody>
     ${prow(CS+' season',SEA,'','his per-game average this season')}${prow('last 3',L3,'','his last three games')}${prow(span+' all',L,'all','every scraped game — the yardstick the green / red is measured against')}
     ${VS.length?prow(`vs ${opp} · H2H`,VS,'h2h',`his ${VS.length} game${VS.length>1?'s':''} against ${opp}`):opp&&L.length?`<tr class="h2h"><td>vs ${opp} · H2H</td><td class="n dim">0</td><td colspan="${C.length}" class="dim" style="text-align:left">never faced them in ${span}</td></tr>`:''}
     ${orow}${brow}</tbody></table>
     <p class="mini" style="margin:3px 0 6px">green / red = 15%+ above / below his ${span} average${opp?` · badges = where ${opp} ranks among ${O?O.nD:NT} defenses, 1 = gives up the most`:''}</p>`:'';
  const u=UNIVERSE.find(x=>x.player===n&&x.team===team),pr=u?projection(u):null,TP=J.tdpicks,tp=TP&&TP.picks.find(x=>x.n===n&&x.t===team);
  const defs=J.dvp&&J.dvp.combined?Object.keys(J.dvp.combined).map(t2=>({t2,v:(J.dvp.combined[t2].comps||{})[grp]})).filter(d=>d.v!=null).sort((a,b)=>a.v-b.v):[];
  const mr=t=>{const i=defs.findIndex(d=>d.t2===t);return i<0?null:i+1};
  const r0=opp?mr(opp):null,ug=USG[n],sp=SEA.length?avg(SEA,'ppr'):null,sk=SEA.filter(l=>nz(l[LOG.rtd])+nz(l[LOG.rectd])>0).length;
  const sg=v=>(v>0?'+':'')+v;
  const tiles=[
    pr?wkTile('projection',`${pr.p.toFixed(1)}<span class="dim" style="font-size:12px"> PPR</span>`,`range ${pr.floor.toFixed(1)}–${pr.ceil.toFixed(1)}`,'',true):'',
    tp?wkTile(`wk ${TP.week} TD chance`,`${Math.round(100*tp.p)}%${tp.inj==='-1'?' <span class="injm1">OUT</span>':tp.inj==='0'?' <span class="inj0">Q</span>':''}`,`${tp.tier==='long'?'longshot':tp.tier} · fair ${sg(tp.fair)}${tp.price!=null?` · ${esc(tp.book||'')} ${sg(tp.price)}`:''}`,tp.inj==='-1'?'r':tp.p>=.4?'g':tp.p<.2?'r':'',true):'',
    r0?wkTile(`${opp} vs ${grp}s`,`<span class="badge" style="${gradeStyle(r0,defs.length)}">#${r0}</span>`,`of ${defs.length} · 1 = softest`,r0<=8?'g':r0>defs.length-8?'r':'',true):'',
    sp!=null?wkTile(`${CS} season`,`${sp.toFixed(1)}<span class="dim" style="font-size:12px"> PPR/g</span>`,pos==='QB'?`${avg(SEA,'ptd').toFixed(1)} pass TD a game`:`TD in ${sk} of ${SEA.length} games`,'',true):'',
    ug?wkTile(`${USG._se} role`,`${Math.round(100*ug.snp)}%`,`snaps${ug.tsh!=null?` · ${Math.round(100*ug.tsh)}% tgt share`:''}`,'',true):''
  ].filter(Boolean);
  const wk0=G.week||J.week,S26=(J.sched26&&J.sched26[team])||[],nx=[];
  for(let w=wk0+1;w<=Math.min(NWK,wk0+4);w++){const raw=S26[w-1];if(!raw)continue;const o=raw.replace('@',''),r=raw==='BYE'?null:mr(o);
    nx.push(raw==='BYE'?`<span class="ppnx0 dim">wk ${w} bye</span>`:`<span class="ppnx0" title="${o} ranks #${r||'?'} of ${defs.length} vs ${grp}s · 1 = softest">wk ${w} ${raw[0]==='@'?'@':'vs'} ${tcell(o)}${r?` <span class="badge" style="${gradeStyle(r,defs.length)}">${r}</span>`:''}</span>`)}
  return `<div class="ppg">${tiles.length?`<div class="ppk" data-mg="1">${tiles.join('')}</div>`:''}
    ${tp&&((tp.why||[]).length||tp.risk)?`<div class="ppwhy">${(tp.why||[]).map(w=>`<i>${esc(w)}</i>`).join('')}${tp.risk?`<i class="risk">${esc(tp.risk)}</i>`:''}</div>`:''}
    ${tbl}${nx.length?`<div class="ppnx"><span class="mini">next ${nx.length} · rank vs ${grp}s:</span>${nx.join('')}</div>`:''}</div>`}
window.playerPop=function(n){''')
rep(r'''   ${opp?`<p class="mini" style="margin:4px 0 8px">${schemeLine(opp)}''', r'''   ${ppGlance(n,team,slot,grp,opp,oppRaw,L)}
   ${opp?`<p class="mini" style="margin:4px 0 8px">${schemeLine(opp)}''')
rep(r'''   ${L.length?`<p class="mini">averages per game</p>''', r'''   ${L.length?`<p class="mini">averages per game, by season</p>''')

# ------------------------------------------------------------------ Weeklies: the model's week ahead + a graded scorecard
rep(r'''function wkAhead(keepU,TR){const S=LAST_SE,W0=J.week;if(!W0)return [];''', r'''function wkAhead(keepU,TR,W0){const S=LAST_SE;W0=W0||J.week;if(!W0)return [];''')
rep(r'''  <div class="wktiles" id="wkTiles" data-mg="1"></div>
  <div class="wkmain">''', r'''  <div class="wktiles" id="wkTiles" data-mg="1"></div>
  <div class="panel" id="wkMdP" hidden><h3 id="wkMdh"></h3><div id="wkMd"></div></div>
  <div class="wkmain">''')
rep(r'''    /* ---- the bars: every signal's hit rate against the field line ---- */''', r'''    /* ---- the TD Picks model's own call for this week, graded (v22) ---- */
    (()=>{const TPk=J.tdpicks,box=$('#wkMd'),hd=$('#wkMdh'),pnl=$('#wkMdP');if(!box)return;
      const rec=TPk&&(TPk.record||[]).find(r=>r.s===S&&r.w===W&&r.top10&&r.top10[1]),bt=TPk&&TPk.bt&&TPk.bt.top&&TPk.bt.top[S+'-'+W],bw=TPk&&TPk.bt&&(TPk.bt.weeks||[]).find(x=>x[0]===S&&x[1]===W);
      if(!rec&&!bt){pnl.hidden=true;return}pnl.hidden=false;
      const L=rec?rec.rows.filter(x=>x[9]==='W'||x[9]==='L').map(x=>({n:x[0],t:x[1],b:x[3],p:x[4],hit:x[9]==='W'})):bt.map(x=>({n:x[0],t:x[1],b:x[2],p:x[3],hit:!!x[4]}));
      const top=L.slice(0,10),k=top.filter(x=>x.hit).length,fld=bw&&bw[2]?bw[3]/bw[2]:st.base,ps={};
      L.forEach(x=>{const p=String(x.b).startsWith('QB')?'QB':String(x.b).slice(0,2);(ps[p]=ps[p]||[]).push(x)});
      const p3=['QB','RB','WR','TE'].map(p=>(ps[p]||[]).slice().sort((a,b)=>b.p-a.p).slice(0,3)).flat(),k3=p3.filter(x=>x.hit).length;
      const lk=top.filter(x=>x.p>=.5),lkk=lk.filter(x=>x.hit).length,miss=top.filter(x=>!x.hit).sort((a,b)=>b.p-a.p)[0];
      hd.innerHTML=`how the TD Picks model did — week ${W} <span class="f">${rec?'live picks, locked at kickoff':'picked before kickoff: refit on earlier weeks only, then graded'} · ✓ scored · ✗ didn't</span><button class="lk" data-go="tdpicks" title="open the TD Picks tab">TD Picks →</button>`;
      box.innerHTML=`<div class="wkmd"><div class="wkmdk" data-mg="1">${wkTile('top ten',`${k}<span class="dim"> / ${top.length}</span>`,`field ${wkPct(fld)}`,k>=6?'g':k<=3?'r':'',true)}${p3.length?wkTile('top 3 a position',`${k3}<span class="dim"> / ${p3.length}</span>`,`${wkPct(k3/p3.length)} scored`,k3/p3.length>=.5?'g':k3/p3.length<.3?'r':'',true):''}${lk.length?wkTile('rated 50%+',`${lkk}<span class="dim"> / ${lk.length}</span>`,'locks scored',lkk/lk.length>=.5?'g':'r',true):wkTile('rated 50%+','—','no lock that week','',true)}${miss?wkTile('biggest miss',esc(pshort(miss.n)),`rated ${wkPct(miss.p)} · no TD`,'r',true):''}</div>
        <div class="wkpcs">${top.map(x=>`<span class="wkpc ${x.hit?'w':'l'}">${pn(x.n,x.t,true)}<i>${wkPct(x.p)}</i><b>${x.hit?'✓':'✗'}</b></span>`).join('')}</div></div>`;
      const g=hd.querySelector('[data-go]');if(g)g.onclick=()=>go('tdpicks')})();
    /* ---- the bars: every signal's hit rate against the field line ---- */''')
rep(r'''    const AH=wkAhead(u=>slotOK(wkLive,u.dslot||u.slot)&&inP(u.pos),TR),W0=J.week,dn=AH.filter(x=>x.done).length;
    $('#wkAh').innerHTML=''', r'''    const TPk=J.tdpicks,AH=wkAhead(u=>slotOK(wkLive,u.dslot||u.slot)&&inP(u.pos),TR,TPk?TPk.week:null),W0=TPk?TPk.week:J.week,dn=AH.filter(x=>x.done).length;
    if(TPk){const AM={};AH.forEach(x=>AM[x.name+'|'+x.team]=x);
      const PK=TPk.picks.filter(x=>x.inj!=='-1'&&slotOK(wkLive,x.s==='WR4+'?'WR4':x.s)&&inP(x.pos)),dn2=PK.filter(x=>x.res!=null).length;
      const TC={lock:'var(--green)',strong:'#7dd87d',solid:'var(--amber)',long:'#6db3e8',low:'var(--dim)'},sg=v=>(v>0?'+':'')+v;
      $('#wkAh').innerHTML=`week ${W0} — the model's top five per position <span class="f">chance to score, from TD Picks · green tags = the core signals he carries going in · ✓ / ✗ once his game is logged${dn2?` (${dn2} so far)`:''}</span><button class="lk" data-go="tdpicks" title="open the full board">full board →</button>`;
      const card2=x=>{const a=AM[x.n+'|'+x.t];return `<div class="wka${x.res!=null?(x.res>0?' hit':' miss'):''}"><div class="h">${pn(x.n,x.t,true)} ${slotchip(x.b)} <span class="mini">${x.h?'vs':'@'} ${tcell(x.o)}</span>${x.res!=null?`<span class="res">${x.res>0?'✓ '+x.res+' TD':'✗'}</span>`:''}</div>
        <div class="m"><b class="n" style="color:${TC[x.tier]||'var(--txt)'}">${Math.round(100*x.p)}%</b><span class="tags">${a?a.on.map(k=>`<i title="${esc(k.long)}">${WK_AB[k.id]||k.lbl}</i>`).join(''):''}</span></div>
        <div class="f2">${x.tier==='long'?'longshot':x.tier} · fair <b>${sg(x.fair)}</b>${x.price!=null?` · ${esc(x.book||'')} <b>${sg(x.price)}</b>`:''}${x.imp!=null?` · implied <b style="color:${x.imp>=24?'var(--green)':x.imp<18?'var(--red)':'var(--txt)'}">${(+x.imp).toFixed(1)}</b>`:''}</div></div>`};
      $('#wkAhead').innerHTML=TPOS.filter(p=>inP(p)).map(p=>{const L=PK.filter(x=>x.pos===p).sort((a,b)=>b.p-a.p);return `<div class="wkacol"><h4>${posIcon(p,11)} ${p} <b>${Math.min(5,L.length)}</b><span class="mini">of ${L.length} on the slate</span></h4>${L.slice(0,5).map(card2).join('')||'<span class="mini dim">nobody</span>'}</div>`}).join('');
      const g=$('#wkAh [data-go]');if(g)g.onclick=()=>go('tdpicks');
    }else{
    $('#wkAh').innerHTML=''')
rep(r'''    $('#wkAhead').innerHTML=AH.length?TPOS.filter(p=>inP(p)).map(p=>{const L=AH.filter(x=>x.pos===p);return `<div class="wkacol"><h4>${posIcon(p,11)} ${p} <b>${Math.min(5,L.length)}</b><span class="mini">of ${L.length} on the slate</span></h4>${L.slice(0,5).map(card).join('')||'<span class="mini dim">nobody</span>'}</div>`}).join(''):'<p class="mini dim">no schedule for the current week</p>';''',
    r'''    $('#wkAhead').innerHTML=AH.length?TPOS.filter(p=>inP(p)).map(p=>{const L=AH.filter(x=>x.pos===p);return `<div class="wkacol"><h4>${posIcon(p,11)} ${p} <b>${Math.min(5,L.length)}</b><span class="mini">of ${L.length} on the slate</span></h4>${L.slice(0,5).map(card).join('')||'<span class="mini dim">nobody</span>'}</div>`}).join(''):'<p class="mini dim">no schedule for the current week</p>';
    }''')

# ------------------------------------------------------------------ TD Picks tab
rep(r'''  const live=new Set(TD_SLOTS);let sortK='p',show='board';''', r'''  const live=new Set(TD_SLOTS);let sortK='p',show='board',more=false;''')
rep(r'''    <span class="note kept">week ${T.week} · depth chart ${T.depth} · built ${T.built}</span>''', r'''    <span class="note kept">week ${T.week} · depth chart ${T.depth} · updated ${T.now?T.now.slice(5)+' ET':T.built}</span>''')
rep(r'''  <div class="panel"><h3 id="tpBh"></h3><div class="tpcols" id="tpCols" data-mg="1"></div></div>''', r'''  <div class="panel"><h3 id="tpBh"></h3><div class="tpcols" id="tpCols" data-mg="1"></div><div class="tpmore"><button id="tpMore"></button></div></div>''')
rep(r'''  <div class="wk2b"><div class="panel"><h3>track record — every week of 2025–26, scored blind <span class="f">the model is refit before each week on games it has already seen, then graded on that week</span></h3><div id="tpRec"></div></div>''',
    r'''  <div class="wk2b"><div class="panel"><h3>track record — every week since 2025, picked before kickoff <span class="f">past weeks: the model is refit on games it has already seen, then graded · live weeks: picks locked at kickoff</span></h3><div id="tpRec"></div></div>''')
rep(r'''<span class="st">${trk(x)}</span></div>
      <div class="m"><b class="pp2">''', r'''${x.res!=null?`<span class="rs ${x.res>0?'w':'l'}">${x.res>0?'✓ '+x.res+' TD':'✗ no TD'}</span>`:x.lk?'<span class="rs k" title="his game has kicked off — this pick is locked in the record">locked</span>':''}<span class="st">${trk(x)}</span></div>
      <div class="m"><b class="pp2">''')
rep(r'''      +wkTile('frozen record',rg?`${rw}-${rg-rw}`:'—',rg?`${pct(rw/rg)} of frozen picks scored`:`week ${T.week} picks frozen ${(T.record||[]).length?(T.record[T.record.length-1].frozen||'').slice(5):''} · graded as games log`);''',
    r'''      +wkTile('live record',rg?`${rw}-${rg-rw}`:'—',rg?`${pct(rw/rg)} of locked picks scored`:`week ${T.week}: picks update until each kickoff, then lock`);''')
rep(r'''    const N={QB:5,RB:10,WR:12,TE:7};''', r'''    const N=more?16:8;$('#tpMore').textContent=more?'show 8 a position':'show 16 a position';''')
rep(r'''· ★ sends it to Tracking</span>`;''', r'''· ★ sends it to Tracking</span>${(T.nolines||[]).length?` <span class="note kept" style="color:var(--amber)">no line yet for ${T.nolines.join(', ')} — implied total assumed 22 until one posts</span>`:''}`;''')
rep(r'''<b>${Math.min(N[p],L.length)}</b><span class="mini">of ${L.length}</span></h4>${L.slice(0,N[p]).map(card).join('')''', r'''<b>${Math.min(N,L.length)}</b><span class="mini">of ${L.length}</span></h4>${L.slice(0,N).map(card).join('')''')
rep(r'''    const W=BT.weeks||[];
    $('#tpRec').innerHTML=`<div class="tpwk">${W.map(w=>{const r=w[5]?w[4]/w[5]:0;return `<span class="b" title="${w[0]} wk ${w[1]}: ${w[4]} of the top ${w[5]} scored · field ${pct(w[3]/w[2])}"><i style="height:${Math.max(4,Math.round(100*r))}%;background:${r>=.6?'var(--green)':r>=.4?'var(--amber)':'var(--red)'}"></i><em>${w[1]}</em></span>`}).join('')}</div>
      <div class="mini" style="margin:4px 0 10px">each bar = how many of that week's ten highest-rated players scored · ${BT.top10?BT.top10[0]+' of '+BT.top10[1]:''} overall''',
    r'''    const LV={};(T.record||[]).forEach(r=>{if(r.top10&&r.top10[1]===10)LV[r.s+'-'+r.w]=r});
    const W=(BT.weeks||[]).filter(w=>!LV[w[0]+'-'+w[1]]).map(w=>({s:w[0],w:w[1],k:w[4],n:w[5],f:w[2]?w[3]/w[2]:null,lv:false})).concat(Object.values(LV).map(r=>({s:r.s,w:r.w,k:r.top10[0],n:r.top10[1],f:null,lv:true}))).sort((a,b)=>a.s-b.s||a.w-b.w);
    const k10=W.reduce((a,x)=>a+x.k,0),n10=W.reduce((a,x)=>a+x.n,0);
    $('#tpRec').innerHTML=`<div class="tpwk">${W.map((x,i)=>{const r=x.n?x.k/x.n:0,ns=i===0||W[i-1].s!==x.s;return `<span class="b${x.lv?' lv':''}${ns?' ns':''}" title="${x.s} wk ${x.w}${x.lv?' · live picks':''}: ${x.k} of the top ${x.n} scored${x.f!=null?' · field '+pct(x.f):''}">${ns?`<em class="se">${x.s}</em>`:''}<s>${x.k}</s><i style="height:${Math.max(4,Math.round(100*r))}%;background:${r>=.6?'var(--green)':r>=.4?'var(--amber)':'var(--red)'}"></i><em>${x.w}</em></span>`}).join('')}</div>
      <div class="mini" style="margin:4px 0 10px">each bar = how many of that week's ten highest-rated players scored (number on top) · green = 6 or more · red = 3 or fewer${Object.keys(LV).length?' · outlined = live picks':''} · ${k10} of ${n10} overall''')
rep(r'''    $('#tpLh').innerHTML=`frozen picks <span class="f">written down the first time a week is scored and never re-scored · ✓ scored · ✗ didn't · blank = not played yet</span>`;''',
    r'''    $('#tpLh').innerHTML=`the live record <span class="f">a game's picks update with the latest news until it kicks off, then lock for good · ✓ scored · ✗ didn't · dashed = locked, not graded yet · plain = still updating</span>`;''')
rep(r'''<h4>week ${r.w} <span class="mini">frozen ${r.frozen} · ${r.graded?`${r.wins} of ${r.graded} graded picks scored · top ten ${r.top10[0]}/${r.top10[1]}`:'not graded yet'}</span></h4>''',
    r'''<h4>week ${r.w} <span class="mini">${r.locked||0} of ${r.n} picks locked · last update ${r.frozen} · ${r.graded?`${r.wins} of ${r.graded} graded picks scored${r.top10&&r.top10[1]?` · top ten ${r.top10[0]}/${r.top10[1]}`:''}`:'none graded yet'}</span></h4>''')
rep(r'''.map(x=>`<span class="wkpc ${x[9]==='W'?'w':x[9]==='L'?'l':''}">${pn(x[0],x[1],true)}<i>${pct(x[4])}</i>''', r'''.map(x=>`<span class="wkpc ${x[9]==='W'?'w':x[9]==='L'?'l':x[10]?'k':''}">${pn(x[0],x[1],true)}<i>${pct(x[4])}</i>''')
rep(r'''<p class="mini dim">no frozen week yet</p>''', r'''<p class="mini dim">no live week yet</p>''')
rep(r'''  slotChipsWire('tpSlots',live,render);['tpInj','tpSort'].forEach(i=>$('#'+i).onchange=render);$('#tpQ').oninput=render;''',
    r'''  slotChipsWire('tpSlots',live,render);['tpInj','tpSort'].forEach(i=>$('#'+i).onchange=render);$('#tpQ').oninput=render;$('#tpMore').onclick=()=>{more=!more;render()};''')
rep(r'''record = every week of 2025–26 picked blind, then graded''', r'''record = every week since 2025 picked before kickoff — live picks lock at kickoff''')

rep(r"""x.inj==='0'?' <span class="inj0">Q</span>':x.inj==='-1'?' <span class="injm1">OUT</span>'""",
    r"""x.inj==='0'?` <span class="inj0" title="${esc(x.injn||'questionable')}">Q</span>`:x.inj==='-1'?` <span class="injm1" title="${esc(x.injn||'out')}">OUT</span>`""", 2)

# ------------------------------------------------------------------ notes
rep(r'''const BOOT=[''', r'''Object.assign(NOTES,{
 tdpicks:['v22','picks now update with the latest depth chart, injuries, lines and prices until each game kicks off, then lock — never written after kickoff · ✓ / ✗ / locked on every card · 8 a position (show 16) · live weeks join the track record'],
 weeklies:['v22','the week ahead comes from the TD Picks model (one ranking, not two) with the signal tags kept · new: how the model\'s own top ten did in the week you\'re looking back on'],
});
const BOOT=[''')
open(P, 'w', encoding='utf-8').write(s)
print('patch_v22: template patched')
