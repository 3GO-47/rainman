"""v56 — META rebuilt as the all-in composite, and the red-zone layer wired into every board.

META (F2 → META): every signal the dash gathers, folded with declared weights — Ψ .15 · RZ .16 · ATD .12 · ENV .10 ·
  TD .09 · SCH .08 · FORM .07 · H2H .07 · MKT .06 · SNP .05 · 1st .05; the walk-forward backtest's Ψ/FORM/ENV recipe stays
  as a second mode. Layout: position tabs + one wide table (the five squeezed columns are gone). RZ, SNP, MKT, 1st columns.
META v2: RZ and SNP boards join the fold; META's row is the all-in score.
Red zone everywhere: Player Board + TD Board (xTD, RZ%, GL+EZ columns, sortable), Matchup Board (xTD, RZ% next to TD λ),
  Player Explorer (summary columns + a chip on the player card), projections (±12% red-zone multiplier, in the tip),
  Insights (red-zone risers / shares / softest end zones).
Rerunnable; guarded by the /* v56 */ marker."""
import re, ast, sys
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v56 */' in s:
    print('v56 already applied'); sys.exit(0)

def rep(old, new, n=1, src=None):
    global s
    t = s if src is None else src
    c = t.count(old)
    assert c == n, f'expected {n} got {c}: {old[:90]!r}'
    t = t.replace(old, new)
    if src is None: s = t
    return t

def rep_first(old, new):
    global s
    i = s.index(old); s = s[:i] + new + s[i+len(old):]

# ---------- shared helpers: one lookup, percentiles within position, cells / chips every board shares ----------
HELP = r"""/* v56 */ /* red zone everywhere: one lookup by name+team (nflverse names normalised), percentiles within this week's slot owners at his position, cells and chips the boards share */
const rzNorm=s=>String(s||'').toLowerCase().replace(/\b(jr|sr|ii|iii|iv|v)\b\.?/g,'').replace(/[^a-z]/g,'');
const RZP=(()=>{const o={l5:{},season:{}};if(!RZ)return o;RZ.players.forEach(r=>{const p=Object.fromEntries(RZ.pcols.map((c,i)=>[c,r[i]]));const k=o[p.scope];if(!k)return;const g=Math.max(1,p.games||0);p.xtdg=p.xtd/g;p.glez=(p.gl_rush+p.ez_tgt)/g;p.rzg=p.rz_opp/g;const n=rzNorm(p.player);k[n+'|'+p.team]=p;if(!k[n])k[n]=p});return o})();
function rzOf(u,scope='l5'){const k=RZP[scope];if(!k||!u)return null;const n=rzNorm(u.ln||u.player);return k[n+'|'+u.team]||k[n]||null}
const RZPCT={};function rzPct(pos,m,v,scope='l5'){if(v==null)return null;const key=pos+'|'+scope;if(!RZPCT[key]){const Q=UNIVERSE.filter(u=>u.pos===pos&&TD_SLOTS.includes(u.dslot||u.slot)&&u.inj!=='-1').map(u=>rzOf(u,scope)).filter(Boolean);RZPCT[key]={};['xtdg','rz_opp_share','glez','snap_pct','rzg'].forEach(c=>RZPCT[key][c]=Q.map(p=>p[c]).filter(x=>x!=null).sort((a,b)=>a-b))}return pctRank(RZPCT[key][m]||[],v)}
const rzDefPct=(()=>{let arr=null;return v=>{if(v==null)return null;if(!arr)arr=RZ?RZ.teams.filter(x=>x[RZT.side]==='def'&&x[RZT.scope]==='season').map(x=>x[RZT.td_rate]).filter(x=>x!=null).sort((a,b)=>a-b):[];return pctRank(arr,v)}})();
/* 0–1 red-zone score: xTD/g .35 · RZ opportunity share .25 · goal-line carries + end-zone targets a game .20 · the opponent's red-zone TD rate allowed .20 */
function rzScore(u,opp,scope='l5'){const p=rzOf(u,scope);if(!p)return null;const a=rzPct(u.pos,'xtdg',p.xtdg,scope);if(a==null)return null;const b=rzPct(u.pos,'rz_opp_share',p.rz_opp_share,scope),g=rzPct(u.pos,'glez',p.glez,scope);let sc=.35*a+.25*(b??a)+.2*(g??a),w=.8;const d=opp?rzTeam('def','season',opp):null;const dd=d?rzDefPct(d.td_rate):null;if(dd!=null){sc+=.2*dd;w+=.2}return sc/w}
/* projection multiplier: his expected-TD rate a game vs his position, ±12% (QBs and sub-2-game samples untouched) */
const rzX=(u,grp)=>{if(grp==='QB'||!RZ||!u)return 1;const p=rzOf(u);if(!p||p.games<2)return 1;const q=rzPct(u.pos,'xtdg',p.xtdg);return q==null?1:1+Math.max(-.12,Math.min(.12,.12*(2*q-1)))};
const rzTip=(p,u)=>`red zone · his team's last ${RZ?RZ.window:5} games: ${p.xtd} expected TD over ${p.games} g (${p.xtdg.toFixed(2)}/g · scored ${p.td}) · ${p.rz_opp} of his team's ${p.team_rz} red-zone plays (${p.rz_opp_share==null?'—':Math.round(100*p.rz_opp_share)+'%'}) · ${p.gl_rush} goal-line carries + ${p.ez_tgt} end-zone targets · ${p.rz_tgt} RZ targets · ${p.rz_rush} RZ carries${p.snap_pct!=null?' · snaps '+Math.round(100*p.snap_pct)+'%':''} · shaded within ${u.pos}s`;
const rzShade=(u,m,v)=>{const q=rzPct(u.pos,m,v);return q==null?'':gradeStyle(1+(1-q)*(NT-1))};
function rzCells(u){if(!RZ)return '';const p=rzOf(u);if(!p)return '<td class="md"><span class="dim">·</span></td>'.repeat(3);const t=esc(rzTip(p,u));
  return `<td class="md" title="${t}"><span class="badge" style="${rzShade(u,'xtdg',p.xtdg)}">${p.xtdg.toFixed(2)}</span></td><td class="md" title="${t}"><span class="badge" style="${rzShade(u,'rz_opp_share',p.rz_opp_share)}">${p.rz_opp_share==null?'—':Math.round(100*p.rz_opp_share)+'%'}</span></td><td class="md" title="${t}"><span class="badge" style="${rzShade(u,'glez',p.glez)}">${p.glez.toFixed(1)}</span></td>`}
const RZ_TH=`<th class="md" data-k="rzx" title="red zone: expected touchdowns a game from where his carries and targets come (league TD rate by yard line) · his team's last 5 games · shaded within his position">xTD</th><th class="md" data-k="rzs" title="red zone: his share of his team's red-zone pass + run plays · last 5 games">RZ%</th><th class="md" data-k="rzg" title="red zone: goal-line carries (5 in) + end-zone targets a game · last 5 games">GL+EZ</th>`;
const rzSort=(u,k)=>{const p=u.rz||rzOf(u);if(!p)return -1;return k==='rzx'?p.xtdg:k==='rzs'?(p.rz_opp_share??-1):p.glez};
function rzChip(u){if(!RZ||!u)return '';const p=rzOf(u);if(!p)return '';return `<span class="rzc" title="${esc(rzTip(p,u))}" style="${rzShade(u,'xtdg',p.xtdg)}">RZ ${p.xtdg.toFixed(2)} xTD · ${p.rz_opp_share==null?'—':Math.round(100*p.rz_opp_share)+'%'} share · ${p.gl_rush+p.ez_tgt} GL+EZ${p.snap_pct!=null?' · snp '+Math.round(100*p.snap_pct)+'%':''}</span>`}
"""
rep("const pctRank=(arr,v)=>{if(v==null||!arr.length)return null;", HELP + "const pctRank=(arr,v)=>{if(v==null||!arr.length)return null;")

