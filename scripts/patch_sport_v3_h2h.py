"""sport template v3 (n108): H2H tab under Matchups; Matchups cards carry the posted lines, the plays in the game and the last
meetings; Matchup Lab becomes a per-market lab with hit rates against the posted line; the player card gets hit rates, splits
and a sparkline. Rerunnable (guarded)."""
import os, re, sys
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sport_template.html')
s = open(P, encoding='utf-8').read()
if 'function h2h()' in s:
    print('already applied'); sys.exit()

def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:80])
    s = s.replace(old, new)

# ---- nav: H2H under Matchups, intro text ----
rep("{id:'board',label:'Big Board',desc:'every player on the slate × market: projection, band, opponent rank — sort any column'}]}",
    "{id:'board',label:'Big Board',desc:'every player on the slate × market: projection, band, opponent rank — sort any column'},{id:'h2h',label:'H2H',desc:'head to head: the last meetings between the two teams and every rotation player\\'s history against tonight\\'s opponent, market by market, against the posted line'}]}")
rep("{id:'lab',label:'Matchup Lab',desc:'every player: season · prior · last-10 averages beside the opponent\\'s rank for his slot'}",
    "{id:'lab',label:'Matchup Lab',desc:'one market at a time: every player\\'s averages, trend, projection, the posted line and how often he has cleared it (L5 · L10 · season · vs this opponent)'}")
rep(" cards:{what:'Every upcoming game: both rotations against the defense they face, market by market.',how:['colored number = the opponent\\'s rank allowing that stat to his slot (1 = allows the most)','his averages are this season, blended with last season when the sample is thin','proj = projection for this game']},",
    " cards:{what:'Every upcoming game: the plays in it, the last meetings, and both rotations against the defense they face, market by market, with every posted line.',how:['colored number = the opponent\\'s rank allowing that stat to his slot (1 = allows the most) with the projection under it','under each name: his posted lines — ▲ over / ▼ under is the model\\'s lean, the number is the edge in points','plays in this game = the prop edges and the game edge that clear the bar; lines only = hide players with nothing posted']},\n h2h:{what:'Head to head. The last meetings between the two teams, then every rotation player\\'s games against tonight\\'s opponent across the loaded seasons.',how:['vs = his average in those games · Δ = against his season average (green = better vs this opponent)','O-U = his record over the posted line in those games','sorted by games against the opponent; lines only = players with a posted prop']},")
rep(" lab:{what:'Every player\\'s season, prior-season and last-10 averages beside the opponent\\'s rank for his slot.',how:['L10 = last ten games','rank 1 = softest opponent']},",
    " lab:{what:'One market at a time. Every player\\'s averages and trend, the opponent\\'s rank, the projection, the posted line and his hit rate over it.',how:['pick the market with the chips · hit = share of games over the posted line (L5 · L10 · season · vs this opponent)','trend = last 5 against the season (▲ hot · ▼ cold)','lines only = players with a posted prop · starters = starter rate above 50%']},")

