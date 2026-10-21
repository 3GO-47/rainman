"""v32 — every F6 TEST summary tile opens the history behind it; METAPROP / Depth Delta / Backtest follow the week selector;
Backtest shows in-sample (wks 4-6) vs out-of-sample (wk 7+). Additive; rerunnable (asserts exact match counts)."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'v32: every summary tile opens the history behind it' in s:
    print('already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, ('match count %d != %d for: %s' % (c, n, old[:90]))
    s = s.replace(old, new)

def ins_before(anchor, text):
    rep(anchor, text + anchor)

def ins_after(anchor, text):
    rep(anchor, anchor + text)

# ---------- CSS ----------
ins_after(".kpi[data-go]{cursor:pointer}", "\n/* v32 tile histories */[data-th]{cursor:pointer}[data-th]:hover{border-color:#4a4b52}"
    ".kpi[data-th]::after,.wkt[data-th]::after{content:'history ›';display:block;margin-top:5px;font:600 9px var(--mono);letter-spacing:.06em;color:var(--acc)}"
    ".mlc[data-th] .mlh::after{content:' · full list ›';font:600 9px var(--mono);letter-spacing:.06em;color:var(--acc)}"
    ".thh4{margin:12px 0 4px;font-size:11px;color:var(--dim2);text-transform:uppercase;letter-spacing:.08em}table.thh th{white-space:nowrap}table.thh td.n{text-align:right;white-space:nowrap}"
    ".btio{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin:12px 0 4px}"
    ".btio .c{background:var(--panel);border:1px solid var(--edge);border-top:3px solid var(--green);border-radius:8px;padding:11px 14px;min-width:0;cursor:pointer}.btio .c.r{border-top-color:var(--red)}.btio .c.a{border-top-color:#e8b100}.btio .c:hover{border-color:var(--edge2);background:#ffffff05}"
    ".btio .k{font:600 10px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--dim)}.btio .h{font:700 22px var(--mono);margin:4px 0 4px;color:var(--txt);display:flex;align-items:center;gap:8px;flex-wrap:wrap}.btio .s{font-size:12.5px;line-height:1.45;color:var(--dim)}"
    ".btio .bd{font:700 9.5px var(--mono);letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border-radius:3px}.btio .c::after{content:'history \u203a';display:block;margin-top:7px;font:600 9.5px var(--mono);letter-spacing:.06em;color:var(--acc)}\n")

# ---------- helpers ----------
helpers = r'''/* ---------- v32: every summary tile opens the history behind it ---------- */
const THIST={};let THN=0;
const thReg=p=>{const id='th'+(++THN);THIST[id]=p;return id};
/* give the i-th tile in an html string its history (null = leave that tile alone); a payload may be a function (built on click) */
function thSeq(html,list){let i=0;return html.replace(/<div class="(kpi|wkt|mlc)(?=[\s"])([^"]*)"/g,(m,a,b)=>{const p=list[i++];return p?`<div class="${a}${b}" data-th="${thReg(p)}"`:m})}
/* same, for tiles already in the DOM */
function thDom(root,list){if(!root)return;[...root.querySelectorAll('.kpi,.wkt,.mlc')].forEach((e,i)=>{const p=list[i];if(p)e.dataset.th=thReg(p)})}
/* a history table: cols = labels or {l,t:tip,lo:true = lower is better,g:false = no shading} · a cell = text/html, a number, or {v:number,h:html} · every column sorts, numbers are shaded by rank */
function thTable(cols,rows){if(!rows||!rows.length)return '<p class="note mini">nothing recorded yet</p>';
  const C=cols.map(c=>typeof c==='string'?{l:c}:c);
  const val=x=>x&&typeof x==='object'&&'v' in x?x.v:(typeof x==='number'?x:null);
  const shade=C.map((c,j)=>{if(c.g===false)return null;const vs=rows.map(r=>val(r[j])).filter(v=>v!=null&&!isNaN(v));if(vs.length<2||new Set(vs).size<2)return null;const srt=vs.slice().sort((a,b)=>c.lo?a-b:b-a);return v=>gradeStyle(srt.indexOf(v)+1,srt.length)});
  const cell=(x,j)=>{const v=val(x);const h=x&&typeof x==='object'&&'h' in x?x.h:(x==null||x===''?'<span class="dim">—</span>':typeof x==='number'?(Number.isInteger(x)?String(x):x.toFixed(1)):String(x));
    return v!=null&&shade[j]?`<td class="n" data-v="${v}"><span class="badge" style="${shade[j](v)}">${h}</span></td>`:`<td${v!=null?` class="n" data-v="${v}"`:''}>${h}</td>`};
  return `<div class="tscroll"><table class="fx thh"><thead><tr>${C.map(c=>`<th title="${esc(c.t||'')}">${c.l}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr${r.hi?' class="pl"':''}>${r.map(cell).join('')}</tr>`).join('')}</tbody></table></div>`}
function thOpen(id){let p=THIST[id];if(!p)return;if(typeof p==='function')p=p();if(!p)return;
  const secs=(p.sections||[p]).map(x=>`${x.h?`<h4 class="thh4">${x.h}</h4>`:''}${x.note?`<p class="note mini">${x.note}</p>`:''}${x.html||thTable(x.cols||[],x.rows||[])}`).join('');
  const o=document.getElementById('ppModal');if(o)o.remove();
  document.body.insertAdjacentHTML('beforeend',`<div class="modal" id="ppModal"><div class="modalbox wide"><button class="mclose" id="ppX">ESC &#10005;</button><h3>${p.title||'history'} <span class="f">${p.sub||''}</span></h3>${secs}</div></div>`);wireModal()}
document.addEventListener('click',e=>{const t=e.target.closest('[data-th]');if(!t||e.target.closest('button,select,input,a[href],.pp,.plink,.wksig,.slotchip,.tc,[data-c],[data-go]'))return;e.stopPropagation();thOpen(t.dataset.th)});
'''
ins_before("function sortableAll(root)", helpers)

# ---------- Injuries (F4 Intel) ----------
inj = r'''
    const injCols=['player','team','side','role','status','injury','practice','return','updated','source'];
    const injRow=r=>[pn(r.player,r.team,true),tcell(r.team),r.side,r.role,r.status,r.injury||'',r.practice||'',r.ret||'',r.updated||'',r.source];
    const injList=(t,L,sub)=>({title:t+' · week '+wk,sub:sub||(L.length+' players · every column sorts · click a name for his card'),cols:injCols,rows:L.map(injRow)});
    const kpisH=thSeq(kpis,[()=>injList('listed',listed),()=>injList('out / IR',out),()=>injList('questionable / doubtful / limited',q),()=>injList('starting defenders down',defOut,'rank-1 or rank-2 defenders at the positions that move a matchup'),
      ...(lifts[0]?[()=>({title:'injury lifts · week '+wk,sub:'every slot that gains from a missing defender, biggest first',cols:['offense','slot','starter','vs',{l:'missing',g:false},{l:'lift',t:'extra production the slot can expect'}],rows:lifts.map(l=>[tcell(l.off),slotchip(l.sl),l.u?pn(l.u.player,l.off,true):'—',tcell(l.def),l.L.who.map(r=>pshort(r.player)).join(', '),{v:l.L.pct,h:'+'+l.L.pct.toFixed(0)+'%'}])})]:[]),
      ()=>{const by={};listed.forEach(r=>{const k=r.source;by[k]=by[k]||{n:0,d:''};by[k].n++;if((r.updated||'')>by[k].d)by[k].d=r.updated||''});return {title:'sources',sub:'who reported what',cols:['source','players listed','newest report'],rows:Object.entries(by).map(([k,v])=>[k,v.n,v.d])}}]);'''
i = s.index("    const kpis=`<div class=\"kpis\">${kp('listed',listed.length,'players on a report this week')}")
j = s.index('\n', i)
s = s[:j] + inj + s[j:]
a_i = s.index("function injuriesView("); b_i = s.index("\n}", a_i); seg = s[a_i:b_i]
c = seg.count("el.innerHTML=kpis+liftT+"); assert c == 1, c
s = s[:a_i] + seg.replace("el.innerHTML=kpis+liftT+", "el.innerHTML=kpisH+liftT+") + s[b_i:]

# ---------- API ----------
api = r'''    const apiHist=()=>({title:'The Odds API · credits by day',sub:`${days.length} days logged · ${L.length} calls · plan ${plan.toLocaleString()} / month`,sections:[
      {cols:['day',{l:'calls',g:false},{l:'paid',g:false},{l:'credits',lo:true},{l:'by reason',g:false}],rows:days.slice().reverse().map(d=>Object.assign([d,byDay[d].calls,byDay[d].paid,byDay[d].cost,Object.entries(byDay[d].by).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`${k} ${v}`).join(' · ')],{hi:d===today}))},
      {h:'by reason',cols:['reason',{l:'calls',g:false},{l:'credits',lo:true}],rows:Object.entries(byR).sort((a,b)=>b[1].cost-a[1].cost).map(([k,v])=>[k,v.calls,v.cost])},
      {h:'by league',cols:['league',{l:'calls',g:false},{l:'credits',lo:true}],rows:Object.entries(byLg).sort((a,b)=>b[1].cost-a[1].cost).map(([k,v])=>[k,v.calls,v.cost])}]});
    const kpisH=thSeq(kpis,[apiHist,apiHist,apiHist,apiHist,apiHist,apiHist]);
'''
ins_before("    const mx=Math.max(1,...last30.map(d=>byDay[d].cost));", api)
rep("    el.innerHTML=kpis+chart+`<div class=\"grid2 hgl\">${reasons}${leagues}</div>`+games+logT+policy;sortableAll(el);logoize(el)}",
    "    el.innerHTML=kpisH+chart+`<div class=\"grid2 hgl\">${reasons}${leagues}</div>`+games+logT+policy;sortableAll(el);logoize(el)}")

# ---------- Picks / Card v2: week-by-week record of the card ----------
card = r'''    thDom($('#'+px+'gmOut').querySelector('.kpis'),(()=>{const h=()=>{const wks=[...new Set(ALL.filter(pass).map(p=>+p.week))].sort((a,b)=>a-b);
        const rows=wks.map(w=>{const rr=sortRows(dedupe(ALL.filter(p=>+p.week===w&&pass(p)))),r=pkRec(rr),top=rr.slice().sort((a,b)=>(pkEdgePct(b)??-9)-(pkEdgePct(a)??-9))[0];
          return Object.assign([w,rr.length,r.graded||0,r.graded?pkWL(r):'—',r.graded?{v:r.units,h:pkU(r.units)}:null,r.graded?{v:r.hit,h:pkPct(r.hit,1)}:null,top?(top.player||top.team||'')+' '+pkEdge(top):'—'],{hi:w===wk})});
        return {title:(px?'Card v2':'the card')+' · week by week',sub:'every frozen position that passes the filters on screen · the selected week is tinted',cols:[{l:'week',g:false},{l:'positions',g:false},{l:'graded',g:false},{l:'record',g:false},'units',{l:'hit',t:'graded wins over graded'},{l:'biggest edge',g:false}],rows}};return [h,h,h,h]})());
'''
ins_after("    logoize($('#'+px+'gmOut'));\n", card)


# ---------- Weeklies: verdict tiles, position tiles and the TD Picks box ----------
wkv = r"""    {const wkSigH=(sg,pos)=>()=>{const rows=AL.map(a=>{const m=a.P.filter(sg.f).filter(x=>!pos||x.pos===pos),k=m.filter(x=>x.td>0).length,hr=m.length?k/m.length:null,fp=pos?a.P.filter(x=>x.pos===pos):a.P,fb=fp.length?fp.filter(x=>x.td>0).length/fp.length:null;
        return Object.assign([a.w,m.length,k,hr!=null?{v:hr,h:wkPct(hr)}:null,fb!=null?{v:fb,h:wkPct(fb)}:null,hr!=null&&fb?{v:hr/fb,h:wkX(hr/fb)}:null,m.filter(x=>x.td>0).slice(0,4).map(x=>pshort(x.name)).join(', ')],{hi:a.w===W})});
        return {title:esc(sg.lbl)+(pos?' · '+pos:'')+' · week by week',sub:esc(sg.long||'')+' · '+S+' · the week on screen is tinted',cols:[{l:'week',g:false},{l:'carried it',g:false},{l:'scored',g:false},{l:'hit rate'},{l:'field'},{l:'vs the field',t:'hit rate over the field rate'},{l:'who scored',g:false}],rows}};
      thDom($('#wkSeason'),[steady?wkSigH(steady):null,shaky&&shaky!==steady?wkSigH(shaky):null,fade?wkSigH(fade):null].filter(Boolean));
      thDom($('#wkPos4'),TPOS.map(p=>{const b=TR.posB[p];const best=TR.sig.filter(x=>x.kind==='pos'&&x.pp[p].n>=40).sort((a,c)=>c.pp[p].hr-a.pp[p].hr)[0];return best&&b.hr?wkSigH(best,p):null}))}