# CSS
rep_first("</style>", "/* v56 */ .rzc{display:inline-block;padding:1px 7px;border-radius:9px;font-size:10px;margin-left:4px;white-space:nowrap} .mtone{max-height:72vh;overflow:auto} .mtone table.lgt{width:100%} .mtone th.nw,.mtone td.nw{opacity:.55}\n</style>")

# ---------- projections: red-zone multiplier ----------
rep("  const p=applyW(comp,MODEL);", "  const p0=applyW(comp,MODEL),zR=rzX(u,grp),p=p0*zR;   /* v56: red-zone usage, ±12% */")
rep("const r={p,base,own,n:sw,mR,rawR,sR,eR,rR,floor,ceil,def,o,g,psiV,c,t,prior,env:envP,edge:e,", "const r={p,base,own,n:sw,mR,rawR,sR,eR,rR,zR,floor,ceil,def,o,g,psiV,c,t,prior,env:envP,edge:e,")
rep("× env ${eR.toFixed(2)} × role ${rR.toFixed(2)}`};", "× env ${eR.toFixed(2)} × role ${rR.toFixed(2)} × red zone ${zR.toFixed(2)}`};")

# ---------- Player Board + TD Board: three red-zone columns ----------
rep("snp:ug.snp==null?null:ug.snp,tsh:ug.tsh==null?null:ug.tsh,", "rz:rzOf(u),snp:ug.snp==null?null:ug.snp,tsh:ug.tsh==null?null:ug.tsh,", 2)
rep("else if(sortK==='kick'){x=a.kickord;y=b.kickord}", "else if(sortK==='kick'){x=a.kickord;y=b.kickord}\n      else if(/^rz[xsg]$/.test(sortK)){x=rzSort(a,sortK);y=rzSort(b,sortK)}", 4)
def slice_edit(start_marker, end_marker, fn):
    global s
    a = s.index(start_marker); b = s.index(end_marker, a)
    s = s[:a] + fn(s[a:b]) + s[b:]
def board_cols(seg):
    i = seg.index('const tail=`'); j = seg.index('`;', i)
    seg = seg[:j] + '${RZ_TH}' + seg[j:]
    i = seg.index('const rowTail=u=>`'); j = seg.index('`;\n', i)
    seg = seg[:j] + '${rzCells(u)}' + seg[j:]
    return seg
slice_edit('function lab(){', 'function tdLab(){', board_cols)
slice_edit('function tdLab(){', 'function player(){', board_cols)
rep('<th colspan="4" class="md">model</th>', '<th colspan="${4+(RZ?3:0)}" class="md">model · red zone</th>')
rep('<th colspan="5" class="md">ATD model</th>', '<th colspan="${5+(RZ?3:0)}" class="md">ATD model · red zone</th>')

