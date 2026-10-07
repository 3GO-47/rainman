"""Layer 0 — the multi-sport landing page -> dashboard/index.html, plus Layer-1 shells for the sports that have no data
pipeline yet (nba.html, ncaab.html, wnba.html, mlb.html, nhl.html, soccer.html) from the same slate file.

Usage: python3 scripts/build_landing.py
Input : data/raw/slate_all_YYYY-MM-DD.txt (latest; ESPN scoreboard pulls, see notes/scrape_recipe.md "multi-sport slate")
Every number on the page comes from that file; nothing is typed in by hand. NFL -> rainman.html, CFB -> ncaa.html.
"""
import os, glob, json, re
from datetime import datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
LEAGUES = [  # key, label, sport group, page, status, icon
    ('nfl', 'NFL', 'football', 'rainman.html', 'live', 'football'),
    ('cfb', 'CFB', 'football', 'ncaa.html', 'live', 'football'),
    ('nba', 'NBA', 'basketball', 'nba.html', 'shell', 'basketball'),
    ('ncaab', 'NCAAB', 'basketball', 'ncaab.html', 'shell', 'basketball'),
    ('wnba', 'WNBA', 'basketball', 'wnba.html', 'shell', 'basketball'),
    ('mlb', 'MLB', 'baseball', 'mlb.html', 'shell', 'baseball'),
    ('nhl', 'NHL', 'hockey', 'nhl.html', 'shell', 'hockey'),
    ('soccer', 'Soccer', 'soccer', 'soccer.html', 'shell', 'soccer')]
SOCCER = {'epl': 'Premier League', 'mls': 'MLS', 'ucl': 'Champions League', 'laliga': 'La Liga', 'bund': 'Bundesliga', 'seriea': 'Serie A', 'ligue1': 'Ligue 1'}
COMING = [('golf', 'Golf'), ('ufc', 'UFC'), ('f1', 'F1'), ('tennis', 'Tennis'), ('nascar', 'NASCAR')]