"""
ins_before("    /* ---- the current week: who carries what works ---- */", wkv)
tdbox = r"""      {const bx=()=>({title:`TD Picks model · week ${W}`,sub:`${L.length} players rated before kickoff, by the model's chance · ✓ scored · ✗ didn't`,cols:[{l:'#',g:false},'player',{l:'slot',g:false},{l:'chance'},{l:'scored',g:false}],rows:L.slice().sort((a,b)=>b.p-a.p).map((x,i)=>[i+1,pn(x.n,x.t,true),String(x.b),{v:x.p,h:wkPct(x.p)},x.hit?'<b style="color:var(--green)">✓</b>':'<b style="color:var(--red)">✗</b>'])});
        thDom(box,[bx,bx,bx,bx])}
"""
ins_before("      const g=hd.querySelector('[data-go]');if(g)g.onclick=()=>go('tdpicks')})();", tdbox)

# ---------- Card v2: the edge-bucket tiles open the graded positions behind them ----------
bk = r"""    {const T2=ft==='ALL'?'PROP':ft,K=$('#'+px+'gmOut').querySelectorAll('.kpis')[1];if(K&&typeof EB!=='undefined'&&typeof GR!=='undefined')thDom(K,EB.map(([lo,hi])=>{const Q=GR.filter(q=>q.type===T2&&pkEdgePct(q)!=null&&pkEdgePct(q)>=lo&&pkEdgePct(q)<hi);return pkRec(Q).graded?()=>({title:`${PK_TL[T2]} · edge ${bLbl(lo,hi)}`,sub:`${Q.length} graded positions behind the bucket`,cols:[{l:'week',g:false},'player','team',{l:'opp',g:false},{l:'market',g:false},{l:'side',g:false},{l:'line',g:false},{l:'price',g:false},'edge',{l:'result',g:false}],rows:Q.map(q=>[+q.week,q.player?pn(q.player,q.team,true):'',tcell(q.team),q.opp||'',q.market||'',String(q.side??''),q.line??'',q.price!=null&&q.price!==''?mlTxt(+q.price):'—',{v:pkEdgePct(q),h:pkEdge(q)},q.result==='W'?'<b style="color:var(--green)">W</b>':q.result==='L'?'<b style="color:var(--red)">L</b>':String(q.result||'')])}):null}).filter(Boolean))}
"""
ins_before("    thDom($('#'+px+'gmOut').querySelector('.kpis'),(()=>{const h=()=>{const wks=", bk)


# ---------- Markets (F11 Bets + Markets v2): the market tiles open the rows behind them ----------
mkt = r"""
    {const row=r=>[pn(r.u.player,r.u.team,true),tcell(r.u.team),r.o?oppcell(r.o):'',slotchip(r.u.slot),{v:r.own,h:fmt(r.own,mk.dec)},r.l5!=null?{v:r.l5,h:fmt(r.l5,mk.dec)}:null,{v:r.allowed,h:fmt(r.allowed,mk.dec)},r.rank!=null?{v:r.rank,h:'#'+r.rank}:null,{v:r.score,h:r.score.toFixed(mk.dec||1)},r.line!=null?{v:r.line,h:`${r.line} <span class="mini">${r.src||''}</span>`}:null,r.edge!=null?{v:r.edge,h:(r.edge>0?'over ':'under ')+Math.abs(100*r.edge).toFixed(0)+'%'}:null];
      const cols=['player','team',{l:'opp',g:false},{l:'slot',g:false},{l:'his /gm',t:'his own average per game this season'},{l:'last 5'},{l:'opp allows',t:'what the opponent allows per game to his slot'},{l:'rank',lo:true,t:'1 = allows the most'},{l:'score',t:'his volume × the matchup ratio'},{l:'line',g:false},{l:'model − Kalshi',t:'the model\'s side and the gap to the exchange'}];
      const tb=(t,sub,L)=>()=>({title:`${mk.label} · ${t}`,sub:`${sub} · wk ${W} · ${L.length} players`,cols,rows:L.map(row)});
      const byS=R.slice().sort((a,b)=>b.score-a.score),lined=R.filter(r=>r.line!=null),gap=R.filter(r=>r.edge!=null).sort((a,b)=>Math.abs(b.edge)-Math.abs(a.edge));
      thDom($('#'+px+'mkKpi'),[tb('every starter','the whole board',R),top?tb('volume × matchup','ranked by score, best first',byS):null,tb('lines posted','every starter with a posted line',lined),gap.length?tb('model − Kalshi gaps','ranked by the size of the gap',gap):null,mk.proxy?()=>({title:`${mk.label} · matchup column`,sub:mk.proxy,html:`<p class="note">${esc(mk.proxy)}</p>`}):null].filter((x,i,a)=>x!==null))}