# ---- helpers ----
rep("/* ---- MATCHUPS ---- */\nconst OPEN=new Set();",
r"""/* ---- v3 helpers: lines, logs, hit rates, meetings ---- */
const COMBO={pra:['pts','reb','ast'],pr:['pts','reb'],pa:['pts','ast'],ra:['reb','ast']};
const lval=(l,k)=>{const c=COMBO[k];return c?c.reduce((s,x)=>s+(+l[LC[x]]||0),0):+l[LC[k]]};
const LINES={};(J.props||[]).forEach(r=>{(LINES[r.pid]=LINES[r.pid]||{})[r.market]=r});
const logsOf=pid=>(PLOGS[pid]||[]).slice().sort((a,b)=>a[LC.date]<b[LC.date]?1:-1);
const hit=(L,k,line)=>{let o=0,u=0;L.forEach(l=>{const v=lval(l,k);if(v>line)o++;else if(v<line)u++});return {o,u,n:L.length,pct:(o+u)?o/(o+u):null}};
const hitTxt=(h,short)=>h.n?`<span class="mono" style="color:${h.pct>=.6?'var(--green)':h.pct<=.4?'var(--red)':'var(--txt)'}">${h.o}-${h.u}</span>${short?'':` <span class="mini">${(100*h.pct).toFixed(0)}%</span>`}`:'<span class="dim">·</span>';
const lean=r=>r?`<span class="mono" style="color:${r.edge>=.05?'var(--green)':r.edge>=.03?'#e8b100':'var(--dim)'}" title="${r.player} ${MKL[r.market]||r.market} ${r.line}: model ${r.side} · proj ${r.proj} · P(over) ${(100*r.p_over).toFixed(0)}% vs market ${(100*r.p_imp).toFixed(0)}% · best ${amer(r.price)} ${r.book||''}">${r.side==='Over'?'▲':'▼'}${(100*r.edge).toFixed(0)}</span>`:'';
const okProp=r=>r.n_books>=2&&(r.gp+r.gp_prior)>=8;
const dlt=(a,b,dec)=>a==null||b==null?'':`<span class="mini" style="color:${a-b>0?'var(--green)':a-b<0?'var(--red)':'var(--dim)'}">${a-b>0?'+':''}${(a-b).toFixed(dec)}</span>`;
function meetings(a,b){const by={};J.logs.forEach(l=>{if((l[LC.team]===a&&l[LC.opp]===b)||(l[LC.team]===b&&l[LC.opp]===a)){const d=l[LC.date];const m=by[d]=by[d]||{date:d,season:l[LC.season],stype:l[LC.stype],[a]:0,[b]:0,home:''};m[l[LC.team]]+=+l[LC.pts]||0;if(l[LC.team]===a)m.home=l[LC.ha]==='H'?a:b}});
  return Object.values(by).filter(m=>m[a]>0&&m[b]>0).sort((x,y)=>x.date<y.date?1:-1)}
function meetTxt(g,n=5){const ms=meetings(g.away,g.home).slice(0,n);if(!ms.length)return '';const w=ms.filter(m=>m[g.home]>m[g.away]).length;const tot=mean(ms.map(m=>m[g.away]+m[g.home]));
  return `<span class="mini">last ${ms.length}: ${g.home} ${w}-${ms.length-w} · avg total <b>${tot.toFixed(1)}</b>${g.ou?` (O/U ${g.ou})`:''} · ${ms.map(m=>`<span title="${m.date}${m.stype==='post'?' · playoffs':''}">${m[g.away]}-${m[g.home]}</span>`).join(', ')}</span>`}
function gamePlays(g){const T=new Set([g.away,g.home]);const ps=PR.filter(r=>T.has(r.team)&&okProp(r)&&r.edge>=.03).sort((a,b)=>b.edge-a.edge).slice(0,4);const out=[];
  if(g.home_line!=null&&g.model_margin!=null){const e=g.model_margin+g.home_line;if(Math.abs(e)>=2)out.push(`<span class="mono">${e>0?g.home:g.away} ${e>0?(g.home_line>0?'+':'')+g.home_line:(-g.home_line>0?'+':'')+(-g.home_line)} <span style="color:var(--green)">+${Math.abs(e).toFixed(1)}</span></span>`)}
  if(g.ou&&g.model_total!=null){const e=g.model_total-parseFloat(g.ou);if(Math.abs(e)>=2.5)out.push(`<span class="mono">${e>0?'Over':'Under'} ${g.ou} <span style="color:var(--green)">${e>0?'+':''}${e.toFixed(1)}</span></span>`)}
  ps.forEach(r=>out.push(`<span class="mono">${esc(r.player)} ${r.side==='Over'?'o':'u'}${r.line} ${MKL[r.market]||r.market} ${lean(r)}</span>`));
  return out.length?`<div class="mplays"><span class="mini">plays in this game</span>${out.join('<span class="dim"> · </span>')}</div>`:''}
/* ---- MATCHUPS ---- */
const OPEN=new Set();""")

# ---- cards: lines under each name, plays + meetings per game, lines-only toggle ----
rep("""  const side=(off,def,full)=>{const ps=rotation(off).filter(p=>inS(p.slot)).slice(0,full?40:J.rotation);""",
    """  const side=(off,def,full)=>{const ps=rotation(off).filter(p=>inS(p.slot)&&(!G.lo||LINES[p.pid])).slice(0,full?40:J.rotation);""")
