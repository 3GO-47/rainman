"""Tracking — dashboard/tracking.html: everything the user starred anywhere on the site (rainman.html game panes and slate tiles,
the Arb Engine rows, Social), held against the live markets. A tracked item is a game or a player market; the page shows the line
and price it was saved at, the best price now, how far the consensus has moved since, the model's number when there is one,
and a parlay slip that multiplies any legs the user ticks. Items live in this browser (localStorage rainman.track) — the page is
rebuilt by the loop every markets pass so the "now" side stays fresh.

Reads the same market pipeline as the Arb Engine (scripts/build_arb.py loaders) and the finals Social grades with."""
import os, sys, json, csv
from datetime import datetime, timezone
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, 'scripts')
import brand, build_arb as A, build_social as S
from track_js import TRACK_JS, TRACK_CSS

HEAD = S.HEAD
CSS = S.CSS + r"""
.trow{cursor:default}.mv{font:600 11px var(--mono)}.mv.up{color:var(--green)}.mv.dn{color:var(--red)}.spark{vertical-align:middle;margin-left:4px}
.legs{display:flex;flex-direction:column;gap:6px}.leg{display:grid;grid-template-columns:1fr auto auto;gap:8px;align-items:center;padding:6px 8px;border:1px solid var(--edge2);border-radius:7px;font-size:12px}.leg b{font-family:var(--mono)}
.chip{display:inline-block;font:600 9.5px var(--mono);letter-spacing:1px;padding:1px 6px;border:1px solid var(--edge2);border-radius:4px;color:var(--dim);text-transform:uppercase}.chip.g{color:var(--green);border-color:rgba(63,185,80,.5)}.chip.r{color:var(--red);border-color:rgba(240,86,74,.5)}.chip.p{color:#ffd600;border-color:#ffd60066}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.filters button{font:600 10.5px var(--mono);padding:4px 10px;border-radius:5px;border:1px solid var(--edge2);background:var(--panel);color:var(--dim);cursor:pointer}.filters button.on{color:var(--fg);border-color:var(--acc)}
td input.note{width:160px;background:var(--s2);border:1px solid var(--edge2);color:var(--fg);border-radius:4px;padding:3px 6px;font:500 11px var(--sans)}
.pk{font:600 10px var(--mono);padding:1px 5px;border-radius:3px;border:1px solid var(--edge2);color:var(--dim)}.pk.on{color:var(--green);border-color:rgba(63,185,80,.5)}
.howto{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;margin:10px 0}.howto div{border:1px solid var(--edge);border-radius:8px;padding:10px 12px;background:var(--panel);font-size:12px;color:var(--dim)}.howto b{display:block;color:var(--fg);margin-bottom:3px}.howto .star{color:#ffd600}
"""
CSS, CSS_VARS = brand.themed_css(CSS)

