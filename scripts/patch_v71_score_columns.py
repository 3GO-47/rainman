"""v71 — Player Grid: his red-zone share, his last-5 trend and a fitted SCORE sit in every row, with a $ chip when a contract
incentive is still in play. Data: scripts/build_player_score.py -> data/processed/player_score.json (J.pscore).
Also: the live week gets defense ranks in build_categories (the opponent categories were empty for the week in progress),
refresh.py runs the score builder, build_dashboard embeds it. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:110])
    s = s.replace(old, new)
if '/* v71 */' not in s:
    rep("function labGrid(){const lgLive=new Set(TD_SLOTS);",
        r"""/* v71 */const PSC=(J.pscore&&J.pscore.players)||{};const psKey=n=>String(n||'').toLowerCase().replace(/ jr/g,'').replace(/ sr/g,'').replace(/ iii/g,'').replace(/ ii/g,'').replace(/[^a-z]/g,'');
const psOf=u=>PSC[psKey(u.player)]||PSC[psKey(u.ln)]||null;
const psPct=v=>v==null?'—':Math.round(100*v)+'%';
function psPop(u){const p=psOf(u);if(!p)return null;const W=J.pscore.weights||{},T=J.pscore.test,S=J.pscore.single||{},inc=p.inc;
  const secs=[{h:'what goes into the score',cols:[{l:'input',g:false},{l:'his number',g:false},{l:'vs his position this week',t:'percentile among players at his position on this week\'s board'},{l:'weight',g:false,t:'fitted on every 2025–26 player-game, not declared'}],rows:[
    ['matchup',p.mrank!=null?`${p.opp} is #${p.mrank} softest for the ${p.slot}`:'—',p.matchup_p==null?'—':{v:p.matchup_p,h:psPct(p.matchup_p)},psPct(W.matchup)],
    ['red-zone share',p.rz==null?'—':`${psPct(p.rz)} of the team's red-zone targets + carries, last 4${p.rz_se!=null?' · season '+psPct(p.rz_se):''}`,p.rz_p==null?'—':{v:p.rz_p,h:psPct(p.rz_p)},psPct(W.rz)],
    ['last 5',p.l5==null?'—':`${p.ppr_l5.toFixed(1)} PPR last five vs ${p.ppr_se.toFixed(1)} season${p.stat_l5!=null&&p.stat_se!=null?` · ${p.stat} ${p.stat_l5.toFixed(1)} vs ${p.stat_se.toFixed(1)}`:''}`,p.l5_p==null?'—':{v:p.l5_p,h:psPct(p.l5_p)},psPct(W.l5)+(W.l5?'':' — shown, not weighed')],
    ['contract incentive',inc&&inc.next?`$${inc.next.pay}K at ${inc.next.th} ${inc.next.label} · needs ${inc.next.npg} a game, averages ${inc.next.avg}`:'none in play','—',p.bump?'+'+p.bump+' pts (a judgment call, untested)':'—']]}];
  if(inc)secs.push({h:`contract incentives · ${inc.left} games left · Spotrac`,cols:[{l:'stat',g:false},{l:'threshold',g:false},{l:'pays',t:'$ thousands'},{l:'has',g:false},{l:'needs a game',g:false},{l:'his average',g:false},{l:'needed ÷ average',lo:true,t:'1.0 = exactly his pace'},{l:'status',g:false}],
    rows:inc.rows.map(r=>[r.label+(r.cond?' *':''),r.th,{v:r.pay,h:'$'+r.pay+'K'},r.have,r.npg==null||r.status==='reached'?'—':r.npg,r.avg,r.ratio==null||r.status==='reached'?'—':{v:r.ratio,h:r.ratio.toFixed(2)+'×'},r.status==='reached'?'<b class="rise">reached</b>':r.status==='on pace'?'<b class="rise">on pace</b>':r.status==='needs a push'?'<b style="color:#e8b100">needs a push</b>':'<span class="dim">out of reach</span>'])});
  if(T)secs.push({h:'does the score work · fitted on 2025, tested on 2026',cols:[{l:'group',g:false},{l:'player-games',g:false},{l:'scored a TD'},{l:'beat his own baseline'}],rows:[['top fifth by score',T.top.n,{v:T.top.td,h:psPct(T.top.td)},{v:T.top.beat,h:psPct(T.top.beat)}],['everyone',T.n,{v:T.field.td,h:psPct(T.field.td)},{v:T.field.beat,h:psPct(T.field.beat)}],['bottom fifth',T.bottom.n,{v:T.bottom.td,h:psPct(T.bottom.td)},{v:T.bottom.beat,h:psPct(T.bottom.beat)}]],
    note:`read: the score finds touchdowns (red-zone share does the work), it does not find players beating their own average. Last-5 form gets no weight because it did not carry over: the hottest fifth beat their baseline ${psPct(S.l5&&S.l5.top_beat)} of the time, the coldest fifth ${psPct(S.l5&&S.l5.bottom_beat)}.`});
  return {title:`${esc(p.player)} · score ${p.score??'—'}`,sub:`${p.team}${p.opp?' vs '+p.opp:''} · ${p.slot} · week ${J.pscore.week}`,sections:secs}}