rep("""<span class="mhis">${p.gp?`${p.gp} gp · `:`${p.gp_prior} gp last yr · `}${MKS.slice(0,4).map(mk=>`${mk.label} ${fmt(his(p,mk.k),mk.dec)}`).join(' · ')}</span></span>""",
    """<span class="mhis">${p.gp?`${p.gp} gp · `:`${p.gp_prior} gp last yr · `}${MKS.slice(0,4).map(mk=>`${mk.label} ${fmt(his(p,mk.k),mk.dec)}`).join(' · ')}</span>${LINES[p.pid]?`<span class="mhis mln">${MK.filter(mk=>LINES[p.pid][mk.k]).map(mk=>{const r=LINES[p.pid][mk.k];return `<span>${mk.label} <b>${r.line}</b> ${lean(r)}</span>`}).join(' ')}</span>`:''}</span>""")
rep("""<button class="mopen" id="mAll">${OPEN.size?'collapse all':'open all'}</button><span class="note">one card per game""",
    """<button class="mopen" id="mAll">${OPEN.size?'collapse all':'open all'}</button><button class="mopen ${G.lo?'on':''}" id="mLo">lines only</button><span class="note">one card per game""")
rep("""      <div class="msides">${side(g.away,g.home,open)}${side(g.home,g.away,open)}</div>""",
    """      ${gamePlays(g)}${(m=>m?`<div class="mplays">${m}</div>`:'')(meetTxt(g))}
      <div class="msides">${side(g.away,g.home,open)}${side(g.home,g.away,open)}</div>""")
rep("""$('#mAll').onclick=()=>{if(OPEN.size)OPEN.clear();else gs.forEach(g=>OPEN.add(g.away+'@'+g.home));cards()};bindPL(el)}""",
    """$('#mAll').onclick=()=>{if(OPEN.size)OPEN.clear();else gs.forEach(g=>OPEN.add(g.away+'@'+g.home));cards()};$('#mLo').onclick=()=>{G.lo=!G.lo;cards()};bindPL(el)}
function h2h(){const gs=GAMESD();const el=$('#match');const MKS=MK.filter(m=>['pts','reb','ast','tpm','pra'].includes(m.k));const minG=G.h2n||2;
  el.innerHTML=`<div class="controls">${dayChips()}<button class="mopen ${G.lo?'on':''}" id="hLo">lines only</button><select id="hMin">${[1,2,3,5].map(n=>`<option value="${n}" ${n===minG?'selected':''}>${n}+ games vs opp</option>`).join('')}</select><span class="note">per game: the last meetings (scores from the box scores), then every rotation player's history against the opponent across ${J.seasons.join(' + ')} · vs = his average in those games, Δ = against this season's average · O-U = his record over the posted line in those games</span></div>`+
   (gs.map(g=>{const ms=meetings(g.away,g.home).slice(0,8);const k=g.away+'@'+g.home;
    const rows=[[g.away,g.home],[g.home,g.away]].flatMap(([t,o])=>rotation(t).filter(p=>inS(p.slot)&&(!G.lo||LINES[p.pid])).slice(0,J.rotation+2).map(p=>({p,o,L:logsOf(p.pid).filter(l=>l[LC.opp]===o)}))).filter(x=>x.L.length>=minG).sort((a,b)=>b.L.length-a.L.length||primaryOf(b.p)-primaryOf(a.p));
    return `<div class="panel mcard"><div class="mtop"><span>${tc(g.away)} <span class="dim">@</span> ${tc(g.home)}</span><span class="mini">${dayKey(g.date)} ${fmtT(g.date)} CT · ${g.odds?lineTxt(g):'no line'}${g.ou?' · O/U '+g.ou:''}</span></div>
      ${ms.length?`<div class="mplays"><span class="mini">last meetings</span>${ms.map(m=>`<span class="mono" title="${m.season} ${m.stype}">${m.date.slice(2)} <b style="color:${m[g.home]>m[g.away]?'var(--green)':'var(--txt)'}">${g.home} ${m[g.home]}</b>-<b style="color:${m[g.away]>m[g.home]?'var(--green)':'var(--txt)'}">${m[g.away]} ${g.away}</b> <span class="dim">${m[g.home]+m[g.away]}</span></span>`).join('<span class="dim"> · </span>')}<span class="mini">· ${g.home} ${ms.filter(m=>m[g.home]>m[g.away]).length}-${ms.filter(m=>m[g.away]>m[g.home]).length} · avg total <b>${mean(ms.map(m=>m[g.away]+m[g.home])).toFixed(1)}</b></span></div>`:'<div class="mplays"><span class="mini">no meetings in the loaded seasons</span></div>'}
      ${rows.length?`<div class="wrap-x"><table><thead><tr><th>player</th><th>tm</th><th>slot</th><th title="games vs this opponent">G</th>${MKS.map(mk=>`<th colspan="3">${mk.label}<div class="mini">vs · Δ · line O-U</div></th>`).join('')}</tr></thead><tbody>
      ${rows.map(({p,o,L})=>`<tr><td>${pname(p)}</td><td>${tc(p.team)}</td><td><span class="slot">${p.slot}</span></td><td class="mono">${L.length}</td>${MKS.map(mk=>{const v=mean(L.map(l=>lval(l,mk.k)));const r=LINES[p.pid]&&LINES[p.pid][mk.k];return `<td class="mono"><b>${fmt(v,mk.dec)}</b></td><td>${dlt(v,his(p,mk.k),mk.dec)}</td><td>${r?`<span class="mini">${r.line}</span> ${hitTxt(hit(L,mk.k,r.line),1)} ${lean(r)}`:'<span class="dim">·</span>'}</td>`}).join('')}</tr>`).join('')}</tbody></table></div>`:'<p class="note">no rotation player with enough games against the opponent</p>'}</div>`}).join('')||'<p class="note">no games match the filter</p>');
  bindDays(el);$('#hLo').onclick=()=>{G.lo=!G.lo;h2h()};$('#hMin').onchange=()=>{G.h2n=+$('#hMin').value;h2h()};bindPL(el)}""")

