"""v40 — NCAA: (a) global LINES filter — only players with a book line this week (any / anytime TD / yardage-reception prop),
fed by J.lines from the Odds API CFB pull; (b) the CONF filter gains Power 4 and Group of 5 groups; (c) a player's card lists his
posted lines. NFL untouched (every NFL player is priced). Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'id="gLines"' in s:
    print('already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

# (a) control in the global bar, after CONF
rep('<span class="gl lgncaa" hidden>CONF</span><select class="lgncaa" id="gConf" hidden></select>',
    '<span class="gl lgncaa" hidden>CONF</span><select class="lgncaa" id="gConf" hidden></select>\n'
    '<span class="gl lgncaa" hidden>LINES</span><select class="lgncaa" id="gLines" hidden title="only players a sportsbook has posted a line on this week (Odds API: FanDuel / DraftKings / ESPN BET / BetRivers / BetMGM)"></select>')
# state
rep("const G={week:J.week||1,slates:new Set(),pos:new Set(),game:'',team:'',owner:'',conf:''};",
    "const G={week:J.week||1,slates:new Set(),pos:new Set(),game:'',team:'',owner:'',conf:'',lines:''};\n"
    "/* v40: book lines on CFB players (J.lines, 'player|team' -> {td,pr,b,m}); power-conference groups for the CONF filter */\n"
    "const LINES=J.cfbLines||{};const P4=new Set(['SEC','Big Ten','Big 12','ACC']);\n"
    "const CONF_GROUPS=[['__P4__','Power 4 (SEC · Big Ten · Big 12 · ACC)',t=>P4.has(t.conf)],['__G5__','Group of 5 + independents',t=>t.fbs&&!P4.has(t.conf)]];\n"
    "const confHas=(t,c)=>{const g=CONF_GROUPS.find(x=>x[0]===c);return g?g[2](TEAM[t]||{}):(TEAM[t]||{}).conf===c};\n"
    "const inL=(p,t)=>{if(!G.lines)return true;const x=LINES[p+'|'+t];return !!x&&(G.lines==='any'||(G.lines==='td'?!!x.td:!!x.pr))};")
# conf groups in recompute
rep("  if(G.conf){const c=new Set(Object.keys(TEAM).filter(t=>TEAM[t].conf===G.conf));ACT=ACT?new Set([...ACT].filter(t=>c.has(t))):c}",
    "  if(G.conf){const c=new Set(Object.keys(TEAM).filter(t=>confHas(t,G.conf)));ACT=ACT?new Set([...ACT].filter(t=>c.has(t))):c}")
# lines gate rides on the roster gate, which every player-level board already applies
rep("const inO=(p,t)=>!G.owner||", "const inO0=(p,t)=>!G.owner||")
rep("const inU=u=>inF(u.team)&&inO(u.player,u.team);", "const inO=(p,t)=>inL(p,t)&&inO0(p,t);\nconst inU=u=>inF(u.team)&&inO(u.player,u.team);")
# hash
rep("  if(h.get('conf')&&CONFS.includes(h.get('conf')))G.conf=h.get('conf');",
    "  if(h.get('conf')&&(CONFS.includes(h.get('conf'))||CONF_GROUPS.some(g=>g[0]===h.get('conf'))))G.conf=h.get('conf');\n"
    "  if(h.get('lines')&&['any','td','pr'].includes(h.get('lines')))G.lines=h.get('lines');")
rep("if(G.conf)h.set('conf',G.conf);", "if(G.conf)h.set('conf',G.conf);if(G.lines)h.set('lines',G.lines);")
# selects
rep("$('#gConf').innerHTML=`<option value=\"\">all conferences</option>`+CONFS.map(",
    "$('#gConf').innerHTML=`<option value=\"\">all conferences</option>`+CONF_GROUPS.map(g=>`<option value=\"${g[0]}\" ${g[0]===G.conf?'selected':''}>${g[1]}</option>`).join('')+`<option disabled>──</option>`+CONFS.map(")
rep("$('#gConf').onchange=()=>{G.conf=$('#gConf').value;apply()}}",
    "$('#gConf').onchange=()=>{G.conf=$('#gConf').value;apply()};\n"
    "    const nL=Object.keys(LINES).filter(k=>k!=='__asof__'),nTd=nL.filter(k=>LINES[k].td).length,nPr=nL.filter(k=>LINES[k].pr).length;\n"
    "    $('#gLines').innerHTML=`<option value=\"\">all players</option><option value=\"any\" ${G.lines==='any'?'selected':''}>has a line (${nL.length})</option><option value=\"td\" ${G.lines==='td'?'selected':''}>anytime TD line (${nTd})</option><option value=\"pr\" ${G.lines==='pr'?'selected':''}>yardage / reception prop (${nPr})</option>`;\n"
    "    $('#gLines').onchange=()=>{G.lines=$('#gLines').value;apply()}}")
rep("G.owner='';G.conf='';$('#gTeam').value='';$('#gOwner').value='';if($('#gConf'))$('#gConf').value='';apply()};",
    "G.owner='';G.conf='';G.lines='';$('#gTeam').value='';$('#gOwner').value='';if($('#gConf'))$('#gConf').value='';if($('#gLines'))$('#gLines').value='';apply()};")
rep("G.slates.clear();G.pos.clear();G.game='';G.team='';G.owner='';G.conf='';readHash();",
    "G.slates.clear();G.pos.clear();G.game='';G.team='';G.owner='';G.conf='';G.lines='';readHash();if($('#gLines'))$('#gLines').value=G.lines;if($('#gConf'))$('#gConf').value=G.conf;")
# summary line
rep("  $('#gSum').innerHTML=`wk ${G.week} · ${nG} game${nG===1?'':'s'} · ${nT} team${nT===1?'':'s'}`",
    "  $('#gSum').innerHTML=`wk ${G.week} · ${nG} game${nG===1?'':'s'} · ${nT} team${nT===1?'':'s'}`+(G.lines?` · <span style=\"color:#e8b100\">${G.lines==='td'?'anytime-TD lines only':G.lines==='pr'?'prop lines only':'priced players only'}</span>`:'')")
rep("+(G.conf?' · <b>'+esc(G.conf)+'</b>':'');", "+(G.conf?' · <b>'+esc(G.conf==='__P4__'?'Power 4':G.conf==='__G5__'?'Group of 5':G.conf)+'</b>':'');")
# (c) player card: his posted lines
rep("   <p style=\"margin-top:10px\"><button class=\"mclose\" style=\"position:static\" id=\"ppDeepBtn\">open full deep dive &rarr;</button></p>",
    "   ${ppLines(n,team)}\n   <p style=\"margin-top:10px\"><button class=\"mclose\" style=\"position:static\" id=\"ppDeepBtn\">open full deep dive &rarr;</button></p>")
rep("window.playerPop=function(n){",
    "/* v40: the book lines posted on a CFB player this week */\n"
    "const MKL={anytime_td:'anytime TD',rec_yds:'rec yds',receptions:'receptions',rush_yds:'rush yds',pass_yds:'pass yds',pass_td:'pass TD',rush_att:'rush att',pass_att:'pass att',completions:'completions',interceptions:'INT'};\n"
    "function ppLines(n,team){const x=LINES[n+'|'+team];if(!x)return IS_NFL||!Object.keys(LINES).length?'':'<p class=\"mini dim\" style=\"margin-top:8px\">no sportsbook line posted on him this week</p>';\n"
    "  const am=p=>p==null?'':(p>0?'+':'')+p;\n"
    "  return `<div class=\"panel\" style=\"margin-top:8px\"><h3>lines <span class=\"f\">posted this week · ${x.b} book${x.b===1?'':'s'} · as of ${esc(LINES.__asof__||'')}Z</span></h3><table class=\"fx\"><thead><tr><th style=\"text-align:left\">market</th><th>line</th><th>price</th><th>book</th></tr></thead><tbody>${x.m.map(r=>`<tr><td style=\"text-align:left\">${MKL[r[0]]||r[0]}</td><td>${r[1]==null?'—':r[1]}</td><td>${am(r[2])}</td><td class=\"dim\">${esc(r[3])}</td></tr>`).join('')}</tbody></table></div>`}\n"
    "window.playerPop=function(n){")
s = s.replace("Object.assign(NOTES,{v39:", "Object.assign(NOTES,{v40:['v40','NCAA: a LINES filter in the global bar keeps only players a sportsbook has priced this week (any line / anytime TD / yardage-reception prop) \\u00b7 CONF gains Power 4 and Group of 5 groups \\u00b7 a player card lists his posted lines']});\nObject.assign(NOTES,{v39:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v40 applied', len(s))