"""
ins_after("${mk.proxy?kpi('matchup column',mk.proxy.split(':')[0],mk.proxy.split(':')[1].trim()):''}</div>`;", mkt)
atd = r"""
    {const row=r=>[pn(r.u.player,r.u.team,true),tcell(r.u.team),r.o?oppcell(r.o):'',slotchip(r.u.slot),{v:r.own,h:r.own.toFixed(2)},{v:r.allowed,h:(+r.allowed).toFixed(2)},r.rank!=null?{v:r.rank,h:'#'+r.rank}:null,{v:r.score,h:(+r.score).toFixed(2)},r.pm!=null?{v:r.pm,h:(100*r.pm).toFixed(0)+'%'}:null,r.kp!=null?{v:r.kp,h:(100*r.kp).toFixed(0)+'%'}:null,r.edge!=null?{v:r.edge,h:(r.edge>0?'+':'')+(100*r.edge).toFixed(0)+'%'}:null];
      const cols=['player','team',{l:'opp',g:false},{l:'slot',g:false},{l:'TD/gm',t:'his TDs per game this season'},{l:'opp allows',t:'TDs the opponent allows per game to his slot'},{l:'rank',lo:true,t:'1 = allows the most'},{l:'score'},{l:'model',t:'the model\'s chance he scores'},{l:'Kalshi',t:'the exchange yes price'},{l:'gap',t:'model minus Kalshi'}];
      const tb=(t,sub,L)=>()=>({title:`anytime TD · ${t}`,sub:`${sub} · wk ${W} · ${L.length} players`,cols,rows:L.map(row)});
      const e0=R.filter(r=>r.edge!=null).sort((a,b)=>Math.abs(b.edge)-Math.abs(a.edge));
      thDom($('#'+px+'mkKpi'),[tb('every starter','the whole board',R),top?tb('rate × end zone','ranked by score, best first',R.slice().sort((a,b)=>b.score-a.score)):null,tb('Kalshi priced','every starter with an exchange price',R.filter(r=>r.kp!=null)),e0.length?tb('model − Kalshi gaps','ranked by the size of the gap',e0):null].filter(x=>x!==null))}