# ---- lab: per-market lab with hit rates ----
a = s.index("function lab(){"); b = s.index("function explorer(){")
s = s[:a] + r"""function lab(){const el=$('#players');const mk=STAT[G.lm||'pts']||MK[0];const k=mk.k;
  const ps=J.players.filter(p=>inT(p.team)&&inS(p.slot)&&(p.gp||p.gp_prior)&&(!G.lo||(LINES[p.pid]&&LINES[p.pid][k]))&&(!G.st||p.starter_rate>=.5)).map(p=>{const o=nextGame(p.team);const opp=o?(o.away===p.team?o.home:o.away):'';const r=opp?rankOf(opp,p.slot,k):null;const pj=PJ[p.pid]&&PJ[p.pid][k];const ln=LINES[p.pid]&&LINES[p.pid][k];const L=logsOf(p.pid);const cur=L.filter(l=>l[LC.season]===J.cur);
    const line=ln?ln.line:null;return {p,opp,r,pj,ln,line,h5:line!=null?hit(L.slice(0,5),k,line):null,h10:line!=null?hit(L.slice(0,10),k,line):null,hs:line!=null?hit(cur,k,line):null,ho:line!=null&&opp?hit(L.filter(l=>l[LC.opp]===opp),k,line):null,l5:mean(L.slice(0,5).map(l=>lval(l,k))),vo:opp?mean(L.filter(l=>l[LC.opp]===opp).map(l=>lval(l,k))):null,nvo:opp?L.filter(l=>l[LC.opp]===opp).length:0}})
    .sort((a,b)=>(b.ln?b.ln.edge:-1)-(a.ln?a.ln.edge:-1)||(a.r?a.r.rank:99)-(b.r?b.r.rank:99)||(his(b.p,k)||0)-(his(a.p,k)||0));
  el.innerHTML=`<div class="controls"><span class="chips" id="lbMk">${MK.map(m=>`<button data-k="${m.k}" class="${m.k===k?'on':''}">${m.label}</button>`).join('')}</span><button class="mopen ${G.lo?'on':''}" id="lbLo">lines only</button><button class="mopen ${G.st?'on':''}" id="lbSt">starters</button><span class="note">${ps.length} players · ${mk.label}: season · last season · L5 (trend vs season) · L10 · vs this opponent (games) · the opponent's rank for his slot (${G.src}) · projection · the posted line with the model's lean and edge · hit = his record over that line in the last 5, last 10, this season and against this opponent · sorted by edge, then matchup</span></div>
    <div class="panel wrap-x"><table><thead><tr><th>player</th><th>tm</th><th>slot</th><th>opp</th><th>gp</th><th>min</th><th>st%</th><th>se</th><th>pr</th><th>L5</th><th>L10</th><th>vs opp</th><th>opp rk</th><th>proj</th><th>line</th><th>lean</th><th>hit L5</th><th>hit L10</th><th>hit se</th><th>hit vs</th></tr></thead><tbody>
    ${ps.map(x=>{const p=x.p;const se=p[k];const tr=x.l5!=null&&se!=null?x.l5-se:null;return `<tr><td>${pname(p)}</td><td>${tc(p.team)}</td><td><span class="slot">${p.slot}</span></td><td class="mini">${x.opp?oppOf(p.team):'—'}</td><td class="mini">${p.gp}<span class="dim">/${p.gp_prior}</span></td><td class="mini">${fmt(his(p,'min'),0)}</td><td class="mini">${p.starter_rate!=null?(100*p.starter_rate).toFixed(0):'·'}</td>
      <td class="mono"><b>${fmt(se,mk.dec)}</b></td><td class="mono dim">${fmt(p[k+'_prior'],mk.dec)}</td><td class="mono" data-v="${x.l5??-1}">${fmt(x.l5,mk.dec)} ${tr==null?'':`<span class="${tr>0?'rise':tr<0?'fall':'dim'}" style="font-size:10px">${tr>0?'▲':tr<0?'▼':'='}</span>`}</td><td class="mono">${fmt(p[k+'_l10'],mk.dec)}</td><td class="mono" data-v="${x.vo??-1}">${x.nvo?`${fmt(x.vo,mk.dec)} <span class="mini">(${x.nvo})</span>`:'<span class="dim">·</span>'}</td>
      <td>${x.r?`<span class="hc" style="${gradeStyle(x.r.rank)}">${x.r.rank}</span>`:'·'}</td><td class="mono" title="${x.ln?`market-shrunk ${x.ln.proj} · raw model ${x.ln.raw}`:'raw model'}">${x.ln?x.ln.proj:x.pj?fmt(x.pj.proj,mk.dec):'·'}</td><td class="mono" data-v="${x.line??-1}">${x.line??'<span class="dim">·</span>'}</td><td data-v="${x.ln?x.ln.edge:-1}">${lean(x.ln)}</td>
      <td data-v="${x.h5?x.h5.pct??-1:-1}">${x.h5?hitTxt(x.h5):''}</td><td data-v="${x.h10?x.h10.pct??-1:-1}">${x.h10?hitTxt(x.h10):''}</td><td data-v="${x.hs?x.hs.pct??-1:-1}">${x.hs?hitTxt(x.hs):''}</td><td data-v="${x.ho?x.ho.pct??-1:-1}">${x.ho?hitTxt(x.ho):''}</td></tr>`}).join('')}</tbody></table></div>`;
  el.querySelectorAll('#lbMk button').forEach(b=>b.onclick=()=>{G.lm=b.dataset.k;lab()});$('#lbLo').onclick=()=>{G.lo=!G.lo;lab()};$('#lbSt').onclick=()=>{G.st=!G.st;lab()};bindPL(el)}
""" + s[b:]

