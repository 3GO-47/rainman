"""v64 — Def Trends rebuilt: colour strips instead of a number wall. One strip per defense x slot = its rank over the last
10 / 7 / 5 / 3 / 1 games (old -> recent), green = allows the most. Three short lists + one 32 x 7 map, no sideways scroll,
numbers only in the click-through. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v64 */' in s:
    print('v64 already applied'); sys.exit(0)
a = s.index("/* ---------- v63: Def Trends"); b = s.index("function qbTargetsView(){const el=$('#qbtargets');if(!el)return;")
assert a < b
VIEW = r"""/* ---------- v64: Def Trends — every defense x slot as a colour strip over its last 10 / 7 / 5 / 3 / 1 games ---------- */
/* v64 */function defTrendsView(){const el=$('#deftrends');if(!el)return;
  const SL=['QB','RB1','RB2','WR1','WR2','WR3','TE1'],WINS=[1,3,5,7,10],ORD=[10,7,5,3,1],SE=LAST_SE;
  const ST={ppr:{l:'PPR points',d:1,f:(l,q)=>l[LOG.fppr]},yds:{l:'yards',d:0,f:(l,q)=>q?l[LOG.py]+l[LOG.ry]:l[LOG.ry]+l[LOG.recy]},rec:{l:'receptions',d:1,f:(l,q)=>q?null:l[LOG.rec]},td:{l:'touchdowns',d:2,f:(l,q)=>q?l[LOG.ptd]+l[LOG.rtd]:l[LOG.rtd]+l[LOG.rectd]}};
  const IDX={};J.logs.forEach(l=>{if(l[LOG.season]!==SE)return;const g=SLOTG(l[LOG.slot]);if(!SL.includes(g))return;const o=l[LOG.opp];const a=((IDX[o]=IDX[o]||{})[g]=IDX[o][g]||{});const c=a[l[LOG.week]]=a[l[LOG.week]]||{ppr:0,yds:0,rec:0,td:0};for(const k in ST){const v=ST[k].f(l,g==='QB');if(v!=null)c[k]+=v}});
  const GAMES={};J.weekly.forEach(r=>{if(r[1]===SE)(GAMES[r[0]]=GAMES[r[0]]||[]).push({w:r[2],opp:r[3]})});Object.values(GAMES).forEach(a=>a.sort((x,y)=>x.w-y.w));
  const DEFS=Object.keys(GAMES).sort();
  let win=3,stat='ppr';
  const avg=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;
  const fmt=(v,k=stat)=>v==null||isNaN(v)?'—':v.toFixed(ST[k].d);
  function build(wk,k){const R=[];
    DEFS.forEach(d=>{const gs=GAMES[d].filter(g=>g.w<wk);if(!gs.length)return;SL.forEach(s=>{if(k==='rec'&&s==='QB')return;
      const vals=gs.map(g=>{const c=IDX[d]&&IDX[d][s]&&IDX[d][s][g.w];return c?c[k]:0});const w={};WINS.forEach(n=>w[n]=avg(vals.slice(-n)));
      R.push({d,s,vals,w,se:avg(vals),n:vals.length,rk:{},lg:{}})})});
    SL.forEach(s=>{const rs=R.filter(r=>r.s===s);if(!rs.length)return;[...WINS,'se'].forEach(n=>{const get=r=>n==='se'?r.se:r.w[n];const lg=avg(rs.map(get));rs.slice().sort((a,b)=>get(b)-get(a)).forEach((r,i)=>{r.rk[n]=i+1;r.lg[n]=lg;r.nr=rs.length})})});
    return R}
  const MEMO={};const B=(wk,k)=>MEMO[wk+k]||(MEMO[wk+k]=build(wk,k));
  const draw=(d,s,wk)=>{const o=(J.sched26[d]||[])[wk-1]||'';if(!o)return {};if(o==='BYE')return {bye:true};const t=o.replace('@','');
    const c=UNIVERSE.filter(u=>u.team===t&&u.grp===s&&String(u.inj)!=='-1').sort((a,b)=>(a.slot===s?0:1)-(b.slot===s?0:1)||a.depth-b.depth)[0];return {opp:t,p:c?c.player:null}};
  const drawH=x=>x.bye?'<span class="dim">bye</span>':!x.opp?'<span class="dim">—</span>':`${x.p?pn(x.p,x.opp,true):tcell(x.opp)}`;
  // the strip: five squares, last 10 -> 7 -> 5 -> 3 -> 1, each coloured by this defense's rank against the slot over that window
  const strip=r=>`<span class="dts" title="${esc(`${r.d} vs ${r.s} · ${ST[stat].l} allowed per game — `+ORD.map(n=>`last ${Math.min(n,r.n)}: ${fmt(r.w[n])} (#${r.rk[n]})`).join(' · ')+` · season ${fmt(r.se)}`)}">${ORD.map(n=>`<i style="${gradeStyle(r.rk[n],r.nr)}"></i>`).join('')}</span>`;
  const pop=(d,s,wk)=>()=>{const ks=Object.keys(ST).filter(k=>!(k==='rec'&&s==='QB'));const per={};ks.forEach(k=>per[k]=B(wk,k).find(r=>r.d===d&&r.s===s));const b=per[ks[0]];if(!b)return null;const x=draw(d,s,wk);
    const cols=[{l:'window',g:false},{l:'games',g:false},...ks.flatMap(k=>[{l:ST[k].l,g:false,t:'allowed per game to the '+s+(k==='yds'?' · QB = passing + rushing, everyone else = rushing + receiving':'')},{l:'rank',g:false,t:'among the defenses over the same window · 1 = allows the most'},{l:'league',g:false,t:'league average for the slot over the same window'}])];
    const rows=[...WINS,'se'].map(n=>Object.assign([n==='se'?'season':'last '+n,n==='se'?b.n:Math.min(n,b.n),...ks.flatMap(k=>{const r=per[k],v=n==='se'?r.se:r.w[n];return [{v,h:'<b>'+fmt(v,k)+'</b>'},{v:r.rk[n],h:badge(r.rk[n])},{v:r.lg[n],h:fmt(r.lg[n],k)}]})],{hi:n===win}));
    return {title:`${d} vs ${s}`,sub:`${SE} · through week ${wk-1} · ${b.n} games · this week: ${x.bye?'bye':x.opp?x.opp+(x.p?' · '+esc(x.p):''):'—'}`,sections:[{h:'allowed per game, window by window · rank 1 = allows the most',cols,rows},{h:'game by game · who did it',html:defLogTable(d,s,[SE])}]}};
  function render(){const wk=G.week;const R=B(wk,stat).filter(r=>inD(r.d)&&inP(posOf(r.s)));
    const ctl=`<div class="clbox" style="align-items:center"><span class="mini dim">rank on</span>${WINS.map(n=>`<button class="dtb${n===win?' on':''}" data-w="${n}">last ${n}</button>`).join('')}<label class="mini">stat <select id="dtS">${Object.entries(ST).map(([k,v])=>`<option value="${k}"${k===stat?' selected':''}>${v.l}</option>`).join('')}</select></label></div>
      <p class="note mini dtkey"><span class="dts">${[26,20,14,8,2].map(k=>`<i style="${gradeStyle(k,NT)}"></i>`).join('')}</span> each strip = one defense against one slot over its last <b>10 · 7 · 5 · 3 · 1</b> games, left to right · <b class="rise">green</b> = allows the most in the league, <b class="fall">red</b> = the least · a strip turning green toward the right is a hole opening · click a strip for the numbers and who did it</p>`;
    if(!R.length){el.innerHTML=ctl+`<p class="note">no ${SE} games before week ${wk}</p>`;wire();return}
    R.forEach(r=>{r.ex=r.w[win]-r.lg[win]});
    const cw=win>=7?3:win,od=r=>r.w[cw]-r.se,live=R.filter(r=>!draw(r.d,r.s,wk).bye);
    const holes=live.slice().sort((a,b)=>b.ex-a.ex).slice(0,6);
    const open=live.filter(r=>r.n>cw&&r.w[cw]>r.lg[cw]).sort((a,b)=>od(b)-od(a)).slice(0,6);
    const shut=live.filter(r=>r.n>cw&&r.se>r.lg.se).sort((a,b)=>od(a)-od(b)).slice(0,6);
    const line=(r,n)=>`<tr data-th="${thReg(pop(r.d,r.s,wk))}"><td>${tcell(r.d)}</td><td>${slotchip(r.s)}</td><td>${strip(r)}</td><td class="n"><b>${fmt(r.w[n])}</b></td><td class="dtp">${drawH(draw(r.d,r.s,wk))}</td></tr>`;
    const card=(h,f,rows,n)=>`<div class="panel dtc"><h3>${h}</h3><p class="mini dim" style="margin:0 0 6px">${f}</p>${rows.length?`<table class="dtm"><tbody>${rows.map(r=>line(r,n)).join('')}</tbody></table>`:'<p class="note mini">nothing qualifies yet</p>'}</div>`;
    const cards=`<div class="dtcards">${card(`biggest holes`,`most ${ST[stat].l} over the league average, last ${win} · number = allowed per game · who draws it this week`,holes,win)}${card(`opening`,`already soft and worse over the last ${cw} than on the season`,open,cw)}${card(`closing`,`soft on the season, tightening over the last ${cw}`,shut,cw)}</div>`;
    const by={};R.forEach(r=>by[r.d+'|'+r.s]=r);const defs=[...new Set(R.map(r=>r.d))],sls=SL.filter(s=>R.some(r=>r.s===s));
    const lg=`<div class="dtlg">${ORD.map(n=>`<b${n===win?' class="on"':''}>${n}</b>`).join('')}</div>`;
    const mx=`<div class="panel"><h3>every defense</h3><table class="dtmap"><thead><tr><th>def</th><th title="the offense it faces in week ${wk}">wk ${wk}</th>${sls.map(s=>`<th title="click to sort on the last ${win}">${s}${lg}</th>`).join('')}</tr></thead><tbody>
      ${defs.map(t=>{const x=draw(t,'QB',wk);return `<tr><td>${tcell(t)}</td><td>${x.bye?'<span class="dim">bye</span>':x.opp?tcell(x.opp):'<span class="dim">—</span>'}</td>${sls.map(s=>{const r=by[t+'|'+s];return r?`<td data-v="${r.w[win]}" data-th="${thReg(pop(t,s,wk))}">${strip(r)}</td>`:'<td></td>'}).join('')}</tr>`}).join('')}</tbody></table></div>`;
    el.innerHTML=ctl+cards+mx;wire();logoize(el);sortableAll(el)}
  function wire(){el.querySelectorAll('.dtb').forEach(b=>b.onclick=()=>{win=+b.dataset.w;render()});const s=$('#dtS');if(s)s.onchange=()=>{stat=s.value;render()}}
  render();RR.push(render)}

"""
s = s[:a] + VIEW + s[b:]
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:100])
    s = s.replace(old, new)
# one short intro line instead of three
i = s.index(" deftrends:{what:'Where each defense is leaking right now.'"); j = s.index("\n", i)
s = s[:i] + " deftrends:{what:'Where each defense is leaking right now.',how:['strips read left to right: last 10 · 7 · 5 · 3 · 1 games · green = allows the most · click a strip for the numbers']}," + s[j:]
rep("</style>", """/* v64 */.dts{display:inline-flex;gap:2px;vertical-align:middle}.dts i{display:block;width:16px;height:16px;border-radius:2px;border:0!important}
.dtlg{display:flex;gap:2px;justify-content:center;margin-top:2px}.dtlg b{width:16px;font:400 9px/1 var(--mono);color:var(--dim);text-align:center}.dtlg b.on{color:var(--amber);font-weight:700}
table.dtmap{border-collapse:collapse;width:100%;max-width:1100px}table.dtmap th{font-size:11px;color:var(--dim);padding:4px 4px;text-align:center;cursor:pointer;white-space:nowrap}table.dtmap th:first-child,table.dtmap td:first-child{text-align:left}
table.dtmap td{padding:3px 4px;text-align:center;border-bottom:1px solid var(--edge);white-space:nowrap}table.dtmap tr:hover td{background:rgba(255,255,255,.03)}
.dtcards{grid-template-columns:repeat(auto-fit,minmax(min(100%,380px),1fr))}.dtm td.dtp{white-space:normal}.dtkey{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#deftrends{max-width:100%;overflow-x:hidden}
@media(max-width:760px){.dts i{width:9px;height:14px}.dtlg b{width:9px;font-size:7px}table.dtmap th:nth-child(2),table.dtmap td:nth-child(2){display:none}table.dtmap td,table.dtmap th{padding:3px 2px}}
</style>""")
rep(" deftrends:['v63',", " deftrends64:['v64','Def Trends rebuilt as colour strips: one strip per defense × slot (last 10 · 7 · 5 · 3 · 1), three short lists and one map, no sideways scroll; the numbers moved into the click-through'],\n deftrends:['v63',")
open(P, 'w', encoding='utf-8').write(s)
print('v64 applied')
