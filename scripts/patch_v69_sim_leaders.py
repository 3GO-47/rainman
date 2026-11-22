"""v69 — Simulations: a Leaders tab. One consolidated view of the week's simulations: the best projected stat line at every
position (top 8 QB / RB / WR / TE with the full line), and the most likely touchdown scorers (any TD, 2+ TD) plus the QBs
most likely to throw 2+ / 3+. Rank by points, yards, touchdowns or volume; games already played can be hidden. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/build_simulations_page.py'
s = open(P, encoding='utf-8').read()
if 'function renderTop' in s:
    print('v69 already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:110])
    s = s.replace(old, new)
rep("const TABS=[['slate','Slate','cards · box scores · key numbers'],", "const TABS=[['slate','Slate','cards · box scores · key numbers'],['top','Leaders','best lines · TD scorers'],")
rep(".card{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:12px 14px}",
    ".card{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:12px 14px}\n"
    ".tgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:12px;margin-top:12px}.tgrid table.st{width:100%}.tgrid td.ln{white-space:normal;text-align:left;color:var(--dim);line-height:1.45}.tgrid td.ln b{color:var(--fg)}.tgrid td.rk{color:var(--dim);width:22px}\n"
    ".tbar{display:inline-block;width:110px;max-width:32vw;height:8px;background:var(--s3);border-radius:4px;vertical-align:middle;margin-right:8px;overflow:hidden}.tbar i{display:block;height:100%;border-radius:4px;background:rgba(46,204,113,.85)}.tbar.b2 i{background:rgba(88,166,255,.85)}")
rep("$('#vMin').onchange=renderVol;renderVol();",
    r"""$('#vMin').onchange=renderVol;renderVol();