"""
ins_after("% vs ${(100*e.kp).toFixed(0)}% — reference, not a pick`,'a'):''})()}</div>`;", atd)
gl = r"""
    {const gh=()=>{const t=$('#'+px+'mkOut').querySelector('table.mkt');return {title:`game lines · wk ${W}`,sub:`${gs.length} games · Kalshi exchange mids, DraftKings consensus and the model, side by side`,html:t?t.outerHTML.replace(/ id="[^"]*"/g,''):'<p class="note mini">nothing posted yet</p>'}};
      thDom($('#'+px+'mkKpi'),[gh,gh,gh])}
"""
ins_after("(DraftKings consensus)')}</div>`;", gl)

# ---------- META / METAPROP: the full ranked list behind each lead card ----------
rep("const R=ROWS.filter(keep),top=(f,k,asc,n=3)=>R.filter(x=>sv(x,k)!=null&&(!f||f(x))).sort(cmp(k,asc)).slice(0,n);",
    "const R=ROWS.filter(keep),top=(f,k,asc,n=60)=>R.filter(x=>sv(x,k)!=null&&(!f||f(x))).sort(cmp(k,asc)).slice(0,n);", 2)
rep("$$('Lead').innerHTML=cards.map(([t,tone,L,val])=>`<div class=\"mlc ${tone}\"><div class=\"mlh\">${t}</div>${L.map(x=>line(x,val(x))).join('')||'<div class=\"mini dim\">nothing on the board</div>'}</div>`).join('');",
    "$$('Lead').innerHTML=cards.map(([t,tone,L,val])=>thSeq(`<div class=\"mlc ${tone}\"><div class=\"mlh\">${t}</div>${L.slice(0,3).map(x=>line(x,val(x))).join('')||'<div class=\"mini dim\">nothing on the board</div>'}</div>`,[()=>({title:t,sub:`every player on the board, ranked · week ${typeof WK!=='undefined'?WK:G.week} · ${L.length} shown`,html:`<div class=\"mlc ${tone}\" style=\"max-width:520px\">${L.map(x=>line(x,val(x))).join('')||'<div class=\"mini dim\">nothing on the board</div>'}</div>`})])).join('');", 2)

# ---------- Weeklies: the six numbers, week by week ----------
rep("    const best=posQ.slice().sort((a,b)=>b.hr-a.hr||b.lift-a.lift)[0],worst=posQ.slice().sort((a,b)=>a.lift-b.lift||a.hr-b.hr)[0];",
    "    const six=(a,pq)=>{const best=pq.slice().sort((x,y)=>y.hr-x.hr||y.lift-x.lift)[0],worst=pq.slice().sort((x,y)=>x.lift-y.lift||x.hr-y.hr)[0];const bs={};a.P.forEach(x=>{const o=bs[x.grp]=bs[x.grp]||{g:x.grp,n:0,k:0};o.n++;if(x.td>0)o.k++});\n"
    "      const sl=Object.values(bs).filter(o=>o.n>=5).map(o=>Object.assign(o,{r:o.k/o.n})).sort((x,y)=>y.r-x.r);const dv={};a.P.forEach(x=>{if(x.td>0){const o=dv[x.opp]=dv[x.opp]||{d:x.opp,n:0,who:[]};o.n+=x.td;o.who.push(x)}});return {best,worst,sl,lk:Object.values(dv).sort((x,y)=>y.n-x.n)[0]}};\n"
    "    const best=posQ.slice().sort((a,b)=>b.hr-a.hr||b.lift-a.lift)[0],worst=posQ.slice().sort((a,b)=>a.lift-b.lift||a.hr-b.hr)[0];")
wk6 = r'''    {const wkH=()=>{const rows=F.weeks.filter(w=>w<=W).map((w,i)=>{const a=AL[i],pq=a.sig.filter(z=>live.includes(z.id)&&z.n>=a.minN&&z.hr!=null&&z.kind==='pos'),x=six(a,pq);
        return Object.assign([w,a.tds,{v:a.sc.length,h:`${a.sc.length} / ${a.P.length}`},{v:a.base,h:wkPct(a.base)},x.best?`${esc(x.best.lbl)} <b>${wkPct(x.best.hr)}</b>`:'—',x.worst?`${esc(x.worst.lbl)} <b>${wkPct(x.worst.hr)}</b>`:'—',x.sl.length?`${x.sl[0].g} ${wkPct(x.sl[0].r)}`:'—',x.lk?`${tcell(x.lk.d)} ${x.lk.n}`:'—'],{hi:w===W})});
        return {title:`${S} · week by week`,sub:'the six tiles for every recorded week · the week on screen is tinted',cols:[{l:'week',g:false},'TDs',{l:'scored / field',t:'players who scored a TD over players in view'},{l:'field rate'},{l:'best signal',g:false},{l:'weakest',g:false},{l:'best slot',g:false},{l:'leakiest defense',g:false}],rows}};
      thDom($('#wkTiles'),[wkH,wkH,wkH,wkH,wkH,wkH])}
'''
ins_before("    /* ---- the TD Picks model's own call for this week, graded (v22) ---- */", wk6)

# ---------- Category Grid (wkNext): the tiles, week by week ----------
wg = r'''    {const wgH=()=>{const wks=F.weeks.concat(F.weeks.length?[Math.max(...F.weeks)+1]:[]).filter(w=>w>=2);
        const rows=wks.map(w=>{const d=wgData(wkLive,'cur',null,w),R2=d.R.filter(x=>inU(x.u)&&inP(x.pos)),B2=d.best.filter(x=>inU(x.u)&&inP(x.pos)),g2=R2.filter(x=>x.done),k2=g2.filter(x=>x.done.td>0).length,t2=d.PK[0];
          return Object.assign([w,R2.length,t2?esc(WG_AB[t2.s.id]||t2.s.lbl):'—',R2.filter(x=>x.cat>=3).length,B2[0]?pn(B2[0].name,B2[0].team,true)+(B2[0].done?(B2[0].done.td>0?' <b style="color:var(--green)">✓</b>':' <b style="color:var(--red)">✗</b>'):''):'—',g2.length?{v:k2/g2.length,h:`${k2} / ${g2.length} · ${wkPct(k2/g2.length)}`}:null,d.base!=null?{v:d.base,h:wkPct(d.base)}:null],{hi:w===NX})});
        return {title:'Category Grid · week by week',sub:'each week scored only from the weeks before it · the week on screen is tinted',cols:[{l:'week',g:false},{l:'on the slate',g:false},{l:'most consistent',g:false},'carry 3+',{l:'top pick',g:false},{l:'graded',t:'listed players who scored'},{l:'field',t:'everyone on the slate who scored'}],rows}};
      thDom($('#wkTiles'),[wgH,wgH,wgH,wgH,wgH])}
'''
ins_before("    const by=r=>R.filter(x=>r.s.f(x))", wg)

# ---------- TD Picks: the tiles, week by week ----------
tp = r'''    {const tpH=()=>{const rows=[];for(let w=1;w<=NWK;w++){const b=tdBoard(w);if(!b||b.m==='none')continue;const P2=b.P.filter(keep),g2=P2.filter(x=>x.res!=null),k2=g2.filter(x=>x.res>0).length,T2=g2.slice().sort((x,y)=>y.p-x.p).slice(0,10),k10=T2.filter(x=>x.res>0).length,L2=P2.filter(x=>x.tier==='lock'),Lg=L2.filter(x=>x.res!=null),top=P2.slice().sort((x,y)=>y.p-x.p)[0];
        rows.push(Object.assign([w,{live:'live',wf:'final',pre:'grading',early:'early look'}[b.m]||b.m,b.g||0,P2.length,L2.length,Lg.length?{v:Lg.filter(x=>x.res>0).length/Lg.length,h:`${Lg.filter(x=>x.res>0).length} / ${Lg.length}`}:null,T2.length?{v:k10/T2.length,h:`${k10} / ${T2.length}`}:null,g2.length?{v:k2/g2.length,h:`${k2} / ${g2.length} · ${pct(k2/g2.length)}`}:null,top?pn(top.n,top.t||top.team||'',true)+' '+pct(top.p):'—'],{hi:w===BW}))}
        return {title:'TD Picks · week by week',sub:'every board, rated blind from the games before it · the week on screen is tinted',cols:[{l:'week',g:false},{l:'board',g:false},{l:'games',g:false},{l:'players',g:false},{l:'locks',g:false},{l:'locks scored'},{l:'top 10 scored'},{l:'graded scored'},{l:'top pick',g:false}],rows}};
      thDom($('#tpTiles'),[tpH,tpH,tpH,tpH,tpH,tpH])}
'''
ins_before("    /* the board: four positions */", tp)


# ---------- Category Grid lead cards: the full list behind the top 3 / top 5 ----------
rep("""    ${L.slice(0,3).map(x=>`<div class="mlr"><span style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</span>${wgName(x)}<span class="mini">${x.opp?oppcell(x.raw):''}</span>${x.tp?`<b style="color:${wgTpc(x.tp.p)}">${Math.round(100*x.tp.p)}%</b>`:'<span class="dim">·</span>'}</div>`).join('')||'<div class="mini dim">nobody carries it in</div>'}</div>`}""",
    """    ${L.slice(0,3).map(wgRow).join('')||'<div class="mini dim">nobody carries it in</div>'}</div>`,[()=>({title:esc(r.s.lbl),sub:`${esc(r.s.long||'')} · beat the field ${r.bw}/${r.qw} weeks · ${wkX(r.lift)} · ${r.k}/${r.n} scored · ${L.length} carry it in, by TD chance`,html:`<div class="mlc ${tone}" style="max-width:520px">${L.map(wgRow).join('')||'<div class="mini dim">nobody carries it in</div>'}</div>`})])}
