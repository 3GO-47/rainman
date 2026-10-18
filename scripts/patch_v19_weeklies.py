# -*- coding: utf-8 -*-
"""v19 — Weeklies rebuilt to be read at a glance: one row of tiles, a hit-rate bar chart against the field line, player chips,
a three-tile season verdict, a slim season heatmap; the full player table folds away. No paragraphs."""
T='scripts/dashboard_template.html'
s=open(T,encoding='utf-8').read()
def once(old,new):
    global s
    assert s.count(old)==1,(old[:90],s.count(old));s=s.replace(old,new)

NEW = r"""/* a player as a compact chip: logo + short name, with a small tag (×2, his slot, signal count) */
const wkChip=(x,tag)=>`<span class="wkpc">${pn(x.name,x.team,true)}${tag?`<i>${tag}</i>`:''}</span>`;
/* one tile: small label, a big value, one short line under it */
const wkTile=(lbl,val,sub,tone,sm)=>`<div class="wkt ${tone||''}"><span class="k">${lbl}</span><b class="v${sm?' sm':''}">${val}</b><span class="s">${sub||''}</span></div>`;
function weeklies(){
  const el=$('#weeklies');if(!el)return;
  const SES=ALL_SE.slice().reverse();let S=SES[0];if(!wkFeat(S).weeks.length&&SES[1])S=SES[1];
  let W=null,show='sc';const CORE7=['QB1','RB1','RB2','WR1','WR2','WR3','TE1'],wkLive=new Set(CORE7);
  el.innerHTML=`<div class="controls">
    <select id="wkSe" title="which season to look back on">${SES.map(s=>`<option value="${s}" ${s===S?'selected':''}>${s} season</option>`).join('')}</select>
    <span class="chips" id="wkW" title="every week whose games are all played and logged"></span>
    ${slotChipsHTML('wkSlots',wkLive)}
    <span class="note kept">signals as they stood before kickoff, checked against who scored</span>
  </div>
  <div class="wktiles" id="wkTiles"></div>
  <div class="wkmain">
    <div class="panel"><h3 id="wkBh"></h3><div id="wkBars"></div></div>
    <div class="wkside"><div class="panel"><h3 id="wkPh2"></h3><div id="wkPlay"></div></div>
      <div class="panel"><h3 id="wkSeh"></h3><div id="wkSeason"></div></div></div>
  </div>
  <div class="panel"><h3 id="wkMh"></h3><div id="wkMx"></div></div>
  <details class="panel wkdet"><summary id="wkPh"></summary>
    <div class="controls" style="margin:6px 0"><span class="chips" id="wkShow"><button data-s="sc" class="on">scorers</button><button data-s="nm">near misses</button><button data-s="all">everyone</button></span></div><div id="wkPl"></div></details>`;
  const keep=x=>slotOK(wkLive,x.slot)&&inP(x.pos);
  function chipsW(F){const box=$('#wkW');box.innerHTML=F.weeks.map(w=>`<button data-w="${w}" class="${w===W?'on':''}">wk ${w}</button>`).join('')+(F.pending.length?`<span class="mini" style="margin-left:6px" title="a week appears once every game is logged">wk ${F.pending.join(', ')} in progress</span>`:'');
    box.querySelectorAll('button').forEach(b=>b.onclick=()=>{W=+b.dataset.w;render()})}
  const col=(s,l)=>l==null?'var(--dim2)':s.kind==='neg'?(wkR(l)<=.9?'var(--green)':wkR(l)>=1.1?'var(--red)':'#8b98a5'):(wkR(l)>=1.1?'var(--green)':wkR(l)<=.9?'var(--red)':'#8b98a5');
  function render(){
    S=+$('#wkSe').value;const F=wkFeat(S),SG=wkSigs();
    if(!F.weeks.length){$('#wkW').innerHTML='';['wkTiles','wkBars','wkPlay','wkSeason','wkMx','wkPl'].forEach(i=>$('#'+i).innerHTML='');$('#wkBh').textContent=`no completed week in ${S} yet`;return}
    if(W==null||!F.weeks.includes(W))W=F.weeks[F.weeks.length-1];
    chipsW(F);
    const AL=F.weeks.filter(w=>w<=W).map(w=>wkStats(F,w,keep,SG)),st=AL[AL.length-1];
    const live=SG.filter(s=>AL.some(a=>a.sig.find(y=>y.id===s.id).n>0)).map(s=>s.id);
    const q=st.sig.filter(s=>live.includes(s.id)&&s.n>0),ok=q.filter(s=>s.n>=st.minN&&s.hr!=null),posQ=ok.filter(s=>s.kind==='pos');
    /* ---- the tiles: the week in six numbers ---- */
    const best=posQ.slice().sort((a,b)=>b.hr-a.hr||b.lift-a.lift)[0],worst=posQ.slice().sort((a,b)=>a.lift-b.lift||a.hr-b.hr)[0];
    const bySlot={};st.P.forEach(x=>{const o=bySlot[x.grp]=bySlot[x.grp]||{g:x.grp,n:0,k:0};o.n++;if(x.td>0)o.k++});
    const sl=Object.values(bySlot).filter(o=>o.n>=5).map(o=>Object.assign(o,{r:o.k/o.n})).sort((a,b)=>b.r-a.r);
    const dv={};st.P.forEach(x=>{if(x.td>0){const o=dv[x.opp]=dv[x.opp]||{d:x.opp,n:0,who:[]};o.n+=x.td;o.who.push(x)}});const lk=Object.values(dv).sort((a,b)=>b.n-a.n)[0];
    $('#wkTiles').innerHTML=wkTile(`week ${W} · ${S}`,String(st.tds),'rushing + receiving TDs')
      +wkTile('scored',`${st.sc.length}<span class="dim"> / ${st.P.length}</span>`,`field rate <b>${wkPct(st.base)}</b>`)
      +(best?wkTile('best signal',best.lbl,`<b style="color:${col(best,best.lift)}">${wkPct(best.hr)}</b> scored · ${wkX(best.lift)} the field`,wkR(best.lift)>=1.1?'g':'',true):wkTile('best signal','—','no usable sample'))
      +(worst&&worst!==best?wkTile('weakest signal',worst.lbl,`<b style="color:${col(worst,worst.lift)}">${wkPct(worst.hr)}</b> scored · ${wkX(worst.lift)} the field`,wkR(worst.lift)<=.9?'r':'',true):'')
      +(sl.length>1?wkTile('best slot',`${slotchip(sl[0].g)} ${wkPct(sl[0].r)}`,`worst ${slotchip(sl[sl.length-1].g)} ${wkPct(sl[sl.length-1].r)}`,'g',true):'')
      +(lk?wkTile('leakiest defense',`${tcell(lk.d)} ${lk.n}`,`TDs allowed to ${lk.who.length} player${lk.who.length===1?'':'s'}`,'r',true):'');
    /* ---- the bars: every signal's hit rate against the field line ---- */
    const pos=q.filter(s=>s.kind==='pos').sort((a,b)=>(b.n>=st.minN)-(a.n>=st.minN)||b.hr-a.hr),neg=q.filter(s=>s.kind==='neg').sort((a,b)=>a.hr-b.hr);
    const mx=Math.max(.5,...q.map(s=>s.hr||0))*1.08,fx=100*st.base/mx;
    const bar=s=>{const thin=s.n<st.minN,c=col(s,s.lift);return `<div class="wkb${thin?' thin':''}" title="${esc(`${s.long}: ${s.k} of ${s.n} scored (${wkPct(s.hr)}) · ${wkX(s.lift)} the ${wkPct(st.base)} field${thin?' · under '+st.minN+' players, a small sample':''}`)}">
      <span class="l">${s.lbl}</span><span class="t"><i style="width:${(100*(s.hr||0)/mx).toFixed(1)}%;background:${c}"></i><u style="left:${fx.toFixed(1)}%"></u></span><span class="r"><b style="color:${c}">${wkPct(s.hr)}</b><span class="mini"> ${s.k}/${s.n}</span></span></div>`};
    $('#wkBh').innerHTML=`what hit — week ${W} <span class="wklg"><u></u> field ${wkPct(st.base)}</span><span class="wklg"><i style="background:var(--green)"></i> beat it</span><span class="wklg"><i style="background:var(--red)"></i> fell short</span><span class="wklg dim">faded = small sample</span>`;
    $('#wkBars').innerHTML=pos.map(bar).join('')+(neg.length?`<div class="wkgap">fades — players expected to score less · green = they did</div>${neg.map(bar).join('')}`:'');
    /* ---- the players, as chips ---- */
    const grp=(lbl,arr,tag,tip)=>`<div class="wkpg"><h4 title="${esc(tip)}">${lbl} <b>${arr.length}</b></h4><div class="wkpcs">${arr.length?arr.slice(0,8).map(x=>wkChip(x,tag(x))).join('')+(arr.length>8?`<span class="mini">+${arr.length-8} more</span>`:''):'<span class="mini dim">none</span>'}</div></div>`;
    $('#wkPh2').innerHTML=`players — week ${W}`;
    $('#wkPlay').innerHTML=grp('multi-TD',st.sc.filter(x=>x.td>1).sort((a,b)=>b.td-a.td),x=>'×'+x.td,'scored two or more')
      +grp('out of nowhere',st.sc.filter(x=>x.cs<=1).sort((a,b)=>b.td-a.td),x=>x.grp,'scored while carrying one core signal or none going in')
      +grp('lined up, no TD',st.P.filter(x=>x.td===0&&x.cs>=5).sort((a,b)=>b.cs-a.cs),x=>x.cs+'/8','five or more core signals going in, no touchdown');
    /* ---- the season: three verdicts and the heatmap ---- */
    let tn=0,tk=0;AL.forEach(a=>{tn+=a.P.length;tk+=a.sc.length});const sBase=tn?tk/tn:null;
    const SS=SG.filter(s=>live.includes(s.id)).map(s=>{let n=0,k=0,qw=0,bw=0;
      const pips=AL.map(a=>{const x=a.sig.find(y=>y.id===s.id);n+=x.n;k+=x.k;if(x.n<a.minN||x.hr==null)return 0;qw++;const won=s.kind==='pos'?wkR(x.lift)>=1.1:wkR(x.lift)<=.9;if(won)bw++;return won?1:-1});
      const hr=n?k/n:null;return Object.assign({},s,{n,k,hr,lift:hr!=null&&sBase?hr/sBase:null,qw,bw,pips})});
    const need=Math.max(2,Math.ceil(AL.length/2)),sp=SS.filter(r=>r.kind==='pos'&&r.qw>=need);
    const steady=sp.slice().sort((a,b)=>b.bw/b.qw-a.bw/a.qw||b.lift-a.lift)[0],shaky=sp.slice().sort((a,b)=>a.bw/a.qw-b.bw/b.qw||a.lift-b.lift)[0];
    const fade=SS.filter(r=>r.kind==='neg'&&r.qw>=2&&wkR(r.lift)<=.9).sort((a,b)=>a.lift-b.lift)[0];
    $('#wkSeh').innerHTML=`season so far — ${AL.length>1?`weeks ${AL[0].w}–${W}`:`week ${W}`}`;
    $('#wkSeason').innerHTML=AL.length<2?'<p class="mini dim">the verdicts start once a second week is in</p>':`<div class="wkss3">${
      steady?wkTile('steadiest',steady.lbl,`beat the field <b>${steady.bw}/${steady.qw}</b> wks · ${wkPct(steady.hr)}`,'g',true):''}${
      shaky&&shaky!==steady?wkTile('least reliable',shaky.lbl,`beat the field <b>${shaky.bw}/${shaky.qw}</b> wks · ${wkPct(shaky.hr)}`,'r',true):''}${
      fade?wkTile('best fade',fade.lbl,`only <b>${wkPct(fade.hr)}</b> scored vs ${wkPct(sBase)}`,'g',true):''}</div>`;
    const rows=SS.filter(r=>r.kind==='pos').sort((a,b)=>(b.hr??-1)-(a.hr??-1)).concat(SS.filter(r=>r.kind==='neg').sort((a,b)=>(a.hr??9)-(b.hr??9)));
    const pip=v=>`<i class="pip ${v>0?'w':v<0?'l':'o'}"></i>`;
    $('#wkMh').innerHTML=`season heatmap — every signal, every week <span class="f">cell = hit rate that week, green = beat the field, red = fell short, faded = small sample · dots = weeks it beat the field</span>`;
    $('#wkMx').innerHTML=`<table class="fx wkm"><thead><tr><th>signal</th>${AL.map(a=>`<th class="c${a.w===W?' on':''}">wk ${a.w}</th>`).join('')}<th class="c gs">season</th><th class="c" title="green dot = beat the field that week">beat field</th></tr></thead><tbody>
      <tr class="fld"><td><b>the field</b></td>${AL.map(a=>`<td class="c" data-v="${a.base??''}">${wkPct(a.base)}</td>`).join('')}<td class="c gs" data-v="${sBase??''}"><b>${wkPct(sBase)}</b></td><td class="c"></td></tr>
      ${rows.map(r=>`<tr class="${r.kind==='neg'?'neg':''}"><td title="${esc(r.long)}">${r.kind==='neg'?'<span class="dim">fade · </span>':''}${r.lbl}</td>${AL.map((a,i)=>{const x=a.sig.find(y=>y.id===r.id),thin=x.n<a.minN;
          return `<td class="c${thin?' thin':''}" data-v="${x.hr??''}" title="${esc(`${r.lbl} · wk ${a.w}: ${x.k} of ${x.n} scored${x.lift!=null?' · '+wkX(x.lift)+' the field':''}`)}">${x.hr==null?'<span class="dim">·</span>':`<span class="hc" style="color:${col(r,x.lift)};background:color-mix(in srgb, ${col(r,x.lift)} 16%, transparent)">${wkPct(x.hr)}</span>`}</td>`}).join('')}
        <td class="c gs" data-v="${r.hr??''}" title="${r.k} of ${r.n} · ${wkX(r.lift)} the field">${r.hr==null?'<span class="dim">·</span>':`<b style="color:${col(r,r.lift)}">${wkPct(r.hr)}</b>`}</td>
        <td class="c" data-v="${r.qw?r.bw/r.qw:''}" title="beat the field in ${r.bw} of ${r.qw} weeks with a usable sample">${r.pips.map(pip).join('')}</td></tr>`).join('')}</tbody></table>`;
    /* ---- the full table, folded away ---- */
    const SH={sc:'every scorer',nm:'near misses (4+ signals, no TD)',all:'everyone who played'};
    let P=show==='sc'?st.sc:show==='nm'?st.P.filter(x=>x.td===0&&x.cs>=4):st.P;P=P.slice().sort((a,b)=>b.td-a.td||b.cs-a.cs||b.ppr-a.ppr);
    const ck=v=>v===true?'<b style="color:var(--green)">✓</b>':v===false?'<span class="dim">·</span>':'<span class="dim">—</span>';
    const rk=(r,n)=>r==null?'<span class="dim">·</span>':`<span class="badge" style="${gradeStyle(r,n||NT)}">${r}</span>`;
    $('#wkPh').innerHTML=`player table — week ${W} <span class="mini">${SH[show]} · ${P.length} · open for every player's pre-game profile</span>`;
    $('#wkPl').innerHTML=`<table class="fx wkp"><thead><tr><th>player</th><th>slot</th><th>opp</th><th title="rushing + receiving touchdowns this week">TD</th><th title="PPR points this week">PPR</th>
      <th title="the opponent's rank in TDs allowed to his slot going into the week · 1 = the most">TD rk</th><th title="the opponent's rank in PPR allowed to his slot going into the week">PPR rk</th>
      <th title="his touchdowns in earlier meetings with this opponent">vs them</th><th title="scored in his previous game">last</th><th title="games with a TD in his last three">L3</th><th title="TDs per game this season before this week">TD/g</th>
      <th title="snap share this season before this week">snap</th><th title="team implied total from the closing line">implied</th><th title="core signals he carried going in (of 8)">signals</th></tr></thead><tbody>
      ${P.map(x=>`<tr><td>${pn(x.name,x.team,true)}</td><td>${slotchip(x.grp)}</td><td>${x.home?'':'@'}${tcell(x.opp)}</td>
        <td class="n" data-v="${x.td}" title="${x.rtd} rushing · ${x.rectd} receiving">${x.td?`<b style="color:var(--green)">${x.td}</b>`:'<span class="dim">0</span>'}</td><td class="n" data-v="${x.ppr}">${x.ppr.toFixed(1)}</td>
        <td class="n" data-v="${x.tdR??''}">${rk(x.tdR,x.nD)}</td><td class="n" data-v="${x.pprR??''}">${rk(x.pprR,x.nD)}</td>
        <td class="n" data-v="${x.hN?x.hTD:''}">${x.hN?`<b style="color:${x.hTD?'var(--green)':'var(--dim)'}">${x.hTD}</b><span class="mini"> in ${x.hN}</span>`:'<span class="dim">—</span>'}</td>
        <td class="c">${ck(x.last)}</td><td class="n" data-v="${x.l3??''}">${x.l3==null?'<span class="dim">—</span>':`<b style="color:${x.l3>=2?'var(--green)':x.l3===0?'var(--dim)':'var(--txt)'}">${x.l3}</b>`}</td>
        <td class="n" data-v="${x.rate??''}">${x.rate==null?'<span class="dim">—</span>':x.rate.toFixed(2)}</td><td class="n" data-v="${x.snp??''}">${x.snp==null?'<span class="dim">—</span>':Math.round(100*x.snp)+'%'}</td>
        <td class="n" data-v="${x.imp??''}">${x.imp==null?'<span class="dim">—</span>':`<span style="color:${x.imp>=24?'var(--green)':x.imp<18?'var(--red)':'var(--txt)'}">${x.imp.toFixed(1)}</span>`}</td>
        <td class="n" data-v="${x.cs}"><span class="badge" style="${gradeStyle(1+(1-x.cs/8)*(NT-1))}">${x.cs}</span></td></tr>`).join('')||'<tr><td colspan="14" class="dim">nobody here</td></tr>'}</tbody></table>`;
    tWire(el)}
  $('#wkSe').onchange=()=>{W=null;render()};slotChipsWire('wkSlots',wkLive,render);
  $('#wkShow').querySelectorAll('button').forEach(b=>b.onclick=()=>{show=b.dataset.s;$('#wkShow').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render()});
  render();RR.push(render);
}"""

