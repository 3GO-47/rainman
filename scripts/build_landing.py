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
    ('nba', 'NBA', 'basketball', 'nba.html', 'live', CDN + 'teamlogos/leagues/500-dark/nba.png'),
    ('ncaab', 'College Basketball', 'basketball', 'ncaab.html', 'shell', NCAA_LOGO),
    ('wnba', 'WNBA', 'basketball', 'wnba.html', 'live', CDN + 'teamlogos/leagues/500-dark/wnba.png'),
    ('mlb', 'MLB', 'baseball', 'mlb.html', 'shell', CDN + 'teamlogos/leagues/500-dark/mlb.png'),
    ('nhl', 'NHL', 'hockey', 'nhl.html', 'live', CDN + 'teamlogos/leagues/500-dark/nhl.png'),
    ('soccer', 'Soccer', 'soccer', 'soccer.html', 'shell', CDN + 'leaguelogos/soccer/500-dark/2.png')]
SOCCER = {'epl': 'Premier League', 'mls': 'MLS', 'ucl': 'Champions League', 'laliga': 'La Liga', 'bund': 'Bundesliga', 'seriea': 'Serie A', 'ligue1': 'Ligue 1'}
SOCCER_LOGO = {'epl': 23, 'mls': 19, 'ucl': 2, 'laliga': 15, 'bund': 10, 'seriea': 12, 'ligue1': 9}
SOCCER_LOGO = {k: CDN + f'leaguelogos/soccer/500-dark/{v}.png' for k, v in SOCCER_LOGO.items()}
COMING = [('f1', 'Formula 1', CDN + 'teamlogos/leagues/500-dark/f1.png'), ('ufc', 'UFC', CDN + 'teamlogos/leagues/500/ufc.png')]

MK_LABEL = {'pass_yds': 'Pass yds', 'pass_td': 'Pass TD', 'rush_yds': 'Rush yds', 'rush_att': 'Rush att', 'receptions': 'Receptions', 'rec_yds': 'Rec yds'}
def nfl_teaser():
    """Softest NFL matchups per market this week from prop_projections.csv (matchup multiplier × projected volume)."""
    f = 'data/processed/prop_projections.csv'
    if not os.path.exists(f): return None
    import csv
    rows = list(csv.DictReader(open(f, encoding='utf-8')))
    if not rows: return None
    wk = max(int(r['week']) for r in rows); rows = [r for r in rows if int(r['week']) == wk and r['market'] in MK_LABEL]
    out = {}
    for mk in MK_LABEL:
        R = [r for r in rows if r['market'] == mk and float(r['base'] or 0) > 0]
        floor = sorted((float(r['base']) for r in R), reverse=True)[:40]
        cut = floor[-1] if floor else 0
        R = [r for r in R if float(r['base']) >= cut]
        R.sort(key=lambda r: -float(r['matchup_x']))
        out[mk] = [dict(player=r['player'], team=r['team'], opp=r['opp'], slot=r['slot'], proj=round(float(r['proj']), 1), base=round(float(r['base']), 1), mx=round(float(r['matchup_x']), 2)) for r in R[:3]]
    return dict(week=wk, markets=out)

def sport_teaser(lg, labels):
    """Softest matchups per market for the sportsdataverse leagues (scripts/sports/build.py projections.csv)."""
    f = f'data/sports/{lg}/processed/projections.csv'
    if not os.path.exists(f): return None
    import csv
    rows = [r for r in csv.DictReader(open(f, encoding='utf-8')) if r['market'] in labels and r['opp_rank']]
    if not rows: return None
    out = {}
    for mk in labels:
        R = [r for r in rows if r['market'] == mk and float(r['base'] or 0) > 0]
        R.sort(key=lambda r: -float(r['base'])); R = R[:40]; R.sort(key=lambda r: -(float(r['base']) * float(r['ratio'])))
        out[mk] = [dict(player=r['player'], team=r['team'], opp=r['opp'], proj=round(float(r['proj']), 1), base=round(float(r['base']), 1), mx=round(float(r['ratio']), 2), rank=int(float(r['opp_rank']))) for r in R[:3]]
    return dict(week='', markets={k: v for k, v in out.items() if v})