const psCells=u=>{const p=psOf(u);if(!p)return '<td class="md"><span class="dim">·</span></td><td class="md"><span class="dim">·</span></td><td class="md gs"><span class="dim">·</span></td>';
  const rz=p.rz==null?'<td class="md"><span class="dim">·</span></td>':`<td class="md" title="${esc(`his share of the team's red-zone targets + carries · last 4 games ${psPct(p.rz)}${p.rz_se!=null?' · season '+psPct(p.rz_se):''}`)}"><span class="badge" style="${gradeStyle(1+(1-(p.rz_p??.5))*(NT-1))}">${Math.round(100*p.rz)}</span></td>`;
  const l5=p.l5==null?'<td class="md"><span class="dim">·</span></td>':`<td class="md" title="${esc(`PPR ${p.ppr_l5.toFixed(1)} over his last five vs ${p.ppr_se.toFixed(1)} on the season${p.stat_l5!=null&&p.stat_se!=null?` · ${p.stat} ${p.stat_l5.toFixed(1)} vs ${p.stat_se.toFixed(1)}`:''}`)}"><b class="${p.l5>.03?'rise':p.l5<-.03?'fall':'dim'}">${p.l5>.03?'▲':p.l5<-.03?'▼':''}${Math.abs(Math.round(100*p.l5))}</b></td>`;
  const sc=p.score==null?'<td class="md gs"><span class="dim">·</span></td>':`<td class="md gs" data-th="${thReg(()=>psPop(u))}" style="cursor:pointer" title="score ${p.score} of 100 within his position · matchup ${psPct(J.pscore.weights.matchup)} + red zone ${psPct(J.pscore.weights.rz)}${p.bump?' · +'+p.bump+' incentive':''} · click for the breakdown"><span class="badge" style="${gradeStyle(1+(1-p.score/100)*(NT-1))}">${p.score}</span></td>`;
  return rz+l5+sc};
