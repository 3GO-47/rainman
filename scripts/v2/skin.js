/* RAINMAN v2 shell: sidebar rail with spring indicator, view transitions, staggered cards, count-up numbers, card tilt. */
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
 locker:'<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z"/>',
 help:'<circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1.1.9-1.1 1.6v.6M12 17h.01"/>'};
const ico=k=>`<svg class="ico" viewBox="0 0 24 24">${I[k]||I.home}</svg>`;
function shell(){
  const nav=$('#top nav');if(!nav)return;
  const sub=$('header .sub');
  const rail=document.createElement('aside');rail.id='rail';
  rail.innerHTML=`<div class="brand"><i><svg width="16" height="16" viewBox="0 0 16 16"><ellipse cx="8" cy="8" rx="6.6" ry="4.1" transform="rotate(-28 8 8)" fill="#0b0d14"/><path d="M5.8 9.7 L10.2 6.3" stroke="#fff" stroke-width="1.1"/></svg></i><div>RAINMAN<small>defense-vs-position</small></div></div>`;
  rail.appendChild(nav);
  const meta=document.createElement('div');meta.className='meta';
  meta.innerHTML=(sub?sub.innerHTML.replace(/DVP TERMINAL &middot; |DVP TERMINAL · /,'').replace(/ &middot; p&#8407;.*$| · p⃗.*$/,''):'')+`<a class="v1link" href="https://3go-47.github.io/rainman/v1/">← classic view (v1)</a>`;
  rail.appendChild(meta);document.body.prepend(rail);
  nav.querySelectorAll('button[data-v]').forEach(b=>{const fk=b.querySelector('.fk');const label=[...b.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim();
    b.innerHTML=ico(b.dataset.v)+`<span class="lbl">${label}</span>`+(fk?fk.outerHTML:'');b.title=label});
  const h=$('#gHelp');if(h){h.innerHTML=ico('help')+'<span class="lbl">Glossary</span><span class="fk">?</span>';h.style.marginLeft='0'}
  const ind=document.createElement('div');ind.className='ind';nav.prepend(ind);
  const place=()=>{const on=nav.querySelector('button.on');if(!on)return;ind.style.transform=`translateY(${on.offsetTop}px)`;ind.style.height=on.offsetHeight+'px'};
  nav.addEventListener('click',e=>{if(e.target.closest('button[data-v]'))requestAnimationFrame(()=>{place();enter()})});
  addEventListener('resize',place);setTimeout(place,30);
  const sticky=()=>document.documentElement.style.setProperty('--sticky',$('#top').offsetHeight+'px');sticky();addEventListener('resize',sticky);
}
function visible(){return $$('main>div').find(d=>!d.hidden)}
let enter=function(){const v=visible();if(!v||RM)return;v.classList.remove('v2enter');void v.offsetWidth;v.classList.add('v2enter');stagger(v);countUp(v)};
function stagger(root){const ps=[...root.querySelectorAll('.panel')].filter(p=>p.offsetParent).slice(0,14);
  ps.forEach((p,i)=>{p.classList.remove('v2stagger');void p.offsetWidth;p.style.setProperty('--i',i);p.classList.add('v2stagger')})}
const NUM=/^[+-]?\d{1,4}(\.\d{1,2})?$/;
function countUp(root){if(RM)return;const els=[...root.querySelectorAll('td>b, .sm-psi, .psi')].filter(e=>e.offsetParent&&NUM.test(e.textContent.trim())).slice(0,160);
  const t0=performance.now(),D=650;const data=els.map(e=>{const s=e.textContent.trim();return {e,v:+s,dp:(s.split('.')[1]||'').length,s,pre:s[0]==='+'?'+':''}});
  const tick=t=>{const k=Math.min(1,(t-t0)/D),q=1-Math.pow(1-k,4);data.forEach(d=>{d.e.textContent=k<1?d.pre+(d.v*q).toFixed(d.dp):d.s});if(k<1)requestAnimationFrame(tick)};requestAnimationFrame(tick)}
/* spring tilt on game cards: rotate toward the cursor, settle back with overshoot */
function tilt(){if(RM||matchMedia('(hover:none)').matches)return;
  document.addEventListener('mousemove',e=>{const c=e.target.closest('.gamecard,.panel.story');$$('.tilt-on').forEach(x=>{if(x!==c){x.classList.remove('tilt-on');x.style.transition='transform .7s var(--spring)';x.style.transform=''}});
    if(!c)return;const r=c.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;
    c.classList.add('tilt-on','tilt');c.style.transition='transform .12s ease-out';c.style.transform=`perspective(1400px) rotateX(${(-y*2.2).toFixed(2)}deg) rotateY(${(x*2.6).toFixed(2)}deg) translateY(-2px)`},{passive:true})}
/* re-run the entrance on filter changes for the visible view (lighter: count-up only) */
function hookRender(){const o=window.runView;if(typeof o!=='function')return;window.runView=function(v){const r=o.apply(this,arguments);requestAnimationFrame(()=>{const vis=visible();if(vis&&vis.id===v){heroFor(v);countUp(vis)}});return r}}

/* ---------- page hero per view + Home KPI tiles (all values computed from the same payload as v1) ---------- */
const VIEWS={home:['Home','This week at a glance — projections, matchups, storylines, waiver targets.'],board:['Big Board','Every player projected for the week, with the full factor breakdown and the walk-forward Model Lab.'],
 chamber:['Weekly Matchups','Every game: each offense’s slot owners against the opposing defense’s allowed-stats field.'],players:['Players','Depth charts, the matchup lab across positions, and full player deep dives.'],
 defenses:['Defenses','Rankings, the 32 × slot matrix and each defense’s weekly observatory.'],tdb:['TD Board','Who faces the defenses that give up touchdowns to their role.'],sked:['Schedule','Season grid and strength of schedule by slot.'],
 intel:['Intel','Scheme tags, tendencies, coaching and starter turnover, usage.'],games:['Games & Picks','Market lines vs the model, frozen picks ledger, player props.'],locker:['Locker Room','Rivalries, alumni reunions, homecomings, revenge games and birthdays.']};
function heroFor(v){const d=$('#'+v);if(!d)return;let h=d.querySelector(':scope>.v2hero');if(!h){h=document.createElement('div');h.className='v2hero';d.prepend(h)}
  const [t,sub]=VIEWS[v]||[v,''];const sum=($('#gSum')||{}).textContent||'';
  h.innerHTML=`<div><div class="wk">${esc(sum.split(' · ').slice(0,3).join(' · '))}</div><h1>${t}</h1><p>${sub}</p></div>`;
  if(v==='home')kpis(d)}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function kickTime(g){try{const [hm,ap]=(g[GM.time]||'1:00 PM').split(' ');let [H,M]=hm.split(':').map(Number);if(ap==='PM'&&H<12)H+=12;if(ap==='AM'&&H===12)H=0;
  const d=new Date(g[GM.date]+'T00:00:00-04:00');d.setHours(d.getHours()+H,d.getMinutes()+M);return d}catch(e){return null}}
function kpis(d){let k=d.querySelector(':scope>.kpis');if(!k){k=document.createElement('div');k.className='kpis';d.querySelector(':scope>.v2hero').after(k)}
  const wk=G.week,gs=GAMES(wk).filter(g=>inF(g[GM.vis])||inF(g[GM.home]));const now=new Date();
  const next=gs.map(g=>({g,t:kickTime(g)})).filter(x=>x.t&&x.t>now).sort((a,b)=>a.t-b.t)[0];
  const cd=next?(()=>{const s=(next.t-now)/1000,dd=Math.floor(s/86400),hh=Math.floor(s%86400/3600),mm=Math.floor(s%3600/60);return dd?`${dd}d ${hh}h`:hh?`${hh}h ${mm}m`:`${mm}m`})():'';
  const st=UNIVERSE.filter(u=>u.grp&&inU(u)&&inP(u.pos)&&u.inj!=='-1'&&u.slot===(u.grp==='QB'?'QB1':u.grp));
  let top=null;st.forEach(u=>{const r=projection(u,wk);if(r&&(!top||r.p>top.r.p))top={u,r}});
  const D=J.dvp.combined;let smash=null;st.forEach(u=>{const o=(J.sched26[u.team]||[])[wk-1];if(!o||o==='BYE')return;const def=o.replace('@','');const v=D[def]&&D[def].comps[u.grp];if(v!=null&&(!smash||v<smash.v))smash={u,v,def}});
  let wv=null;try{wv=waiverRows(wk)[0]}catch(e){}
  let riv=0,bd=0;try{gs.forEach(g=>riv+=storyCount(g,wk).riv);bd=bdUniverse().filter(x=>x.bd.days===0&&inF(x.team)).length}catch(e){}
  const T=(key,go,lab,val,sub,kc)=>`<div class="kpi" data-go="${go}" style="--kc:${kc}"><div class="k">${lab}</div><div class="v">${val}</div><div class="s">${sub}</div></div>`;
  k.innerHTML=T('wk','chamber',`week ${wk}`,`${gs.length} games`,next?`next kick <b>${next.g[GM.vis]} @ ${next.g[GM.home]}</b> in <b>${cd}</b>`:'all games kicked off','rgba(143,163,255,.25)')
   +T('top','board','top projection',top?top.r.p.toFixed(1)+' <span style="font-size:13px;color:var(--dim);font-weight:500">PPR</span>':'—',top?`<b>${esc(top.u.player)}</b> ${top.u.team} · ${top.u.dslot||top.u.slot}`:'','rgba(63,220,154,.22)')
   +T('smash','players','smash spot',smash?'Ψ '+smash.v.toFixed(1):'—',smash?`<b>${esc(smash.u.player)}</b> ${smash.u.grp} vs ${smash.def}`:'','rgba(95,214,228,.22)')
   +T('wv','home','waiver #1',wv?esc(wv.u.player.split(' ').slice(-1)[0]):'—',wv?`${wv.u.team} ${wv.u.dslot} · score <b>${wv.score.toFixed(1)}</b>`:'','rgba(182,156,255,.24)')
   +T('st','locker','storylines',`${riv} rivalries`,bd?`<b>${bd}</b> birthday${bd>1?'s':''} today`:'marquee clashes between starters','rgba(242,193,78,.22)');
  k.querySelectorAll('.kpi').forEach(t=>t.onclick=()=>{const go=t.dataset.go;if(go==='home'){const s=$('#lineupSlot');if(s)s.scrollIntoView({behavior:'smooth',block:'start'});return}const b=$(`nav button[data-v="${go}"]`);if(b)b.click()})}

const _enter=enter;enter=function(){const v=visible();if(v)heroFor(v.id);_enter()};
shell();hookRender();tilt();requestAnimationFrame(enter);
setInterval(()=>{const v=visible();if(v&&v.id==='home')kpis(v)},60000);
})();
