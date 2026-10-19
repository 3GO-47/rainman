"""v25 — Weeklies works on the week being played until its box scores are all in.

The forward list and every signal pane target the first week that is not fully logged (week 6 while its games are still
being imported), built only from games before it, and grade each player ✓ / ✗ as his box score lands. Once the week is
complete it becomes the lookback week and the forward week moves on (to the TD Picks week). The pane keeps a 'next up' tab
for the TD Picks week while the two differ.

Usage: python scripts/patch_v25_pending.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v25: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

rep(r'''    const TPk=J.tdpicks,AH=wkAhead(u=>slotOK(wkLive,u.dslot||u.slot)&&inP(u.pos),TR,TPk?TPk.week:null),W0=TPk?TPk.week:J.week,dn=AH.filter(x=>x.done).length;''',
    r'''    /* the week being played until every box score is in: its players are picked from earlier games and graded as they log */
    const FLs=wkFeat(LAST_SE),Wn=FLs.pending.length?Math.min(...FLs.pending):FLs.weeks.length?Math.max(...FLs.weeks)+1:null;
    const TPk=J.tdpicks,W0=Wn||(TPk?TPk.week:J.week),keepU=u=>slotOK(wkLive,u.dslot||u.slot)&&inP(u.pos),AH=wkAhead(keepU,TR,W0),dn=AH.filter(x=>x.done).length,dK=AH.filter(x=>x.done&&x.done.td>0).length;''')
rep(r'''    if(TPk){const AM={};''', r'''    if(TPk&&TPk.week===W0){const AM={};''')
rep(r'''    $('#wkAh').innerHTML=`week ${W0} — who carries what works <span class="f">top five per position, ranked by the core signals each player carries, weighted by how well each held up · model = anytime-TD chance · ✓ / ✗ once his game is logged${dn?` (${dn} so far)`:''}</span>`;''',
    r'''    $('#wkAh').innerHTML=`week ${W0} — who carries what works <span class="f">built from games before week ${W0} · top five per position, ranked by the core signals each player carries, weighted by how well each held up · model = anytime-TD chance · ✓ / ✗ as week ${W0}'s box scores import</span>${dn?` <span class="note kept">week ${W0} so far: ${dK} of ${dn} graded scored</span>`:''}${TPk&&TPk.week>W0?`<button class="lk" data-go="tdpicks" title="the model's picks for the week after">week ${TPk.week} picks →</button>`:''}`;
    {const g=$('#wkAh [data-go]');if(g)g.onclick=()=>go('tdpicks')}''')
rep(r'''    CUR={S,W,st,TR,AH,W0,SG};''', r'''    CUR={S,W,st,TR,AH,W0,SG,keepU};''')
rep(r'''const {S:S0,W:W1,st,TR,AH,W0,SG}=CUR;''', r'''const {S:S0,W:W1,st,TR,AH,W0,SG,keepU}=CUR;''')
rep(r'''    const B=st.P.filter(qual).sort((a,b)=>b.td-a.td||b.cs-a.cs),bk=B.filter(x=>x.td>0).length;''',
    r'''    const B=st.P.filter(qual).sort((a,b)=>b.td-a.td||b.cs-a.cs),bk=B.filter(x=>x.td>0).length;
    const TPk=J.tdpicks,W2=TPk&&TPk.week!==W0?TPk.week:null,A2=W2?wkAhead(keepU,TR,W2).filter(qual).map(x=>Object.assign(x,{tp:tpOf(x.name,x.team,W2),psR:psiRk(x.opp,x.grp)})).sort((a,b)=>((b.tp||{}).p??-1)-((a.tp||{}).p??-1)||b.cs-a.cs):null;
    const ag=A.filter(x=>x.done),ak=ag.filter(x=>x.done.td>0).length,fb=st.base||.25;''')
rep(r'''      wkTile(`week ${W0} ahead`,String(A.length),`carry it into their next game`,A.length?'g':'',true)].filter(Boolean);''',
    r'''      wkTile(`week ${W0}${ag.length?' · grading':' ahead'}`,ag.length?`${ak}<span class="dim"> / ${ag.length}</span>`:String(A.length),ag.length?`graded so far scored · ${A.length} carry it in`:`carry it in · graded as week ${W0} imports`,ag.length?(ak/ag.length>=fb*1.1?(neg?'r':'g'):ak/ag.length<=fb*.9?(neg?'g':'r'):''):(A.length?'g':''),true),
      A2?wkTile(`week ${W2} · next up`,String(A2.length),'carry it into the week after','',true):''].filter(Boolean);''')
rep(r'''    const aT=A.length?''', r'''    const aTab=(A,W0)=>A.length?''')
rep(r'''in the slots picked on Weeklies':''}</p>`;''', r'''in the slots picked on Weeklies':''}</p>`;
    const aT=aTab(A,W0),aT2=A2?aTab(A2,W2):'';''')
rep(r'''<div class="tabs"><button id="wsT1" class="on">week ${W0} — who carries it · ${A.length}</button><button id="wsT2">week ${W1} — who carried it · ${B.length} (${bk} scored)</button></div>
      <div id="wsV1">${aT}</div><div id="wsV2" hidden>${bT}</div></div>''',
    r'''<div class="tabs"><button data-t="1" class="on">week ${W0} — who carries it · ${A.length}${ag.length?` (${ak} of ${ag.length} graded scored)`:''}</button>${A2?`<button data-t="3">week ${W2} — next up · ${A2.length}</button>`:''}<button data-t="2">week ${W1} — who carried it · ${B.length} (${bk} scored)</button></div>
      <div id="wsV1">${aT}</div>${A2?`<div id="wsV3" hidden>${aT2}</div>`:''}<div id="wsV2" hidden>${bT}</div></div>''')
rep(r'''wireModal();const t1=$('#wsT1'),t2=$('#wsT2'),sw=a=>{t1.classList.toggle('on',a);t2.classList.toggle('on',!a);$('#wsV1').hidden=!a;$('#wsV2').hidden=a};t1.onclick=()=>sw(true);t2.onclick=()=>sw(false)}''',
    r'''wireModal();const bs=[...document.querySelectorAll('#ppModal .wsg .tabs button')];bs.forEach(b=>b.onclick=()=>bs.forEach(x=>{x.classList.toggle('on',x===b);const v=$('#wsV'+x.dataset.t);if(v)v.hidden=x!==b}))}''')
rep(" weeklies:['v24','", " weeklies:['v25','until a week\\'s box scores are all in, the forward list and every signal pane work on that week — built from the games before it and graded ✓ / ✗ as its box scores import — with the TD Picks week one tab over · ")
rep("home, favored, implied team total — from the closing spread and total (betting.glh)", "home, favored, implied team total — from the closing spread and total (betting.glh); a game still to play carries the books' current consensus (live_lines.py)")
rep("/* closing lines: [season, week, away, home, away pts, home pts, spread (+ = home favored), total, roof, ...] */", "/* lines: [season, week, away, home, away pts, home pts, spread (+ = home favored), total, roof, div, 'books' when it is the live consensus of a game still to play] */")
open(P, 'w', encoding='utf-8').write(s)
print('patch_v25: Weeklies targets the week being played')