# ---------- Matchup Board (markets board): xTD + RZ% beside TD λ ----------
rep("${th('td','TD λ','expected rush + receiving touchdowns')}", "${th('td','TD λ','expected rush + receiving touchdowns')}${RZ?th('rzx','xTD','red zone: expected touchdowns a game from where his touches come · last 5 games')+th('rzs','RZ%','his share of his team\\'s red-zone plays · last 5 games'):''}")
rep("<td><b>${r.yds.toFixed(0)}</b></td><td class=\"mini\">${r.pts.toFixed(1)}</td></tr>`).join('')}</tbody></table>",
    "${RZ?(z=>z?`<td title=\"${esc(rzTip(z,r.u))}\"><span class=\"hc\" style=\"${rzShade(r.u,'xtdg',z.xtdg)}\">${z.xtdg.toFixed(2)}</span></td><td class=\"mini\">${z.rz_opp_share==null?'—':Math.round(100*z.rz_opp_share)+'%'}</td>`:'<td class=\"dim\">·</td><td class=\"dim\">·</td>')(rzOf(r.u)):''}<td><b>${r.yds.toFixed(0)}</b></td><td class=\"mini\">${r.pts.toFixed(1)}</td></tr>`).join('')}</tbody></table>")
rep("const V={pts:r=>r.pts,player:r=>r.u.player,team:r=>r.u.team,td:r=>r.lam??-1,match:r=>r.match??99,yds:r=>r.yds};",
    "const V={pts:r=>r.pts,player:r=>r.u.player,team:r=>r.u.team,td:r=>r.lam??-1,match:r=>r.match??99,yds:r=>r.yds,rzx:r=>rzSort(r.u,'rzx'),rzs:r=>rzSort(r.u,'rzs')};")

# ---------- Player Explorer: summary columns + a chip on the card ----------
rep("<th>snap%</th><th>tgt%</th><th title=\"this week's opponent's field for his slot (combined DvP Ψ, 1 = softest)\">opp Ψ</th>",
    "<th>snap%</th><th>tgt%</th><th title=\"red zone: expected touchdowns a game, his team's last 5 games\">xTD</th><th title=\"red zone: his share of his team's red-zone plays, last 5 games\">RZ%</th><th title=\"this week's opponent's field for his slot (combined DvP Ψ, 1 = softest)\">opp Ψ</th>")
rep("<td class=\"mini\">${r.tsh!=null&&p!=='QB'?(100*r.tsh).toFixed(0)+'%':''}</td><td>${(()=>{const o=String(r.o||'').replace('@','');",
    "<td class=\"mini\">${r.tsh!=null&&p!=='QB'?(100*r.tsh).toFixed(0)+'%':''}</td>${(z=>z?`<td title=\"${esc(rzTip(z,r.u))}\"><span class=\"badge\" style=\"${rzShade(r.u,'xtdg',z.xtdg)}\">${z.xtdg.toFixed(2)}</span></td><td class=\"mini\">${z.rz_opp_share==null?'—':Math.round(100*z.rz_opp_share)+'%'}</td>`:'<td class=\"dim\">·</td><td class=\"dim\">·</td>')(rzOf(r.u))}<td>${(()=>{const o=String(r.o||'').replace('@','');")
rep("· μ ${mu.toFixed(1)} ppr · σ ${sd.toFixed(1)}</span></h3>\n        <canvas id=\"pC1\" class=\"chart\"></canvas></div>",
    "· μ ${mu.toFixed(1)} ppr · σ ${sd.toFixed(1)}</span></h3>${(uu=>uu&&rzOf(uu)?`<p class=\"mini\" style=\"margin:0 0 4px\">${rzChip(uu)} <span class=\"dim\">red zone · his team's last ${RZ.window} games · hover</span></p>`:'')(UNIVERSE.find(u=>u.player===n))}\n        <canvas id=\"pC1\" class=\"chart\"></canvas></div>")

