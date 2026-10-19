# -*- coding: utf-8 -*-
"""v21 — F6 TEST › TD Picks: the coming week's anytime-TD picks from build_td_picks.py (the Weeklies study turned into a calibrated,
walk-forward-tested model), plus the pipeline hooks (dashboard payload, PC loop, refresh) and the Weeklies WR4 chip fix."""
def patch(path,pairs):
    s=open(path,encoding='utf-8').read()
    for old,new in pairs:
        assert s.count(old)==1,(path,old[:80],s.count(old))
        s=s.replace(old,new)
    open(path,'w',encoding='utf-8').write(s)

# ---- pipeline: payload, loop, refresh
patch('scripts/build_dashboard.py',[("    data['betting'] = betting_payload()\n",
  "    data['betting'] = betting_payload()\n    # TD Picks (build_td_picks.py): next week's anytime-TD picks, the walk-forward record and the frozen ledger\n    if LEAGUE == 'nfl' and os.path.exists('data/processed/td_picks.json'):\n        data['tdpicks'] = json.load(open('data/processed/td_picks.json'))\n")])
patch('scripts/local/loop.py',[("        if 'odds' in did or 'injuries' in did: step('dashboard', run, ['scripts/build_dashboard.py'], False)",
  "        if 'odds' in did or 'injuries' in did: step('td picks', run, ['scripts/build_td_picks.py'], False); step('dashboard', run, ['scripts/build_dashboard.py'], False)")])
patch('scripts/refresh.py',[("    run(['scripts/build_dashboard.py'])\n    try: run(['scripts/build_tracking.py'])",
  "    try: run(['scripts/build_td_picks.py'])\n    except Exception as e: print('  build_td_picks skipped:', e)\n    run(['scripts/build_dashboard.py'])\n    try: run(['scripts/build_tracking.py'])")])