JS = r"""
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LS=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}},SV=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
const TZ='America/Chicago';const PD=d=>new Date(String(d).replace(/T(\d{2})Z$/,'T$1:00Z'));const when=d=>{const x=PD(d);return isNaN(x)?'':x.toLocaleString('en-US',{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:TZ}).replace(':00','')};
const am=dec=>dec>=2?'+'+Math.round((dec-1)*100):String(Math.round(-100/(dec-1)));const decOf=a=>a>0?1+a/100:1+100/(-a);const pct=p=>p==null?'—':(100*p).toFixed(0)+'%';
const STAT={pass_yds:'pass yds',pass_td:'pass TD',rush_yds:'rush yds',rush_att:'rush att',receptions:'receptions',rec_yds:'rec yds',anytime_td:'anytime TD'};
let FILT='all',SK='saved',SA=false;
const items=()=>TRK.all();
const gameOf=t=>J.games.find(g=>g.away===t.away&&g.home===t.home&&String(g.date).slice(0,10)===String(t.kickoff||'').slice(0,10))||J.games.find(g=>g.away===t.away&&g.home===t.home);
function boardFor(t){const g=gameOf(t);if(!g)return null;const R=J.board.filter(b=>b.event_id===g.id&&(t.market==='td'?b.stat==='anytime_td'&&b.player===t.player:t.market==='prop'?b.market==='prop'&&b.stat===t.stat&&b.player===t.player:b.market===t.market));if(!R.length)return null;
  if(t.point==null||t.point==='')return R[0];const p=+t.point;return R.slice().sort((a,b)=>Math.abs(+a.line-p)-Math.abs(+b.line-p))[0]}
function sideIs(t,b){if(t.market==='total'||t.market==='prop'||t.market==='td')return /^(over|yes)/i.test(t.selection||'')?'a':'b';return t.selection===b.away?'a':'b'}
function nowFor(t){const b=boardFor(t);if(!b)return null;const s=sideIs(t,b);return {line:b.line,src:b['best_'+s+'_src'],dec:+b['best_'+s+'_dec'],american:b['best_'+s+'_american'],fair:b['fair_'+s]!==''?+b['fair_'+s]:null,model:b.model_p!==''?(s==='a'?+b.model_p:1-+b.model_p):null,ev:b['ev_'+s]!==''?+b['ev_'+s]:null,b}}
function gameNow(t){const g=gameOf(t);if(!g)return null;const R=J.board.filter(b=>b.event_id===g.id);const sp=R.find(b=>b.market==='spread'),to=R.find(b=>b.market==='total'),ml=R.find(b=>b.market==='moneyline');if(!sp&&!to&&!ml)return null;return `${sp?`<b>${g.away} ${+sp.line>0?'+':''}${sp.line}</b> <span class="dim">${sp.best_a_american} / ${sp.best_b_american}</span>`:''}${to?` · O/U <b>${to.line}</b>`:''}${ml?` · ML <span class="dim">${ml.best_a_american} / ${ml.best_b_american}</span>`:''}`}
function hist(t){const g=gameOf(t);if(!g)return null;const k=[g.lg,g.away,g.home,String(g.date).slice(0,10),t.market==='td'?'prop':t.market,t.player||'',t.market==='td'?'anytime_td':(t.stat||'')].join('|');return J.hist[k]||null}
function movement(t){const h=hist(t);if(!h||h.length<2)return null;const s=sideIs(t,{away:t.away});const at=(t.saved||'').slice(0,16);let i0=0;for(let i=0;i<h.length;i++){if(h[i][0]<=at)i0=i}const o=h[i0],n=h[h.length-1];const dp=o[2]!=null&&n[2]!=null?(s==='a'?n[2]-o[2]:o[2]-n[2]):null;const dl=o[1]!=null&&n[1]!=null?n[1]-o[1]:null;return {dp,dl,n:h.length-i0,series:h.slice(i0).map(x=>s==='a'?x[2]:(x[2]==null?null:1-x[2])),from:o[0],to:n[0]}}
function spark(v){const s=(v||[]).filter(x=>x!=null);if(s.length<2)return '';const w=70,h=16;const mn=Math.min(...s),mx=Math.max(...s);const X=i=>i/(s.length-1)*w,Y=x=>h-1-(mx===mn?h/2:(x-mn)/(mx-mn)*(h-2));const up=s[s.length-1]>=s[0];return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline fill="none" stroke="${up?'var(--green)':'var(--red)'}" stroke-width="1.5" points="${s.map((x,i)=>X(i).toFixed(1)+','+Y(x).toFixed(1)).join(' ')}"/></svg>`}
function status(t){const g=gameOf(t);const k=g?[g.lg,g.away,g.home,String(g.date).slice(0,10)].join('|'):'';const r=J.results[k];if(r)return {s:'final',txt:`final ${r[0]}-${r[1]}`};const ko=PD((g&&g.date)||t.kickoff);if(!isNaN(ko)&&ko<new Date())return {s:'live',txt:'kicked off'};return {s:'open',txt:'open'}}
function label(t){if(t.label)return t.label;if(t.market==='game')return `${t.away} @ ${t.home} · game`;if(t.market==='td')return `${t.player} anytime TD ${t.selection||'Yes'}`;if(t.market==='prop')return `${t.player} ${t.selection} ${t.point} ${STAT[t.stat]||t.stat}`;if(t.market==='spread')return `${t.selection} ${+t.point>0?'+':''}${t.point}`;if(t.market==='total')return `${t.selection} ${t.point}`;return `${t.selection} ML`}
function rows(){let R=items();if(FILT==='games')R=R.filter(t=>t.kind==='game'||['moneyline','spread','total','game'].includes(t.market));if(FILT==='players')R=R.filter(t=>t.kind==='player'||['prop','td'].includes(t.market));if(FILT==='parlay')R=R.filter(t=>t.parlay);if(FILT==='open')R=R.filter(t=>status(t).s==='open');
  const key=t=>{const n=nowFor(t),m=movement(t);return {saved:t.saved||'',kick:t.kickoff||'',game:(t.away||'')+(t.home||''),bet:label(t),line:+t.point||0,price:+t.price||0,now:n?n.dec:0,move:m&&m.dp!=null?m.dp:-9,fair:n&&n.fair!=null?n.fair:-1,model:n&&n.model!=null?n.model:-1,src:t.source||''}[SK]};
  return R.map(t=>({t,k:key(t)})).sort((a,b)=>(a.k>b.k?1:a.k<b.k?-1:0)*(SA?1:-1)).map(x=>x.t)}
function render(){const all=items();const R=rows();const open=all.filter(t=>status(t).s==='open').length;const legs=all.filter(t=>t.parlay);
  $('#kpis').innerHTML=`<div class="kpi"><span>tracked</span><b>${all.length}</b><small>${open} open · ${all.length-open} started or final</small></div><div class="kpi"><span>games</span><b>${all.filter(t=>['moneyline','spread','total','game'].includes(t.market)).length}</b><small>lines and whole games</small></div><div class="kpi"><span>players</span><b>${all.filter(t=>['prop','td'].includes(t.market)).length}</b><small>props and anytime TD</small></div><div class="kpi"><span>moved your way</span><b class="g">${all.filter(t=>{const m=movement(t);return m&&m.dp!=null&&m.dp>0.01}).length}</b><small>consensus up since you saved it</small></div><div class="kpi"><span>moved against</span><b class="r">${all.filter(t=>{const m=movement(t);return m&&m.dp!=null&&m.dp<-0.01}).length}</b><small>consensus down since you saved it</small></div><div class="kpi"><span>parlay legs</span><b>${legs.length}</b><small>${legs.length?'ticked below':'tick ◻ on a row to add a leg'}</small></div>`;
  const th=(k,l,cls='')=>`<th data-k="${k}" class="${cls} ${SK===k?(SA?'srt-asc':'srt-desc'):''}">${l}</th>`;
  $('#list').innerHTML=all.length?`<table><thead><tr><th>◻</th>${th('saved','saved')}${th('kick','kickoff')}${th('game','game')}${th('bet','what you tracked')}${th('line','saved line')}${th('price','saved price')}${th('now','best now')}${th('move','consensus since')}${th('fair','fair now')}${th('model','model')}<th>status</th><th>note</th><th></th></tr></thead><tbody>${R.map((t,i)=>{const n=nowFor(t),m=t.market==='game'?movement(Object.assign({},t,{market:'spread',selection:t.away})):movement(t),st=status(t);const g=gameOf(t);
    return `<tr class="trow"><td><button class="pk${t.parlay?' on':''}" data-pk="${esc(t.id)}" title="add to / remove from the parlay slip">${t.parlay?'✓':'+'}</button></td><td class="dim">${when(t.saved)}</td><td>${when((g&&g.date)||t.kickoff)}</td><td><b>${esc(t.away||'')}</b> <span class="dim">@</span> <b>${esc(t.home||'')}</b> <span class="chip">${esc((t.league||'').toUpperCase())}</span></td><td>${esc(label(t))}${t.from?` <span class="dim">· ${esc(t.from)}</span>`:''}</td><td class="num">${t.point??'—'}</td><td class="num">${t.price!=null&&t.price!==''?esc(String(t.price)):'—'} <span class="dim">${esc(t.source||'')}</span></td>
      <td class="num">${t.market==='game'?(gameNow(t)||'<span class="dim">not on the board</span>'):n?`<b>${n.line??''}</b> ${esc(n.american||'')} <span class="dim">${esc(n.src||'')}</span>`:'<span class="dim">not on the board</span>'}</td>
      <td>${m&&m.dp!=null?`<span class="mv ${m.dp>0.005?'up':m.dp<-0.005?'dn':''}" title="${m.n} snapshots since you saved it (${m.from} → ${m.to}) · line ${m.dl!=null?(m.dl>0?'+':'')+m.dl.toFixed(1):'—'}">${m.dp>0?'+':''}${(100*m.dp).toFixed(1)}%${m.dl?` · line ${m.dl>0?'+':''}${m.dl.toFixed(1)}`:''}</span>${spark(m.series)}`:'<span class="dim">no snapshots yet</span>'}</td>
      <td class="num">${n&&n.fair!=null?pct(n.fair):'—'}</td><td class="num ${n&&n.ev!=null?(n.ev>0?'g':'r'):''}">${n&&n.model!=null?pct(n.model)+(n.ev!=null?` <small>${n.ev>0?'+':''}${(100*n.ev).toFixed(1)}% EV</small>`:''):'—'}</td>
      <td><span class="chip ${st.s==='final'?'':st.s==='live'?'r':'g'}">${st.txt}</span></td><td><input class="note" data-note="${esc(t.id)}" value="${esc(t.note||'')}" placeholder="why you like it"></td><td><button class="pk" data-rm="${esc(t.id)}" title="remove from Tracking">×</button></td></tr>`}).join('')}</tbody></table>`:`<div class="empty">nothing tracked yet — press <span style="color:#ffd600">★</span> on any game tile or game pane on the NFL / CFB dashboards, or on any row of the Arb Engine, and it lands here</div>`;
  $$('#list th[data-k]').forEach(h=>h.onclick=()=>{const k=h.dataset.k;if(SK===k)SA=!SA;else{SK=k;SA=k==='bet'||k==='game'}render()});
  $$('#list [data-rm]').forEach(b=>b.onclick=()=>{const a=items().filter(t=>t.id!==b.dataset.rm);TRK.save(a);render()});
  $$('#list [data-pk]').forEach(b=>b.onclick=()=>{const a=items();const t=a.find(x=>x.id===b.dataset.pk);if(t){t.parlay=!t.parlay;TRK.save(a);render()}});
  $$('#list input[data-note]').forEach(i=>i.onchange=()=>{const a=items();const t=a.find(x=>x.id===i.dataset.note);if(t){t.note=i.value;TRK.save(a)}});
  $$('.filters button').forEach(b=>b.classList.toggle('on',b.dataset.f===FILT));
  slip()}
function slip(){const legs=items().filter(t=>t.parlay);const el=$('#slip');if(!legs.length){el.innerHTML='<div class="empty">tick + on any tracked rows to build a parlay — the slip multiplies the best current price of every leg and shows the model\'s combined probability when it has one</div>';return}
  const stake=+($('#stake')&&$('#stake').value||LS('rainman.parlayStake',10));let dec=1,fair=1,model=1,nf=0,nm=0;const L=legs.map(t=>{const n=nowFor(t);const d=n&&n.dec?n.dec:(t.price!=null&&t.price!==''?decOf(+t.price):null);if(d)dec*=d;if(n&&n.fair!=null){fair*=n.fair;nf++}if(n&&n.model!=null){model*=n.model;nm++}return {t,n,d}});
  const allPriced=L.every(x=>x.d);const same=new Set(legs.map(t=>t.away+'@'+t.home)).size<legs.length;
  el.innerHTML=`<div class="legs">${L.map(x=>`<div class="leg"><span>${esc(label(x.t))} <span class="dim">· ${esc(x.t.away)} @ ${esc(x.t.home)}</span></span><b>${x.d?am(x.d):'—'}</b><span class="dim">${x.n?esc(x.n.src||''):'saved price'}</span></div>`).join('')}</div>
   <div class="kpis" style="margin-top:10px"><div class="kpi"><span>legs</span><b>${legs.length}</b><small>${same?'<span class="r">two legs share a game — books treat that as an SGP with its own pricing</span>':'independent games'}</small></div><div class="kpi"><span>parlay price</span><b>${allPriced?am(dec):'—'}</b><small>${allPriced?`decimal ${dec.toFixed(2)} · implied ${pct(1/dec)}`:'a leg has no price'}</small></div><div class="kpi"><span>fair · market</span><b>${nf===legs.length?pct(fair):'—'}</b><small>${nf===legs.length?`de-vigged consensus, all ${nf} legs`:`${nf} of ${legs.length} legs have a fair number`}</small></div><div class="kpi ${nm===legs.length&&allPriced?(model*dec>1?'g':'r'):''}"><span>model</span><b>${nm===legs.length?pct(model):'—'}</b><small>${nm===legs.length&&allPriced?`EV ${((model*dec-1)*100).toFixed(1)}% at this price`:`${nm} of ${legs.length} legs have a model number`}</small></div><div class="kpi"><span>stake → payout</span><b>${allPriced?'$'+(stake*dec).toFixed(2):'—'}</b><small>stake $<input id="stake" value="${stake}" style="width:54px;background:var(--s2);border:1px solid var(--edge2);color:var(--fg);border-radius:4px;padding:2px 4px;font:600 11px var(--mono)"> · profit ${allPriced?'$'+(stake*(dec-1)).toFixed(2):'—'}</small></div></div>
   <p style="margin:10px 0 0"><button class="btn" id="toSocial">save this parlay to Social as a play</button> <button class="btn ghost" id="clearP">clear legs</button></p>`;
  $('#stake').onchange=()=>{SV('rainman.parlayStake',+$('#stake').value||10);slip()};
  $('#clearP').onclick=()=>{const a=items();a.forEach(t=>t.parlay=false);TRK.save(a);render()};
  $('#toSocial').onclick=()=>{if(!allPriced){TRK.toast('every leg needs a price first');return}const P=LS('rainman.plays',[]);const id='parlay|'+legs.map(t=>t.id).join('||');if(P.some(p=>p.id===id)){TRK.toast('already saved');return}
    P.push({id,league:legs[0].league||'',game:legs.map(t=>t.away+' @ '+t.home).filter((v,i,a)=>a.indexOf(v)===i).join(' + '),kickoff:legs.map(t=>t.kickoff||'').sort()[0]||'',market:'parlay',selection:legs.map(t=>label(t)).join(' + '),point:'',player:'',stat:'',side:'',source:'parlay',dec:+dec.toFixed(4),american:am(dec),fair:nf===legs.length?+fair.toFixed(4):null,ev:nm===legs.length?+((model*dec-1)).toFixed(4):null,conf:null,tier:'',saved:new Date().toISOString(),status:'open',from:'tracking',legs:legs.map(t=>({label:label(t),away:t.away,home:t.home,kickoff:t.kickoff,market:t.market,selection:t.selection,point:t.point}))});
    SV('rainman.plays',P);TRK.toast(`parlay saved · set a stake on <a href="social.html">Social</a>`)}}
$$('.filters button').forEach(b=>b.onclick=()=>{FILT=b.dataset.f;render()});
$('#exp').onclick=()=>{const blob=new Blob([JSON.stringify(items(),null,1)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='rainman-tracking.json';a.click()};
$('#imp').onchange=e=>{const f=e.target.files[0];if(!f)return;f.text().then(t=>{try{const a=JSON.parse(t);if(Array.isArray(a)){const cur=items();a.forEach(x=>{if(x&&x.id&&!cur.some(y=>y.id===x.id))cur.push(x)});TRK.save(cur);render();TRK.toast('restored')}}catch(x){TRK.toast('not a tracking file')}})};
$('#wipe').onclick=()=>{if(confirm('remove everything from Tracking in this browser?')){TRK.save([]);render()}};
render();window.addEventListener('storage',e=>{if(e.key===TRK.key)render()});
"""

