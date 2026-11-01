"""v57 — META and META v2 back to the rule: ONE composite column, the rest separated by position.
Five sections (all · QB · RB · WR · TE) like the TD Grid; each row = player · opp · the composite (META / CONS).
Every signal stays inside the composite and its hover breakdown; no signal columns, no position tabs, no lens chips.
Rerunnable; guarded by /* v57 */."""
import sys
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v57 */' in s:
    print('v57 already applied'); sys.exit(0)
assert '/* v56 */' in s, 'needs v56 first'

def rep(old, new, n=1, src=None):
    global s
    t = s if src is None else src
    c = t.count(old); assert c == n, f'expected {n} got {c}: {old[:100]!r}'
    t = t.replace(old, new)
    if src is None: s = t
    return t

rep("</style>", "/* v57 */ .meta .lgt td.md.gs .badge{min-width:30px;font-size:12px}\n</style>")
LG = "  <div class=\"lgrid td5 wide full meta\">${['ALL'].concat(TPOS).map(p=>`<section class=\"lgcol\"><h3>${p==='ALL'?'◉ all':posIcon(p,12)+' '+p} <span class=\"gl\" id=\"${px}G${p}\"></span> <span class=\"f\" id=\"${px}N${p}\"></span></h3><div id=\"${px}B${p}\"></div></section>`).join('')}</div>`;"

# ---------- META ----------
a = s.index('function metaGrid('); b = s.index('/* ---------------- v44: META v2', a); m = s[a:b]
m = rep('<span class="chips" id="${px}Lens" title="what every column is ranked by', '<span class="chips" id="${px}Lens" style="display:none" title="what every column is ranked by', 1, m)
i = m.index('  <div class="controls"><span class="chips" id="${px}Pos"'); j = m.index('</div></div>`;', i) + len('</div></div>`;')
m = m[:i] + LG + m[j:]
m = rep("Hover any META cell for the full breakdown · lens chips re-rank the table · a header click re-sorts one column · click a name for his card</span>",
        "One column: META. Hover any META cell for the full breakdown, every signal and its weight · every position together, then QB, RB, WR, TE · click a name for his card</span>", 1, m)
m = rep("sigs=()=>SIGS.filter(k=>HAS[k]);let posTab='ALL';", "sigs=()=>['meta'];", 1, m)
m = m.replace("$$('NALL').textContent", "$$('N'+p).textContent")
m = rep("$$('GALL').textContent=`ranked by ${LBL[st.k]||st.k} · ${setL()} · ${$$('Mode').value==='bt'?'backtest recipe':'all-in recipe'}`;$$('H').firstChild.textContent=(p==='ALL'?'◉ all':p)+' ';",
        "$$('G'+p).textContent=`${st.k==='meta'?'':'by '+(LBL[st.k]||st.k)+' · '}${setL()} · ${$$('Mode').value==='bt'?'backtest recipe':'all-in'}`;", 1, m)
m = m.replace("$$('BALL')", "$$('B'+p)")
m = rep("const S=sigs(),wname=13,wpos=p==='ALL'?4:0,wopp=8,", "const S=sigs(),wname=p==='ALL'?46:56,wpos=p==='ALL'?10:0,wopp=22,", 1, m)
m = rep("    tWire($$('B'+p));\n  }", "    tWire($$('B'+p));\n    const sec=$$('B'+p).closest('.lgcol'),h=sec&&sec.querySelector('h3');if(h)sec.style.setProperty('--h3h',h.offsetHeight+'px');\n  }", 1, m)
m = rep("const cols=()=>{col(posTab);lead()};", "const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead()};", 1, m)
m = rep("  $$('Pos').querySelectorAll('button').forEach(b=>b.onclick=()=>{posTab=b.dataset.p;$$('Pos').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));col(posTab)});\n", "", 1, m)
s = s[:a] + m + s[b:]

# ---------- META v2 ----------
a = s.index('function metaV2('); b = s.index('/* ---------------- METAPROP', a); m = s[a:b]
m = rep('<span class="chips" id="${px}Pos" title="which position the table shows"><button data-p="ALL" class="on">all</button>${TPOS.map(p=>`<button data-p="${p}">${p}</button>`).join(\'\')}</span>\n    ', '', 1, m)
m = rep('<span class="chips" id="${px}Lens" title="rank the table by — CONS folds every board; click any column header to sort it too"><button data-l="cons" class="on">CONS</button>${MV_B.map(b=>`<button data-l="${b[0]}" title="${esc(b[2])}">${b[1]}</button>`).join(\'\')}</span>\n    ', '', 1, m)
m = rep('<span class="note">every board that ranks this week\'s players, compiled. Each cell is <b>that board\'s own number</b> (TD and Ψ = rank of ${NT}, 1 = softest; TDP = chance he scores; META 0–100 …), shaded by his percentile at his position — hover for it; <b>CONS</b> folds the percentiles &middot; <b>T10</b> = how many boards put him in their top 10%, <b>T25</b> their top quarter &middot; hover a cell for the raw number, a CONS cell for every board</span>',
        '<span class="note">every board that ranks this week\'s players, folded into one number. <b>CONS</b> = his percentile at his position on every board in the fold (TD Grid, Ψ, H2H, TD Picks, First TD, Weeklies, categories, META, red zone, snaps, ENV, FORM, scheme, market), combined by the method in the select and shrunk toward 50 when few boards have him &middot; hover a CONS cell for every board\'s own number, his percentile on it, and how many boards put him in their top 10% / top quarter &middot; board chips drop a board from the fold</span>', 1, m)
