"""v23 — F6 TEST > METAPROP: META for player props.

Same five columns (all · QB · RB · WR · TE), lens chips, slot chips, data-set select, H2H season select, OUT filter, search and
the leader cards across the top as META — one row per posted prop line instead of one per starter. The row's line is the one
most books post; best over / under price across books ride in the tooltip. Signals, each turned into a 0–1 lean (1 = over):
  DVP  the opponent's rank allowing that exact stat to his slot, from the chosen data set (1 = allows the most)
  MDL  the prop model's chance he goes over the line (betting.lines p_over_model)
  L10  times he cleared the line in his last ten games (game logs)
  AVG  his average this season (last ten if under three games) vs the line
  H2H  his average in this stat against this opponent vs the line, discounted under three meetings
META folds them with META's own rule: 100 = everything says OVER, 0 = everything says UNDER.

Usage: python scripts/patch_v23_metaprop.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v23: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# ---------------- registration: item, container, sub list, boot, intro, notes
rep(r'''c:'test',sub:'meta'},''', r'''c:'test',sub:'meta'},
   {id:'metaprop',nfl:true,label:'METAPROP',desc:'META for player props: every posted prop line with the defense-vs-position rank for that exact stat, the prop model, his hit rate over the line, his average and his head-to-head folded into one over / under score — META\'s five columns, data sets and filters',c:'test',sub:'metaprop'},''')
rep(r'''<div id="meta" hidden></div>''', r'''<div id="meta" hidden></div><div id="metaprop" hidden></div>''')
rep(r'''['meta','weeklies','tdpicks',''', r'''['meta','metaprop','weeklies','tdpicks',''')
rep(r'''['test',metaGrid],''', r'''['test',metaGrid],['test',metaProp],''')
rep(r''' meta:{what:'Every board at once.',''', r''' metaprop:{what:'META for player props.',how:['one row per posted prop line (the line most books post) · META = every signal in one over / under score, 0–100 — 100 = everything says OVER, 0 = everything says UNDER; hover a META cell for the breakdown','DVP = the opponent\'s rank allowing that exact stat to his slot (1 = the most) · MDL = the prop model\'s over % · L10 = times he cleared the line in his last 10 · AVG / H2H = his average this season / against this opponent, green above the line, red below','market chips pick the props; the data-set select (2024 · 2025 · 2026 · combined · adjusted · μ) drives DVP and META']},
 meta:{what:'Every board at once.',''')
rep(r'''const BOOT=[''', r'''Object.assign(NOTES,{metaprop:['v23','new tab: META for player props — every posted prop line scored over / under on the defense\'s rank for that exact stat, the prop model, his last-10 hit rate, his average and his head-to-head; META\'s five columns, data sets, filters and leader cards']});
const BOOT=[''')

# ---------------- CSS
rep(r'''.lgrid.meta td .psi{font:700 11px var(--mono)}''', r'''.lgrid.meta td .psi{font:700 11px var(--mono)}
.lgrid.mp td.ln{white-space:nowrap;font:600 10.5px var(--mono);color:var(--txt);overflow:hidden;text-overflow:ellipsis}.lgrid.mp td.ln .mpk{font:600 8.5px var(--ui);color:var(--dim2);letter-spacing:.04em;margin-right:3px}''')

# ---------------- the tab
rep(r'''
/* ---------------- Weeklies (F6 TEST) — the touchdown lookback ----------------''', r'''
/* ---------------- METAPROP (F6 TEST, v23) — META for player props ----------------
   META's five columns, data sets and filters, one row per posted prop line (the line most books post; best price on each side
   across books in the tooltip). Every signal becomes a 0–1 lean, 1 = OVER, .5 = none, 0 = UNDER, folded with META's rule. */
const MP_W={dvp:.25,mdl:.30,l10:.20,avg:.15,h2h:.10};
const MP_L=[['meta','META','everything together · 0–100, 100 = every signal says OVER, 0 = every signal says UNDER'],['dvp','DVP','what the opponent allows his slot in this exact stat · rank, 1 = the most'],['mdl','MDL','the prop model\'s chance he goes over the line'],['l10','L10','times he cleared this line in his last ten games'],['avg','AVG','his average this season vs the line'],['h2h','H2H','his average in this stat against this opponent vs the line']];
const MP_MK={pass_yds:['passing yards','PY'],pass_td:['passing TDs','PTD'],completions:['completions','CMP'],pass_att:['pass attempts','ATT'],interceptions:['interceptions','INT'],rush_yds:['rushing yards','RY'],rush_att:['carries','CAR'],rec_yds:['receiving yards','RCY'],receptions:['receptions','REC']};
function metaProp(root='#metaprop',px='mp'){
  const srcs=Object.keys(J.dvp),$$=k=>$('#'+px+k),live=new Set(TD_SLOTS),mk=new Set();
  const LBL=Object.fromEntries(MP_L.map(([k,l])=>[k,l])),DESC=new Set(['meta','mdl','l10','avg','h2h']);
  const LI={pass_yds:LOG.py,pass_td:LOG.ptd,pass_att:LOG.patt,interceptions:LOG.int,rush_yds:LOG.ry,rush_att:LOG.ra,rec_yds:LOG.recy,receptions:LOG.rec};
  const ALLL=((J.betting||{}).lines)||[];
  if(!ALLL.length){$(root).innerHTML='<p class="note">no player-prop lines in this build yet — the loop pulls them from the books as they post</p>';return}
  const MKS=Object.keys(MP_MK).filter(m=>ALLL.some(r=>r.market===m));
  let lens='meta';
  $(root).innerHTML=`<div class="controls">
    <span class="chips" id="${px}Lens" title="what every column is ranked by — META folds all of them together; click any column header to re-sort just that column">${MP_L.map(([k,l,t])=>`<button data-l="${k}" class="${k==='meta'?'on':''}" title="${esc(t)}">${l}</button>`).join('')}</span>
    <span class="chips" id="${px}Slots" title="which depth slots the board covers — click to toggle, ALL for every body on the chart">
      <button data-s="">all</button>${TD_SLOTS.map(s=>`<button data-s="${s}" class="on">${s}</button>`).join('')}</span>
    <span class="chips" id="${px}Mk" title="which prop markets the board covers — click one or more, ALL for every market"><button data-m="" class="on">all</button>${MKS.map(m=>`<button data-m="${m}" title="${MP_MK[m][0]}">${MP_MK[m][1]}</button>`).join('')}</span>
    <select id="${px}Src" title="which data set the DVP ranks read — and with them META">${srcs.map(s=>`<option value="${s}" ${s==='combined'?'selected':''}>${s}</option>`).join('')}<option value="mu">μ every set</option></select>
    <select id="${px}Se" title="which seasons of head-to-head history count"><option value="">H2H: all seasons (${ALL_SE[0]}–${String(ALL_SE[ALL_SE.length-1]).slice(2)})</option>${ALL_SE.slice().reverse().map(s=>`<option value="${s}">H2H: ${s} only</option>`).join('')}</select>
    <select id="${px}Inj"><option value="x" selected>hide OUT</option><option value="">incl. OUT</option></select>
    <input id="${px}Q" placeholder="search player..." size="15">
    <span class="note">META for player props. One row per posted line (the line most books post). <b>META</b> folds the other five into one score, 0–100 — 100 = every signal says OVER, 0 = every signal says UNDER &middot; <b>DVP</b> = what this week's opponent allows his slot in that exact stat, rank of ${NT} (1 = the most) &middot; <b>MDL</b> = the prop model's chance he goes over &middot; <b>L10</b> = times he cleared the line in his last ten &middot; <b>AVG</b> = his average this season, green above the line, red below &middot; <b>H2H</b> = his average against this opponent, green above the line, red below &middot; the data-set select drives DVP and META; hover any cell for the detail, the line cell for every book's price &middot; click a name for his card</span>
  </div>
  <div class="mlead" id="${px}Lead" data-mg="1"></div>
  <div class="lgrid td5 wide full meta mp">${['ALL'].concat(TPOS).map(p=>`<section class="lgcol"><h3>${p==='ALL'?'◉ all':posIcon(p,12)+' '+p} <span class="gl" id="${px}G${p}"></span> <span class="f" id="${px}N${p}"></span></h3><div id="${px}B${p}"></div></section>`).join('')}</div>`;
  const sort={};['ALL'].concat(TPOS).forEach(p=>sort[p]={k:'meta',a:false});
  const avg=a=>{const g=a.filter(v=>v!=null);return g.length?g.reduce((t,v)=>t+v,0)/g.length:null};
  const eq=p=>1+(1-p)*(NT-1),clamp=v=>Math.max(0,Math.min(1,v));
  const dec=a=>a==null||a===''||isNaN(+a)?null:(+a>0?1+a/100:1-100/+a);
  const mpKey=(m,grp)=>{const gs=J.groupStats[grp]||[];
    if(m==='pass_yds'||m==='completions'||m==='pass_att')return grp==='QB'?'QB PY':null;
    if(m==='pass_td')return grp==='QB'?'P TD':null;
    if(m==='rush_yds'||m==='rush_att')return grp==='QB'?'QB RY':grp==='RB1'?'RB1 RY':grp==='RB2'?'RB2+ RY':/^WR/.test(grp)?'WR RY':null;
    if(m==='rec_yds')return gs.find(c=>/RecY$/.test(c))||null;
    if(m==='receptions')return gs.find(c=>/Recep$/.test(c))||null;
    return null};
  const DIRECT={pass_yds:1,pass_td:1,rush_yds:1,rec_yds:1,receptions:1};
  /* a gap to the line is read against the line or a sensible unit for the market, whichever is bigger, so a 0.5 line can't run away with it */
  const UNIT={pass_yds:40,pass_td:1,completions:4,pass_att:5,interceptions:1,rush_yds:15,rush_att:4,rec_yds:15,receptions:2};
  let ROWS=[],HAS={meta:1,dvp:1,mdl:1,l10:1,avg:1,h2h:1},WK=G.week;
  const SIGS=['meta','dvp','mdl','l10','avg','h2h'],SIGW={meta:8,dvp:7,mdl:7,l10:7,avg:11,h2h:11},sigs=()=>SIGS.filter(k=>HAS[k]);
  function build(){
    WK=ALLL.some(r=>+r.week===G.week)?G.week:((J.betting||{}).week||G.week);
    const v=$$('Src').value,S=v==='mu'?srcs:[v],se=$$('Se').value,by={};
    ALLL.forEach(r=>{if(+r.week!==WK||r.line==null||r.line==='')return;const k=r.player+'|'+r.team+'|'+r.market;(by[k]=by[k]||[]).push(r)});
    const R=Object.values(by).map(A=>{const r0=A[0],m=r0.market;
      const cnt={};A.forEach(r=>cnt[+r.line]=(cnt[+r.line]||0)+1);const ls=A.map(r=>+r.line).sort((a,b)=>a-b),md=ls[ls.length>>1];
      const line=+Object.keys(cnt).sort((a,b)=>cnt[b]-cnt[a]||Math.abs(a-md)-Math.abs(b-md))[0];
      const at=A.filter(r=>+r.line===line),bo=at.filter(r=>dec(r.over_price)).sort((a,b)=>dec(b.over_price)-dec(a.over_price))[0],bu=at.filter(r=>dec(r.under_price)).sort((a,b)=>dec(b.under_price)-dec(a.under_price))[0];
      const ref=at.find(r=>r.p_over_model!=null&&r.p_over_model!=='')||at[0];
      const sl0=r0.slot==='WR4+'?'WR4':r0.slot;
      const u=UNIVERSE.find(x=>x.player===r0.player&&x.team===r0.team)||UNIVERSE.find(x=>x.player===r0.player)||{player:r0.player,team:r0.team,slot:sl0,dslot:sl0,grp:SLOTG(r0.slot),pos:posOf(r0.slot),inj:'1'};
      const oppRaw=r0.opp||'',opp=oppRaw.replace('@',''),grp=u.grp||SLOTG(r0.slot),pos=u.pos||posOf(r0.slot);
      const kD=mpKey(m,grp),dvp=kD&&opp?avg(S.map(s=>{const d=J.dvp[s]&&J.dvp[s][opp];return d&&d.stats[kD]?d.stats[kD].rank:null})):null;
      const pm=ref&&ref.p_over_model!=null&&ref.p_over_model!==''?+ref.p_over_model:null;
      const li=LI[m],Lg=PLOGS[u.ln||u.player]||PLOGS[r0.player]||[],val=l=>+l[li]||0;
      const l10s=li==null?[]:Lg.slice(-10).map(val),l10k=l10s.filter(z=>z>line).length,l10=l10s.length>=4?l10k/l10s.length:null;
      const cur=Lg.filter(l=>l[LOG.season]===LAST_SE),base=li==null?[]:(cur.length>=3?cur:Lg.slice(-10)),av=base.length?base.reduce((t,l)=>t+val(l),0)/base.length:null;
      const den=Math.max(line,UNIT[m]||1),ea=av==null?null:(av-line)/den;
      const vs=li==null||!opp?[]:Lg.filter(l=>l[LOG.opp]===opp&&(!se||l[LOG.season]===+se)),ha=vs.length?vs.reduce((t,l)=>t+val(l),0)/vs.length:null,eh=ha==null?null:(ha-line)/den;
      return {u,pos,grp,m,line,oppRaw,opp,A,at,bo,bu,ref,kD,proxy:!!kD&&!DIRECT[m],dvp,pm,l10,l10n:l10s.length,l10k,av,avN:base.length,avCur:cur.length>=3,ea,ha,hn:vs.length,eh,last:vs.length?vs[vs.length-1]:null}});
    const W=Object.values(MP_W).reduce((a,b)=>a+b,0);
    R.forEach(x=>{const c={dvp:x.dvp==null?null:clamp((NT-x.dvp)/(NT-1)),mdl:x.pm==null?null:clamp(.5+(x.pm-.5)*2.5),l10:x.l10,avg:x.ea==null?null:clamp(.5+x.ea),h2h:x.eh==null?null:clamp(.5+x.eh*Math.min(x.hn,3)/3)};
      let t=0,w=0;Object.entries(MP_W).forEach(([k,wt])=>{if(c[k]!=null){t+=wt*c[k];w+=wt}});
      x.c=c;x.cov=w/W;x.meta=w?50+(100*t/w-50)*(.6+.4*w/W):null});
    ROWS=R;HAS={meta:1,dvp:R.some(x=>x.dvp!=null),mdl:R.some(x=>x.pm!=null),l10:R.some(x=>x.l10!=null),avg:R.some(x=>x.av!=null),h2h:R.some(x=>x.ha!=null)};
    $$('Lens').querySelectorAll('button').forEach(b=>b.hidden=!HAS[b.dataset.l])}
  const keep=x=>{const q=$$('Q').value.toLowerCase();return inU(x.u)&&(!live.size||live.has(x.u.dslot||x.u.slot))&&(!mk.size||mk.has(x.m))&&($$('Inj').value!=='x'||x.u.inj!=='-1')&&(!q||x.u.player.toLowerCase().includes(q))};
  const sv=(x,k)=>k==='meta'?x.meta:k==='dvp'?x.dvp:k==='mdl'?x.pm:k==='l10'?x.l10:k==='avg'?x.ea:k==='h2h'?x.c.h2h:k==='player'?x.u.player:k==='opp'?(x.opp||null):k==='pos'?TPOS.indexOf(x.pos):k==='line'?x.m:null;
  const cmp=(k,asc)=>(a,b)=>{const x=sv(a,k),y=sv(b,k);
    if(x==null||y==null){if(x==null&&y==null)return (b.meta??-1)-(a.meta??-1);return x==null?1:-1}
    return (x<y?-1:x>y?1:0)*(asc?1:-1)||(b.meta??-1)-(a.meta??-1)};
  const f1=v=>v==null?'—':(+v).toFixed(1),fv=(v,m)=>v==null?'—':(m==='pass_td'||m==='interceptions'?v.toFixed(2):v.toFixed(1)),fc=(v,m)=>v==null?'—':m==='pass_td'||m==='interceptions'?v.toFixed(1):v>=10?String(Math.round(v)):v.toFixed(1),gp=(v,x)=>v==null?'—':(v>=x.line?'+':'−')+fv(Math.abs(v-x.line),x.m);
  const nmk=x=>MP_MK[x.m]?MP_MK[x.m][0]:x.m,sk=x=>MP_MK[x.m]?MP_MK[x.m][1]:x.m;
  const lean=v=>v==null?'':v>=55?'leans OVER':v<=45?'leans UNDER':'no real lean';
  const why=x=>[`METAPROP ${x.meta==null?'—':Math.round(x.meta)} of 100 · ${lean(x.meta)} · ${Math.round(100*x.cov)}% of the weight has data`,
    `DVP ${x.dvp==null?'—':`${x.opp} rank ${f1(x.dvp)} of ${NT} allowing ${x.grp}s ${x.kD}${x.proxy?' (proxy)':''}`} → ${x.c.dvp==null?'—':Math.round(100*x.c.dvp)} (weight ${MP_W.dvp})`,
    `model ${x.pm==null?'—':Math.round(100*x.pm)+'% over '+x.line} → ${x.c.mdl==null?'—':Math.round(100*x.c.mdl)} (weight ${MP_W.mdl})`,
    `L10 ${x.l10==null?'—':`cleared ${x.line} in ${x.l10k} of ${x.l10n}`} → ${x.c.l10==null?'—':Math.round(100*x.c.l10)} (weight ${MP_W.l10})`,
    `average ${x.av==null?'—':`${fv(x.av,x.m)} ${x.avCur?'this season':'over his last '+x.avN} (${gp(x.av,x)} vs the line)`} → ${x.c.avg==null?'—':Math.round(100*x.c.avg)} (weight ${MP_W.avg})`,
    `H2H ${x.ha==null?'no prior meeting':`${fv(x.ha,x.m)} in ${x.hn} game${x.hn===1?'':'s'} vs ${x.opp} (${gp(x.ha,x)} vs the line)`} → ${x.c.h2h==null?'—':Math.round(100*x.c.h2h)} (weight ${MP_W.h2h})`].join('\n');
  const lineTip=x=>{const alt=[...new Set(x.A.map(r=>+r.line))].filter(v=>v!==x.line).sort((a,b)=>a-b);
    return `${nmk(x)} ${x.line} · posted at ${x.at.length} of ${x.A.length} books${alt.length?' (others: '+alt.join(' / ')+')':''}${x.bo?` · best over ${mlTxt(+x.bo.over_price)} ${x.bo.book}`:''}${x.bu?` · best under ${mlTxt(+x.bu.under_price)} ${x.bu.book}`:''}${x.ref&&x.ref.proj!=null?` · model projection ${x.ref.proj}${x.ref.q10!=null?` (10–90%: ${x.ref.q10}–${x.ref.q90})`:''}`:''}${x.ref&&x.ref.ev!=null&&x.ref.side?` · bet board: ${x.ref.side} at ${x.ref.ev>=0?'+':''}${x.ref.ev}% EV`:''}`};
  const setL=()=>{const v=$$('Src').value;return v==='mu'?'μ every set':v};
  const ud=(v,t)=>v==null?'':v>=t?'rise':v<=-t?'fall':'';
  const cells=x=>{
    const meta=x.meta==null?'<td class="md gs"><span class="dim">·</span></td>'
      :`<td class="md gs" title="${esc(why(x))}"><span class="badge" style="${gradeStyle(eq(x.meta/100))}">${Math.round(x.meta)}</span></td>`;
    const dvp=x.dvp==null?'<td class="op gs"><span class="dim">·</span></td>'
      :`<td class="op gs" title="${esc(`${x.opp} allows ${x.grp}s ${x.kD}${x.proxy?' (closest stat the DvP tracks)':''} · ${setL()} · rank ${f1(x.dvp)} of ${NT}, 1 = the most`)}"><span class="badge" style="${gradeStyle(x.dvp)}">${Math.round(x.dvp)}</span></td>`;
    const mdl=x.pm==null?'<td class="op"><span class="dim">·</span></td>'
      :`<td class="op" title="${esc(`prop model: ${Math.round(100*x.pm)}% he goes over ${x.line}${x.ref.proj!=null?' · projection '+x.ref.proj:''}${x.ref.q10!=null?` (10–90%: ${x.ref.q10}–${x.ref.q90})`:''}`)}"><span class="badge" style="${gradeStyle(eq(x.c.mdl))}">${Math.round(100*x.pm)}</span></td>`;
    const l10=x.l10==null?'<td class="md hp"><span class="dim">·</span></td>'
      :`<td class="md hp ${x.l10>=.6?'rise':x.l10<=.4?'fall':''}" title="${esc(`cleared ${x.line} in ${x.l10k} of his last ${x.l10n} games`)}"><b>${x.l10k}</b>${x.l10n<10?`<i>/${x.l10n}</i>`:''}</td>`;
    const av=x.av==null?'<td class="md hp"><span class="dim">·</span></td>'
      :`<td class="md hp ${ud(x.ea,.1)}" title="${esc(`${fv(x.av,x.m)} a game ${x.avCur?'this season':'over his last '+x.avN} vs the ${x.line} line (${gp(x.av,x)})`)}"><b>${fc(x.av,x.m)}</b></td>`;
    const h2h=x.ha==null?'<td class="md hp"><span class="dim">·</span></td>'
      :`<td class="md hp ${ud(x.eh,.1)}" title="${esc(`${fv(x.ha,x.m)} a game in ${x.hn} meeting${x.hn===1?'':'s'} with ${x.opp} vs the ${x.line} line (${gp(x.ha,x)})${x.last?` · last: ${x.last[LOG.season]} wk ${x.last[LOG.week]}, ${fv(+x.last[LI[x.m]]||0,x.m)}`:''}`)}"><b>${fc(x.ha,x.m)}</b></td>`;
    const o={meta,dvp,mdl,l10,avg:av,h2h};return sigs().map(k=>o[k]).join('')};
  function col(p){
    const st=sort[p];
    const R=ROWS.filter(x=>(p==='ALL'||x.pos===p)&&keep(x)).sort(cmp(st.k,st.a));
    $$('N'+p).textContent=R.length+(R.length===1?' line':' lines');
    $$('G'+p).textContent=`ranked by ${LBL[st.k]||st.k} · ${setL()} · wk ${WK}`;
    const th=(k,l,tip,cls)=>`<th class="${cls||''}" data-k="${k}" title="${esc(tip||'')}">${l}${st.k===k?(st.a?' ▲':' ▼'):''}</th>`;
    const S=sigs(),wname=p==='ALL'?20:20,wpos=p==='ALL'?5:0,wopp=p==='ALL'?12:15,wln=p==='ALL'?14:18,ws=S.reduce((a,k)=>a+SIGW[k],0),wk=k=>((100-wname-wpos-wopp-wln)*SIGW[k]/ws).toFixed(2);
    const TH={meta:th('meta','META','every signal folded into one score · 0–100, 100 = all say OVER, 0 = all say UNDER · hover a cell for the breakdown','md gs'),
      dvp:th('dvp','DVP','what the opponent allows his slot in this exact stat · rank of '+NT+' · 1 = the most','op gs'),
      mdl:th('mdl','MDL','the prop model\'s chance he goes over the line, %','op'),
      l10:th('l10','L10','times he cleared this line in his last ten games (fewer games shown as k/n)','md'),
      avg:th('avg','AVG','his average this season · green = above the line, red = below · sorts on the gap to the line','md'),
      h2h:th('h2h','H2H','his average in this stat against this opponent · green = above the line, red = below · sorts on the gap, discounted under three meetings','md')};
    $$('B'+p).innerHTML=`<table class="lgt"><colgroup><col style="width:${wname}%">${p==='ALL'?`<col style="width:${wpos}%">`:''}<col style="width:${wopp}%"><col style="width:${wln}%">${S.map(k=>`<col style="width:${wk(k)}%">`).join('')}</colgroup><thead>
      <tr class="hd">${th('player','Player')}${p==='ALL'?th('pos',''):''}${th('opp','Opp',"this week's opponent")}${th('line','Line','the prop and the line most books post · hover for every book\'s price')}
      ${S.map(k=>TH[k]).join('')}</tr></thead><tbody>
      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.u.player)}" title="${esc(x.u.player)} · ${esc(x.u.dslot||x.u.slot)} · ${esc(x.u.team)}${x.meta==null?'':' · META '+Math.round(x.meta)+' · '+lean(x.meta)}">${esc(pshort(x.u.player))}${x.u.inj==='0'?' <span class="inj0">Q</span>':x.u.inj==='-1'?' <span class="injm1">OUT</span>':''}</td>
        ${p==='ALL'?`<td style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</td>`:''}<td>${x.opp?oppcell(x.oppRaw):'<span class="dim">—</span>'}</td><td class="ln" title="${esc(lineTip(x))}"><span class="mpk">${sk(x)}</span>${x.line}</td>${cells(x)}</tr>`).join('')
        ||`<tr><td colspan="${S.length+(p==='ALL'?4:3)}" class="dim">nothing matches</td></tr>`}</tbody></table>`;
    $$('B'+p).querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=h.dataset.k;
      if(st.k===k)st.a=!st.a;else{st.k=k;st.a=!DESC.has(k)}col(p)});
    tWire($$('B'+p));
    const sec=$$('B'+p).closest('.lgcol'),h=sec&&sec.querySelector('h3');if(h)sec.style.setProperty('--h3h',h.offsetHeight+'px');
  }
  function lead(){
    const R=ROWS.filter(keep),top=(f,k,asc,n=3)=>R.filter(x=>sv(x,k)!=null&&(!f||f(x))).sort(cmp(k,asc)).slice(0,n);
    const nm=x=>`<span class="plink" data-p="${esc(x.u.player)}" title="${esc(x.u.player)} · ${esc(x.u.dslot||x.u.slot)} · ${esc(x.u.team)} · ${esc(lineTip(x))}">${esc(pshort(x.u.player))}</span>`;
    const line=(x,v)=>`<div class="mlr"><span style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</span>${nm(x)}<span class="mini">${sk(x)} ${x.line}</span>${v}</div>`;
    const B=(r,st2)=>`<span class="badge" style="${st2}">${r}</span>`;
    const cards=[
      ['best overs · META','g',top(x=>x.meta>=55,'meta',false),x=>B(Math.round(x.meta),gradeStyle(eq(x.meta/100))),'meta'],
      ['best unders · META','r',top(x=>x.meta<=45,'meta',true),x=>B(Math.round(x.meta),gradeStyle(eq(x.meta/100))),'meta'],
      ['softest stat · DVP','',top(null,'dvp',true),x=>B(Math.round(x.dvp),gradeStyle(x.dvp)),'dvp'],
      ['prop model · over','',top(null,'mdl',false),x=>B(Math.round(100*x.pm)+'%',gradeStyle(eq(x.c.mdl))),'mdl'],
      ['hit rate · L10','',top(x=>x.l10n>=8,'l10',false),x=>`<b class="rise">${x.l10k}/${x.l10n}</b>`,'l10'],
      ['average vs line','',top(null,'avg',false),x=>`<b class="rise">${gp(x.av,x)}</b>`,'avg'],
      ['head to head','',top(x=>x.hn>0,'h2h',false),x=>`<span class="mv"><b class="${ud(x.eh,.1)}">${fv(x.ha,x.m)}</b><span class="mini"> ${x.hn}g</span></span>`,'h2h']].filter(c=>HAS[c[4]]);
    $$('Lead').innerHTML=cards.map(([t,tone,L,val])=>`<div class="mlc ${tone}"><div class="mlh">${t}</div>${L.map(x=>line(x,val(x))).join('')||'<div class="mini dim">nothing on the board</div>'}</div>`).join('');
    tWire($$('Lead'))}
  const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead()};
  const all=()=>{build();if(!HAS[lens])$$('Lens').querySelector('button[data-l="meta"]').click();cols()};
  ['Src','Se','Inj'].forEach(i=>$$(i).onchange=all);$$('Q').oninput=cols;
  $$('Slots').querySelectorAll('button').forEach(b=>b.onclick=()=>{const v=b.dataset.s;
    if(!v)live.clear();else live.has(v)?live.delete(v):live.add(v);
    $$('Slots').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.s?live.has(x.dataset.s):live.size===0));cols()});
  $$('Mk').querySelectorAll('button').forEach(b=>b.onclick=()=>{const v=b.dataset.m;
    if(!v)mk.clear();else mk.has(v)?mk.delete(v):mk.add(v);
    $$('Mk').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.m?mk.has(x.dataset.m):mk.size===0));cols()});
  $$('Lens').querySelectorAll('button').forEach(b=>b.onclick=()=>{lens=b.dataset.l;
    $$('Lens').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));
    Object.keys(sort).forEach(p=>sort[p]={k:lens,a:!DESC.has(lens)});['ALL'].concat(TPOS).forEach(col)});
  all();RR.push(all);
}

/* ---------------- Weeklies (F6 TEST) — the touchdown lookback ----------------''')
open(P, 'w', encoding='utf-8').write(s)
print('patch_v23: METAPROP added')