TD_JS = r"""
/* ---------------- TD Picks (F6 TEST) — the coming week's anytime touchdowns ----------------
   Everything here is computed by scripts/build_td_picks.py and embedded as J.tdpicks: a ridge logistic model on the pre-kickoff profile
   the Weeklies tab tests (form vs career, career TD rate, share of his team's TDs, touches / targets / carries, snap share, implied
   total, spread, what the defense allows his slot season-long and lately, a TD vs this opponent before, slot), calibrated with
   isotonic regression fitted only on earlier weeks. The record on this page is walk-forward (every week of 2025-26 scored by a model
   that had not seen it) plus the frozen ledger: a week's picks are written down the first time it is scored and graded from the logs. */
function tdPicks(){
  const el=$('#tdpicks');if(!el)return;const T=J.tdpicks;
  if(!T){el.innerHTML='<p class="note">no TD picks in this build yet — scripts/build_td_picks.py writes them</p>';return}
  const live=new Set(TD_SLOTS);let sortK='p',show='board';
  const TIER={lock:['lock','50%+','g'],strong:['strong','40–50%','g2'],solid:['solid','30–40%','a'],long:['longshot','20–30%','b'],low:['low','under 20%','d']};
  const pct=v=>v==null?'—':Math.round(100*v)+'%',ml=v=>v==null?'—':(v>0?'+':'')+v;
  const BT=T.bt||{},tk=Object.keys(TIER);
  el.innerHTML=`<div class="controls">
    ${slotChipsHTML('tpSlots',live)}
    <select id="tpInj"><option value="x" selected>hide OUT</option><option value="">incl. OUT</option></select>
    <select id="tpSort" title="how each column is ordered"><option value="p" selected>rank by chance to score</option><option value="ev">rank by value at the posted price</option></select>
    <input id="tpQ" placeholder="search player..." size="15">
    <span class="note kept">week ${T.week} · depth chart ${T.depth} · built ${T.built}</span>
  </div>
  <div class="wktiles" id="tpTiles" data-mg="1"></div>
  <div class="panel"><h3 id="tpBh"></h3><div class="tpcols" id="tpCols" data-mg="1"></div></div>
  <div class="panel"><h3 id="tpVh"></h3><div id="tpVal"></div></div>
  <div class="wk2b"><div class="panel"><h3>track record — every week of 2025–26, scored blind <span class="f">the model is refit before each week on games it has already seen, then graded on that week</span></h3><div id="tpRec"></div></div>
    <div class="panel"><h3>does the % mean what it says? <span class="f">predicted chance vs how often those players actually scored · white tick = the prediction</span></h3><div id="tpCal"></div></div></div>
  <div class="panel"><h3 id="tpLh"></h3><div id="tpLed"></div></div>
  <details class="panel wkdet"><summary id="tpAh"></summary><div id="tpAll"></div></details>`;
  const keep=x=>slotOK(live,x.s==='WR4+'?'WR4':x.s)&&($('#tpInj').value!=='x'||x.inj!=='-1')&&inP(x.pos)&&inF(x.t)&&(()=>{const q=$('#tpQ').value.toLowerCase();return !q||x.n.toLowerCase().includes(q)})();
  const trk=x=>TRK.btn({kind:'player',league:'nfl',away:x.h?x.o:x.t,home:x.h?x.t:x.o,kickoff:'',market:'td',stat:'anytime_td',player:x.n,team:x.t,selection:'Yes',point:'',price:x.price!=null?String(x.price):'',source:x.book||'',label:`${x.n} anytime TD`,from:'td picks'});
  const evC=v=>v==null?'var(--dim)':v>=.05?'var(--green)':v<=-.05?'var(--red)':'var(--txt)';
  const card=x=>{const t=TIER[x.tier]||TIER.low;return `<div class="tpc ${t[2]}${x.inj==='-1'?' out':''}">
      <div class="h">${pn(x.n,x.t,true)} ${slotchip(x.b)} <span class="mini">${x.h?'vs':'@'} ${tcell(x.o)}</span>${x.inj==='0'?' <span class="inj0">Q</span>':x.inj==='-1'?' <span class="injm1">OUT</span>':''}<span class="st">${trk(x)}</span></div>
      <div class="m"><b class="pp2">${pct(x.p)}</b><span class="tier">${t[0]}</span><span class="fo" title="the price this chance is worth">fair <b>${ml(x.fair)}</b></span>${x.price!=null?`<span class="fo" title="best posted anytime-TD price">${esc(x.book||'')} <b>${ml(x.price)}</b></span><span class="ev" style="color:${evC(x.ev)}" title="expected return at that price">${x.ev>=0?'+':''}${Math.round(100*x.ev)}%</span>`:''}</div>
      <div class="why">${(x.why||[]).map(w=>`<i>${esc(w)}</i>`).join('')}${x.risk?`<i class="risk">${esc(x.risk)}</i>`:''}</div></div>`};
  function render(){
    const P=T.picks.filter(keep),sk=$('#tpSort').value;
    const ord=(a,b)=>sk==='ev'?((b.ev??-9)-(a.ev??-9)||b.p-a.p):b.p-a.p;
    /* tiles */
    const lk=P.filter(x=>x.tier==='lock'),rec=(T.record||[]).filter(r=>r.graded),rw=rec.reduce((s,r)=>s+r.wins,0),rg=rec.reduce((s,r)=>s+r.graded,0),bl=BT.tiers&&BT.tiers.lock;
    $('#tpTiles').innerHTML=wkTile(`week ${T.week}`,String(T.games),`games · ${T.dates?T.dates[0].slice(5)+' to '+T.dates[1].slice(5):''}`)
      +wkTile('locks',String(lk.length),lk.slice(0,2).map(x=>esc(pshort(x.n))).join(' · ')||'none above 50%','g')
      +wkTile('top 10 each week',BT.top10?pct(BT.top10[0]/BT.top10[1]):'—',`scored · ${BT.top10?BT.top10[0]+' of '+BT.top10[1]:''} blind picks`,'g')
      +wkTile('lock tier',bl&&bl[0]?pct(bl[1]/bl[0]):'—',`hit · ${bl?bl[1]+' of '+bl[0]:''} picks rated 50%+`,'g')
      +wkTile('prices posted',String(T.priced),T.priced?'best anytime-TD price across books':'books post props midweek — fair odds until then',T.priced?'':'')
      +wkTile('frozen record',rg?`${rw}-${rg-rw}`:'—',rg?`${pct(rw/rg)} of frozen picks scored`:`week ${T.week} picks frozen ${(T.record||[]).length?(T.record[T.record.length-1].frozen||'').slice(5):''} · graded as games log`);
    /* the board: four positions */
    const N={QB:5,RB:10,WR:12,TE:7};
    $('#tpBh').innerHTML=`week ${T.week} — the picks <span class="f">chance he scores a rushing or receiving TD · tier = lock 50%+, strong 40–50%, solid 30–40%, longshot 20–30% · fair = the odds that chance is worth${T.priced?' · EV = expected return at the best posted price':''} · ★ sends it to Tracking</span>`;
    $('#tpCols').innerHTML=TPOS.filter(p=>inP(p)).map(p=>{const L=P.filter(x=>x.pos===p).sort(ord);return `<div class="tpcol"><h4>${posIcon(p,11)} ${p} <b>${Math.min(N[p],L.length)}</b><span class="mini">of ${L.length}</span></h4>${L.slice(0,N[p]).map(card).join('')||'<span class="mini dim">nobody matches</span>'}</div>`}).join('');
    /* value: the posted price beats the model's fair price */
    const V=P.filter(x=>x.ev!=null&&x.ev>=.05).sort((a,b)=>b.ev-a.ev);
    $('#tpVh').innerHTML=`value at the posted price <span class="f">players whose best posted anytime-TD price pays more than the model's fair price · biggest edge first</span>`;
    $('#tpVal').innerHTML=!T.priced?'<p class="mini dim">no week-'+T.week+' anytime-TD prices are posted yet — the loop picks them up as books open them, and this fills in on its own</p>'
      :V.length?`<div class="tpvals">${V.slice(0,16).map(x=>`<div class="tpv"><span>${pn(x.n,x.t,true)} ${slotchip(x.b)}</span><span class="mini">model <b>${pct(x.p)}</b> · fair ${ml(x.fair)}</span><span class="mini">${esc(x.book||'')} <b>${ml(x.price)}</b></span><b style="color:var(--green)">+${Math.round(100*x.ev)}%</b>${trk(x)}</div>`).join('')}</div>`:'<p class="mini dim">every posted price is at or below the model\'s fair price right now</p>';
    /* track record: weekly top-10, tiers */
    const W=BT.weeks||[];
    $('#tpRec').innerHTML=`<div class="tpwk">${W.map(w=>{const r=w[5]?w[4]/w[5]:0;return `<span class="b" title="${w[0]} wk ${w[1]}: ${w[4]} of the top ${w[5]} scored · field ${pct(w[3]/w[2])}"><i style="height:${Math.max(4,Math.round(100*r))}%;background:${r>=.6?'var(--green)':r>=.4?'var(--amber)':'var(--red)'}"></i><em>${w[1]}</em></span>`}).join('')}</div>
      <div class="mini" style="margin:4px 0 10px">each bar = how many of that week's ten highest-rated players scored · ${BT.top10?BT.top10[0]+' of '+BT.top10[1]:''} overall · top three per position ${BT.top3pos?pct(BT.top3pos[0]/BT.top3pos[1]):''} · model AUC ${BT.auc} vs ${BT.auc_base} for slot alone</div>
      ${tk.map(k=>{const v=(BT.tiers||{})[k]||[0,0],t=TIER[k],r=v[0]?v[1]/v[0]:null;return `<div class="wkb"><span class="l">${t[0]} <span class="mini">${t[1]}</span></span><span class="t"><i style="width:${(100*(r||0)/.75).toFixed(1)}%;background:${k==='lock'||k==='strong'?'var(--green)':k==='solid'?'var(--amber)':k==='long'?'#6db3e8':'#55606a'}"></i></span><span class="r"><b>${pct(r)}</b><span class="mini"> ${v[1]}/${v[0]}</span></span></div>`}).join('')}`;
    $('#tpCal').innerHTML=(BT.calib||[]).map(c=>{const off=Math.abs(c[1]-c[0]);return `<div class="wkb" title="${c[2]} players rated about ${pct(c[0])} — ${pct(c[1])} scored"><span class="l">rated ~${pct(c[0])}</span><span class="t"><i style="width:${(100*c[1]/.75).toFixed(1)}%;background:${off<=.04?'var(--green)':off<=.08?'var(--amber)':'var(--red)'}"></i><u style="left:${(100*c[0]/.75).toFixed(1)}%"></u></span><span class="r"><b>${pct(c[1])}</b><span class="mini"> ${c[2]}</span></span></div>`}).join('');
    /* the frozen ledger */
    const R=T.record||[];
    $('#tpLh').innerHTML=`frozen picks <span class="f">written down the first time a week is scored and never re-scored · ✓ scored · ✗ didn't · blank = not played yet</span>`;
    $('#tpLed').innerHTML=R.length?R.slice().reverse().map(r=>`<div class="tpled"><h4>week ${r.w} <span class="mini">frozen ${r.frozen} · ${r.graded?`${r.wins} of ${r.graded} graded picks scored · top ten ${r.top10[0]}/${r.top10[1]}`:'not graded yet'}</span></h4>
      <div class="wkpcs">${r.rows.slice().sort((a,b)=>(a[6]||99)-(b[6]||99)).slice(0,24).map(x=>`<span class="wkpc ${x[9]==='W'?'w':x[9]==='L'?'l':''}">${pn(x[0],x[1],true)}<i>${pct(x[4])}</i>${x[9]==='W'?'<b>✓</b>':x[9]==='L'?'<b>✗</b>':''}</span>`).join('')}</div></div>`).join(''):'<p class="mini dim">no frozen week yet</p>';
    /* every player, folded */
    const A=P.slice().sort(ord);
    $('#tpAh').innerHTML=`every player — week ${T.week} <span class="mini">${A.length} · open for the full sortable table</span>`;
    $('#tpAll').innerHTML=`<table class="fx wkp"><thead><tr><th>player</th><th>slot</th><th>opp</th><th title="chance he scores">P(TD)</th><th>tier</th><th title="the odds that chance is worth">fair</th><th title="best posted price">price</th><th title="expected return at the posted price">EV</th><th title="games with a TD this season">season</th><th title="games with a TD in his last three">L3</th><th title="his share of his team's TDs">team TD share</th><th title="carries + targets a game">touches</th><th title="team implied total">implied</th><th title="TDs the defense allows his slot per game">D allows</th><th>★</th></tr></thead><tbody>
      ${A.map(x=>`<tr><td>${pn(x.n,x.t,true)}${x.inj==='0'?' <span class="inj0">Q</span>':x.inj==='-1'?' <span class="injm1">OUT</span>':''}</td><td>${slotchip(x.b)}</td><td>${x.h?'':'@'}${tcell(x.o)}</td>
        <td class="n" data-v="${x.p}"><span class="badge" style="${gradeStyle(1+(1-Math.min(1,x.p/.6))*(NT-1))}">${pct(x.p)}</span></td><td>${(TIER[x.tier]||TIER.low)[0]}</td><td class="n" data-v="${x.fair}">${ml(x.fair)}</td>
        <td class="n" data-v="${x.price??''}">${x.price!=null?`${ml(x.price)} <span class="mini">${esc(x.book||'')}</span>`:'<span class="dim">—</span>'}</td><td class="n" data-v="${x.ev??''}">${x.ev!=null?`<b style="color:${evC(x.ev)}">${x.ev>=0?'+':''}${Math.round(100*x.ev)}%</b>`:'<span class="dim">—</span>'}</td>
        <td class="n" data-v="${x.gpS?x.hitS/x.gpS:''}">${x.gpS?`${x.hitS}/${x.gpS}`:'<span class="dim">—</span>'}</td><td class="n" data-v="${x.l3n?x.l3k/x.l3n:''}">${x.l3n?`${x.l3k}/${x.l3n}`:'<span class="dim">—</span>'}</td>
        <td class="n" data-v="${x.share??''}">${x.share!=null?pct(x.share):'<span class="dim">—</span>'}</td><td class="n" data-v="${x.touch}">${x.touch}</td>
        <td class="n" data-v="${x.imp??''}">${x.imp!=null?`<span style="color:${x.imp>=24?'var(--green)':x.imp<19?'var(--red)':'var(--txt)'}">${x.imp}</span>`:'<span class="dim">—</span>'}</td><td class="n" data-v="${x.dr??''}">${x.dr??'—'}</td><td>${trk(x)}</td></tr>`).join('')}</tbody></table>`;
    tWire(el);TRK.paint()}
  slotChipsWire('tpSlots',live,render);['tpInj','tpSort'].forEach(i=>$('#'+i).onchange=render);$('#tpQ').oninput=render;
  render();RR.push(render);
}
"""

