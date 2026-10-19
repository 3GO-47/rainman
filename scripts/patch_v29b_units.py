"""v29b — money, not hit rate: every strategy card and pop-up counts units at the price each pick was taken at
(picks_all.csv 'price', patch_v29_prices.py), the site-wide pkUnits does the same, and 'Player props — plays (EV 3%+)' gets its
own card and pop-up beside every lean. Apply after patch_v29_backtest_pops.py.
Usage: python scripts/patch_v29b_units.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v29b: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# units site-wide: the posted price when the pick carries one
rep(r'''const pkUnits=p=>{if(p.result==='W'){const mp=+p.market_ref;return (p.type==='ML'||p.type==='TD')&&mp>0&&mp<1?(1/mp-1):0.909}return p.result==='L'?-1:0};''',
    r'''const pkUnits=p=>{if(p.result==='W'){const a=+p.price,mp=+p.market_ref;if(p.price!==''&&p.price!=null&&a)return a>0?a/100:100/-a;return (p.type==='ML'||p.type==='TD')&&mp>0&&mp<1?(1/mp-1):0.909}return p.result==='L'?-1:0};''')

# the cards: units decide 'making money'
i0 = s.index("    const card=(name,rec,hit,need,note,n,key)=>{")
i1 = s.index("r.w+r.l,r.k)}).join('')", i0) + len("r.w+r.l,r.k)}).join('')")
s = s[:i0] + r'''    const card=r=>{const n=r.w+r.l,few=n<30,win=(r.units||0)>0,tone=few?'a':win?'g':'r';
      return `<div class="c ${tone}" data-bst="${r.k}"><div class="k">${esc(r.lbl)}</div><div class="h">${(r.units||0)>=0?'+':''}${(r.units||0).toFixed(1)}u <span class="bd ${tone}">${few?'too few to tell':win?'making money':'losing money'}</span></div><div class="s">${r.w}-${r.l}${r.p?'-'+r.p:''} · hit ${pc(r.hit)} · needs ${pc(r.be)} at the prices taken</div></div>`};
    $('#btSt').innerHTML=st.map(card).join('')''' + s[i1:]

# the strategy pop-up: price-aware units, the plays filter, a price column
rep(r'''function stPop(t){const R0=(J.picksAll||[]).filter(p=>p.type===t),r=(B.strat||[]).find(x=>x.k===t)||{};''',
    r'''function stPop(t){const tp=t==='PLAY'?'PROP':t,R0=(J.picksAll||[]).filter(p=>t==='PLAY'?p.type==='PROP'&&+p.edge>=3:p.type===t),r=(B.strat||[]).find(x=>x.k===t)||{};''')
rep(r'''(J.picksClv||[]).forEach(c=>{if(c.type===t)CL[''', r'''(J.picksClv||[]).forEach(c=>{if(c.type===tp)CL[''')
rep(r'''const m110=['PROP','ATS','TOTAL'].includes(t),unit=p=>p.result==='W'?(m110?100/110:(+p.market_ref>0?1/(+p.market_ref)-1:100/110)):p.result==='L'?-1:0;''',
    r'''const dw=p=>{const a=+p.price;if(p.price!==''&&p.price!=null&&a)return a>0?a/100:100/-a;const m=+p.market_ref;return (tp==='ML'||tp==='TD')&&m>0&&m<1?1/m-1:100/110},unit=p=>p.result==='W'?dw(p):p.result==='L'?-1:0;''')
rep(r'''const pick=p=>t==='PROP'||t==='TD'?''', r'''const pick=p=>tp==='PROP'||tp==='TD'?''')
rep(r'''${kpi('units',`${U>=0?'+':''}${U.toFixed(1)}`,m110?'1 unit a pick at −110':'1 unit a pick at the market\'s price',U>=0?'g':'r')}''',
    r'''${kpi('units',`${U>=0?'+':''}${U.toFixed(1)}`,'1 unit a pick, paid at the price it was taken at',U>=0?'g':'r')}''')
rep(r'''${t==='PROP'?`<div class="btx2">''', r'''${tp==='PROP'?`<div class="btx2">''')
rep(r'''<th>side</th><th>line</th><th>model</th><th>market</th><th>edge</th><th>result</th><th>actual</th><th>close</th><th>beat close</th>''', r'''<th>side</th><th>line</th><th>price</th><th>model</th><th>market</th><th>edge</th><th>result</th><th>actual</th><th>close</th><th>beat close</th>''')
rep(r'''<td class="n">${esc(p.line||'')}</td><td class="n" data-v="${p.model||''}">''', r'''<td class="n">${esc(p.line||'')}</td><td class="n" data-v="${p.price||''}">${p.price!==''&&p.price!=null&&!isNaN(+p.price)?(+p.price>0?'+':'')+(+p.price):'—'}</td><td class="n" data-v="${p.model||''}">''')
rep(r'''<span class="f">model / market = chance of the pick hitting''', r'''<span class="f">price = the odds it was taken at · model / market = chance of the pick hitting''')
open(P, 'w', encoding='utf-8').write(s)
print('patch_v29b: units at the price taken')