def load_slate():
    files = sorted(glob.glob('data/raw/slate_all_*.txt'))
    if not files: raise SystemExit('no data/raw/slate_all_*.txt — pull the multi-sport slate first (notes/scrape_recipe.md)')
    f = files[-1]; pulled = re.search(r'(\d{4}-\d{2}-\d{2})', f).group(1)
    games = []
    for line in open(f, encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 26: continue
        lg = p[1]
        games.append(dict(lg=lg, sport='soccer' if lg in SOCCER else lg, sub=SOCCER.get(lg, ''), id=p[2], date=p[3], status=p[4],
                          away=dict(id=p[5], abbr=p[6], name=p[7], rec=p[8], logo=p[9], rank=p[10] if p[10] not in ('', '99') else ''),
                          home=dict(id=p[11], abbr=p[12], name=p[13], rec=p[14], logo=p[15], rank=p[16] if p[16] not in ('', '99') else ''),
                          venue=p[17], tv=p[18], odds=p[19], ou=p[20], week=p[21], neutral=p[23] == '1', book=p[24], note=p[25]))
    return games, pulled

CSS = """
:root{--bg:#000;--panel:#0b0b0c;--s2:#131315;--s3:#1a1a1d;--edge:#1d1e21;--edge2:#2a2b30;--fg:#e6e6e9;--dim:#8b8d94;--mute:#5c5e66;--acc:#e8b339;--green:#3fb950;--red:#f0564a;--blue:#58a6ff;--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;--sans:'Inter',system-ui,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:13px;line-height:1.45}
a{color:inherit;text-decoration:none}
#hdr{display:flex;align-items:center;gap:18px;padding:12px 22px;border-bottom:1px solid var(--edge);background:linear-gradient(180deg,#0e0e10,#000)}
#hdr .brand{font-family:var(--mono);font-weight:700;letter-spacing:.22em;font-size:15px}#hdr .brand i{color:var(--acc);font-style:normal}
#hdr .tag{color:var(--dim);font-size:12px}#hdr .right{margin-left:auto;font-family:var(--mono);color:var(--dim);font-size:11px}
.wrap{max-width:1500px;margin:0 auto;padding:16px 22px 60px}
h2{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin:26px 0 10px;font-weight:600}h2 span{color:var(--mute);text-transform:none;letter-spacing:0;font-weight:400;margin-left:8px}
#field{position:relative;height:300px;border:1px solid var(--edge);border-radius:14px;background:radial-gradient(ellipse at 50% 120%,#15130c 0%,#000 60%);overflow:hidden}
#field canvas{position:absolute;inset:0;width:100%;height:100%}
.bub{position:absolute;left:0;top:0;width:var(--d);height:var(--d);margin:calc(var(--d)/-2) 0 0 calc(var(--d)/-2);border-radius:50%;border:1px solid var(--edge2);background:radial-gradient(circle at 35% 30%,#232327,#0b0b0c 70%);display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;user-select:none;box-shadow:0 0 0 1px #000,0 10px 30px rgba(0,0,0,.6);transition:box-shadow .15s,border-color .15s;will-change:transform}
.bub:hover,.bub.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc),0 0 30px rgba(232,179,57,.25)}
.bub b{font-size:13px;letter-spacing:.04em}.bub small{font-family:var(--mono);color:var(--dim);font-size:10px}.bub .ic{width:28px;height:28px;margin-bottom:4px;opacity:.9}
.bub.live b{color:var(--acc)}.bub .st{position:absolute;bottom:-9px;font-size:9px;font-family:var(--mono);padding:1px 6px;border-radius:9px;background:var(--s3);border:1px solid var(--edge2);color:var(--dim);letter-spacing:.08em}
.bub.live .st{background:#2b2309;border-color:#6b5415;color:var(--acc)}.bub.soon{opacity:.55}.bub.soon:hover{opacity:.9}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 0}.chip{font-family:var(--mono);font-size:11px;padding:4px 10px;border:1px solid var(--edge2);border-radius:14px;color:var(--dim);cursor:pointer;background:var(--panel)}
.chip.on{color:#000;background:var(--acc);border-color:var(--acc)}.chip:hover:not(.on){color:var(--fg);border-color:#444}
.lead{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:12px;margin-top:12px}.lead .card{background:var(--panel);border:1px solid var(--edge);border-radius:10px;padding:12px 14px}
.card .k{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}.card .v{font-family:var(--mono);font-size:22px;font-weight:700;margin:4px 0 2px}.card .s{color:var(--dim);font-size:11px}
.open{display:inline-flex;align-items:center;gap:8px;margin-top:8px;padding:7px 12px;border:1px solid var(--acc);border-radius:8px;color:var(--acc);font-family:var(--mono);font-size:11px;letter-spacing:.08em}
.open:hover{background:var(--acc);color:#000}.open.dim{border-color:var(--edge2);color:var(--dim)}
.days{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px}
.day{background:var(--panel);border:1px solid var(--edge);border-radius:10px;overflow:hidden}.day h3{margin:0;padding:8px 12px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);border-bottom:1px solid var(--edge);background:var(--s2);display:flex;justify-content:space-between}
.g{display:grid;grid-template-columns:70px 1fr auto;gap:8px;padding:8px 12px;border-bottom:1px solid var(--edge);align-items:center}.g:last-child{border-bottom:0}
.g .t{font-family:var(--mono);font-size:11px;color:var(--dim)}.g .t b{display:block;color:var(--fg)}
.g .tm{display:flex;align-items:center;gap:6px;font-size:12px}.g .tm img{width:20px;height:20px;object-fit:contain}.g .tm .rec{font-family:var(--mono);color:var(--mute);font-size:10px}.g .tm .rk{font-family:var(--mono);color:var(--acc);font-size:10px}
.g .tm .at{color:var(--mute);margin:0 2px}.g .ln{text-align:right;font-family:var(--mono);font-size:11px}.g .ln b{color:var(--fg)}.g .ln span{display:block;color:var(--dim);font-size:10px}
.g .sub{grid-column:1/-1;color:var(--mute);font-size:10px;margin-top:-4px}.g .sub em{color:var(--blue);font-style:normal}
.empty{color:var(--dim);padding:20px;border:1px dashed var(--edge2);border-radius:10px;text-align:center}
.teams{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}.team{display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--panel);border:1px solid var(--edge);border-radius:8px;font-size:12px}
.team img{width:26px;height:26px;object-fit:contain}.team small{display:block;color:var(--dim);font-family:var(--mono);font-size:10px}
.foot{margin-top:40px;color:var(--mute);font-size:11px;font-family:var(--mono);border-top:1px solid var(--edge);padding-top:12px}
@media(max-width:800px){.lead{grid-template-columns:1fr}#field{height:380px}.wrap{padding:12px 14px 40px}}
"""

ICONS = {
 'football': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><ellipse cx="12" cy="12" rx="10" ry="6.2" transform="rotate(-35 12 12)"/><path d="M8.5 15.5l7-7M9.5 12.5l1.3 1.3M11 11l1.3 1.3M12.5 9.5l1.3 1.3"/></svg>',
 'basketball': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9.5"/><path d="M2.5 12h19M12 2.5v19M5.3 5.3c3.8 3.6 3.8 9.8 0 13.4M18.7 5.3c-3.8 3.6-3.8 9.8 0 13.4"/></svg>',
 'baseball': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9.5"/><path d="M5 5.5c2.5 3 2.5 10 0 13M19 5.5c-2.5 3-2.5 10 0 13M6.2 8.5l1.5.5M6 11.5l1.6.1M6.2 14.5l1.5-.5M17.8 8.5l-1.5.5M18 11.5l-1.6.1M17.8 14.5l-1.5-.5"/></svg>',
 'hockey': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><ellipse cx="12" cy="15" rx="8.5" ry="3.3"/><path d="M3.5 15v-3c0 1.8 3.8 3.3 8.5 3.3s8.5-1.5 8.5-3.3v3"/></svg>',
 'soccer': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9.5"/><path d="M12 7l4.2 3-1.6 5h-5.2l-1.6-5z"/><path d="M12 7V2.6M16.2 10l4.3-1.4M14.6 15l2.7 3.6M9.4 15l-2.7 3.6M7.8 10L3.5 8.6"/></svg>',
 'soon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9.5"/><path d="M12 7v5l3 2"/></svg>'}

JS = r"""
const G=J.games,LG=J.leagues,SUB=J.soccer,FULL={cfb:'College Football',ncaab:'College Basketball'};
const logo=p=>p?'https://a.espncdn.com/i/teamlogos/'+p:'';
const TZD='America/Chicago';const fmtT=d=>new Date(d).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:TZD}).replace(':00','');
const dayKey=d=>new Date(d).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:TZD});
const byLg={};G.forEach(g=>{(byLg[g.sport]=byLg[g.sport]||[]).push(g)});
let SEL=location.hash.replace('#','')||'nfl',SUBSEL='';
/* ---------- the bubble field: a tiny physics sim (spring to anchor + pairwise repulsion + drag) ---------- */
const field=document.getElementById('field');const all=[...LG.map(l=>({...l,n:(byLg[l.key]||[]).length})),...J.coming.map(c=>({key:c[0],label:c[1],status:'soon',icon:'soon',n:0}))];
const B=all.map((l,i)=>{const d=l.status==='soon'?74:Math.round(96+Math.min(60,Math.sqrt(l.n)*7));
  const el=document.createElement('div');el.className='bub '+l.status+(l.key===SEL?' on':'');el.style.setProperty('--d',d+'px');el.dataset.k=l.key;
  el.innerHTML=`<div class="ic">${J.icons[l.icon]||J.icons.soon}</div><b>${l.label}</b><small>${FULL[l.key]?FULL[l.key]+' · ':''}${l.status==='soon'?'coming soon':l.n+' games'}</small><span class="st">${l.status==='live'?'LIVE MODEL':l.status==='shell'?'SCHEDULE':'SOON'}</span>`;
  field.appendChild(el);return {l,el,d,r:d/2,x:0,y:0,vx:0,vy:0,ax:0,ay:0}});
function layout(){const W=field.clientWidth,H=field.clientHeight,n=B.length;B.forEach((b,i)=>{b.ax=W*(i+.5)/n;b.ay=H/2+(i%2?28:-28);if(!b.x){b.x=b.ax+(Math.random()-.5)*40;b.y=-60-Math.random()*200}})}
layout();addEventListener('resize',layout);
let t0=performance.now();function step(now){const dt=Math.min(.05,(now-t0)/1000);t0=now;const W=field.clientWidth,H=field.clientHeight;
  for(const b of B){b.vx+=(b.ax-b.x)*3.2*dt;b.vy+=(b.ay-b.y)*3.2*dt;b.vy+=(Math.sin(now/900+b.ax)*8)*dt}
  for(let i=0;i<B.length;i++)for(let j=i+1;j<B.length;j++){const a=B[i],c=B[j];let dx=c.x-a.x,dy=c.y-a.y,d=Math.hypot(dx,dy)||1,min=a.r+c.r+10;if(d<min){const f=(min-d)*6*dt;dx/=d;dy/=d;a.vx-=dx*f;a.vy-=dy*f;c.vx+=dx*f;c.vy+=dy*f}}
  for(const b of B){b.vx*=Math.pow(.12,dt);b.vy*=Math.pow(.12,dt);b.x+=b.vx*dt*60/60*1;b.y+=b.vy*dt;b.x=Math.max(b.r+4,Math.min(W-b.r-4,b.x));b.y=Math.max(b.r+4,Math.min(H-b.r-18,b.y));b.el.style.transform=`translate(${b.x.toFixed(1)}px,${b.y.toFixed(1)}px)`}
  requestAnimationFrame(step)}requestAnimationFrame(step);
B.forEach(b=>{b.el.onclick=()=>{if(b.l.status==='soon'){b.vy-=120;return}select(b.l.key);b.vy-=90}});
/* ---------- the slate under the field ---------- */
function select(k){SEL=k;SUBSEL='';history.replaceState(null,'','#'+k);B.forEach(b=>b.el.classList.toggle('on',b.l.key===k));render()}
function gameRow(g){const line=g.odds?`<b>${g.odds}</b>`:'<b class="dim">—</b>';const ou=g.ou?`<span>O/U ${g.ou}</span>`:'';const tm=t=>`<img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'">${t.rank?`<span class="rk">#${t.rank}</span>`:''}<span>${t.abbr||t.name}</span><span class="rec">${t.rec}</span>`;
  return `<div class="g"><div class="t"><b>${fmtT(g.date)}</b>${g.tv||''}</div><div class="tm">${tm(g.away)}<span class="at">${g.neutral?'vs':'@'}</span>${tm(g.home)}</div><div class="ln">${line}${ou}</div>${g.note||g.venue?`<div class="sub">${g.note?`<em>${g.note}</em> · `:''}${g.venue}${g.sub?` · ${g.sub}`:''}</div>`:''}</div>`}
function render(){const l=all.find(x=>x.key===SEL)||all[0];let gs=(byLg[SEL]||[]).slice().sort((a,b)=>a.date.localeCompare(b.date));
  const subs=SEL==='soccer'?[...new Set(gs.map(g=>g.lg))]:[];if(SUBSEL)gs=gs.filter(g=>g.lg===SUBSEL);
  const days={};gs.forEach(g=>{(days[dayKey(g.date)]=days[dayKey(g.date)]||[]).push(g)});
  const withLines=gs.filter(g=>g.odds).length,teams=new Set();gs.forEach(g=>{teams.add(g.away.abbr);teams.add(g.home.abbr)});
  const big=gs.filter(g=>g.ou).sort((a,b)=>parseFloat(b.ou)-parseFloat(a.ou))[0];
  document.getElementById('slate').innerHTML=`<h2>${FULL[l.key]||l.label} <span>next 7 days · ${gs.length} games · Central time</span></h2>
   ${subs.length?`<div class="chips"><span class="chip ${SUBSEL?'':'on'}" data-s="">all</span>${subs.map(s=>`<span class="chip ${SUBSEL===s?'on':''}" data-s="${s}">${SUB[s]||s} <small>${(byLg.soccer||[]).filter(g=>g.lg===s).length}</small></span>`).join('')}</div>`:''}
   <div class="lead"><div class="card"><div class="k">${l.status==='live'?'full model online':'pipeline status'}</div><div class="v">${l.status==='live'?'LIVE':'SCHEDULE + LINES'}</div><div class="s">${l.status==='live'?'game logs · defense-vs-position · projections · markets · picks':'ESPN schedule and DraftKings lines are wired; game logs, DvP and projections follow the NFL framework'}</div><a class="open ${l.status==='live'?'':'dim'}" href="${l.page||'#'}">${l.status==='live'?'OPEN '+(FULL[l.key]||l.label).toUpperCase()+' DASHBOARD →':'OPEN '+(FULL[l.key]||l.label).toUpperCase()+' SHELL →'}</a></div>
   <div class="card"><div class="k">lines posted</div><div class="v">${withLines}<span style="color:var(--mute);font-size:14px"> / ${gs.length}</span></div><div class="s">${gs[0]?gs[0].book||'DraftKings':''} via ESPN · ${teams.size} teams on the slate</div></div>
   <div class="card"><div class="k">highest total</div><div class="v">${big?big.ou:'—'}</div><div class="s">${big?`${big.away.abbr} @ ${big.home.abbr} · ${dayKey(big.date)} ${fmtT(big.date)}`:'no totals posted yet'}</div></div></div>
   <div class="days" style="margin-top:12px">${Object.entries(days).map(([d,g])=>`<div class="day"><h3><span>${d}</span><span>${g.length}</span></h3>${g.map(gameRow).join('')}</div>`).join('')||'<div class="empty">nothing scheduled in the next seven days</div>'}</div>`;
  document.querySelectorAll('#slate .chip').forEach(c=>c.onclick=()=>{SUBSEL=c.dataset.s;render()});
  document.querySelectorAll('.lg a').forEach(a=>a.classList.toggle('on',a.dataset.k===SEL))}
render();
"""

def page(games, pulled):
    leagues = [dict(key=k, label=l, group=g, page=p, status=s, icon=i) for k, l, g, p, s, i in LEAGUES]
    J = dict(games=games, leagues=leagues, soccer=SOCCER, coming=COMING, icons=ICONS, pulled=pulled)
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · every sport, this week</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div id="hdr"><span class="brand"><i>◍</i> RAINMAN</span><span class="tag">matchup intelligence · every sport · pick a bubble</span><nav class="lg" style="display:flex;gap:4px;margin-left:10px">{''.join(f'<a data-k="{k}" href="{p}" style="font-family:var(--mono);font-size:11px;padding:4px 8px;border:1px solid var(--edge);border-radius:6px;color:var(--dim)">{l}</a>' for k, l, g, p, s, i in LEAGUES if s == 'live')}</nav><span class="right">slate pulled {pulled} · built {built}</span></div>
<div class="wrap">
<div id="field"></div>
<div id="slate"></div>
<div class="foot">Layer 0 · schedules, records, broadcast and DraftKings lines from ESPN's public scoreboard (pulled {pulled}). The NFL and College Football bubbles open the full RAINMAN model; the others open a schedule shell on the same framework until their game-log pipelines are connected.</div>
</div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script>
<script>{JS}</script></body></html>"""

SHELL_JS = r"""
const G=J.games;const logo=p=>p?'https://a.espncdn.com/i/teamlogos/'+p:'';
const TZD='America/Chicago';const fmtT=d=>new Date(d).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:TZD}).replace(':00',''),dayKey=d=>new Date(d).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:TZD});
let SUBSEL='';
function gameRow(g){const line=g.odds?`<b>${g.odds}</b>`:'<b class="dim">—</b>';const ou=g.ou?`<span>O/U ${g.ou}</span>`:'';const tm=t=>`<img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'">${t.rank?`<span class="rk">#${t.rank}</span>`:''}<span>${t.abbr||t.name}</span><span class="rec">${t.rec}</span>`;
  return `<div class="g"><div class="t"><b>${fmtT(g.date)}</b>${g.tv||''}</div><div class="tm">${tm(g.away)}<span class="at">${g.neutral?'vs':'@'}</span>${tm(g.home)}</div><div class="ln">${line}${ou}</div>${g.note||g.venue?`<div class="sub">${g.note?`<em>${g.note}</em> · `:''}${g.venue}${g.sub?` · ${g.sub}`:''}</div>`:''}</div>`}