TD_CSS = """
/* ---- v21 TD Picks ---- */
.tpcols{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;align-items:start}@media(max-width:1300px){.tpcols{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:760px){.tpcols{grid-template-columns:1fr!important}}
.tpcol{display:flex;flex-direction:column;gap:6px;min-width:0}.tpcol h4{margin:0 0 2px;font:600 10px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2);display:flex;gap:6px;align-items:center}.tpcol h4 b{font:700 11px var(--mono);color:var(--txt)}.tpcol h4 .mini{text-transform:none;letter-spacing:0}
.tpc{background:rgba(255,255,255,.02);border:1px solid var(--edge);border-left:3px solid #55606a;border-radius:7px;padding:7px 9px;display:flex;flex-direction:column;gap:4px;min-width:0}
.tpc.g{border-left-color:var(--green)}.tpc.g2{border-left-color:#7dd87d}.tpc.a{border-left-color:var(--amber)}.tpc.b{border-left-color:#6db3e8}.tpc.out{opacity:.5}
.tpc .h{display:flex;align-items:center;gap:5px;font-size:12.5px;white-space:nowrap;overflow:hidden}.tpc .h .pp{font-weight:600}.tpc .st{margin-left:auto}
.tpc .m{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.tpc .pp2{font:700 21px/1 var(--mono);color:var(--txt)}.tpc.g .pp2{color:var(--green)}.tpc.g2 .pp2{color:#7dd87d}.tpc.a .pp2{color:var(--amber)}.tpc.b .pp2{color:#6db3e8}
.tpc .tier{font:600 9.5px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--dim2)}.tpc .fo{font-size:11px;color:var(--dim)}.tpc .fo b{font-family:var(--mono);color:var(--txt)}.tpc .ev{font:700 11.5px var(--mono)}
.tpc .why{display:flex;flex-wrap:wrap;gap:3px}.tpc .why i{font-style:normal;font-size:10.5px;color:var(--dim);border:1px solid var(--edge2);border-radius:3px;padding:0 5px;line-height:16px}.tpc .why i.risk{color:var(--red);border-color:#ff525255}
.tpvals{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:6px}.tpv{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto auto;gap:8px;align-items:center;font-size:12px;border:1px solid var(--edge);border-radius:6px;padding:5px 8px}.tpv .mini b{font-family:var(--mono);color:var(--txt)}
.tpwk{display:flex;align-items:flex-end;gap:3px;height:74px;border-bottom:1px solid var(--edge2);padding-bottom:14px;position:relative}.tpwk .b{flex:1;height:100%;display:flex;flex-direction:column;justify-content:flex-end;position:relative;min-width:6px}
.tpwk .b i{display:block;border-radius:2px 2px 0 0;opacity:.85}.tpwk .b em{position:absolute;bottom:-14px;left:0;right:0;text-align:center;font:500 8.5px var(--mono);color:var(--dim2);font-style:normal}
.tpled{margin:0 0 10px}.tpled h4{margin:0 0 6px;font:600 11px var(--ui);color:var(--txt)}.tpled h4 .mini{margin-left:8px;font-weight:500}
.wkpc.w{border-color:#00c85366}.wkpc.l{opacity:.55}.wkpc b{font:700 10px var(--mono);margin-left:3px}.wkpc.w b{color:var(--green)}.wkpc.l b{color:var(--red)}"""

