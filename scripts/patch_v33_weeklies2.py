"""v33 — Weeklies v2 and Category Grid v2 as new F6 TEST sub-tabs (the originals stay). Plain language, visuals first,
every tile / bar / row opens its history (v32 thSeq/thReg), both follow the global week selector. Additive; rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function weeklies2()' in s:
    print('already applied'); sys.exit(0)
assert 'function thSeq(' in s, 'v32 must be applied first'

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:90])); s = s.replace(old, new)

# ---------- CSS ----------
rep("/* v32 tile histories */", "/* v33 Weeklies v2 / Category Grid v2 */"
    ".w2bar{display:grid;grid-template-columns:200px minmax(0,1fr) 54px 70px;gap:10px;align-items:center;padding:4px 0;font-size:12.5px;cursor:pointer;border-bottom:1px solid #141414}.w2bar:hover{background:#ffffff06}"
    ".w2bar .l{color:var(--txt);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.w2bar .l i{display:block;font:10px var(--mono);color:var(--dim);font-style:normal}"
    ".w2bar .b{position:relative;height:12px;background:#111;border-radius:2px}.w2bar .b i{position:absolute;left:0;top:0;bottom:0;border-radius:2px}.w2bar .b u{position:absolute;top:-3px;bottom:-3px;width:2px;background:#bbb;z-index:2}"
    ".w2bar b{font:700 13px var(--mono);text-align:right}.w2bar em{font:10.5px var(--mono);color:var(--dim);font-style:normal;text-align:right}"
    ".w2sub{margin:12px 0 4px;font:600 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2)}"
    ".w2gh,.w2row{display:grid;grid-template-columns:200px minmax(0,1fr) 120px;gap:10px;align-items:center;padding:4px 0;font-size:12.5px}.w2row{cursor:pointer;border-bottom:1px solid #141414}.w2row:hover{background:#ffffff06}"
    ".w2gh{font:600 9.5px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--dim2)}.w2gh .sq i{width:18px;text-align:center;font-style:normal;color:var(--dim)}"
    ".w2row .l{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.w2row .l .tg{font:600 9px var(--mono);color:var(--dim);border:1px solid var(--edge);border-radius:3px;padding:0 4px;margin-left:4px;font-style:normal}"
    ".w2row .sq,.w2gh .sq{display:flex;gap:3px}.w2row .sq i{width:18px;height:14px;border-radius:2px;background:#222}.w2row .sq i.w{background:var(--green)}.w2row .sq i.l{background:var(--red)}.w2row .sq i.o{background:#2a2a2a}"
    ".w2row .r{text-align:right;font:12px var(--mono)}.w2row .r em{font-style:normal;font-size:10px;margin-left:5px;padding:1px 5px;border-radius:3px;border:1px solid var(--edge);color:var(--dim)}.w2row .r em.g{color:var(--green);border-color:var(--green)}.w2row .r em.r{color:var(--red);border-color:var(--red)}.w2row .r em.a{color:#e8b100;border-color:#e8b100}"
    ".g2cat{display:grid;grid-template-columns:150px minmax(0,1fr) 60px 60px;gap:10px;align-items:center;padding:4px 0;font-size:12.5px;cursor:pointer;border-bottom:1px solid #141414}.g2cat:hover{background:#ffffff06}.g2cat .b{position:relative;height:12px;background:#111;border-radius:2px}.g2cat .b i{position:absolute;left:0;top:0;bottom:0;background:var(--green);border-radius:2px}.g2cat b{font:700 13px var(--mono);text-align:right}.g2cat em{font:10.5px var(--mono);color:var(--dim);font-style:normal;text-align:right}"
    ".g2sq{display:inline-flex;gap:2px;vertical-align:middle}.g2sq i{width:9px;height:12px;border-radius:1px;background:#262626}.g2sq i.on{background:var(--green)}"
    "table.g2t td.n{text-align:right;white-space:nowrap}table.g2t th{white-space:nowrap}@media(max-width:840px){.w2bar{grid-template-columns:120px minmax(0,1fr) 48px}.w2bar em{display:none}.w2gh,.w2row{grid-template-columns:120px minmax(0,1fr) 90px}.g2cat{grid-template-columns:110px minmax(0,1fr) 50px}.g2cat em{display:none}}\n"
    "/* v32 tile histories */")

# ---------- registry, panels, boot ----------
rep("{id:'wkgrid',label:'Category Grid',desc:'", "{id:'weeklies2',label:'Weeklies v2',desc:'the touchdown lookback, reworked: for the week picked up top, what called the touchdowns (every signal\\'s hit rate against the field as one ranked bar chart), which signals are reliable week after week (a square per week), who scored and who was called but didn\\'t \\u2014 every tile, bar and row opens its numbers',c:'test',sub:'weeklies2'},\n   {id:'wkgrid',label:'Category Grid',desc:'")
rep("c:'test',sub:'wkgrid'},", "c:'test',sub:'wkgrid'},\n   {id:'wkgrid2',label:'Category Grid v2',desc:'the category board, reworked: the categories that keep beating the field as bars, then one ranked list of who carries them into the week picked up top with his TD chance and, once played, whether he scored',c:'test',sub:'wkgrid2'},")
rep("<div id=\"wkgrid\" hidden></div>", "<div id=\"wkgrid\" hidden></div><div id=\"weeklies2\" hidden></div><div id=\"wkgrid2\" hidden></div>")
rep("['meta','metaprop','weeklies','wkgrid','tdpicks','labgrid','gameview','tdgridTest','h2h','markets2','ddelta','card2','splits','api','injuries','dev','backtest']",
    "['meta','metaprop','weeklies','weeklies2','wkgrid','wkgrid2','tdpicks','labgrid','gameview','tdgridTest','h2h','markets2','ddelta','card2','splits','api','injuries','dev','backtest']")
rep("['test',wkGrid],", "['test',wkGrid],['test',weeklies2],['test',wkGrid2],")
rep(" wkgrid:{what:'The Weeklies categories, every recorded week at once.'",
    " weeklies2:{what:'What called the touchdowns, one week at a time.',how:['the four tiles are the week in one glance \\u2014 click any for the week-by-week','bars: how often the players carrying each signal scored \\u2014 the white line is the field, green beat it by 10%+ \\u2014 click a bar for the players','the square grid: one square per week, green = the signal beat the field that week \\u2014 a row of green is a signal to trust, a mix is noise','fades are signals that point away from a touchdown; for those green means the fade held','follows the week picked up top; a week that is not graded yet falls back to the newest graded one']},\n wkgrid2:{what:'Who carries the reliable categories into the week.',how:['bars: the categories that beat the field most consistently across the recorded weeks before the week picked \\u2014 a square per week','the list: every starter in view carrying at least one category \\u2014 filled squares are the categories he carries, REC is how often he scored when he carried them before, TD % is the TD Picks model','\\u2713 / \\u2717 appear once the week is played','every column sorts, every tile opens its week-by-week, click a name for his card']},\n wkgrid:{what:'The Weeklies categories, every recorded week at once.'")

# ---------- the views ----------
views = r'''
/* ---------------- v33: Weeklies v2 + Category Grid v2 (F6 TEST) ---------------- */
const W2CORE=new Set(['QB1','RB1','RB2','WR1','WR2','WR3','TE1']);
const w2keep=x=>W2CORE.has(x.slot==='WR4+'?'WR4':x.slot)&&inP(x.pos);
const w2res=x=>x.td>0?'<b style="color:var(--green)">✓</b>':'<b style="color:var(--red)">✗</b>';
const w2won=(s,x)=>x.hr!=null&&(s.kind==='neg'?wkR(x.lift)<=.9:wkR(x.lift)>=1.1);
const w2opp=x=>x.raw?oppcell(x.raw):(x.opp?tcell(x.opp):'');
function weeklies2(){const el=$('#weeklies2');if(!el)return;
  const SES=ALL_SE.slice().reverse();let S=SES.find(se=>wkFeat(se).weeks.length)||SES[0];
  el.innerHTML=`<div class="controls"><span class="chips" id="w2Se">${SES.map(se=>`<button data-s="${se}" class="${se===S?'on':''}">${se}</button>`).join('')}</span><span class="note mini" id="w2Note"></span></div>
    <div class="wktiles" id="w2Tiles" data-mg="1"></div>
    <div class="wk2b"><div class="panel"><h3 id="w2Bh"></h3><div id="w2Bars"></div></div><div class="panel"><h3 id="w2Gh"></h3><div id="w2Grid"></div></div></div>
    <div class="wk2b"><div class="panel"><h3 id="w2Sh"></h3><div id="w2Sc"></div></div><div class="panel"><h3 id="w2Mh"></h3><div id="w2Miss"></div></div></div>`;
  function render(){
    const F=wkFeat(S),SG=wkSigs();
    if(!F.weeks.length){$('#w2Note').textContent='no graded week in this season yet';['w2Tiles','w2Bars','w2Grid','w2Sc','w2Miss'].forEach(id=>$('#'+id).innerHTML='');return}
    const W=F.weeks.includes(G.week)?G.week:Math.max(...F.weeks.filter(w=>w<=G.week).concat([F.weeks[0]]));
    const AL=F.weeks.filter(w=>w<=W).map(w=>wkStats(F,w,w2keep,SG)),st=AL[AL.length-1];
    $('#w2Note').innerHTML=W===G.week?`week ${W} · ${S} · ${st.P.length} starters in view (QB1, RB1–2, WR1–3, TE1)`:`week ${G.week} isn't graded yet — showing week ${W}, the newest graded week of ${S}`;
    const live=new Set(SG.filter(s=>AL.some(a=>a.sig.find(y=>y.id===s.id).n>0)).map(s=>s.id));
    const ok=st.sig.filter(s=>live.has(s.id)&&s.n>=st.minN&&s.hr!=null);
    const pos=ok.filter(s=>s.kind==='pos').sort((a,b)=>b.lift-a.lift),neg=ok.filter(s=>s.kind==='neg').sort((a,b)=>a.lift-b.lift);
    const rel=SG.filter(s=>live.has(s.id)).map(s=>{const cells=AL.map(a=>{const x=a.sig.find(y=>y.id===s.id);return x.n<a.minN||x.hr==null?0:(w2won(s,x)?1:-1)});const qw=cells.filter(c=>c).length,bw=cells.filter(c=>c>0).length;
      const n=AL.reduce((t,a)=>t+a.sig.find(y=>y.id===s.id).n,0),k=AL.reduce((t,a)=>t+a.sig.find(y=>y.id===s.id).k,0);return {s,cells,qw,bw,n,k,hr:n?k/n:null}}).filter(r=>r.qw).sort((a,b)=>b.bw/b.qw-a.bw/a.qw||b.qw-a.qw||(b.hr||0)-(a.hr||0));
    const need=Math.max(2,Math.ceil(AL.length/2)),steady=rel.filter(r=>r.s.kind==='pos'&&r.qw>=need)[0],fade=rel.filter(r=>r.s.kind==='neg'&&r.qw>=2&&r.bw/r.qw>=.5)[0];
    const sigRows=s=>()=>({title:esc(s.lbl)+' · week by week',sub:esc(s.long||'')+' · '+S,cols:[{l:'week',g:false},{l:'carried it',g:false},{l:'scored',g:false},'hit rate','field',{l:'vs the field'},{l:'who scored',g:false}],
      rows:AL.map(a=>{const x=a.sig.find(y=>y.id===s.id);return Object.assign([a.w,x.n,x.k,x.hr!=null?{v:x.hr,h:wkPct(x.hr)}:null,{v:a.base,h:wkPct(a.base)},x.lift!=null?{v:x.lift,h:wkX(x.lift)}:null,a.P.filter(s.f).filter(p=>p.td>0).slice(0,4).map(p=>pshort(p.name)).join(', ')],{hi:a.w===W})})});
    const who=s=>()=>({title:esc(s.lbl)+` · week ${W}`,sub:`${esc(s.long||'')} · everyone carrying it, scorers first`,cols:['player','team',{l:'slot',g:false},{l:'opp',g:false},{l:'TDs',g:false},{l:'signals',t:'how many of the eight core signals he carried'},{l:'scored',g:false}],
      rows:st.P.filter(s.f).sort((a,b)=>b.td-a.td||b.cs-a.cs).map(x=>[pn(x.name,x.team,true),tcell(x.team),slotchip(x.slot),w2opp(x),x.td,x.cs,w2res(x)])});
    const wkRows=()=>({title:`${S} · week by week`,sub:'touchdowns, scorers and the best signal each week',cols:[{l:'week',g:false},'TDs',{l:'scored / field'},'field rate',{l:'best signal',g:false}],
      rows:AL.map(a=>{const b=a.sig.filter(s=>live.has(s.id)&&s.n>=a.minN&&s.hr!=null&&s.kind==='pos').sort((x,y)=>y.lift-x.lift)[0];return Object.assign([a.w,a.tds,{v:a.sc.length,h:`${a.sc.length} / ${a.P.length}`},{v:a.base,h:wkPct(a.base)},b?`${esc(b.lbl)} <b>${wkPct(b.hr)}</b>`:'—'],{hi:a.w===W})})});
    $('#w2Tiles').innerHTML=thSeq(wkTile(`week ${W} · touchdowns`,String(st.tds),`${st.sc.length} of ${st.P.length} starters scored · field ${wkPct(st.base)}`)
      +(pos[0]?wkTile('best signal this week',esc(pos[0].lbl),`<b style="color:var(--green)">${wkPct(pos[0].hr)}</b> scored · ${wkX(pos[0].lift)} the field · ${pos[0].n} players`,'g',true):'')
      +(steady?wkTile('most reliable this season',esc(steady.s.lbl),`beat the field <b>${steady.bw} of ${steady.qw}</b> weeks · ${wkPct(steady.hr)} scored`,'g',true):'')
      +(fade?wkTile('best fade',esc(fade.s.lbl),`only <b>${wkPct(fade.hr)}</b> scored · held ${fade.bw} of ${fade.qw} weeks`,'r',true):''),
      [wkRows,pos[0]?sigRows(pos[0]):null,steady?sigRows(steady.s):null,fade?sigRows(fade.s):null].filter(Boolean));
    const mx=Math.max(.5,...ok.map(s=>s.hr))*1.05,good=s=>s.kind==='neg'?wkR(s.lift)<=.9:wkR(s.lift)>=1.1,bad=s=>s.kind==='neg'?wkR(s.lift)>=1.1:wkR(s.lift)<=.9;
    const bar=s=>`<div class="w2bar" data-th="${thReg(who(s))}" title="click for everyone carrying it"><span class="l">${esc(s.lbl)}<i>${s.n} players</i></span><span class="b"><u style="left:${(100*st.base/mx).toFixed(1)}%" title="the field: ${wkPct(st.base)}"></u><i style="width:${(100*s.hr/mx).toFixed(1)}%;background:${good(s)?'var(--green)':bad(s)?'var(--red)':'#6b6b6b'}"></i></span><b style="color:${good(s)?'var(--green)':bad(s)?'var(--red)':'var(--txt)'}">${wkPct(s.hr)}</b><em>${s.k} of ${s.n}</em></div>`;
    $('#w2Bh').innerHTML=`what called the touchdowns — week ${W} <span class="f">how often the players carrying each signal scored · the white line is the field (${wkPct(st.base)}) · green = beat it by 10%+, red = fell short · click a bar for the players</span>`;
    $('#w2Bars').innerHTML=(pos.map(bar).join('')||'<p class="note mini">no signal had enough players this week</p>')+(neg.length?`<div class="w2sub">fades — signals that point away from a touchdown · green = the fade held</div>${neg.map(bar).join('')}`:'');
    const verdict=r=>r.qw<2?['thin sample','']:r.bw/r.qw>=.67?[r.s.kind==='neg'?'trust the fade':'trust','g']:r.bw/r.qw>=.5?['lean on','a']:['noise','r'];
    $('#w2Gh').innerHTML=`reliable, or noise? — ${S}, weeks ${AL[0].w}–${W} <span class="f">one square per week: green = beat the field by 10%+ that week, red = didn't, grey = too few players · a row of green is a signal to trust · click a row for the numbers</span>`;
    $('#w2Grid').innerHTML=`<div class="w2gh"><span>signal</span><span class="sq">${AL.map(a=>`<i title="week ${a.w}">${a.w}</i>`).join('')}</span><span>beat the field</span></div>`+rel.map(r=>{const [v,t]=verdict(r);
      return `<div class="w2row" data-th="${thReg(sigRows(r.s))}"><span class="l">${esc(r.s.lbl)}${r.s.kind==='neg'?' <i class="tg">fade</i>':''}</span><span class="sq">${r.cells.map((c,i)=>`<i class="${c>0?'w':c<0?'l':'o'}" title="week ${AL[i].w}"></i>`).join('')}</span><span class="r"><b style="color:${r.bw/r.qw>=.67?'var(--green)':r.bw/r.qw<.5?'var(--red)':'var(--txt)'}">${r.bw} / ${r.qw}</b><em class="${t}">${v}</em></span></div>`}).join('');
    const sc=st.P.filter(x=>x.td>0).sort((a,b)=>b.td-a.td||b.cs-a.cs),miss=st.P.filter(x=>x.td===0&&x.cs>=4).sort((a,b)=>b.cs-a.cs).slice(0,20);
    const chip=x=>`<span class="wkpc ${x.td>0?'w':'l'}">${pn(x.name,x.team,true)}<i>${x.td>1?x.td+' TD':x.td===1?'TD':''}${x.td>0&&x.cs?' · ':''}${x.cs?x.cs+' sig':''}</i></span>`;
    $('#w2Sh').innerHTML=`who scored — week ${W} <span class="f">${sc.length} starters · "sig" = how many of the eight core signals pointed at him before kickoff · click a name for his card</span>`;
    $('#w2Sc').innerHTML=`<div class="wkpcs">${sc.map(chip).join('')||'<span class="mini dim">nobody yet</span>'}</div>`;
    $('#w2Mh').innerHTML=`called, but no touchdown <span class="f">starters carrying four or more core signals who didn't score · the ones the signals got wrong</span>`;
    $('#w2Miss').innerHTML=`<div class="wkpcs">${miss.map(chip).join('')||'<span class="mini dim">none</span>'}</div>`;
    logoize(el)}
  $('#w2Se').querySelectorAll('button').forEach(b=>b.onclick=()=>{S=+b.dataset.s;$('#w2Se').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render()});
  render();RR.push(render)}

function wkGrid2(){const el=$('#wkgrid2');if(!el)return;
  el.innerHTML=`<div class="controls"><span class="note mini" id="g2Note"></span></div><div class="wktiles" id="g2Tiles" data-mg="1"></div>
    <div class="wk2b"><div class="panel"><h3 id="g2Ch"></h3><div id="g2Cats"></div></div><div class="panel"><h3 id="g2Ph"></h3><div id="g2Picks"></div></div></div>
    <div class="panel"><h3 id="g2Th"></h3><div id="g2Tbl"></div></div>`;
  let sortK='cat',sortA=false;
  function render(){
    const F=wkFeat(LAST_SE),SG=wkSigs();if(!F.weeks.length){$('#g2Note').textContent='no graded week yet';return}
    const W0=Math.max(2,G.week),D=wgData(W2CORE,'cur',null,W0),R=D.R.filter(x=>inP(x.pos)),B=D.best.filter(x=>inP(x.pos)),gr=R.filter(x=>x.done),gk=gr.filter(x=>x.done.td>0).length,c3=R.filter(x=>x.cat>=3).length,top=D.PK[0];
    const played=W0<=Math.max(...F.weeks);$('#g2Note').innerHTML=`week ${W0}${played?' · played':gr.length?' · grading':' · ahead'} · ${R.length} starters in view · categories judged on ${esc(D.lbl)}`;
    const cat=r=>()=>({title:esc(r.s.lbl)+' · week by week',sub:esc(r.s.long||'')+' · green squares = beat the field by 10%+ that week',cols:[{l:'week',g:false},{l:'carried it',g:false},{l:'scored',g:false},'hit rate','field',{l:'vs the field'},{l:'who scored',g:false}],
      rows:D.Wk.map(w=>{const a=wkStats(F,w,w2keep,SG),x=a.sig.find(y=>y.id===r.s.id);return [w,x.n,x.k,x.hr!=null?{v:x.hr,h:wkPct(x.hr)}:null,{v:a.base,h:wkPct(a.base)},x.lift!=null?{v:x.lift,h:wkX(x.lift)}:null,a.P.filter(r.s.f).filter(p=>p.td>0).slice(0,4).map(p=>pshort(p.name)).join(', ')]})});
    const hist=()=>{const wks=F.weeks.concat([Math.max(...F.weeks)+1]).filter(w=>w>=2);
      return {title:'Category Grid v2 · week by week',sub:'each week judged only from the weeks before it · the week on screen is tinted',cols:[{l:'week',g:false},{l:'in view',g:false},{l:'most consistent',g:false},'carry 3+',{l:'top pick',g:false},{l:'graded',t:'listed players who scored'},{l:'field'}],
        rows:wks.map(w=>{const d=wgData(W2CORE,'cur',null,w),R2=d.R.filter(x=>inP(x.pos)),B2=d.best.filter(x=>inP(x.pos)),g2=R2.filter(x=>x.done),k2=g2.filter(x=>x.done.td>0).length,t2=d.PK[0];
          return Object.assign([w,R2.length,t2?esc(t2.s.lbl):'—',R2.filter(x=>x.cat>=3).length,B2[0]?pn(B2[0].name,B2[0].team,true)+(B2[0].done?' '+w2res(B2[0].done):''):'—',g2.length?{v:k2/g2.length,h:`${k2} / ${g2.length} · ${wkPct(k2/g2.length)}`}:null,d.base!=null?{v:d.base,h:wkPct(d.base)}:null],{hi:w===W0})})}};
    $('#g2Tiles').innerHTML=thSeq(wkTile(`week ${W0}${played?' · played':gr.length?' · grading':' · ahead'}`,String(R.length),'starters carrying at least one category')
      +(top?wkTile('most consistent category',esc(top.s.lbl),`beat the field ${top.bw} of ${top.qw} weeks · ${wkX(top.lift)}`,'g',true):'')
      +wkTile('carry three or more',String(c3),'starters stacking 3+ reliable categories',c3?'g':'')
      +(B[0]?wkTile('top pick',esc(pshort(B[0].name)),`${B[0].cat} categories${B[0].tp?' · TD chance '+Math.round(100*B[0].tp.p)+'%':''}${B[0].done?' · '+(B[0].done.td>0?'scored':'no TD'):''}`,'g',true):'')
      +wkTile('graded',gr.length?`${gk}<span class="dim"> / ${gr.length}</span>`:'—',gr.length?`scored · ${wkPct(gk/gr.length)} vs field ${wkPct(D.base)}`:'✓ / ✗ land as the games are played',gr.length&&D.base?(gk/gr.length>=D.base*1.1?'g':gk/gr.length<=D.base*.9?'r':''):''),
      [hist,...(top?[cat(top)]:[]),hist,...(B[0]?[hist]:[]),hist]);
    const PKs=D.PK.slice().sort(wgRank),fad=D.fades.slice(0,3);
    const cbar=(r,tone)=>`<div class="g2cat" data-th="${thReg(cat(r))}" title="click for the week-by-week"><span>${esc(r.s.lbl)}</span><span class="b"><i style="width:${(100*r.bw/Math.max(1,r.qw)).toFixed(0)}%;background:${tone==='r'?'var(--red)':'var(--green)'}"></i></span><b>${r.bw}/${r.qw}</b><em>${wkX(r.lift)}</em></div>`;
    $('#g2Ch').innerHTML=`the categories that keep working <span class="f">weeks beaten the field by 10%+ over the weeks qualified (${esc(D.lbl)}) · × = scored vs the field overall · click for the numbers</span>`;
    $('#g2Cats').innerHTML=(PKs.map(r=>cbar(r,'g')).join('')||'<p class="note mini">no category has beaten the field consistently yet</p>')+(fad.length?`<div class="w2sub">fades — carrying these has meant fewer touchdowns</div>${fad.map(r=>cbar(r,'r')).join('')}`:'');
    const sq=x=>`<span class="g2sq" title="${PKs.filter(r=>x.cells[r.s.id]&&x.cells[r.s.id].now).map(r=>r.s.lbl).join(' · ')||'none'}">${PKs.map(r=>`<i class="${x.cells[r.s.id]&&x.cells[r.s.id].now?'on':''}"></i>`).join('')}</span>`;
    $('#g2Ph').innerHTML=`best picks — week ${W0} <span class="f">most reliable categories carried in, then the TD Picks chance · click a name for his card</span>`;
    $('#g2Picks').innerHTML=`<div class="wkpcs">${B.slice(0,16).map(x=>`<span class="wkpc ${x.done?(x.done.td>0?'w':'l'):''}">${pn(x.name,x.team,true)}<i>${x.cat} cat${x.tp?' · '+Math.round(100*x.tp.p)+'%':''}</i>${x.done?`<b>${x.done.td>0?'✓':'✗'}</b>`:''}</span>`).join('')||'<span class="mini dim">nobody carries one in</span>'}</div>`;
    const V={player:x=>x.name,team:x=>x.team,pos:x=>x.pos,opp:x=>x.opp||'zz',cat:x=>x.cat,rec:x=>wgRec(x)??-1,hn:x=>x.hn,tp:x=>wgTp(x)??-1,res:x=>x.done?x.done.td:-1};
    const L=R.filter(x=>x.cat>0).sort((a,b)=>{const u=V[sortK](a),v=V[sortK](b);return (u<v?-1:u>v?1:0)*(sortA?1:-1)||b.cat-a.cat||(wgTp(b)??-1)-(wgTp(a)??-1)});
    const th=(k,l,t)=>`<th data-k="${k}" title="${t||''}" style="cursor:pointer">${l}${sortK===k?(sortA?' ▲':' ▼'):''}</th>`;
    const rk=(v,n)=>v==null?'<span class="dim">·</span>':`<span class="badge" style="${gradeStyle(n-Math.round(v*(n-1)),n)}">${wkPct(v)}</span>`;
    $('#g2Th').innerHTML=`everyone carrying a category — week ${W0} <span class="f">${L.length} starters · squares = the categories he carries (hover for names) · REC = how often he scored when he carried them in earlier weeks · every column sorts</span>`;
    $('#g2Tbl').innerHTML=L.length?`<div class="tscroll"><table class="fx g2t"><thead><tr>${th('player','player')}${th('team','tm')}${th('pos','pos')}${th('opp','opp')}${th('cat','categories','how many reliable categories he carries in')}${th('rec','REC','scored in k of n earlier games where he carried one')}${th('tp','TD %','TD Picks: his chance to score')}${th('res','result')}</tr></thead><tbody>
      ${L.map(x=>`<tr><td>${pn(x.name,x.team,true)}</td><td>${tcell(x.team)}</td><td style="color:${POSC[x.pos]||'inherit'}">${x.pos}</td><td>${w2opp(x)}</td><td class="n" data-v="${x.cat}">${sq(x)} <b>${x.cat}</b></td><td class="n" data-v="${wgRec(x)??''}">${x.hn?`${rk(wgRec(x),NT)} <span class="mini">${x.hk}/${x.hn}</span>`:'<span class="dim">·</span>'}</td><td class="n" data-v="${wgTp(x)??''}">${x.tp?`<b style="color:${wgTpc(x.tp.p)}">${Math.round(100*x.tp.p)}%</b>`:'<span class="dim">·</span>'}</td><td>${x.done?w2res(x.done):'<span class="dim">—</span>'}</td></tr>`).join('')}</tbody></table></div>`:'<p class="note mini">nobody in view carries a reliable category into this week</p>';
    $('#g2Tbl').querySelectorAll('th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(sortK===k)sortA=!sortA;else{sortK=k;sortA=['player','team','pos','opp'].includes(k)}render()});
    logoize(el)}
  render();RR.push(render)}
'''
rep("\n/* ---------- v32: every summary tile opens the history behind it ---------- */", views + "\n/* ---------- v32: every summary tile opens the history behind it ---------- */")

rep("Object.assign(NOTES,{tiles32:", "Object.assign(NOTES,{weeklies2:['v33','new tab: Weeklies reworked \\u2014 four tiles, one ranked bar chart of every signal\\'s hit rate against the field, a square-per-week reliability grid, who scored and who was called but didn\\'t; follows the global week'],wkgrid2:['v33','new tab: Category Grid reworked \\u2014 the reliable categories as bars, best picks as chips, one sortable list of everyone carrying a category with his record and TD chance; follows the global week']});\nObject.assign(NOTES,{tiles32:")
io.open(T, 'w', encoding='utf-8').write(s)
print('v33 applied', len(s))