def load_slate():
    files = sorted(glob.glob('data/raw/slate_all_*.txt'))
    if not files: raise SystemExit('no data/raw/slate_all_*.txt — pull the multi-sport slate first (notes/scrape_recipe.md)')
    f = files[-1]; pulled = re.search(r'(\d{4}-\d{2}-\d{2})', f).group(1)
    games = []
    for line in open(f, encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 26: continue
        if p[22] == '1': continue            # preseason is ignored everywhere (Josh, 2026-10-07)
        lg = p[1]
        games.append(dict(lg=lg, sport='soccer' if lg in SOCCER else lg, sub=SOCCER.get(lg, ''), id=p[2], date=p[3], status=p[4],
                          away=dict(id=p[5], abbr=p[6], name=p[7], rec=p[8], logo=p[9], rank=p[10] if p[10] not in ('', '99') else ''),
                          home=dict(id=p[11], abbr=p[12], name=p[13], rec=p[14], logo=p[15], rank=p[16] if p[16] not in ('', '99') else ''),
                          venue=p[17], tv=p[18], odds=p[19], ou=p[20], week=p[21], neutral=p[23] == '1', book=p[24], note=p[25]))
    return games, pulled

def model_records():
    """W-L by pick type per league from the frozen ledgers (NFL picks_all.csv; sports/<lg>/processed/picks.csv). Data only — no picks."""
    import csv
    out = {}
    def tally(rows, lg):
        by = {}
        for r in rows:
            t = (r.get('type') or '').upper() or 'ALL'; b = by.setdefault(t, dict(W=0, L=0, P=0, pending=0))
            res = (r.get('result') or '').upper()
            if res in ('W', 'L', 'P'): b[res] += 1
            else: b['pending'] += 1
        if by: out[lg] = by
    f = 'data/processed/picks_all.csv'
    if os.path.exists(f): tally(list(csv.DictReader(open(f, encoding='utf-8'))), 'nfl')
    for lg in ('nba', 'nhl', 'wnba'):
        f = f'data/sports/{lg}/processed/picks.csv'
        if os.path.exists(f): tally(list(csv.DictReader(open(f, encoding='utf-8'))), lg)
    return out

HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">"""

CSS = """
:root{--bg:#000;--panel:#0b0b0c;--s2:#131315;--s3:#1a1a1d;--edge:#1d1e21;--edge2:#2a2b30;--fg:#e6e6e9;--dim:#8b8d94;--mute:#5c5e66;--acc:#e8b339;--green:#3fb950;--red:#f0564a;--blue:#58a6ff;--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;--sans:'Inter',system-ui,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:13px;line-height:1.45}a{color:inherit;text-decoration:none}img{-webkit-user-drag:none}
#hdr{display:flex;align-items:center;gap:16px;padding:12px 24px;border-bottom:1px solid var(--edge);background:#050506;position:sticky;top:0;z-index:5}
.brand{font:800 15px/1 var(--mono);letter-spacing:4px}.brand i{color:var(--acc);font-style:normal;margin-right:6px}.tag{color:var(--dim);font-size:12px}#hdr .right{margin-left:auto;color:var(--mute);font:500 10.5px var(--mono)}
.hl{display:flex;gap:4px;margin-left:10px}.hl a{font:600 10px var(--mono);letter-spacing:1px;padding:3px 9px;border:1px solid var(--edge2);border-radius:4px;color:var(--dim)}.hl a:hover{color:var(--fg);border-color:var(--acc)}
.wrap{max-width:1480px;margin:0 auto;padding:18px 24px 40px}
h1{font:800 26px/1.15 var(--sans);letter-spacing:-.3px;margin:6px 0 4px}h1 small{display:block;font:400 13px/1.5 var(--sans);color:var(--dim);margin-top:6px}
h2{font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin:26px 0 10px;display:flex;align-items:baseline;gap:10px}h2 span{font:400 11px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}
.sports{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:14px}
.sp{display:flex;flex-direction:column;align-items:flex-start;gap:4px;padding:12px 12px 10px;border:1px solid var(--edge);border-radius:10px;background:var(--panel);cursor:pointer;position:relative;min-height:116px}.sp:hover{border-color:var(--edge2)}.sp.on{border-color:var(--acc);box-shadow:inset 0 0 0 1px var(--acc)}
.sp img{height:30px;width:auto;max-width:60px;object-fit:contain}.sp b{font-size:13px;margin-top:4px}.sp small{color:var(--dim);font-size:11px}.sp .st{position:absolute;right:10px;top:10px;font:600 9px var(--mono);letter-spacing:1px;padding:2px 6px;border-radius:3px;background:rgba(232,179,57,.12);color:var(--acc)}.sp.shell .st{background:var(--s3);color:var(--dim)}
.sp .rec{font:600 10.5px var(--mono);color:var(--fg)}.sp .rec i{font-style:normal;color:var(--dim);font-weight:400}
.today{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}
.tg{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:9px 11px;border:1px solid var(--edge);border-radius:8px;background:var(--panel)}.tg.lk{cursor:pointer}.tg.lk:hover{border-color:var(--edge2)}
.tg .ln{display:flex;align-items:center;gap:7px;font-size:12.5px}.tg .ln img{width:18px;height:18px;object-fit:contain}.tg .ln b{font-weight:600}.tg .ln small{color:var(--dim);font-size:10.5px}.tg .ln .rk{font:600 9.5px var(--mono);color:var(--acc)}
.tg .meta{grid-column:1/-1;display:flex;justify-content:space-between;gap:8px;font:500 10.5px var(--mono);color:var(--dim);margin-top:3px}.tg .meta b{color:var(--fg)}.tg .lgc{grid-column:2;grid-row:1/3;align-self:center;font:600 9px var(--mono);letter-spacing:1px;color:var(--mute);text-align:right}
.trio{display:grid;grid-template-columns:1.1fr 1.3fr .9fr;gap:12px}@media (max-width:1100px){.trio{grid-template-columns:1fr}}
.card{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:14px 16px}.card h3{margin:0 0 8px;font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);display:flex;justify-content:space-between;align-items:baseline}.card h3 span{font:400 11px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}
.mq{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px;margin:8px 0 10px}.mq .t{display:flex;flex-direction:column;align-items:center;gap:4px;text-align:center}.mq .t img{width:60px;height:60px;object-fit:contain}.mq .t b{font-size:15px}.mq .t small{color:var(--dim)}.mq .t .imp{font:600 13px var(--mono);color:var(--acc)}.mq .at{color:var(--mute);font:600 14px var(--mono)}
.mq2{display:flex;flex-wrap:wrap;gap:6px 14px;font:500 11.5px var(--mono);color:var(--dim);justify-content:center}.mq2 b{color:var(--fg)}
.edge{display:grid;grid-template-columns:auto 1fr auto auto;gap:4px 10px;align-items:center;padding:4px 0;border-bottom:1px solid var(--edge);font-size:12px}.edge:last-child{border:0}.edge .mk{font:600 9.5px var(--mono);letter-spacing:1px;color:var(--mute);min-width:84px}.edge .who b{font-weight:600}.edge .who small{color:var(--dim);margin-left:6px;font-size:10.5px}.edge .pj{font:600 12px var(--mono)}.edge .mx{font:600 10px var(--mono);padding:1px 6px;border-radius:3px;background:rgba(63,185,80,.15);color:var(--green)}
.recrow{display:grid;grid-template-columns:90px 1fr auto;gap:8px;align-items:center;padding:5px 0;border-bottom:1px solid var(--edge);font-size:12px}.recrow:last-child{border:0}.recrow .ty{font:600 9.5px var(--mono);letter-spacing:1px;color:var(--mute)}.recrow .bar{height:8px;background:var(--s3);border-radius:2px;overflow:hidden;display:flex}.recrow .bar i{display:block;height:100%}.recrow .bar .w{background:var(--green)}.recrow .bar .l{background:var(--red)}.recrow .n{font:600 12px var(--mono)}.recrow .n small{color:var(--dim);font-weight:400;margin-left:6px}
.filt{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}.filt button{font:600 10.5px var(--mono);letter-spacing:.5px;padding:4px 10px;border-radius:5px;border:1px solid var(--edge2);background:var(--panel);color:var(--dim);cursor:pointer}.filt button.on{border-color:var(--acc);color:var(--fg);background:rgba(232,179,57,.1)}
table{border-collapse:collapse;width:100%;font-size:12px}th{font:600 9.5px var(--mono);letter-spacing:1px;text-transform:uppercase;color:var(--mute);text-align:left;padding:6px 8px;border-bottom:1px solid var(--edge2);cursor:pointer;white-space:nowrap}th.srt-asc::after{content:' ▲'}th.srt-desc::after{content:' ▼'}td{padding:6px 8px;border-bottom:1px solid var(--edge);vertical-align:middle;white-space:nowrap}tr:hover td{background:var(--s2)}
.tm{display:inline-flex;align-items:center;gap:6px}.tm img{width:18px;height:18px;object-fit:contain}.tm small{color:var(--dim)}.tm .rk{font:600 9.5px var(--mono);color:var(--acc)}.mono{font-family:var(--mono)}.dim{color:var(--dim)}.g{color:var(--green)}.r{color:var(--red)}
.mbar{display:inline-block;height:6px;border-radius:2px;background:var(--acc);vertical-align:middle;margin-left:6px}
.how{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px}.how .card p{margin:4px 0;color:var(--dim);font-size:12px;line-height:1.55}.how .card p b{color:var(--fg)}
.foot{margin-top:28px;padding-top:12px;border-top:1px solid var(--edge);color:var(--mute);font:400 11px/1.6 var(--sans)}
.stand{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}
.empty{color:var(--mute);padding:12px;border:1px dashed var(--edge2);border-radius:8px;text-align:center}
@media (max-width:760px){.wrap{padding:12px}h1{font-size:20px}#hdr .tag,#hdr .hl{display:none}}
"""

JS = r"""
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LG=J.leagues,LGBY={};LG.forEach(l=>LGBY[l.key]=l);const SHELL=!!J.shell;
let SEL=SHELL?LG[0].key:(new URLSearchParams(location.hash.replace('#','')).get('lg')||'nfl');if(!LGBY[SEL])SEL=LG[0].key;
const CT=d=>new Date(d).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:'America/Chicago'}).replace(':00','');
const DAY=d=>new Date(d).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:'America/Chicago'});
const DKEY=d=>new Date(d).toLocaleDateString('en-CA',{timeZone:'America/Chicago'});
const TODAY=DKEY(new Date());
const logo=t=>t.logo?`<img src="https://a.espncdn.com/i/teamlogos/${t.logo}" alt="" onerror="this.style.display='none'">`:'';
const tm=(t,nm)=>`<span class="tm">${logo(t)}${t.rank?`<span class="rk">${t.rank}</span>`:''}<b>${esc(nm?t.name:t.abbr)}</b>${t.rec?`<small>${esc(t.rec)}</small>`:''}</span>`;
const fav=g=>{const m=(g.odds||'').match(/^([A-Z0-9&.' -]+?)\s*(-?\d+(\.\d+)?)$/);return m?{team:m[1].trim(),line:+m[2]}:null};
const implied=g=>{const f=fav(g),ou=+g.ou;if(!f||!ou)return null;const h=f.team===g.home.abbr;const favTot=(ou-f.line)/2;return h?{home:favTot,away:ou-favTot}:{away:favTot,home:ou-favTot}};
const games=J.games.slice().sort((a,b)=>a.date<b.date?-1:1);const byLg={};games.forEach(g=>(byLg[g.sport]=byLg[g.sport]||[]).push(g));
const lgName=g=>g.sport==='soccer'?(J.soccer[g.lg]||g.lg):(LGBY[g.sport]||{label:g.sport}).label;
// ---- sports rail
function rail(){const el=$('#sports');if(!el||SHELL){if(el)el.hidden=true;return}
  el.innerHTML=LG.map(l=>{const n=(byLg[l.key]||[]).length,td=(byLg[l.key]||[]).filter(g=>DKEY(g.date)===TODAY).length;const R=J.records&&J.records[l.key];let rec='';
    if(R){let w=0,L=0;Object.values(R).forEach(b=>{w+=b.W;L+=b.L});if(w+L)rec=`<span class="rec">${w}-${L} <i>model</i></span>`}
    return `<div class="sp ${l.status}${l.key===SEL?' on':''}" data-k="${l.key}"><span class="st">${l.status==='live'?'LIVE MODEL':'SCHEDULE'}</span><img src="${l.logo}" alt="" onerror="this.style.visibility='hidden'"><b>${l.label}</b><small>${td?td+' today · ':''}${n} games this week</small>${rec}</div>`}).join('');
  el.querySelectorAll('.sp').forEach(d=>d.onclick=()=>{SEL=d.dataset.k;history.replaceState(null,'','#lg='+SEL);render()})}
// ---- today
function today(){const el=$('#today');const pool=SHELL?games:games;let day=TODAY;let T=pool.filter(g=>DKEY(g.date)===day);
  if(!T.length){const nxt=pool.find(g=>DKEY(g.date)>TODAY);if(nxt){day=DKEY(nxt.date);T=pool.filter(g=>DKEY(g.date)===day)}}
  $('#todayH').innerHTML=`${day===TODAY?'today':'next up'} · ${T.length?DAY(T[0].date):''} <span>${T.length} games · every league · Central time · click a game to open its league</span>`;
  const sel=T.filter(g=>g.sport===SEL),rest=T.filter(g=>g.sport!==SEL);
  el.innerHTML=[...sel,...rest].slice(0,24).map(g=>{const l=LGBY[g.sport]||{};const f=fav(g);return `<div class="tg ${l.page?'lk':''}" data-p="${l.page||''}"><div class="ln">${tm(g.away)}<small>@</small>${tm(g.home)}</div><div class="lgc">${esc(lgName(g)).toUpperCase()}</div><div class="meta"><span>${CT(g.date)}${g.tv?' · '+esc(g.tv.split(',')[0]):''}</span><span>${f?`<b>${esc(f.team)} ${f.line>0?'+':''}${f.line}</b>`:'<span class="dim">no line</span>'}${g.ou?` · O/U <b>${g.ou}</b>`:''}</span></div></div>`}).join('')||'<div class="empty">nothing scheduled in the slate window</div>';
  if(!SHELL)el.querySelectorAll('.tg.lk').forEach(d=>d.onclick=()=>{if(d.dataset.p&&d.dataset.p!=='#')location.href=d.dataset.p})}
// ---- trio: marquee · edges · record
function trio(){const l=LGBY[SEL];const G=(byLg[SEL]||[]).filter(g=>DKEY(g.date)>=TODAY);
  const score=g=>{const f=fav(g);const rk=(g.away.rank?1:0)+(g.home.rank?1:0);return (g.ou?+g.ou:0)/2-(f?Math.abs(f.line):15)+rk*12+(g.tv?3:0)};
  const mq=G.slice().sort((a,b)=>score(b)-score(a))[0];
  const f=mq&&fav(mq),im=mq&&implied(mq);
  $('#marquee').innerHTML=mq?`<h3>marquee · ${esc(l.label)} <span>${DAY(mq.date)} · ${CT(mq.date)} CT</span></h3><div class="mq"><div class="t">${logo(mq.away)}<b>${esc(mq.away.name)}</b><small>${esc(mq.away.rec)}${mq.away.rank?' · #'+mq.away.rank:''}</small>${im?`<span class="imp">${im.away.toFixed(1)}</span>`:''}</div><div class="at">@</div><div class="t">${logo(mq.home)}<b>${esc(mq.home.name)}</b><small>${esc(mq.home.rec)}${mq.home.rank?' · #'+mq.home.rank:''}</small>${im?`<span class="imp">${im.home.toFixed(1)}</span>`:''}</div></div>
    <div class="mq2">${f?`<span>line <b>${esc(f.team)} ${f.line>0?'+':''}${f.line}</b></span>`:'<span>no line yet</span>'}${mq.ou?`<span>total <b>${mq.ou}</b></span>`:''}${mq.tv?`<span>TV <b>${esc(mq.tv.split(',')[0])}</b></span>`:''}<span>${esc(mq.venue)}</span></div>${im?'<p class="dim" style="text-align:center;font-size:10.5px;margin:8px 0 0">gold numbers = implied team totals from the spread and total</p>':''}`:`<h3>marquee</h3><div class="empty">no upcoming games for ${esc(l.label)} in the slate window</div>`;
  const T=J.teasers&&J.teasers[SEL];const ed=$('#edges');
  if(T&&Object.keys(T.markets).length){ed.innerHTML=`<h3>softest matchups${T.week?' · wk '+T.week:''} <span>top player per market · from the ${esc(l.label)} model</span></h3>${Object.entries(T.markets).map(([mk,rows])=>{const r=rows[0];if(!r)return '';return `<div class="edge"><span class="mk">${esc(T.labels&&T.labels[mk]||mk)}</span><span class="who"><b>${esc(r.player)}</b><small>${esc(r.team)} vs ${esc(r.opp)}</small></span><span class="pj">${r.proj}</span><span class="mx" title="matchup multiplier vs his baseline${r.rank?' · opponent rank '+r.rank:''}">×${r.mx.toFixed(2)}</span></div>`}).join('')}<p class="dim" style="font-size:10.5px;margin:8px 0 0">projection · ×multiplier = how much softer than average the opponent is for that stat · the full board lives on the dashboard</p>`}
  else ed.innerHTML=`<h3>softest matchups</h3><div class="empty">${l.status==='live'?'no games on the slate for the model yet':'player modeling for '+esc(l.label)+' arrives with a box-score source — schedule and lines are live'}</div>`;
  const R=J.records&&J.records[SEL];const rc=$('#record');const LBL={ML:'moneyline',ATS:'spread',TOTAL:'total',PROP:'props',TD:'anytime TD',DFS:'DFS',ALL:'all'};
  if(R){const rows=Object.entries(R).filter(([t,b])=>b.W+b.L+b.P);let w=0,L=0;rows.forEach(([,b])=>{w+=b.W;L+=b.L});
    rc.innerHTML=`<h3>model record <span>frozen before kickoff, graded after</span></h3><div class="recrow"><span class="ty">ALL</span><span class="bar"><i class="w" style="width:${w+L?100*w/(w+L):0}%"></i><i class="l" style="width:${w+L?100*L/(w+L):0}%"></i></span><span class="n">${w}-${L}<small>${w+L?(100*w/(w+L)).toFixed(0)+'%':''}</small></span></div>${rows.map(([t,b])=>`<div class="recrow"><span class="ty">${LBL[t]||t}</span><span class="bar"><i class="w" style="width:${b.W+b.L?100*b.W/(b.W+b.L):0}%"></i><i class="l" style="width:${b.W+b.L?100*b.L/(b.W+b.L):0}%"></i></span><span class="n">${b.W}-${b.L}${b.P?'-'+b.P:''}<small>${b.pending} open</small></span></div>`).join('')}<p class="dim" style="font-size:10.5px;margin:8px 0 0">break-even at −110 is 52.4% · the dashboard has every graded position</p>`}
  else rc.innerHTML=`<h3>model record</h3><div class="empty">${l.status==='live'?'nothing graded yet':'no model for '+esc(l.label)+' yet'}</div>`}
// ---- the week: one sortable table
let DAYF='all',sortK='date',sortA=true;
function week(){const l=LGBY[SEL];const G=(byLg[SEL]||[]);const days=[...new Set(G.map(g=>DKEY(g.date)))].sort();
  $('#weekH').innerHTML=`${esc(l.label)} · the week <span>${G.length} games · ${G.filter(g=>g.odds).length} with lines · Central time · click a header to sort</span>`;
  $('#filt').innerHTML=`<button data-d="all" class="${DAYF==='all'?'on':''}">all days</button>${days.map(d=>`<button data-d="${d}" class="${DAYF===d?'on':''}">${DAY(G.find(g=>DKEY(g.date)===d).date)} <span class="dim">${G.filter(g=>DKEY(g.date)===d).length}</span></button>`).join('')}`;
  $('#filt').querySelectorAll('button').forEach(b=>b.onclick=()=>{DAYF=b.dataset.d;week()});
  const rows=G.filter(g=>DAYF==='all'||DKEY(g.date)===DAYF).map(g=>{const f=fav(g),im=implied(g);return {g,f,im,date:g.date,match:g.away.abbr+'@'+g.home.abbr,line:f?Math.abs(f.line):99,tot:+g.ou||0,tv:g.tv||'',sub:g.sub||''}});
  const V={date:r=>r.date,match:r=>r.match,line:r=>r.line,tot:r=>r.tot,tv:r=>r.tv,sub:r=>r.sub};rows.sort((a,b)=>{const x=V[sortK](a),y=V[sortK](b);return (x<y?-1:x>y?1:0)*(sortA?1:-1)});
  const th=(k,lab)=>`<th data-k="${k}" class="${sortK===k?(sortA?'srt-asc':'srt-desc'):''}">${lab}</th>`;const mx=Math.max(1,...rows.map(r=>r.f?Math.abs(r.f.line):0));
  $('#week').innerHTML=rows.length?`<table><thead><tr>${th('date','kick (CT)')}${SEL==='soccer'?th('sub','league'):''}${th('match','matchup')}${th('line','favorite · line')}${th('tot','total')}<th>implied</th>${th('tv','tv')}<th>venue</th></tr></thead><tbody>
    ${rows.map(r=>`<tr><td class="mono">${DAY(r.date)} ${CT(r.date)}</td>${SEL==='soccer'?`<td class="dim">${esc(r.sub)}</td>`:''}<td>${tm(r.g.away)} <span class="dim">${r.g.neutral?'vs':'@'}</span> ${tm(r.g.home)}</td><td>${r.f?`<b>${esc(r.f.team)} ${r.f.line>0?'+':''}${r.f.line}</b><span class="mbar" style="width:${(60*Math.abs(r.f.line)/mx).toFixed(0)}px"></span>`:'<span class="dim">—</span>'}</td><td class="mono">${r.g.ou||'<span class="dim">—</span>'}</td><td class="mono dim">${r.im?`${r.im.away.toFixed(1)} · ${r.im.home.toFixed(1)}`:''}</td><td class="dim">${esc(r.tv.split(',')[0])}</td><td class="dim">${esc(r.g.venue)}</td></tr>`).join('')}</tbody></table>`:'<div class="empty">no games in the slate window</div>';
  $('#week').querySelectorAll('th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(sortK===k)sortA=!sortA;else{sortK=k;sortA=k!=='tot'}week()})}
// ---- standings from the records carried on the slate (shell leagues; the live leagues have real standings on their dashboards)
function standings(){const el=$('#stand');if(!el)return;const G=byLg[SEL]||[];const T={};
  G.forEach(g=>[g.away,g.home].forEach(t=>{if(!t.rec||T[t.abbr])return;const m=t.rec.match(/^(\d+)-(\d+)(?:-(\d+))?/);if(!m)return;T[t.abbr]={t,w:+m[1],l:+m[2],d:m[3]!=null?+m[3]:null,rec:t.rec,sub:g.sub}}));
  const rows=Object.values(T).sort((a,b)=>(b.w/(b.w+b.l+(b.d||0)||1))-(a.w/(a.w+a.l+(a.d||0)||1))||b.w-a.w);
  if(!rows.length){el.innerHTML='';$('#standH').innerHTML='';return}
  const groups={};rows.forEach(r=>(groups[r.sub||'']=groups[r.sub||'']||[]).push(r));
  if(Object.keys(groups).length===1&&rows.length>12){const k=Object.keys(groups)[0];const per=Math.ceil(rows.length/Math.min(3,Math.ceil(rows.length/11)));delete groups[k];for(let i=0;i<rows.length;i+=per)groups[(k?k+' · ':'')+`${i+1}–${Math.min(rows.length,i+per)}`]=rows.slice(i,i+per)}
  $('#standH').innerHTML=`records <span>every team on this week's slate · from the records ESPN carries on the schedule</span>`;
  el.innerHTML=`<div class="stand">${Object.entries(groups).map(([k,R])=>`<div class="card">${k?`<h3>${esc(k)}</h3>`:''}<table><thead><tr><th>#</th><th>team</th><th>record</th><th>win%</th></tr></thead><tbody>${R.map((r,i)=>`<tr><td class="dim">${rows.indexOf(r)+1}</td><td>${tm(r.t,true)}</td><td class="mono">${esc(r.rec)}</td><td class="mono">${(100*r.w/((r.w+r.l+(r.d||0))||1)).toFixed(0)}%</td></tr>`).join('')}</tbody></table></div>`).join('')}</div>`}
function render(){rail();today();trio();week();standings();const l=LGBY[SEL];const o=$('#openlg');if(o){o.href=l.page||'#';o.textContent=l.status==='live'?`open the ${l.label} dashboard →`:`${l.label}: schedule & lines →`;o.style.display=SHELL?'none':''}
  const h=$('#lgh');if(h)h.textContent=l.label}
render();
"""

def page(games, pulled):
    leagues = [dict(key=k, label=l, group=g, page=p, status=s, logo=i) for k, l, g, p, s, i in LEAGUES]
    BB = {'pts': 'Points', 'reb': 'Rebounds', 'ast': 'Assists', 'tpm': '3-pointers', 'pra': 'P+R+A'}
    HK = {'sog': 'Shots on goal', 'p': 'Points', 'g': 'Goals', 'a': 'Assists', 'sv': 'Saves'}
    teasers = {'nfl': nfl_teaser(), 'nba': sport_teaser('nba', BB), 'wnba': sport_teaser('wnba', BB), 'nhl': sport_teaser('nhl', HK)}
    for k, lab in (('nfl', MK_LABEL), ('nba', BB), ('wnba', BB), ('nhl', HK)):
        if teasers.get(k): teasers[k]['labels'] = lab
    J = dict(games=games, leagues=leagues, soccer=SOCCER, soccerLogo=SOCCER_LOGO, pulled=pulled, teasers=teasers, records=model_records())
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    links = ''.join(f'<a href="{p}">{l}</a>' for k, l, g, p, s, i in LEAGUES)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · every sport, one slate</title>
{HEAD}<style>{CSS}</style></head><body>
<div id="hdr"><span class="brand"><i>◍</i> RAINMAN</span><span class="tag">matchup intelligence for every sport</span><span class="hl">{links}</span><span class="right">slate {pulled} · built {built}</span></div>
<div class="wrap">
<h1>What's on. Who's soft. Where the model stands.<small>Pick a league. Every game of the week with its line, the players whose opponents give up the most, and the record of the picks we froze before kickoff. Every number traces back to game logs and public schedules — nothing is typed in by hand.</small></h1>
<div id="sports" class="sports"></div>
<h2 id="todayH"></h2><div id="today" class="today"></div>
<h2><span id="lgh"></span> <span>· this week</span> <a id="openlg" class="hl" style="margin-left:auto" href="#"></a></h2>
<div class="trio"><div class="card" id="marquee"></div><div class="card" id="edges"></div><div class="card" id="record"></div></div>
<h2 id="weekH"></h2><div id="filt" class="filt"></div><div id="week"></div>
<h2 id="standH"></h2><div id="stand"></div>
<h2>how to read it</h2><div class="how">
 <div class="card"><h3>matchups</h3><p>Every defense is ranked by how much it gives up to each position slot (QB, RB1, WR1 …). <b>Rank 1 of 32 means the defense allows the most</b> — the best spot for the offense. Ψ is a slot's average rank across the stats that matter for it.</p></div>
 <div class="card"><h3>the model</h3><p>Projections start from a player's own history, then adjust for the opponent's rank in that exact stat, the defense's style, the game environment and his role. Positions are <b>frozen before kickoff</b> and graded afterward — the record is real, not back-fitted.</p></div>
 <div class="card"><h3>the data</h3><p>Game logs and depth charts from the public record (Pro Football Reference, ESPN, nflverse, sportsdataverse), lines from DraftKings via ESPN and the Kalshi exchange. <b>Preseason is ignored everywhere.</b> Rebuilt daily.</p></div>
</div>
<div class="foot">RAINMAN · Layer 0 · schedules, records, ranks, broadcasts and lines from ESPN's public scoreboard (pulled {pulled}); implied team totals are derived from the spread and the total. Dashboards: NFL · College Football · NBA · WNBA · NHL (live models) · College Basketball · MLB · Soccer (schedule and lines until a box-score source lands).</div>
</div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script>
<script>{JS}</script></body></html>"""

LEAGUES_BY = {k: dict(key=k, label=l, page=p, status=s, logo=i) for k, l, g, p, s, i in LEAGUES}

def shell(key, label, games, pulled, logo=''):
    """Schedule-and-lines page for a league without a player data source yet (same look, one league, standings from the slate records)."""
    J = dict(games=games, leagues=[dict(key=key, label=label, page='#', status='shell', logo=logo)], soccer=SOCCER, soccerLogo=SOCCER_LOGO, pulled=pulled, shell=True, teasers={}, records={})
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    links = ''.join(f'<a href="{p}">{l}</a>' for k, l, g, p, s, i in LEAGUES)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · {label}</title>
{HEAD}<style>{CSS}</style></head><body>
<div id="hdr"><a class="brand" href="index.html"><i>◍</i> RAINMAN</a><span class="tag">{label} · schedule &amp; lines</span><span class="hl">{links}</span><span class="right">slate {pulled} · built {built}</span></div>
<div class="wrap">
<h1><img src="{logo}" alt="" style="height:34px;vertical-align:middle;margin-right:10px" onerror="this.style.display='none'">{label}<small>Every game in the slate window with its DraftKings line, total and implied scores, plus the records ESPN carries on the schedule. Player-level matchups and the pick model arrive for {label} when a box-score source is wired in — the same framework as the NFL dashboard.</small></h1>
<div id="sports" class="sports" hidden></div>
<h2 id="todayH"></h2><div id="today" class="today"></div>
<h2><span id="lgh"></span> <span>· this week</span></h2>
<div class="trio"><div class="card" id="marquee"></div><div class="card" id="edges"></div><div class="card" id="record"></div></div>
<h2 id="weekH"></h2><div id="filt" class="filt"></div><div id="week"></div>
<h2 id="standH"></h2><div id="stand"></div>
<div class="foot">RAINMAN · {label} · schedules, records and lines from ESPN's public scoreboard (pulled {pulled}). <a href="index.html">← all sports</a></div>
</div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script>
<script>{JS}</script></body></html>"""

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
