"""NBA v2 — the sport pages (scripts/sport_template.html) gain: Home → Best Picks (the frozen card graded live, tonight's best
prop edges and game edges), Picks → Props (every posted player prop vs the projection: consensus line, P(over), market, lean,
edge, best price, EV; filters by market / lean / edge), and PROP rows in the ledger (player, side, price, result). Rerunnable."""
import io, sys
T = 'scripts/sport_template.html'
s = io.open(T, encoding='utf-8').read()
if "id:'props'" in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

rep(" {id:'home',label:'Home',items:[{id:'overview',label:'Overview',desc:'the slate with lines and the model, softest matchups per market, the defensive field, team ratings'}]},",
    " {id:'home',label:'Home',items:[{id:'overview',label:'Overview',desc:'the slate with lines and the model, softest matchups per market, the defensive field, team ratings'},{id:'bestpicks',label:'Best Picks',desc:'the frozen card (game plays and player props) graded as results land, tonight\\'s best prop edges and the best game edges'}]},")
rep(" {id:'picks',label:'Picks',items:[{id:'lines',label:'Game lines',",
    " {id:'picks',label:'Picks',items:[{id:'props',label:'Props',desc:'every posted player prop on the slate against the projection: the books\\' line, the model\\'s P(over), the market\\'s, the lean, the edge, the best price and its EV'},{id:'lines',label:'Game lines',")
rep(" lines:{what:'DraftKings lines on the slate beside the model: win probability, margin, total and implied team totals.',",
    " bestpicks:{what:'The night\\'s plays in one place.',how:['the card = every frozen position (game plays and props) with the model, the market, the edge and the result as it lands','best prop edges = the largest model-vs-market gaps posted right now, both sides priced; EV = at the best price','a prop is frozen when the edge clears 5 points with two or more books on the line']},\n"
    " props:{what:'Every posted player prop on the slate against the projection.',how:['line = the books\\' consensus (modal) line · P(over) = the model, from the projection and its range · market = the de-vigged consensus price · lean = the side the model likes · edge = model − market on that side','best price = the best posted American odds on the lean, EV = expected return at it · n = books on the line','filter by market, lean, minimum edge; every column sorts; click a name for his log']},\n"
    " lines:{what:'DraftKings lines on the slate beside the model: win probability, margin, total and implied team totals.',")
rep(" ledger:{what:'Every frozen moneyline, spread and total position, graded against the line it was frozen with.',",
    " ledger:{what:'Every frozen position — moneyline, spread, total and player prop — graded against the line it was frozen with.',")

