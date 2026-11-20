"""v63 — Intel → Def Trends: what every defense has allowed to every slot over its last 1 / 3 / 5 / 7 / 10 games (this season),
ranked so the holes that are opening show first, with who draws each one this week. Client-side from the game logs. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v63 */' in s:
    print('v63 already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:100])
    s = s.replace(old, new)

rep("   {id:'ranks',label:'Defenses',desc:'rank + allowed per game, per slot and stat',c:'defenses',sub:'ranks'},",
    "   {id:'deftrends',nfl:true,label:'Def Trends',desc:'every defense against every slot over its last 1 / 3 / 5 / 7 / 10 games: where the holes are right now, which are opening and which are closing, and who draws each one this week',c:'test',sub:'deftrends'},\n   {id:'ranks',label:'Defenses',desc:'rank + allowed per game, per slot and stat',c:'defenses',sub:'ranks'},")
rep('<div id="qbtargets" hidden></div>', '<div id="qbtargets" hidden></div><div id="deftrends" hidden></div>')
rep("'api','injuries','qbtargets',", "'api','injuries','qbtargets','deftrends',")
rep("['test',qbTargetsView],", "['test',qbTargetsView],['test',defTrendsView],")
rep("const INTRO={\n", "const INTRO={\n deftrends:{what:'Where each defense is leaking right now.',how:['pick a window (last 1 / 3 / 5 / 7 / 10 games) and a stat · every cell = allowed per game to that slot, shaded by rank among the defenses (green = allows the most)','vs league = how far above the league average for that slot over the same window · vs own season = the window against that defense\\'s season average (green = getting worse)','click any row or cell for every window side by side and the game-by-game list of who did it']},\n")
rep("const NOTES={\n", "const NOTES={\n deftrends:['v63','new tab, first under Intel: every defense × slot over its last 1 / 3 / 5 / 7 / 10 games (PPR, yards, receptions, TDs), holes ranked against the league, opening / closing against the defense\\'s own season, the player who draws each hole this week, and a 32 × 7 matrix'],\n")
rep("</style>", """/* v63 */.dtcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:10px;margin-bottom:10px}.dtc{margin:0}
.dtm{width:100%;border-collapse:collapse}.dtm td{padding:4px 6px;white-space:nowrap;border-bottom:1px solid var(--edge)}#deftrends tr[data-th],#deftrends td[data-th]{cursor:pointer}#deftrends tr[data-th]:hover{background:rgba(255,255,255,.035)}
table.fx.dtt{table-layout:auto}table.dtt td,table.dtt th{white-space:nowrap}td.dtsel,th.dtsel{box-shadow:inset 0 -2px 0 var(--amber)}
.dtb{font:inherit;font-size:12px;padding:3px 10px;border:1px solid var(--edge2);background:var(--panel);color:var(--dim);border-radius:3px;cursor:pointer}.dtb.on{background:var(--amber);color:#000;font-weight:700;border-color:var(--amber)}
.dtsp{display:inline-flex;align-items:flex-end;gap:1px;height:18px;vertical-align:middle}.dtsp i{width:5px;background:var(--edge2);display:block}.dtsp i.on{background:var(--amber)}
</style>""")

VIEW = r"""
/* ---------- v63: Def Trends — every defense × slot over its last 1 / 3 / 5 / 7 / 10 games; the holes as they open ---------- */
function defTrendsView(){const el=$('#deftrends');if(!el)return;
  const SL=['QB','RB1','RB2','WR1','WR2','WR3','TE1'],WINS=[1,3,5,7,10],SE=LAST_SE;
  const ST={ppr:{l:'PPR points',d:1,f:(l,q)=>l[LOG.fppr]},yds:{l:'yards',d:0,f:(l,q)=>q?l[LOG.py]+l[LOG.ry]:l[LOG.ry]+l[LOG.recy]},rec:{l:'receptions',d:1,f:(l,q)=>q?null:l[LOG.rec]},td:{l:'touchdowns',d:2,f:(l,q)=>q?l[LOG.ptd]+l[LOG.rtd]:l[LOG.rtd]+l[LOG.rectd]}};
  // what each defense allowed to each slot, game by game (this season)
  const IDX={};J.logs.forEach(l=>{if(l[LOG.season]!==SE)return;const g=SLOTG(l[LOG.slot]);if(!SL.includes(g))return;const o=l[LOG.opp];const a=((IDX[o]=IDX[o]||{})[g]=IDX[o][g]||{});const c=a[l[LOG.week]]=a[l[LOG.week]]||{ppr:0,yds:0,rec:0,td:0};for(const k in ST){const v=ST[k].f(l,g==='QB');if(v!=null)c[k]+=v}});
  const GAMES={};J.weekly.forEach(r=>{if(r[1]===SE)(GAMES[r[0]]=GAMES[r[0]]||[]).push({w:r[2],opp:r[3]})});Object.values(GAMES).forEach(a=>a.sort((x,y)=>x.w-y.w));
  const DEFS=Object.keys(GAMES).sort();
  let win=3,stat='ppr';
  const avg=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;
  const fmt=(v,k=stat)=>v==null||isNaN(v)?'—':v.toFixed(ST[k].d),sg=(v,d=1)=>(v>=0?'+':'')+v.toFixed(d);
  function build(wk,k){const R=[];
    DEFS.forEach(d=>{const gs=GAMES[d].filter(g=>g.w<wk);if(!gs.length)return;SL.forEach(s=>{if(k==='rec'&&s==='QB')return;
      const vals=gs.map(g=>{const c=IDX[d]&&IDX[d][s]&&IDX[d][s][g.w];return c?c[k]:0});const w={};WINS.forEach(n=>w[n]=avg(vals.slice(-n)));
      R.push({d,s,vals,w,se:avg(vals),n:vals.length,rk:{},lg:{}})})});
    SL.forEach(s=>{const rs=R.filter(r=>r.s===s);if(!rs.length)return;[...WINS,'se'].forEach(n=>{const get=r=>n==='se'?r.se:r.w[n];const lg=avg(rs.map(get));rs.slice().sort((a,b)=>get(b)-get(a)).forEach((r,i)=>{r.rk[n]=i+1;r.lg[n]=lg;r.nr=rs.length})})});
    return R}
  const MEMO={};const B=(wk,k)=>MEMO[wk+k]||(MEMO[wk+k]=build(wk,k));
  const draw=(d,s,wk)=>{const o=(J.sched26[d]||[])[wk-1]||'';if(!o)return {};if(o==='BYE')return {bye:true};const t=o.replace('@','');
    const c=UNIVERSE.filter(u=>u.team===t&&u.grp===s&&String(u.inj)!=='-1').sort((a,b)=>(a.slot===s?0:1)-(b.slot===s?0:1)||a.depth-b.depth)[0];return {opp:t,p:c?c.player:null}};
  const drawH=x=>x.bye?'<span class="dim">bye</span>':!x.opp?'<span class="dim">—</span>':`${tcell(x.opp)}${x.p?' '+pn(x.p,x.opp,true):''}`;
  const spark=(vals,n)=>{const v=vals.slice(-10),mx=Math.max(1e-9,...v);return `<span class="dtsp" title="${esc('last '+v.length+' games, oldest → newest: '+v.map(x=>fmt(x)).join(' · '))}">${v.map((x,i)=>`<i${i>=v.length-n?' class="on"':''} style="height:${Math.max(2,Math.round(18*x/mx))}px"></i>`).join('')}</span>`};
  const pop=(d,s,wk)=>()=>{const ks=Object.keys(ST).filter(k=>!(k==='rec'&&s==='QB'));const per={};ks.forEach(k=>per[k]=B(wk,k).find(r=>r.d===d&&r.s===s));const b=per[ks[0]];if(!b)return null;const x=draw(d,s,wk);
    const cols=[{l:'window',g:false},{l:'games',g:false},...ks.flatMap(k=>[{l:ST[k].l,t:'allowed per game to the '+s+(k==='yds'?' · QB = passing + rushing, everyone else = rushing + receiving':'')},{l:'rank',g:false,t:'among the defenses over the same window · 1 = allows the most'},{l:'league',g:false,t:'league average for the slot over the same window'}])];
    const rows=[...WINS,'se'].map(n=>Object.assign([n==='se'?'season':'last '+n,n==='se'?b.n:Math.min(n,b.n),...ks.flatMap(k=>{const r=per[k],v=n==='se'?r.se:r.w[n];return [{v,h:fmt(v,k)},{v:r.rk[n],h:badge(r.rk[n])},{v:r.lg[n],h:fmt(r.lg[n],k)}]})],{hi:n===win}));
    return {title:`${d} vs ${s}`,sub:`${SE} · through week ${wk-1} · ${b.n} games · this week: ${x.bye?'bye':x.opp?x.opp+(x.p?' · '+esc(x.p):''):'—'}`,sections:[{h:'allowed per game, window by window · rank 1 = allows the most · the selected window is tinted',cols,rows},{h:'game by game · who did it',html:defLogTable(d,s,[SE])}]}};
  function render(){const wk=G.week;const R=B(wk,stat).filter(r=>inD(r.d)&&inP(posOf(r.s)));
    const ctl=`<div class="clbox" style="align-items:center"><span class="mini dim">window</span>${WINS.map(n=>`<button class="dtb${n===win?' on':''}" data-w="${n}">last ${n}</button>`).join('')}<label class="mini">stat <select id="dtS">${Object.entries(ST).map(([k,v])=>`<option value="${k}"${k===stat?' selected':''}>${v.l}</option>`).join('')}</select></label><span class="mini dim">${SE} games through week ${wk-1} · allowed per game · green = allows the most · click anything for every window and the game log</span></div>`;
    if(!R.length){el.innerHTML=ctl+`<p class="note">no ${SE} games before week ${wk}${stat==='rec'?' (receptions has no QB row)':''}</p>`;wire();return}
    const d=ST[stat].d;R.forEach(r=>{r.ex=r.w[win]-r.lg[win];r.own=r.w[win]-r.se});
    const cw=win>=7?3:win,od=r=>r.w[cw]-r.se;
    const holes=R.slice().sort((a,b)=>b.ex-a.ex).slice(0,6);
    const open=R.filter(r=>r.n>cw&&r.w[cw]>r.lg[cw]).sort((a,b)=>od(b)-od(a)).slice(0,6);
    const shut=R.filter(r=>r.n>cw&&r.se>r.lg.se).sort((a,b)=>od(a)-od(b)).slice(0,6);
    const line=(r,val,dl)=>`<tr data-th="${thReg(pop(r.d,r.s,wk))}"><td>${tcell(r.d)}</td><td>${slotchip(r.s)}</td><td class="n"><span class="badge" style="${gradeStyle(r.rk[val],r.nr)}">${fmt(r.w[val])}</span></td><td class="n">${dl}</td><td>${drawH(draw(r.d,r.s,wk))}</td></tr>`;
    const card=(h,f,rows,dl,val)=>`<div class="panel dtc"><h3>${h} <span class="f">${f}</span></h3>${rows.length?`<table class="dtm"><tbody>${rows.map(r=>line(r,val,dl(r))).join('')}</tbody></table>`:'<p class="note mini">nothing qualifies yet</p>'}</div>`;
    const cards=`<div class="dtcards">${card(`biggest holes · last ${win}`,`${ST[stat].l} per game over the league average for the slot · who draws it this week`,holes,r=>`<b class="rise">${sg(r.ex,d)}</b>`,win)}${card(`opening · last ${cw} vs own season`,'already above the league and getting worse',open,r=>`<b class="rise">${sg(od(r),d)}</b>`,cw)}${card(`closing · last ${cw} vs own season`,'was a hole on the season, tightening now',shut,r=>`<b class="fall">${sg(od(r),d)}</b>`,cw)}</div>`;
    const wc=(r,n)=>{const v=n==='se'?r.se:r.w[n],g=n==='se'?r.n:Math.min(n,r.n);return `<td class="n${n===win?' dtsel':''}" data-v="${v}" title="${esc(`${r.d} vs ${r.s} · ${n==='se'?'season':'last '+g+' game'+(g===1?'':'s')} · rank ${r.rk[n]} of ${r.nr} · league ${fmt(r.lg[n])}`)}"><span class="badge" style="${gradeStyle(r.rk[n],r.nr)}">${fmt(v)}</span>${n!=='se'&&r.n<n?`<span class="mini dim"> ${r.n}g</span>`:''}</td>`};
    const H=(l,t,c)=>`<th${c?` class="${c}"`:''} title="${esc(t||'')}">${l}</th>`;
    const L=R.slice().sort((a,b)=>b.ex-a.ex);
    const tbl=`<div class="panel"><h3>every defense × slot <span class="f">${L.length} rows, biggest hole over the last ${win} first · every column sorts · bars = the last 10 games, the selected window in amber</span></h3><div class="tscroll"><table class="fx dtt"><thead><tr>${H('def')}${H('slot')}${WINS.map(n=>H('L'+n,'allowed per game over the last '+n+' game'+(n===1?'':'s'),n===win?'dtsel':'')).join('')}${H('season','allowed per game, all '+SE+' games')}${H('vs league','last '+win+' minus the league average for the slot over the same window · % of that average')}${H('vs own season','last '+win+' minus this defense\'s season average · green = allowing more lately')}${H('last 10','game by game, oldest to newest','nosort')}${H('this week','the offense it faces in week '+wk+' and the player in that slot')}</tr></thead><tbody>
      ${L.map(r=>`<tr data-th="${thReg(pop(r.d,r.s,wk))}"><td>${tcell(r.d)}</td><td>${slotchip(r.s)}</td>${WINS.map(n=>wc(r,n)).join('')}${wc(r,'se')}<td class="n" data-v="${r.ex}"><b class="${r.ex>0?'rise':'fall'}">${sg(r.ex,d)}</b>${r.lg[win]?` <span class="mini dim">${sg(100*r.ex/r.lg[win],0)}%</span>`:''}</td><td class="n" data-v="${r.own}"><span class="${r.own>0?'rise':r.own<0?'fall':'dim'}">${sg(r.own,d)}</span></td><td>${spark(r.vals,win)}</td><td>${drawH(draw(r.d,r.s,wk))}</td></tr>`).join('')}</tbody></table></div></div>`;
    const by={};R.forEach(r=>by[r.d+'|'+r.s]=r);const defs=[...new Set(R.map(r=>r.d))],sls=SL.filter(s=>R.some(r=>r.s===s));
    const mx=`<div class="panel"><h3>the map · last ${win} <span class="f">${ST[stat].l} allowed per game · shaded by rank within the slot · ▲ ▼ = 15%+ above / below that defense's own season · softest = its worst slot by rank</span></h3><div class="tscroll"><table class="fx dtt"><thead><tr>${H('def')}${H('this week','the offense it faces in week '+wk)}${sls.map(s=>H(s)).join('')}${H('softest','the slot where this defense ranks worst over the window')}</tr></thead><tbody>
      ${defs.map(t=>{const rs=sls.map(s=>by[t+'|'+s]).filter(Boolean);const worst=rs.slice().sort((a,b)=>a.rk[win]-b.rk[win])[0];const x=draw(t,'QB',wk);
        return `<tr><td>${tcell(t)}</td><td>${x.bye?'<span class="dim">bye</span>':x.opp?tcell(x.opp):'<span class="dim">—</span>'}</td>${sls.map(s=>{const r=by[t+'|'+s];if(!r)return '<td></td>';const a=r.se?(r.w[win]-r.se)/r.se:0;return `<td class="n" data-v="${r.w[win]}" data-th="${thReg(pop(t,s,wk))}" title="${esc(`${t} vs ${s} · last ${Math.min(win,r.n)} · rank ${r.rk[win]} of ${r.nr} · league ${fmt(r.lg[win])} · own season ${fmt(r.se)}`)}"><span class="badge" style="${gradeStyle(r.rk[win],r.nr)}">${fmt(r.w[win])}</span>${a>.15?'<span class="rise mini"> ▲</span>':a<-.15?'<span class="fall mini"> ▼</span>':''}</td>`}).join('')}<td data-v="${worst?worst.rk[win]:99}">${worst?`${slotchip(worst.s)} <span class="mini dim">#${worst.rk[win]}</span>`:''}</td></tr>`}).join('')}</tbody></table></div></div>`;
    el.innerHTML=ctl+cards+tbl+mx;wire();logoize(el);sortableAll(el)}
  function wire(){el.querySelectorAll('.dtb').forEach(b=>b.onclick=()=>{win=+b.dataset.w;render()});const s=$('#dtS');if(s)s.onchange=()=>{stat=s.value;render()}}
  render();RR.push(render)}

"""
rep("function qbTargetsView(){const el=$('#qbtargets');if(!el)return;", VIEW + "function qbTargetsView(){const el=$('#qbtargets');if(!el)return;")
open(P, 'w', encoding='utf-8').write(s)
print('v63 applied')
