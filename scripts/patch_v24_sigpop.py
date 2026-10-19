"""v24 — Weeklies: click any signal for the players who carry it.

Every signal name on the Weeklies tab (the bars, the tiles, the trust board, the per-position tiles, the heatmap rows, the
core list, the week-ahead tags) and every stacking bar opens one pane:
  * the signal's record — every season, its verdict, each season's lift, the week on screen;
  * week ahead — every player carrying it into his next game: opponent, the opponent's TD / PPR / Ψ rank against his slot,
    the TD Picks chance (and price when posted), implied total, spread, TD share, TD rate, last three, touches, snaps,
    core signals, ✓ / ✗ once his game is logged; sortable;
  * the week on screen — who carried it and whether he scored.
The lists follow the Weeklies slot / position filters.

Usage: python scripts/patch_v24_sigpop.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v24: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# ---------------- CSS
rep(r'''.wkpc.k{border-style:dashed;border-color:var(--dim)}''', r'''.wkpc.k{border-style:dashed;border-color:var(--dim)}
.wksig{cursor:pointer;text-decoration:underline dotted var(--dim2);text-underline-offset:3px}.wksig:hover{color:var(--txt);text-decoration-color:var(--txt)}
.wktc.wksig,.wka .tags i.wksig{text-decoration:none}.wktc.wksig:hover{border-color:var(--dim)}.wka .tags i.wksig:hover{background:#00c85322}
#ppModal .wsg{margin:4px 0 8px}#ppModal .wsg .tabs{margin:8px 0 6px}#ppModal table.wkp td.n{text-align:right}''')

# ---------------- a clickable signal name
rep(r'''const wkTile=(lbl,val,sub,tone,sm)=>''', r'''const wkSL=s=>s?`<span class="wksig" data-sig="${s.id}" title="click for every player carrying it into the next game">${s.lbl}</span>`:'—';
const wkTile=(lbl,val,sub,tone,sm)=>''')
rep(r'''<span class="l">${s.lbl}</span>''', r'''<span class="l wksig" data-sig="${s.id}">${s.lbl}</span>''')
rep(r'''wkTile('best signal',best.lbl,''', r'''wkTile('best signal',wkSL(best),''')
rep(r'''wkTile('weakest signal',worst.lbl,''', r'''wkTile('weakest signal',wkSL(worst),''')
rep(r'''wkTile('steadiest',steady.lbl,''', r'''wkTile('steadiest',wkSL(steady),''')
rep(r'''wkTile('least reliable',shaky.lbl,''', r'''wkTile('least reliable',wkSL(shaky),''')
rep(r'''wkTile('best fade',fade.lbl,''', r'''wkTile('best fade',wkSL(fade),''')
rep(r'''<div class="wktc" title=''', r'''<div class="wktc wksig" data-sig="${x.id}" title=''')
rep(r'''best.lbl,`<b style="color:var(--green)">''', r'''wkSL(best),`<b style="color:var(--green)">''')
rep(r'''<span class="l">${x.c}${x.c===6?''', r'''<span class="l wksig" data-stack="${x.c}">${x.c}${x.c===6?''')
rep(r'''WK_KEY.map(id=>`<span>${(SG.find(z=>z.id===id)||{}).lbl}</span>`)''', r'''WK_KEY.map(id=>`<span class="wksig" data-sig="${id}">${(SG.find(z=>z.id===id)||{}).lbl}</span>`)''')
rep(r''''neg'?'<span class="dim">fade · </span>':''}${r.lbl}</td>''', r''''neg'?'<span class="dim">fade · </span>':''}${wkSL(r)}</td>''')
rep(r'''<i title="${esc(k.long)}">${WK_AB[k.id]||k.lbl}</i>''', r'''<i class="wksig" data-sig="${k.id}" title="${esc(k.long)} · click for everyone carrying it">${WK_AB[k.id]||k.lbl}</i>''', 2)

# ---------------- remember what the render saw, then the pane
rep(r'''    tWire(el)}
  $('#wkSe').onchange=()=>{W=null;render()};''', r'''    CUR={S,W,st,TR,AH,W0,SG};
    tWire(el)}
  /* ---- v24: click any signal → who carries it into the next game, and who carried it in the week on screen ---- */
  let CUR=null;const PSI={};
  const psiRk=(opp,grp)=>{const D=J.dvp&&J.dvp.combined;if(!opp||!grp||!D)return null;
    if(!PSI[grp])PSI[grp]=Object.keys(D).map(t=>({t,v:(D[t].comps||{})[grp]})).filter(d=>d.v!=null).sort((a,b)=>a.v-b.v).map(d=>d.t);const i=PSI[grp].indexOf(opp);return i<0?null:i+1};
  const tpOf=(n,t,w)=>{const T=J.tdpicks;if(T&&T.week===w){const p=T.picks.find(x=>x.n===n&&x.t===t)||T.picks.find(x=>x.n===n);if(p)return {p:p.p,price:p.price,book:p.book}}
    const b=((J.betting||{}).td||[]).find(r=>+r.week===w&&r.player===n);return b&&b.p_model!=null&&b.p_model!==''?{p:+b.p_model,price:b.price!=null&&b.price!==''?+b.price:null,book:b.book}:null};
  function wkSigPop(id,stack){if(!CUR)return;const {S:S0,W:W1,st,TR,AH,W0,SG}=CUR;
    const sg=stack==null?SG.find(z=>z.id===id):null;if(stack==null&&!sg)return;
    const qual=stack!=null?(x=>stack>=6?x.cs>=6:x.cs===stack):sg.f;
    const t=sg?TR.sig.find(z=>z.id===sg.id):TR.stack.find(z=>z.c===stack);
    const lift=t?(t.lift!=null?t.lift:(t.hr!=null&&TR.base?t.hr/TR.base:null)):null,neg=!!sg&&sg.kind==='neg';
    const A=AH.filter(qual).map(x=>Object.assign(x,{tp:tpOf(x.name,x.team,W0),psR:psiRk(x.opp,x.grp)})).sort((a,b)=>((b.tp||{}).p??-1)-((a.tp||{}).p??-1)||b.cs-a.cs);
    const B=st.P.filter(qual).sort((a,b)=>b.td-a.td||b.cs-a.cs),bk=B.filter(x=>x.td>0).length;
    const lbl=sg?sg.lbl:`${stack}${stack>=6?'+':''} core signal${stack===1?'':'s'}`,long=sg?sg.long:`players carrying ${stack>=6?'six or more':stack===0?'none':'exactly '+stack} of the eight core signals going in`;
    const rk=(r,n)=>r==null?'<span class="dim">·</span>':`<span class="badge" style="${gradeStyle(r,n||NT)}">${r}</span>`;
    const tpc=v=>v>=.5?'var(--green)':v>=.4?'#7dd87d':v>=.3?'var(--amber)':v>=.2?'#6db3e8':'var(--dim)';
    const imC=v=>v>=24?'var(--green)':v<18?'var(--red)':'var(--txt)',D='<span class="dim">—</span>';
    const sig=x=>`<span class="badge" style="${gradeStyle(1+(1-x.cs/8)*(NT-1))}">${x.cs}</span>`;
    const lt=lift==null?'':neg?(wkR(lift)<=.9?'g':wkR(lift)>=1.1?'r':''):(wkR(lift)>=1.1?'g':wkR(lift)<=.9?'r':'');
    const tiles=[
      t&&t.hr!=null?wkTile(`every season · ${ALL_SE[0]}–${String(ALL_SE[ALL_SE.length-1]).slice(2)}`,wkPct(t.hr),`of ${(t.n||0).toLocaleString()} scored · ${wkX(lift)} the field`,lt,true):'',
      sg&&t?wkTile('verdict',({trust:'trust',lean:'lean on',fade:'fade',noise:'ignore'})[t.tier]||'—',`beat the field ${t.bw||0} of ${t.qw||0} weeks`,t.tier==='trust'||t.tier==='fade'?'g':t.tier==='lean'?'':'r',true):'',
      sg&&t&&t.per?wkTile('by season',ALL_SE.map(se=>wkX(t.per[se].lift)).join(' · '),ALL_SE.join(' · '),'',true):'',
      wkTile(`week ${W1} · ${S0}`,`${bk}<span class="dim"> / ${B.length}</span>`,`carried it and scored · field ${wkPct(st.base)}`,B.length&&st.base?((bk/B.length)/st.base>=1.1?(neg?'r':'g'):(bk/B.length)/st.base<=.9?(neg?'g':'r'):''):'',true),
      wkTile(`week ${W0} ahead`,String(A.length),`carry it into their next game`,A.length?'g':'',true)].filter(Boolean);
    const aT=A.length?`<table class="fx wkp"><thead><tr><th>player</th><th>slot</th><th title="his next game">next</th><th title="the opponent's rank in TDs allowed to his slot · 1 = the most">TD rk</th><th title="the opponent's rank in PPR allowed to his slot · 1 = the most">PPR rk</th><th title="the opponent's mean rank across every stat of his slot (blend) · 1 = softest">Ψ rk</th><th title="TD Picks: his chance to score a rushing or receiving TD">TD %</th><th title="team implied total">implied</th><th title="spread from his side · + = favored">spread</th><th title="his share of his team's TDs this season">TD share</th><th title="TDs per game this season">TD/g</th><th title="games with a TD in his last three">L3</th><th title="carries + targets a game">touches</th><th title="snap share this season">snap</th><th title="core signals he carries going in (of 8)">signals</th></tr></thead><tbody>
      ${A.map(x=>`<tr><td>${pn(x.name,x.team,true)}${x.u&&x.u.inj==='0'?' <span class="inj0">Q</span>':''}${x.done?(x.done.td>0?' <b style="color:var(--green)">✓</b>':' <b style="color:var(--red)">✗</b>'):''}</td><td>${slotchip(x.slot||x.grp)}</td><td>${x.raw&&x.raw[0]==='@'?'@':'vs'} ${tcell(x.opp)}</td>
        <td class="n" data-v="${x.tdR??''}">${rk(x.tdR,x.nD)}</td><td class="n" data-v="${x.pprR??''}">${rk(x.pprR,x.nD)}</td><td class="n" data-v="${x.psR??''}">${rk(x.psR)}</td>
        <td class="n" data-v="${x.tp?x.tp.p:''}">${x.tp?`<b style="color:${tpc(x.tp.p)}">${Math.round(100*x.tp.p)}%</b>${x.tp.price!=null?` <span class="mini">${mlTxt(+x.tp.price)}</span>`:''}`:D}</td>
        <td class="n" data-v="${x.imp??''}">${x.imp==null?D:`<span style="color:${imC(x.imp)}">${(+x.imp).toFixed(1)}</span>`}</td>
        <td class="n" data-v="${x.sp??''}">${x.sp==null?D:(x.sp>0?'+':'')+x.sp}</td><td class="n" data-v="${x.share??''}">${x.share==null?D:wkPct(x.share)}</td>
        <td class="n" data-v="${x.rate??''}">${x.rate==null?D:x.rate.toFixed(2)}</td><td class="n" data-v="${x.l3??''}">${x.l3==null?D:x.l3}</td>
        <td class="n" data-v="${x.touch??''}">${x.touch==null?D:x.touch.toFixed(1)}</td><td class="n" data-v="${x.snp??''}">${x.snp==null?D:Math.round(100*x.snp)+'%'}</td>
        <td class="n" data-v="${x.cs}">${sig(x)}</td></tr>`).join('')}</tbody></table>`:`<p class="mini dim">nobody on the week-${W0} slate carries it${wkLive.size?' in the slots picked on Weeklies':''}</p>`;
    const bT=B.length?`<table class="fx wkp"><thead><tr><th>player</th><th>slot</th><th>opp</th><th title="rushing + receiving touchdowns that week">TD</th><th title="PPR points that week">PPR</th><th title="the opponent's TD rank vs his slot going in">TD rk</th><th title="the opponent's PPR rank vs his slot going in">PPR rk</th><th title="team implied total">implied</th><th title="his share of his team's TDs going in">TD share</th><th title="TDs per game going in">TD/g</th><th title="core signals he carried (of 8)">signals</th></tr></thead><tbody>
      ${B.map(x=>`<tr><td>${pn(x.name,x.team,true)}</td><td>${slotchip(x.grp)}</td><td>${x.home?'':'@'}${tcell(x.opp)}</td>
        <td class="n" data-v="${x.td}">${x.td?`<b style="color:var(--green)">${x.td}</b>`:'<span class="dim">0</span>'}</td><td class="n" data-v="${x.ppr}">${x.ppr.toFixed(1)}</td>
        <td class="n" data-v="${x.tdR??''}">${rk(x.tdR,x.nD)}</td><td class="n" data-v="${x.pprR??''}">${rk(x.pprR,x.nD)}</td>
        <td class="n" data-v="${x.imp??''}">${x.imp==null?D:`<span style="color:${imC(x.imp)}">${(+x.imp).toFixed(1)}</span>`}</td>
        <td class="n" data-v="${x.share??''}">${x.share==null?D:wkPct(x.share)}</td><td class="n" data-v="${x.rate??''}">${x.rate==null?D:x.rate.toFixed(2)}</td><td class="n" data-v="${x.cs}">${sig(x)}</td></tr>`).join('')}</tbody></table>`:`<p class="mini dim">nobody carried it in week ${W1}</p>`;
    const old=document.getElementById('ppModal');if(old)old.remove();
    document.body.insertAdjacentHTML('beforeend',`<div class="modal" id="ppModal"><div class="modalbox wide">
      <button class="mclose" id="ppX">ESC &#10005;</button>
      <h3>${esc(lbl)} <span class="f">${sg?WK_GL[sg.g].split(' — ')[0]+' · ':''}${esc(long)}</span></h3>
      <div class="ppk" data-mg="1">${tiles.join('')}</div>
      <div class="wsg"><div class="tabs"><button id="wsT1" class="on">week ${W0} — who carries it · ${A.length}</button><button id="wsT2">week ${W1} — who carried it · ${B.length} (${bk} scored)</button></div>
      <div id="wsV1">${aT}</div><div id="wsV2" hidden>${bT}</div></div>
      <p class="mini">${neg?'a fade: players carrying it are expected to score less':'players carrying it have scored more often than the field'} · ranks: 1 = the opponent allows the most to his slot · TD % = the TD Picks model · Weeklies filter: ${wkLive.size?[...wkLive].join(' · '):'every slot'} · click a name for his card · every column sorts</p>
    </div></div>`);
    wireModal();const t1=$('#wsT1'),t2=$('#wsT2'),sw=a=>{t1.classList.toggle('on',a);t2.classList.toggle('on',!a);$('#wsV1').hidden=!a;$('#wsV2').hidden=a};t1.onclick=()=>sw(true);t2.onclick=()=>sw(false)}
  el.addEventListener('click',e=>{const t=e.target.closest('[data-sig],[data-stack]');if(!t||!el.contains(t))return;e.preventDefault();e.stopPropagation();
    t.dataset.stack!=null?wkSigPop(null,+t.dataset.stack):wkSigPop(t.dataset.sig)});
  $('#wkSe').onchange=()=>{W=null;render()};''')
rep(r''' weeklies:['v22','the week ahead comes from the TD Picks model (one ranking, not two) with the signal tags kept · new: how the model\'s own top ten did in the week you\'re looking back on'],''', r''' weeklies:['v24','click any signal — a bar, a tile, a trust chip, a heatmap row, a week-ahead tag or a stacking bar — for every player carrying it into his next game, with the opponent\'s TD / PPR / Ψ ranks against his slot and the TD Picks chance; a second tab lists who carried it in the week on screen'],''')
open(P, 'w', encoding='utf-8').write(s)
print('patch_v24: signal panes added')