const psChip=u=>{const p=psOf(u);const x=p&&p.inc&&p.inc.next;return x?` <span class="incb" data-th="${thReg(()=>psPop(u))}" title="${esc(`contract incentive in play: $${x.pay}K at ${x.th} ${x.label} · has ${x.have}, needs ${x.npg} a game over ${x.left} (averages ${x.avg}) · click for all of them`)}">$</span>`:''};
const psVal=(u,k)=>{const p=psOf(u);if(!p)return null;return k==='rz'?p.rz:k==='l5'?p.l5:p.score};
function labGrid(){const lgLive=new Set(TD_SLOTS);""")
    rep("    R.sort((a,b)=>{const x=tSortVal(a,st.k,st.a),y=tSortVal(b,st.k,st.a);return (x<y?-1:x>y?1:0)*(st.a?1:-1)});\n    const heads=LABDEF[p].heads,sample=LABDEF[p].stats(tKey(p));",
        "    const lgSV=(a,k,asc)=>k==='rz'||k==='l5'||k==='sc'?(v=>v==null?(asc?1e9:-1e9):v)(psVal(a.u,k)):tSortVal(a,k,asc);\n    R.sort((a,b)=>{const x=lgSV(a,st.k,st.a),y=lgSV(b,st.k,st.a);return (x<y?-1:x>y?1:0)*(st.a?1:-1)});\n    const heads=LABDEF[p].heads,sample=LABDEF[p].stats(tKey(p));")
    rep("    const nstat=heads.length+1, wname=Math.max(25,45-nstat*3), wopp=15, wnum=((100-wname-wopp)/nstat).toFixed(2);",
        "    const nstat=heads.length+4, wname=18, wopp=9, wfix=[5,5,6.5,6.5], wnum=((100-wname-wopp-23)/heads.length).toFixed(2);")
    rep('      Array.from({length:nstat},()=>`<col style="width:${wnum}%">`).join(\'\')}</colgroup><thead>',
        '      Array.from({length:heads.length},()=>`<col style="width:${wnum}%">`).join(\'\')}${wfix.map(w=>`<col style="width:${w}%">`).join(\'\')}</colgroup><thead>')
    rep("""        <th class="md">model</th></tr>
      <tr class="hd">""", """        <th class="md">model</th><th class="md" colspan="3" title="his own numbers: red-zone share, last-5 trend and the fitted score">him</th></tr>
      <tr class="hd">""")
    rep("""      ${th('psi','Ψ',"mean of the opponent's ranks across this slot's stats · 1 = softest",'md gs')}</tr></thead><tbody>
      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.u.player)}">${esc(pshort(x.u.player))}${x.u.inj==='0'?' <span class="inj0">Q</span>':x.u.inj==='-1'?' <span class="injm1">OUT</span>':''}</td>""",
        """      ${th('psi','Ψ',"mean of the opponent's ranks across this slot's stats · 1 = softest",'md gs')}${th('rz','RZ',"his share of his team's red-zone targets + carries over his last four games, in % · shaded within his position",'md')}${th('l5','L5','his PPR over his last five games vs his season average, in % · ▲ up, ▼ down · shown, not weighed (form did not carry over)','md')}${th('sc','SCORE','0–100 within his position: matchup + red-zone share at fitted weights, plus a small bump for a contract incentive in play · click a score for the breakdown','md gs')}</tr></thead><tbody>
      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.u.player)}">${esc(pshort(x.u.player))}${x.u.inj==='0'?' <span class="inj0">Q</span>':x.u.inj==='-1'?' <span class="injm1">OUT</span>':''}${psChip(x.u)}</td>""")
    rep("""        ${tPsi(x.psi).replace('class="md"','class="md gs"')}</tr>`).join('')
        ||`<tr><td colspan="${heads.length+3}" class="dim">nothing matches</td></tr>`}</tbody></table>`;""",
        """        ${tPsi(x.psi).replace('class="md"','class="md gs"')}${psCells(x.u)}</tr>`).join('')
        ||`<tr><td colspan="${heads.length+6}" class="dim">nothing matches</td></tr>`}</tbody></table>`;""")
    rep("if(st.k===h.dataset.k)st.a=!st.a;else{st.k=h.dataset.k;st.a=(h.dataset.k==='psi'||h.dataset.k[0]==='r'||h.dataset.k==='player'||h.dataset.k==='team'||h.dataset.k==='opp')}col(p)});\n    tWire($('#lgB'+p));\n  }\n  const all=()=>{TPOS.forEach(col);const f=$('#lgFields');if(f)rolePane(f,'prop')};",
        "if(st.k===h.dataset.k)st.a=!st.a;else{st.k=h.dataset.k;st.a=(h.dataset.k==='psi'||(h.dataset.k[0]==='r'&&h.dataset.k!=='rz')||h.dataset.k==='player'||h.dataset.k==='team'||h.dataset.k==='opp')}col(p)});\n    tWire($('#lgB'+p));\n  }\n  const all=()=>{TPOS.forEach(col);const f=$('#lgFields');if(f)rolePane(f,'prop')};")
    rep("The small number beside each figure is its rank of ${NT} (1 = allows the most) &middot;", "The small number beside each figure is its rank of ${NT} (1 = allows the most) &middot; <b>RZ</b> = his red-zone share, <b>L5</b> = his last five vs his season, <b>SCORE</b> = matchup + red zone at fitted weights (click it), <b style=\"color:#e8b100\">$</b> = a contract incentive still in play &middot;")
    rep("</style>", "/* v71 */.incb{display:inline-block;font:700 10px/1.5 var(--mono);padding:0 4px;border-radius:3px;background:#e8b100;color:#000;cursor:pointer;vertical-align:1px}\n</style>")
    open(P, 'w', encoding='utf-8').write(s); print('template: v71 applied')
else: print('template already v71')
B = 'scripts/build_dashboard.py'; b = open(B, encoding='utf-8').read()
if "data['pscore']" not in b:
    anchor = "    data['qbTargets'] = "; i = b.index(anchor)
    b = b[:i] + "    data['pscore'] = json.load(open('data/processed/player_score.json', encoding='utf-8')) if os.path.exists('data/processed/player_score.json') else None  # v71\n" + b[i:]
    open(B, 'w', encoding='utf-8').write(b); print('build_dashboard: pscore payload')
R = 'scripts/refresh.py'; r = open(R, encoding='utf-8').read()
if 'build_player_score' not in r:
    old = "'scripts/build_categories.py', 'scripts/build_mix_backtest.py'):"
    assert r.count(old) == 1; open(R, 'w', encoding='utf-8').write(r.replace(old, "'scripts/build_categories.py', 'scripts/build_mix_backtest.py', 'scripts/build_player_score.py'):")); print('refresh: player score wired')
C = 'scripts/build_categories.py'; c = open(C, encoding='utf-8').read()
old = "        for w in sorted(cur.week.unique()):"
if old in c:
    open(C, 'w', encoding='utf-8').write(c.replace(old, "        for w in sorted(set(int(x) for x in cur.week.unique()) | ({int(cur.week.max()) + 1} if len(cur) else set())):   # + the week ahead, so the live week has ranks")); print('categories: live-week ranks')