# ---------- Insights: red-zone panel ----------
rep("$('#insights').innerHTML=`<div id=\"inSm\"></div><div id=\"inRest\"></div>`;", "$('#insights').innerHTML=`<div id=\"inSm\"></div><div id=\"inRZ\"></div><div id=\"inRest\"></div>`;")
rep("    logoize($('#insights'));sortableAll($('#insights'))}", "    rzInsights();logoize($('#insights'));sortableAll($('#insights'))}")
INS = r"""
/* v56: red-zone takeaways — who the goal-line work runs through, whose red-zone role is growing, and the end zones that give */
function rzInsights(){const el=$('#inRZ');if(!el)return;if(!RZ){el.innerHTML='';return}const wk=G.week;
  const S=UNIVERSE.filter(u=>['RB','WR','TE','QB'].includes(u.pos)&&TD_SLOTS.includes(u.dslot||u.slot)&&u.inj!=='-1'&&inU(u)).map(u=>{const l5=rzOf(u,'l5'),se=rzOf(u,'season');if(!l5)return null;const oppRaw=(J.sched26[u.team]||[])[wk-1]||'',opp=oppRaw&&oppRaw!=='BYE'?oppRaw.replace('@',''):'';
    return {u,l5,se,opp,oppRaw,d:se&&se.games>=4?l5.xtdg-se.xtd/Math.max(1,se.games):null,def:opp?rzTeam('def','season',opp):null}}).filter(Boolean);
  const nm=x=>`<span class="plink" data-p="${esc(x.u.player)}">${esc(pshort(x.u.player))}</span> <span class="mini">${tcell(x.u.team)}${x.opp?' '+oppcell(x.oppRaw):' <span class="dim">bye</span>'}</span>`;
  const row=(x,v)=>`<div class="mlr">${posIcon(x.u.pos,10,x.u.dslot||x.u.slot)} ${nm(x)}${v}</div>`;
  const B=(x,m,v,t)=>`<span class="badge" title="${esc(rzTip(x.l5,x.u))}" style="${rzShade(x.u,m,v)}">${t}</span>`;
  const top=(f,k,n=6)=>S.filter(f).sort(k).slice(0,n);
  const cards=[
    ['goal-line engines · xTD a game','g',top(x=>x.l5.games>=2,(a,b)=>b.l5.xtdg-a.l5.xtdg),x=>B(x,'xtdg',x.l5.xtdg,x.l5.xtdg.toFixed(2))],
    ['red-zone share · who the trips run through','',top(x=>x.l5.rz_opp_share!=null&&x.l5.games>=2,(a,b)=>b.l5.rz_opp_share-a.l5.rz_opp_share),x=>B(x,'rz_opp_share',x.l5.rz_opp_share,Math.round(100*x.l5.rz_opp_share)+'%')],
    ['rising · last 5 vs season','',top(x=>x.d!=null&&x.d>0,(a,b)=>b.d-a.d),x=>`<b class="rise">+${x.d.toFixed(2)}</b><span class="mini"> xTD/g</span>`],
    ['fading · last 5 vs season','r',top(x=>x.d!=null&&x.d<0,(a,b)=>a.d-b.d),x=>`<b class="fall">${x.d.toFixed(2)}</b><span class="mini"> xTD/g</span>`],
    ['softest end zones this week · opponent\'s RZ TD rate allowed','g',top(x=>x.def&&x.def.td_rate!=null&&x.l5.xtdg>=.25,(a,b)=>b.def.td_rate-a.def.td_rate||b.l5.xtdg-a.l5.xtdg),x=>`<b style="color:${gradeColor(1+(1-(rzDefPct(x.def.td_rate)||0))*(NT-1))}">${Math.round(100*x.def.td_rate)}%</b><span class="mini"> ${x.opp} · ${x.l5.xtdg.toFixed(2)} xTD</span>`],
    ['stingiest end zones this week','r',top(x=>x.def&&x.def.td_rate!=null&&x.l5.xtdg>=.25,(a,b)=>a.def.td_rate-b.def.td_rate||b.l5.xtdg-a.l5.xtdg),x=>`<b style="color:${gradeColor(1+(1-(rzDefPct(x.def.td_rate)||0))*(NT-1))}">${Math.round(100*x.def.td_rate)}%</b><span class="mini"> ${x.opp} · ${x.l5.xtdg.toFixed(2)} xTD</span>`]];
  el.innerHTML=`<div class="panel"><h3>red zone <span class="f">this week's slot owners · their team's last ${RZ.window} games · nflverse play-by-play · click a name for his card</span></h3><div class="mlead" data-mg="1">${cards.map(([t,tone,L,val])=>`<div class="mlc ${tone}"><div class="mlh">${t}</div>${L.map(x=>row(x,val(x))).join('')||'<div class="mini dim">nothing on the board</div>'}</div>`).join('')}</div></div>`;
  tWire(el)}
"""
rep("function insights(){", INS.lstrip('\n') + "function insights(){")

# ---------- META: the all-in composite ----------
rep("plus its missing men']];",
    "plus its missing men'],['rz','RZ','red-zone usage: expected TDs a game from where his touches come, his share of his team\\'s red-zone plays, goal-line carries + end-zone targets, and the opponent\\'s red-zone TD rate allowed · percentile within his position'],['snp','SNP','offensive snap share, season to date'],['mkt','MKT','the anytime-TD market: the model\\'s edge over the best posted price, EV %'],['ftd','1st','the First-TD model\\'s chance he scores the game\\'s first touchdown']];")
rep("const MBT=J.metaBT||null;const META_W=MBT&&MBT.weights?MBT.weights:metaWeights();",
    "const MBT=J.metaBT||null;const META_W=MBT&&MBT.weights?MBT.weights:metaWeights();\n/* v56: the all-in recipe — every signal the dash gathers, declared weights (sum 1); the backtest recipe stays as a second mode */\nconst META_ALL={psi:.15,rz:.16,atd:.12,env:.10,td:.09,sch:.08,form:.07,h2h:.07,mkt:.06,snp:.05,ftd:.05};let META_USE=META_ALL;")

a = s.index('function metaGrid('); b = s.index('/* ---------------- v44: META v2', a)
m = s[a:b]
m = rep('<select id="${px}Inj"><option value="x" selected>hide OUT</option><option value="">incl. OUT</option></select>\n    <input id="${px}Q" placeholder="search player..." size="15">${MBT?',
        '<select id="${px}Mode" title="which recipe folds the columns into META"><option value="all" selected>META: all-in — every signal</option><option value="bt">META: backtest recipe — Ψ · FORM · ENV</option></select>\n    <select id="${px}Inj"><option value="x" selected>hide OUT</option><option value="">incl. OUT</option></select>\n    <input id="${px}Q" placeholder="search player..." size="15">${MBT?', 1, m)
