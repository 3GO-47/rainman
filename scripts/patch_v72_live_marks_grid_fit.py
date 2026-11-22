"""v72 — three things, one pass.
1. The v67 check-off boxes are removed everywhere (Category Grid table + lead cards, the category pane, Category Grid v2).
   Names get their full width back. v67's CSS had also overwritten the older .scb bar class; that is restored.
2. The existing scored marks (the green tick / red cross, the 'who has scored' panel, the TD Board results) now refresh on their
   own: while the live week is on screen the page reads ESPN's public scoreboard + per-game scoring plays straight from the
   browser (every 45 s with a game on, slower between slates, off once every game is final) and feeds the same LIVE_TD path
   the 6-hourly loop file feeds. Only a game whose score or state moved is re-read. WSH/LA/JAC are mapped to the dash's codes
   (Washington never matched before).
3. Player Grid fits: two tables per row from 1280 px, four from 2560 px, one below; fixed pixel columns for name / opp / psi /
   RZ / L5 / SCORE with the stat columns sharing the rest; rank subscripts lose their box; headers never wrap or clip.
Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v72 */' in s:
    print('v72 already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:110])
    s = s.replace(old, new)
def cut(a, b, new=''):
    """drop everything from marker a up to (not including) marker b"""
    global s
    assert s.count(a) == 1 and s.count(b) >= 1, (s.count(a), s.count(b), a[:80])
    i = s.index(a); j = s.index(b, i)
    s = s[:i] + new + s[j:]

# ---------- 1. the check-off boxes go ----------
cut("/* v67 */const SCM={};", "const wgName=x=>`<span class=\"plink\" data-p=\"${esc(x.name)}\"",
    "/* v67 */ /* the check-off boxes were removed in v72: the scored marks refresh live instead */\n")
rep("""title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${scBox(x.name)}${esc(pshort(x.name))}${x.done?""",
    """title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${esc(pshort(x.name))}${x.done?""")
rep("""      ${R.map(x=>`<tr${scHas(x.name,CS.W0)?' class="scored"':''}><td class="plink" data-p="${esc(x.name)}" title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${scBox(x.name,CS.W0)}<span class="scn">${esc(pshort(x.name))}</span>""",
    """      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.name)}" title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${esc(pshort(x.name))}""")
rep("""    <span class="mini scc"></span>
""", """    <span class="mini livestamp"></span>
""")
rep("lead();scPaint()};", "lead();liveStamp()};")
rep("""      ${A.map(x=>`<tr${scHas(x.name,W0)?' class="scored"':''}><td>${scBox(x.name,W0)}${pn(x.name,x.team,true)}""",
    """      ${A.map(x=>`<tr><td>${pn(x.name,x.team,true)}""")
rep("""<span class="wkpc ${x.done?(x.done.td>0?'w':'l'):''}${scHas(x.name)?' scored':''}">${scBox(x.name)}${pn(x.name,x.team,true)}""",
    """<span class="wkpc ${x.done?(x.done.td>0?'w':'l'):''}">${pn(x.name,x.team,true)}""")
rep("""      ${L.map(x=>`<tr${scHas(x.name)?' class="scored"':''}><td>${scBox(x.name)}${pn(x.name,x.team,true)}</td>""",
    """      ${L.map(x=>`<tr><td>${pn(x.name,x.team,true)}</td>""")
cut("/* v67 */.scb{display:inline-block;", "/* v68 */sub.trk{")   # the three v67 lines only
for dead in ('scBox(', 'scHas(', 'scPaint(', 'data-sc'):
    assert dead not in s, dead

# ---------- 2. the scored marks refresh themselves ----------
rep("const LIVE_TD=(J.liveTd&&J.liveTd.week===J.week&&J.liveTd.season===(J.season||2026))?J.liveTd:null;",
    """/* v72 */const LIVE_AB={WSH:'WAS',LA:'LAR',JAC:'JAX'},liveAb=t=>LIVE_AB[t]||t,liveGk=k=>String(k).split('@').map(liveAb).join('@');
function liveNorm(d){if(!d)return d;const fx=o=>{const r={};Object.keys(o||{}).forEach(k=>r[liveGk(k)]=o[k]);return r};
  return Object.assign({},d,{games:fx(d.games),scores:fx(d.scores),plays:(d.plays||[]).map(p=>Object.assign({},p,{team:liveAb(p.team),game:liveGk(p.game)}))})}
let LIVE_TD=(J.liveTd&&J.liveTd.week===J.week&&J.liveTd.season===(J.season||2026))?liveNorm(J.liveTd):null;""")
rep("const liveRes=(name,team)=>{const lv=liveTdOf(name,team);if(lv!=null)return lv;return liveState(team)==='post'?0:null};const liveOpen=team=>liveState(team)==='in';",
    """const liveRes=(name,team)=>{const lv=liveTdOf(name,team);if(lv!=null)return lv;return liveState(team)==='post'?0:null};const liveOpen=team=>liveState(team)==='in';
/* v72: the same file, read straight from ESPN in this browser while games are on — so a touchdown shows within a minute
   instead of at the next loop push. Only a game whose score or state moved is re-read; a final game is read three times, then left. */
const LIVE_API='https://site.api.espn.com/apis/site/v2/sports/football/nfl/',LIVE_SUM={},LIVE_POLL={busy:false,t:null,at:null,err:0,on:false,sig:''};
/* what a redraw depends on: game states, who has scored, and the score of games that are final (in-game field goals do not redraw) */
const liveSig=d=>d?JSON.stringify([d.games,d.plays.map(p=>p.player+'|'+p.team),Object.keys(d.scores||{}).filter(k=>(d.games||{})[k]==='post').map(k=>k+d.scores[k])]):'';
function liveStamp(){const P=LIVE_POLL,n=LIVE_TD&&liveOK()?liveScorers().length:0;
  const txt=!LIVE_TD||!liveOK()?'':P.at?`<b style="color:var(--green)">●</b> scored marks live · ${n} scorer${n===1?'':'s'} · checked ${P.at.toLocaleTimeString([], {hour:'numeric',minute:'2-digit',second:'2-digit'})}${P.on?'':' · all games final'}`
    :`scored marks as of ${esc(String(LIVE_TD.pulled||'').replace('T',' '))}`;
  document.querySelectorAll('.livestamp').forEach(e=>e.innerHTML=txt)}
function liveSet(d){LIVE_TD=d;J.liveTd=d;LIVE_SC=null;LIVE_IX=null;for(const k in LIVE_ST)delete LIVE_ST[k];if(J.tdpicks)J.tdpicks._lv=0;
  if(!liveOK())return;const vis=[...document.querySelectorAll('#legacyNav nav button')].find(b=>b.classList.contains('on')),v=vis?vis.dataset.v:'home';
  new Set(RRV.map(e=>e.v)).forEach(x=>{if(x!==v)DIRTY.add(x)});if(typeof PCACHE!=='undefined')for(const k in PCACHE)delete PCACHE[k];
  const y=scrollY;runView(v);scrollTo(0,y)}
async function livePoll(){const P=LIVE_POLL;if(P.busy)return;clearTimeout(P.t);if(document.hidden){P.t=setTimeout(livePoll,30000);return}
  P.busy=true;let next=60000;
  try{const get=u=>fetch(LIVE_API+u,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()});
    const sb=await get('scoreboard'),wk=(sb.week||{}).number,se=(sb.season||{}).year;
    if(wk!==J.week||se!==(J.season||2026)){P.on=false;P.busy=false;return}
    const games={},scores={},byEv={},now=Date.now();let anyIn=false,kick=null;
    await Promise.all((sb.events||[]).map(async ev=>{const c=ev.competitions[0],st=c.status.type.state,H=c.competitors.find(t=>t.homeAway==='home'),A=c.competitors.find(t=>t.homeAway==='away');
      const key=liveAb(A.team.abbreviation)+'@'+liveAb(H.team.abbreviation),sc=[+A.score,+H.score];games[key]=st;if(sc.every(Number.isFinite))scores[key]=sc;
      if(st==='in')anyIn=true;if(st==='pre'){const t=Date.parse(ev.date);if(Number.isFinite(t)&&(kick==null||t<kick))kick=t;return}
      const sig=st+'|'+sc.join('-');let m=LIVE_SUM[ev.id];
      /* a final the loop file already holds at the same score needs no read at all */
      if(!m&&st==='post'&&LIVE_TD&&LIVE_TD.games&&LIVE_TD.games[key]==='post'&&String((LIVE_TD.scores||{})[key])===String(sc))m=LIVE_SUM[ev.id]={sig,n:9,plays:LIVE_TD.plays.filter(p=>p.game===key)};
      if(!m||st==='in'||m.sig!==sig||m.n<3){try{const sm=await get('summary?event='+ev.id),pl=[];
          (sm.scoringPlays||[]).forEach(x=>{if(((x.scoringType||{}).name)!=='touchdown'&&!String((x.type||{}).abbreviation||'').includes('TD'))return;
            const t=x.text||'',mm=t.match(/^(.+?) \\d+ Yd (Rush|Pass|Interception Return|Fumble Return|Kickoff Return|Punt Return|Blocked)/i);
            const hw=mm?(/pass/i.test(mm[2])?'rec':/rush/i.test(mm[2])?'rush':'ret'):'?';
            pl.push({game:key,q:(x.period||{}).number,clock:(x.clock||{}).displayValue,team:liveAb((x.team||{}).abbreviation),player:mm?mm[1]:t.slice(0,40),how:hw})});
          m=LIVE_SUM[ev.id]={sig,n:m&&m.sig===sig?m.n+1:1,plays:pl}}catch(e){if(!m)m={sig:'',n:0,plays:LIVE_TD?LIVE_TD.plays.filter(p=>p.game===key):[]}}}
      byEv[ev.id]=m.plays}));
    const plays=[];(sb.events||[]).forEach(ev=>(byEv[ev.id]||[]).forEach(p=>plays.push(p)));
    const d={pulled:new Date().toISOString().slice(0,16)+'Z',season:se,week:wk,source:'ESPN scoreboard + scoring plays, read in this browser',games,scores,plays};
    P.at=new Date();P.err=0;const settling=Object.values(LIVE_SUM).some(m=>m.n<3);
    P.on=anyIn||kick!=null||settling;
    next=anyIn||settling?45000:kick!=null?Math.min(900000,Math.max(60000,kick-now-60000)):0;
    const sig=liveSig(d);if(sig!==P.sig){P.sig=sig;if(!LIVE_TD||sig!==liveSig(LIVE_TD))liveSet(d)}
  }catch(e){P.err++;next=Math.min(600000,60000*P.err)}
  P.busy=false;liveStamp();if(next)P.t=setTimeout(livePoll,next)}
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&LIVE_POLL.on&&!LIVE_POLL.busy)livePoll()});
setTimeout(livePoll,1200);""")

# ---------- 3. Player Grid fits ----------
# v68 gave the rank subscript the class of the bet-tracking button (.trk): it inherited that button's box, padding and 11px font
rep('<sub class="trk">', '<sub class="rks">')
rep('/* v68 */sub.trk{', '/* v68 */sub.rks{')
rep("const nstat=heads.length+4, wname=18, wopp=9, wfix=[5,5,6.5,6.5], wnum=((100-wname-wopp-23)/heads.length).toFixed(2);",
    "const wfix=[34,34,38,56];/* v72: fixed pixel columns; the stat columns share what is left */")
rep("""<colgroup><col style="width:${wname}%"><col style="width:${wopp}%">${
      Array.from({length:heads.length},()=>`<col style="width:${wnum}%">`).join('')}${wfix.map(w=>`<col style="width:${w}%">`).join('')}</colgroup>""",
    """<colgroup><col class="cnm"><col class="cop">${
      Array.from({length:heads.length},()=>`<col>`).join('')}${wfix.map((w,i)=>`<col class="cf${i}" style="width:${w}px">`).join('')}</colgroup>""")
rep("""<th class="md">model</th><th class="md" colspan="3" title="his own numbers: red-zone share, last-5 trend and the fitted score">him</th></tr>""",
    """<th class="md" colspan="4" title="Ψ = the matchup in one number · then his own: red-zone share, last-5 trend and the fitted score">matchup · him</th></tr>""")
rep("</style>", """/* v72 */#labgrid .lgrid{grid-template-columns:minmax(0,1fr)!important}
@media(min-width:1280px){#labgrid .lgrid{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
@media(min-width:2560px){#labgrid .lgrid{grid-template-columns:repeat(4,minmax(0,1fr))!important}}
#labgrid table.lgt col.cnm{width:170px}#labgrid table.lgt col.cop{width:60px}
#labgrid table.lgt th,#labgrid table.lgt td{padding-left:3px;padding-right:3px}
#labgrid table.lgt th{white-space:nowrap!important;overflow:hidden!important}
#labgrid table.lgt .badge{padding:0 2px}#labgrid table.lgt td.op{padding-left:2px;padding-right:2px}#labgrid sub.rks{margin-left:1px}
#labgrid table.lgt td .tc img,#labgrid table.lgt td img.tl{margin-right:3px}
@media(max-width:700px){#labgrid table.lgt{width:100%!important;min-width:0!important}#labgrid sub.rks,#labgrid table.lgt td img.tl,#labgrid table.lgt .incb{display:none}#labgrid table.lgt td.plink{font-size:10.5px}#labgrid table.lgt col.cnm{width:118px}#labgrid table.lgt col.cop{width:46px}
 #labgrid table.lgt col.cf1,#labgrid table.lgt col.cf2{width:0!important}#labgrid table.lgt col.cf0{width:22px!important}#labgrid table.lgt col.cf3{width:36px!important}
 #labgrid table.lgt tr.hd th:nth-last-child(2),#labgrid table.lgt tr.hd th:nth-last-child(3),#labgrid table.lgt td:nth-last-child(2),#labgrid table.lgt td:nth-last-child(3){padding:0!important;border:0!important;font-size:0!important}
 #labgrid table.lgt td:nth-last-child(2) *,#labgrid table.lgt td:nth-last-child(3) *{display:none}
 #labgrid table.lgt th,#labgrid table.lgt td{padding-left:2px;padding-right:2px}#labgrid table.lgt .badge{padding:0 2px}#labgrid table.lgt td .tc img,#labgrid table.lgt tr.grp{display:none}}
@media(max-width:380px){#labgrid table.lgt col.cnm{width:114px}#labgrid table.lgt col.cf0{width:0!important}
 #labgrid table.lgt tr.hd th:nth-last-child(4),#labgrid table.lgt td:nth-last-child(4){padding:0!important;border:0!important;font-size:0!important}#labgrid table.lgt td:nth-last-child(4) *{display:none}}
</style>""")
# ---------- 4. Category Grid fits too: as many tables per row as have room for full names, never five squeezed across ----------
rep("const W=p==='ALL'?[26,5,19,8,11,8,23]:[31,0,20,8,11,8,22];",
    "const W=p==='ALL'?[0,28,60,46,40,40,92]:[0,-1,60,46,40,40,92];/* v72: pixels · 0 = the name takes what is left · -1 = no such column */")
rep("""<colgroup>${W.map(w=>w?`<col style="width:${w}%">`:'').join('')}</colgroup>""",
    """<colgroup>${W.map((w,i)=>w<0?'':w?`<col class="wc${i}" style="width:${w}px">`:'<col>').join('')}</colgroup>""")
rep("</style>", """.lgrid.wg{grid-template-columns:repeat(auto-fill,minmax(min(456px,100%),1fr))!important}
.lgrid.wg table.lgt th,.lgrid.wg table.lgt td{padding-left:3px;padding-right:3px}.lgrid.wg table.lgt th{white-space:nowrap!important;overflow:hidden!important}
@media(max-width:700px){.lgrid.wg table.lgt{width:100%!important;min-width:0!important}.lgrid.wg table.lgt td .tc img{display:none}.lgrid.wg col.wc1{width:24px!important}.lgrid.wg col.wc2{width:44px!important}
 .lgrid.wg col.wc3{width:42px!important}.lgrid.wg col.wc4{width:32px!important}.lgrid.wg col.wc5{width:36px!important}.lgrid.wg col.wc6{width:58px!important}.lgrid.wg td.plink{font-size:10.5px}.lgrid.wg td.plink img.tl{display:none}.lgrid.wg table.lgt th,.lgrid.wg table.lgt td{padding-left:2px;padding-right:2px}}
</style>""")
open(P, 'w', encoding='utf-8').write(s); print('v72 applied')
