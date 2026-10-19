"""v28 — Backtest rebuilt to read in ten seconds: the verdict first, then three ranked bar lists in plain words.

  1. four verdict cards: which tables to trust, the best touchdown picker, the best matchup number, what to ignore;
  2. 'who picks touchdowns best' — every signal as one bar: how often it picked the right player (a scorer over a
     non-scorer in the same slot that week; coin flip = 50%), with soft-vs-tough points beside it;
  3. 'which tables to trust' — every data set as one bar: how often it called the softer defense right next week;
  4. 'are the strategies making money' — one card each: hit rate vs what it needs to profit, WINNING / LOSING.
The statistics tables are gone; the method sits in one folded line. Replaces backtestView() and its CSS from v27.

Usage: python scripts/patch_v28_backtest_plain.py [path/to/dashboard_template.html]"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n: raise SystemExit(f'patch_v28: expected {n} match(es), found {c}: {old[:90]!r}')
    s = s.replace(old, new)

# ---------------- the view: replace v27's function whole
i0 = s.index('function backtestView(){')
i1 = s.index('/* ---------------- Weeklies (F6 TEST) — the touchdown lookback ----------------', i0)
s = s[:i0] + r'''function backtestView(){
  const el=$('#backtest');if(!el)return;const B=J.backtest;
  if(!B){el.innerHTML='<p class="note">no backtest in this build yet — scripts/build_backtest.py writes it</p>';return}
  const SES=Object.keys(B.sigs).sort().reverse();let S=SES[0],pos='ALL',tab='comb';
  const pc=v=>v==null?'—':(100*v).toFixed(1)+'%',pts=v=>v==null?'—':(v>=0?'+':'−')+Math.abs(v).toFixed(1)+' pts';
  const NAME={tdA:'TD allowed to his slot',ydA:'Yards allowed to his slot',psi:'Ψ matchup score',meta:'META',h2h:'H2H',sch:'SCH (scheme)',atd:'Anytime-TD model',imp:'Vegas team total',form:'His recent points',tdr:'His TD rate'};
  const WHAT={tdA:'touchdowns his opponent gives up to his slot',ydA:'yards his opponent gives up to his slot',psi:'his opponent\'s rank across every stat of his slot',meta:'the META tab\'s blended score',h2h:'how he did against this team before',sch:'how this defense\'s scheme treats his slot',atd:'the TD Picks model\'s chance he scores',imp:'the points Vegas expects his team to score',form:'his own average over his last 8 games',tdr:'how often he has scored lately'};
  const DEP=new Set(['tdA','ydA','psi','meta']),MATCH=['tdA','ydA','psi','meta','sch','h2h','imp'];
  const col=v=>v==null?'var(--dim)':v>=.58?'var(--green)':v>=.54?'#8bc34a':v>=.51?'#e8b100':'var(--red)';
  const cap=t=>String(t).charAt(0).toUpperCase()+String(t).slice(1);
  const bar=(v,g)=>{const lo=.40,hi=.65,w=v==null?0:Math.max(1,Math.min(100,(v-lo)/(hi-lo)*100));return `<span class="btb"><i style="width:${w}%;background:${g?'var(--green)':col(v)}"></i><u style="left:${(.5-lo)/(hi-lo)*100}%" title="coin flip = 50%"></u></span>`};
  el.innerHTML=`<div class="controls">
    <span class="chips" id="btSe">${SES.map(s=>`<button data-s="${s}" class="${s===S?'on':''}">${s} season</button>`).join('')}</span>
    <span class="chips" id="btPos">${['ALL','QB','RB','WR','TE'].map(p=>`<button data-p="${p}" class="${p===pos?'on':''}">${p==='ALL'?'all positions':p}</button>`).join('')}</span>
    <span class="chips" id="btTab" title="which defense tables the matchup numbers read">${[['comb','tables: Combined (site default)'],['adj','tables: Adjusted']].map(([k,l])=>`<button data-t="${k}" class="${k===tab?'on':''}">${l}</button>`).join('')}</span>
  </div>
  <div class="btv" id="btV" data-mg="1"></div>
  <div class="panel"><h3 id="btSh"></h3><div class="btl" id="btSg"></div></div>
  <div class="wk2b"><div class="panel"><h3 id="btDh"></h3><div class="btl" id="btDs"></div></div>
    <div class="panel"><h3>are the strategies making money? <span class="f">every pick frozen before kickoff, graded from the box scores</span></h3><div class="btsc" id="btSt"></div></div></div>
  <details class="panel wkdet"><summary>how this was tested</summary><p class="mini" style="line-height:1.6;margin:8px 0 2px">Every week is replayed using only the games played before it — nothing from the future leaks in. <b>Picks the right player</b>: take two players in the same slot the same week, one who scored a touchdown and one who didn't — how often did the number rate the scorer higher? A coin flip gets 50%. <b>Soft vs tough</b>: players facing the softest third of matchups (by that number) against the toughest third — how many more fantasy points they scored than their own average. <b>Calls the softer defense</b>: take two defenses — how often did the table correctly say which one would give up more the next week, stat by stat. Built ${esc(B.built)} by scripts/build_backtest.py from the game logs.</p></details>`;
  const sv=(k,src)=>{const x=B.sigs[S].sig[k];if(!x)return {};const o=DEP.has(k)?(x.src[src||tab]||{}):x.all;return pos==='ALL'?o:(o[pos]||{})};
  function render(){
    const SG=B.sigs[S],DS=(B.dsets[S]||{rows:[]}).rows,L=B.lbl[S]||{},wk=SG.weeks;
    const R=Object.keys(SG.sig).map(k=>({k,v:sv(k)})).filter(x=>x.v.auc!=null).sort((a,b)=>b.v.auc-a.v.auc);
    const best=R[0],bm=R.filter(x=>MATCH.includes(x.k))[0],junk=R.filter(x=>x.v.auc<.51),bd=DS[0],cd=DS.find(r=>r.k==='comb');
    const tb=v=>(v-.5)*100;
    /* ---- the verdict ---- */
    $('#btV').innerHTML=[
      bd?`<div class="c"><div class="k">trust these tables</div><div class="h">${esc(cap(bd.lbl))}</div><div class="s">Called the softer defense right <b>${pc(bd.pr)}</b> of the time — best of the ${DS.length}.${cd&&cd!==bd?` The site's default, Combined, was ${pc(cd.pr)}.`:''} Every table is only a little better than a coin flip, so use matchups as a tiebreaker.</div></div>`:'',
      best?`<div class="c"><div class="k">best touchdown picker</div><div class="h">${esc(NAME[best.k])}</div><div class="s">Picked the right player <b>${pc(best.v.auc)}</b> of the time — ${tb(best.v.auc).toFixed(0)} points better than a coin flip.</div></div>`:'',
      bm?`<div class="c"><div class="k">best matchup number</div><div class="h">${esc(NAME[bm.k])}</div><div class="s">Picked the right player <b>${pc(bm.v.auc)}</b> of the time; players in its softest third scored <b>${pts(bm.v.edge)}</b> more (vs their own average) than its toughest third.</div></div>`:'',
      `<div class="c r"><div class="k">ignore</div><div class="h">${junk.length?junk.map(x=>esc(NAME[x.k])).join(' · '):'nothing'}</div><div class="s">${junk.length?`No better than a coin flip (${junk.map(x=>pc(x.v.auc)).join(', ')}). Don't lean on ${junk.length>1?'them':'it'}.`:'Every number beat a coin flip.'}</div></div>`].join('');
    /* ---- who picks touchdowns ---- */
    $('#btSh').innerHTML=`who picks touchdowns best — ${S}, weeks ${wk[0]}–${wk[wk.length-1]}${pos!=='ALL'?' · '+pos:''} <span class="f">how often it picked the right player (coin flip = 50%) · soft vs tough = extra fantasy points in its softest third of matchups vs its toughest</span>`;
    $('#btSg').innerHTML=R.map((x,i)=>`<div class="btr${x.v.auc<.51?' bad':''}"><span class="rk">${i+1}</span><span><span class="n">${esc(NAME[x.k])}</span>${i===0?' <em class="tg g">best</em>':''}${x.v.auc<.51?' <em class="tg r">ignore</em>':''}<span class="w">${esc(WHAT[x.k])}${DEP.has(x.k)?` · ${tab==='adj'?'Adjusted':'Combined'} tables`:''}</span></span>
      ${bar(x.v.auc)}<b class="v" style="color:${col(x.v.auc)}">${pc(x.v.auc)}</b><span class="x">soft vs tough <b style="color:${(x.v.edge||0)>=.5?'var(--green)':(x.v.edge||0)<0?'var(--red)':'var(--txt)'}">${pts(x.v.edge)}</b></span></div>`).join('');
    /* ---- which tables ---- */
    $('#btDh').innerHTML=`which defense tables to trust — ${S} <span class="f">how often it called the softer defense right the next week (coin flip = 50%)</span>`;
    $('#btDs').innerHTML=DS.map((r,i)=>`<div class="btr d"><span class="rk">${i+1}</span><span><span class="n">${esc(cap(r.lbl))}</span>${i===0?' <em class="tg g">best</em>':''}${r.k==='comb'?' <em class="tg">site default</em>':''}<span class="w">${esc(r.role)}</span></span>${bar(r.pr,i===0)}<b class="v" style="color:${i===0?'var(--green)':col(r.pr)}">${pc(r.pr)}</b></div>`).join('');
    /* ---- strategies ---- */
    const st=(B.strat||[]).slice().sort((a,b)=>(b.w+b.l)-(a.w+a.l)),T=B.tdp||{};
    const card=(name,rec,hit,need,note,n)=>{const few=n<30,win=hit!=null&&need!=null&&hit>need;
      return `<div class="c ${few?'a':win?'g':'r'}"><div class="k">${esc(name)}</div><div class="h">${pc(hit)} <span class="bd ${few?'a':win?'g':'r'}">${few?'too few to tell':win?'winning':'losing'}</span></div><div class="s">${rec} · needs ${pc(need)} to profit${note?'<br>'+note:''}</div></div>`};
    $('#btSt').innerHTML=st.map(r=>{const e6=(r.buckets||[]).find(b=>/6\+/.test(b.lbl));
      return card(r.lbl,`${r.w}-${r.l}${r.p?'-'+r.p:''}`,r.hit,r.be,r.k==='PROP'&&e6?`only the biggest-edge props win: <b style="color:${e6.hit>.524?'var(--green)':'var(--red)'}">${pc(e6.hit)}</b> on ${e6.n} bets with an edge of 6+`:'',r.w+r.l)}).join('')
      +(T.top10?`<div class="c g"><div class="k">TD Picks — each week's top 10</div><div class="h">${pc(T.top10[0]/T.top10[1])} <span class="bd g">scored</span></div><div class="s">${T.top10[0]} of ${T.top10[1]} over ${T.weeks} weeks — about 3 in 10 players score in a given week</div></div>`:'');
  }
  const wire=(id,a,f)=>$('#'+id).querySelectorAll('button').forEach(b=>b.onclick=()=>{f(b.dataset[a]);$('#'+id).querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render()});
  wire('btSe','s',v=>S=v);wire('btPos','p',v=>pos=v);wire('btTab','t',v=>tab=v);
  render();
}

''' + s[i1:]

# ---------------- CSS: swap v27's table styles for the bar lists
i0 = s.index('.btins{margin:0;'); i1 = s.index('.wksig{cursor:pointer;', i0)
s = s[:i0] + r'''.btv{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:0 0 12px}
.btv .c,.btsc .c{background:var(--panel);border:1px solid var(--edge);border-top:3px solid var(--green);border-radius:8px;padding:11px 14px;min-width:0}
.btv .c.r,.btsc .c.r{border-top-color:var(--red)}.btsc .c.a{border-top-color:#e8b100}
.btv .k,.btsc .k{font:600 10px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--dim)}
.btv .h{font:700 19px var(--ui);margin:5px 0 6px;color:var(--txt)}.btsc .h{font:700 22px var(--mono);margin:4px 0 4px;color:var(--txt);display:flex;align-items:center;gap:8px}
.btv .s,.btsc .s{font-size:12.5px;line-height:1.45;color:var(--txt)}.btv .s b{color:var(--green)}.btsc .s{color:var(--dim)}
.btsc{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.btsc .bd{font:700 9.5px var(--mono);letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border-radius:3px}.bd.g{background:#00c85322;color:var(--green)}.bd.r{background:#ff525222;color:var(--red)}.bd.a{background:#e8b10022;color:#e8b100}
.btl{display:grid}.btr{display:grid;grid-template-columns:22px minmax(180px,1.3fr) minmax(140px,2fr) 70px minmax(120px,.8fr);gap:14px;align-items:center;padding:8px 2px;border-bottom:1px solid var(--edge)}
.btr.d{grid-template-columns:22px minmax(150px,1.3fr) minmax(120px,2fr) 70px}.btr.bad .n{color:var(--dim)}
.btr .rk{font:700 12px var(--mono);color:var(--dim2)}.btr .n{font:700 13.5px var(--ui);color:var(--txt)}.btr .w{display:block;font-size:11px;color:var(--dim);margin-top:2px}
.btr .v{font:700 17px var(--mono);text-align:right}.btr .x{font-size:11.5px;color:var(--dim)}.btr .tg{font:700 9px var(--mono);letter-spacing:.06em;text-transform:uppercase;font-style:normal;padding:1px 5px;border-radius:3px;border:1px solid var(--edge2);color:var(--dim);margin-left:6px;vertical-align:2px}
.btr .tg.g{color:var(--green);border-color:#00c85366}.btr .tg.r{color:var(--red);border-color:#ff525266}
.btb{position:relative;display:block;height:12px;background:#161b22;border-radius:6px}.btb i{position:absolute;left:0;top:0;bottom:0;border-radius:6px}.btb u{position:absolute;top:-4px;bottom:-4px;width:2px;background:#ffffffaa}
@media(max-width:840px){.btv{grid-template-columns:1fr}.btr,.btr.d{grid-template-columns:20px 1fr 64px;gap:6px 10px}.btr .v{grid-row:1;grid-column:3}.btr .btb{grid-row:2;grid-column:2/4}.btr .x{grid-row:3;grid-column:2/4}}
''' + s[i1:]

# ---------------- words
rep(r''' backtest:{what:'Which data set and which signal have actually been right.',how:['data sets: for every stat and week, how well each version of a defense\'s numbers ordered what the defenses allowed NEXT week — rank correlation, 0 = a coin flip, 1 = perfect','signals: among players in the same slot the same week, did the softer matchup (or the higher model %) score more? AUC = how often a scorer was ranked above a non-scorer (.500 = coin flip); vs-norm = did he beat his own average','everything is point in time: a week is predicted only from games before it']},''',
    r''' backtest:{what:'What has actually been right — and what to ignore.',how:['the four cards up top are the answer','bars: how often each number picked the right player or the right defense — 50% is a coin flip','every week is replayed using only the games before it']},''')
rep(r'''Object.assign(NOTES,{backtest:['v27','new tab:''', r'''Object.assign(NOTES,{backtest:['v28','rebuilt to read at a glance — the verdict in four cards, then ranked bars: who picks touchdowns best, which tables to trust, which strategies make money (all as "right X% of the time", coin flip = 50%) · was: new tab:''')
open(P, 'w', encoding='utf-8').write(s)
print('patch_v28: Backtest in plain words')
