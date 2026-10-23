"""v39 — First TD tab under F5 Picks (data: scripts/build_first_td.py -> J.firstTd). Follows the global week: played week =
who scored first in every game; upcoming week = the board (model P(first), fair odds, Kalshi, edge). Every tile opens its
history, every table sorts and is shaded. Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function firstTd()' in s:
    print('already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

rep("c:'test',sub:'tdpicks'},", "c:'test',sub:'tdpicks'},\n   {id:'firsttd',nfl:true,label:'First TD',desc:'first touchdown scorer: for a played week, who scored first in every game (and each team\\'s first); for the week ahead, every slot owner\\'s chance to score the game\\'s first TD, fair odds, the Kalshi price and the edge \\u2014 plus which slot scores first against each defense, each offense\\'s habits, and the model\\'s own record',c:'test',sub:'firsttd'},")
rep("<div id=\"wkgrid2\" hidden></div>", "<div id=\"wkgrid2\" hidden></div><div id=\"firsttd\" hidden></div>")
rep("['meta','metaprop','weeklies','weeklies2','wkgrid','wkgrid2','tdpicks',", "['meta','metaprop','weeklies','weeklies2','wkgrid','wkgrid2','tdpicks','firsttd',")
rep("['test',wkGrid2],", "['test',wkGrid2],['test',firstTd],")
rep(" weeklies2:{what:'What called the touchdowns, one week at a time.'",
    " firsttd:{what:'Who scores the first touchdown.',how:['a played week: every game\\'s first scorer and each team\\'s first, with the quarter and clock','the week ahead: P(first) = his team\\'s share of the implied points x his share of his team\\'s anytime-TD chances \\u2014 a proxy, and the record tile says how often its top pick per game has been right','fair odds from that chance; Kalshi is the exchange mid where a market exists; edge = model minus Kalshi','below: which slot scores first against each defense, and each offense\\'s first-TD habits','every tile opens its history, every column sorts, click a name for his card']},\n weeklies2:{what:'What called the touchdowns, one week at a time.'")

view = r'''
/* ---------------- v39: First TD (F5 Picks) ---------------- */
function firstTd(){const el=$('#firsttd');if(!el)return;const D=J.firstTd;if(!D){el.innerHTML='<p class="note">no first-TD data in this build yet — scripts/build_first_td.py writes it</p>';return}
  const CUR=String(Math.max(...D.seasons)),SL=['QB1','RB1','RB2','WR1','WR2','WR3','WR4+','TE1','TE2','D/ST'];
  const pct=v=>v==null?'—':(100*v).toFixed(v<.1?1:0)+'%',odds=v=>v==null?'—':(v>0?'+':'')+v;
  const clk=(q,c)=>q==null?'':`Q${q} ${c!=null?String(Math.floor((c%900)/60)).padStart(2,'0')+':'+String(c%60).padStart(2,'0'):''}`;
  el.innerHTML=`<div class="wktiles" id="ftTiles" data-mg="1"></div><div id="ftMain"></div>
    <div class="wk2b"><div class="panel"><h3 id="ftDh"></h3><div id="ftDef"></div></div><div class="panel"><h3 id="ftOh"></h3><div id="ftOff"></div></div></div>`;
  let sk='p_first',sa=false;
  function render(){const W=G.week,played=!!(D.results[CUR]||{})[String(W)],res=(D.results[CUR]||{})[String(W)]||[],tres=(D.tresults[CUR]||{})[String(W)]||[];
    const bs=D.by_slot[CUR]||{},top=Object.entries(bs).sort((a,b)=>b[1][0]-a[1][0]);
    const slotH=()=>({title:'who scores the first touchdown · by depth slot',sub:'share of games, by the scorer\'s slot that week',cols:[{l:'slot',g:false},...D.seasons.map(se=>({l:String(se)})),{l:'all seasons'}],rows:SL.concat(['other']).map(sl=>[sl,...D.seasons.map(se=>{const v=(D.by_slot[String(se)]||{})[sl];return v?{v:v[1],h:`${pct(v[1])} <span class="mini">${v[0]}</span>`}:null}),(D.by_slot.all||{})[sl]?{v:D.by_slot.all[sl][1],h:pct(D.by_slot.all[sl][1])}:null])});
    const homeH=()=>({title:'home team scores first',sub:'share of games',cols:[{l:'season',g:false},{l:'home first'},{l:'pass',t:'first TD by a pass'},{l:'rush'},{l:'1st quarter',t:'first TD came in Q1'}],rows:D.seasons.map(se=>{const h=D.by_how[String(se)]||{},q=D.by_qtr[String(se)]||{};return [se,{v:D.home_first[String(se)],h:pct(D.home_first[String(se)])},h.pass?{v:h.pass[1],h:pct(h.pass[1])}:null,h.rush?{v:h.rush[1],h:pct(h.rush[1])}:null,q['1']?{v:q['1'][1],h:pct(q['1'][1])}:null]})});
    const chkH=()=>({title:'the model · top pick per game, week by week',sub:'rated before kickoff from the TD Picks walk-forward chances and the closing implied totals · "right" = that man scored the game\'s first TD',cols:[{l:'season',g:false},{l:'week',g:false},{l:'games',g:false},{l:'right'},{l:'hit rate'},{l:'team right',t:'the pick\'s team scored first'},{l:'avg chance',t:'the model\'s own average chance on its top picks'}],rows:D.check.slice().reverse().map(c=>Object.assign([c.season,c.week,c.games,c.hit,{v:c.hit/c.games,h:pct(c.hit/c.games)},{v:c.team_hit/c.games,h:`${c.team_hit}/${c.games}`},{v:c.top_p,h:pct(c.top_p)}],{hi:c.season===+CUR&&c.week===W}))});
    const kalH=()=>({title:`Kalshi first-TD markets · week ${W}`,sub:'exchange mid prices on file · the loop pulls them Thu / Sat / Sun',cols:['player','team',{l:'opp',g:false},{l:'Kalshi'},{l:'model'},{l:'edge'},{l:'volume',g:false}],rows:D.board.filter(b=>b.kalshi!=null).sort((a,b)=>(b.edge??-9)-(a.edge??-9)).map(b=>[pn(b.player,b.team,true),tcell(b.team),oppcell((b.home?'':'@')+b.opp),{v:b.kalshi,h:pct(b.kalshi)},{v:b.p_first,h:pct(b.p_first)},b.edge!=null?{v:b.edge,h:(b.edge>=0?'+':'')+(100*b.edge).toFixed(1)+'%'}:null,b.vol])});
    $('#ftTiles').innerHTML=thSeq(wkTile(`week ${W}${played?' · played':' · ahead'}`,String(played?res.length:[...new Set(D.board.map(b=>b.team+'|'+b.opp))].length/2|0),played?'games with a first touchdown':`games on the slate · ${D.kalshi_n} Kalshi first-TD markets on file`)
      +wkTile('who scores first',top[0]?`${top[0][0]} ${pct(top[0][1][1])}`:'—',top[1]?`then ${top[1][0]} ${pct(top[1][1][1])} · ${top[2]?top[2][0]+' '+pct(top[2][1][1]):''} · ${CUR}`:'','',true)
      +wkTile('home team first',pct(D.home_first[CUR]),`${CUR} · ${pct((D.by_how[CUR]||{}).pass?.[1])} by pass`,D.home_first[CUR]>.55?'g':'',true)
      +wkTile('the model\'s top pick per game',D.wf.games?`${D.wf.hit}<span class="dim"> / ${D.wf.games}</span>`:'—',D.wf.games?`${pct(D.wf.hit/D.wf.games)} scored the first TD · team right ${pct(D.wf.team_hit/D.wf.games)}`:'no walk-forward yet',D.wf.games&&D.wf.hit/D.wf.games>=.13?'g':'')
      +wkTile('Kalshi priced',String(D.board.filter(b=>b.kalshi!=null).length),`of ${D.board.length} on the board · week ${D.week}`),[slotH,slotH,homeH,chkH,kalH]);
    const th=(k,l,t)=>`<th data-k="${k}" title="${esc(t||'')}" style="cursor:pointer">${l}${sk===k?(sa?' ▲':' ▼'):''}</th>`;
    const shade=(v,arr,lo)=>{const vs=arr.filter(x=>x!=null);if(v==null||vs.length<2)return `<span class="dim">—</span>`;const srt=vs.slice().sort((a,b)=>lo?a-b:b-a);return `<span class="badge" style="${gradeStyle(srt.indexOf(v)+1,srt.length)}">${pct(v)}</span>`};
    if(played){
      const G=res.filter(r=>inF(r.team)||inF(r.vs)).map(r=>{const tf=tres.filter(x=>x.game===r.game);return Object.assign({},r,{other:tf.find(x=>x.team!==r.team)})});
      $('#ftMain').innerHTML=`<div class="panel"><h3>who scored first — week ${W} <span class="f">the game\'s first touchdown, then the other team\'s first · slot = his depth slot that week · click a name for his card</span></h3>
        <div class="tscroll"><table class="fx"><thead><tr><th>game</th><th>first scorer</th><th>team</th><th>slot</th><th>how</th><th>when</th><th>home?</th><th>other team\'s first</th><th>slot</th><th>when</th></tr></thead><tbody>${G.map(r=>`<tr><td>${r.game.split('_').slice(2).map(t=>tcell(t)).join(' @ ')}</td><td>${r.pos==='D/ST'?esc(r.player):pn(r.player,r.team,true)}</td><td>${tcell(r.team)}</td><td>${r.slot?slotchip(r.slot):'<span class="dim">—</span>'}</td><td>${r.how}</td><td class="mono">${clk(r.qtr,r.clock)}</td><td>${r.home?'home':'away'}</td><td>${r.other?(r.other.pos==='D/ST'?esc(r.other.player):pn(r.other.player,r.other.team,true)):'<span class="dim">never scored</span>'}</td><td>${r.other&&r.other.slot?slotchip(r.other.slot):''}</td><td class="mono">${r.other?clk(r.other.qtr,r.other.clock):''}</td></tr>`).join('')}</tbody></table></div></div>`;
    }else{
      const B=D.board.filter(b=>(inF(b.team)||inF(b.opp))&&inP(b.pos)&&slotOK(new Set(),b.slot)&&(b.inj!=='-1')),V={player:b=>b.player,team:b=>b.team,slot:b=>b.slot,p_first:b=>b.p_first,fair:b=>b.p_first,kalshi:b=>b.kalshi??-1,edge:b=>b.edge??-9,p_any:b=>b.p_any??-1,p_team:b=>b.p_team,first_cur:b=>b.first_cur,first_prev:b=>b.first_prev};
      B.sort((a,b)=>{const u=V[sk](a),v=V[sk](b);return (u<v?-1:u>v?1:0)*(sa?1:-1)||b.p_first-a.p_first});
      const pf=B.map(b=>b.p_first),pk=B.map(b=>b.kalshi),pe=B.map(b=>b.edge),pa=B.map(b=>b.p_any),ptm=B.map(b=>b.p_team);
      $('#ftMain').innerHTML=`<div class="panel"><h3>the board — week ${W} <span class="f">${B.length} slot owners · chance = team\'s share of the implied points × his share of the team\'s anytime-TD chances · Kalshi = exchange mid · edge = model − Kalshi · every column sorts</span></h3>
        <div class="tscroll"><table class="fx"><thead><tr>${th('player','player')}${th('team','tm')}<th>opp</th>${th('slot','slot')}${th('p_first','first TD','the model\'s chance he scores the game\'s first TD')}${th('fair','fair','fair American odds from that chance')}${th('kalshi','Kalshi','exchange mid price')}${th('edge','edge','model minus Kalshi')}${th('p_team','team first','chance his team scores the first TD')}${th('p_any','anytime','TD Picks: chance he scores at all')}${th('first_cur','1st TDs '+CUR,'games this season where he scored the first TD')}${th('first_prev','before','earlier seasons')}</tr></thead><tbody>
        ${B.map(b=>`<tr><td>${pn(b.player,b.team,true)}${b.inj==='0'?' <span class="inj0">Q</span>':''}</td><td>${tcell(b.team)}</td><td>${oppcell((b.home?'':'@')+b.opp)}</td><td>${slotchip(b.slot)}</td><td class="n" data-v="${b.p_first}">${shade(b.p_first,pf)}</td><td class="n mono">${odds(b.fair)}</td><td class="n" data-v="${b.kalshi??''}">${b.kalshi!=null?shade(b.kalshi,pk):'<span class="dim">—</span>'}</td><td class="n" data-v="${b.edge??''}">${b.edge!=null?`<b style="color:${b.edge>=.02?'var(--green)':b.edge<=-.02?'var(--red)':'var(--txt)'}">${(b.edge>=0?'+':'')+(100*b.edge).toFixed(1)}%</b>`:'<span class="dim">—</span>'}</td><td class="n" data-v="${b.p_team}">${shade(b.p_team,ptm)}</td><td class="n" data-v="${b.p_any??''}">${shade(b.p_any,pa)}</td><td class="n" data-v="${b.first_cur}">${b.first_cur||'<span class="dim">0</span>'}</td><td class="n" data-v="${b.first_prev}">${b.first_prev||'<span class="dim">0</span>'}</td></tr>`).join('')}</tbody></table></div></div>`;
      $('#ftMain').querySelectorAll('th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(sk===k)sa=!sa;else{sk=k;sa=['player','team','slot'].includes(k)}render()});
    }
    /* defenses: which slot scores first against them */
    const DA=D.def_allow[CUR]||{};const teams=Object.keys(DA).filter(inF).sort();
    const cell=(t,sl)=>{const v=(DA[t].slot||{})[sl];return v?v[1]:0};
    const col=sl=>teams.map(t=>cell(t,sl));
    $('#ftDh').innerHTML=`first TD allowed, by slot — ${CUR} <span class="f">share of each team\'s first TDs against this defense that went to each slot · green = allows the most · every column sorts</span>`;
    $('#ftDef').innerHTML=`<div class="tscroll"><table class="fx"><thead><tr><th>defense</th><th>n</th>${SL.map(sl=>`<th>${sl}</th>`).join('')}</tr></thead><tbody>${teams.map(t=>`<tr><td>${tcell(t)}</td><td class="n">${DA[t].n}</td>${SL.map(sl=>{const v=cell(t,sl);return `<td class="n" data-v="${v}">${v?shade(v,col(sl)):'<span class="dim">·</span>'}</td>`}).join('')}</tr>`).join('')}</tbody></table></div>`;
    const OF=D.off_first[CUR]||{};const ot=Object.keys(OF).filter(inF).sort();
    $('#ftOh').innerHTML=`each offense\'s first TD — ${CUR} <span class="f">who scores it, and the slot share · every column sorts</span>`;
    $('#ftOff').innerHTML=`<div class="tscroll"><table class="fx"><thead><tr><th>offense</th><th>n</th><th style="text-align:left">scorers</th>${['QB1','RB1','RB2','WR1','WR2','WR3','TE1'].map(sl=>`<th>${sl}</th>`).join('')}</tr></thead><tbody>${ot.map(t=>`<tr><td>${tcell(t)}</td><td class="n">${OF[t].n}</td><td style="text-align:left">${OF[t].players.map(([p,n])=>`${/D\/ST$/.test(p)?esc(p):pn(p,t,true)} <span class="mini">${n}</span>`).join(' · ')}</td>${['QB1','RB1','RB2','WR1','WR2','WR3','TE1'].map(sl=>{const v=(OF[t].slot||{})[sl];return `<td class="n" data-v="${v?v[1]:0}">${v?shade(v[1],ot.map(x=>((OF[x].slot||{})[sl]||[0,0])[1])):'<span class="dim">·</span>'}</td>`}).join('')}</tr>`).join('')}</tbody></table></div>`;
    sortableAll($('#ftDef'));sortableAll($('#ftOff'));if(played)sortableAll($('#ftMain'));logoize(el)}
  render();RR.push(render)}
'''
rep("\n/* ---------------- v33: Weeklies v2 + Category Grid v2 (F6 TEST) ---------------- */", view + "\n/* ---------------- v33: Weeklies v2 + Category Grid v2 (F6 TEST) ---------------- */")
s = s.replace("Object.assign(NOTES,{v38:", "Object.assign(NOTES,{v39:['v39','First TD tab on F5 Picks: who scored first in every game of a played week, the board for the week ahead (model chance, fair odds, Kalshi, edge), first TD allowed by slot per defense, each offense\\'s habits, and the model\\'s walk-forward record \\u00b7 depth charts: ESPN\\'s order is the chart again \\u2014 usage no longer moves anyone']});\nObject.assign(NOTES,{v38:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v39 applied', len(s))
