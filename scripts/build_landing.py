"""Layer 0 — the multi-sport landing page -> dashboard/index.html, plus Layer-1 shells for the sports that have no data
pipeline yet (nba.html, ncaab.html, wnba.html, mlb.html, nhl.html, soccer.html) from the same slate file.

Usage: python3 scripts/build_landing.py
Input : data/raw/slate_all_YYYY-MM-DD.txt (latest; ESPN scoreboard pulls, see notes/scrape_recipe.md "multi-sport slate")
Every number on the page comes from that file; nothing is typed in by hand. NFL -> rainman.html, CFB -> ncaa.html.
"""
import os, glob, json, re
from datetime import datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
CDN = 'https://a.espncdn.com/i/'
NCAA_LOGO = 'https://upload.wikimedia.org/wikipedia/commons/d/dd/NCAA_logo.svg'
LEAGUES = [  # key, label, sport group, page, status, logo (real league marks: ESPN CDN dark variants; NCAA mark for the college sports)
    ('nfl', 'NFL', 'football', 'rainman.html', 'live', CDN + 'teamlogos/leagues/500-dark/nfl.png'),
    ('cfb', 'College Football', 'football', 'ncaa.html', 'live', NCAA_LOGO),
    ('nba', 'NBA', 'basketball', 'nba.html', 'shell', CDN + 'teamlogos/leagues/500-dark/nba.png'),
    ('ncaab', 'College Basketball', 'basketball', 'ncaab.html', 'shell', NCAA_LOGO),
    ('wnba', 'WNBA', 'basketball', 'wnba.html', 'shell', CDN + 'teamlogos/leagues/500-dark/wnba.png'),
    ('mlb', 'MLB', 'baseball', 'mlb.html', 'shell', CDN + 'teamlogos/leagues/500-dark/mlb.png'),
    ('nhl', 'NHL', 'hockey', 'nhl.html', 'shell', CDN + 'teamlogos/leagues/500-dark/nhl.png'),
    ('soccer', 'Soccer', 'soccer', 'soccer.html', 'shell', CDN + 'leaguelogos/soccer/500-dark/2.png')]