function render(){let gs=G.slice().sort((a,b)=>a.date.localeCompare(b.date));const subs=[...new Set(gs.map(g=>g.lg))];if(SUBSEL)gs=gs.filter(g=>g.lg===SUBSEL);
  const days={};gs.forEach(g=>{(days[dayKey(g.date)]=days[dayKey(g.date)]||[]).push(g)});const teams={};gs.forEach(g=>{[g.away,g.home].forEach(t=>{if(t.abbr!=='TBD')teams[t.abbr+'|'+g.lg]=t})});
  document.getElementById('out').innerHTML=`${subs.length>1?`<div class="chips"><span class="chip ${SUBSEL?'':'on'}" data-s="">all</span>${subs.map(s=>`<span class="chip ${SUBSEL===s?'on':''}" data-s="${s}">${J.soccer[s]||s}</span>`).join('')}</div>`:''}
   <h2>this week <span>${gs.length} games · Central time</span></h2><div class="days">${Object.entries(days).map(([d,g])=>`<div class="day"><h3><span>${d}</span><span>${g.length}</span></h3>${g.map(gameRow).join('')}</div>`).join('')||'<div class="empty">nothing scheduled</div>'}</div>
   <h2>teams on the slate <span>${Object.keys(teams).length}</span></h2><div class="teams">${Object.values(teams).sort((a,b)=>a.name.localeCompare(b.name)).map(t=>`<div class="team"><img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'"><div>${t.name}<small>${t.abbr} · ${t.rec||'—'}</small></div></div>`).join('')}</div>`;
  document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{SUBSEL=c.dataset.s;render()})}