const wgRow=x=>`<div class="mlr"><span style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</span>${wgName(x)}<span class="mini">${x.opp?oppcell(x.raw):''}</span>${x.tp?`<b style="color:${wgTpc(x.tp.p)}">${Math.round(100*x.tp.p)}%</b>`:'<span class="dim">·</span>'}</div>`;
const wgRow5=x=>`<div class="mlr"><span style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</span>${wgName(x)}<span class="mini">${x.opp?oppcell(x.raw):''}</span><span class="mv"><b title="consistent categories he carries in">${x.cat}</b> ${x.tp?`<b style="color:${wgTpc(x.tp.p)}">${Math.round(100*x.tp.p)}%</b>`:'<span class="dim">·</span>'}</span></div>`;""")
rep("""function wgCatCard(r,tone,L){const pip=v=>`<i class="pip ${v>0?'w':v<0?'l':'o'}"></i>`;
  return `<div class="mlc ${tone}">""", """function wgCatCard(r,tone,L){const pip=v=>`<i class="pip ${v>0?'w':v<0?'l':'o'}"></i>`;
  return thSeq(`<div class="mlc ${tone}">""")
rep("""function wgBestCard(L,W0){return `<div class="mlc g"><div class="mlh">best picks · week ${W0}</div><div class="wgs"><span>most consistent categories carried in, then TD chance</span></div>
    ${L.slice(0,5).map(x=>`<div class="mlr"><span style="color:${POSC[x.pos]}">${posIcon(x.pos,10)}</span>${wgName(x)}<span class="mini">${x.opp?oppcell(x.raw):''}</span><span class="mv"><b title="consistent categories he carries in">${x.cat}</b> ${x.tp?`<b style="color:${wgTpc(x.tp.p)}">${Math.round(100*x.tp.p)}%</b>`:'<span class="dim">·</span>'}</span></div>`).join('')||'<div class="mini dim">nobody carries one in</div>'}</div>`}""",
    """function wgBestCard(L,W0){return thSeq(`<div class="mlc g"><div class="mlh">best picks · week ${W0}</div><div class="wgs"><span>most consistent categories carried in, then TD chance</span></div>
    ${L.slice(0,5).map(wgRow5).join('')||'<div class="mini dim">nobody carries one in</div>'}</div>`,[()=>({title:`best picks · week ${W0}`,sub:`everyone carrying a consistent category in · ${L.length} players · categories carried, then TD chance`,html:`<div class="mlc g" style="max-width:520px">${L.map(wgRow5).join('')||'<div class="mini dim">nobody carries one in</div>'}</div>`})])}""")

# ---------- Weeklies signal pane: the signal, week by week ----------
rep("CUR={S,W,st,TR,AH,W0,SG,keepU};", "CUR={S,W,st,TR,AH,W0,SG,keepU,F,keep};")
rep("const {S:S0,W:W1,st,TR,AH,W0,SG,keepU}=CUR;", "const {S:S0,W:W1,st,TR,AH,W0,SG,keepU,F,keep}=CUR;")
rep("\n      <div class=\"ppk\" data-mg=\"1\">${tiles.join('')}</div>",
    "\n      <div class=\"ppk\" data-mg=\"1\">${thSeq(tiles.join(''),tiles.map(()=>sigH))}</div>")
sigh = r'''    const sigH=()=>{const rows=(F&&F.weeks||[]).map(w=>{const a=wkStats(F,w,keep,SG);const m=a.P.filter(qual),k=m.filter(x=>x.td>0).length,hr=m.length?k/m.length:null;
        return Object.assign([w,m.length,k,hr!=null?{v:hr,h:wkPct(hr)}:null,a.base!=null?{v:a.base,h:wkPct(a.base)}:null,hr!=null&&a.base?{v:hr/a.base,h:wkX(hr/a.base)}:null,m.filter(x=>x.td>0).slice(0,4).map(x=>pshort(x.name)).join(', ')],{hi:w===W1})});
      return {title:esc(lbl)+' · week by week',sub:esc(long)+' · the week on screen is tinted',cols:[{l:'week',g:false},{l:'carried it',g:false},{l:'scored',g:false},{l:'hit rate'},{l:'field'},{l:'vs the field',t:'hit rate over the field rate'},{l:'who scored',g:false}],rows}};
'''
ins_before("    const aTab=(A,W0)=>A.length?`<table class=\"fx wkp\">", sigh)

# ---------- METAPROP follows the week selector ----------
rep("    WK=ALLL.some(r=>+r.week===G.week)?G.week:((J.betting||{}).week||G.week);",
    "    WK=ALLL.some(r=>+r.week===G.week)?G.week:((J.betting||{}).week||G.week);mpWeekNote();")
mpnote = r'''  /* v32: the books' full prop sheet is kept only for the live week — say so, and for an earlier week show the card's graded props instead */
  function mpWeekNote(){const LW=(J.betting||{}).week||G.week;let n=$$('WkNote');if(!n){n=document.createElement('div');n.id=px+'WkNote';$(root).insertBefore(n,$(root).children[1]||null)}
    const past=(J.picksAll||[]).filter(p=>p.type==='PROP'&&+p.week===G.week);
    if(G.week===LW){n.innerHTML='';n.hidden=true;return}
    n.hidden=false;
    const res=r=>r.result==='W'?'<b style="color:var(--green)">W</b>':r.result==='L'?'<b style="color:var(--red)">L</b>':r.result==='P'?'P':'<span class="dim">open</span>';
    const tbl=past.length?thTable(['player','team','opp','market','side',{l:'line',g:false},{l:'price',g:false},{l:'model',t:'the model\'s chance for the side'},{l:'edge'},{l:'actual',g:false},{l:'result',g:false}],past.map(p=>[pn(p.player,p.team,true),tcell(p.team),p.opp||'',p.market,p.side,p.line,p.price!=null&&p.price!==''?mlTxt(+p.price):'—',p.model!=null&&p.model!==''?{v:+p.model,h:pkPct(+p.model,0)}:null,p.edge!=null&&p.edge!==''?{v:+p.edge,h:pkPct(+p.edge,1)}:null,p.actual??'',res(p)])):'';
    n.innerHTML=`<div class="panel"><h3>week ${G.week} · ${G.week<LW?'the card, graded':'no lines yet'} <span class="f">${G.week<LW?`the books' full prop sheet is kept only for the live week (wk ${LW}, below) · these are the props the card bet in week ${G.week}, graded from the box scores`:`the books post week-${G.week} props midweek · the live sheet below is week ${LW}`}</span></h3>${tbl}</div>`};
'''
ins_before("  function build(){\n    WK=ALLL.some(r=>+r.week===G.week)", mpnote)

# ---------- Depth Delta follows the week selector (J.depthHist) + tile histories ----------
a = s.index("  const el=$('#ddelta');if(!el)return;const PV=J.depthPrev;")
b = s.index("  const gone=PV.rows.filter(r=>!curByName[r[0]]")
b = s.index("\n", b) + 1
region = s[a:b]
assert region.count("UNIVERSE") == 7, region.count("UNIVERSE")
region = region.replace("UNIVERSE", "CUR").replace("const wk=G.week,D=J.dvp.combined||{};", "const D=J.dvp.combined||{};")
old_head = "  const el=$('#ddelta');if(!el)return;const PV=J.depthPrev;\n  if(!PV){el.innerHTML='<p class=\"note\">only one depth-chart snapshot in the build — the diff appears once a second week is pulled</p>';return}"
assert old_head in region, 'ddelta head'
region = region.replace(old_head,
    "  const el=$('#ddelta');if(!el)return;\n  if(!J.depthPrev){el.innerHTML='<p class=\"note\">only one depth-chart snapshot in the build — the diff appears once a second week is pulled</p>';return}\n"
    "  /* v32: the diff for any week — today's chart vs the previous snapshot for the live week; snapshot vs snapshot (J.depthHist, the chart as it stood before each week's first kickoff) for earlier weeks */\n"
    "  function ddBuild(wk){const H=J.depthHist||[];const hs=w=>{let h=H.find(x=>x.week===w);let g=0;while(h&&h.same!=null&&g++<9){const o=H.find(x=>x.week===h.same);h=o?Object.assign({},o,{week:h.week}):null}return h&&h.rows?h:null};\n"
    "    const now=wk>=J.week||!hs(wk)||!hs(wk-1);const PV=now?J.depthPrev:hs(wk-1);const curDate=now?J.depthDate:hs(wk).date;\n"
    "    const CUR=now?UNIVERSE:hs(wk).rows.map(([pl,tm,sl,inj,dep])=>{const o=(J.sched26[tm]||[])[wk-1]||'';return {player:pl,team:tm,slot:sl,dslot:sl,grp:SLOTG(sl),inj:String(inj),depth:+dep||0,pos:String(sl).replace(/[0-9+]/g,''),opp:o&&o!=='BYE'?o.replace('@',''):'',oppRaw:o}});")
assert "function ddBuild(wk)" in region
region += "    return {wk,rowsAll,gone,PV,curDate,now}}\n  let DD=ddBuild(G.week);\n"
s = s[:a] + region + s[b:]
a2 = s.index("  let DD=ddBuild(G.week);\n") + len("  let DD=ddBuild(G.week);\n")
b2 = s.index("  render();RR.push(render);\n}", a2)
tail = s[a2:b2]
for old, new, n in [("rowsAll.concat(gone)", "DD.rowsAll.concat(DD.gone)", 3), ("rowsAll.filter", "DD.rowsAll.filter", 2),
                    ("${PV.date}", "${DD.PV.date}", 2), ("${J.depthDate}", "${DD.curDate}", 1),
                    ("different from the <b>${DD.PV.date}</b> chart", "different from the <b id=\"ddPrev\">${DD.PV.date}</b> chart", 1)]:
    c = tail.count(old); assert c == n, (old, c, n); tail = tail.replace(old, new)
old_r = "  function render(){\n    const kind=$('#ddKinds button.on').dataset.k,tm=$('#ddTeam').value,q=$('#ddQ').value.toLowerCase();"
assert tail.count(old_r) == 1
tail = tail.replace(old_r,
    "  function render(){\n    if(DD.wk!==G.week){DD=ddBuild(G.week);const sel=$('#ddTeam'),v=sel.value;sel.innerHTML='<option value=\"\">all teams</option>'+[...new Set(DD.rowsAll.concat(DD.gone).map(r=>r.u.team))].sort().map(t=>`<option>${t}</option>`).join('');sel.value=v;const pv=$('#ddPrev');if(pv)pv.textContent=DD.PV.date}\n"
    "    const kind=$('#ddKinds button.on').dataset.k,tm=$('#ddTeam').value,q=$('#ddQ').value.toLowerCase();")
ddh = r'''    {const ddH=k=>()=>{const H=J.depthHist||[],wks=H.map(h=>h.week).filter(w=>w>=2&&w<=J.week);
        const rows=wks.map(w=>{const d=ddBuild(w),A=d.rowsAll.concat(d.gone),nn=x=>A.filter(r=>r.kinds.includes(x)&&r.u.depth<=2).length;
          return Object.assign([w,d.PV.date,d.curDate,A.length,d.rowsAll.filter(r=>r.kinds.includes('hurt')&&r.inj==='-1'&&r.u.depth<=2).length,nn('up'),nn('down'),nn('back'),d.rowsAll.filter(r=>(r.kinds.includes('new')||r.kinds.includes('team'))&&r.u.depth===1).length,nn('off')],{hi:w===G.week})});
        const L=DD.rowsAll.concat(DD.gone).filter(r=>k==='all'||(k==='out'?(r.kinds.includes('hurt')&&r.inj==='-1'&&r.u.depth<=2):k==='new'?((r.kinds.includes('new')||r.kinds.includes('team'))&&r.u.depth===1):(r.kinds.includes(k)&&r.u.depth<=2)));
        return {title:'depth-chart changes · week by week',sub:'each week\'s chart against the one before it · the week on screen is tinted',sections:[{cols:[{l:'week',g:false},{l:'from',g:false},{l:'to',g:false},'changes','ruled out','promoted','demoted','cleared','new starters','off the chart'],rows},
          {h:`behind the number · week ${G.week}`,cols:['player','team','slot',{l:'change',g:false},{l:'was',g:false},{l:'flag',g:false},{l:'steps in',g:false},{l:'opp',g:false}],rows:L.map(r=>[pn(r.u.player,r.u.team,true),tcell(r.u.team),slotchip(r.u.dslot||r.u.slot),r.kinds.map(x=>(KINDS.find(y=>y[0]===x)||[x,x])[1]).join(' · '),r.was||'',r.inj==='-1'?'OUT':r.inj==='0'?'Q':'active',r.next||'',r.u.oppRaw||''])}]}};
      thDom($('#ddKpi'),[ddH('all'),ddH('out'),ddH('up'),ddH('back'),ddH('new')])}
'''
k = tail.index("    $('#ddKpi').innerHTML=kpi('changes'"); k = tail.index("\n", k) + 1
tail = tail[:k] + ddh + tail[k:]
s = s[:a2] + tail + s[b2:]

# ---------- Backtest: in-sample vs out-of-sample, following the week selector ----------
rep('proof</span></h3><div class="btsc" id="btSt"></div></div></div>', 'proof</span></h3><div class="btsc" id="btSt"></div><div class="btio" id="btIO"></div></div></div>')
btio = r'''    /* v32: in-sample (the weeks the card's rules were picked on) vs out-of-sample (every week after), through the week picked up top */
    {const IS=new Set((B.card||{}).insample||[4,5,6]),W=G.week,io=$('#btIO'),mx=Math.max(...IS),mn=Math.min(...IS);
      const sum=(wk,f)=>{let w=0,l=0,u=0,n=0;Object.keys(wk||{}).map(Number).filter(f).forEach(k=>{const x=wk[k];w+=x[0];l+=x[1];u+=x[2];n+=x[3]});return {w,l,u,n}};
      const hist=r=>()=>({title:esc(r.lbl)+' · week by week',sub:'frozen before kickoff, graded from the box scores · in-sample weeks are the ones the card\'s rules were picked on',cols:[{l:'week',g:false},{l:'sample',g:false},{l:'frozen',g:false},{l:'record',g:false},'units',{l:'hit'}],rows:Object.keys(r.wk).map(Number).sort((a,b)=>a-b).map(k=>{const x=r.wk[k];return Object.assign([k,IS.has(k)?'in-sample':k>mx?'out-of-sample':'before the rules',x[3],x[0]+x[1]?`${x[0]}-${x[1]}`:'—',x[0]+x[1]?{v:x[2],h:(x[2]>=0?'+':'')+x[2].toFixed(1)+'u'}:null,x[0]+x[1]?{v:x[0]/(x[0]+x[1]),h:pc(x[0]/(x[0]+x[1]))}:null],{hi:k===W})})});
      const cell=(lbl,r,tone,h)=>`<div class="c ${tone}"${h?` data-th="${thReg(h)}"`:''}><div class="k">${lbl}</div><div class="h">${r.w+r.l?`${r.w}-${r.l}`:'—'} <span class="bd ${tone}">${r.w+r.l?(r.u>=0?'+':'')+r.u.toFixed(1)+'u':'no bets graded'}</span></div><div class="s">${r.n} frozen · ${r.w+r.l?`hit ${pc(r.w/(r.w+r.l))}`:'nothing graded yet'}</div></div>`;
      const strat=st.filter(r=>r.wk);
      if(io)io.innerHTML=strat.length?strat.map(r=>{const a=sum(r.wk,k=>IS.has(k)&&k<=W),b=sum(r.wk,k=>k>mx&&k<=W);
        return cell(`${esc(r.lbl)} · in-sample wks ${mn}–${mx}`,a,a.w+a.l<30?'a':a.u>0?'g':'r',hist(r))+cell(`${esc(r.lbl)} · out-of-sample wk ${mx+1}+${W>mx?' through wk '+W:''}`,b,b.w+b.l<30?'a':b.u>0?'g':'r',hist(r))}).join('')
        +`<p class="note mini" style="grid-column:1/-1">${esc((B.card||{}).note||'')} · the out-of-sample column is the one that counts · both follow the week picked up top (through week ${W})</p>`:'';}
'''
k = s.index("      +(T.top10?`<div class=\"c g\" data-btp=\"1\"><div class=\"k\">TD Picks — each week's top 10</div>"); k = s.index("\n", k) + 1
assert s[k:k+4] == "  }\n", repr(s[k:k+12])
s = s[:k] + btio + s[k:]
rep("  wire('btSe','s',v=>S=v);wire('btPos','p',v=>pos=v);wire('btTab','t',v=>tab=v);\n  render();\n}",
    "  wire('btSe','s',v=>S=v);wire('btPos','p',v=>pos=v);wire('btTab','t',v=>tab=v);\n  render();RR.push(render);\n}")

# ---------- notes ----------
rep("Object.assign(NOTES,{backtest:['v30',", "Object.assign(NOTES,{tiles32:['v32','every summary tile on META, METAPROP, Weeklies, Category Grid, TD Picks, Depth Delta, Card v2, API and Injuries now opens the history behind it (week by week, or the rows that make the number) · METAPROP and Depth Delta follow the week selector (the card\\'s graded props / snapshot-vs-snapshot for earlier weeks) · Backtest shows in-sample weeks 4–6 against out-of-sample week 7 on, through the week picked up top']});\nObject.assign(NOTES,{backtest:['v30',")

io.open(T, 'w', encoding='utf-8').write(s)
print('v32 applied', len(s))
