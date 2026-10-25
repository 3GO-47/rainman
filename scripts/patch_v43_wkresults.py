"""v43 — F1 Home → Results: the Weeklies data as one flat, filterable table. Every player-game of a graded week (and the week
ahead's slate), one row each, with every Weeklies category he carried into it; filter by category (any / all of the picked ones),
season, week scope, result, slot set, minimum signal count, search — on top of the global bar (week, pos, team, roster). Sortable
on every column; a category chip in a row adds it to the filter; a name opens his card. Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function wkResults(' in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

# nav item (Home section, after Category Grid) + panel + syncSub + BOOT
rep("   {id:'wkgrid',label:'Category Grid',desc:",
    "   {id:'wkres',label:'Results',desc:'the Weeklies data as one flat table: every player-game of a graded week (and the slate ahead) with every category he carried into it \\u2014 filter by category, season, week, result, slot; sortable on every column',c:'test',sub:'wkres'},\n   {id:'wkgrid',label:'Category Grid',desc:")
rep('<div id="test" hidden><div id="backtest" hidden></div>', '<div id="test" hidden><div id="wkres" hidden></div><div id="backtest" hidden></div>')
rep("if(it.c==='test'){['meta','metaprop','weeklies','weeklies2','wkgrid','wkgrid2',", "if(it.c==='test'){['wkres','meta','metaprop','weeklies','weeklies2','wkgrid','wkgrid2',")
rep("['test',weeklies2],['test',wkGrid2],", "['test',weeklies2],['test',wkGrid2],['test',wkResults],")

# the view
view = r'''
/* ---------------- v43: Weeklies RESULTS — one flat, filterable table of player-games and their categories ---------------- */
function wkResults(){const el=$('#wkres');if(!el)return;
  const SG=wkSigs(),BYID={};SG.forEach(s=>BYID[s.id]=s);
  const st={se:LAST_SE,scope:'week',res:'',mode:'any',core:true,min:0,q:'',cats:new Set(),lim:400};
  const GL=Object.keys(WK_GL);
  el.innerHTML=`<div class="controls">
    <span class="chips" id="wrSe">${ALL_SE.slice().reverse().map(se=>`<button data-s="${se}" class="${se===st.se?'on':''}">${se}</button>`).join('')}</span>
    <select id="wrScope" title="which games the rows come from"><option value="week">the week picked up top</option><option value="all">every graded week of the season</option><option value="ahead">the week ahead (not played yet)</option></select>
    <select id="wrRes" title="what happened"><option value="">scored or not</option><option value="y">scored a TD</option><option value="n">no TD</option><option value="2">2+ TDs</option></select>
    <select id="wrCore" title="which depth slots"><option value="1">QB1 · RB1–2 · WR1–3 · TE1</option><option value="">every slot</option></select>
    <select id="wrMin" title="at least this many of the eight core signals"><option value="0">any signal count</option><option value="2">2+ core signals</option><option value="3">3+ core signals</option><option value="4">4+ core signals</option><option value="5">5+ core signals</option></select>
    <span class="chips" id="wrMode" title="a row must carry ANY of the picked categories, or ALL of them"><button data-m="any" class="on">any of</button><button data-m="all">all of</button></span>
    <input id="wrQ" placeholder="search player / team..." size="18">
    <span class="btnlk" id="wrClear">&#10005; categories</span>
    <span class="note mini" id="wrN"></span></div>
    <div class="wrcats" id="wrCats">${GL.map(g=>`<div class="wrg"><span class="gl" title="${esc(WK_GL[g])}">${g}</span><span class="chips">${SG.filter(x=>x.g===g).map(x=>`<button data-c="${x.id}" class="${x.kind==='neg'?'neg':''}" title="${esc(x.long)}">${esc(x.lbl)}</button>`).join('')}</span></div>`).join('')}</div>
    <div class="panel"><div id="wrTbl" class="tscroll"></div><p class="mini dim" id="wrMore"></p></div>`;
  const keepRow=x=>(!st.core||WK_CORE.has(x.slot==='WR4+'?'WR4':x.slot))&&inP(x.pos)&&inF(x.team)&&inO(x.name,x.team);
  const rows=()=>{
    let R=[];
    if(st.scope==='ahead'){const TR=wkTrust(x=>true,SG,'wres');R=wkAhead(u=>true,TR,G.week).map(x=>Object.assign(x,{w:G.week,ahead:true,se:LAST_SE,res:x.done?x.done.td:null,ppr:null}))}
    else{const F=wkFeat(st.se),ws=st.scope==='week'?[F.weeks.includes(G.week)?G.week:Math.max(...F.weeks.filter(w=>w<=G.week).concat([F.weeks[0]||0]))]:F.weeks;
      const WS=new Set(ws);st.shown=st.scope==='week'?ws[0]:null;R=F.rows.filter(x=>WS.has(x.w)).map(x=>Object.assign(x,{se:st.se,res:x.td}))}
    R=R.filter(keepRow);
    R.forEach(x=>{x.on=SG.filter(s=>s.f(x));x.ids=new Set(x.on.map(s=>s.id));x.cs=WK_KEY.filter(id=>x.ids.has(id)).length});
    if(st.cats.size)R=R.filter(x=>st.mode==='all'?[...st.cats].every(c=>x.ids.has(c)):[...st.cats].some(c=>x.ids.has(c)));
    if(st.res==='y')R=R.filter(x=>x.res>0);else if(st.res==='n')R=R.filter(x=>x.res===0);else if(st.res==='2')R=R.filter(x=>x.res>=2);
    if(st.min)R=R.filter(x=>x.cs>=st.min);
    if(st.q){const q=st.q.toLowerCase();R=R.filter(x=>(x.name+' '+x.team).toLowerCase().includes(q))}
    return R};
  const catChip=(s,on)=>`<span class="wkpc ${s.kind==='neg'?'l':''}${on?' on':''}" data-c="${s.id}" title="${esc(s.long)} · click to filter on it">${esc(s.lbl)}</span>`;
  const num=v=>v==null?'':Math.round(10*v)/10;
  function render(){
    const R=rows();const sc=R.filter(x=>x.res>0).length,gr=R.filter(x=>x.res!=null).length;
    $('#wrN').innerHTML=`${st.scope==='week'&&st.shown!=null?`week ${st.shown}${st.shown!==G.week?' (newest graded — week '+G.week+' is not graded yet)':''} · `:st.scope==='all'?`every graded week of ${st.se} · `:''}${R.length} player-game${R.length===1?'':'s'}${gr?` · ${sc} scored (${Math.round(100*sc/gr)}%)`:''}${st.scope==='ahead'?' · the week ahead: result fills in as games finish':''}${st.cats.size?` · ${st.mode} of: <b>${[...st.cats].map(c=>esc(BYID[c].lbl)).join(st.mode==='all'?' + ':' / ')}</b>`:''}`;
    const show=R.slice(0,st.lim);
    $('#wrTbl').innerHTML=`<table class="fx wrt"><colgroup>${[34,150,52,52,58,52,52,36,44,52,46,48].map(w=>`<col style="width:${w}px">`).join('')}<col></colgroup><thead><tr><th>wk</th><th style="text-align:left">player</th><th>team</th><th>slot</th><th>opp</th><th title="touchdowns in the game">TD</th><th title="PPR points in the game">PPR</th><th title="how many of the eight core signals he carried">sig</th><th title="season TD rate going in">rate</th><th title="share of his team's TDs going in">share</th><th title="team implied points going in">imp</th><th title="opponent's TD rank for his slot going in · 1 = allows the most">TD rk</th><th style="text-align:left">categories carried in</th></tr></thead><tbody>${show.map(x=>`<tr>
      <td data-v="${x.w}">${x.w}</td><td style="text-align:left">${pn(x.name,x.team,true)}</td><td>${tcell(x.team)}</td><td>${slotchip(x.slot)}</td><td>${x.raw?oppcell(x.raw):(x.l?tcell(x.l[LOG.opp]):(x.opp?tcell(x.opp):''))}</td>
      <td data-v="${x.res==null?-1:x.res}">${x.res==null?'<span class="dim">—</span>':x.res>0?`<b style="color:var(--green)">✓ ${x.res}</b>`:'<span style="color:var(--red)">✗</span>'}</td>
      <td data-v="${x.ppr==null?-1:x.ppr}">${x.ppr==null?'':x.ppr.toFixed(1)}</td><td data-v="${x.cs}">${x.cs}</td>
      <td data-v="${x.rate==null?-1:x.rate}">${x.rate==null?'':num(x.rate)}</td><td data-v="${x.share==null?-1:x.share}">${x.share==null?'':Math.round(100*x.share)+'%'}</td><td data-v="${x.imp==null?-1:x.imp}">${x.imp==null?'':num(x.imp)}</td><td data-v="${x.tdR==null?99:x.tdR}">${x.tdR==null?'':x.tdR}</td>
      <td style="text-align:left"><span class="wkpcs">${x.on.map(s=>catChip(s,st.cats.has(s.id))).join('')||'<span class="dim">—</span>'}</span></td></tr>`).join('')||'<tr><td colspan="13" class="dim">nothing matches</td></tr>'}</tbody></table>`;
    $('#wrMore').innerHTML=R.length>show.length?`showing ${show.length} of ${R.length} · <a href="#" id="wrMoreA">show ${Math.min(R.length,st.lim+400)}</a>`:'';
    const a=$('#wrMoreA');if(a)a.onclick=e=>{e.preventDefault();st.lim+=400;render()};
    sortableAll($('#wrTbl'));tWire($('#wrTbl'));
    $('#wrTbl').querySelectorAll('.wkpc[data-c]').forEach(c=>c.onclick=()=>{toggleCat(c.dataset.c)});
    $('#wrCats').querySelectorAll('button[data-c]').forEach(b=>b.classList.toggle('on',st.cats.has(b.dataset.c)))}
  function toggleCat(id){st.cats.has(id)?st.cats.delete(id):st.cats.add(id);st.lim=400;render()}
  $('#wrCats').querySelectorAll('button[data-c]').forEach(b=>b.onclick=()=>toggleCat(b.dataset.c));
  $('#wrSe').querySelectorAll('button').forEach(b=>b.onclick=()=>{st.se=+b.dataset.s;$('#wrSe').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));if(st.scope==='ahead'){st.scope='week';$('#wrScope').value='week'}render()});
  $('#wrMode').querySelectorAll('button').forEach(b=>b.onclick=()=>{st.mode=b.dataset.m;$('#wrMode').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render()});
  $('#wrScope').onchange=()=>{st.scope=$('#wrScope').value;if(st.scope==='ahead'){st.se=LAST_SE;$('#wrSe').querySelectorAll('button').forEach(x=>x.classList.toggle('on',+x.dataset.s===LAST_SE))}render()};
  $('#wrRes').onchange=()=>{st.res=$('#wrRes').value;render()};$('#wrCore').onchange=()=>{st.core=!!$('#wrCore').value;render()};$('#wrMin').onchange=()=>{st.min=+$('#wrMin').value;render()};
  $('#wrQ').oninput=()=>{st.q=$('#wrQ').value;render()};$('#wrClear').onclick=()=>{st.cats.clear();render()};
  render();RR.push(render);
}
'''
rep("function weeklies2(){const el=$('#weeklies2');if(!el)return;", view + "function weeklies2(){const el=$('#weeklies2');if(!el)return;")
# CSS
rep("/* v42 */.btnlk{", "/* v43 results */.wrcats{display:flex;flex-direction:column;gap:3px;margin:0 0 8px}.wrg{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.wrg>.gl{min-width:64px}.wrg .chips button.neg{opacity:.75}.wrg .chips button.on{background:#e8b100;color:#000;border-color:#e8b100}.wrg .chips button.neg.on{background:#ff5252;border-color:#ff5252;color:#fff}\n.wrt{width:100%;table-layout:fixed}.wrt td,.wrt th{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.wrt td:last-child,.wrt th:last-child{white-space:normal}.wrt .wkpcs{display:flex;gap:3px;flex-wrap:wrap}.wrt .wkpc{cursor:pointer;font-size:10.5px;padding:1px 6px 1px 6px}.wrt .wkpc.on{border-color:#e8b100;color:#e8b100}.wrt .wkpc.l.on{border-color:#ff5252;color:#ff5252;opacity:1}\n/* v42 */.btnlk{")
# intro
rep(" meta:{what:'Every board at once.',", " wkres:{what:'The Weeklies data as one table.',how:['one row per player-game: the week, who, where, what happened (TD · PPR) and every Weeklies category he carried INTO that game','click categories to filter — any of / all of — or click a chip in a row; season chips, the week picked up top (or every graded week, or the slate ahead), scored / blanked, slot set, minimum signal count, search','every column sorts; the global bar (pos · team · roster) applies']},\n meta:{what:'Every board at once.',")
s = s.replace("Object.assign(NOTES,{v42:", "Object.assign(NOTES,{v43:['v43','F1 Home \\u2192 Results: the Weeklies data as one flat table \\u2014 every player-game with the categories he carried in, filterable by category (any / all), season, week scope, result, slot set and signal count, sortable on every column']});\nObject.assign(NOTES,{v42:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v43 applied', len(s))
