"""v47 — refinement pass on the live week:
 (a) live touchdowns reach every week-ahead view: wkAhead's `done` falls back to J.liveTd, so Category Grid v1/v2 best picks,
     Weeklies v1 (the week ahead), player cards and Results all show ✓ as games are played, ✗ once a game has kicked off;
 (b) TD Picks live board: picks carry the live result; a "so far" tile (scored / graded, top-10 by model) replaces the static tiles
     once anything has kicked off; rows show ✓ / ✗;
 (c) First TD (week ahead): a "first scorers so far" strip — each game's first TD and where the board had him (rank, top pick ✓);
 (d) Results scorers panel: a board scorecard — for every board and data set, how many of today's scorers it had in its top
     quarter among the players it rated, vs the 25% a coin would give; category blocks order by hit rate once games finish;
 (e) META v2: ✓ beside a player who has scored; META v1: zero-weight columns dimmed with the reason in the header.
Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function liveFirst(' in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

# (a) wkAhead: done falls back to live
rep("    out.push(Object.assign(x,{u,name:u.player,team:u.team,slot:u.dslot||u.slot,raw,on,cs:on.length,score:on.reduce((s,k)=>s+Math.max(0,(TL[k.id]||1)-1),0),t:tdOf(u),done:done?{td:wkTD(done)}:null}))});",
    "    const lv=done?null:(typeof liveTdOf==='function'?liveTdOf(u.player,u.team):null),gmk=done||lv!=null?null:(typeof LIVE_TD!=='undefined'&&LIVE_TD&&kickedOff(gameOf(u.team,W0)));\n"
    "    out.push(Object.assign(x,{u,name:u.player,team:u.team,slot:u.dslot||u.slot,raw,on,cs:on.length,score:on.reduce((s,k)=>s+Math.max(0,(TL[k.id]||1)-1),0),t:tdOf(u),done:done?{td:wkTD(done)}:lv!=null?{td:lv,live:true}:gmk?{td:0,live:true,open:true}:null}))});")
# the live helpers must exist before wkAhead runs at BOOT: they are defined in the v46 block (before wkResults, which is before weeklies2) — wkAhead is called at render time, fine.

# (b) TD Picks: live results on the live board
rep("  if(w===T.week)return {m:'live',w,P:T.picks,g:T.games,d:T.dates};",
    "  if(w===T.week){if(typeof LIVE_TD!=='undefined'&&LIVE_TD&&LIVE_TD.week===w)T.picks.forEach(x=>{const lv=liveTdOf(x.n,x.t);x.res=lv!=null?lv:(kickedOff(gameOf(x.t,w))?0:null);x.live=x.res!=null});return {m:'live',w,P:T.picks,g:T.games,d:T.dates}}")
rep("    else $('#tpTiles').innerHTML=wkTile(`week ${T.week}`,String(T.games),`games · ${T.dates?T.dates[0].slice(5)+' to '+T.dates[1].slice(5):''}`)",
    "    else if(P.some(x=>x.res!=null)){const gr=P.filter(x=>x.res!=null),gk=gr.filter(x=>x.res>0).length,T10=gr.slice().sort((a,b)=>b.p-a.p).slice(0,10),k10=T10.filter(x=>x.res>0).length,LKg=lk.filter(x=>x.res!=null),lkk=LKg.filter(x=>x.res>0).length,open=P.filter(x=>x.res==null).length;\n"
    "      $('#tpTiles').innerHTML=wkTile(`week ${T.week} · in play`,`${gk}<span class=\"dim\"> / ${gr.length}</span>`,`listed players scored so far · ${pct(gk/gr.length)} · ${open} still to kick off`,gk/gr.length>=.3?'g':'')\n"
    "        +wkTile('top 10 so far',`${k10}<span class=\"dim\"> / ${T10.length}</span>`,'of the ten highest rated who have played',k10>=6?'g':k10<=3&&T10.length>=8?'r':'')\n"
    "        +wkTile('locks',LKg.length?`${lkk}<span class=\"dim\"> / ${LKg.length}</span>`:String(lk.length),LKg.length?'locks that have played, scored':(lk.slice(0,2).map(x=>esc(pshort(x.n))).join(' · ')||'none above 50%'),'g')\n"
    "        +wkTile('top 10 each week',BT.top10?pct(BT.top10[0]/BT.top10[1]):'—',`scored · ${BT.top10?BT.top10[0]+' of '+BT.top10[1]:''} blind picks`,'')\n"
    "        +wkTile('live record',rg?`${rw}-${rg-rw}`:'—',rg?`${pct(rw/rg)} of locked picks scored`:'locked picks, graded as they finish')}\n"
    "    else $('#tpTiles').innerHTML=wkTile(`week ${T.week}`,String(T.games),`games · ${T.dates?T.dates[0].slice(5)+' to '+T.dates[1].slice(5):''}`)")

# (c) First TD: first scorers so far
rep("function scorerPanel(){",
    "function liveFirst(){if(!LIVE_TD)return [];const by={};LIVE_TD.plays.forEach(p=>{const k=p.game;const cur=by[k];const t=(p.q||9)*10000-(parseInt(String(p.clock).split(':')[0]||0)*60+parseInt(String(p.clock).split(':')[1]||0));if(!cur||t<cur.t)by[k]={t,p}});return Object.values(by).map(x=>x.p)}\n"
    "function scorerPanel(){")
rep("    if(played){\n      const G=res.filter(r=>inF(r.team)||inF(r.vs))",
    "    const LF=typeof liveFirst==='function'&&!played?liveFirst().filter(p=>{const [a,h]=p.game.split('@');return inF(a)||inF(h)}):[];\n"
    "    $('#ftLive').innerHTML=LF.length?`<div class=\"panel\"><h3>first scorers so far <span class=\"f\">${LF.length} game${LF.length===1?'':'s'} with a touchdown · where the board had him · ✓ = the board's top pick for that game</span></h3><div class=\"wkpcs\">${LF.map(p=>{const [a,h]=p.game.split('@');const gb=D.board.filter(b=>(b.team===a&&b.opp===h)||(b.team===h&&b.opp===a)).sort((x,y)=>y.p_first-x.p_first);const i=gb.findIndex(b=>nmKey(b.player)===nmKey(p.player)&&b.team===p.team);const top=gb[0]&&nmKey(gb[0].player)===nmKey(p.player);\n"
    "      return `<span class=\"wkpc ${top?'w':i<0?'l':''}\" title=\"${esc(p.game)} · Q${p.q} ${esc(p.clock)} · ${p.how}${i>=0?' · board rank '+(i+1)+' of '+gb.length+' · '+(100*gb[i].p_first).toFixed(1)+'%':' · not on the board'}\">${pn(p.player,p.team,true)}<i>${esc(p.game)} · ${i>=0?'#'+(i+1)+' of '+gb.length:'off board'}</i>${top?'<b>✓</b>':''}</span>`}).join('')}</div></div>`:'';\n"
    "    if(played){\n      const G=res.filter(r=>inF(r.team)||inF(r.vs))")
# a holder for it: find the First TD panel markup root
i = s.index("function firstTd("); j = s.index("function render(){const W=G.week,played=", i)
seg = s[i:j]
assert 'id="ftTiles"' in seg, 'ftTiles holder'
seg2 = seg.replace('id="ftTiles"', 'id="ftTiles"', 1)
k = seg2.index('id="ftTiles"'); e = seg2.index('</div>', k) + len('</div>')
seg2 = seg2[:e] + '<div id="ftLive"></div>' + seg2[e:]
s = s[:i] + seg2 + s[j:]

# (d) board scorecard in the scorers panel + ordered category blocks
rep("  const hit=(r,f)=>R.filter(f).length;\n  const sum=",
    "  const hit=(r,f)=>R.filter(f).length;\n"
    "  const SC={};R.forEach(r=>r.calls.forEach(c=>{const o=SC[c.k]=SC[c.k]||{k:c.k,grp:c.grp,n:0,q:0,t:0};o.n++;if(c.pct<=.25)o.q++;if(c.pct<=.1)o.t++}));\n"
    "  const card=Object.values(SC).filter(o=>o.n>=5).sort((a,b)=>b.q/b.n-a.q/a.n||b.t-a.t);\n"
    "  const scorecard=card.length?`<div class=\"scb\"><span class=\"gl\">board scorecard</span>${card.map(o=>`<span class=\"scall\" style=\"${gradeStyle(1+(1-Math.min(1,o.q/o.n/.5))*(NT-1))}\" title=\"${esc(o.k)}: of the ${o.n} scorers it rated, ${o.q} were in its top quarter (${Math.round(100*o.q/o.n)}% · a coin gives 25%), ${o.t} in its top tenth\">${esc(o.k)} <b>${Math.round(100*o.q/o.n)}%</b><i>${o.q}/${o.n}</i></span>`).join('')}</div>`:'';\n"
    "  const sum=")
rep("    <div class=\"tscroll\"><table class=\"fx sct\">", "    ${scorecard}<div class=\"tscroll\"><table class=\"fx sct\">")
rep("      const blocks=SG.filter(s=>!st.cats.size||st.cats.has(s.id)).map(s=>{",
    "      const ordered=SG.filter(s=>!st.cats.size||st.cats.has(s.id)).map(s=>{const L=R.filter(x=>x.ids.has(s.id)),g=L.filter(x=>x.res!=null).length,k=L.filter(x=>x.res>0).length;return {s,hr:g>=3?k/g:-1,g}}).sort((a,b)=>(a.s.kind==='neg')-(b.s.kind==='neg')||b.hr-a.hr||b.g-a.g).map(o=>o.s);\n"
    "      const blocks=ordered.map(s=>{")
rep("/* v46 */.scall{", "/* v47 */.scb{display:flex;flex-wrap:wrap;gap:2px 4px;align-items:center;margin:0 0 8px}.scb>.gl{margin-right:6px}\n/* v46 */.scall{")

# (e) META v2 ✓ ; META v1 dim zero-weight headers
rep("      ${R.map(x=>`<tr><td class=\"plink\" data-p=\"${esc(x.u.player)}\" title=\"${esc(x.u.player)} · ${esc(x.u.dslot||x.u.slot)} · ${esc(x.u.team)}\">${esc(pshort(x.u.player))}${x.u.inj==='0'?' <span class=\"inj0\">Q</span>':x.u.inj==='-1'?' <span class=\"injm1\">OUT</span>':''}</td>\n        ${p==='ALL'?`<td>${posIcon(x.pos,10,x.u.dslot||x.u.slot)}</td>`:''}<td>${x.opp?oppcell(x.oppRaw):'<span class=\"dim\">bye</span>'}</td>\n        ${x.cons==null?",
    "      ${R.map(x=>{const lv=typeof liveTdOf==='function'?liveTdOf(x.u.player,x.u.team):null;return `<tr><td class=\"plink\" data-p=\"${esc(x.u.player)}\" title=\"${esc(x.u.player)} · ${esc(x.u.dslot||x.u.slot)} · ${esc(x.u.team)}\">${esc(pshort(x.u.player))}${lv?` <b style=\"color:var(--green)\" title=\"${lv} TD so far\">✓${lv>1?lv:''}</b>`:''}${x.u.inj==='0'?' <span class=\"inj0\">Q</span>':x.u.inj==='-1'?' <span class=\"injm1\">OUT</span>':''}</td>\n        ${p==='ALL'?`<td>${posIcon(x.pos,10,x.u.dslot||x.u.slot)}</td>`:''}<td>${x.opp?oppcell(x.oppRaw):'<span class=\"dim\">bye</span>'}</td>\n        ${x.cons==null?")
# close the arrow-function body we opened: the row template ends with `</tr>`).join('')
i2 = s.index("function metaV2("); j2 = s.index("/* ---------------- METAPROP (F6 TEST, v23)", i2); seg = s[i2:j2]
old_end = "        ${ks.map(k=>cell(k,x)).join('')}</tr>`).join('')||`<tr><td colspan=\"${ks.length+6}\" class=\"dim\">nothing matches</td></tr>`}</tbody></table>`;"
assert seg.count(old_end) == 1, 'metav2 row end'
seg = seg.replace(old_end, "        ${ks.map(k=>cell(k,x)).join('')}</tr>`}).join('')||`<tr><td colspan=\"${ks.length+6}\" class=\"dim\">nothing matches</td></tr>`}</tbody></table>`;")
s = s[:i2] + seg + s[j2:]
# META v1 headers: zero weight → dim + note
rep("    $$('G'+p).textContent=`ranked by ${LBL[st.k]||st.k} · ${setL()}`;\n    const th=(k,l,tip,cls)=>`<th class=\"${cls||''}\" data-k=\"${k}\" title=\"${esc(tip||'')}\">${l}${st.k===k?(st.a?' ▲':' ▼'):''}</th>`;\n    const S=sigs(),wname=p==='ALL'?24:29",
    "    $$('G'+p).textContent=`ranked by ${LBL[st.k]||st.k} · ${setL()}`;\n    const nw=k=>SIGS.includes(k)&&k!=='meta'&&!(META_W[k]>0);   /* a column the backtest left without weight: shown for the read, dimmed */\n    const th=(k,l,tip,cls)=>`<th class=\"${cls||''}${nw(k)?' nw':''}\" data-k=\"${k}\" title=\"${esc((tip||'')+(nw(k)?' · no weight in META (the backtest found it adds nothing once Ψ is in) — shown for the read':''))}\">${l}${st.k===k?(st.a?' ▲':' ▼'):''}</th>`;\n    const S=sigs(),wname=p==='ALL'?24:29")
rep("/* v47 */.scb{", "/* v47 */th.nw{opacity:.55}.scb{")
s = s.replace("Object.assign(NOTES,{v46:", "Object.assign(NOTES,{v47:['v47','live touchdowns reach every week-ahead view (Category Grid, Weeklies, TD Picks, META v2) \\u00b7 First TD shows each game\\'s first scorer so far against the board \\u00b7 the scorers panel grades every board on today\\'s scorers \\u00b7 META v1 dims the columns that carry no weight']});\nObject.assign(NOTES,{v46:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v47 applied', len(s))
