# -*- coding: utf-8 -*-
"""v18 — the TD Grid's player filter (slot chips · hide OUT · search) on every board that lists players.
The old "1st string / top 2 / all depths" dropdown is replaced by the slot chips on: Player Grid + Lab Grid, TD Board, Player Board,
H2H Board, Player Splits (F3 + F6), Depth Delta (F3 + F6). Markets (F5 + F6 Markets v2) gains slot chips + search. Weeklies' pool
select and position chips become the slot chips (default = the starters) and it follows the global POS filter like every board.
Untouched on purpose: F6 TD Grid (the frozen draft with its original depth filter); TD Grid, H2H Grid / Head to Head and META already carry it."""
T='scripts/dashboard_template.html'
s=open(T,encoding='utf-8').read()
def fn_span(start):
    i=s.index(start);j=s.find('\nfunction ',i+len(start))
    return i,(j if j>0 else len(s))
def in_fn(start,old,new):
    global s
    i,j=fn_span(start);seg=s[i:j]
    assert seg.count(old)==1,(start,old[:90],seg.count(old))
    s=s[:i]+seg.replace(old,new)+s[j:]
def once(old,new):
    global s
    assert s.count(old)==1,(old[:90],s.count(old));s=s.replace(old,new)

# ---- shared helpers, right before the Player Board
once("function lab(){","""/* ---------- the player filter: the TD Grid's slot chips, shared by every board that lists players ----------
   chips = depth-chart slots (WR order re-ranked by depth, as on the TD Grid); ALL = every body on the chart */
function slotChipsHTML(id,on){on=on||new Set(TD_SLOTS);return `<span class="chips" id="${id}" title="which depth slots the board covers — click to toggle, ALL for every body on the chart"><button data-s="" class="${on.size?'':'on'}">all</button>${TD_SLOTS.map(x=>`<button data-s="${x}" class="${on.has(x)?'on':''}">${x}</button>`).join('')}</span>`}
function slotChipsWire(id,live,cb){const box=document.getElementById(id);if(!box)return;box.querySelectorAll('button').forEach(b=>b.onclick=()=>{const v=b.dataset.s;
  if(!v)live.clear();else live.has(v)?live.delete(v):live.add(v);box.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.s?live.has(x.dataset.s):live.size===0));cb()})}
const slotOK=(live,sl)=>!live.size||live.has(sl);
function lab(){""")
DEP_SEL='<select id="{0}"><option value="1" selected>1st string only</option><option value="2">top 2 depths</option><option value="">all depths</option></select>'

# ---- Player Board
in_fn("function lab(){","function lab(){","function lab(){const labLive=new Set(TD_SLOTS);")
in_fn("function lab(){",DEP_SEL.format('labDepth'),'')
in_fn("function lab(){",'<select id="labSrc">','${slotChipsHTML(\'labSlots\',labLive)}\n    <select id="labSrc">')
in_fn("function lab(){","const dep=$('#labDepth').value,hin=$('#labInj').value;","const hin=$('#labInj').value;")
in_fn("function lab(){","      &&(!dep||u.depth<=+dep)\n","      &&slotOK(labLive,u.dslot||u.slot)\n")
in_fn("function lab(){","['labSrc','labDepth','labInj','labCol','labAvg'].forEach(id=>$('#'+id).onchange=render);","['labSrc','labInj','labCol','labAvg'].forEach(id=>$('#'+id).onchange=render);slotChipsWire('labSlots',labLive,render);")

# ---- TD Board
in_fn("function tdLab(){","function tdLab(){","function tdLab(){const tdxLive=new Set(TD_SLOTS);")
in_fn("function tdLab(){",DEP_SEL.format('tdxDepth'),'')
in_fn("function tdLab(){",'<select id="tdxSrc">','${slotChipsHTML(\'tdxSlots\',tdxLive)}\n    <select id="tdxSrc">')
in_fn("function tdLab(){","const dep=$('#tdxDepth').value,hin=$('#tdxInj').value;","const hin=$('#tdxInj').value;")
in_fn("function tdLab(){","(!dep||u.depth<=+dep)","slotOK(tdxLive,u.dslot||u.slot)")
in_fn("function tdLab(){","['tdxSrc','tdxDepth','tdxInj','tdxAvg'].forEach(id=>$('#'+id).onchange=render);","['tdxSrc','tdxInj','tdxAvg'].forEach(id=>$('#'+id).onchange=render);slotChipsWire('tdxSlots',tdxLive,render);")

