"""v66 — tested plays at the top of the existing META tab (no new tab): the one mixture of signals the ledger backtest supports
(last-10 over-rate + defense allowed agree; tier A adds the projection), its record, and this week's qualifying lines.
Data: scripts/build_mix_backtest.py -> data/processed/mix_backtest.json. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:100])
    s = s.replace(old, new)
if '/* v66 */' not in s:
    rep('<div id="meta" hidden>', '<div id="mixplays" hidden></div><div id="meta" hidden>')
    rep("'metaprop2','dev','backtest'].forEach(k=>{const e=$('#'+k);if(e)e.hidden=k!==it.sub})", "'metaprop2','dev','backtest'].forEach(k=>{const e=$('#'+k);if(e)e.hidden=k!==it.sub});{const mp=$('#mixplays');if(mp)mp.hidden=it.sub!=='meta'}")
    rep("['test',qbTargetsView],", "['test',qbTargetsView],['test',mixPlaysView],")
    rep("</style>", """/* v66 */#mixplays{margin-bottom:12px}table.mixt{width:100%;border-collapse:collapse}table.mixt th{font-size:11px;color:var(--dim);text-align:left;padding:4px 8px;cursor:pointer}table.mixt td{padding:5px 8px;border-bottom:1px solid var(--edge);text-align:left}table.mixt td.n{text-align:left}table.mixt tr[data-th]{cursor:pointer}table.mixt tr[data-th]:hover td{background:rgba(255,255,255,.03)}
