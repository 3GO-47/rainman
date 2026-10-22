"""v34 — paired views (one sub-tab, a Grid | Board switch), the last dead tiles (Schedule, Picks Board, Model, DFS) open
their history, Depth Delta measures the live week against last week's chart. Additive; rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'const PAIRS=' in s:
    print('already applied'); sys.exit(0)
assert 'function thSeq(' in s and 'function weeklies2()' in s, 'v32 + v33 first'

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

# ---------- A. paired views ----------
rep("/* v33 Weeklies v2 / Category Grid v2 */", "/* v34 paired views */.pairseg{margin-left:auto}.controls.pairrow{justify-content:flex-end;padding:4px 0 0}.pairseg button.on{background:#1a1a1a;color:var(--txt)}\n/* v33 Weeklies v2 / Category Grid v2 */")
pairs = r'''/* v34: paired views — two views of the same thing live under ONE sub-tab with a switch; the choice sticks for the session */
const PAIRS={tdboard:['tdbx','Grid','Board','TD'],labgridp:['lab','Grid','Board','Players'],h2hgridp:['h2hp','Grid','Board','H2H'],weeklies:['weeklies2','v1','v2','Weeklies'],wkgrid:['wkgrid2','v1','v2','Category Grid']};
const PAIR_OF={};Object.entries(PAIRS).forEach(([a,[b]])=>{PAIR_OF[b]=a});const PAIR_PREF={};
function pairBar(it){document.querySelectorAll('.pairseg').forEach(e=>e.remove());const old=$('#pairBar');if(old)old.remove();
  const a=PAIRS[it.id]?it.id:PAIR_OF[it.id];if(!a||!itemOK(ITEMS[a])||!itemOK(ITEMS[PAIRS[a][0]]))return;
  const [b]=PAIRS[a],isB=it.id===b,M={tdbx:'#tdBx',lab:'#lab',h2hp:'#h2hP',tdboard:'#tdb'};
  const panel=document.querySelector(M[it.id]||('#'+(it.sub||it.c)));if(!panel)return;
  let row=panel.querySelector(':scope > .controls');if(!row){row=document.createElement('div');row.className='controls pairrow';panel.insertBefore(row,panel.firstChild)}
  const seg=document.createElement('span');seg.className='seg pairseg';seg.innerHTML=`<button class="${isB?'':'on'}" data-g="${a}">${esc(ITEMS[a].label)}</button><button class="${isB?'on':''}" data-g="${b}">${esc(ITEMS[b].label)}</button>`;
  row.appendChild(seg);seg.querySelectorAll('button').forEach(x=>x.onclick=()=>{PAIR_PREF[a]=x.dataset.g===b?'b':'a';go(x.dataset.g,{pair:1})})}
'''
rep("function buildSub(sec){const nav=$('#snav');nav.dataset.sec=sec.id;const its=sec.items.filter(itemOK);nav.hidden=its.length<2;\n  nav.innerHTML=its.map(it=>`<a class=\"sitem\" data-i=\"${it.id}\" href=\"#v=${it.id}\" title=\"${esc(it.desc)}\">${it.label}</a>`).join('');",
    pairs + "function buildSub(sec){const nav=$('#snav');nav.dataset.sec=sec.id;const its=sec.items.filter(itemOK).filter(it=>!(PAIR_OF[it.id]&&itemOK(ITEMS[PAIR_OF[it.id]])));nav.hidden=its.length<2;\n  nav.innerHTML=its.map(it=>`<a class=\"sitem\" data-i=\"${it.id}\" href=\"#v=${it.id}\" title=\"${esc(PAIRS[it.id]&&itemOK(ITEMS[PAIRS[it.id][0]])?it.desc+' · or: '+ITEMS[PAIRS[it.id][0]].desc:it.desc)}\">${PAIRS[it.id]&&itemOK(ITEMS[PAIRS[it.id][0]])?PAIRS[it.id][3]:it.label}</a>`).join('');")
rep("function go(id,opts={}){const it=ITEMS[id]||ITEMS.overview;if(!itemOK(it))return go('overview');CUR_ITEM=it.id;",
    "function go(id,opts={}){let it=ITEMS[id]||ITEMS.overview;if(!itemOK(it))return go('overview');if(!opts.pair&&PAIRS[it.id]&&PAIR_PREF[it.id]==='b'&&itemOK(ITEMS[PAIRS[it.id][0]]))it=ITEMS[PAIRS[it.id][0]];if(!opts.pair&&PAIR_OF[it.id])PAIR_PREF[PAIR_OF[it.id]]='b';CUR_ITEM=it.id;")
rep("  document.querySelectorAll('#snav .sitem').forEach(a=>a.classList.toggle('on',a.dataset.i===it.id));",
    "  document.querySelectorAll('#snav .sitem').forEach(a=>a.classList.toggle('on',a.dataset.i===it.id||a.dataset.i===PAIR_OF[it.id]));pairBar(it);")

# ---------- B. the last dead tiles ----------
# Schedule
sk = r'''    {const tb=(t,sub,L,key)=>()=>({title:t,sub,cols:['offense',{l:key==='d'?'next 4 minus season':'mean Ψ · lens',lo:true,t:'Ψ: 1 = softest'},{l:'next 4',lo:true},{l:'rest of season',lo:true},{l:'weeks 15–17',lo:true},{l:'all 18',lo:true}],rows:L.map(r=>[tcell(r.t),r[key]!=null?{v:r[key],h:r[key].toFixed(1)}:null,r.n4!=null?{v:r.n4,h:r.n4.toFixed(1)}:null,r.ros!=null?{v:r.ros,h:r.ros.toFixed(1)}:null,r.po!=null?{v:r.po,h:r.po.toFixed(1)}:null,r.avg!=null?{v:r.avg,h:r.avg.toFixed(1)}:null])});
      const sw=rows.map(r=>Object.assign({},r,{d:r.n4!=null&&r.avg!=null?r.n4-r.avg:null})).filter(x=>x.d!=null).sort((a,b)=>a.d-b.d);
      thDom($('#skKpi').querySelector('.kpis'),[tb(`strength of schedule · ${slot}`,'every offense by the mean Ψ of its opponents over the lens picked · 1 = softest',easiest,'lensAvg'),...(easiest[0]?[tb(`easiest slates · ${slot}`,'softest first',easiest,'lensAvg')]:[]),...(easiest.length?[tb(`hardest slates · ${slot}`,'hardest first',easiest.slice().reverse(),'lensAvg')]:[]),...(sw.length?[tb(`softening · ${slot}`,'next four weeks minus the season mean · most negative = softening most',sw,'d'),tb(`hardening · ${slot}`,'next four weeks minus the season mean · most positive = hardening most',sw.slice().reverse(),'d')]:[])])}
'''
rep("    $('#skTbl').innerHTML=`<table class=\"sk\"><thead><tr><th>offense</th>", sk + "    $('#skTbl').innerHTML=`<table class=\"sk\"><thead><tr><th>offense</th>")
# Picks Board
pb = r'''    {const tb=(t,L)=>()=>({title:`${t} · week ${wk}`,sub:`${L.length} positions · frozen at the number the model saw`,html:L.length?table(L):'<p class="note mini">none</p>'});
      thDom(root.querySelector('.kpis'),[tb('plays',plays),tb('leans',leans),tb('priced, passed',rest),null,tb('biggest edges',F.slice(0,30))])}
'''
rep("    root.querySelectorAll('tr.gb[data-game]').forEach(tr=>tr.onclick=e=>{if(e.target.closest('.pp,.tc'))return;G.game=tr.dataset.game;",
    pb + "    root.querySelectorAll('tr.gb[data-game]').forEach(tr=>tr.onclick=e=>{if(e.target.closest('.pp,.tc'))return;G.game=tr.dataset.game;")
# Model (picksHome)
pk = r'''  {const wkH=()=>({title:'the model · week by week',sub:'every frozen position, graded from the box scores · the selected week is tinted',cols:[{l:'week',g:false},{l:'frozen',g:false},{l:'graded',g:false},{l:'record',g:false},'units',{l:'hit'},{l:'running',g:false}],rows:byW.map((x,i)=>Object.assign([x.week,x.n,x.graded||0,x.graded?pkWL(x):'—',x.graded?{v:x.units,h:pkU(x.units)}:null,x.graded?{v:x.hit,h:pkPct(x.hit,1)}:null,pkU(curve[i].cum)],{hi:x.week===wk}))});
    const gmH=()=>({title:'game model · every graded game',sub:`${gmRows.length} games · the spread the model made, the closing line and the result`,cols:[{l:'week',g:false},{l:'game',g:false},{l:'model spread',g:false},{l:'closing spread',g:false},{l:'result',g:false},{l:'ATS',g:false},{l:'total',g:false}],rows:gmRows.slice().sort((a,b)=>b.week-a.week).map(g=>[g.week,`${tcell(g.away_team)} @ ${tcell(g.home_team)}`,g.model_spread,g.spread_line??'',g.result,g.res_ats||'',g.res_total||''])});
    thDom(el.querySelector('.kpis'),[wkH,wkH,wkH,wkH,wkH,null,gmH,gmH])}
'''
rep("  logoize(el);\n  el.querySelectorAll('tr.pkwk').forEach(tr=>tr.onclick=()=>{const w=+tr.dataset.wk;", pk + "  logoize(el);\n  el.querySelectorAll('tr.pkwk').forEach(tr=>tr.onclick=()=>{const w=+tr.dataset.wk;")
# DFS
dfs = r'''thSeq(kp,[()=>({title:'DraftKings Classic · every slate on record',sub:'projected vs actual DK points per frozen lineup · the selected week is tinted',cols:[{l:'week',g:false},{l:'slate',g:false},{l:'games',g:false},{l:'cap',g:false},'projected','actual',{l:'frozen',g:false}],rows:DFS.summary.map(x=>Object.assign([+x.week,x.slate,+x.games,x.capped==='True'?money(+x.salary):'uncapped',{v:+x.proj_total,h:(+x.proj_total).toFixed(1)},x.actual_total!==''&&x.actual_total!=null?{v:+x.actual_total,h:(+x.actual_total).toFixed(1)}:null,x.frozen_on],{hi:+x.week===wk}))}),
      ()=>({title:`salaries · week ${wk}`,sub:SAL&&SAL.n?`${priced.length} qualified plays priced`:'no DraftKings export for this week — drop it at data/raw/dk_salaries_wk'+wk+'.csv',cols:['player','team',{l:'slot',g:false},{l:'salary',lo:true},'projection','value'],rows:priced.slice().sort((a,b)=>b.val-a.val).map(r=>[pn(r.u.player,r.u.team,true),tcell(r.u.team),slotchip(r.u.slot),{v:r.sal,h:money(r.sal)},{v:r.pts,h:r.pts.toFixed(1)},{v:r.val,h:r.val.toFixed(2)}])}),
      ...(S[0]?[()=>({title:`${S[0].slate} lineup · week ${wk}`,sub:'the frozen lineup, projected and actual',cols:[{l:'roster',g:false},'player','team',{l:'opp',g:false},{l:'salary',lo:true},'projected','actual'],rows:E.filter(e=>e.slate===S[0].slate).map(e=>[e.roster,pn(e.player,e.team,true),tcell(e.team),e.opp||'',{v:+e.salary,h:money(+e.salary)},{v:+e.proj_pts,h:(+e.proj_pts).toFixed(1)},e.actual_pts!==''&&e.actual_pts!=null?{v:+e.actual_pts,h:(+e.actual_pts).toFixed(1)}:null])})]:[]),
      ...(best?[()=>({title:`projections · week ${wk}`,sub:`${q.length} qualified plays by projected DK points`,cols:['player','team',{l:'slot',g:false},'projection',{l:'salary',lo:true}],rows:q.slice().sort((a,b)=>b.pts-a.pts).slice(0,60).map(r=>[pn(r.u.player,r.u.team,true),tcell(r.u.team),slotchip(r.u.slot),{v:r.pts,h:r.pts.toFixed(1)},r.sal?{v:r.sal,h:money(r.sal)}:null])})]:[]),
      ...(bv?[()=>({title:`value board · week ${wk}`,sub:'points per $1k of salary',cols:['player','team',{l:'slot',g:false},'value','projection',{l:'salary',lo:true}],rows:vboard.map(r=>[pn(r.u.player,r.u.team,true),tcell(r.u.team),slotchip(r.u.slot),{v:r.val,h:r.val.toFixed(2)},{v:r.pts,h:r.pts.toFixed(1)},{v:r.sal,h:money(r.sal)}])})]:[])])+lineups'''
rep("    slot.innerHTML=kp+lineups", "    slot.innerHTML=" + dfs)

# ---------- C. Depth Delta: the live week against LAST WEEK's chart, not yesterday's snapshot ----------
rep("    const now=wk>=J.week||!hs(wk)||!hs(wk-1);const PV=now?J.depthPrev:hs(wk-1);const curDate=now?J.depthDate:hs(wk).date;",
    "    const now=wk>=J.week||!hs(wk)||!hs(wk-1);const PV=now?(hs(Math.min(wk,J.week)-1)||J.depthPrev):hs(wk-1);const curDate=now?J.depthDate:hs(wk).date;")
rep("Object.assign(NOTES,{weeklies2:['v33',", "Object.assign(NOTES,{pairs34:['v34','paired views: TD Grid / TD Board, Player Grid / Player Board, H2H Grid / H2H Board, Weeklies v1 / v2 and Category Grid v1 / v2 each live under one sub-tab with a switch that sticks \\u00b7 the Schedule, Picks Board, Model and DFS tiles open their history \\u00b7 Depth Delta compares the live week with last week\\'s chart (snapshot before last week\\'s first kickoff) instead of yesterday\\'s']});\nObject.assign(NOTES,{weeklies2:['v33',")
io.open(T, 'w', encoding='utf-8').write(s)
print('v34 applied', len(s))