# note + layout
i = m.index('<span class="note">every board at once.'); j = m.index('<div class="lgrid td5 wide full meta">', i); k = m.index('</div>`;', j) + 8
NOTE = ('<span class="note"><b>META</b> = one score, 0–100 (100 = the softest spot), folding <b>every</b> signal the dash gathers for the player: '
        '<b>Ψ</b> the opponent\'s field for his slot · <b>RZ</b> his red-zone usage (xTD a game, share of his team\'s red-zone plays, goal-line + end-zone looks, the opponent\'s red-zone TD rate) · <b>ATD</b> the anytime-TD model · <b>ENV</b> his team\'s implied points · <b>TD</b> touchdowns the opponent allows his slot · <b>SCH</b> scheme edge + the opponent\'s missing men · <b>FORM</b> his last two games vs his season · <b>H2H</b> his history against them · <b>MKT</b> the market\'s edge · <b>SNP</b> snap share · <b>1st</b> first-TD chance. '
        'Recipe: ${Object.entries(META_ALL).map(([k,v])=>LBL[k]+\' \'+Math.round(100*v)+\'%\').join(\' · \')} — each signal becomes a percentile within his position among this week\'s slot owners, the score is shaded toward 50 when signals split or data is missing, and a questionable tag pulls it 15% toward 50. '
        '${MBT?`The walk-forward backtest\'s own recipe (Ψ ${Math.round(100*(META_W.psi||0))}% · FORM ${Math.round(100*(META_W.form||0))}% · ENV ${Math.round(100*(META_W.env||0))}%, rho ${MBT.chosen_oos.rho} out of sample) is the second mode in the select.`:\'\'} '
        'Hover any META cell for the full breakdown · lens chips re-rank the table · a header click re-sorts one column · click a name for his card</span>\n  </div>\n'
        '  <div class="mlead" id="${px}Lead" data-mg="1"></div>\n'
        '  <div class="controls"><span class="chips" id="${px}Pos" title="which position the table shows"><button data-p="ALL" class="on">◉ all</button>${TPOS.map(p=>`<button data-p="${p}">${posIcon(p,11)} ${p}</button>`).join(\'\')}</span></div>\n'
        '  <div class="panel"><h3 id="${px}H">◉ all <span class="gl" id="${px}GALL"></span> <span class="f" id="${px}NALL"></span></h3><div id="${px}BALL" class="mtone"></div></div>`;')
m = m[:i] + NOTE + m[k:]
m = rep("DESC=new Set(['meta','atd','h2h','sch','env','form'])", "DESC=new Set(['meta','atd','h2h','sch','env','form','rz','snp','mkt','ftd'])", 1, m)
m = rep("const SIGS=['meta','env','td','atd','psi','form','h2h','sch'],SIGW={meta:9,env:7,td:8,atd:8,psi:7,form:7,h2h:11,sch:8},sigs=()=>SIGS.filter(k=>HAS[k]);",
        "const SIGS=['meta','psi','rz','atd','env','td','sch','form','h2h','mkt','snp','ftd'],SIGW={meta:8,psi:6,rz:8,atd:7,env:7,td:6,sch:7,form:7,h2h:10,mkt:7,snp:6,ftd:6},sigs=()=>SIGS.filter(k=>HAS[k]);let posTab='ALL';", 1, m)
m = rep("const T=((J.betting||{}).td||[]).filter(r=>+r.week===wk);",
        "const T=((J.betting||{}).td||[]).filter(r=>+r.week===wk);META_USE=$$('Mode').value==='bt'?META_W:META_ALL;const FT=(J.firstTd&&J.firstTd.week===wk?J.firstTd.board:[])||[];", 1, m)
m = rep("const t=tdOf(u),atd=t&&t.p_model!=null&&t.p_model!==''?+t.p_model:null;",
        "const t=tdOf(u),atd=t&&t.p_model!=null&&t.p_model!==''?+t.p_model:null;const rzp=rzOf(u),ft=FT.find(r=>r.player===u.player&&r.team===u.team)||FT.find(r=>r.player===u.player),snpv=(USG[u.ln||u.player]||{}).snp;", 1, m)
m = rep("pool:TD_SLOTS.includes(u.dslot||u.slot)}});\n    /* percentiles come from this week's slot owners only",
        "rzp,rzs:opp?rzScore(u,opp):null,snp:snpv==null?null:+snpv,mkt:t&&t.ev!=null&&t.ev!==''&&t.price!=null?+t.ev:null,ftd:ft&&ft.p_first!=null?+ft.p_first:null,\n        pool:TD_SLOTS.includes(u.dslot||u.slot)}});\n    /* percentiles come from this week's slot owners only", 1, m)
m = rep("const W=Object.values(META_W).reduce((a,b)=>a+b,0);\n    R.forEach(x=>{const c={psi",
        "const pR={},pN={},pM={},pFt={};TPOS.forEach(p=>{const Q=P.filter(x=>x.pos===p);pR[p]=pct(Q.map(x=>x.rzs));pN[p]=pct(Q.map(x=>x.snp));pM[p]=pct(Q.map(x=>x.mkt));pFt[p]=pct(Q.map(x=>x.ftd))});\n    const W=Object.values(META_USE).reduce((a,b)=>a+b,0);\n    R.forEach(x=>{const c={rz:pR[x.pos](x.rzs),snp:pN[x.pos](x.snp),mkt:pM[x.pos](x.mkt),ftd:pFt[x.pos](x.ftd),psi", 1, m)
m = rep("Object.entries(META_W).forEach(([k,wt])=>{if(wt>0&&c[k]!=null)", "Object.entries(META_USE).forEach(([k,wt])=>{if(wt>0&&c[k]!=null)", 1, m)
m = rep("x.meta=w&&x.opp?50+(100*s/w-50)*(META_CFG.cov?(.6+.4*w/W):1)*(META_CFG.agree?(.75+.25*agree):1):null});",
        "x.meta=w&&x.opp?50+(100*s/w-50)*(META_CFG.cov?(.6+.4*w/W):1)*(META_CFG.agree?(.75+.25*agree):1):null;if(x.meta!=null&&x.u.inj==='0')x.meta=50+(x.meta-50)*.85});", 1, m)
