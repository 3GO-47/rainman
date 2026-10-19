"""v27 — F6 TEST > Backtest: every DvP data set and every board signal scored against what happened (J.backtest,
scripts/build_backtest.py). Tiles, plain-language takeaways, the data-set race (defense level), the signal race (player
level, by position and data set), data set x signal matrix, week by week, and the graded record of every frozen strategy.

Usage: python scripts/patch_v27_backtest.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v27_backtest: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# ---------------- registration: the last F6 TEST tab
rep(r'''c:'test',sub:'api'}]}];''', r'''c:'test',sub:'api'},
   {id:'backtest',label:'Backtest',desc:'every data set and every board signal scored against what actually happened: which version of the DvP tables (2024, 2025, 2026, combined, adjusted, last 4 games) best predicts what a defense allows next week, which signal (TD allowed, yards allowed, Ψ, META, H2H, SCH, the anytime-TD model, the implied total, his own form) best calls a player\'s game, and the graded record of every frozen strategy',c:'test',sub:'backtest'}]}];''')
rep(r'''<div id="test" hidden>''', r'''<div id="test" hidden><div id="backtest" hidden></div>''')
rep(r"""'api','injuries','dev']""", r"""'api','injuries','dev','backtest']""")
rep(r'''['test',devView]''', r'''['test',devView],['test',backtestView]''')
rep(r''' metaprop:{what:'META for player props.',''', r''' backtest:{what:'Which data set and which signal have actually been right.',how:['data sets: for every stat and week, how well each version of a defense\'s numbers ordered what the defenses allowed NEXT week — rank correlation, 0 = a coin flip, 1 = perfect','signals: among players in the same slot the same week, did the softer matchup (or the higher model %) score more? AUC = how often a scorer was ranked above a non-scorer (.500 = coin flip); vs-norm = did he beat his own average','everything is point in time: a week is predicted only from games before it']},
 metaprop:{what:'META for player props.',''')
rep(r'''const BOOT=[''', r'''Object.assign(NOTES,{backtest:['v27','new tab: the backtest — every DvP data set (2024, 2025, 2026, combined, adjusted, last 4 games) on what a defense allows next week, every board signal (TD allowed, yards allowed, Ψ, META, H2H, SCH, the anytime-TD model, the implied total, his own form) on the player\'s game, by position and data set, week by week, plus the graded record of every frozen strategy']});
const BOOT=[''')

# ---------------- CSS
rep(r'''.wksig{cursor:pointer;''', r'''.btins{margin:0;padding:0 0 0 16px;display:grid;gap:5px;font-size:12px;line-height:1.45}.btins li{color:var(--txt)}.btins li::marker{color:var(--acc)}.btins .s{font:600 10px var(--mono);color:var(--dim2);margin-right:6px}
.fx.bt{table-layout:auto;width:100%}.fx.bt td,.fx.bt th{text-align:right;white-space:nowrap;overflow:visible;font-variant-numeric:tabular-nums}.fx.bt td:first-child,.fx.bt th:first-child{text-align:left}.fx.bt td:nth-child(5){white-space:nowrap;text-align:right;line-height:inherit}.fx.bt td.w,.fx.bt th.w{text-align:left;white-space:normal;color:var(--dim);font-size:11px;min-width:240px;max-width:460px;line-height:1.35}.fx.bt td.c,.fx.bt th.c{text-align:center}.bt tr.best td:first-child{box-shadow:inset 3px 0 0 var(--green)}
.bt .bar{display:inline-block;height:7px;border-radius:2px;vertical-align:middle;margin-left:6px}.bt .kd{font:600 9px var(--mono);letter-spacing:.04em;text-transform:uppercase;padding:1px 5px;border-radius:3px;border:1px solid var(--edge2);color:var(--dim)}
.bt .kd.m{color:#6db3e8;border-color:#6db3e866}.bt .kd.p{color:#c39bff;border-color:#c39bff66}.bt .kd.x{color:var(--amber);border-color:#ffb30066}.bt td.hb{font-weight:700;outline:1px solid #00c85388;outline-offset:-2px}
#btMet button,#btPos button{min-width:34px}.btsub td{color:var(--dim);font-size:11px}.btsub td:first-child{padding-left:18px}
.wksig{cursor:pointer;''')

# ---------------- the tab
rep(r'''
/* ---------------- Weeklies (F6 TEST) — the touchdown lookback ----------------''', r'''
/* ---------------- Backtest (F6 TEST, v27) — which data set and which signal have actually been right ----------------
   Everything is computed by scripts/build_backtest.py from tables the site already builds, point in time (a week is predicted
   only from games before it), and embedded as J.backtest. Data sets: Spearman between each version of a defense's per-game
   numbers and what it allowed the following week, per stat column, averaged. Signals: among players in the same slot group the
   same week (QB1, RB1, RB2, WR1-3, TE1), TD AUC · rho with PPR · rho with PPR minus his own shrunk average · soft third minus
   tough third, n-weighted into positions. Strategies: picks_all.csv graded, picks_clv.csv, TD Picks walk-forward. */
function backtestView(){
  const el=$('#backtest');if(!el)return;const B=J.backtest;
  if(!B){el.innerHTML='<p class="note">no backtest in this build yet — scripts/build_backtest.py writes it</p>';return}
  const SES=Object.keys(B.sigs).sort().reverse();let S=SES[0],src='adj',pos='ALL',met='auc';
  const LB=s=>B.lbl[s]||{};
  const fr=v=>v==null?'—':(v<0?'−':'+')+Math.abs(v).toFixed(3).replace(/^0/,''),fa=v=>v==null?'—':v.toFixed(3).replace(/^0/,''),fp=v=>v==null?'—':(v<0?'−':'+')+Math.abs(v).toFixed(2),pc=v=>v==null?'—':Math.round(100*v)+'%';
  const cR=v=>v==null?'var(--dim)':v>=.08?'var(--green)':v>=.04?'#8bc34a':v>=.015?'var(--txt)':v>=0?'#ff8a65':'var(--red)';
  const cA=v=>v==null?'var(--dim)':v>=.58?'var(--green)':v>=.54?'#8bc34a':v>=.515?'var(--txt)':v>=.5?'#ff8a65':'var(--red)';
  const cE=v=>v==null?'var(--dim)':v>=1?'var(--green)':v>=.4?'#8bc34a':v>=0?'var(--txt)':'var(--red)';
  const KIND={tdA:['m','matchup'],ydA:['m','matchup'],psi:['m','matchup'],meta:['x','blend'],h2h:['m','history'],sch:['m','scheme'],atd:['p','model'],imp:['x','market'],form:['p','player'],tdr:['p','player']};
  const SRCDEP=new Set(['tdA','ydA','psi','meta']);
  el.innerHTML=`<div class="controls">
    <select id="btSe" title="which season is replayed">${SES.map(s=>`<option value="${s}">replay ${s} · weeks ${B.sigs[s].weeks[0]}–${B.sigs[s].weeks.slice(-1)[0]}</option>`).join('')}</select>
    <span class="chips" id="btPos" title="which position the signal race scores">${['ALL','QB','RB','WR','TE'].map(p=>`<button data-p="${p}" class="${p===pos?'on':''}">${p==='ALL'?'all':p}</button>`).join('')}</span>
    <select id="btSrc" title="which data set the DvP signals (TD allowed, yards allowed, Ψ, META) read in the signal race"></select>
    <span class="mini" style="color:var(--dim)">built ${esc(B.built)} · point in time: every week predicted only from the games before it</span>
  </div>
  <div class="wktiles" id="btTiles" data-mg="1"></div>
  <div class="panel"><h3>what the backtest says <span class="f">plain-language takeaways, recomputed every build</span></h3><ul class="btins" id="btIns"></ul></div>
  <div class="panel"><h3 id="btDh"></h3><div id="btDs"></div></div>
  <div class="panel"><h3 id="btSh"></h3><div id="btSg"></div></div>
  <div class="wk2b"><div class="panel"><h3 id="btMh"></h3><div id="btMx"></div></div><div class="panel"><h3 id="btWh"></h3><div id="btDw"></div></div></div>
  <div class="panel"><h3 id="btKh"></h3><div id="btWk"></div></div>
  <div class="panel"><h3>the tracked strategies — every frozen pick, graded <span class="f">picks frozen before kickoff (picks_all.csv), graded from the box scores · break-even = what a pick must hit to pay at the price · beat the close = the line moved toward the pick</span></h3><div id="btSt"></div></div>`;
  const sigVal=(k,s)=>{const x=B.sigs[S].sig[k];if(!x)return {};const o=SRCDEP.has(k)?(x.src[s||src]||{}):x.all;return pos==='ALL'?o:(o[pos]||{})};
  function render(){
    const DS=B.dsets[S]||{rows:[],weeks:[]},SG=B.sigs[S],L=LB(S);
    $('#btSrc').innerHTML=B.srcs.filter(k=>Object.values(SG.sig.psi.src).length&&SG.sig.psi.src[k]&&SG.sig.psi.src[k].n).map(k=>`<option value="${k}" ${k===src?'selected':''}>DvP signals read: ${esc(L[k]||k)}</option>`).join('');
    if(!SG.sig.psi.src[src]||!SG.sig.psi.src[src].n){src='comb';$('#btSrc').value=src}
    const keys=Object.keys(SG.sig);
    const rank=(m,excl)=>keys.filter(k=>!(excl||[]).includes(k)).map(k=>({k,v:sigVal(k)[m]})).filter(x=>x.v!=null).sort((a,b)=>b.v-a.v);
    const bA=rank('auc'),bN=rank('rn',['form','tdr']),best=DS.rows[0],mA=sigVal('meta').auc,mr=bA.findIndex(x=>x.k==='meta')+1,h=sigVal('h2h');
    $('#btTiles').innerHTML=(best?wkTile('most accurate data set',esc(best.lbl),`ρ ${fr(best.all)} on next week · best in ${best.wins} of ${best.weeks} weeks`,'g',true):'')
      +(bA[0]?wkTile('best TD picker',esc(SG.sig[bA[0].k].lbl),`AUC ${fa(bA[0].v)} · .500 = coin flip`,'g',true):'')
      +(bN[0]?wkTile('best matchup read',esc(SG.sig[bN[0].k].lbl),`ρ ${fr(bN[0].v)} with beating his own average`,'g',true):'')
      +wkTile('META',fa(mA),`AUC · #${mr} of ${bA.length} signals${pos!=='ALL'?' · '+pos:''}`,mA>=.54?'g':'',true)
      +wkTile('H2H',fa(h.auc),h.auc!=null&&h.auc<.52?'no signal — at or below a coin flip':'AUC on players with a prior meeting',h.auc!=null&&h.auc<.5?'r':'',true)
      +wkTile('sample',String(SG.n),`player-games · weeks ${SG.weeks[0]}–${SG.weeks.slice(-1)[0]} · ${DS.cells||0} defense-stat-weeks`,'',true);
    $('#btIns').innerHTML=B.ins.filter(x=>x.s===S||x.s==='all').map(x=>`<li><span class="s">${x.s==='all'?'record':x.s}</span>${x.t.replace(/^\d{4}[:,]\s*/,'')}</li>`).join('');
    /* ---- data sets: what a defense allows next week ---- */
    const mx=Math.max(.001,...DS.rows.map(r=>r.all||0));
    $('#btDh').innerHTML=`which data set predicts what a defense allows next week — ${S} <span class="f">for every stat column and week: rank correlation between the data set's per-game number and what each defense actually allowed that week (0 = no better than a coin flip, 1 = the order was exactly right), averaged · hover a number for its uncertainty · weeks best = weeks it had the highest average</span>`;
    $('#btDs').innerHTML=`<table class="fx bt"><thead><tr><th>data set</th><th class="w">what it is</th><th class="n" title="every stat">all stats</th><th class="n">yards</th><th class="n">catches</th><th class="n">TDs</th><th class="n">QB</th><th class="n">RB</th><th class="n">WR</th><th class="n">TE</th><th class="n">weeks best</th></tr></thead><tbody>
      ${DS.rows.map((r,i)=>`<tr class="${i===0?'best':''}"><td><b>${esc(r.lbl)}</b></td><td class="w">${esc(r.role)}</td>
        <td class="n" data-v="${r.all}"><b style="color:${cR(r.all)}" title="± ${(r.se||0).toFixed(3).replace(/^0/,'')} (the uncertainty)">${fr(r.all)}</b><i class="bar" style="width:${Math.max(2,Math.round(60*Math.max(0,r.all||0)/mx))}px;background:${cR(r.all)}"></i></td>
        ${['Yds','Rec','TD'].map(f=>`<td class="n" data-v="${r.fam[f]??''}" style="color:${cR(r.fam[f])}">${fr(r.fam[f])}</td>`).join('')}
        ${['QB','RB','WR','TE'].map(g=>`<td class="n" data-v="${r.grp[g]??''}" style="color:${cR(r.grp[g])}">${fr(r.grp[g])}</td>`).join('')}
        <td class="n" data-v="${r.wins}">${r.wins}<span class="mini"> / ${r.weeks}</span></td></tr>`).join('')}</tbody></table>`;
    /* ---- signals: the player's game ---- */
    $('#btSh').innerHTML=`which signal calls the player's game — ${S}${pos!=='ALL'?' · '+pos:''} <span class="f">QB1 / RB1 / RB2 / WR1-3 / TE1 owners, each compared only with players in the same slot that week · TD AUC = how often a scorer was ranked above a non-scorer (.500 = coin flip) · PPR ρ = order vs his fantasy points · vs-norm ρ = order vs points above his own recent average (the pure matchup effect) · soft − tough = points over his norm, softest third minus toughest third · DvP signals read ${esc(L[src]||src)}</span>`;
    const SR=keys.map(k=>({k,x:SG.sig[k],v:sigVal(k)})).sort((a,b)=>(b.v.auc??-1)-(a.v.auc??-1));
    $('#btSg').innerHTML=`<table class="fx bt"><thead><tr><th>signal</th><th class="c">kind</th><th class="w">what it reads</th><th class="n" title="share of player-games where the signal exists">covers</th><th class="n">TD AUC</th><th class="n">PPR ρ</th><th class="n">vs-norm ρ</th><th class="n" title="points above his norm: softest third minus toughest third">soft − tough</th><th class="n" title="how often the softest third scored a TD">TD% soft</th><th class="n" title="how often the toughest third scored a TD">TD% tough</th></tr></thead><tbody>
      ${SR.map(({k,x,v},i)=>{const o=SRCDEP.has(k)?(x.src[src]||{}):x.all;return `<tr class="${i===0?'best':''}"><td><b>${esc(x.lbl)}</b></td><td class="c"><span class="kd ${KIND[k][0]}">${KIND[k][1]}</span></td><td class="w">${esc(x.desc)}</td>
        <td class="n" data-v="${o.cov??''}">${pc(o.cov)}</td><td class="n" data-v="${v.auc??''}"><b style="color:${cA(v.auc)}">${fa(v.auc)}</b></td><td class="n" data-v="${v.rr??''}" style="color:${cR(v.rr)}">${fr(v.rr)}</td>
        <td class="n" data-v="${v.rn??''}"><b style="color:${cR(v.rn)}">${fr(v.rn)}</b></td><td class="n" data-v="${v.edge??''}" style="color:${cE(v.edge)}">${fp(v.edge)}</td>
        <td class="n" data-v="${v.tdt??''}">${pc(v.tdt)}</td><td class="n" data-v="${v.tdb??''}">${pc(v.tdb)}</td></tr>`}).join('')}</tbody></table>
      <p class="mini" style="margin:6px 0 0;color:var(--dim)">matchup = what the opponent allows · player = his own numbers · model = TD Picks · market = the betting line · blend = META. His own form ranks raw points best but runs <i>below</i> his norm (a hot player cools off) — that's regression, not a matchup.</p>`;
    /* ---- data set x DvP signal ---- */
    const MET={auc:['TD AUC',fa,cA],rn:['vs-norm ρ',fr,cR],edge:['soft − tough',fp,cE]};
    $('#btMh').innerHTML=`every data set × every DvP signal — ${S}${pos!=='ALL'?' · '+pos:''} <span class="chips" id="btMet" style="margin-left:8px">${Object.entries(MET).map(([k,[l]])=>`<button data-m="${k}" class="${k===met?'on':''}">${l}</button>`).join('')}</span><span class="f">the same four signals read through each version of the defense tables · outlined = the best data set for that signal</span>`;
    const DK=['tdA','ydA','psi','meta'],[ml,mf,mc]=MET[met],SRC=B.srcs.filter(k=>SG.sig.psi.src[k]&&SG.sig.psi.src[k].n);
    const bestOf=k=>{let b=null,bv=-9;SRC.forEach(s=>{const v=sigVal(k,s)[met];if(v!=null&&v>bv){bv=v;b=s}});return b};
    const BB=Object.fromEntries(DK.map(k=>[k,bestOf(k)]));
    $('#btMx').innerHTML=`<table class="fx bt"><thead><tr><th>data set</th>${DK.map(k=>`<th class="n">${esc(SG.sig[k].lbl)}</th>`).join('')}</tr></thead><tbody>
      ${SRC.map(s=>`<tr><td><b>${esc(L[s]||s)}</b></td>${DK.map(k=>{const v=sigVal(k,s)[met];return `<td class="n${BB[k]===s?' hb':''}" data-v="${v??''}" style="color:${mc(v)}">${mf(v)}</td>`}).join('')}</tr>`).join('')}</tbody></table>`;
    $('#btMet').querySelectorAll('button').forEach(b=>b.onclick=()=>{met=b.dataset.m;render()});
    /* ---- data sets week by week ---- */
    $('#btWh').innerHTML=`data sets week by week — ${S} <span class="f">average rank correlation on that week · outlined = the week's best</span>`;
    const DR=DS.rows.slice().sort((a,b)=>B.srcs.indexOf(a.k)-B.srcs.indexOf(b.k));
    $('#btDw').innerHTML=`<table class="fx bt"><thead><tr><th>wk</th>${DR.map(r=>`<th class="n">${esc(r.lbl)}</th>`).join('')}</tr></thead><tbody>
      ${DS.weeks.map(w=>{const vals=DR.map(r=>r.wk[w]),mxw=Math.max(...vals.filter(v=>v!=null));return `<tr><td>${w}</td>${vals.map(v=>`<td class="n${v!=null&&v===mxw?' hb':''}" data-v="${v??''}" style="color:${cR(v)}">${fr(v)}</td>`).join('')}</tr>`}).join('')}</tbody></table>`;
    /* ---- signals week by week ---- */
    const WK=Object.keys(SG.wk).map(Number).sort((a,b)=>a-b),KS=keys.filter(k=>SG.wk[WK[0]]&&SG.wk[WK[0]][k]!==undefined);
    $('#btKh').innerHTML=`signals week by week — ${S} <span class="f">TD AUC each week, every position (DvP signals on the combined data set) · outlined = the week's best · one week is a small sample — read the season line above first</span>`;
    $('#btWk').innerHTML=`<table class="fx bt"><thead><tr><th>wk</th>${KS.map(k=>`<th class="n">${esc(SG.sig[k].lbl)}</th>`).join('')}</tr></thead><tbody>
      ${WK.map(w=>{const vals=KS.map(k=>(SG.wk[w][k]||{}).auc),mxw=Math.max(...vals.filter(v=>v!=null));return `<tr><td>${w}</td>${vals.map(v=>`<td class="n${v!=null&&v===mxw?' hb':''}" data-v="${v??''}" style="color:${cA(v)}">${fa(v)}</td>`).join('')}</tr>`}).join('')}</tbody></table>`;
    /* ---- strategies ---- */
    const st=B.strat||[],T=B.tdp||{};
    $('#btSt').innerHTML=`<table class="fx bt"><thead><tr><th>strategy</th><th class="n">record</th><th class="n">hit</th><th class="n">break-even</th><th class="n">vs break-even</th><th class="n">beat the close</th><th class="n">still open</th></tr></thead><tbody>
      ${st.map(r=>{const d=r.hit!=null&&r.be!=null?r.hit-r.be:null;return `<tr><td><b>${esc(r.lbl)}</b></td><td class="n" data-v="${r.w}">${r.w}-${r.l}${r.p?'-'+r.p:''}</td><td class="n" data-v="${r.hit??''}"><b>${pc(r.hit)}</b></td><td class="n" data-v="${r.be??''}">${pc(r.be)}</td>
        <td class="n" data-v="${d??''}"><b style="color:${d==null?'var(--dim)':d>.01?'var(--green)':d<-.01?'var(--red)':'var(--txt)'}">${d==null?'—':(d<0?'−':'+')+Math.abs(Math.round(1000*d)/10)+' pts'}</b></td><td class="n" data-v="${r.clv??''}">${r.clv!=null?pc(r.clv)+`<span class="mini"> of ${r.clvn}</span>`:'—'}</td><td class="n">${r.open||''}</td></tr>
        ${(r.buckets||[]).map(b=>`<tr class="btsub"><td>${esc(b.lbl)}</td><td class="n">${b.n}</td><td class="n" style="color:${b.hit>=.524?'var(--green)':'var(--red)'}">${pc(b.hit)}</td><td class="n">52%</td><td colspan="3"></td></tr>`).join('')}
        ${(r.markets||[]).map(b=>`<tr class="btsub"><td>${esc(b.lbl)}</td><td class="n">${b.n}</td><td class="n" style="color:${b.hit>=.524?'var(--green)':'var(--red)'}">${pc(b.hit)}</td><td class="n">52%</td><td colspan="3"></td></tr>`).join('')}`}).join('')}
      ${T.auc?`<tr><td><b>TD Picks model (walk-forward)</b></td><td class="n">${T.top10?T.top10[0]+' / '+T.top10[1]:'—'}</td><td class="n"><b>${T.top10?pc(T.top10[0]/T.top10[1]):'—'}</b></td><td class="n" title="the field's TD rate">—</td><td class="n" colspan="3" style="text-align:left;color:var(--dim)">each week's ten highest-rated, ${T.weeks} weeks · AUC ${fa(T.auc)} vs ${fa(T.base)} for slot alone${T.lock?` · locks (50%+) ${T.lock[1]} of ${T.lock[0]}`:''}</td></tr>`:''}</tbody></table>`;
    tWire(el)}
  $('#btSe').onchange=()=>{S=$('#btSe').value;render()};$('#btSrc').onchange=()=>{src=$('#btSrc').value;render()};
  $('#btPos').querySelectorAll('button').forEach(b=>b.onclick=()=>{pos=b.dataset.p;$('#btPos').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render()});
  render();
}

/* ---------------- Weeklies (F6 TEST) — the touchdown lookback ----------------''')
open(P, 'w', encoding='utf-8').write(s)
print('patch_v27_backtest: Backtest tab added')
