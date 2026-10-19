"""v26 — TD Picks follows the week picked up top, like every other tab.

The live board stays the week being picked (prices, locks at kickoff). Any other week reads td_picks.json 'wk'
(build_td_picks.py): a finished week = every player who played, rated by the walk-forward model and graded; a week still
importing = rated from the games before it and graded as its box scores land; a week to come = an early look. The track
record's bars for this season jump to their week. tdP() hands the same numbers to the Weeklies tab and the Category Grid.

Usage: python scripts/patch_v26_tdweek.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v26_tdweek: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# ---------------- shared: any week's board, decoded once
rep(r'''function tdPicks(){
  const el=$('#tdpicks');if(!el)return;const T=J.tdpicks;''', r'''const TD_TIER=[['lock',.5],['strong',.4],['solid',.3],['long',.2],['low',0]];
const tdFair=p=>p>=.5?Math.round(-100*p/(1-p)):Math.round(100*(1-p)/p);
/* the reasons, from the feature codes build_td_picks.py writes (same wording as its why_text / risk_of) */
function tdWhyTxt(k,x,risk){const g=(J.tdpicks.grp||{})[x.b]||x.b,f1=v=>v==null?'—':(+v).toFixed(1),f2=v=>v==null?'—':(+v).toFixed(2),gg=v=>String(+v),e=x.est?'~':'';
  if(risk)switch(k){case 'sp':return `underdog by ${e}${gg(Math.abs(x.sp))}`;case 'imp':return `team implied only ${e}${f1(x.imp)}`;case 'def':return `${x.o} allows just ${f2(x.dr)} TD/g to ${g}s`;case 'def_l3':return `${x.o} has held ${g}s to ${f1(x.dl3)} TD/g lately`;
    case 'l3':return `no TD in his last ${x.l3n}`;case 'touch':return `only ${f1(x.touch)} touches a game`;case 'snp':return `plays ${x.snp}% of snaps`;default:return null}
  switch(k){case 'ra_qb':case 'ra':return `${f1(x.ra)} carries a game`;case 'form':return x.gpS?`TD in ${x.hitS} of ${x.gpS} — below his career norm`:'scoring history';case 'l3':return x.l3n?`TD in ${x.l3k} of his last ${x.l3n}`:'no games yet this season';
    case 'crate':return `career: TD in ${x.hitC} of ${x.gC}`;case 'share':return `${x.mine} of his team's ${x.tt} TDs`;case 'touch':return `${f1(x.touch)} touches a game`;case 'tgt':return `${f1(x.tgt)} targets a game`;
    case 'snp':return x.snp!=null?`${x.snp}% of snaps`:'every-down role';case 'imp':return x.imp!=null?`team implied ${e}${f1(x.imp)}`:'team total';case 'sp':return x.sp>0?`favored by ${e}${gg(x.sp)}`:'spread';
    case 'def':return x.dr!=null?`${x.o} allows ${f2(x.dr)} TD/g to ${g}s`:'soft defense';case 'def_l3':return x.dl3!=null?`${x.o} gave ${g}s ${f1(x.dl3)} TD/g lately`:'defense trend';case 'h2h':return `scored vs ${x.o} before`;
    default:return ((J.tdpicks.model||{}).labels||{})[k]||k}}
/* any week's board: the live picks for the week being picked, otherwise td_picks.json 'wk' — final week = walk-forward (graded),
   week importing = rated from the games before it (graded as it lands), week to come = early look */
function tdBoard(w){const T=J.tdpicks;if(!T)return null;
  if(w===T.week)return {m:'live',w,P:T.picks,g:T.games,d:T.dates};
  const E=(T.wk||{})[w];if(!E)return null;
  if(!E._P){const F=T.model.feats;E._P=E.r.map(r=>{const e=typeof r[0]==='number',B=e?T.base[r[0]]:null;
    const b=e?B[3]:r[12],p=(e?r[3]:r[5])/1000,st=e?B.slice(4):r[10],os=e?r[7]:r[11],wc=e?r[4]:r[7],rc=e?r[5]:r[8];
    const x={n:e?B[0]:r[0],t:e?B[1]:r[1],o:e?r[1]:r[2],h:!!(e?r[2]:r[3]),s:e?B[2]:r[4],b,pos:b==='QB1'?'QB':b.slice(0,2),p,res:e?null:r[6],inj:String(e?r[6]:r[9]),
      hitS:st[0],gpS:st[1],l3k:st[2],l3n:st[3],hitC:st[4],gC:st[5],mine:st[6],tt:st[7],touch:st[8],tgt:st[9],ra:st[10],snp:st[11],
      imp:os[0],sp:os[1],dr:os[2],dl3:os[3],h2h:os[4],est:!!os[5],price:null,book:null,ev:null};
    x.share=x.tt?x.mine/x.tt:null;x.fair=tdFair(p);x.tier=TD_TIER.find(z=>p>=z[1])[0];
    x.why=wc.map(j=>tdWhyTxt(F[j],x));x.risk=rc>=0?tdWhyTxt(F[rc],x,true):null;return x})}
  return {m:E.m,w,P:E._P,g:E.g,d:E.d,ln:E.ln}}
/* one player's TD chance for a week (the board above, else the anytime-TD model's row) */
function tdP(n,t,w){const BD=tdBoard(w);if(BD){const p=BD.P.find(x=>x.n===n&&x.t===t)||BD.P.find(x=>x.n===n);if(p)return {p:p.p,price:p.price,book:p.book}}
  const b=((J.betting||{}).td||[]).find(r=>+r.week===w&&r.player===n);return b&&b.p_model!=null&&b.p_model!==''?{p:+b.p_model,price:b.price!=null&&b.price!==''?+b.price:null,book:b.book}:null}
function tdSetWk(w){const s=$('#gWk');if(!s)return;s.value=w;s.onchange()}
function tdPicks(){
  const el=$('#tdpicks');if(!el)return;const T=J.tdpicks;''')

# ---------------- the tab reads the selected week
rep(r'''<span class="note kept">week ${T.week} · depth chart ${T.depth} · updated ${T.now?T.now.slice(5)+' ET':T.built}</span>''', r'''<span class="mini tpnote" id="tpNote"></span>''')
rep(r'''<span class="st">${trk(x)}</span>''', r'''<span class="st">${x.res==null?trk(x):''}</span>''')
rep(r'''    const P=T.picks.filter(keep),sk=$('#tpSort').value;''',
    r'''    const BD=tdBoard(G.week)||{m:'none',w:G.week,P:[],g:0,d:null},BW=BD.w,isLive=BD.m==='live',P=BD.P.filter(keep),sk=$('#tpSort').value;
    const MN={live:`live board · depth chart ${T.depth.slice(5)} · updated ${T.now?T.now.slice(5)+' ET':T.built} · picks lock at kickoff`,
      wf:'final — every player who played, rated blind, graded',pre:'grading — rated from the games before it · ✓ / ✗ as box scores import',
      early:`early look — today's depth chart and form vs the week-${BW} opponent${BD.ln!=null&&BD.ln<BD.g?' · ~ = estimated line':''}`,none:'no board for this week'};
    $('#tpNote').innerHTML=`week ${BW} · ${MN[BD.m]}${isLive?'':` · <a href="#" class="tplive">live board: week ${T.week} →</a>`}`;
    {const a=$('#tpNote .tplive');if(a)a.onclick=e=>{e.preventDefault();tdSetWk(T.week)}}''')
rep(r'''    $('#tpTiles').innerHTML=wkTile(`week ${T.week}`,''', r'''    if(!isLive){const gr=P.filter(x=>x.res!=null),gk=gr.filter(x=>x.res>0).length,T10=gr.slice().sort((a,b)=>b.p-a.p).slice(0,10),k10=T10.filter(x=>x.res>0).length,LKa=P.filter(x=>x.tier==='lock'),LKg=LKa.filter(x=>x.res!=null),top=P.slice().sort((a,b)=>b.p-a.p)[0];
      $('#tpTiles').innerHTML=wkTile(`week ${BW}${BD.m==='early'?' · early look':BD.m==='pre'?' · grading':' · final'}`,String(BD.g||0),`games · ${BD.d?BD.d[0].slice(5)+' to '+BD.d[1].slice(5):''}`)
        +wkTile('locks',String(LKa.length),LKg.length?`${LKg.filter(x=>x.res>0).length} of ${LKg.length} graded scored`:(LKa.slice(0,2).map(x=>esc(pshort(x.n))).join(' · ')||'none above 50%'),'g')
        +(gr.length?wkTile('top 10',`${k10}<span class="dim"> / ${T10.length}</span>`,'of the ten highest rated scored',k10>=6?'g':k10<=3?'r':''):wkTile('top pick',top?esc(pshort(top.n)):'—',top?`${pct(top.p)} · ${top.h?'vs':'@'} ${top.o}`:'','g',true))
        +wkTile(gr.length?'graded':'rated 15%+',gr.length?`${gk}<span class="dim"> / ${gr.length}</span>`:String(P.length),gr.length?`listed players who scored · ${pct(gk/gr.length)}`:BD.m==='early'?'players in view':'graded as box scores import')
        +wkTile('live board',`wk ${T.week}`,'prices · locks at kickoff','',true)}
    else $('#tpTiles').innerHTML=wkTile(`week ${T.week}`,''')
rep(r'''    $('#tpBh').innerHTML=`week ${T.week} — the picks <span class="f">''', r'''    $('#tpBh').innerHTML=`week ${BW} — ${isLive?'the picks':BD.m==='early'?'early look':BD.m==='wf'?'the picks, graded':'the picks · grading'} <span class="f">''')
rep(r'''that chance is worth${T.priced?' · EV''', r'''that chance is worth${isLive&&T.priced?' · EV''')
rep(r'''${(T.nolines||[]).length?` <span class="note kept" style="color:var(--amber)">''', r'''${isLive&&(T.nolines||[]).length?` <span class="note kept" style="color:var(--amber)">''')
rep(r'''    $('#tpVal').innerHTML=!T.priced?''', r'''    $('#tpVal').innerHTML=!isLive?`<p class="mini dim">posted prices are tracked for the live week only (week ${T.week})</p>`:!T.priced?''')
rep(r'''return `<span class="b${x.lv?' lv':''}${ns?' ns':''}" title=''', r'''return `<span class="b${x.lv?' lv':''}${ns?' ns':''}${x.s===T.season&&x.w===BW?' sel':''}"${x.s===T.season?` data-w="${x.w}"`:''} title=''')
rep(r'''    /* the frozen ledger */''', r'''    $('#tpRec').querySelectorAll('[data-w]').forEach(b=>b.onclick=()=>tdSetWk(+b.dataset.w));
    /* the frozen ledger */''')
rep(r'''every player — week ${T.week} <span class="mini">''', r'''every player — week ${BW} <span class="mini">''')
rep(r'''.tpwk .b.lv i{outline:1px solid var(--txt);outline-offset:-1px}''', r'''.tpwk .b.lv i{outline:1px solid var(--txt);outline-offset:-1px}.tpwk .b[data-w]{cursor:pointer}.tpnote{color:var(--dim)}.tpnote a{color:var(--acc)}.tpwk .b.sel{background:#ffffff17;border-radius:3px}''')

# ---------------- the Weeklies tab uses the same numbers
i0 = s.index("  const tpOf=(n,t,w)=>{const T=J.tdpicks;if(T&&T.week===w){")
i1 = s.index("book:b.book}:null};", i0) + len("book:b.book}:null};")
s = s[:i0] + "  const tpOf=tdP;" + s[i1:]

# ---------------- words
rep(r'''desc:'next week\'s anytime touchdowns: every slot owner''', r'''desc:'anytime touchdowns for the week picked up top — the live board for the week being picked, graded boards for past weeks, an early look ahead: every slot owner''')
rep(r''' tdpicks:{what:'Next week\'s anytime touchdowns.',how:[''', r''' tdpicks:{what:'Anytime touchdowns for the week picked up top.',how:['the week picker up top drives it: the week being picked = the live board · a finished week = every player who played, rated blind, graded · a week importing = graded as box scores land · a week to come = an early look',''')
rep(r'''const BOOT=[''', r'''Object.assign(NOTES,{tdpicks:['v26','follows the week picked up top like every other tab — the live board for the week being picked; a finished week shows every player who played, rated by the model refit on earlier weeks only and graded; the week importing is rated from the games before it and graded as box scores land; weeks to come get an early look (today\'s depth chart and form vs that opponent, implied totals estimated until lines post) · track-record bars jump to their week']});
const BOOT=[''')
open(P, 'w', encoding='utf-8').write(s)
print('patch_v26_tdweek: TD Picks follows the selected week')
