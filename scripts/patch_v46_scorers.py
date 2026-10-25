"""v46 — today's scorers, mapped. J.liveTd (ESPN scoring plays, pulled by the markets loop on game days) marks the week's scorers
before the box scores land, and Results (slate ahead) opens with a panel: every scorer so far, with where he was ranked HIGHEST
before kickoff — across the data sets (2024 · 2025 · 2026 · combined · adjusted: TD rank and Ψ for his slot vs that defense) and
across the boards (META v2 CONS, META, TD Picks, First TD, Weeklies, H2H, ENV, FORM …) — then every rank in full, sortable.
Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function scorerMap(' in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

core = r'''
/* ---------------- v46: today's scorers, mapped to where each was ranked highest ---------------- */
const LIVE_TD=(J.liveTd&&J.liveTd.week===J.week&&J.liveTd.season===(J.season||2026))?J.liveTd:null;
const nmKey=s=>String(s||'').toLowerCase().replace(/[^a-z]/g,'').replace(/(jr|sr|ii|iii|iv)$/,'');
function liveScorers(){if(!LIVE_TD)return [];const agg={};LIVE_TD.plays.forEach(pl=>{const k=nmKey(pl.player)+'|'+pl.team;(agg[k]=agg[k]||{player:pl.player,team:pl.team,game:pl.game,n:0,how:[],q:[]}).n++;agg[k].how.push(pl.how);agg[k].q.push(pl.q+' '+pl.clock)});return Object.values(agg)}
const liveTdOf=(name,team)=>{if(!LIVE_TD)return null;const k=nmKey(name);const r=liveScorers().find(x=>nmKey(x.player)===k&&x.team===team)||liveScorers().find(x=>nmKey(x.player)===k);return r?r.n:null};
/* game state at the last pull: pre / in / post (older files: inferred from kickoff) */
const liveState=team=>{if(!LIVE_TD)return null;if(LIVE_TD.games){const k=Object.keys(LIVE_TD.games).find(g=>g.split('@').includes(team));if(k)return LIVE_TD.games[k]}const g=gameOf(team,J.week);return g?(kickedOff(g)?'in':'pre'):null};
/* a player's live result: touchdowns if he has one, 0 once his game is final, null while it is on or before kickoff */
const liveRes=(name,team)=>{const lv=liveTdOf(name,team);if(lv!=null)return lv;return liveState(team)==='post'?0:null};const liveOpen=team=>liveState(team)==='in';
/* game state at the last pull: pre / in / post (older files: inferred from kickoff) */
const liveState=team=>{if(!LIVE_TD)return null;if(LIVE_TD.games){const k=Object.keys(LIVE_TD.games).find(g=>g.split('@').includes(team));if(k)return LIVE_TD.games[k]}const g=gameOf(team,J.week);return g?(kickedOff(g)?'in':'pre'):null};
/* a player's live result: touchdowns if he has one, 0 once his game is final, null while it is on or before kickoff */
const liveRes=(name,team)=>{const lv=liveTdOf(name,team);if(lv!=null)return lv;return liveState(team)==='post'?0:null};const liveOpen=team=>liveState(team)==='in';
/* rank of val among arr by key (1 = best); higher = better unless lo */
const rankIn=(arr,val,key,lo)=>{const v=arr.map(key).filter(x=>x!=null);if(val==null||!v.length)return null;return [1+v.filter(x=>lo?x<val:x>val).length,v.length]};
function scorerMap(){
  const wk=G.week,MV=window.MV_LAST||[],M1=window.META_LAST||[];
  const TP=(J.tdpicks&&J.tdpicks.week===wk?J.tdpicks.picks:[])||[],FT=(J.firstTd&&J.firstTd.week===wk?J.firstTd.board:[])||[];
  let WA=[];try{const SG=wkSigs(),TR=wkTrust(x=>true,SG,'card38');WA=wkAhead(x=>true,TR,wk)}catch(e){}
  const srcs=Object.keys(J.dvp);
  return liveScorers().map(sc=>{
    const k=nmKey(sc.player);const u=UNIVERSE.find(x=>x.team===sc.team&&nmKey(x.player)===k)||UNIVERSE.find(x=>nmKey(x.player)===k);
    const row={sc,u,slot:u?(u.dslot||u.slot):'',opp:u?u.opp:'',calls:[]};if(!u)return row;
    const pos=u.pos,grp=u.grp,opp=u.opp;
    const tdc=(LABDEF[pos].stats(grp)||[]).filter(c=>/TD/.test(c)),tdcs=tdc.length>1?tdc.filter(c=>c!=='P TD'):tdc;
    srcs.forEach(src=>{const d=J.dvp[src]&&J.dvp[src][opp];if(!d)return;const r=tdcs.map(c=>d.stats[c]?d.stats[c].rank:null).filter(v=>v!=null);
      if(r.length)row.calls.push({k:src+' TD',grp:'set',rank:Math.round(r.reduce((a,b)=>a+b,0)/r.length),of:NT,tip:`${src}: touchdowns ${opp} allows to ${grp} · rank of ${NT}, 1 = the most`});
      if(d.comps&&d.comps[grp]!=null)row.calls.push({k:src+' Ψ',grp:'set',rank:Math.round(d.comps[grp]),of:NT,tip:`${src}: ${opp}'s mean rank across every ${grp} stat · 1 = softest`})});
    const mv=MV.find(x=>x.u===u);if(mv&&mv.cons!=null){const P=MV.filter(x=>x.pos===pos&&x.pool);const r=rankIn(P,mv.cons,x=>x.cons);row.calls.push({k:'META v2',grp:'board',rank:r[0],of:r[1],tip:`CONS ${Math.round(mv.cons)} · top-10% on ${mv.t10} boards · rank among ${pos}s`});
      MV_B.forEach(([bk,bl])=>{const p=mv.pc[bk];if(p==null)return;const rr=rankIn(P,p,x=>x.pc[bk]);if(rr)row.calls.push({k:'v2 '+bl,grp:'board',rank:rr[0],of:rr[1],tip:`META v2 ${bl} column · ${Math.round(100*p)}th percentile among ${pos}s`})})}
    const m1=M1.find(x=>x.u===u);if(m1&&m1.meta!=null){const r=rankIn(M1.filter(x=>x.pos===pos&&x.pool),m1.meta,x=>x.meta);row.calls.push({k:'META',grp:'board',rank:r[0],of:r[1],tip:`META ${Math.round(m1.meta)} · rank among ${pos}s`})}
    const tp=TP.find(r=>r.n===u.player&&r.t===u.team)||TP.find(r=>r.n===u.player);if(tp&&tp.p!=null){const r=rankIn(TP.filter(r=>r.pos===pos),+tp.p,r=>+r.p);row.calls.push({k:'TD Picks',grp:'board',rank:r[0],of:r[1],tip:`${Math.round(100*tp.p)}% to score · rank among ${pos}s`})}
    const ft=FT.find(r=>r.player===u.player&&r.team===u.team)||FT.find(r=>r.player===u.player);if(ft&&ft.p_first!=null){const r=rankIn(FT.filter(r=>r.pos===pos),+ft.p_first,r=>+r.p_first);row.calls.push({k:'First TD',grp:'board',rank:r[0],of:r[1],tip:`${(100*ft.p_first).toFixed(1)}% first TD · rank among ${pos}s`})}
    const wa=WA.find(x=>x.name===u.player&&x.team===u.team);if(wa){const r=rankIn(WA.filter(x=>x.pos===pos),wa.score,x=>x.score);row.calls.push({k:'Weeklies',grp:'board',rank:r[0],of:r[1],tip:`${wa.cs} of 8 core signals${wa.on.length?': '+wa.on.map(z=>z.lbl).join(', '):''} · rank among ${pos}s`});row.sig=wa.cs}
    row.calls.forEach(c=>{c.pct=c.of>1?(c.rank-1)/(c.of-1):0});
    row.best=row.calls.slice().sort((a,b)=>a.pct-b.pct||a.rank-b.rank)[0]||null;
    return row})}
function scorerPanel(){
  const R=scorerMap();if(!R.length)return '';
  const chip=c=>`<span class="scall" title="${esc(c.tip)}" style="${gradeStyle(1+c.pct*(NT-1))}">${esc(c.k)} <b>#${c.rank}</b><i>/${c.of}</i></span>`;
  const rows=R.sort((a,b)=>(a.best?a.best.pct:9)-(b.best?b.best.pct:9)).map(r=>{const sets=r.calls.filter(c=>c.grp==='set'&&c!==r.best).sort((a,b)=>a.rank-b.rank),bds=r.calls.filter(c=>c.grp==='board'&&c!==r.best).sort((a,b)=>a.pct-b.pct);
    return `<tr><td style="text-align:left">${r.u?pn(r.u.player,r.u.team,true):esc(r.sc.player)}</td><td>${tcell(r.sc.team)}</td><td>${r.slot?slotchip(r.slot):'<span class="dim">—</span>'}</td><td>${r.opp?tcell(r.opp):''}</td><td data-v="${r.sc.n}"><b style="color:var(--green)">${r.sc.n}</b> <span class="mini dim">${r.sc.how.join('+')}</span></td>
      <td data-v="${r.best?r.best.pct:9}">${r.best?chip(r.best):'<span class="dim">not on a depth chart (D/ST · OL · deep bench)</span>'}</td>
      <td style="text-align:left"><span class="scalls">${bds.slice(0,4).map(chip).join('')}</span></td><td style="text-align:left"><span class="scalls">${sets.slice(0,3).map(chip).join('')}</span></td></tr>`}).join('');
  const hit=(r,f)=>R.filter(f).length;
  const sum=`${R.length} scorer${R.length===1?'':'s'} so far · ${hit(R,r=>r.best&&r.best.pct<=.1)} had a top-10% call somewhere · ${hit(R,r=>r.best&&r.best.pct<=.25)} a top-quarter call · ${hit(R,r=>!r.u)} not on a depth chart`;
  return `<div class="panel" id="scPanel"><h3>who has scored — week ${G.week} <span class="f">${esc(sum)} · best call = the board or data set that had him ranked highest before kickoff · every rank in the hover · as of ${esc((LIVE_TD.pulled||'').replace('T',' '))}</span></h3>
    <div class="tscroll"><table class="fx sct"><thead><tr><th style="text-align:left">scorer</th><th>team</th><th>slot</th><th>opp</th><th>TDs</th><th>best call</th><th style="text-align:left">boards (best first)</th><th style="text-align:left">data sets (best first)</th></tr></thead><tbody>${rows}</tbody></table></div></div>`}
'''
rep("function wkResults(){const el=$('#wkres');if(!el)return;", core + "function wkResults(){const el=$('#wkres');if(!el)return;")
# the panel sits above the category blocks on the slate-ahead scope; live TDs mark ✓ on ahead rows
rep("    <div id=\"wrBy\"></div><div class=\"panel\" id=\"wrTblP\">", "    <div id=\"wrSc\"></div><div id=\"wrBy\"></div><div class=\"panel\" id=\"wrTblP\">")
rep("    if(st.scope==='ahead'){const TR=wkTrust(x=>true,SG,'wres');R=wkAhead(u=>true,TR,G.week).map(x=>Object.assign(x,{w:G.week,ahead:true,se:LAST_SE,res:x.done?x.done.td:null,ppr:null}))}",
    "    if(st.scope==='ahead'){const TR=wkTrust(x=>true,SG,'wres');R=wkAhead(u=>true,TR,G.week).map(x=>Object.assign(x,{w:G.week,ahead:true,se:LAST_SE,res:x.done?x.done.td:liveRes(x.name,x.team),open:!x.done&&liveOpen(x.team),ppr:null}))}")
rep("    $('#wrBy').hidden=st.view!=='cat';$('#wrTblP').hidden=st.view==='cat';",
    "    $('#wrSc').innerHTML=st.scope==='ahead'?scorerPanel():'';tWire($('#wrSc'));sortableAll($('#wrSc'));\n    $('#wrBy').hidden=st.view!=='cat';$('#wrTblP').hidden=st.view==='cat';")
# the week-ahead chips: a live scorer whose game is still on shows ✓ too (res from liveTdOf) — already via res. CSS:
rep("/* v45 */.wrcat{", "/* v46 */.scall{display:inline-flex;gap:3px;align-items:baseline;border-radius:4px;padding:1px 6px;font:500 10.5px var(--mono);margin:1px 3px 1px 0;white-space:nowrap}.scall b{font-weight:700}.scall i{font-style:normal;opacity:.7;font-size:9.5px}.scalls{display:flex;flex-wrap:wrap}.sct td{white-space:nowrap}.sct td:nth-child(7),.sct td:nth-child(8){white-space:normal;min-width:260px}\n/* v45 */.wrcat{")
s = s.replace("Object.assign(NOTES,{v45:", "Object.assign(NOTES,{v46:['v46','who has scored \\u2014 the week\\'s touchdowns land as they happen (ESPN, markets loop) and Results maps every scorer to where he was ranked highest before kickoff, across the data sets and the boards']});\nObject.assign(NOTES,{v45:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v46 applied', len(s))
