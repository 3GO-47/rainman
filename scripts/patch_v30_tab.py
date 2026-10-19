"""v30 — the card on the Backtest tab: the five rules, the step-by-step funnel from every lean to the card (bets and units at each
step, week by week), 'Player props — the card' first and 'every lean (the old way)' last. Apply after patch_v29b_units.py.
Usage: python scripts/patch_v30_tab.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v30_tab: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

rep(r'''const st=(B.strat||[]).slice().sort((a,b)=>(b.w+b.l)-(a.w+a.l))''',
    r'''const st=(B.strat||[]).slice().sort((a,b)=>(a.k==='PROP'?-1:b.k==='PROP'?1:0)||(a.k==='LEAN'?1:b.k==='LEAN'?-1:0)||(b.w+b.l)-(a.w+a.l))''')
rep(r'''    $('#btSt').innerHTML=st.map(card).join('')''', r'''    const FN=(B.card||{}).funnel||[];
    const fun=FN.length?`<div class="btfun" data-bst="PROP" title="click for the rules, the funnel week by week and every bet">${FN.map((f,i)=>`<div class="st${i===FN.length-1?' last':''}"><b>${f.n}</b><span>${esc(f.lbl)}</span><i style="color:${f.units>=0?'var(--green)':'var(--red)'}">${f.units>=0?'+':''}${f.units}u · ${f.w}-${f.l}</i></div>`).join('<em>›</em>')}</div>`:'';
    $('#btSt').innerHTML=fun+st.map(card).join('')''')
rep(r'''<h3>are the strategies making money? <span class="f">every pick frozen before kickoff, graded from the box scores</span></h3>''',
    r'''<h3>are the strategies making money? <span class="f">props are bet only when they pass all five rules of the card — the strip shows what each rule removed and what it did to the money · every pick frozen before kickoff, graded from the box scores · click anything for the proof</span></h3>''')

# the rules + funnel inside the props pop-up; 'every lean' gets its own pop-up (the page carries only bets)
rep(r'''  function stPop(t){''', r'''  const funWeeks=()=>[...new Set(((B.card||{}).funnel||[]).flatMap(f=>Object.keys(f.wk).map(Number)))].sort((a,b)=>a-b);
  const funTbl=()=>{const F=(B.card||{}).funnel||[],W=funWeeks();return `<table class="fx bt"><thead><tr><th>step</th><th>bets</th><th>record</th><th>hit</th><th>units</th>${W.map(w=>`<th>wk ${w}</th>`).join('')}</tr></thead><tbody>
    ${F.map((f,i)=>`<tr class="${i===F.length-1?'best':''}"><td>${i?'+ ':''}${esc(f.lbl)}</td><td>${f.n}</td><td>${f.w}-${f.l}</td><td>${pc(f.hit)}</td><td data-v="${f.units}"><b style="color:${f.units>=0?'var(--green)':'var(--red)'}">${f.units>=0?'+':''}${f.units}</b></td>${W.map(w=>{const u=f.wk[w];return `<td data-v="${u??''}" style="color:${u==null?'var(--dim)':u>=0?'var(--green)':'var(--red)'}">${u==null?'—':(u>=0?'+':'')+u}<span class="mini"> · ${(f.wn||{})[w]||0}</span></td>`}).join('')}</tr>`).join('')}</tbody></table>`};
  const cardBox=()=>B.card?`<div class="panel"><h3>the strategy — a prop is bet only when all five hold <span class="f">${esc(B.card.note)}</span></h3><ol class="btrules">${B.card.rules.map(r=>`<li>${esc(r)}</li>`).join('')}</ol>
    <h3 style="margin-top:10px">how the card is built from every lean <span class="f">each step adds one rule · units at the price taken · week columns = units · bets</span></h3>${funTbl()}</div>`:'';
  function leanPop(){const r=(B.strat||[]).find(x=>x.k==='LEAN')||{};
    modal('Player props — every lean (the old way)','every prop the books posted got a side and counted as a bet — kept now only as research',
      `<div class="kpis">${kpi('record',`${r.w??0}-${r.l??0}${r.p?'-'+r.p:''}`,'every posted prop')}${kpi('hit rate',pc(r.hit),`needs ${pc(r.be)} at the prices taken`,r.hit>r.be?'g':'r')}${kpi('units',`${(r.units||0)>=0?'+':''}${(r.units||0).toFixed(1)}`,'1 unit a pick at the price taken',(r.units||0)>=0?'g':'r')}${kpi('beat the closing line',pc(r.clv),`${r.clvn||0} with a closing line`)}</div>
      ${cardBox()}<p class="mini" style="margin:6px 2px">Every lean is still frozen and graded in bet_ledger.csv / picks_all.csv for research; the site now carries and counts only the bets on the card.</p>`)}
  function stPop(t){if(t==='LEAN'){leanPop();return}''')
rep(r'''<div class="panel"><h3>week by week <span class="f">running units = the total after that week</span></h3>''',
    r'''${tp==='PROP'?cardBox():''}<div class="panel"><h3>week by week <span class="f">running units = the total after that week</span></h3>''')
rep(r'''.btb{position:relative;display:block;height:12px;''', r'''.btfun{grid-column:1/-1;display:flex;align-items:stretch;gap:6px;cursor:pointer;margin:0 0 4px;flex-wrap:wrap}.btfun .st{flex:1;min-width:118px;background:var(--panel);border:1px solid var(--edge);border-radius:8px;padding:8px 10px;display:flex;flex-direction:column;gap:3px}
.btfun .st b{font:700 18px var(--mono);color:var(--txt)}.btfun .st span{font-size:11px;color:var(--dim);line-height:1.3}.btfun .st i{font:700 11.5px var(--mono);font-style:normal}.btfun .st.last{border-color:var(--green);box-shadow:inset 0 0 0 1px #00c85355}.btfun em{align-self:center;color:var(--dim2);font-style:normal}.btfun:hover .st{border-color:var(--edge2)}
#ppModal ol.btrules{margin:4px 0 6px 18px;padding:0;font-size:12.5px;line-height:1.65}
@media(max-width:840px){.btfun em{display:none}.btfun .st{min-width:44%}}
.btb{position:relative;display:block;height:12px;''')
rep("Object.assign(NOTES,{backtest:['v29','", "Object.assign(NOTES,{backtest:['v30','props are bet only on the card — five rules (edge 6%+, price −200..+200, the model itself 50%+, one per player, 3 per game); the strip shows each rule\\'s effect, every lean stays as research · ")
open(P, 'w', encoding='utf-8').write(s)
print('patch_v30_tab: the card on Backtest')