# ---- player card: lines + hit rates, splits, sparkline ----
rep("""  const cols=J.stats.filter(s=>s.k!=='pa'&&s.k!=='ra'&&s.k!=='pr');
  return `<h3 style="margin:0 0 8px">""",
    """  const cols=J.stats.filter(s=>s.k!=='pa'&&s.k!=='ra'&&s.k!=='pr');
  const ln=LINES[pid]||{};const cur=L.filter(l=>l[LC.season]===J.cur);const vs=opp?L.filter(l=>l[LC.opp]===opp):[];
  const lines=Object.keys(ln).length?`<div class="panel"><h3>posted lines <span class="f">the books' consensus line, the model's lean and edge, and his record over the line: last 5 · last 10 · this season · last season · vs ${opp||'—'}</span></h3><table><thead><tr><th>market</th><th>line</th><th>proj</th><th>lean</th><th>best</th><th>L5</th><th>L10</th><th>${J.cur}</th><th>${J.prior}</th><th>vs ${opp||'opp'}</th></tr></thead><tbody>${MK.filter(mk=>ln[mk.k]).map(mk=>{const r=ln[mk.k];const pr=L.filter(l=>l[LC.season]===J.prior);return `<tr><td>${mk.label}</td><td class="mono"><b>${r.line}</b></td><td class="mono">${r.proj}</td><td>${lean(r)}</td><td class="mono mini">${amer(r.price)} ${r.book||''}</td><td>${hitTxt(hit(L.slice(0,5),mk.k,r.line))}</td><td>${hitTxt(hit(L.slice(0,10),mk.k,r.line))}</td><td>${hitTxt(hit(cur,mk.k,r.line))}</td><td>${hitTxt(hit(pr,mk.k,r.line))}</td><td>${hitTxt(hit(vs,mk.k,r.line))}</td></tr>`}).join('')}</tbody></table></div>`:'';
  const spk=(()=>{const k=G.lm||PRIMARY;const mk=STAT[k];const R=L.slice(0,15).reverse();if(R.length<3)return '';const vs_=R.map(l=>lval(l,k));const line=ln[k]?ln[k].line:null;const mx=Math.max(...vs_,line||0)||1;const W=420,H=70,bw=W/R.length;
    return `<div class="panel"><h3>last ${R.length} games · ${mk.label}${line!=null?` <span class="f">against the posted line ${line} · green = over</span>`:''}</h3><svg viewBox="0 0 ${W} ${H+14}" width="${W}" height="${H+14}" style="max-width:100%">${R.map((l,i)=>{const v=vs_[i];const h=v/mx*H;return `<rect x="${i*bw+2}" y="${H-h}" width="${bw-4}" height="${h}" fill="${line==null?'var(--acc)':v>line?'var(--green)':v<line?'var(--red)':'var(--dim)'}" opacity=".85"><title>${l[LC.date]} ${l[LC.ha]==='H'?'vs':'@'} ${l[LC.opp]}: ${fmt(v,mk.dec)}</title></rect><text x="${i*bw+bw/2}" y="${H+11}" font-size="8" fill="var(--dim)" text-anchor="middle" font-family="var(--mono)">${l[LC.opp]}</text>`}).join('')}${line!=null?`<line x1="0" x2="${W}" y1="${H-line/mx*H}" y2="${H-line/mx*H}" stroke="#e8b100" stroke-dasharray="3 3"/>`:''}</svg></div>`})();
  const splits=(()=>{const S=[['home',cur.filter(l=>l[LC.ha]==='H')],['away',cur.filter(l=>l[LC.ha]==='A')],['as starter',cur.filter(l=>l[LC.starter])],['off bench',cur.filter(l=>!l[LC.starter])],[`vs ${opp||'—'} (all)`,vs]].filter(x=>x[1].length);if(!S.length)return '';
    return `<div class="panel"><h3>splits <span class="f">this season per game · vs the opponent across all loaded seasons</span></h3><table><thead><tr><th>split</th><th>g</th>${MK.slice(0,5).map(mk=>`<th>${mk.label}</th>`).join('')}<th>MIN</th></tr></thead><tbody>${S.map(([n,R])=>`<tr><td>${n}</td><td class="mono">${R.length}</td>${MK.slice(0,5).map(mk=>`<td class="mono">${fmt(mean(R.map(l=>lval(l,mk.k))),mk.dec)}</td>`).join('')}<td class="mono">${fmt(mean(R.map(l=>+l[LC.min])),1)}</td></tr>`).join('')}</tbody></table></div>`})();
  return `<h3 style="margin:0 0 8px">""")