m = rep("env:R.some(x=>x.env!=null),form:R.some(x=>x.form!=null)};",
        "env:R.some(x=>x.env!=null),form:R.some(x=>x.form!=null),rz:R.some(x=>x.rzs!=null),snp:R.some(x=>x.snp!=null),mkt:R.some(x=>x.mkt!=null),ftd:R.some(x=>x.ftd!=null)};", 1, m)
m = rep("k==='sch'?x.sch:k==='player'?x.u.player:k==='opp'?(x.opp||null):k==='pos'?TPOS.indexOf(x.pos):null;",
        "k==='sch'?x.sch:k==='rz'?x.rzs:k==='snp'?x.snp:k==='mkt'?x.mkt:k==='ftd'?x.ftd:k==='player'?x.u.player:k==='opp'?(x.opp||null):k==='pos'?TPOS.indexOf(x.pos):null;", 1, m)
# why(): weights shown from META_USE + the new lines
m = m.replace("(weight ${META_W.env||0})", "(weight ${META_USE.env||0})").replace("(weight ${META_W.form||0})", "(weight ${META_USE.form||0})")
for k in ('psi', 'td', 'sch', 'h2h'):
    m = rep("(weight ${META_W.%s})" % k, "(weight ${META_USE.%s||0})" % k, 1, m)
m = rep("`ATD ${x.atd==null?'no model':Math.round(100*x.atd)+'%'} → ${x.c.atd==null?'—':Math.round(100*x.c.atd)} (weight ${META_W.atd})`].join('\\n');",
        "`ATD ${x.atd==null?'no model':Math.round(100*x.atd)+'%'} → ${x.c.atd==null?'—':Math.round(100*x.c.atd)} (weight ${META_USE.atd||0})`,\n"
        "    `RZ ${x.rzp?x.rzp.xtdg.toFixed(2)+' xTD/g · '+(x.rzp.rz_opp_share==null?'—':Math.round(100*x.rzp.rz_opp_share)+'%')+' of team RZ plays · '+(x.rzp.gl_rush+x.rzp.ez_tgt)+' GL+EZ looks'+(x.opp&&rzTeam('def','season',x.opp)&&rzTeam('def','season',x.opp).td_rate!=null?' · '+x.opp+' allows a TD on '+Math.round(100*rzTeam('def','season',x.opp).td_rate)+'% of RZ trips':''):'no red-zone data'} → ${x.c.rz==null?'—':Math.round(100*x.c.rz)} (weight ${META_USE.rz||0})`,\n"
        "    `SNP ${x.snp==null?'—':Math.round(100*x.snp)+'% of snaps'} → ${x.c.snp==null?'—':Math.round(100*x.c.snp)} (weight ${META_USE.snp||0})`,\n"
        "    `MKT ${x.mkt==null?'no price':'EV '+(x.mkt>=0?'+':'')+x.mkt.toFixed(1)+'% vs best ATD price'} → ${x.c.mkt==null?'—':Math.round(100*x.c.mkt)} (weight ${META_USE.mkt||0})`,\n"
        "    `1st ${x.ftd==null?'—':(100*x.ftd).toFixed(1)+'% to score first'} → ${x.c.ftd==null?'—':Math.round(100*x.c.ftd)} (weight ${META_USE.ftd||0})`+(x.u.inj==='0'?'\\nquestionable: pulled 15% toward 50':'')].join('\\n');", 1, m)
# cells
m = rep("const o={meta,env,td,atd,psi,form,h2h,sch};return sigs().map(k=>o[k]).join('')};",
        "const pb=(k,v,txt,tip)=>v==null?'<td class=\"md\"><span class=\"dim\">·</span></td>':`<td class=\"md\" title=\"${esc(tip)}\"><span class=\"badge\" style=\"${x.c[k]==null?'':gradeStyle(eq(x.c[k]))}\">${txt}</span></td>`;\n"
        "    const rz=pb('rz',x.rzs,x.rzp?x.rzp.xtdg.toFixed(2):'·',x.rzp?rzTip(x.rzp,x.u)+(x.opp&&rzTeam('def','season',x.opp)&&rzTeam('def','season',x.opp).td_rate!=null?` · ${x.opp} allows a TD on ${Math.round(100*rzTeam('def','season',x.opp).td_rate)}% of red-zone trips`:'')+' · score '+Math.round(100*(x.c.rz||0)):'');\n"
        "    const snp=pb('snp',x.snp,x.snp==null?'·':Math.round(100*x.snp)+'%',`${Math.round(100*(x.snp||0))}% of his team's offensive snaps · shaded within ${x.pos}s`);\n"
        "    const mkt=pb('mkt',x.mkt,x.mkt==null?'·':(x.mkt>=0?'+':'')+x.mkt.toFixed(0)+'%',`anytime-TD market: EV ${(x.mkt||0)>=0?'+':''}${(x.mkt||0).toFixed(1)}% vs the best posted price${x.t&&x.t.price!=null?' '+mlTxt(+x.t.price)+(x.t.book?' ('+x.t.book+')':''):''} · shaded within ${x.pos}s`);\n"
        "    const ftd=pb('ftd',x.ftd,x.ftd==null?'·':(100*x.ftd).toFixed(1)+'%',`First-TD model: ${(100*(x.ftd||0)).toFixed(1)}% to score the game's first touchdown · shaded within ${x.pos}s`);\n"
        "    const o={meta,env,td,atd,psi,form,h2h,sch,rz,snp,mkt,ftd};return sigs().map(k=>o[k]).join('')};", 1, m)