# ---- Player Splits
in_fn("function splits(){","function splits(){","function splits(){const spLive=new Set(TD_SLOTS);")
in_fn("function splits(){",DEP_SEL.format('spDepth'),'')
in_fn("function splits(){",'<select id="spSe">','${slotChipsHTML(\'spSlots\',spLive)}\n    <select id="spSe">')
in_fn("function splits(){","dep=$('#spDepth').value,","")
in_fn("function splits(){","(!dep||u.depth<=+dep)","slotOK(spLive,u.dslot||u.slot)")
in_fn("function splits(){","['spSe','spDepth','spInj','spMin'].forEach(i=>$('#'+i).onchange=render);","['spSe','spInj','spMin'].forEach(i=>$('#'+i).onchange=render);slotChipsWire('spSlots',spLive,render);")

# ---- H2H Board
in_fn("function h2hLab(){","function h2hLab(){","function h2hLab(){const h2hLive=new Set(TD_SLOTS);")
in_fn("function h2hLab(){",DEP_SEL.format('h2hDepth'),'')
in_fn("function h2hLab(){",'<select id="h2hSe"','${slotChipsHTML(\'h2hSlots\',h2hLive)}\n    <select id="h2hSe"')
in_fn("function h2hLab(){","dep=$('#h2hDepth').value,","")
in_fn("function h2hLab(){","(!dep||u.depth<=+dep)","slotOK(h2hLive,u.dslot||u.slot)")
in_fn("function h2hLab(){","['h2hSe','h2hDepth','h2hInj','h2hMin','h2hAvg'].forEach(i=>$('#'+i).onchange=render);","['h2hSe','h2hInj','h2hMin','h2hAvg'].forEach(i=>$('#'+i).onchange=render);slotChipsWire('h2hSlots',h2hLive,render);")

# ---- Player Grid (F2) + Lab Grid (F6): one renderer
in_fn("function labGrid(){","function labGrid(){","function labGrid(){const lgLive=new Set(TD_SLOTS);")
in_fn("function labGrid(){",DEP_SEL.format('lgDepth'),'')
in_fn("function labGrid(){",'<select id="lgSrc"','${slotChipsHTML(\'lgSlots\',lgLive)}\n    <select id="lgSrc"')
in_fn("function labGrid(){","{dep:$('#lgDepth').value,hin:","{slots:lgLive.size?lgLive:null,hin:")
in_fn("function labGrid(){","['lgSrc','lgDepth','lgInj'].forEach(i=>$('#'+i).onchange=all);","['lgSrc','lgInj'].forEach(i=>$('#'+i).onchange=all);slotChipsWire('lgSlots',lgLive,all);")

# ---- Depth Delta (F3 + F6)
in_fn("function depthDelta(){","function depthDelta(){","function depthDelta(){const ddLive=new Set(TD_SLOTS);")
in_fn("function depthDelta(){",'<select id="ddDepth"><option value="2" selected>top 2 depths</option><option value="1">starters only</option><option value="">every depth</option></select>','')
in_fn("function depthDelta(){",'<select id="ddTeam">','${slotChipsHTML(\'ddSlots\',ddLive)}\n    <select id="ddTeam">')
in_fn("function depthDelta(){","dep=$('#ddDepth').value,","")
in_fn("function depthDelta(){","(!dep||r.u.depth<=+dep||r.kinds.includes('off'))","slotOK(ddLive,r.u.dslot||r.u.slot)")
in_fn("function depthDelta(){","['ddTeam','ddDepth'].forEach(i=>$('#'+i).onchange=render);","$('#ddTeam').onchange=render;slotChipsWire('ddSlots',ddLive,render);")

# ---- Markets (F5) + Markets v2 (F6): slot chips + search (the market rows already leave OUT players out)
M="function bets11(root='#bets',px=''){"
in_fn(M,"""<div class="r11top"><div class="tabs" id="${px}r11Tabs">${tabs}</div></div><div id="${px}mkKpi"></div>""",
        """<div class="r11top"><div class="tabs" id="${px}r11Tabs">${tabs}</div></div><div class="controls" id="${px}mkCtl">${slotChipsHTML(px+'mkSlots')}<input id="${px}mkQ" placeholder="search player..." size="15"><span class="note kept">OUT players never get a market, so they never appear here</span></div><div id="${px}mkKpi"></div>""")
in_fn(M,"let sortK='score',sortA=false,open=null;",
        "let sortK='score',sortA=false,open=null;const mkLive=new Set(TD_SLOTS);const mkKeep=r=>{const q=(($('#'+px+'mkQ')||{}).value||'').toLowerCase();return slotOK(mkLive,r.u.dslot||r.u.slot)&&(!q||r.u.player.toLowerCase().includes(q))};")