views = r'''
/* ---- NBA v2: props board, best picks ---- */
const MKL=Object.fromEntries((J.stats||[]).map(s=>[s.k,s.label]));
const amer=p=>p==null||p===''?'':(p>0?'+':'')+p;
const PR=(J.props||[]).map(r=>Object.assign({},r,{key:r.pid+'|'+r.market}));
function props(){const el=$('#picks');const mks=[...new Set(PR.map(r=>r.market))];const st=G.pr||(G.pr={mk:'',lean:'',min:0});
  const R=PR.filter(r=>inT(r.team)&&inS(r.slot)&&(!st.mk||r.market===st.mk)&&(!st.lean||r.side===st.lean)&&r.edge>=st.min).sort((a,b)=>b.edge-a.edge);
  const n2=R.filter(r=>r.n_books>=2).length;
  el.innerHTML=`<div class="controls"><span class="chips" id="prMk"><button data-m="" class="${st.mk?'':'on'}">all</button>${mks.map(m=>`<button data-m="${m}" class="${st.mk===m?'on':''}">${MKL[m]||m}</button>`).join('')}</span>
    <select id="prLean"><option value="">over or under</option><option value="Over" ${st.lean==='Over'?'selected':''}>overs</option><option value="Under" ${st.lean==='Under'?'selected':''}>unders</option></select>
    <select id="prMin"><option value="0">any edge</option><option value="0.03" ${st.min==.03?'selected':''}>3+ pts</option><option value="0.05" ${st.min==.05?'selected':''}>5+ pts (frozen)</option><option value="0.08" ${st.min==.08?'selected':''}>8+ pts</option></select>
    <span class="note">${PR.length?`${PR.length} player-markets priced · ${R.length} in view · ${n2} with both sides on the line · posted ${(PR[0]&&PR[0].updated||'').replace('T',' ')}Z`:'no props posted yet — the books post the night\'s lines the morning of; the markets loop pulls them (OPEN · MOVE · CLOSE)'}</span></div>
    <div class="panel wrap-x"><table><thead><tr><th>player</th><th>tm</th><th>opp</th><th>slot</th><th>market</th><th title="the books' consensus line">line</th><th title="the model's projection">proj</th><th title="the model's P(over)">P(over)</th><th title="de-vigged consensus">market</th><th>lean</th><th title="model − market on the lean">edge</th><th title="best posted price on the lean">best</th><th>EV</th><th title="books on the line">n</th><th title="opponent's rank allowing this stat to his slot · 1 = allows the most">opp rk</th></tr></thead><tbody>
    ${R.map(r=>`<tr><td>${pname(r)}</td><td>${tc(r.team)}</td><td>${tc(r.opp)}</td><td class="mini">${r.slot}</td><td class="mini">${MKL[r.market]||r.market}</td><td class="mono">${r.line}</td><td class="mono">${r.proj}</td><td class="mono">${(100*r.p_over).toFixed(0)}%</td><td class="mono">${(100*r.p_imp).toFixed(0)}%</td><td><b>${r.side}</b></td><td class="mono" data-v="${r.edge}" style="color:${r.edge>=.05?'var(--green)':r.edge>=.03?'#e8b100':'var(--dim)'}">+${(100*r.edge).toFixed(1)}</td><td class="mono">${amer(r.price)} <span class="mini">${r.book||''}</span></td><td class="mono" data-v="${r.ev??-99}" style="color:${r.ev>0?'var(--green)':'var(--dim)'}">${r.ev!=null?(r.ev>0?'+':'')+r.ev.toFixed(0)+'%':''}</td><td class="mono">${r.n_books}</td><td>${r.opp_rank!=null?`<span class="hc" style="${gradeStyle(r.opp_rank)}">${r.opp_rank}</span>`:''}</td></tr>`).join('')||`<tr><td colspan="15" class="mini">nothing in view</td></tr>`}</tbody></table></div>`;
  el.querySelectorAll('#prMk button').forEach(b=>b.onclick=()=>{st.mk=b.dataset.m;props();sortableAll()});$('#prLean').onchange=()=>{st.lean=$('#prLean').value;props();sortableAll()};$('#prMin').onchange=()=>{st.min=+$('#prMin').value;props();sortableAll()}}
function bestpicks(){const el=$('#home');const gs=GAMES();const today=gs.length?dayKey(gs[0].date):'';
  const P=J.picks.slice().sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:(b.edge||0)-(a.edge||0));
  const rec=L=>{const g=L.filter(p=>p.result==='W'||p.result==='L');const w=g.filter(p=>p.result==='W').length;return {w,l:g.length-w,n:L.length,open:L.filter(p=>!p.result).length}};
  const dates=[...new Set(P.map(p=>p.date))].slice(0,3);const cur=P.filter(p=>dates.includes(p.date));
  const G1=cur.filter(p=>p.type!=='PROP'),G2=cur.filter(p=>p.type==='PROP');const all=rec(P),rp=rec(P.filter(p=>p.type==='PROP')),rg=rec(P.filter(p=>p.type!=='PROP'));
  const res=p=>p.result?`<span class="res ${p.result}">${p.result==='P'?'PUSH':p.result}</span>`:'<span class="mini">open</span>';
  const side=p=>p.type==='PROP'?`${pname(p)} <b>${esc(String(p.side))}</b> <span class="mini">${MKL[p.market]||p.market}</span>`:`${p.game.split('@').map(t=>tc(t)).join(' <span class="dim">@</span> ')} <b>${esc(String(p.side))}</b>${p.line!==''&&p.line!=null?' <span class="mono mini">'+p.line+'</span>':''}`;
  const best=PR.filter(r=>r.n_books>=2&&inT(r.team)).sort((a,b)=>b.edge-a.edge).slice(0,12);
  const ge=gs.filter(g=>g.home_line!=null&&g.model_margin!=null).map(g=>({g,e:g.model_margin+g.home_line})).sort((a,b)=>Math.abs(b.e)-Math.abs(a.e)).slice(0,6);   /* spread edge: model margin vs the DK line, home perspective */
  el.innerHTML=`<div class="kpis">
    <div class="kpi ${all.w>all.l?'g':all.l>all.w?'r':''}"><div class="k">the card · all time</div><div class="v">${all.w}-${all.l}</div><div class="s">${all.n} positions · ${all.open} open</div></div>
    <div class="kpi ${rg.w>rg.l?'g':rg.l>rg.w?'r':''}"><div class="k">game plays</div><div class="v">${rg.w}-${rg.l}</div><div class="s">ML · spread · total</div></div>
    <div class="kpi ${rp.w>rp.l?'g':rp.l>rp.w?'r':''}"><div class="k">player props</div><div class="v">${rp.w}-${rp.l}</div><div class="s">${rp.n} frozen · ${rp.open} open</div></div>
    <div class="kpi"><div class="k">priced now</div><div class="v">${PR.length}</div><div class="s">player-markets on the slate${best[0]?' · best edge +'+(100*best[0].edge).toFixed(1):''}</div></div></div>
    <div class="panel wrap-x"><h3>the card <span class="f">every frozen position from the last three slates (${dates.join(' · ')||'none yet'}) · model vs market at freeze, edge, result as it lands · older positions on the ledger</span></h3>
      <table><thead><tr><th>date</th><th>type</th><th>play</th><th>model</th><th>market</th><th>edge</th><th>price</th><th>result</th><th>actual</th></tr></thead><tbody>
      ${cur.map(p=>`<tr><td class="mono">${p.date}</td><td class="mini">${p.type}</td><td>${side(p)}</td><td class="mono">${p.type==='ML'?(100*p.model).toFixed(0)+'%':p.model}</td><td class="mono">${p.type==='ML'||p.type==='PROP'?(100*p.market_ref).toFixed(0)+'%':p.market_ref}</td><td class="mono">${p.type==='ML'||p.type==='PROP'?'+'+(100*p.edge).toFixed(0)+'%':'+'+p.edge}</td><td class="mono">${p.type==='PROP'?amer(p.price):''}</td><td>${res(p)}</td><td class="mini">${p.actual??''}</td></tr>`).join('')||'<tr><td colspan="9" class="mini">no positions on the last slates</td></tr>'}</tbody></table></div>
    <div class="wk2b" style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <div class="panel wrap-x"><h3>best prop edges now <span class="f">model − market on the lean, both sides priced · EV at the best price · these freeze at 5+ points</span></h3>
      <table><thead><tr><th>player</th><th>opp</th><th>market</th><th>line</th><th>proj</th><th>lean</th><th>edge</th><th>best</th><th>EV</th></tr></thead><tbody>
      ${best.map(r=>`<tr><td>${pname(r)}</td><td>${tc(r.opp)}</td><td class="mini">${MKL[r.market]||r.market}</td><td class="mono">${r.line}</td><td class="mono">${r.proj}</td><td><b>${r.side}</b></td><td class="mono" style="color:${r.edge>=.05?'var(--green)':'#e8b100'}">+${(100*r.edge).toFixed(1)}</td><td class="mono">${amer(r.price)}</td><td class="mono">${r.ev!=null?(r.ev>0?'+':'')+r.ev.toFixed(0)+'%':''}</td></tr>`).join('')||'<tr><td colspan="9" class="mini">no props posted yet for this slate</td></tr>'}</tbody></table></div>
    <div class="panel wrap-x"><h3>best game edges <span class="f">model margin vs the DraftKings spread (points) · the model's total vs the posted total · spread positions freeze at 2.5, totals at 3</span></h3>
      <table><thead><tr><th>game</th><th>tip (CT)</th><th>lean</th><th>DK line</th><th>model margin</th><th>edge</th><th>DK total</th><th>model total</th><th>total edge</th></tr></thead><tbody>
      ${ge.map(({g,e})=>{const te=g.ou&&g.model_total!=null?g.model_total-parseFloat(g.ou):null;return `<tr><td>${tc(g.away)} <span class="dim">@</span> ${tc(g.home)}</td><td class="mono mini">${dayKey(g.date).replace(/,.*$/,'')} ${fmtT(g.date)}</td><td><b>${e>0?g.home:g.away} ${e>0?(g.home_line>0?'+':'')+g.home_line:(-g.home_line>0?'+':'')+(-g.home_line)}</b></td><td class="mono">${g.odds||''}</td><td class="mono">${(g.model_margin>0?'+':'')+g.model_margin.toFixed(1)}</td><td class="mono" style="color:${Math.abs(e)>=2.5?'var(--green)':'var(--dim)'}">+${Math.abs(e).toFixed(1)}</td><td class="mono">${g.ou||''}</td><td class="mono">${g.model_total!=null?g.model_total.toFixed(1):''}</td><td class="mono" style="color:${te!=null&&Math.abs(te)>=3?'var(--green)':'var(--dim)'}">${te!=null?(te>0?'over +':'under +')+Math.abs(te).toFixed(1):''}</td></tr>`}).join('')||'<tr><td colspan="9" class="mini">no lines on the slate yet</td></tr>'}</tbody></table></div></div>`}
'''
rep("function lines(){const el=$('#picks');const gs=GAMES();", views + "function lines(){const el=$('#picks');const gs=GAMES();")
# ledger: PROP rows show the player and the price
rep("<td>${p.game.split('@').map(t=>tc(t)).join(' <span class=\"dim\">@</span> ')}</td><td><b>${esc(String(p.side))}</b></td><td class=\"mono\">${p.line??''}</td><td class=\"mono\">${p.type==='ML'?(100*p.model).toFixed(0)+'%':p.model}</td><td class=\"mono\">${p.type==='ML'?(100*p.market_ref).toFixed(0)+'%':p.market_ref}</td><td class=\"mini\">${p.type==='ML'?'+'+(100*p.edge).toFixed(0)+'%':'+'+p.edge}</td>",
    "<td>${p.type==='PROP'?pname(p)+' <span class=\"mini\">'+(MKL[p.market]||p.market)+' · '+esc(String(p.game))+'</span>':p.game.split('@').map(t=>tc(t)).join(' <span class=\"dim\">@</span> ')}</td><td><b>${esc(String(p.side))}</b>${p.type==='PROP'&&p.price!==''&&p.price!=null?' <span class=\"mini mono\">'+amer(p.price)+'</span>':''}</td><td class=\"mono\">${p.line??''}</td><td class=\"mono\">${p.type==='ML'?(100*p.model).toFixed(0)+'%':p.model}</td><td class=\"mono\">${p.type==='ML'||p.type==='PROP'?(100*p.market_ref).toFixed(0)+'%':p.market_ref}</td><td class=\"mini\">${p.type==='ML'||p.type==='PROP'?'+'+(100*p.edge).toFixed(0)+'%':'+'+p.edge}</td>")
rep("el.innerHTML=`<div class=\"kpis\">${['','ML','ATS','TOTAL'].map(t=>{const r=rec(t);", "el.innerHTML=`<div class=\"kpis\">${['','ML','ATS','TOTAL','PROP'].map(t=>{const r=rec(t);")
rep("function render(){({overview:home,cards,board,lab,explorer,dvp,ratings:ratingsView,lines,ledger})[G.sub]();sortableAll();}",
    "function render(){({overview:home,bestpicks,cards,board,lab,explorer,dvp,ratings:ratingsView,props,lines,ledger})[G.sub]();sortableAll();}")
io.open(T, 'w', encoding='utf-8').write(s)
print('sport v2 applied', len(s))