m = rep("const nw=k=>SIGS.includes(k)&&k!=='meta'&&!(META_W[k]>0);", "const nw=k=>SIGS.includes(k)&&k!=='meta'&&!(META_USE[k]>0);", 1, m)
m = rep("(nw(k)?' · no weight in META (the backtest found it adds nothing once Ψ is in) — shown for the read':'')", "(nw(k)?' · no weight in this META recipe — shown for the read':'')", 1, m)
m = rep("sch:th('sch','SCH','what the opponent\\'s defensive style gives up to his slot vs league, % · plus 0.6 × the lift from its missing men','md')};",
        "sch:th('sch','SCH','what the opponent\\'s defensive style gives up to his slot vs league, % · plus 0.6 × the lift from its missing men','md'),\n"
        "      rz:th('rz','RZ','red-zone usage: xTD a game (shown) · share of his team\\'s red-zone plays · goal-line + end-zone looks · the opponent\\'s red-zone TD rate allowed · shaded by the blended percentile within his position','md'),\n"
        "      snp:th('snp','SNP','offensive snap share, season to date · shaded within his position','md'),mkt:th('mkt','MKT','anytime-TD market: model EV vs the best posted price · shaded within his position','md'),\n"
        "      ftd:th('ftd','1st','First-TD model: chance he scores the game\\'s first touchdown · shaded within his position','md')};", 1, m)
# one table: every container is the ALL slot, the tab decides the rows
m = m.replace("$$('N'+p).textContent", "$$('NALL').textContent").replace("$$('G'+p).textContent", "$$('GALL').textContent").replace("$$('B'+p)", "$$('BALL')")
m = rep("$$('GALL').textContent=`ranked by ${LBL[st.k]||st.k} · ${setL()}`;", "$$('GALL').textContent=`ranked by ${LBL[st.k]||st.k} · ${setL()} · ${$$('Mode').value==='bt'?'backtest recipe':'all-in recipe'}`;$$('H').firstChild.textContent=(p==='ALL'?'◉ all':p)+' ';", 1, m)
m = rep("    const sec=$$('BALL').closest('.lgcol'),h=sec&&sec.querySelector('h3');if(h)sec.style.setProperty('--h3h',h.offsetHeight+'px');\n", "", 1, m)
m = rep("const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead()};", "const cols=()=>{col(posTab);lead()};", 1, m)
m = rep("Object.keys(sort).forEach(p=>sort[p]={k:lens,a:!DESC.has(lens)});['ALL'].concat(TPOS).forEach(col)});",
        "Object.keys(sort).forEach(p=>sort[p]={k:lens,a:!DESC.has(lens)});cols()});\n"
        "  $$('Pos').querySelectorAll('button').forEach(b=>b.onclick=()=>{posTab=b.dataset.p;$$('Pos').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));col(posTab)});", 1, m)
m = rep("['Src','QB','Se','Inj'].forEach(i=>$$(i).onchange=all);", "['Src','QB','Se','Inj','Mode'].forEach(i=>$$(i).onchange=all);", 1, m)
m = rep("if(c.h2h!=null&&c.h2h>=.65&&x.n>0)r.push(['H2H',x.hp.toFixed(1)+' ppr',c.h2h]);",
        "if(c.h2h!=null&&c.h2h>=.65&&x.n>0)r.push(['H2H',x.hp.toFixed(1)+' ppr',c.h2h]);if(c.rz!=null&&c.rz>=.65&&x.rzp)r.push(['RZ',x.rzp.xtdg.toFixed(2)+' xTD',c.rz]);if(c.mkt!=null&&c.mkt>=.65)r.push(['MKT','EV '+(x.mkt>=0?'+':'')+x.mkt.toFixed(0)+'%',c.mkt]);", 1, m)
m = rep("['SCH',c.sch,x.sch==null?'':(x.sch>=0?'+':'')+Math.round(x.sch)]].forEach(([l,v,t])=>{if(v!=null&&v<=.35)r.push([l,t,v])});",
        "['SCH',c.sch,x.sch==null?'':(x.sch>=0?'+':'')+Math.round(x.sch)],['RZ',c.rz,x.rzp?x.rzp.xtdg.toFixed(2)+' xTD':''],['SNP',c.snp,x.snp==null?'':Math.round(100*x.snp)+'%']].forEach(([l,v,t])=>{if(v!=null&&v<=.35)r.push([l,t,v])});", 1, m)
m = rep("['scheme edge','',top(null,'sch',false),x=>`<b style=\"color:${schC(x.sch)}\">${x.sch>=0?'+':''}${Math.round(x.sch)}</b>`],",
        "['scheme edge','',top(null,'sch',false),x=>`<b style=\"color:${schC(x.sch)}\">${x.sch>=0?'+':''}${Math.round(x.sch)}</b>`],\n"
        "      ['red zone · RZ','',top(x=>!!x.rzp,'rz',false),x=>B(x.rzp.xtdg.toFixed(2)+' xTD',x.c.rz==null?'':gradeStyle(eq(x.c.rz)))],\n"
        "      ['market edge · MKT','',top(null,'mkt',false),x=>B('EV '+(x.mkt>=0?'+':'')+x.mkt.toFixed(0)+'%',x.c.mkt==null?'':gradeStyle(eq(x.c.mkt)))],", 1, m)
m = rep("].filter((c,i)=>HAS[['meta','env','td','atd','psi','h2h','sch','meta'][i]]);", "].filter((c,i)=>HAS[['meta','env','td','atd','psi','h2h','sch','rz','mkt','meta'][i]]);", 1, m)
s = s[:a] + m + s[b:]