rep("""next ${opp?oppOf(p.team):'—'}</span></h3>${sum}
    <div class="wrap-x" style="max-height:520px;overflow:auto">""",
    """next ${opp?oppOf(p.team):'—'}</span></h3>${sum}${lines}${spk}${splits}
    <div class="wrap-x" style="max-height:520px;overflow:auto">""")

# ---- router + css ----
rep("function render(){({overview:home,bestpicks,cards,board,lab,explorer,dvp,ratings:ratingsView,props,lines,ledger})[G.sub]();sortableAll();}",
    "function render(){({overview:home,bestpicks,cards,board,h2h,lab,explorer,dvp,ratings:ratingsView,props,lines,ledger})[G.sub]();sortableAll();}")
rep(".mopen:hover{color:var(--txt);border-color:var(--acc)}",
    ".mopen:hover{color:var(--txt);border-color:var(--acc)}.mopen.on{color:#000;background:var(--acc);border-color:var(--acc)}.mplays{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center;font-size:11px;padding:5px 0;border-bottom:1px dotted var(--edge)}.mplays>.mini{color:var(--mute);text-transform:uppercase;letter-spacing:.04em;font-size:9px}.mln{white-space:normal}.mln span{margin-right:6px}")
open(P, 'w', encoding='utf-8').write(s)
print('applied')