render();
"""

def shell(key, label, games, pulled):
    J = dict(games=games, soccer=SOCCER)
    tabs = ['Home', 'Matchups', 'Players', 'Intel', 'Picks']
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · {label}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}
#tnav{{display:flex;gap:2px;margin-left:14px}}#tnav span{{font-family:var(--mono);font-size:11px;padding:6px 10px;border-bottom:2px solid transparent;color:var(--mute)}}#tnav span.on{{color:var(--fg);border-color:var(--acc)}}
.pipe{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:10px}}.pipe .card{{background:var(--panel);border:1px solid var(--edge);border-radius:10px;padding:12px 14px}}.pipe .ok{{color:var(--green)}}.pipe .todo{{color:var(--mute)}}
</style></head><body>
<div id="hdr"><a class="brand" href="index.html"><i>◍</i> RAINMAN</a><span class="tag" style="font-family:var(--mono);color:var(--acc)">{label}</span><nav id="tnav">{''.join(f'<span class="{"on" if t == "Home" else ""}">{t}</span>' for t in tabs)}</nav><span class="right"><a href="index.html">← all sports</a> · slate pulled {pulled}</span></div>
<div class="wrap">
<h2>Layer 1 · {label} <span>schedule shell on the RAINMAN framework — the five tabs light up as each pipeline connects</span></h2>
<div class="pipe">
 <div class="card"><div class="k">schedule + broadcast</div><div class="v ok">ON</div><div class="s">ESPN scoreboard, 7-day window</div></div>
 <div class="card"><div class="k">game lines</div><div class="v ok">ON</div><div class="s">DraftKings via ESPN (spread / ML, total)</div></div>
 <div class="card"><div class="k">team logos + colors</div><div class="v ok">ON</div><div class="s">ESPN CDN</div></div>
 <div class="card"><div class="k">game logs</div><div class="v todo">NEXT</div><div class="s">per-player box scores → the atomic table</div></div>
 <div class="card"><div class="k">defense vs position</div><div class="v todo">NEXT</div><div class="s">stats allowed per slot, ranks, trends</div></div>
 <div class="card"><div class="k">projections · markets · picks</div><div class="v todo">NEXT</div><div class="s">same model as NFL once logs exist</div></div>
</div>
<div id="out"></div>
<div class="foot">Every row here comes from data/raw/slate_all_*.txt (ESPN). Nothing is hand-typed.</div></div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script><script>{SHELL_JS}</script></body></html>"""

def main():
    games, pulled = load_slate()
    os.makedirs('dashboard', exist_ok=True)
    open('dashboard/index.html', 'w', encoding='utf-8').write(page(games, pulled))
    n = {}
    for k, l, g, p, s, i in LEAGUES:
        if s != 'shell': continue
        gs = [x for x in games if x['sport'] == k]
        open('dashboard/' + p, 'w', encoding='utf-8').write(shell(k, l, gs, pulled)); n[p] = len(gs)
    print(f"dashboard/index.html: {len(games)} games across {len(set(g['lg'] for g in games))} leagues (pulled {pulled}) · shells {n}")

if __name__ == '__main__':
    main()
