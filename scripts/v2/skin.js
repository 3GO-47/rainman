/* RAINMAN v3 shell: broadcast header (sections + sliding indicator), live plays ticker, sub-navigation, view transitions, clamped notes, scoreboard tiles. */
(function(){
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const I={home:'<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
 board:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
 chamber:'<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M12 4v16M3 12h4M17 12h4"/><circle cx="12" cy="12" r="2.5"/>',
 players:'<circle cx="9" cy="8" r="3.2"/><path d="M3 20c.6-3.4 3-5.4 6-5.4s5.4 2 6 5.4"/><circle cx="17.5" cy="9" r="2.4"/><path d="M16 14.6c2.6.1 4.4 1.9 5 4.9"/>',
 defenses:'<path d="M12 3 4.5 6v5.5c0 4.6 3.1 8 7.5 9.5 4.4-1.5 7.5-4.9 7.5-9.5V6z"/>',
 tdb:'<path d="M5 21V4M5 4h11l-2.5 4L16 12H5"/>',
 sked:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/>',
 intel:'<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
 games:'<path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="8.5"/>',
 bets:'<path d="M4 7h16v10H4z"/><path d="M8 7v10M16 7v10"/><circle cx="12" cy="12" r="1.8"/>',
 locker:'<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z"/>',
 help:'<circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1.1.9-1.1 1.6v.6M12 17h.01"/>'};
const ico=k=>`<svg class="ico" viewBox="0 0 24 24">${I[k]||I.home}</svg>`;
function shell(){
  const nav=$('#top nav');if(!nav)return;
  const hdr=document.createElement('header');hdr.id='hdr';
  hdr.innerHTML=`<a class="brand" href="#" title="RAINMAN"><svg viewBox="0 0 32 32"><defs><linearGradient id="rmg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5cc8ff"/><stop offset="1" stop-color="#19e68c"/></linearGradient></defs>
    <path d="M16 2c5 6.6 9 11.4 9 16.4A9 9 0 0 1 7 18.4C7 13.4 11 8.6 16 2z" fill="url(#rmg)"/><path d="M17.6 11 12.8 19h3.6l-1.8 6.4 5.6-8.6h-3.8z" fill="#06080b"/></svg>
    <div><b>RAINMAN</b><small>NFL betting terminal</small></div></a><div class="hdr-r"><button id="hSearch" title="find any player or team">${ico('intel')}<span class="lbl">Search</span><kbd>Ctrl K</kbd></button></div>`;
  hdr.insertBefore(nav,hdr.querySelector('.hdr-r'));
  document.body.prepend(hdr);
  hdr.querySelector('.brand').onclick=e=>{e.preventDefault();if(window.go)go('bets')};
  $('#hSearch').onclick=()=>{const f=$('#gFind');if(f)f.click()};
  const h=$('#gHelp');if(h){h.innerHTML=ico('help');h.title='glossary (?)';h.style.marginLeft='0';hdr.querySelector('.hdr-r').appendChild(h);h.className='hbtn'}
  nav.querySelectorAll('button[data-sec]').forEach(b=>{const fk=b.querySelector('.fk');const label=[...b.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim();
    b.innerHTML=ico(b.dataset.v)+`<span class="lbl">${label}</span>`+(fk?fk.outerHTML:'');b.title=label});
  const ind=document.createElement('div');ind.className='ind';nav.appendChild(ind);
  const place=()=>{const on=nav.querySelector('button.on');if(!on)return;const lb=on.querySelector('.lbl')||on;ind.style.width=lb.offsetWidth+'px';ind.style.transform=`translateX(${on.offsetLeft+lb.offsetLeft}px)`};
  document.addEventListener('rm:view',()=>requestAnimationFrame(()=>{place();enter()}));
  addEventListener('resize',place);setTimeout(place,60);if(document.fonts)document.fonts.ready.then(place);
  ticker(hdr);footer();
  const sticky=()=>document.documentElement.style.setProperty('--sticky',$('#top').offsetHeight+'px');sticky();addEventListener('resize',sticky);
}
function ticker(hdr){const B=J.betting;if(!B||!B.lines)return;
  const P=B.lines.filter(l=>l.ev>=3).sort((a,b)=>b.ev-a.ev).slice(0,24);if(!P.length)return;
  const MK={pass_yds:'pass yds',pass_td:'pass TD',pass_att:'attempts',completions:'completions',interceptions:'INT',rush_yds:'rush yds',rush_att:'carries',receptions:'rec',rec_yds:'rec yds',rush_rec_yds:'rush+rec',pass_rush_yds:'pass+rush'};
  const item=l=>`<span class="tk" data-p="${esc(l.player)}">${typeof hs==='function'?hs(l.player):''}<b>${esc(l.player)}</b><span class="tk-s ${l.side==='Over'?'o':'u'}">${l.side==='Over'?'O':'U'} ${l.line}</span>${MK[l.market]||l.market}<em>+${l.ev}%</em></span>`;
  const t=document.createElement('div');t.id='ticker';
  t.innerHTML=`<span class="tk-l">wk ${B.week} plays</span><div class="tk-run" style="--tkd:${Math.max(30,P.length*5)}s">${P.map(item).join('')}${P.map(item).join('')}</div>`;
  hdr.after(t);t.addEventListener('click',e=>{const k=e.target.closest('.tk');if(k&&window.playerPop)playerPop(k.dataset.p)})}
function footer(){const m=$('main');if(!m)return;const f=document.createElement('footer');f.id='ftr';
  const seasons=[...new Set(J.logs.map(l=>l[2]))].sort().map(x=>`'${String(x).slice(2)}`).join(' ');
  f.innerHTML=`<span>data <b>${seasons}</b></span><span><b>${Math.round(J.weekly.length/2)}</b> games</span><span><b>${J.logs.length.toLocaleString()}</b> player-game rows</span>
   <span>depth charts <b>${J.depthDate}</b></span><span>DvP <b>${J.blend}</b></span><span>built <b>${J.built}</b></span><a href="https://3go-47.github.io/rainman/v1/">classic terminal (v1)</a><a href="https://3go-47.github.io/rainman/archive/">archived builds</a>`;
  m.after(f)}
function visible(){return $$('main>div').find(d=>!d.hidden)}
let enter=function(){const v=visible();if(!v||RM)return;v.classList.remove('v2enter');void v.offsetWidth;v.classList.add('v2enter');stagger(v);countUp(v)};
function stagger(root){const ps=[...root.querySelectorAll('.panel')].filter(p=>p.offsetParent).slice(0,14);
  ps.forEach((p,i)=>{p.classList.remove('v2stagger');void p.offsetWidth;p.style.setProperty('--i',i);p.classList.add('v2stagger')})}
const NUM=/^[+-]?\d{1,4}(\.\d{1,2})?$/;
function countUp(root){if(RM)return;const els=[...root.querySelectorAll('.kpi .v')].filter(e=>e.offsetParent&&NUM.test(e.textContent.trim())).slice(0,160);
  const t0=performance.now(),D=650;const data=els.map(e=>{const s=e.textContent.trim();return {e,v:+s,dp:(s.split('.')[1]||'').length,s,pre:s[0]==='+'?'+':''}});
  const tick=t=>{const k=Math.min(1,(t-t0)/D),q=1-Math.pow(1-k,4);data.forEach(d=>{d.e.textContent=k<1?d.pre+(d.v*q).toFixed(d.dp):d.s});if(k<1)requestAnimationFrame(tick)};requestAnimationFrame(tick)}

/* ---------- polish pass: runs after every render of the visible view (MutationObserver, debounced) ----------
   · header cells take the alignment of their column's data · tables that overflow get their own scroller
   · long explanatory paragraphs collapse behind an "how to read" chip · panel titles toggle collapse (remembered)
   · Home gets its section order + deep analytics collapsed by default */
const INFO='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>';
let COL={};try{COL=JSON.parse(localStorage.getItem('rm.v2.col')||'{}')}catch(e){}
const saveCol=()=>{try{localStorage.setItem('rm.v2.col',JSON.stringify(COL))}catch(e){}};
const hkey=h=>(h.firstChild&&h.firstChild.nodeType===3?h.firstChild.textContent:h.textContent).toLowerCase().replace(/\d+/g,'#').replace(/\s+/g,' ').trim().slice(0,48);
function alignHeads(root){root.querySelectorAll('table').forEach(t=>{if(t.dataset.v2a)return;const r=t.tBodies[0]&&[...t.tBodies[0].rows].find(r=>r.cells.length>2);const hr=t.tHead&&t.tHead.rows[t.tHead.rows.length-1];
  if(!r||!hr||hr.cells.length!==r.cells.length)return;t.dataset.v2a=1;[...hr.cells].forEach((th,i)=>{const td=r.cells[i];if(!td||th.colSpan>1)return;const a=getComputedStyle(td).textAlign;if(a==='left'||a==='center')th.style.textAlign=a})})}
function overflow(root){root.querySelectorAll('table').forEach(t=>{const p=t.parentElement;if(!p||p.tagName==='TD')return;const over=t.scrollWidth>p.clientWidth+2;p.classList.toggle('hscroll',over)})}
function notes(root){root.querySelectorAll('.note, .controls>.note').forEach(n=>{if(n.dataset.v2n)return;n.dataset.v2n=1;const txt=n.textContent.trim();
  if(txt.length<150||/^\d+ (players|defenses|games|rows)/.test(txt))return;
  n.classList.add('v2note');n.title='click to expand';n.addEventListener('click',e=>{if(e.target.closest('a,button,.plink,.pp,.tc'))return;n.classList.toggle('open')})})}
const HOMEDEEP=/best &(amp;)? worst|best & worst|field extremes|momentum|least trustworthy|season slate|uncertainty|geodesics|— wk #$|predictable|system/;
function collapsible(root){root.querySelectorAll('.panel>h3').forEach(h=>{const p=h.parentElement;const k=(root.id||'')+':'+hkey(h);
  if(!h.classList.contains('v2h')){if(h.id||h.querySelector('select,input,button'))return;h.classList.add('v2h');h.addEventListener('click',e=>{if(e.target.closest('a,button,select,input,.plink,.pp,.tc'))return;const c=p.classList.toggle('v2col');COL[k]=c?1:0;saveCol()})}
  const deep=p.classList.contains('betstatus');
  const want=k in COL?!!COL[k]:deep;p.classList.toggle('v2col',want)})}
function capH(root){root.querySelectorAll('h3').forEach(h=>{const n=h.firstChild;if(n&&n.nodeType===3&&/^\s*[a-z]/.test(n.textContent))n.textContent=n.textContent.replace(/^(\s*)([a-z])/,(m,a,b)=>a+b.toUpperCase())})}
function polish(){const v=visible();if(!v)return;capH(v);alignHeads(v);notes(v);collapsible(v);overflow(v)}
let pT=0;const mo=new MutationObserver(()=>{clearTimeout(pT);pT=setTimeout(polish,60)});
/* spring tilt on game cards: rotate toward the cursor, settle back with overshoot */
function tilt(){if(RM||matchMedia('(hover:none)').matches)return;
  document.addEventListener('mousemove',e=>{const c=e.target.closest('.gamecard,.panel.story');$$('.tilt-on').forEach(x=>{if(x!==c){x.classList.remove('tilt-on');x.style.transition='transform .7s var(--spring)';x.style.transform=''}});
    if(!c)return;const r=c.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;
    c.classList.add('tilt-on','tilt');c.style.transition='transform .12s ease-out';c.style.transform=`perspective(1400px) rotateX(${(-y*2.2).toFixed(2)}deg) rotateY(${(x*2.6).toFixed(2)}deg) translateY(-2px)`},{passive:true})}
/* re-run the entrance on filter changes for the visible view (lighter: count-up only) */
function hookRender(){const o=window.runView;if(typeof o!=='function')return;window.runView=function(v){const r=o.apply(this,arguments);requestAnimationFrame(()=>{const vis=visible();if(vis&&vis.id===v){heroFor(v);countUp(vis)}});return r}}

/* ---------- page hero per view + Home KPI tiles (all values computed from the same payload as v1) ---------- */
const VIEWS={bets:['Bet Board','Props, anytime TDs and correlated parlays priced from player form and the matchup rankings — edges anchored to the market, every pick graded.'],
 games:['Lines & model','Spreads, totals and implied team points for the week, the game model’s view, and every game card.'],
 chamber:['Slot matchups','Every game: each offense’s slot owners against the opposing defense’s allowed-stats field.'],
 locker:['Storylines','Rivalries, alumni reunions, homecomings, revenge games and birthdays.'],
 home:['This week','The core matchup read: the softest spot at every role, who to target and avoid, and the slate.'],
 mlab:['Matchup lab','Every depth-chart player with his opponent’s per-stat ranks — sort by any stat.'],
 tdb:['TD matchups','Who faces the defenses that give up touchdowns to their role.'],
 board:['Projections','Every player projected for the week with the full factor breakdown and the walk-forward Model Lab.'],
 defenses:['Defense rankings','Rankings, the 32 × slot matrix and each defense’s weekly observatory.'],
 trends:['Trends','Defenses softening or tightening right now, how predictable each one is, and full-season schedule strength.'],
 sked:['Schedule','Season grid and strength of schedule by slot.'],
 intel:['Scheme & usage','Coordinator scheme tags, tendencies, scheme × slot and player usage.'],
 players:['Players','Depth charts for any two teams and the full player card.'],
 fantasy:['Fantasy roster','Your roster’s matchups — or the waiver radar when no roster is selected.']};
function heroFor(v){const d=$('#'+v);if(!d)return;let h=d.querySelector(':scope>.v2hero');if(!h){h=document.createElement('div');h.className='v2hero';d.prepend(h)}
  const [t,sub]=VIEWS[v]||[v,''];const sum=($('#gSum')||{}).textContent||'';
  const sec=typeof SECOF!=='undefined'?SECOF[v]:'';const SN={bets:'Bets',games:'Games',match:'Matchups',def:'Defenses',plyr:'Players'}[sec]||'';
  h.innerHTML=`<div><div class="eb">${SN} &middot; week ${G.week}</div><h1>${t}</h1><p>${sub}</p></div>`;
  if(v==='bets')kpis(d)}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function kickTime(g){try{const [hm,ap]=(g[GM.time]||'1:00 PM').split(' ');let [H,M]=hm.split(':').map(Number);if(ap==='PM'&&H<12)H+=12;if(ap==='AM'&&H===12)H=0;
  const d=new Date(g[GM.date]+'T00:00:00-04:00');d.setHours(d.getHours()+H,d.getMinutes()+M);return d}catch(e){return null}}
function kpis(d){let k=d.querySelector(':scope>.kpis');if(!k){k=document.createElement('div');k.className='kpis';d.querySelector(':scope>.v2hero').after(k)}
  const wk=G.week,gs=GAMES(wk).filter(g=>inF(g[GM.vis])||inF(g[GM.home]));const now=new Date();
  const next=gs.map(g=>({g,t:kickTime(g)})).filter(x=>x.t&&x.t>now).sort((a,b)=>a.t-b.t)[0];
  const cd=next?(()=>{const s=(next.t-now)/1000,dd=Math.floor(s/86400),hh=Math.floor(s%86400/3600),mm=Math.floor(s%3600/60);return dd?`${dd}d ${hh}h`:hh?`${hh}h ${mm}m`:`${mm}m`})():'';
  const st=UNIVERSE.filter(u=>u.grp&&inU(u)&&inP(u.pos)&&u.inj!=='-1'&&u.slot===(u.grp==='QB'?'QB1':u.grp));
  const D=J.dvp[typeof DSRC!=='undefined'?DSRC:'combined'];let smash=null;st.forEach(u=>{const o=(J.sched26[u.team]||[])[wk-1];if(!o||o==='BYE')return;const def=o.replace('@','');const v=D[def]&&D[def].comps[u.grp];if(v!=null&&(!smash||v<smash.v))smash={u,v,def}});
  const BTk=J.betting;const edge=BTk?BTk.lines.filter(l=>inF(l.team)&&l.n_eff>=3).sort((a,b)=>b.ev-a.ev)[0]:null;
  const T=(key,go,lab,val,sub,kc)=>`<div class="kpi" data-go="${go}" style="--kc:${kc}"><div class="k">${lab}</div><div class="v">${val}</div><div class="s">${sub}</div></div>`;
  let riv=0,bd=0;try{gs.forEach(g=>riv+=storyCount(g,wk).riv);bd=bdUniverse().filter(x=>x.bd.days===0&&inF(x.team)).length}catch(e){}
  const plays=BTk?BTk.lines.filter(l=>inF(l.team)&&l.ev>=3).length:0;
  k.innerHTML=T('wk','games',`week ${wk}`,`${gs.length} games`,next?`next kick <b>${next.g[GM.vis]} @ ${next.g[GM.home]}</b> in <b>${cd}</b>`:'all games kicked off','rgba(143,163,255,.25)')
   +T('plays','bets','plays (EV ≥ 3%)',String(plays),BTk?`of ${BTk.lines.filter(l=>inF(l.team)).length} posted lines`:'no lines loaded','rgba(63,220,154,.22)')
   +(edge?T('edge','bets','best prop edge',(edge.ev>0?'+':'')+edge.ev+'%',`<b>${esc(edge.player)}</b> ${edge.side==='Over'?'o':'u'}${edge.line} ${edge.market.replace(/_/g,' ')}`,'rgba(63,220,154,.3)'):'')
   +T('smash','home','smash spot',smash?'Ψ '+smash.v.toFixed(1):'—',smash?`<b>${esc(smash.u.player)}</b> ${smash.u.grp} vs ${smash.def}`:'','rgba(95,214,228,.22)')
   +T('st','locker','storylines',`${riv} rivalries`,bd?`<b>${bd}</b> birthday${bd>1?'s':''} today`:'marquee clashes between starters','rgba(242,193,78,.22)');
  k.querySelectorAll('.kpi').forEach(t=>t.onclick=()=>{const go=t.dataset.go;if(go!==CURVIEW&&window.go)window.go(go)})}

const _enter=enter;enter=function(){const v=visible();if(v)heroFor(v.id);_enter()};
shell();hookRender();tilt();setTimeout(()=>{enter();polish()},0);/* setTimeout, not rAF: rAF never fires while the tab loads in the background */mo.observe(document.querySelector('main'),{childList:true,subtree:true});addEventListener('resize',()=>{const v=visible();if(v)overflow(v)});
setInterval(()=>{const v=visible();if(v&&v.id==='bets')kpis(v)},60000);
})();