# ---------- META v2: RZ + SNP boards join the fold; META's row is the all-in score ----------
rep("  ['meta','META','META v1: Ψ + FORM + ENV, the backtested recipe',false],",
    "  ['meta','META','META: the all-in composite — every signal the dash gathers, declared weights',false],\n  ['rz','RZ','TD Usage: red-zone score — xTD a game, share of his team\\'s red-zone plays, goal-line + end-zone looks, the opponent\\'s red-zone TD rate allowed',false],\n  ['snp','SNP','offensive snap share, season to date',false],")
rep("env:m1&&m1.env!=null?m1.env:null,form:m1&&m1.form!=null?m1.form:null,sch:", "env:m1&&m1.env!=null?m1.env:null,form:m1&&m1.form!=null?m1.form:null,rz:m1&&m1.rzs!=null?m1.rzs:null,snp:m1&&m1.snp!=null?m1.snp:null,sch:")
rep("case 'mkt':return (v>=0?'+':'')+(+v).toFixed(0)+'%';default:return String(v)}};", "case 'mkt':return (v>=0?'+':'')+(+v).toFixed(0)+'%';case 'rz':return String(Math.round(100*v));case 'snp':return Math.round(100*v)+'%';default:return String(v)}};")
rep("const rawTxt=(k,x)=>{const v=x.raw[k];if(v==null)return '—';switch(k){", "const rawTxt=(k,x)=>{const v=x.raw[k];if(v==null)return '—';switch(k){case 'rz':return `red-zone score ${Math.round(100*v)} of 100`;case 'snp':return `${Math.round(100*v)}% of his team's offensive snaps`;")

# INTRO / notes
rep_first("Object.assign(NOTES,{", "Object.assign(NOTES,{v56:['META rebuilt: one all-in score folding Ψ, red-zone usage, the anytime-TD model, implied points, TD allowed, scheme, form, H2H, the market, snaps and first-TD chance — declared weights, the backtest recipe kept as a second mode; one wide table with position tabs instead of five squeezed columns','META v2: red-zone and snap-share boards join the fold','Red zone everywhere: Player Board, TD Board, Matchup Board, Player Explorer, projections (±12% multiplier) and Insights all read the nflverse red-zone layer'],")

# ---------- INTRO strips + one-table column widths ----------
rep(" meta:{what:'Every board at once.',how:['META = one score, 0–100 — 100 = the softest spot; its recipe is what the walk-forward backtest picked (Ψ 56% · FORM 34% · ENV 10% — the other columns are reads, not weights) · hover a META cell for the breakdown, the backtest chip for the audit',",
    " meta:{what:'Every signal, one score.',how:['META = one score, 0–100 (100 = the softest spot) folding EVERY signal the dash gathers for him: Ψ · red zone · the anytime-TD model · implied points · TD allowed · scheme + missing men · form · H2H · the market · snaps · first-TD chance — declared weights (Ψ 15 · RZ 16 · ATD 12 · ENV 10 · TD 9 · SCH 8 · FORM 7 · H2H 7 · MKT 6 · SNP 5 · 1st 5), each a percentile within his position; the backtest\\'s Ψ/FORM/ENV recipe is the second mode · hover a META cell for the breakdown',")
rep("TD and Ψ = the opponent\\'s rank of 32, 1 = allows the most · ATD = the model\\'s chance he scores · H2H = his own PPR vs this opponent, ▲ / ▼ vs his norm · SCH = the defense\\'s style edge for his slot','lens chips re-rank every column at once; the data-set select (2024 · 2025 · 2026 · combined · adjusted · μ) drives TD, Ψ and META']},",
    "TD and Ψ = the opponent\\'s rank of 32, 1 = allows the most · ATD = the model\\'s chance he scores · RZ = his red-zone usage (xTD a game shown; share, goal-line + end-zone looks and the opponent\\'s red-zone TD rate in the shade) · H2H = his own PPR vs this opponent, ▲ / ▼ vs his norm · SCH = the defense\\'s style edge for his slot · MKT = EV vs the best anytime-TD price · SNP = snap share · 1st = first-TD chance','position tabs pick the table; lens chips re-rank it; the data-set select (2024 · 2025 · 2026 · combined · adjusted · μ) drives TD, Ψ and META']},")
rep("TD Grid, Player Board Ψ, H2H, TD Picks, First TD, Weeklies, categories, META, ENV, FORM, scheme, market edge · position tabs", "TD Grid, Player Board Ψ, H2H, TD Picks, First TD, Weeklies, categories, META (all-in), red zone, snaps, ENV, FORM, scheme, market edge · position tabs")
a = s.index('function metaGrid('); b = s.index('/* ---------------- v44: META v2', a); m = s[a:b]
m = rep("const S=sigs(),wname=p==='ALL'?24:29,wpos=p==='ALL'?5:0,wopp=p==='ALL'?15:18,", "const S=sigs(),wname=13,wpos=p==='ALL'?4:0,wopp=8,", 1, m)
s = s[:a] + m + s[b:]

rep("desc:'every board at once: the TD Board, Player Grid, H2H Grid, Scheme and the anytime-TD model folded into one score per starter, in the TD Grid\\'s five columns \\u2014 every position together, then QB, RB, WR and TE \\u2014 with the week\\'s best spot on each signal across the top'",
    "desc:'every signal, one score: the opponent\\'s field (Ψ, TD allowed, scheme + missing men), his red-zone usage, the anytime-TD and first-TD models, implied points, form, H2H, snaps and the market folded into one 0\\u2013100 per starter with declared weights \\u2014 one table with position tabs, the week\\'s best spot on each signal across the top'")

open(P, 'w', encoding='utf-8').write(s)
print('v56 applied')