m = rep('<div class="panel"><h3>the boards compiled <span class="gl" id="${px}GALL"></span> <span class="f" id="${px}NALL"></span></h3><div id="${px}BALL" class="tscroll"></div></div>`;', LG, 1, m)
m = rep("const sort={ALL:{k:'cons',a:false}};", "const sort={};['ALL'].concat(TPOS).forEach(p=>sort[p]={k:'cons',a:false});", 1, m)
m = rep("const R=ROWS.filter(x=>(posTab==='ALL'||x.pos===posTab)&&keep(x)).sort(cmp(st.k,st.a));", "const R=ROWS.filter(x=>(p==='ALL'||x.pos===p)&&keep(x)).sort(cmp(st.k,st.a));", 1, m)
m = rep("$$('N'+p).textContent=R.length+(R.length===1?' player':' players')+(posTab==='ALL'?'':' · '+posTab);$$('G'+p).textContent=`ranked by ${st.k==='cons'?'CONS':st.k==='t10'?'T10':st.k==='t25'?'T25':st.k==='nb'?'boards':LBL[st.k]||st.k} · ${$$('Src').value}`;",
        "$$('N'+p).textContent=R.length+(R.length===1?' player':' players');$$('G'+p).textContent=`${st.k==='cons'?'':'by '+(st.k)+' · '}${ks.length} boards · ${$$('Src').value}`;", 1, m)
m = rep("const wname=14,wpos=5,wopp=8,wc=6,wt=4,wn=((100-wname-wpos-wopp-wc-2*wt)/Math.max(ks.length,1)).toFixed(2);", "const wname=p==='ALL'?46:56,wpos=p==='ALL'?10:0,wopp=22;", 1, m)
m = rep("""<col style="width:${wopp}%"><col style="width:${wc}%"><col style="width:${wt}%"><col style="width:${wt}%">${ks.map(()=>`<col style="width:${wn}%">`).join('')}</colgroup>""", """<col style="width:${wopp}%"><col style="width:${100-wname-wpos-wopp}%"></colgroup>""", 1, m)
m = rep('<table class="lgt mvt">', '<table class="lgt">', 1, m)
m = rep("""${th('cons','CONS','the boards folded · 0–100 · hover for every board','md gs')}${th('t10','T10','boards where he is in the top 10% of his position','md')}${th('t25','T25','boards where he is in the top quarter of his position','md')}${ks.map(k=>th(k,LBL[k],TIP[k]+' · the board\\'s own number, shaded by his percentile at the position (hover)','op')).join('')}</tr></thead>""",
        """${th('cons','CONS','every board folded into one · 0–100 · hover for every board, his percentile on each, and his top-10% / top-quarter counts','md gs')}</tr></thead>""", 1, m)
m = rep("""<td class="md" title="top 10% on ${x.t10} of ${x.nb} boards"><b style="color:${x.t10>=4?'#00c853':x.t10>=2?'#8bc34a':'var(--dim)'}">${x.t10||''}</b></td><td class="md" title="top quarter on ${x.t25} of ${x.nb} boards">${x.t25||''}</td>
        ${ks.map(k=>cell(k,x)).join('')}</tr>`}).join('')||`<tr><td colspan="${ks.length+6}" class="dim">nothing matches</td></tr>`}</tbody></table>`;""",
        """</tr>`}).join('')||`<tr><td colspan="${p==='ALL'?4:3}" class="dim">nothing matches</td></tr>`}</tbody></table>`;""", 1, m)
m = rep("    tWire($$('B'+p))}\n  function lead(){", "    tWire($$('B'+p));const sec=$$('B'+p).closest('.lgcol'),h=sec&&sec.querySelector('h3');if(h)sec.style.setProperty('--h3h',h.offsetHeight+'px')}\n  function lead(){", 1, m)
m = rep("const cols=()=>{col('ALL');lead()};const all=()=>{build();cols()};", "const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead()};const all=()=>{build();cols()};", 1, m)
m = rep("  $$('Pos').querySelectorAll('button').forEach(b=>b.onclick=()=>{posTab=b.dataset.p;$$('Pos').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));col('ALL')});\n", "", 1, m)
m = rep("  $$('Lens').querySelectorAll('button').forEach(b=>b.onclick=()=>{const k=b.dataset.l;sort.ALL={k,a:false};$$('Lens').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));col('ALL')});\n", "", 1, m)
s = s[:a] + m + s[b:]

# intro / desc
rep("'position tabs pick the table; lens chips re-rank it; the data-set select (2024 · 2025 · 2026 · combined · adjusted · μ) drives TD, Ψ and META']},",
    "'one column — META; every position together, then QB, RB, WR and TE; the data-set select (2024 · 2025 · 2026 · combined · adjusted · μ) drives the Ψ and TD inside it']},")
rep("with declared weights \\u2014 one table with position tabs, the week\\'s best spot on each signal across the top'", "with declared weights \\u2014 one column, every position together then QB, RB, WR and TE, the week\\'s best spot on each signal across the top'")
rep("META (all-in), red zone, snaps, ENV, FORM, scheme, market edge · position tabs and lens chips re-rank the table'", "META (all-in), red zone, snaps, ENV, FORM, scheme, market edge · one CONS column, every position together then QB, RB, WR and TE'")
rep("'every board that ranks this week\\'s players, side by side, each cell the board\\'s own number shaded by where he sits among his position (hover for the percentile): ", "'every board that ranks this week\\'s players folded into one CONS number per man (hover it for every board\\'s own number and his percentile on it): ")
i = s.index("Object.assign(NOTES,{"); s = s[:i] + "Object.assign(NOTES,{v57:['META and META v2: one composite column (META / CONS), every position together then QB, RB, WR, TE — every signal lives inside the composite and its hover breakdown; signal columns, position tabs and lens chips removed']," + s[i+len("Object.assign(NOTES,{"):]
open(P, 'w', encoding='utf-8').write(s); print('v57 applied')