T='scripts/dashboard_template.html'
patch(T,[
 ("""   {id:'labgrid',label:'Lab Grid',""",
  """   {id:'tdpicks',nfl:true,label:'TD Picks',desc:'next week\\'s anytime touchdowns: every slot owner\\'s chance to score from the model built on the Weeklies study, with fair odds, the best posted price and its edge, the reasons and the risk \\u2014 plus the blind week-by-week record and the frozen picks graded as games are logged',c:'test',sub:'tdpicks'},
   {id:'labgrid',label:'Lab Grid',"""),
 ("""<div id="test" hidden><div id="meta" hidden></div><div id="weeklies" hidden></div>""","""<div id="test" hidden><div id="meta" hidden></div><div id="weeklies" hidden></div><div id="tdpicks" hidden></div>"""),
 ("""if(it.c==='test'){['meta','weeklies','labgrid',""","""if(it.c==='test'){['meta','weeklies','tdpicks','labgrid',"""),
 ("""/* ---------------- Game View — one game, everything the site knows about it ----------------""",TD_JS+"""
/* ---------------- Game View — one game, everything the site knows about it ----------------"""),
 ("""['test',metaGrid],['test',weeklies],""","""['test',metaGrid],['test',weeklies],['test',tdPicks],"""),
 ("""table.wkp td.c{text-align:center}""","""table.wkp td.c{text-align:center}"""+TD_CSS),
 # Weeklies: logs label deeper receivers WR4+, the chips say WR4
 ("""  const keep=x=>slotOK(wkLive,x.slot)&&inP(x.pos);""","""  const keep=x=>slotOK(wkLive,x.slot==='WR4+'?'WR4':x.slot)&&inP(x.pos);"""),
])
s=open(T,encoding='utf-8').read()
old="const INTRO={\n";assert s.count(old)==1
s=s.replace(old,old+""" tdpicks:{what:'Next week\\'s anytime touchdowns.',how:['% = his chance to score a rushing or receiving TD · fair = the odds that chance is worth','green tags = why · red tag = the main risk','record = every week of 2025–26 picked blind, then graded']},
""",1)
i=s.index(" weeklies:['v20',");j=s.index("\n",i);line=s[i:j]
s=s[:i]+line.replace("});","")+"\n tdpicks:['v21','new tab: next week\\'s TD picks from the model built on the Weeklies study — chance to score, fair odds, best posted price and edge, the reasons, the blind record and the frozen picks']"+("});" if line.rstrip().endswith("});") else "")+s[j:]
open(T,'w',encoding='utf-8').write(s)
print('v21 TD Picks patched')
