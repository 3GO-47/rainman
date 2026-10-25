"""v45 — the global bar (slate · game · team · conf · roster · lines) now gates the current-week player lists on every Weeklies
view: Weeklies v1 + v2 (the week's bars, who scored, called-but-no-TD), Category Grid v1 + v2 (best picks, everyone carrying a
category, the grading tile). Historical reliability (which categories beat the field, week by week) stays judged on the whole
field. Results opens on the current slate (the week ahead) when the picked week isn't graded, and gains a "by category" view:
every category as a block with the players carrying it into this week's games. Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'const w2now=' in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

# shared gate: the global bar on a Weeklies row (played game) or a wkAhead row
rep("const w2res=x=>x.td>0?", "const w2now=x=>w2keep(x)&&inF(x.team)&&inO(x.name,x.team);   /* v45: the global bar on the week's own lists */\nconst gbOn=()=>!!(ACT||G.owner||G.lines);\nconst w2res=x=>x.td>0?")
# Weeklies v2: the displayed week's stats honour the bar (history grid stays on the whole field)
rep("    const AL=F.weeks.filter(w=>w<=W).map(w=>wkStats(F,w,w2keep,SG)),st=AL[AL.length-1];",
    "    const AL=F.weeks.filter(w=>w<=W).map(w=>wkStats(F,w,w2keep,SG)),st=gbOn()?wkStats(F,W,w2now,SG):AL[AL.length-1];")
rep("$('#w2Note').innerHTML=W===G.week?`week ${W} · ${S} · ${st.P.length} starters in view (QB1, RB1–2, WR1–3, TE1)`",
    "$('#w2Note').innerHTML=W===G.week?`week ${W} · ${S} · ${st.P.length} starters in view (QB1, RB1–2, WR1–3, TE1)${gbOn()?' · narrowed by the global bar':''}`")
# Category Grid v2 + v1 (wgData feeds both): current-week rows through the bar
rep("  const AH=wkAhead(u=>slotOK(live,u.dslot||u.slot)&&inP(u.pos),TR,W0);",
    "  const AH=wkAhead(u=>slotOK(live,u.dslot||u.slot)&&inP(u.pos)&&inF(u.team)&&inO(u.player,u.team),TR,W0);")
rep("const W0=Math.max(2,G.week),D=wgData(W2CORE,'cur',null,W0),R=D.R.filter(x=>inP(x.pos)),B=D.best.filter(x=>inP(x.pos))",
    "const W0=Math.max(2,G.week),D=wgData(W2CORE,'cur',null,W0),R=D.R.filter(x=>inP(x.pos)),B=D.best.filter(x=>inP(x.pos))   /* v45: D.R already passed the global bar */")
# Weeklies v1: the week-ahead list through the bar
rep("keepU=u=>slotOK(wkLive,u.dslot||u.slot)&&inP(u.pos),AH=wkAhead(keepU,TR,W0)",
    "keepU=u=>slotOK(wkLive,u.dslot||u.slot)&&inP(u.pos)&&inF(u.team)&&inO(u.player,u.team),AH=wkAhead(keepU,TR,W0)")
# wkTrust cache keys must not mix filtered and unfiltered pools: wgData's key already carries slots+pos; AH is filtered after TR, fine.

# ---- Results: open on the slate ahead; by-category view ----
rep("  const st={se:LAST_SE,scope:'week',res:'',mode:'any',core:true,min:0,q:'',cats:new Set(),lim:400};",
    "  const graded=wkFeat(LAST_SE).weeks.includes(G.week);\n  const st={se:LAST_SE,scope:graded?'week':'ahead',res:'',mode:'any',core:true,min:0,q:'',cats:new Set(),lim:400,view:'cat'};")
rep("    <select id=\"wrScope\" title=\"which games the rows come from\"><option value=\"week\">the week picked up top</option><option value=\"all\">every graded week of the season</option><option value=\"ahead\">the week ahead (not played yet)</option></select>",
    "    <select id=\"wrScope\" title=\"which games the rows come from\"><option value=\"ahead\">this week's slate (the games ahead)</option><option value=\"week\">the week picked up top, once graded</option><option value=\"all\">every graded week of the season</option></select>\n    <span class=\"chips\" id=\"wrView\" title=\"one block per category, or one flat table\"><button data-v=\"cat\" class=\"on\">by category</button><button data-v=\"tbl\">table</button></span>")
rep("    <div class=\"panel\"><div id=\"wrTbl\" class=\"tscroll\"></div><p class=\"mini dim\" id=\"wrMore\"></p></div>`;",
    "    <div id=\"wrBy\"></div><div class=\"panel\" id=\"wrTblP\"><div id=\"wrTbl\" class=\"tscroll\"></div><p class=\"mini dim\" id=\"wrMore\"></p></div>`;\n  $('#wrScope').value=st.scope;")
rep("    const show=R.slice(0,st.lim);\n    $('#wrTbl').innerHTML=",
    "    $('#wrBy').hidden=st.view!=='cat';$('#wrTblP').hidden=st.view==='cat';\n"
    "    if(st.view==='cat'){const base=gr?sc/gr:null;const tp=x=>x.t&&x.t.p!=null?Math.round(100*+x.t.p)+'%':(x.tp&&x.tp.p!=null?Math.round(100*x.tp.p)+'%':'');\n"
    "      const chip=x=>`<span class=\"wkpc ${x.res==null?'':x.res>0?'w':'l'}\">${pn(x.name,x.team,true)}<i>${x.raw?esc(x.raw):(x.l?esc(x.l[LOG.opp]):'')}${tp(x)?' · '+tp(x):''}${x.cs?' · '+x.cs+' sig':''}</i>${x.res==null?(x.open?'<b class="dim" title="in play, no TD yet">·</b>':''):`<b>${x.res>0?'✓':'✗'}</b>`}</span>`;\n"
    "      const blocks=SG.filter(s=>!st.cats.size||st.cats.has(s.id)).map(s=>{const L=R.filter(x=>x.ids.has(s.id)).sort((a,b)=>(b.res??-1)-(a.res??-1)||b.cs-a.cs);if(!L.length)return '';const k=L.filter(x=>x.res>0).length,g=L.filter(x=>x.res!=null).length;\n"
    "        return `<div class=\"panel wrcat${s.kind==='neg'?' neg':''}\"><h3>${esc(s.lbl)} <span class=\"f\">${esc(s.long)} · ${L.length} player${L.length===1?'':'s'}${g?` · ${k} scored (${Math.round(100*k/g)}%${base!=null?' vs field '+Math.round(100*base)+'%':''})`:''}${s.kind==='neg'?' · fade':''}</span></h3><div class=\"wkpcs\">${L.map(chip).join('')}</div></div>`}).join('');\n"
    "      $('#wrBy').innerHTML=blocks||'<p class=\"note mini\">nothing matches</p>';tWire($('#wrBy'));logoize($('#wrBy'))}\n"
    "    const show=R.slice(0,st.lim);\n    $('#wrTbl').innerHTML=")
rep("    $('#wrN').innerHTML=`${st.scope==='week'&&st.shown!=null?",
    "    $('#wrN').innerHTML=`${st.scope==='ahead'?`week ${G.week} slate · `:''}${st.scope==='week'&&st.shown!=null?")
rep("  $('#wrRes').onchange=()=>{st.res=$('#wrRes').value;render()};",
    "  $('#wrView').querySelectorAll('button').forEach(b=>b.onclick=()=>{st.view=b.dataset.v;$('#wrView').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render()});\n  $('#wrRes').onchange=()=>{st.res=$('#wrRes').value;render()};")
# the ahead rows carry x.t (TD Picks) from wkAhead; played rows don't — chip handles both
rep("/* v43 results */", "/* v45 */.wrcat{margin:0 0 8px}.wrcat h3{margin-bottom:4px}.wrcat.neg h3{opacity:.8}\n/* v43 results */")
rep(" wkres:{what:'The Weeklies data as one table.',how:['one row per player-game: the week, who, where, what happened (TD · PPR) and every Weeklies category he carried INTO that game',",
    " wkres:{what:'The Weeklies picks, by category, for the games ahead.',how:['opens on this week\\'s slate: one block per category with every player carrying it into his game (TD Picks chance, core-signal count; ✓ / ✗ land as games finish) — switch to the table for one row per player-game',")
s = s.replace("Object.assign(NOTES,{v44:", "Object.assign(NOTES,{v45:['v45','the global bar (slate \\u00b7 game \\u00b7 team \\u00b7 roster) now narrows the week\\'s lists on Weeklies v1/v2 and Category Grid v1/v2 \\u00b7 Results opens on the slate ahead with one block per category']});\nObject.assign(NOTES,{v44:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v45 applied', len(s))