in_fn(M,"function playerTable(mk){const R=marketRows(mk);","function playerTable(mk){const R=marketRows(mk).filter(mkKeep);")
in_fn(M,"function tdTable(){const mk=MKT_BY.td;const R=marketRows(mk);","function tdTable(){const mk=MKT_BY.td;const R=marketRows(mk).filter(mkKeep);")
in_fn(M,"function render(){const O=$('#'+px+'mkOut');","function render(){const C=$('#'+px+'mkCtl');if(C)C.hidden=cur==='G';const O=$('#'+px+'mkOut');")
in_fn(M,"  RR.push(()=>{sortK=cur==='T'?'score':'score';render()})}",
        "  slotChipsWire(px+'mkSlots',mkLive,render);$('#'+px+'mkQ').oninput=render;\n  RR.push(()=>{sortK=cur==='T'?'score':'score';render()})}")

# ---- Weeklies: the slot chips replace the pool select + position chips; the global POS filter applies like everywhere else
W="function weeklies(){"
in_fn(W,"let W=null,show='sc';const posSet=new Set();","let W=null,show='sc';const CORE7=['QB1','RB1','RB2','WR1','WR2','WR3','TE1'],wkLive=new Set(CORE7);")
in_fn(W,"""<select id="wkPool" title="who counts"><option value="core" selected>starters: QB1 · RB1-2 · WR1-3 · TE1</option><option value="all">every slot that played</option></select>
    <span class="chips" id="wkPos" title="narrow the pool to one or more positions — click to toggle"><button data-p="" class="on">all</button>${TPOS.map(p=>`<button data-p="${p}">${posIcon(p,11)} ${p}</button>`).join('')}</span>""",
      """${slotChipsHTML('wkSlots',wkLive)}""")
in_fn(W,"const keep=x=>($('#wkPool').value==='all'||x.core)&&(!posSet.size||posSet.has(x.pos));","const keep=x=>slotOK(wkLive,x.slot)&&inP(x.pos);")
in_fn(W,"const poolL=()=>{const p=posSet.size?[...posSet].join(' / ')+' ':'';return $('#wkPool').value==='all'?`every ${p}player who played`:`the ${p}starters`};",
        "const poolL=()=>{const p=G.pos&&G.pos.size?[...G.pos].join(' / ')+' ':'';if(!wkLive.size)return `every ${p}player who played`;if(wkLive.size===CORE7.length&&CORE7.every(x=>wkLive.has(x)))return `the ${p}starters`;return `the ${p}${[...wkLive].join(' · ')} players`};")
in_fn(W,"$('#wkSe').onchange=()=>{W=null;render()};$('#wkPool').onchange=render;","$('#wkSe').onchange=()=>{W=null;render()};slotChipsWire('wkSlots',wkLive,render);")
in_fn(W,"""  $('#wkPos').querySelectorAll('button').forEach(b=>b.onclick=()=>{const p=b.dataset.p;if(!p)posSet.clear();else posSet.has(p)?posSet.delete(p):posSet.add(p);
    $('#wkPos').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.p?posSet.has(x.dataset.p):posSet.size===0));render()});
""","")
in_fn(W,"  render();\n}","  render();RR.push(render);\n}")

# ---- the "updated" chips on every tab that changed
once("const BOOT=[","""Object.assign(NOTES,{
 lab:['v18','the TD Grid\\'s slot chips replace the depth dropdown — click QB1 · RB1 · RB2 · WR1–WR4 · TE1 · TE2 on or off, ALL for every body on the chart; hide OUT and search unchanged'],
 tdbx:['v18','slot chips (QB1 · RB1 · RB2 · WR1–WR4 · TE1 · TE2, ALL for everyone) replace the depth dropdown, the same filter as the TD Grid'],
 labgridp:['v18','now carries the TD Grid\\'s player filter: slot chips in place of the depth dropdown, hide OUT, search'],
 labgrid:['v18','slot chips in place of the depth dropdown — the same player filter as the TD Grid'],
 h2hp:['v18','slot chips replace the depth dropdown — the same player filter as the TD Grid and H2H Grid'],
 splitsp:['v18','slot chips replace the depth dropdown — the same player filter as the TD Grid'],
 splits:['v18','slot chips replace the depth dropdown — the same player filter as the TD Grid'],
 ddeltap:['v18','slot chips replace the depth dropdown (a body that left the chart is filed under his old slot)'],
 ddelta:['v18','slot chips replace the depth dropdown (a body that left the chart is filed under his old slot)'],
 props:['v18','slot chips and a player search on every player market and anytime TD (hidden on game lines)'],
 markets2:['v18','slot chips and a player search on every player market and anytime TD (hidden on game lines)'],
 weeklies:['v18','the pool is now the slot chips (default = the starters, ALL = every slot that played) and it follows the POS filter in the top bar']});
const BOOT=[""")
open(T,'w',encoding='utf-8').write(s)
print('v18 filters patched')