/* ---- leaders: the best simulated line at every position and the likeliest touchdown scorers ---- */
function renderTop(){const hideP=$('#tHide').checked,by=$('#tBy').value;
  const played=new Set(G.filter(g=>g.actual&&Object.values(g.actual).some(v=>v!=null)).map(g=>g.game_id));
  const L=ALLP.filter(p=>p.inj!=='-1'&&(!hideP||!played.has(p.gid))),F=p=>fanOf(p)||{};
  const KEY={pts:p=>F(p).mean||0,yds:p=>p.pos==='QB'?p.pass_yds:(p.rush_yds||0)+(p.rec_yds||0),td:p=>p.pos==='QB'?p.pass_td+(p.rush_td||0):(p.rush_td||0)+(p.rec_td||0),vol:p=>p.pos==='QB'?p.att:posOf(p)==='RB'?(p.car||0)+(p.rec||0):(p.rec||0)};
  const KL={pts:SC.toUpperCase()+' points',yds:'yards',td:'touchdowns',vol:'volume (attempts · touches · catches)'},KF={pts:f1,yds:f0,td:f2,vol:f1};
  const top=(arr,f,n)=>arr.slice().sort((a,b)=>f(b)-f(a)).slice(0,n);
  const line=p=>p.pos==='QB'?`<b>${f0(p.pass_yds)}</b> pass yds · <b>${f1(p.pass_td)}</b> TD · ${f1(p.int)} int · <b>${f0(p.rush_yds)}</b> rush yds`
    :posOf(p)==='RB'?`<b>${f0(p.rush_yds)}</b> rush yds on ${f0(p.car)} carries · <b>${f1(p.rec)}</b> catches · <b>${f0(p.rec_yds)}</b> rec yds · <b>${f2(p.td)}</b> TD`
    :`<b>${f1(p.rec)}</b> catches on ${f1(p.tgt)} targets · <b>${f0(p.rec_yds)}</b> yds · <b>${f2(p.td)}</b> TD`;
  const who=p=>`<td class="n"><b>${esc(p.name)}</b>${p.inj==='0'?' <span class="q">Q</span>':''}<br><span class="slot">${logo(p.team)} ${p.team} ${p.home?'vs':'@'} ${p.opp}</span></td>`;
  const bar=(v,mx,cls)=>`<span class="tbar ${cls||''}"><i style="width:${Math.round(100*Math.min(1,v/Math.max(mx,1e-9)))}%"></i></span>`;
  // the strip: the best line at each position and the likeliest scorer
  const best=POS.map(ps=>top(L.filter(p=>posOf(p)===ps),KEY[by],1)[0]).filter(Boolean),sk=L.filter(p=>p.pos!=='QB'&&p.p_td!=null),tdb=top(sk,p=>p.p_td,1)[0];
  $('#tKpis').innerHTML=best.map(p=>`<div class="kpi"><span>top ${posOf(p)} · ${KL[by].split(' (')[0]}</span><b>${esc(p.name)}</b><small>${p.team} ${p.home?'vs':'@'} ${p.opp} · ${line(p).replace(/<\/?b>/g,'')}</small></div>`).join('')+(tdb?`<div class="kpi"><span>likeliest to score</span><b>${esc(tdb.name)}</b><small>${tdb.team} ${tdb.home?'vs':'@'} ${tdb.opp} · ${pc(tdb.p_td)} any TD · ${pc(tdb.p_2td)} two or more</small></div>`:'');
  $('#tPos').innerHTML=POS.map(ps=>{const R=top(L.filter(p=>posOf(p)===ps),KEY[by],8);if(!R.length)return '';const mx=KEY[by](R[0]),pm=R.map(p=>F(p).mean||0);
    return `<div class="card"><h2 style="margin-top:0">${ps} · best projected lines <span>ranked on ${KL[by]} · the line is the average of the simulations</span></h2><table class="st"><thead><tr><th>#</th><th>player</th><th>projected line</th><th>${by==='pts'?SC.toUpperCase():KL[by].split(' (')[0]}</th><th>${by==='pts'?'floor – ceiling':SC.toUpperCase()}</th><th>${ps==='QB'?'2+ pass TD':'any TD'}</th></tr></thead><tbody>
      ${R.map((p,i)=>`<tr class="pr" data-i="${p.i}"><td class="rk">${i+1}</td>${who(p)}<td class="ln">${line(p)}</td><td data-v="${KEY[by](p)}">${bar(KEY[by](p),mx)}<b>${KF[by](KEY[by](p))}</b></td><td data-v="${F(p).mean||0}">${by==='pts'?`${f0(F(p).p10)} – ${f0(F(p).p90)}`:`<span style="${heatPct(F(p).mean||0,pm)}">${f1(F(p).mean)}</span>`}</td><td data-v="${ps==='QB'?p.p_2td:p.p_td}" style="${heatP(ps==='QB'?p.p_2td:p.p_td,.5,.3)}">${pc(ps==='QB'?p.p_2td:p.p_td)}</td></tr>`).join('')}</tbody></table></div>`}).join('');
  const T=top(sk,p=>p.p_td,15),Q=top(L.filter(p=>p.pos==='QB'),p=>p.p_2td||0,8);
  $('#tTd').innerHTML=`<div class="card"><h2 style="margin-top:0">most likely to score <span>share of the ${J.sims.n.toLocaleString()} simulations with at least one rushing or receiving touchdown</span></h2><table class="st"><thead><tr><th>#</th><th>player</th><th>any TD</th><th>two or more</th><th>TDs a game</th></tr></thead><tbody>
      ${T.map((p,i)=>`<tr class="pr" data-i="${p.i}"><td class="rk">${i+1}</td>${who(p)}<td data-v="${p.p_td}">${bar(p.p_td,1)}<b>${pc(p.p_td)}</b></td><td data-v="${p.p_2td||0}" style="${heatP(p.p_2td,.15,.15)}">${pc(p.p_2td)}</td><td data-v="${p.td}">${f2(p.td)}</td></tr>`).join('')}</tbody></table></div>
    <div class="card"><h2 style="margin-top:0">quarterbacks · passing touchdowns <span>share of simulations with two or more, and three or more</span></h2><table class="st"><thead><tr><th>#</th><th>player</th><th>2+ pass TD</th><th>3+</th><th>pass TDs a game</th><th>rushing TD</th></tr></thead><tbody>
      ${Q.map((p,i)=>`<tr class="pr" data-i="${p.i}"><td class="rk">${i+1}</td>${who(p)}<td data-v="${p.p_2td||0}">${bar(p.p_2td||0,1,'b2')}<b>${pc(p.p_2td)}</b></td><td data-v="${p.p_3td||0}" style="${heatP(p.p_3td,.15,.15)}">${pc(p.p_3td)}</td><td data-v="${p.pass_td}">${f2(p.pass_td)}</td><td data-v="${p.p_td||0}">${pc(p.p_td)}</td></tr>`).join('')}</tbody></table></div>`;
  $$('#t-top tr.pr').forEach(tr=>tr.onclick=()=>{const p=ALLP[+tr.dataset.i];const ex=tr.nextElementSibling;if(ex&&ex.classList.contains('dx')){ex.remove();return}const d=document.createElement('tr');d.className='dx';d.innerHTML=`<td colspan="${tr.cells.length}" style="white-space:normal;padding:0">${pdetail(p)}</td>`;tr.after(d);wireCalc(d,p)});
  $('#tNote').textContent=played.size?(hideP?`${played.size} game${played.size===1?'':'s'} already played ${played.size===1?'is':'are'} left out`:`includes ${played.size} game${played.size===1?'':'s'} already played`):''}
$('#tBy').onchange=renderTop;$('#tHide').onchange=renderTop;renderTop();""")
rep("{if(i==='pSc'){SC=$('#pSc').value;renderSlate();renderVol()}renderPlayers()}", "{if(i==='pSc'){SC=$('#pSc').value;renderSlate();renderVol();renderTop()}renderPlayers()}")
rep('<section class="tab" id="t-players">',
    '<section class="tab" id="t-top">\n<h2>leaders <span>the week in one view: the best simulated stat line at every position, then who is most likely to score · click any row for his full distribution and the over / under calculator</span></h2>\n'
    '<div class="ctl"><label>rank the lines on<select id="tBy"><option value="pts" selected>fantasy points</option><option value="yds">yards</option><option value="td">touchdowns</option><option value="vol">volume</option></select></label><label><input type="checkbox" id="tHide" checked> leave out games already played</label><span class="note" id="tNote"></span></div>\n'
    '<div id="tKpis" class="kpis"></div>\n<div id="tPos" class="tgrid"></div>\n<div id="tTd" class="tgrid"></div>\n</section>\n\n<section class="tab" id="t-players">')
open(P, 'w', encoding='utf-8').write(s); print('v69 applied')