def main():
    G = A.slate()
    oa, has_dk = A.load_oddsapi(G)
    lines = (A.load_dk(G) if not has_dk else []) + oa + A.load_props(G) + A.load_kalshi(G) + A.load_poly(G)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    live = [l for l in lines if l['kickoff'] > now]
    M = A.load_model()
    board, arbs, evs, H = A.analyse(live, G, M)
    keep = ('league', 'event_id', 'kickoff', 'away', 'home', 'market', 'line', 'side_a', 'side_b', 'player', 'stat', 'fair_a', 'fair_b', 'best_a_src', 'best_a_dec', 'best_a_american', 'best_b_src', 'best_b_dec', 'best_b_american', 'model_p', 'ev_a', 'ev_b')
    board = [{k: b.get(k, '') for k in keep} for b in board]
    games = [dict(id=k, lg=g['lg'], date=g['date'], away=g['away'], home=g['home']) for k, g in G.items()]
    hist = {k: [[x[0][5:16], x[1], x[2]] for x in v[-40:]] for k, v in H.items()}
    results = {k: list(v) for k, v in S.results().items()}
    J = dict(games=games, board=board, hist=hist, results=results, built=datetime.now().strftime('%Y-%m-%d %H:%M'))
    built = J['built']
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{brand.THEME_BOOT}<title>RAINMAN · Tracking</title>{HEAD}<style>{brand.THEME_CSS}{brand.alias_css("alt")}{brand.SWITCH_CSS}.brand .rmask{{vertical-align:-5px;margin-right:4px}}{CSS_VARS}{CSS}{TRACK_CSS}
@media (max-width:760px){{
 html,body{{overflow-x:hidden;max-width:100vw}}
 body{{font-size:12px}}
 #hdr{{flex-wrap:wrap;height:auto!important;min-height:0;padding:6px 10px!important;gap:6px 10px!important;row-gap:4px}}
 #hdr .brand{{font-size:13px}}#hdr .brand small{{display:none}}
 #hdr .tag,#hdr .mini{{display:none}}
 #hdr .hl,#hdr .tabs,#hdr nav{{flex-wrap:wrap;gap:3px;margin-left:0}}
 #hdr .hl a,#hdr .tabs a,#hdr .tabs button,#hdr nav a{{padding:5px 8px;min-height:30px;display:inline-flex;align-items:center;font-size:11.5px}}
 main{{padding:8px!important}}
 .panel{{padding:8px!important;border-radius:5px}}
 h1{{font-size:15px}}h2{{font-size:13px}}h3{{font-size:12px}}
 .mscroll{{overflow-x:auto;width:0;min-width:100%;max-width:100%;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain;position:relative}}
 .mgrid1>*,.panel,main>*{{min-width:0}}
 header{{flex-wrap:wrap;height:auto;padding:6px 10px;gap:6px 10px}}header nav{{flex-wrap:wrap}}
 .mscroll>table{{font-size:11px;width:max-content;min-width:100%}}
 .mscroll>table th,.mscroll>table td{{white-space:nowrap;max-width:220px;overflow:hidden;text-overflow:ellipsis}}
 .mscroll>table th:first-child,.mscroll>table td:first-child{{position:sticky;left:0;z-index:2;background:#000;box-shadow:1px 0 0 var(--edge2,#222)}}
 .mscroll>table thead th{{position:sticky;top:0;z-index:3}}
 .mscroll>table thead th:first-child{{z-index:4}}
 .mscroll.one>table th:first-child,.mscroll.one>table td:first-child{{position:static;box-shadow:none}}
 .mgrid1{{grid-template-columns:1fr!important}}
 select,input[type=text],input[type=search],input[type=number]{{min-height:32px;font-size:13px}}
 .chips button,button.sw,.chip{{min-height:30px;padding:5px 9px}}
 .modal{{padding:0!important;align-items:stretch!important}}
 .modal .modalbox,.modal .modalbox.wide,.modalbox{{max-width:100%!important;width:100%;min-height:100%;padding:10px 10px 40px!important;border-left:0;border-right:0}}
 .mclose{{position:sticky!important;top:0;float:right;z-index:5;min-height:32px;padding:4px 12px}}
 .sfoot{{flex-wrap:wrap;gap:8px}}
 .trk{{min-width:26px;line-height:22px}}
}}
</style></head><body>
<div id="hdr"><a class="brand" href="index.html">{brand.mascot("counting", 20, "rmask hdr")}RAINMAN</a><span class="tag">Tracking · your watchlist and parlay slip</span><span class="hl"><a href="index.html">all sports</a><a href="arb.html">Arb Engine</a><a href="social.html">Social</a><a class="on" href="tracking.html">Tracking</a>{brand.theme_switch_html()}</span><span class="right">markets as of {built}</span></div>
<div class="wrap">
<h1>Tracking<small>Every game, line and player market you starred anywhere on the site, held against the market right now: the line and price you saved it at, the best price available this minute, how far the consensus has moved since, and the model's number when it has one. Tick legs to build a parlay. Everything lives in this browser — nothing leaves your machine.</small></h1>
<div class="howto"><div><b><span class="star">★</span> on a slate tile</b>tracks the whole game — its spread, total and moneyline move together here.</div><div><b><span class="star">★</span> on a game pane row</b>tracks one line or one player market: a prop, an anytime-TD price, a spread side.</div><div><b><span class="star">★</span> on an Arb Engine row</b>tracks that exact price at that book or exchange, so you can see if it was the top of the market.</div><div><b>consensus since</b>how the de-vigged market probability for your side has moved since the moment you saved it (Odds API snapshots, every pass); green = it moved your way.</div></div>
<div id="kpis" class="kpis"></div>
<div class="filters"><button data-f="all" class="on">all</button><button data-f="open">open</button><button data-f="games">games &amp; lines</button><button data-f="players">players</button><button data-f="parlay">parlay legs</button><span style="flex:1"></span><button id="exp">backup</button><label style="cursor:pointer"><button style="pointer-events:none">restore</button><input id="imp" type="file" accept="application/json" hidden></label><button id="wipe">clear</button></div>
<div id="list"></div>
<h2>parlay slip <span>tick + on any rows above · the slip prices the legs at the best current price and shows the model's combined probability</span></h2><div id="slip"></div>
<div class="foot">RAINMAN · Tracking (local prototype) · the watchlist is stored in this browser only; backup writes it to a file you can restore on another device. Prices from the same sources the Arb Engine reads (DraftKings via ESPN, the Odds API books, Kalshi, Polymarket), rebuilt every markets pass. Information, not advice.</div></div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script><script>{TRACK_JS}</script><script>{JS}</script><script>{brand.THEME_JS}</script><script>(function(){{const mq=matchMedia('(max-width:760px)');let mo,tm;
function wrap(){{document.querySelectorAll('table').forEach(t=>{{if(t.closest('.mscroll,.tw,.tscroll,#mnav'))return;if(t.parentElement&&t.parentElement.closest('table'))return;const w=document.createElement('div');w.className='mscroll';t.parentNode.insertBefore(w,t);w.appendChild(t);const f=t.querySelector('tr');if(f&&f.children.length<=2)w.classList.add('one')}})}}
function grids(){{document.querySelectorAll('main *,body>div *').forEach(e=>{{if(e.classList.contains('mgrid1')||e.dataset.mg)return;const cs=getComputedStyle(e);if(cs.display!=='grid')return;const tr=cs.gridTemplateColumns.split(' ').filter(Boolean);e.dataset.mg='1';if(tr.length<2)return;const row=tr.some(x=>/^\d+(\.\d+)?px$/.test(x)&&parseFloat(x)<90);if(row)return;if(e.scrollWidth>e.clientWidth+2||tr.length>=3)e.classList.add('mgrid1')}})}}
function pass(){{wrap();grids()}}
function on(){{document.documentElement.classList.add('mob');pass();mo=new MutationObserver(()=>{{clearTimeout(tm);tm=setTimeout(pass,150)}});mo.observe(document.body,{{childList:true,subtree:true}})}}
function off(){{document.documentElement.classList.remove('mob');if(mo)mo.disconnect()}}
if(mq.matches)on();mq.addEventListener('change',e=>e.matches?on():off());window.rmMobile=mq}})();</script></body></html>"""
    os.makedirs('dashboard', exist_ok=True)
    open('dashboard/tracking.html', 'w', encoding='utf-8').write(html)
    print(f'tracking: {len(board)} markets on the board · {len(hist)} histories · {len(games)} games · dashboard/tracking.html {len(html)//1024} KB')

if __name__ == '__main__':
    main()