.mixA{display:inline-block;min-width:20px;text-align:center;font:700 11px/1.6 var(--mono);border-radius:3px;background:#e8b100;color:#000}.mixB{display:inline-block;min-width:20px;text-align:center;font:700 11px/1.6 var(--mono);border-radius:3px;background:var(--edge2);color:var(--txt)}
</style>""")
    VIEW = r"""
/* ---------- v66: tested plays — the mixture of signals the ledger backtest supports, at the top of META ---------- */
/* v66 */function mixPlaysView(){const el=$('#mixplays');if(!el)return;const M=J.mix;if(!M||!M.rules||!M.current){el.innerHTML='';return}
  const MKL={pass_yds:'pass yds',pass_td:'pass TD',pass_att:'pass att',completions:'completions',interceptions:'INT',rush_yds:'rush yds',rush_att:'carries',receptions:'receptions',rec_yds:'rec yds',rush_rec_yds:'rush + rec yds',pass_rush_yds:'pass + rush yds'};
  const MKF={pass_yds:l=>l[LOG.py],pass_td:l=>l[LOG.ptd],pass_att:l=>l[LOG.patt],completions:l=>l[28]||0,interceptions:l=>l[LOG.int],rush_yds:l=>l[LOG.ry],rush_att:l=>l[LOG.ra],receptions:l=>l[LOG.rec],rec_yds:l=>l[LOG.recy],rush_rec_yds:l=>l[LOG.ry]+l[LOG.recy],pass_rush_yds:l=>l[LOG.py]+l[LOG.ry]};
  const SIGL={mdl:'prop model',edge:'model vs market',projgap:'projection vs line',l10:'last-10 over-rate',l5:'last-5 over-rate',avg:'season average vs line',l3:'last-3 average vs line',h2h:'head to head',dvp:'defense, season',dvp3:'defense, last 3',dvp5:'defense, last 5',env:'implied points',home:'home / away'};
  const nk=n=>String(n).toLowerCase().replace(/\./g,' ').replace(/\b(jr|sr|ii|iii|iv|v)\b/g,'').replace(/[^a-z]/g,'');
  const rec=r=>`${r.w}-${r.n-r.w}`,pc=v=>v==null?'—':(100*v).toFixed(1)+'%',un=v=>(v>=0?'+':'')+v.toFixed(1)+'u';
  const A=M.rules.A,B=M.rules.B,WF=M.walk_forward_total.top1;
  const wkPop=()=>({title:'the rule, week by week',sub:'tier A = projection + last-10 + defense agree · tier B = last-10 + defense agree · units at the best posted price · break-even at -110 is 52.4%',sections:[
    {h:'chosen on earlier weeks only, then bet the next week — the honest estimate',cols:[{l:'week',g:false},{l:'combination picked',g:false},{l:'record',g:false},'hit','units'],rows:M.walk_forward.map(r=>['wk '+r.week,r.signals.map(x=>SIGL[x]||x).join(' + '),rec(r),r.hit==null?'—':{v:r.hit,h:pc(r.hit)},{v:r.units,h:un(r.units)}])},
    {h:'the fixed rule, week by week (fitted to all weeks, so it flatters itself)',cols:[{l:'week',g:false},{l:'tier A',g:false},'A hit','A units',{l:'tier B',g:false},'B hit','B units'],rows:Object.keys(B.by_week).map(w=>{const a=A.by_week[w],b=B.by_week[w];return ['wk '+w,a.n?rec(a):'—',a.hit==null?'—':{v:a.hit,h:pc(a.hit)},{v:a.units,h:un(a.units)},b.n?rec(b):'—',b.hit==null?'—':{v:b.hit,h:pc(b.hit)},{v:b.units,h:un(b.units)}]})},
    {h:'every signal on its own · every graded line since week 4',cols:[{l:'signal',g:false},{l:'bets',g:false},'hit','units',{l:'weeks up',g:false}],rows:Object.entries(M.single).map(([k,r])=>[SIGL[k]||k,r.n,{v:r.hit,h:pc(r.hit)},{v:r.units,h:un(r.units)},r.weeks_up+' / '+M.weeks.length])}]});
  const rowPop=p=>()=>{const k=nk(p.player),f=MKF[p.market],d=p.opp.replace('@',''),g=SLOTG(p.slot);
    const gs=J.logs.filter(l=>nk(l[LOG.player])===k&&(l[LOG.season]<LAST_SE||l[LOG.week]<M.current.week)).sort((a,b)=>b[LOG.season]-a[LOG.season]||b[LOG.week]-a[LOG.week]).slice(0,10);
    return {title:`${esc(p.player)} · ${p.side} ${p.line} ${MKL[p.market]||p.market}`,sub:`${p.team} ${p.opp.startsWith('@')?'at':'vs'} ${d} · over in ${p.l10k} of his last ${p.l10n} · ${d} allows ${p.allowed} a game to the ${g} (league ${p.league})${p.proj!=null?' · projection '+p.proj:''}`,
      sections:[{h:`his last ${gs.length} games against this line`,cols:[{l:'season',g:false},{l:'wk',g:false},{l:'opp',g:false},MKL[p.market]||p.market,{l:'vs '+p.line,g:false}],rows:gs.map(l=>{const v=f(l);return [l[LOG.season],l[LOG.week],tcell(l[LOG.opp]),{v,h:String(v)},v>p.line?'<b class="rise">over</b>':v<p.line?'<b class="fall">under</b>':'push']})},{h:`${d} against the ${g}, game by game`,html:defLogTable(d,g,[LAST_SE])}]}};
  function render(){const C=M.current,live=G.week===C.week;
    const kp=(k,v,s2,tone='')=>`<div class="kpi ${tone}"><span class="k">${k}</span><b class="v">${v}</b><span class="s">${s2||''}</span></div>`;
    const tiles=thSeq(`<div class="kpis">${kp('picked blind, bet next week',pc(WF.w/Math.max(1,WF.n)),`${WF.w}-${WF.n-WF.w} · ${un(WF.units)} · the honest number`,'g')}${kp('tier A · fitted',pc(A.hit),`${rec(A)} · ${un(A.units)} · projection + last 10 + defense`)}${kp('tier B · fitted',pc(B.hit),`${rec(B)} · ${un(B.units)} · last 10 + defense`)}${kp('tier B at Kalshi prices',pc(B.kalshi.hit),`${B.kalshi.w}-${B.kalshi.n-B.kalshi.w} · ${un(B.kalshi.units)}`)}${kp('break-even','52.4%',`at -110 · the prop model alone hits ${pc(M.single.mdl.hit)}`)}</div>`,[wkPop,wkPop,wkPop,wkPop,wkPop]);
    const P=live?C.plays.filter(p=>inF(p.team)&&inP(posOf(p.slot))):[];
    const l10=p=>{const r=p.l10n?p.l10k/p.l10n:.5,t=p.side==='OVER'?r:1-r;return `<span class="badge" style="${gradeStyle(1+(1-t)*(NT-1))}">${p.l10k} / ${p.l10n} over</span>`};
    const dv=p=>{if(p.dvp==null)return '—';const t=Math.max(0,Math.min(1,.5+(p.side==='OVER'?p.dvp:-p.dvp)));return `<span class="badge" style="${gradeStyle(1+(1-t)*(NT-1))}">${p.allowed}</span> <span class="mini dim">lg ${p.league} · ${p.dvp>=0?'+':''}${Math.round(100*p.dvp)}%${p.dvp3_agrees?' · last 3 ✓':''}</span>`};
    const tbl=!live?`<p class="note mini">the plays are built for the live week (week ${C.week}) — pick it up top to see them</p>`:!P.length?'<p class="note mini">no line qualifies in this filter</p>'
      :`<table class="mixt"><thead><tr><th title="A = projection, last 10 and defense all agree · B = last 10 and defense agree">tier</th><th>player</th><th>opp</th><th>play</th><th title="how often he went over this exact line in his last 10 games">last 10</th><th title="what this defense allows his slot in this stat per game · league average · last 3 ✓ = its last three games say the same">defense allows</th><th title="the prop model's median">proj</th><th title="best price at the last pull — check it before you bet">price</th></tr></thead><tbody>
        ${P.map(p=>`<tr data-th="${thReg(rowPop(p))}"><td data-v="${p.tier==='A'?2:1}"><span class="mix${p.tier}">${p.tier}</span></td><td>${pn(p.player,p.team)}</td><td>${tcell(p.opp.replace('@',''))}</td><td data-v="${p.side==='OVER'?1:0}"><b class="${p.side==='OVER'?'rise':'fall'}">${p.side}</b> <b>${p.line}</b> <span class="mini dim">${MKL[p.market]||p.market}</span></td><td data-v="${p.l10n?p.l10k/p.l10n:.5}">${l10(p)}</td><td data-v="${p.dvp??''}">${dv(p)}</td><td class="n" data-v="${p.proj??''}">${p.proj??'—'}</td><td data-v="${p.price??''}">${p.price==null?'—':mlTxt(p.price)} <span class="mini dim">${esc(p.book||'')}</span></td></tr>`).join('')}</tbody></table>`;
    el.innerHTML=`<div class="panel"><h3>tested plays${live?' · week '+C.week+' · '+P.length:''}</h3><p class="mini dim" style="margin:0 0 8px">every signal on the dash was graded against ${M.n.toLocaleString()} settled lines, alone and in every combination. One mix holds up: <b style="color:var(--txt)">he has cleared (or missed) this exact line in 7+ of his last 10, and the defense allows his slot 10%+ more (or less) than the league in that stat</b>. Tier A adds the projection on the same side. Eight weeks of data — a lead, not a law. Click a tile for the weeks, a row for the games.</p>${tiles}${tbl}</div>`;
    logoize(el);sortableAll(el)}
  render();RR.push(render)}

"""
    rep("function qbTargetsView(){const el=$('#qbtargets');if(!el)return;", VIEW + "function qbTargetsView(){const el=$('#qbtargets');if(!el)return;")
    open(P, 'w', encoding='utf-8').write(s); print('template: v66 applied')
else: print('template already v66')
B = 'scripts/build_dashboard.py'; b = open(B, encoding='utf-8').read()
if "data['mix']" not in b:
    anchor = "    data['qbTargets'] = "; i = b.index(anchor)
    add = ("    if os.path.exists('data/processed/mix_backtest.json'):   # v66: the mixture backtest (rule record + this week's plays)\n"
           "        _mx = json.load(open('data/processed/mix_backtest.json', encoding='utf-8'))\n"
           "        data['mix'] = {k: _mx.get(k) for k in ('built', 'n', 'weeks', 'single', 'rules', 'walk_forward', 'walk_forward_total', 'current')}\n")
    b = b[:i] + add + b[i:]; open(B, 'w', encoding='utf-8').write(b); print('build_dashboard: mix payload')
R = 'scripts/refresh.py'; r = open(R, encoding='utf-8').read()
if 'build_mix_backtest' not in r:
    old = "for _s in ('scripts/build_qb_targets.py', 'scripts/build_categories.py'):"
    assert r.count(old) == 1; r = r.replace(old, "for _s in ('scripts/build_qb_targets.py', 'scripts/build_categories.py', 'scripts/build_mix_backtest.py'):"); open(R, 'w', encoding='utf-8').write(r); print('refresh: mix backtest wired')