a=s.index("function wkNames(")
b=s.index("function weeklies(){")
e=s.index("  render();RR.push(render);\n}",b)+len("  render();RR.push(render);\n}")
s=s[:a]+NEW+s[e:]

CSS = """
/* ---- v19 Weeklies at a glance ---- */
.wktiles{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:0 0 10px}@media(max-width:1300px){.wktiles{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:760px){.wktiles{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
.wkt{background:var(--panel);border:1px solid var(--edge);border-top:2px solid var(--edge2);border-radius:8px;padding:9px 11px;display:flex;flex-direction:column;gap:4px;min-width:0}
.wkt.g{border-top-color:var(--green)}.wkt.r{border-top-color:var(--red)}
.wkt .k{font:600 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2)}
.wkt .v{font:700 22px/1.1 var(--mono);color:var(--txt);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.wkt .v.sm{font:600 14px/1.3 var(--ui)}.wkt .v .dim{font-size:14px}
.wkt .s{font-size:11.5px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.wkt .s b{color:var(--txt);font-family:var(--mono)}
.wkmain{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:12px;align-items:start}@media(max-width:1150px){.wkmain{grid-template-columns:1fr}}
.wkside{display:flex;flex-direction:column;gap:12px;min-width:0}.wkside>.panel{margin:0}
.wkb{display:grid;grid-template-columns:190px minmax(0,1fr) 92px;gap:10px;align-items:center;padding:4px 0;font-size:12.5px}
.wkb .l{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--txt)}
.wkb .t{position:relative;height:14px;background:rgba(255,255,255,.04);border-radius:3px}
.wkb .t i{position:absolute;left:0;top:0;bottom:0;border-radius:3px;opacity:.8}
.wkb .t u{position:absolute;top:-4px;bottom:-4px;width:2px;margin-left:-1px;background:#fff;opacity:.6;text-decoration:none}
.wkb .r{text-align:right;font:600 12px var(--mono);white-space:nowrap}.wkb .r .mini{font-weight:500}.wkb.thin{opacity:.4}
.wkgap{font:600 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2);margin:10px 0 4px;border-top:1px dashed var(--edge);padding-top:9px}
.wklg{display:inline-flex;align-items:center;gap:4px;margin-left:12px;font:500 10.5px var(--ui);color:var(--dim);text-transform:none;letter-spacing:0}
.wklg u{display:inline-block;width:2px;height:12px;background:#fff;opacity:.6}.wklg i{display:inline-block;width:10px;height:10px;border-radius:2px;opacity:.8}
.wkpg{margin:0 0 12px}.wkpg:last-child{margin:0}
.wkpg h4{font:600 10px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--dim2);margin:0 0 6px;display:flex;gap:6px;align-items:center}.wkpg h4 b{font:700 11px var(--mono);color:var(--txt)}
.wkpcs{display:flex;flex-wrap:wrap;gap:5px;align-items:center}
.wkpc{display:inline-flex;align-items:center;gap:3px;border:1px solid var(--edge2);border-radius:12px;padding:2px 8px 2px 5px;font-size:11.5px;background:rgba(255,255,255,.02)}
.wkpc i{font-style:normal;font:600 10px var(--mono);color:var(--amber);margin-left:3px}
.wkss3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}@media(max-width:760px){.wkss3{grid-template-columns:1fr!important}}
table.wkm .hc{display:inline-block;min-width:38px;padding:2px 4px;border-radius:3px;font:600 10.5px var(--mono)}table.wkm td.thin .hc{opacity:.4}
.pip{display:inline-block;width:8px;height:8px;border-radius:50%;margin:0 1.5px;background:var(--edge2)}.pip.w{background:var(--green)}.pip.l{background:var(--red)}.pip.o{background:transparent;box-shadow:inset 0 0 0 1px var(--edge2)}
details.wkdet>summary{cursor:pointer;font:600 12.5px var(--ui);color:var(--txt);list-style:none;padding:2px 0}details.wkdet>summary::-webkit-details-marker{display:none}
details.wkdet>summary:before{content:'▸ ';color:var(--dim2)}details.wkdet[open]>summary:before{content:'▾ '}details.wkdet>summary .mini{margin-left:8px;font-weight:500}
@media(max-width:760px){.wkb{grid-template-columns:118px minmax(0,1fr) 72px;gap:6px;font-size:11.5px}.wklg{margin-left:6px}}"""
once("table.wkp td.c{text-align:center}","table.wkp td.c{text-align:center}"+CSS)

once(""" weeklies:{what:'The touchdown lookback.',how:['every signal is pre-game: the defense ranks, his form and his history with the opponent as they stood before that week kicked off — then checked against who actually scored','hit rate = share of the players carrying a signal who scored a rushing or receiving TD · × = against everyone in the pool that week · green = scored more often than the field','a week appears once every game is played and logged · click a week card to read it']},""",
     """ weeklies:{what:'The touchdown lookback.',how:['bar = how often players with that signal scored · white line = everyone who played','green = beat the field · red = fell short','a week appears once all its games are logged']},""")
i=s.index(" weeklies:['v18',");j=s.index("\n",i)
line=s[i:j];tail='});' if line.rstrip().endswith('});') else ''
s=s[:i]+" weeklies:['v19','rebuilt to read at a glance: six tiles, a hit-rate bar chart against the field line, player chips, three season verdicts and a heatmap; the full player table folds away']"+tail+s[j:]
open(T,'w',encoding='utf-8').write(s)
print('v19 weeklies patched')
