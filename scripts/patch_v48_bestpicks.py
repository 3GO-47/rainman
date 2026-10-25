"""v48 — F1 Home → Best Picks: the week's plays in one place.
  1. the card — every frozen pick (picks_all, bet = 1) for the week: game plays (ML · ATS · TOTAL), props, anytime TDs, with the
     model number, the market, the edge and the result as it grades;
  2. anytime TD — the TD Picks board's best for the week, and which other boards agree (First TD top ten at his position,
     Weeklies 4+ core signals, META v2 top-10% on 3+ boards); price and EV when a book posts one; ✓ / ✗ live;
  3. matchup plays — the backtested META recipe's best spots (coverage ≥ 75%), with the reasons;
  4. avoid — META in the bottom band AND the TD model in his position's bottom quarter.
Follows the week picker (past weeks show the card and the TD board graded; META sections are for the live week only) and the
global bar. Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function bestPicks(' in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

rep("   {id:'insights',label:'Insights',desc:'best / worst matchup per role this week, the softest and stingiest defense per slot, schedule strength, volatility',c:'home',sub:'insights'},",
    "   {id:'insights',label:'Insights',desc:'best / worst matchup per role this week, the softest and stingiest defense per slot, schedule strength, volatility',c:'home',sub:'insights'},\n"
    "   {id:'bestpicks',nfl:true,label:'Best Picks',desc:'the week\\'s plays in one place: the frozen card (game plays, props, anytime TDs) graded as it lands, the TD board\\'s best with the boards that agree, the backtested META spots, and the avoids',c:'test',sub:'bestpicks'},")
rep('<div id="test" hidden><div id="wkres" hidden></div>', '<div id="test" hidden><div id="bestpicks" hidden></div><div id="wkres" hidden></div>')
rep("if(it.c==='test'){['wkres','metav2','meta',", "if(it.c==='test'){['bestpicks','wkres','metav2','meta',")
rep("['test',weeklies2],['test',wkGrid2],['test',wkResults],", "['test',weeklies2],['test',wkGrid2],['test',wkResults],['test',bestPicks],")

view = r'''
/* ---------------- v48: BEST PICKS — the week's plays in one place ---------------- */
function bestPicks(){const el=$('#bestpicks');if(!el)return;
  el.innerHTML=`<div class="controls"><span class="mini kept" id="bpN" style="color:var(--dim)"></span></div><div class="wktiles" id="bpTiles"></div><div id="bpCard"></div><div id="bpTd"></div><div class="wk2b"><div id="bpMeta"></div><div id="bpAvoid"></div></div>`;
  const resCell=(r,open)=>r==null||r===''?(open?'<span class="dim" title="in play, no TD yet">· live</span>':'<span class="dim">—</span>'):r==='W'||r>0?`<b style="color:var(--green)">✓${typeof r==='number'&&r>1?r:''}</b>`:r==='P'?'<span class="dim">push</span>':'<b style="color:var(--red)">✗</b>';
  const num=(v,d=1)=>v==null||v===''||isNaN(+v)?'':(+v).toFixed(d);
  const kickTxt=(t,w)=>{const g=gameOf(t,w);return g?`${g[GM.day]} ${g[GM.time]||'TBD'}`:''};
  /* grade a game play from the live score once the game is final (the loop writes the official result later) */
  const liveGrade=p=>{if(!LIVE_TD||!LIVE_TD.scores||!LIVE_TD.games)return null;const g=String(p.team);if(LIVE_TD.games[g]!=='post')return null;const sc=LIVE_TD.scores[g];if(!sc)return null;const [a,h]=g.split('@'),[as,hs]=sc,side=String(p.side||'').trim();
    if(p.type==='ML'){const w=as>hs?a:hs>as?h:null;return w==null?'P':w===side?'W':'L'}
    if(p.type==='TOTAL'){const m=side.match(/^(OVER|UNDER)\s+([\d.]+)/i);if(!m)return null;const t=as+hs,l=+m[2];return t===l?'P':(m[1].toUpperCase()==='OVER')===(t>l)?'W':'L'}
    if(p.type==='ATS'){const m=side.match(/^(\S+)\s*([+-]?[\d.]+)/);if(!m)return null;const tm=m[1],ln=+m[2],mg=tm===a?as-hs:tm===h?hs-as:null;if(mg==null)return null;const v=mg+ln;return v===0?'P':v>0?'W':'L'}
    return null};
  function render(){
    const W=G.week,live=W===J.week;
    /* 1. the card */
    const C=PICKS.filter(p=>+p.week===W&&(p.type==='PROP'||p.type==='TD'?inF(p.team)&&inO(p.player,p.team):(()=>{const [a,h]=String(p.team).split('@');return inF(a)||inF(h)})()));
    const rOf=p=>p.result||(['ML','ATS','TOTAL'].includes(p.type)?liveGrade(p):(p.type==='TD'&&live?(()=>{const lv=liveRes(p.player,p.team);return lv==null?null:lv>0?'W':'L'})():null));
    const grade=L=>{const g=L.map(rOf).filter(r=>r==='W'||r==='L');return {w:g.filter(r=>r==='W').length,n:g.length}};
    const G1=C.filter(p=>['ML','ATS','TOTAL'].includes(p.type)),G2=C.filter(p=>p.type==='PROP').sort((a,b)=>(+b.edge||0)-(+a.edge||0)),G3=C.filter(p=>p.type==='TD').sort((a,b)=>(+b.edge||0)-(+a.edge||0));
    const recTxt=(L,lbl)=>{const g=grade(L);return g.n?`${lbl} ${g.w}-${g.n-g.w}`:`${lbl} ${L.length} open`};
    const gameRows=G1.map(p=>{const lg=p.result?null:liveGrade(p);const r=p.result||lg;const act=p.actual||(lg&&LIVE_TD.scores[p.team]?LIVE_TD.scores[p.team].join('-'):'');return `<tr><td style="text-align:left"><span class="mini dim">${p.type}</span> ${esc(p.team)}</td><td style="text-align:left"><b>${esc(p.side)}</b></td><td data-v="${num(p.model)}">${num(p.model)}</td><td data-v="${num(p.market_ref)}">${num(p.market_ref)} <span class="mini dim">${esc(p.market_src||'')}</span></td><td data-v="${num(p.edge)}" style="color:${+p.edge>=0?'var(--green)':'var(--red)'}">${+p.edge>=0?'+':''}${num(p.edge)}</td><td>${esc(p.frozen_on||'').slice(5)}</td><td data-v="${act}">${esc(act)}</td><td>${resCell(r,!r&&liveOpen(String(p.team).split('@')[0]))}${lg?'<span class="mini dim" title="graded from the live score; the loop writes the official result"> live</span>':''}</td></tr>`}).join('');
    const propRows=G2.map(p=>`<tr><td style="text-align:left">${pn(p.player,p.team,true)}</td><td>${tcell(p.team)}</td><td>${tcell(p.opp)}</td><td style="text-align:left"><b>${esc(p.side)}</b> <span class="mini">${esc(p.market).replace(/_/g,' ')} ${esc(p.line)}</span></td><td data-v="${num(p.model)}">${num(p.model)}</td><td data-v="${num(p.edge)}" style="color:${+p.edge>=0?'var(--green)':'var(--red)'}">${+p.edge>=0?'+':''}${num(p.edge)}%</td><td>${p.price?mlTxt(+p.price):''}</td><td data-v="${p.actual||''}">${p.actual?esc(p.actual):''}</td><td>${resCell(p.result)}</td></tr>`).join('');
    const tdRows=G3.map(p=>{const lv=live?liveRes(p.player,p.team):null;const r=p.result||(lv!=null?(lv>0?'W':'L'):null);return `<tr><td style="text-align:left">${pn(p.player,p.team,true)}</td><td>${tcell(p.team)}</td><td>${tcell(p.opp)}</td><td data-v="${num(p.model)}">${num(p.model,0)}%</td><td data-v="${num(p.market_ref)}">${p.market_ref?num(p.market_ref,0)+'%':''} <span class="mini dim">${esc(p.market_src||'')}</span></td><td data-v="${num(p.edge)}" style="color:${+p.edge>=0?'var(--green)':'var(--red)'}">${+p.edge>=0?'+':''}${num(p.edge)}%</td><td>${p.price?mlTxt(+p.price):''}</td><td>${resCell(r,live&&r==null&&liveOpen(p.team))}</td></tr>`}).join('');
    $('#bpCard').innerHTML=C.length?`<div class="panel"><h3>the card — week ${W} <span class="f">every frozen pick (the model vs the market at freeze, edge, result as it lands) · ${recTxt(G1,'games')} · ${recTxt(G2,'props')} · ${recTxt(G3,'TDs')}</span></h3>
      ${G1.length?`<div class="tscroll"><table class="fx bpt"><thead><tr><th style="text-align:left">game</th><th style="text-align:left">play</th><th>model</th><th>market</th><th>edge</th><th>frozen</th><th>actual</th><th>res</th></tr></thead><tbody>${gameRows}</tbody></table></div>`:''}
      ${G2.length?`<h4 class="thh4">props · ${G2.length}</h4><div class="tscroll"><table class="fx bpt"><thead><tr><th style="text-align:left">player</th><th>tm</th><th>opp</th><th style="text-align:left">play</th><th>model</th><th>edge</th><th>price</th><th>actual</th><th>res</th></tr></thead><tbody>${propRows}</tbody></table></div>`:''}
      ${G3.length?`<h4 class="thh4">anytime TD · ${G3.length}</h4><div class="tscroll"><table class="fx bpt"><thead><tr><th style="text-align:left">player</th><th>tm</th><th>opp</th><th>model</th><th>market</th><th>edge</th><th>price</th><th>res</th></tr></thead><tbody>${tdRows}</tbody></table></div>`:''}</div>`
      :`<div class="panel"><h3>the card — week ${W} <span class="f">no frozen picks for this week${ACT||G.owner?' in the current filter':''}</span></h3></div>`;
    /* 2. anytime TD — the board's best + who agrees */
    const BD=tdBoard(W);let tdTop=[];
    if(BD&&BD.P){const P=BD.P.filter(x=>inF(x.t)&&inP(x.pos)&&inO(x.n,x.t)&&(x.inj!=='-1'||x.res!=null));
      const FT=(live&&J.firstTd&&J.firstTd.week===W?J.firstTd.board:[])||[],MV=live?(window.MV_LAST||[]):[];let WA=[];if(live){try{const SG=wkSigs(),TR=wkTrust(x=>true,SG,'card38');WA=wkAhead(x=>true,TR,W)}catch(e){}}
      const ftRank=x=>{if(!FT.length)return null;const L=FT.filter(b=>b.pos===x.pos).sort((a,b)=>b.p_first-a.p_first);const i=L.findIndex(b=>nmKey(b.player)===nmKey(x.n)&&b.team===x.t);return i<0?null:[i+1,L.length]};
      const byP=P.slice().sort((a,b)=>b.p-a.p);
      tdTop=byP.map(x=>{const ft=ftRank(x),wa=WA.find(a=>a.name===x.n&&a.team===x.t),mv=MV.find(m=>m.u.player===x.n&&m.u.team===x.t);const ag=[];
        if(ft&&ft[0]<=10)ag.push(['1st TD','#'+ft[0]+' of '+ft[1]+' at his position on the First TD board']);if(wa&&wa.cs>=4)ag.push(['WKL '+wa.cs,wa.cs+' of 8 core Weeklies signals']);if(mv&&mv.t10>=3)ag.push(['v2 ×'+mv.t10,'top 10% on '+mv.t10+' META v2 boards']);
        const res=x.res!=null?x.res:(live?liveRes(x.n,x.t):null);
        return Object.assign({},x,{ag,res,open:live&&res==null&&liveOpen(x.t),ko:kickTxt(x.t,W)})});
      const top=tdTop.slice(0,14);
      $('#bpTd').innerHTML=`<div class="panel"><h3>anytime TD — the board's best, week ${W} <span class="f">TD Picks model first; <b>agree</b> = the other boards that also have him high (First TD top ten at his position · Weeklies 4+ core signals · META v2 top-10% on 3+ boards) · price = best posted anytime-TD price, EV against it · ${top.filter(x=>x.res!=null).length?`${top.filter(x=>x.res>0).length} of ${top.filter(x=>x.res!=null).length} graded scored`:'✓ / ✗ as games are played'}</span></h3>
        <div class="tscroll"><table class="fx bpt"><thead><tr><th style="text-align:left">player</th><th>tm</th><th>opp</th><th>kick</th><th title="TD Picks model">TD %</th><th title="the model's fair American odds">fair</th><th>price</th><th title="EV against the posted price">EV</th><th style="text-align:left">agree</th><th>res</th></tr></thead><tbody>
        ${top.map(x=>`<tr><td style="text-align:left">${pn(x.n,x.t,true)}${x.inj==='0'?' <span class="inj0">Q</span>':x.inj==='-1'?' <span class="injm1">OUT</span>':''}</td><td>${tcell(x.t)}</td><td>${x.h?'':'@'}${tcell(x.o)}</td><td class="mini">${esc(x.ko)}</td><td data-v="${x.p}"><span class="badge" style="${gradeStyle(1+(1-x.p)*(NT-1))}">${Math.round(100*x.p)}%</span></td><td>${x.fair!=null?mlTxt(+x.fair):''}</td><td>${x.price!=null?mlTxt(+x.price)+(x.book?' <span class="mini dim">'+esc(x.book)+'</span>':''):'<span class="dim">—</span>'}</td><td data-v="${x.ev??-99}" style="color:${x.ev!=null&&x.ev>0?'var(--green)':'var(--dim)'}">${x.ev!=null?(x.ev>0?'+':'')+(100*x.ev).toFixed(0)+'%':''}</td><td style="text-align:left">${x.ag.map(a=>`<span class="wkpc w" title="${esc(a[1])}">${esc(a[0])}</span>`).join(' ')||'<span class="dim">—</span>'}</td><td>${resCell(x.res,x.open)}</td></tr>`).join('')}</tbody></table></div></div>`}
    else $('#bpTd').innerHTML=`<div class="panel"><h3>anytime TD <span class="f">no TD board for week ${W}</span></h3></div>`;
    /* 3. matchup plays (META, live week) · 4. avoid */
    const M1=live?(window.META_LAST||[]):[];
    if(M1.length){const R=M1.filter(x=>x.opp&&x.meta!=null&&x.cov>=.75&&x.u.inj!=='-1'&&inU(x.u)&&inP(x.pos)&&TD_SLOTS.includes(x.u.dslot||x.u.slot));
      const why=x=>[['ENV',x.c.env,x.env==null?'':x.env.toFixed(1)+' imp'],['FORM',x.c.form,x.form==null?'':(x.form>=0?'+':'')+Math.round(100*x.form)+'%'],['Ψ',x.c.psi,x.psi==null?'':Math.round(x.psi)]].filter(a=>a[1]!=null&&a[1]>=.65).map(a=>`<span class="wkpc w">${a[0]} ${a[2]}</span>`).join(' ');
      const top=R.slice().sort((a,b)=>b.meta-a.meta).slice(0,12),tdOf=x=>{const b=BD&&BD.P?BD.P.find(p=>p.n===x.u.player&&p.t===x.u.team):null;return b?b.p:null};
      const row=x=>{const res=liveRes(x.u.player,x.u.team);return `<tr><td style="text-align:left">${pn(x.u.player,x.u.team,true)}</td><td>${slotchip(x.u.dslot||x.u.slot)}</td><td>${oppcell(x.oppRaw)}</td><td data-v="${x.meta}"><span class="badge" style="${gradeStyle(1+(1-x.meta/100)*(NT-1))}">${Math.round(x.meta)}</span></td><td style="text-align:left">${why(x)||'<span class="dim">—</span>'}</td><td data-v="${tdOf(x)??-1}">${tdOf(x)!=null?Math.round(100*tdOf(x))+'%':''}</td><td>${resCell(res,liveOpen(x.u.team))}</td></tr>`};
      $('#bpMeta').innerHTML=`<div class="panel"><h3>matchup plays — META <span class="f">the backtested recipe's best spots this week (Ψ · FORM · ENV, coverage 75%+) — expected to beat his own baseline, not necessarily to score</span></h3><div class="tscroll"><table class="fx bpt"><thead><tr><th style="text-align:left">player</th><th>slot</th><th>opp</th><th>META</th><th style="text-align:left">why</th><th title="TD Picks model">TD %</th><th>TD</th></tr></thead><tbody>${top.map(row).join('')||'<tr><td colspan="7" class="dim">nothing in view</td></tr>'}</tbody></table></div></div>`;
      const q=(()=>{const byPos={};TPOS.forEach(p=>{const v=(BD&&BD.P?BD.P.filter(x=>x.pos===p):[]).map(x=>x.p).sort((a,b)=>a-b);byPos[p]=v.length?v[Math.floor(v.length*.25)]:null});return byPos})();
      const av=R.filter(x=>x.meta<=38&&(tdOf(x)==null||q[x.pos]==null||tdOf(x)<=q[x.pos])).sort((a,b)=>a.meta-b.meta).slice(0,10);
      $('#bpAvoid').innerHTML=`<div class="panel"><h3>avoid <span class="f">META in the bottom band and the TD model in his position's bottom quarter (or unrated)</span></h3><div class="tscroll"><table class="fx bpt"><thead><tr><th style="text-align:left">player</th><th>slot</th><th>opp</th><th>META</th><th style="text-align:left">against</th><th>TD %</th><th>TD</th></tr></thead><tbody>${av.map(x=>{const ag=[['ENV',x.c.env,x.env==null?'':x.env.toFixed(1)+' imp'],['FORM',x.c.form,x.form==null?'':(x.form>=0?'+':'')+Math.round(100*x.form)+'%'],['Ψ',x.c.psi,x.psi==null?'':Math.round(x.psi)]].filter(a=>a[1]!=null&&a[1]<=.35).map(a=>`<span class="wkpc l">${a[0]} ${a[2]}</span>`).join(' ');const res=liveRes(x.u.player,x.u.team);return `<tr><td style="text-align:left">${pn(x.u.player,x.u.team,true)}</td><td>${slotchip(x.u.dslot||x.u.slot)}</td><td>${oppcell(x.oppRaw)}</td><td data-v="${x.meta}"><span class="badge" style="${gradeStyle(1+(1-x.meta/100)*(NT-1))}">${Math.round(x.meta)}</span></td><td style="text-align:left">${ag||'<span class="dim">—</span>'}</td><td>${tdOf(x)!=null?Math.round(100*tdOf(x))+'%':''}</td><td>${resCell(res,liveOpen(x.u.team))}</td></tr>`}).join('')||'<tr><td colspan="7" class="dim">nothing in view</td></tr>'}</tbody></table></div></div>`}
    else{$('#bpMeta').innerHTML=live?'':`<div class="panel"><h3>matchup plays — META <span class="f">live week only (week ${J.week})</span></h3></div>`;$('#bpAvoid').innerHTML=''}
    /* tiles + note */
    const gC=grade(C),gT=tdTop.slice(0,14).filter(x=>x.res!=null),kT=gT.filter(x=>x.res>0).length;
    $('#bpTiles').innerHTML=wkTile(`week ${W}${live?' · live':''}`,String(C.length),`frozen picks on the card${gC.n?` · ${gC.w}-${gC.n-gC.w} graded`:''}`,gC.n?(gC.w/gC.n>=.55?'g':gC.w/gC.n<.45?'r':''):'')
      +wkTile('TD board top 14',gT.length?`${kT}<span class="dim"> / ${gT.length}`:(tdTop[0]?esc(pshort(tdTop[0].n)):'—'),gT.length?'graded, scored':(tdTop[0]?`${Math.round(100*tdTop[0].p)}% · ${tdTop[0].ko}`:''),gT.length?(kT/gT.length>=.5?'g':kT/gT.length<.3?'r':''):'g',!gT.length)
      +wkTile('agreement',String(tdTop.slice(0,14).filter(x=>x.ag.length>=2).length),'of the top 14 with two or more boards agreeing','')
      +(live&&LIVE_TD?wkTile('scorers so far',String(liveScorers().length),`as of ${(LIVE_TD.pulled||'').replace('T',' ')}`,''):'');
    $('#bpN').innerHTML=`week ${W} · ${C.length} on the card · ${tdTop.length} on the TD board${gbOn()?' · narrowed by the global bar':''}`;
    sortableAll(el);tWire(el);logoize(el)}
  render();RR.push(render)}
'''
rep("/* ---------------- v46: today's scorers, mapped to where each was ranked highest ---------------- */", view + "/* ---------------- v46: today's scorers, mapped to where each was ranked highest ---------------- */")
rep("/* v47 */th.nw{", "/* v48 */.bpt td{white-space:nowrap}.bpt td:nth-child(1){max-width:170px;overflow:hidden;text-overflow:ellipsis}#bestpicks .wk2b{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:900px){#bestpicks .wk2b{grid-template-columns:1fr}}\n/* v47 */th.nw{")
rep(" wkres:{what:'The Weeklies picks, by category, for the games ahead.',",
    " bestpicks:{what:'The week\\'s plays in one place.',how:['the card = every frozen pick (game plays, props, anytime TDs): model vs market at freeze, edge, result as it lands','anytime TD = the TD Picks board\\'s best; agree = the other boards that also have him high (First TD, Weeklies, META v2) — two or more agreeing is the strongest spot on the page','matchup plays = the backtested META recipe (expected to beat his own baseline); avoid = bottom-band META with a cold TD model · the week picker and the global bar apply']},\n wkres:{what:'The Weeklies picks, by category, for the games ahead.',")
s = s.replace("Object.assign(NOTES,{v47:", "Object.assign(NOTES,{v48:['v48','F1 Home \\u2192 Best Picks: the frozen card graded as it lands, the TD board\\'s best with the boards that agree, the backtested META spots and the avoids \\u2014 one page']});\nObject.assign(NOTES,{v47:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v48 applied', len(s))