SOCCER = {'epl': 'Premier League', 'mls': 'MLS', 'ucl': 'Champions League', 'laliga': 'La Liga', 'bund': 'Bundesliga', 'seriea': 'Serie A', 'ligue1': 'Ligue 1'}
SOCCER_LOGO = {'epl': 23, 'mls': 19, 'ucl': 2, 'laliga': 15, 'bund': 10, 'seriea': 12, 'ligue1': 9}
SOCCER_LOGO = {k: CDN + f'leaguelogos/soccer/500-dark/{v}.png' for k, v in SOCCER_LOGO.items()}
COMING = [('f1', 'Formula 1', CDN + 'teamlogos/leagues/500-dark/f1.png'), ('ufc', 'UFC', CDN + 'teamlogos/leagues/500/ufc.png')]

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
a{color:inherit;text-decoration:none}img{-webkit-user-drag:none}
#hdr{display:flex;align-items:center;gap:18px;padding:12px 22px;border-bottom:1px solid var(--edge);background:#050506;position:sticky;top:0;z-index:5}
#hdr .brand{font-family:var(--mono);font-weight:700;letter-spacing:.22em;font-size:15px}#hdr .brand i{color:var(--acc);font-style:normal}
#hdr .tag{color:var(--dim);font-size:12px}#hdr .right{margin-left:auto;font-family:var(--mono);color:var(--dim);font-size:11px}
#hdr .hl{display:flex;gap:4px}#hdr .hl a{font-family:var(--mono);font-size:11px;padding:4px 9px;border:1px solid var(--edge2);border-radius:6px;color:var(--dim)}#hdr .hl a:hover{color:var(--fg);border-color:#4a4b52}
#tnav{display:flex;gap:2px;margin-left:14px}#tnav span{font-family:var(--mono);font-size:11px;padding:6px 10px;border-bottom:2px solid transparent;color:var(--mute)}#tnav span.on{color:var(--fg);border-color:var(--acc)}
.wrap{max-width:1560px;margin:0 auto;padding:16px 22px 60px}
h2{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim);margin:24px 0 10px;font-weight:600;display:flex;align-items:baseline;gap:10px}h2 span{color:var(--mute);text-transform:none;letter-spacing:0;font-weight:400}
.mono{font-family:var(--mono)}.dim{color:var(--dim)}.mute{color:var(--mute)}
/* league rail */
.rail{display:grid;grid-template-columns:repeat(10,1fr);gap:8px}
.lg{position:relative;display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 8px 10px;border:1px solid var(--edge2);border-radius:10px;background:linear-gradient(180deg,#141416,#0b0b0c);cursor:pointer;text-align:center;min-width:0}
.lg:hover{border-color:#4a4b52}.lg.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc) inset}
.lg img{height:54px;width:auto;max-width:100%;object-fit:contain}.lg b{font-size:12px;letter-spacing:.02em;line-height:1.2;max-width:100%}
.lg small{font-family:var(--mono);font-size:10px;color:var(--dim)}.lg .st{font-family:var(--mono);font-size:9px;letter-spacing:.1em;padding:2px 7px;border-radius:9px;border:1px solid var(--edge2);color:var(--dim)}
.lg.live .st{background:#2b2309;border-color:#6b5415;color:var(--acc)}.lg.soon{opacity:.45;cursor:default}
.subrail{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.sub{display:flex;align-items:center;gap:7px;padding:5px 10px 5px 6px;border:1px solid var(--edge2);border-radius:8px;background:var(--panel);cursor:pointer;font-size:12px}
.sub img{height:22px;width:auto}.sub small{font-family:var(--mono);font-size:10px;color:var(--dim)}.sub.on{border-color:var(--acc)}.sub:hover:not(.on){border-color:#4a4b52}
/* calendar strip */
.cal{display:grid;grid-template-columns:repeat(8,1fr);gap:6px}
.cd{padding:8px 10px;border:1px solid var(--edge);border-radius:8px;background:var(--panel);cursor:pointer;min-width:0}.cd:hover{border-color:#4a4b52}.cd.on{border-color:var(--acc)}.cd.isToday .d{color:var(--acc)}
.cd .d{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);display:flex;justify-content:space-between}.cd .d b{color:var(--fg);font-size:14px}
.cd .lgs{display:flex;flex-wrap:wrap;gap:3px;margin-top:6px;align-items:center}.cd .lgs img{height:14px;width:auto;max-width:34px;object-fit:contain;opacity:.9}.cd .lgs i{font-style:normal;font-family:var(--mono);font-size:9px;color:var(--mute);margin-right:4px}
/* today strip */
.today{display:grid;grid-template-columns:repeat(auto-fill,minmax(228px,1fr));gap:6px}
.tg{display:grid;grid-template-columns:22px 1fr auto;gap:8px;align-items:center;padding:6px 8px;border:1px solid var(--edge);border-radius:8px;background:var(--panel);font-size:12px;cursor:pointer}
.tg:hover{border-color:#4a4b52}.tg>img{height:18px;width:22px;object-fit:contain}.tg .tt{display:flex;align-items:center;gap:4px;min-width:0}.tg .tt img{width:18px;height:18px;object-fit:contain}.tg .tt b{font-family:var(--mono);font-size:11px}
.tg .tt .at{color:var(--mute);margin:0 2px}.tg .tr{text-align:right;font-family:var(--mono);font-size:10px;color:var(--dim);white-space:nowrap}.tg .tr b{display:block;color:var(--fg);font-size:11px}
/* hero + marquee */
.herow{display:grid;grid-template-columns:1.15fr 1fr;gap:10px;margin-top:12px}
.hero{display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center;padding:16px 20px;border:1px solid var(--edge2);border-radius:12px;background:linear-gradient(135deg,#17171a,#0a0a0b 60%)}
.hero img{height:84px;width:auto;max-width:150px;object-fit:contain}.hero h1{margin:0;font-size:22px;letter-spacing:.02em;display:flex;align-items:center;gap:12px}.hero .hs{display:grid;grid-template-columns:repeat(3,1fr);gap:12px 18px;margin-top:10px}
.hs .k{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}.hs .v{font-family:var(--mono);font-size:19px;font-weight:700;margin-top:2px;white-space:nowrap}.hs .s{color:var(--dim);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.open{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border:1px solid var(--acc);border-radius:8px;color:var(--acc);font-family:var(--mono);font-size:11px;letter-spacing:.08em;white-space:nowrap}
.open:hover{background:var(--acc);color:#000}.open.dim{border-color:var(--edge2);color:var(--dim)}
.mq{border:1px solid var(--edge2);border-radius:12px;padding:14px 18px;justify-content:space-between;background:linear-gradient(135deg,color-mix(in srgb,var(--ca) 16%,#0b0b0c),#0a0a0b 50%,color-mix(in srgb,var(--ch) 16%,#0b0b0c));display:flex;flex-direction:column;gap:8px}
.mq .k{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);display:flex;justify-content:space-between}.mq .k b{color:var(--acc);letter-spacing:.08em}
.mq .vs{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px}.mq .side{display:flex;align-items:center;gap:12px;min-width:0}.mq .side.r{flex-direction:row-reverse;text-align:right}
.mq .side img{width:64px;height:64px;object-fit:contain;flex:none}.mq .side .nm{font-size:17px;font-weight:600;line-height:1.15}.mq .side .rc{font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:2px}.mq .side .rk{color:var(--acc)}
.mq .at{font-family:var(--mono);font-size:12px;color:var(--mute);text-align:center}.mq .at b{display:block;color:var(--fg);font-size:18px}
.mq .ln{display:flex;gap:18px;flex-wrap:wrap;font-family:var(--mono);font-size:11px;color:var(--dim);border-top:1px solid var(--edge);padding-top:8px}.mq .ln b{color:var(--fg)}
/* filters */
.filt{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:12px 0 0}.chip{font-family:var(--mono);font-size:11px;padding:4px 10px;border:1px solid var(--edge2);border-radius:14px;color:var(--dim);cursor:pointer;background:var(--panel)}
.chip.on{color:#000;background:var(--acc);border-color:var(--acc)}.chip:hover:not(.on){color:var(--fg);border-color:#4a4b52}.filt input{background:var(--panel);border:1px solid var(--edge2);color:var(--fg);border-radius:14px;padding:4px 10px;font-family:var(--mono);font-size:11px;width:170px}
.filt .sp{margin-left:auto;font-family:var(--mono);font-size:10px;color:var(--mute)}
/* the week */
.days{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:10px}
.day{background:var(--panel);border:1px solid var(--edge);border-radius:10px;overflow:hidden}.day.isToday{border-color:#6b5415}.day h3{margin:0;padding:8px 12px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);border-bottom:1px solid var(--edge);background:var(--s2);display:flex;justify-content:space-between}.day.isToday h3{color:var(--acc)}
.g{display:grid;grid-template-columns:66px 1fr auto;gap:10px;padding:9px 12px;border-bottom:1px solid var(--edge);align-items:center}.g:last-child{border-bottom:0}.g.hi{background:linear-gradient(90deg,rgba(232,179,57,.06),transparent)}
.g .t{font-family:var(--mono);font-size:10px;color:var(--dim);line-height:1.3}.g .t b{display:block;color:var(--fg);font-size:12px}
.g .tm{display:flex;flex-direction:column;gap:3px;min-width:0}.g .row{display:flex;align-items:center;gap:7px;font-size:13px;min-width:0}.g .row img{width:24px;height:24px;object-fit:contain;flex:none}.g .row .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.g .row .rec{font-family:var(--mono);color:var(--mute);font-size:10px;flex:none}.g .row .rk{font-family:var(--mono);color:var(--acc);font-size:10px;flex:none}.g .row .imp{font-family:var(--mono);color:var(--dim);font-size:10px;flex:none;margin-left:auto}
.g .ln{text-align:right;font-family:var(--mono);font-size:11px;white-space:nowrap}.g .ln b{color:var(--fg);display:block;font-size:12px}.g .ln span{display:block;color:var(--dim);font-size:10px}
.g .vn{grid-column:1/-1;color:var(--mute);font-size:10px;margin-top:-4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.g .vn em{color:var(--blue);font-style:normal}
.empty{color:var(--dim);padding:20px;border:1px dashed var(--edge2);border-radius:10px;text-align:center}
/* lines board */
table.lb{width:100%;border-collapse:collapse;font-size:12px}.lb th{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--dim);text-align:left;padding:6px 8px;border-bottom:1px solid var(--edge2);cursor:pointer;white-space:nowrap}.lb th.r,.lb td.r{text-align:right}
.lb td{padding:6px 8px;border-bottom:1px solid var(--edge);white-space:nowrap}.lb tr:hover td{background:var(--s2)}.lb td.mono,.lb td.r{font-family:var(--mono)}.lb .tc{display:inline-flex;align-items:center;gap:5px}.lb .tc img{width:18px;height:18px;object-fit:contain}.lb .fav{color:var(--fg);font-weight:600}
.lb .bar{display:inline-block;height:6px;border-radius:3px;background:var(--acc);vertical-align:middle;margin-left:6px;opacity:.7}
/* teams */
.teams{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}.team{display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--panel);border:1px solid var(--edge);border-radius:8px;font-size:12px;cursor:pointer}.team:hover,.team.on{border-color:var(--acc)}
.team img{width:26px;height:26px;object-fit:contain}.team small{display:block;color:var(--dim);font-family:var(--mono);font-size:10px}
.pipe{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:10px}.pipe .card{background:var(--panel);border:1px solid var(--edge);border-radius:10px;padding:12px 14px}.card .k{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}.card .v{font-family:var(--mono);font-size:20px;font-weight:700;margin:4px 0 2px}.card .s{color:var(--dim);font-size:11px}.pipe .ok{color:var(--green)}.pipe .todo{color:var(--mute)}
.foot{margin-top:40px;color:var(--mute);font-size:11px;font-family:var(--mono);border-top:1px solid var(--edge);padding-top:12px}
@media(max-width:1100px){.rail{grid-template-columns:repeat(5,1fr)}.herow{grid-template-columns:1fr}.cal{grid-template-columns:repeat(4,1fr)}}@media(max-width:700px){.rail{grid-template-columns:repeat(3,1fr)}.hero{grid-template-columns:1fr}.hero .hs{grid-template-columns:1fr 1fr}.wrap{padding:12px 14px 40px}.lg img{height:40px}.cal{grid-template-columns:repeat(2,1fr)}}
"""

JS = r"""
const G=J.games,LG=J.leagues,SUB=J.soccer,SUBLOGO=J.soccerLogo,TZD='America/Chicago',SHELL=!!J.shell;
const logo=p=>p?'https://a.espncdn.com/i/teamlogos/'+p:'';
const fmtT=d=>new Date(d).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:TZD}).replace(':00','');
const dayKey=d=>new Date(d).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:TZD});
const TODAY=dayKey(new Date().toISOString());const LGBY=Object.fromEntries(LG.map(l=>[l.key,l]));
const byLg={};G.forEach(g=>{(byLg[g.sport]=byLg[g.sport]||[]).push(g)});
const DAYS=[...new Set(G.slice().sort((a,b)=>a.date.localeCompare(b.date)).map(g=>dayKey(g.date)))];
let SEL=SHELL?LG[0].key:(location.hash.replace('#','')||'nfl'),SUBSEL='',DAYSEL='',Q='',TEAM='';if(!LGBY[SEL])SEL=LG[0].key;
const lgLogo=g=>g.sport==='soccer'?SUBLOGO[g.lg]:LGBY[g.sport].logo;
const isSoccer=g=>g.sport==='soccer';
/* odds helpers: "DAL -8.5" = spread (favorite + points); soccer / MLB / NHL odds are moneylines ("ARS -265") */
const parseOdds=g=>{if(!g.odds)return null;const m=g.odds.match(/^(\S+)\s+([+-]?\d+(?:\.\d+)?)$/);if(!m)return {raw:g.odds};const n=parseFloat(m[2]);const ml=Math.abs(n)>=100;return {team:m[1],n,ml,fav:m[1]===g.home.abbr?'home':'away'}};
const implied=g=>{const o=parseOdds(g);if(!o||o.ml||o.raw||!g.ou)return null;const tot=parseFloat(g.ou),sp=Math.abs(o.n);const favPts=(tot+sp)/2,dogPts=tot-favPts;return o.fav==='home'?{away:dogPts,home:favPts}:{away:favPts,home:dogPts}};
const lineTxt=g=>{const o=parseOdds(g);if(!o)return '';if(o.raw)return o.raw;return o.ml?`ML ${o.team} ${o.n>0?'+':''}${o.n}`:`${o.team} ${o.n>0?'+':''}${o.n}`};
/* ---------- league rail (Layer 0 only) ---------- */
const rail=document.getElementById('rail');
if(rail){rail.innerHTML=LG.map(l=>{const n=(byLg[l.key]||[]).length;return `<div class="lg ${l.status}${l.key===SEL?' on':''}" data-k="${l.key}"><img src="${l.logo}" alt=""><b>${l.label}</b><small>${n} games · 7 days</small><span class="st">${l.status==='live'?'LIVE MODEL':'SCHEDULE'}</span></div>`}).join('')
   +(J.coming||[]).map(c=>`<div class="lg soon"><img src="${c[2]}" alt=""><b>${c[1]}</b><small>coming soon</small><span class="st">SOON</span></div>`).join('');
  rail.querySelectorAll('.lg[data-k]').forEach(el=>el.onclick=()=>select(el.dataset.k))}
function select(k){SEL=k;SUBSEL='';DAYSEL='';TEAM='';Q='';history.replaceState(null,'','#'+k);if(rail)rail.querySelectorAll('.lg').forEach(e=>e.classList.toggle('on',e.dataset.k===k));render();const h=document.getElementById('herow');if(h&&!SHELL)h.scrollIntoView({block:'start'})}
/* ---------- calendar strip: every day, every league ---------- */
(function(){const el=document.getElementById('cal');if(!el)return;
  el.innerHTML=DAYS.map(d=>{const gs=G.filter(g=>dayKey(g.date)===d);const by={};gs.forEach(g=>{const k=g.sport==='soccer'?g.lg:g.sport;(by[k]=by[k]||[]).push(g)});
    return `<div class="cd${d===TODAY?' isToday':''}" data-d="${d}"><div class="d"><span>${d}${d===TODAY?' · today':''}</span><b>${gs.length}</b></div><div class="lgs">${Object.entries(by).sort((a,b)=>b[1].length-a[1].length).map(([k,v])=>`<img src="${SUB[k]?SUBLOGO[k]:LGBY[k].logo}" title="${SUB[k]||LGBY[k].label}: ${v.length}" alt=""><i>${v.length}</i>`).join('')}</div></div>`}).join('');
  el.querySelectorAll('.cd').forEach(c=>c.onclick=()=>{DAYSEL=DAYSEL===c.dataset.d?'':c.dataset.d;render()})})();
/* ---------- today, every league ---------- */
(function(){const el=document.getElementById('today');if(!el)return;const t=G.filter(g=>dayKey(g.date)===TODAY).sort((a,b)=>a.date.localeCompare(b.date));
  document.getElementById('todayH').innerHTML=`today · ${TODAY} <span>${t.length} games across ${new Set(t.map(g=>g.lg)).size} leagues · Central time</span>`;
  el.innerHTML=t.map(g=>`<div class="tg" data-k="${g.sport}"><img src="${lgLogo(g)}" alt=""><div class="tt"><img src="${logo(g.away.logo)}" alt="" onerror="this.style.visibility='hidden'"><b>${g.away.abbr}</b><span class="at">${g.neutral?'vs':'@'}</span><img src="${logo(g.home.logo)}" alt="" onerror="this.style.visibility='hidden'"><b>${g.home.abbr}</b></div><div class="tr"><b>${fmtT(g.date)}</b>${lineTxt(g)||g.tv||''}</div></div>`).join('')||'<div class="empty">nothing today — the next slate starts '+(DAYS[0]||'')+'</div>';
  el.querySelectorAll('.tg').forEach(x=>x.onclick=()=>select(x.dataset.k))})();
/* ---------- rows ---------- */
function gameRow(g,hi){const o=parseOdds(g),im=implied(g);const line=o?`<b>${lineTxt(g)}</b>`:'<b class="dim">no line</b>';const ou=g.ou?`<span>O/U ${g.ou}</span>`:'';
  const row=(t,side)=>`<div class="row"><img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'">${t.rank?`<span class="rk">#${t.rank}</span>`:''}<span class="nm">${t.name}</span><span class="rec">${t.rec}</span>${im?`<span class="imp" title="implied team total from the spread and total">${im[side].toFixed(1)}</span>`:''}</div>`;
  return `<div class="g${hi?' hi':''}"><div class="t"><b>${fmtT(g.date)}</b>${g.tv||''}</div><div class="tm">${row(g.away,'away')}${row(g.home,'home')}</div><div class="ln">${line}${ou}</div>${g.note||g.venue?`<div class="vn">${g.note?`<em>${g.note}</em> · `:''}${g.venue}${g.sub?` · ${g.sub}`:''}${g.neutral?' · neutral site':''}</div>`:''}</div>`}
function marquee(gs){if(!gs.length)return '';const ranked=gs.filter(g=>g.away.rank&&g.home.rank).sort((a,b)=>(+a.away.rank+ +a.home.rank)-(+b.away.rank+ +b.home.rank));
  const score=g=>{const o=parseOdds(g);const close=o&&!o.ml&&!o.raw?Math.max(0,10-Math.abs(o.n)):0;const tot=g.ou?parseFloat(g.ou):0;const rk=(g.away.rank?1:0)+(g.home.rank?1:0);return rk*40+close*2+(g.tv&&/ABC|NBC|CBS|Fox|ESPN\b|Prime|Peacock/.test(g.tv)?8:0)+(g.note?10:0)+tot/10};
  const g=ranked[0]||gs.slice().sort((a,b)=>score(b)-score(a))[0];const o=parseOdds(g),im=implied(g);
  const side=(t,cls,sd)=>`<div class="side ${cls}"><img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'"><div><div class="nm">${t.rank?`<span class="rk">#${t.rank} </span>`:''}${t.name}</div><div class="rc">${t.rec}${im?` · implied ${im[sd].toFixed(1)}`:''}</div></div></div>`;
  const why=[];if(g.away.rank&&g.home.rank)why.push(`#${g.away.rank} vs #${g.home.rank}`);const tots=gs.filter(x=>x.ou).map(x=>parseFloat(x.ou));if(g.ou&&parseFloat(g.ou)>=Math.max(...tots))why.push('highest total on the slate');
  const sps=gs.map(parseOdds).filter(x=>x&&!x.ml&&!x.raw).map(x=>Math.abs(x.n));if(o&&!o.ml&&!o.raw&&Math.abs(o.n)<=Math.min(...sps))why.push('tightest line');if(g.note)why.push(g.note);if(g.tv&&/ABC|NBC|CBS|Fox|ESPN\b|Prime|Peacock/.test(g.tv))why.push('national TV');
  const recs=[g.away,g.home].map(t=>t.rec).filter(Boolean);
  return `<div class="mq" style="--ca:#2a2b30;--ch:#2a2b30"><div class="k"><span>marquee · ${ranked[0]?'highest ranked matchup':'the game of the week'}</span><b>${dayKey(g.date)} · ${fmtT(g.date)} CT</b></div>
    <div class="ln" style="border:0;padding:0">${why.map(w=>`<span class="chip on" style="cursor:default">${w}</span>`).join('')}</div>
    <div class="vs">${side(g.away,'','away')}<div class="at">${g.neutral?'vs':'@'}<b>${o?lineTxt(g):'—'}</b></div>${side(g.home,'r','home')}</div>
    <div class="ln">${g.ou?`<span>O/U <b>${g.ou}</b></span>`:''}${g.tv?`<span>TV <b>${g.tv}</b></span>`:''}<span>${g.venue||''}${g.neutral?' (neutral)':''}</span>${g.note?`<span style="color:var(--blue)">${g.note}</span>`:''}${g.sub?`<span>${g.sub}</span>`:''}</div></div>`}
let SORT='date',SORTA=true;
function linesBoard(gs){const rows=gs.filter(g=>g.odds||g.ou);if(!rows.length)return '';const key={date:g=>g.date,away:g=>g.away.name,tv:g=>g.tv||'~',spread:g=>{const o=parseOdds(g);return o&&!o.ml&&!o.raw?Math.abs(o.n):o&&o.ml?Math.abs(o.n)/100:99},total:g=>g.ou?parseFloat(g.ou):-1,fav:g=>parseOdds(g)?.team||'~',implied:g=>{const im=implied(g);return im?Math.max(im.away,im.home):-1}};
  const R=rows.slice().sort((a,b)=>{const x=key[SORT](a),y=key[SORT](b);const c=x<y?-1:x>y?1:0;return SORTA?c:-c});const maxSp=Math.max(...R.map(g=>{const o=parseOdds(g);return o&&!o.ml&&!o.raw?Math.abs(o.n):0}),1);
  const tc=t=>`<span class="tc"><img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'">${t.rank?`<span class="rk" style="color:var(--acc)">#${t.rank}</span>`:''}${t.abbr}</span>`;
  return `<table class="lb"><thead><tr><th data-s="date">kick (CT)</th><th data-s="away">matchup</th><th data-s="tv">tv</th><th data-s="fav">favorite · line</th><th data-s="spread" class="r">margin</th><th data-s="total" class="r">total</th><th data-s="implied" class="r">implied</th></tr></thead><tbody>
   ${R.map(g=>{const o=parseOdds(g),im=implied(g);const sp=o&&!o.ml&&!o.raw?Math.abs(o.n):null;return `<tr><td class="mono">${dayKey(g.date).replace(/,.*$/,'')} ${fmtT(g.date)}</td><td>${tc(g.away)} <span class="mute">${g.neutral?'vs':'@'}</span> ${tc(g.home)}</td><td class="mute">${g.tv||''}</td><td class="mono">${o?`<span class="fav">${lineTxt(g)}</span>`:'<span class="mute">—</span>'}</td><td class="r">${sp!=null?`${sp}<span class="bar" style="width:${(sp/maxSp*60).toFixed(0)}px"></span>`:o&&o.ml?`<span class="mute">ML</span>`:''}</td><td class="r">${g.ou||'<span class="mute">—</span>'}</td><td class="r mute">${im?`${im.away.toFixed(1)} · ${im.home.toFixed(1)}`:''}</td></tr>`}).join('')}</tbody></table>`}
function render(){const l=LGBY[SEL];let all=(byLg[SEL]||[]).slice().sort((a,b)=>a.date.localeCompare(b.date));
  const subs=SEL==='soccer'?[...new Set(all.map(g=>g.lg))]:[];if(SUBSEL)all=all.filter(g=>g.lg===SUBSEL);
  const teams={};all.forEach(g=>{[g.away,g.home].forEach(t=>{if(t.abbr!=='TBD')teams[t.abbr]=t})});
  let gs=all;if(DAYSEL)gs=gs.filter(g=>dayKey(g.date)===DAYSEL);if(TEAM)gs=gs.filter(g=>g.away.abbr===TEAM||g.home.abbr===TEAM);if(Q)gs=gs.filter(g=>(g.away.name+' '+g.home.name+' '+g.away.abbr+' '+g.home.abbr+' '+(g.tv||'')+' '+(g.venue||'')).toLowerCase().includes(Q));
  const days={};gs.forEach(g=>{(days[dayKey(g.date)]=days[dayKey(g.date)]||[]).push(g)});
  const withLines=all.filter(g=>g.odds).length;const big=all.filter(g=>g.ou).sort((a,b)=>parseFloat(b.ou)-parseFloat(a.ou))[0];
  const sp=all.map(g=>({g,o:parseOdds(g)})).filter(x=>x.o&&!x.o.ml&&!x.o.raw);const close=sp.slice().sort((a,b)=>Math.abs(a.o.n)-Math.abs(b.o.n))[0];const wide=sp.slice().sort((a,b)=>Math.abs(b.o.n)-Math.abs(a.o.n))[0];
  const ranked=all.filter(g=>g.away.rank||g.home.rank).length;const title=SUBSEL?SUB[SUBSEL]:l.label;const heroLogo=SUBSEL?SUBLOGO[SUBSEL]:l.logo;
  const hero=document.getElementById('hero');if(hero)hero.innerHTML=`<img src="${heroLogo}" alt=""><div><h1>${title}${l.status==='live'?`<a class="open" href="${l.page}">OPEN ${l.label.toUpperCase()} →</a>`:`<a class="open dim" href="${l.page}">SCHEDULE SHELL →</a>`}</h1><div class="hs">
    <div><div class="k">next 7 days</div><div class="v">${all.length}</div><div class="s">games · ${Object.keys(teams).length} teams${ranked?` · ${ranked} with a ranked team`:''}</div></div>
    <div><div class="k">lines posted</div><div class="v">${withLines}<span class="mute" style="font-size:12px"> / ${all.length}</span></div><div class="s">${all[0]&&all[0].book?all[0].book:'DraftKings'} via ESPN</div></div>
    <div><div class="k">highest total</div><div class="v">${big?big.ou:'—'}</div><div class="s">${big?`${big.away.abbr} @ ${big.home.abbr} · ${dayKey(big.date)}`:''}</div></div>
    <div><div class="k">tightest line</div><div class="v">${close?lineTxt(close.g):'—'}</div><div class="s">${close?`${close.g.away.abbr} @ ${close.g.home.abbr}`:''}</div></div>
    <div><div class="k">biggest favorite</div><div class="v">${wide?lineTxt(wide.g):'—'}</div><div class="s">${wide?`${wide.g.away.abbr} @ ${wide.g.home.abbr}`:''}</div></div>
    <div><div class="k">model</div><div class="v" style="color:${l.status==='live'?'var(--acc)':'var(--dim)'}">${l.status==='live'?'LIVE':'SCHEDULE'}</div><div class="s">${l.status==='live'?'game logs · DvP · projections · markets · picks':'logs, DvP, projections follow the NFL framework'}</div></div></div></div>`;
  const mq=document.getElementById('marquee');if(mq)mq.innerHTML=marquee(all);
  const sr=document.getElementById('subrail');if(sr){sr.innerHTML=subs.length?`<div class="sub ${SUBSEL?'':'on'}" data-s=""><small>all leagues</small></div>`+subs.map(s=>`<div class="sub ${SUBSEL===s?'on':''}" data-s="${s}"><img src="${SUBLOGO[s]}" alt="">${SUB[s]||s}<small>${(byLg.soccer||[]).filter(g=>g.lg===s).length}</small></div>`).join(''):'';
    sr.querySelectorAll('.sub').forEach(c=>c.onclick=()=>{SUBSEL=c.dataset.s;render()})}
  const dl=[...new Set(all.map(g=>dayKey(g.date)))];
  document.getElementById('filt').innerHTML=`<span class="chip ${DAYSEL?'':'on'}" data-d="">every day</span>${dl.map(d=>`<span class="chip ${DAYSEL===d?'on':''}" data-d="${d}">${d.replace(/,.*$/,'')} <small>${all.filter(g=>dayKey(g.date)===d).length}</small></span>`).join('')}<input id="q" placeholder="team · tv · venue" value="${Q}">${TEAM?`<span class="chip on" data-t="">${TEAM} ×</span>`:''}<span class="sp">${gs.length} of ${all.length} games</span>`;
  document.querySelectorAll('#filt .chip[data-d]').forEach(c=>c.onclick=()=>{DAYSEL=c.dataset.d;render()});document.querySelectorAll('#filt .chip[data-t]').forEach(c=>c.onclick=()=>{TEAM='';render()});
  const q=document.getElementById('q');q.oninput=()=>{Q=q.value.trim().toLowerCase();render();const n=document.getElementById('q');n.focus();n.setSelectionRange(n.value.length,n.value.length)};
  document.getElementById('weekH').innerHTML=`${title} · the week <span>${gs.length} games · Central time · implied team totals beside the records</span>`;
  document.getElementById('week').innerHTML=Object.entries(days).map(([d,g])=>`<div class="day${d===TODAY?' isToday':''}"><h3><span>${d}${d===TODAY?' · today':''}</span><span>${g.length}</span></h3>${g.map(x=>gameRow(x,x.away.rank&&x.home.rank)).join('')}</div>`).join('')||'<div class="empty">nothing scheduled for this filter</div>';
  document.getElementById('linesH').innerHTML=`lines board <span>${withLines} lines · click a header to sort · margin bar = spread size</span>`;document.getElementById('lines').innerHTML=linesBoard(all);
  document.querySelectorAll('#lines th[data-s]').forEach(th=>{if(th.dataset.s===SORT)th.textContent+=SORTA?' ▲':' ▼';th.onclick=()=>{if(SORT===th.dataset.s)SORTA=!SORTA;else{SORT=th.dataset.s;SORTA=th.dataset.s!=='total'}render()}});
  document.getElementById('teamsH').innerHTML=`teams on the slate <span>${Object.keys(teams).length} · click to filter the week</span>`;
  document.getElementById('teams').innerHTML=Object.values(teams).sort((a,b)=>a.name.localeCompare(b.name)).map(t=>`<div class="team${TEAM===t.abbr?' on':''}" data-t="${t.abbr}"><img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'"><div>${t.name}<small>${t.abbr}${t.rec?' · '+t.rec:''}${t.rank?' · #'+t.rank:''}</small></div></div>`).join('');
  document.querySelectorAll('#teams .team').forEach(x=>x.onclick=()=>{TEAM=TEAM===x.dataset.t?'':x.dataset.t;render()})}
render();
"""

HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">"""

def page(games, pulled):
    leagues = [dict(key=k, label=l, group=g, page=p, status=s, logo=i) for k, l, g, p, s, i in LEAGUES]
    J = dict(games=games, leagues=leagues, soccer=SOCCER, soccerLogo=SOCCER_LOGO, coming=COMING, pulled=pulled)
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    links = ''.join(f'<a href="{p}">{l}</a>' for k, l, g, p, s, i in LEAGUES if s == 'live')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · every sport, this week</title>
{HEAD}<style>{CSS}</style></head><body>
<div id="hdr"><span class="brand"><i>◍</i> RAINMAN</span><span class="tag">matchup intelligence · every sport · pick a league</span><span class="hl">{links}</span><span class="right">slate pulled {pulled} · built {built}</span></div>
<div class="wrap">
<div id="rail" class="rail"></div>
<h2>the next eight days <span>every league · click a day to filter the week below</span></h2><div id="cal" class="cal"></div>
<h2 id="todayH"></h2><div id="today" class="today"></div>
<div id="herow" class="herow"><div id="hero" class="hero"></div><div id="marquee"></div></div><div id="subrail" class="subrail"></div>
<div id="filt" class="filt"></div>
<h2 id="weekH"></h2><div id="week" class="days"></div>
<h2 id="linesH"></h2><div id="lines"></div>
<h2 id="teamsH"></h2><div id="teams" class="teams"></div>
<div class="foot">Layer 0 · schedules, records, AP ranks, broadcast and DraftKings lines from ESPN's public scoreboard (pulled {pulled}); implied team totals are derived from the spread and total. NFL and College Football open the full RAINMAN model; the other leagues open a schedule shell on the same framework until their game-log pipelines are connected.</div>
</div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script>
<script>{JS}</script></body></html>"""

def shell(key, label, games, pulled, logo=''):
    page_ = dict(LEAGUES_BY[key]) if key in LEAGUES_BY else {}
    J = dict(games=games, leagues=[dict(key=key, label=label, page='#', status='shell', logo=logo)], soccer=SOCCER, soccerLogo=SOCCER_LOGO, coming=[], pulled=pulled, shell=True)
    tabs = ['Home', 'Matchups', 'Players', 'Intel', 'Picks']
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · {label}</title>
{HEAD}<style>{CSS}</style></head><body>
<div id="hdr"><a class="brand" href="index.html"><i>◍</i> RAINMAN</a><img src="{logo}" alt="" style="height:30px;width:auto"><span class="tag" style="font-family:var(--mono);color:var(--acc)">{label}</span><nav id="tnav">{''.join(f'<span class="{"on" if t == "Home" else ""}">{t}</span>' for t in tabs)}</nav><span class="right"><a href="index.html">← all sports</a> · slate pulled {pulled}</span></div>
<div class="wrap">
<h2>Layer 1 · {label} <span>schedule shell on the RAINMAN framework — the five tabs light up as each pipeline connects</span></h2>
<div class="pipe">
 <div class="card"><div class="k">schedule + broadcast</div><div class="v ok">ON</div><div class="s">ESPN scoreboard, 7-day window</div></div>
 <div class="card"><div class="k">game lines</div><div class="v ok">ON</div><div class="s">DraftKings via ESPN (spread / ML, total)</div></div>
 <div class="card"><div class="k">team logos + records</div><div class="v ok">ON</div><div class="s">ESPN CDN</div></div>
 <div class="card"><div class="k">game logs</div><div class="v todo">NEXT</div><div class="s">per-player box scores → the atomic table</div></div>
 <div class="card"><div class="k">defense vs position</div><div class="v todo">NEXT</div><div class="s">stats allowed per slot, ranks, trends</div></div>
 <div class="card"><div class="k">projections · markets · picks</div><div class="v todo">NEXT</div><div class="s">same model as NFL once logs exist</div></div>
</div>
<div id="herow" class="herow"><div id="hero" class="hero"></div><div id="marquee"></div></div><div id="subrail" class="subrail"></div>
<div id="filt" class="filt"></div>
<h2 id="weekH"></h2><div id="week" class="days"></div>
<h2 id="linesH"></h2><div id="lines"></div>
<h2 id="teamsH"></h2><div id="teams" class="teams"></div>
<div class="foot">Every row here comes from data/raw/slate_all_*.txt (ESPN). Nothing is hand-typed.</div></div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script><script>{JS}</script></body></html>"""

LEAGUES_BY = {k: dict(key=k, label=l, page=p, status=s, logo=i) for k, l, g, p, s, i in LEAGUES}

def main():
    games, pulled = load_slate()
    os.makedirs('dashboard', exist_ok=True)
    open('dashboard/index.html', 'w', encoding='utf-8').write(page(games, pulled))
    n = {}
    for k, l, g, p, s, i in LEAGUES:
        if s != 'shell': continue
        gs = [x for x in games if x['sport'] == k]
        open('dashboard/' + p, 'w', encoding='utf-8').write(shell(k, l, gs, pulled, i)); n[p] = len(gs)
    print(f"dashboard/index.html: {len(games)} games across {len(set(g['lg'] for g in games))} leagues (pulled {pulled}) · shells {n}")

if __name__ == '__main__':
    main()
