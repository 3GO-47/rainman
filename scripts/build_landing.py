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
#hdr{display:flex;align-items:center;gap:18px;padding:12px 22px;border-bottom:1px solid var(--edge);background:#050506}
#hdr .brand{font-family:var(--mono);font-weight:700;letter-spacing:.22em;font-size:15px}#hdr .brand i{color:var(--acc);font-style:normal}
#hdr .tag{color:var(--dim);font-size:12px}#hdr .right{margin-left:auto;font-family:var(--mono);color:var(--dim);font-size:11px}
.wrap{max-width:1560px;margin:0 auto;padding:16px 22px 60px}
h2{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim);margin:22px 0 10px;font-weight:600;display:flex;align-items:baseline;gap:10px}h2 span{color:var(--mute);text-transform:none;letter-spacing:0;font-weight:400}
/* league rail */
.rail{display:grid;grid-template-columns:repeat(10,1fr);gap:8px}
.lg{position:relative;display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 8px 10px;border:1px solid var(--edge2);border-radius:10px;background:linear-gradient(180deg,#141416,#0b0b0c);cursor:pointer;text-align:center;min-width:0}
.lg:hover{border-color:#4a4b52}.lg.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc) inset}
.lg img{height:54px;width:auto;max-width:100%;object-fit:contain}.lg b{font-size:12px;letter-spacing:.02em;line-height:1.2;max-width:100%}
.lg small{font-family:var(--mono);font-size:10px;color:var(--dim)}.lg .st{font-family:var(--mono);font-size:9px;letter-spacing:.1em;padding:2px 7px;border-radius:9px;border:1px solid var(--edge2);color:var(--dim)}
.lg.live .st{background:#2b2309;border-color:#6b5415;color:var(--acc)}.lg.soon{opacity:.45;cursor:default}
.subrail{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.sub{display:flex;align-items:center;gap:7px;padding:5px 10px 5px 6px;border:1px solid var(--edge2);border-radius:8px;background:var(--panel);cursor:pointer;font-size:12px}
.sub img{height:22px;width:auto}.sub small{font-family:var(--mono);font-size:10px;color:var(--dim)}.sub.on{border-color:var(--acc)}.sub:hover:not(.on){border-color:#4a4b52}
/* today strip (every league) */
.today{display:grid;grid-template-columns:repeat(auto-fill,minmax(228px,1fr));gap:6px}
.tg{display:grid;grid-template-columns:22px 1fr auto;gap:8px;align-items:center;padding:6px 8px;border:1px solid var(--edge);border-radius:8px;background:var(--panel);font-size:12px;cursor:pointer}
.tg:hover{border-color:#4a4b52}.tg>img{height:18px;width:22px;object-fit:contain}.tg .tt{display:flex;align-items:center;gap:4px;min-width:0}.tg .tt img{width:18px;height:18px;object-fit:contain}.tg .tt b{font-family:var(--mono);font-size:11px}
.tg .tt .at{color:var(--mute);margin:0 2px}.tg .tr{text-align:right;font-family:var(--mono);font-size:10px;color:var(--dim);white-space:nowrap}.tg .tr b{display:block;color:var(--fg);font-size:11px}
/* hero */
.hero{display:grid;grid-template-columns:auto 1fr auto;gap:22px;align-items:center;padding:16px 20px;border:1px solid var(--edge2);border-radius:12px;background:linear-gradient(135deg,#17171a,#0a0a0b 60%);margin-top:12px}
.hero img{height:84px;width:auto;max-width:150px;object-fit:contain}.hero h1{margin:0;font-size:22px;letter-spacing:.02em}.hero .hs{display:flex;gap:26px;flex-wrap:wrap;margin-top:8px}
.hs div{min-width:110px}.hs .k{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}.hs .v{font-family:var(--mono);font-size:20px;font-weight:700;margin-top:2px}.hs .s{color:var(--dim);font-size:11px}
.open{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border:1px solid var(--acc);border-radius:8px;color:var(--acc);font-family:var(--mono);font-size:12px;letter-spacing:.08em;white-space:nowrap}
.open:hover{background:var(--acc);color:#000}.open.dim{border-color:var(--edge2);color:var(--dim)}
/* the week */
.days{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:10px}
.day{background:var(--panel);border:1px solid var(--edge);border-radius:10px;overflow:hidden}.day.isToday{border-color:#6b5415}.day h3{margin:0;padding:8px 12px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);border-bottom:1px solid var(--edge);background:var(--s2);display:flex;justify-content:space-between}.day.isToday h3{color:var(--acc)}
.g{display:grid;grid-template-columns:66px 1fr auto;gap:10px;padding:9px 12px;border-bottom:1px solid var(--edge);align-items:center}.g:last-child{border-bottom:0}
.g .t{font-family:var(--mono);font-size:10px;color:var(--dim);line-height:1.3}.g .t b{display:block;color:var(--fg);font-size:12px}
.g .tm{display:flex;flex-direction:column;gap:3px;min-width:0}.g .row{display:flex;align-items:center;gap:7px;font-size:13px;min-width:0}.g .row img{width:24px;height:24px;object-fit:contain;flex:none}.g .row .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.g .row .rec{font-family:var(--mono);color:var(--mute);font-size:10px;flex:none}.g .row .rk{font-family:var(--mono);color:var(--acc);font-size:10px;flex:none}
.g .ln{text-align:right;font-family:var(--mono);font-size:11px;white-space:nowrap}.g .ln b{color:var(--fg);display:block;font-size:12px}.g .ln span{display:block;color:var(--dim);font-size:10px}
.g .vn{grid-column:1/-1;color:var(--mute);font-size:10px;margin-top:-4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.g .vn em{color:var(--blue);font-style:normal}
.empty{color:var(--dim);padding:20px;border:1px dashed var(--edge2);border-radius:10px;text-align:center}
.teams{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}.team{display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--panel);border:1px solid var(--edge);border-radius:8px;font-size:12px}
.team img{width:26px;height:26px;object-fit:contain}.team small{display:block;color:var(--dim);font-family:var(--mono);font-size:10px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 0}.chip{font-family:var(--mono);font-size:11px;padding:4px 10px;border:1px solid var(--edge2);border-radius:14px;color:var(--dim);cursor:pointer;background:var(--panel)}.chip.on{color:#000;background:var(--acc);border-color:var(--acc)}
.foot{margin-top:40px;color:var(--mute);font-size:11px;font-family:var(--mono);border-top:1px solid var(--edge);padding-top:12px}
@media(max-width:1100px){.rail{grid-template-columns:repeat(5,1fr)}}@media(max-width:700px){.rail{grid-template-columns:repeat(3,1fr)}.hero{grid-template-columns:1fr}.wrap{padding:12px 14px 40px}.lg img{height:40px}}
"""

JS = r"""
const G=J.games,LG=J.leagues,SUB=J.soccer,SUBLOGO=J.soccerLogo,TZD='America/Chicago';
const logo=p=>p?'https://a.espncdn.com/i/teamlogos/'+p:'';
const fmtT=d=>new Date(d).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:TZD}).replace(':00','');
const dayKey=d=>new Date(d).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:TZD});
const TODAY=dayKey(new Date().toISOString());const LGBY=Object.fromEntries(LG.map(l=>[l.key,l]));
const byLg={};G.forEach(g=>{(byLg[g.sport]=byLg[g.sport]||[]).push(g)});
let SEL=location.hash.replace('#','')||'nfl',SUBSEL='';if(!LGBY[SEL])SEL='nfl';
const lgLogo=g=>g.sport==='soccer'?SUBLOGO[g.lg]:LGBY[g.sport].logo;
/* league rail */
const rail=document.getElementById('rail');
rail.innerHTML=LG.map(l=>{const n=(byLg[l.key]||[]).length;return `<div class="lg ${l.status}${l.key===SEL?' on':''}" data-k="${l.key}"><img src="${l.logo}" alt=""><b>${l.label}</b><small>${n} games · 7 days</small><span class="st">${l.status==='live'?'LIVE MODEL':'SCHEDULE'}</span></div>`}).join('')
 +J.coming.map(c=>`<div class="lg soon"><img src="${c[2]}" alt=""><b>${c[1]}</b><small>coming soon</small><span class="st">SOON</span></div>`).join('');
rail.querySelectorAll('.lg[data-k]').forEach(el=>el.onclick=()=>select(el.dataset.k));
function select(k){SEL=k;SUBSEL='';history.replaceState(null,'','#'+k);rail.querySelectorAll('.lg').forEach(e=>e.classList.toggle('on',e.dataset.k===k));render();document.getElementById('hero').scrollIntoView({block:'start',behavior:'instant'})}
/* today, every league */
(function(){const t=G.filter(g=>dayKey(g.date)===TODAY).sort((a,b)=>a.date.localeCompare(b.date));const el=document.getElementById('today');
  document.getElementById('todayH').innerHTML=`today · ${TODAY} <span>${t.length} games across ${new Set(t.map(g=>g.lg)).size} leagues · Central time</span>`;
  el.innerHTML=t.map(g=>`<div class="tg" data-k="${g.sport}"><img src="${lgLogo(g)}" alt=""><div class="tt"><img src="${logo(g.away.logo)}" alt="" onerror="this.style.visibility='hidden'"><b>${g.away.abbr}</b><span class="at">${g.neutral?'vs':'@'}</span><img src="${logo(g.home.logo)}" alt="" onerror="this.style.visibility='hidden'"><b>${g.home.abbr}</b></div><div class="tr"><b>${fmtT(g.date)}</b>${g.odds||g.tv||''}</div></div>`).join('')||'<div class="empty">nothing today</div>';
  el.querySelectorAll('.tg').forEach(x=>x.onclick=()=>select(x.dataset.k))})();
function gameRow(g){const line=g.odds?`<b>${g.odds}</b>`:'<b class="dim">—</b>';const ou=g.ou?`<span>O/U ${g.ou}</span>`:'';const tv=g.tv?`<span>${g.tv}</span>`:'';
  const row=t=>`<div class="row"><img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'">${t.rank?`<span class="rk">#${t.rank}</span>`:''}<span class="nm">${t.name}</span><span class="rec">${t.rec}</span></div>`;
  return `<div class="g"><div class="t"><b>${fmtT(g.date)}</b>${g.tv||''}</div><div class="tm">${row(g.away)}${row(g.home)}</div><div class="ln">${line}${ou}</div>${g.note||g.venue?`<div class="vn">${g.note?`<em>${g.note}</em> · `:''}${g.venue}${g.sub?` · ${g.sub}`:''}${g.neutral?' · neutral site':''}</div>`:''}</div>`}
function render(){const l=LGBY[SEL];let gs=(byLg[SEL]||[]).slice().sort((a,b)=>a.date.localeCompare(b.date));
  const subs=SEL==='soccer'?[...new Set(gs.map(g=>g.lg))]:[];if(SUBSEL)gs=gs.filter(g=>g.lg===SUBSEL);
  const days={};gs.forEach(g=>{(days[dayKey(g.date)]=days[dayKey(g.date)]||[]).push(g)});
  const withLines=gs.filter(g=>g.odds).length,teams=new Set();gs.forEach(g=>{teams.add(g.away.abbr);teams.add(g.home.abbr)});
  const big=gs.filter(g=>g.ou).sort((a,b)=>parseFloat(b.ou)-parseFloat(a.ou))[0];
  const fav=gs.filter(g=>/-\d/.test(g.odds||'')).sort((a,b)=>parseFloat(b.odds.split(' ').pop())-parseFloat(a.odds.split(' ').pop()))[0];
  const favTxt=fav?fav.odds:'—';const favNum=fav?Math.abs(parseFloat(fav.odds.split(' ').pop())):0;
  const bigFav=gs.filter(g=>/-\d/.test(g.odds||'')).sort((a,b)=>Math.abs(parseFloat(a.odds.split(' ').pop()))-Math.abs(parseFloat(b.odds.split(' ').pop())))[0];
  const title=SUBSEL?SUB[SUBSEL]:l.label;const heroLogo=SUBSEL?SUBLOGO[SUBSEL]:l.logo;
  document.getElementById('hero').innerHTML=`<img src="${heroLogo}" alt=""><div><h1>${title}</h1><div class="hs">
    <div><div class="k">next 7 days</div><div class="v">${gs.length}</div><div class="s">games · ${teams.size} teams</div></div>
    <div><div class="k">lines posted</div><div class="v">${withLines}</div><div class="s">${gs[0]&&gs[0].book?gs[0].book:'DraftKings'} via ESPN</div></div>
    <div><div class="k">highest total</div><div class="v">${big?big.ou:'—'}</div><div class="s">${big?`${big.away.abbr} @ ${big.home.abbr} · ${dayKey(big.date)}`:''}</div></div>
    <div><div class="k">closest line</div><div class="v">${bigFav?bigFav.odds:'—'}</div><div class="s">${bigFav?`${bigFav.away.abbr} @ ${bigFav.home.abbr}`:''}</div></div>
    <div><div class="k">model</div><div class="v" style="color:${l.status==='live'?'var(--acc)':'var(--dim)'}">${l.status==='live'?'LIVE':'SCHEDULE'}</div><div class="s">${l.status==='live'?'game logs · DvP · projections · markets · picks':'logs, DvP and projections follow the NFL framework'}</div></div></div></div>
    <a class="open ${l.status==='live'?'':'dim'}" href="${l.page}">${l.status==='live'?'OPEN '+l.label.toUpperCase()+' →':'OPEN '+l.label.toUpperCase()+' SHELL →'}</a>`;
  document.getElementById('subrail').innerHTML=subs.length?`<div class="sub ${SUBSEL?'':'on'}" data-s=""><small>all leagues</small></div>`+subs.map(s=>`<div class="sub ${SUBSEL===s?'on':''}" data-s="${s}"><img src="${SUBLOGO[s]}" alt="">${SUB[s]||s}<small>${(byLg.soccer||[]).filter(g=>g.lg===s).length}</small></div>`).join(''):'';
  document.querySelectorAll('#subrail .sub').forEach(c=>c.onclick=()=>{SUBSEL=c.dataset.s;render()});
  document.getElementById('weekH').innerHTML=`${title} · the week <span>${gs.length} games · Central time</span>`;
  document.getElementById('week').innerHTML=Object.entries(days).map(([d,g])=>`<div class="day${d===TODAY?' isToday':''}"><h3><span>${d}${d===TODAY?' · today':''}</span><span>${g.length}</span></h3>${g.map(gameRow).join('')}</div>`).join('')||'<div class="empty">nothing scheduled in the next seven days</div>'}
render();
"""

def page(games, pulled):
    leagues = [dict(key=k, label=l, group=g, page=p, status=s, logo=i) for k, l, g, p, s, i in LEAGUES]
    J = dict(games=games, leagues=leagues, soccer=SOCCER, soccerLogo=SOCCER_LOGO, coming=COMING, pulled=pulled)
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · every sport, this week</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div id="hdr"><span class="brand"><i>◍</i> RAINMAN</span><span class="tag">matchup intelligence · every sport · pick a league</span><span class="right">slate pulled {pulled} · built {built}</span></div>
<div class="wrap">
<div id="rail" class="rail"></div>
<h2 id="todayH"></h2><div id="today" class="today"></div>
<div id="hero" class="hero"></div><div id="subrail" class="subrail"></div>
<h2 id="weekH"></h2><div id="week" class="days"></div>
<div class="foot">Layer 0 · schedules, records, broadcast and DraftKings lines from ESPN's public scoreboard (pulled {pulled}). NFL and College Football open the full RAINMAN model; the other leagues open a schedule shell on the same framework until their game-log pipelines are connected.</div>
</div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script>
<script>{JS}</script></body></html>"""

SHELL_JS = r"""
const G=J.games;const logo=p=>p?'https://a.espncdn.com/i/teamlogos/'+p:'';
const TZD='America/Chicago';const fmtT=d=>new Date(d).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:TZD}).replace(':00',''),dayKey=d=>new Date(d).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:TZD});
const TODAY=dayKey(new Date().toISOString());let SUBSEL='';
function gameRow(g){const line=g.odds?`<b>${g.odds}</b>`:'<b class="dim">—</b>';const ou=g.ou?`<span>O/U ${g.ou}</span>`:'';
  const row=t=>`<div class="row"><img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'">${t.rank?`<span class="rk">#${t.rank}</span>`:''}<span class="nm">${t.name}</span><span class="rec">${t.rec}</span></div>`;
  return `<div class="g"><div class="t"><b>${fmtT(g.date)}</b>${g.tv||''}</div><div class="tm">${row(g.away)}${row(g.home)}</div><div class="ln">${line}${ou}</div>${g.note||g.venue?`<div class="vn">${g.note?`<em>${g.note}</em> · `:''}${g.venue}${g.sub?` · ${g.sub}`:''}</div>`:''}</div>`}
function render(){let gs=G.slice().sort((a,b)=>a.date.localeCompare(b.date));const subs=[...new Set(gs.map(g=>g.lg))];if(SUBSEL)gs=gs.filter(g=>g.lg===SUBSEL);
  const days={};gs.forEach(g=>{(days[dayKey(g.date)]=days[dayKey(g.date)]||[]).push(g)});const teams={};gs.forEach(g=>{[g.away,g.home].forEach(t=>{if(t.abbr!=='TBD')teams[t.abbr+'|'+g.lg]=t})});
  document.getElementById('out').innerHTML=`${subs.length>1?`<div class="chips"><span class="chip ${SUBSEL?'':'on'}" data-s="">all</span>${subs.map(s=>`<span class="chip ${SUBSEL===s?'on':''}" data-s="${s}">${J.soccer[s]||s}</span>`).join('')}</div>`:''}
   <h2>this week <span>${gs.length} games · Central time</span></h2><div class="days">${Object.entries(days).map(([d,g])=>`<div class="day${d===TODAY?' isToday':''}"><h3><span>${d}${d===TODAY?' · today':''}</span><span>${g.length}</span></h3>${g.map(gameRow).join('')}</div>`).join('')||'<div class="empty">nothing scheduled</div>'}</div>
   <h2>teams on the slate <span>${Object.keys(teams).length}</span></h2><div class="teams">${Object.values(teams).sort((a,b)=>a.name.localeCompare(b.name)).map(t=>`<div class="team"><img src="${logo(t.logo)}" alt="" onerror="this.style.visibility='hidden'"><div>${t.name}<small>${t.abbr} · ${t.rec||'—'}</small></div></div>`).join('')}</div>`;
  document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{SUBSEL=c.dataset.s;render()})}
render();
"""

def shell(key, label, games, pulled, logo=''):
    J = dict(games=games, soccer=SOCCER)
    tabs = ['Home', 'Matchups', 'Players', 'Intel', 'Picks']
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · {label}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}
#tnav{{display:flex;gap:2px;margin-left:14px}}#tnav span{{font-family:var(--mono);font-size:11px;padding:6px 10px;border-bottom:2px solid transparent;color:var(--mute)}}#tnav span.on{{color:var(--fg);border-color:var(--acc)}}
.pipe{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:10px}}.pipe .card{{background:var(--panel);border:1px solid var(--edge);border-radius:10px;padding:12px 14px}}.pipe .ok{{color:var(--green)}}.pipe .todo{{color:var(--mute)}}
</style></head><body>
<div id="hdr"><a class="brand" href="index.html"><i>◍</i> RAINMAN</a><img src="{logo}" alt="" style="height:30px;width:auto"><span class="tag" style="font-family:var(--mono);color:var(--acc)">{label}</span><nav id="tnav">{''.join(f'<span class="{"on" if t == "Home" else ""}">{t}</span>' for t in tabs)}</nav><span class="right"><a href="index.html">← all sports</a> · slate pulled {pulled}</span></div>
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
        open('dashboard/' + p, 'w', encoding='utf-8').write(shell(k, l, gs, pulled, i)); n[p] = len(gs)
    print(f"dashboard/index.html: {len(games)} games across {len(set(g['lg'] for g in games))} leagues (pulled {pulled}) · shells {n}")

if __name__ == '__main__':
    main()
