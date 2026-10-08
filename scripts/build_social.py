"""Social — a shared space for plays: log bets (manual entry or saved from the Arb Engine), grade them, see your record and weekly P&L,
rank on a weekly leaderboard and share plays with a link. Local-only prototype: everything lives in the visitor's browser
(localStorage keys rainman.plays = saved/unplaced plays from the Arb Engine, rainman.bets = the ledger, rainman.profile, rainman.friends);
a share link carries a compact copy of your plays so a friend can import them and tail them. No account, no server, no credentials.

Inputs: data/raw/slate_all_<date>.txt (game picker, logos), data/processed/game_lines.csv (NFL finals for automatic grading).
Output: dashboard/social.html
"""
import csv, glob, json, os, re
from datetime import datetime, timedelta
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
NFLV = {'WAS': 'WSH', 'LA': 'LAR', 'JAX': 'JAX'}   # nflverse → ESPN slate abbreviations

def slate():
    files = sorted(glob.glob('data/raw/slate_all_*.txt')); G = []
    for line in open(files[-1], encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 26 or p[22] == '1': continue
        G.append(dict(lg=p[1], id=p[2], date=p[3], away=p[6], home=p[12], al=p[9], hl=p[15]))
    return G, re.search(r'(\d{4}-\d{2}-\d{2})', files[-1]).group(1)

def results():
    """Finals keyed by league|away|home|date (UTC date of the slate row; NFL from game_lines.csv — gameday is the local date, so both that day and the next are keyed)."""
    R = {}
    f = 'data/processed/game_lines.csv'
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r['season'] != '2026' or not r['home_score']: continue
            a, h = NFLV.get(r['away_team'], r['away_team']), NFLV.get(r['home_team'], r['home_team'])
            d = datetime.fromisoformat(r['gameday']).date()
            for dd in (d, d.fromordinal(d.toordinal() + 1)):           # slate dates are UTC: a Sunday night game is Monday UTC
                R[f"nfl|{a}|{h}|{dd.isoformat()}"] = (float(r['away_score']), float(r['home_score']))
    f = 'ncaa/data/processed/games_2026.csv'                                   # FBS finals (ESPN abbreviations already)
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r['completed'] != '1' or r['vis_pts'] == '' or r['home_pts'] == '': continue
            R[f"cfb|{r['vis']}|{r['home']}|{r['kick_utc'][:10]}"] = (float(r['vis_pts']), float(r['home_pts']))
    return R

def norm_name(n): return re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n.lower()))

def prop_results(days=28):
    """Player box lines for grading prop plays: {league: {date: {player: [pass_yds, pass_td, completions, pass_att, rush_yds, rush_att, receptions, rec_yds, anytime_td]}}} — last `days` of games."""
    out = {}; since = (datetime.now() - timedelta(days=days)).date().isoformat()
    for f, lg in (('data/game_logs/game_logs_2026.csv', 'nfl'), ('ncaa/data/game_logs/game_logs_2026.csv', 'cfb')):
        if not os.path.exists(f): continue
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r['date'] < since: continue
            v = lambda k: float(r[k] or 0)
            out.setdefault(lg, {}).setdefault(r['date'], {})[norm_name(r['player'])] = [v('pass_yds'), v('pass_td'), v('cmp'), v('pass_att'), v('rush_yds'), v('rush_att'), v('rec'), v('rec_yds'), 1 if v('rush_td') + v('rec_td') > 0 else 0]
    return out

HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">"""
CSS = """
:root{--bg:#000;--panel:#0b0b0c;--s2:#131315;--s3:#1a1a1d;--edge:#1d1e21;--edge2:#2a2b30;--fg:#e6e6e9;--dim:#8b8d94;--mute:#5c5e66;--acc:#e8b339;--green:#3fb950;--red:#f0564a;--blue:#58a6ff;--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;--sans:'Inter',system-ui,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:13px;line-height:1.45}a{color:inherit;text-decoration:none}
#hdr{display:flex;align-items:center;gap:16px;padding:10px 24px;border-bottom:1px solid var(--edge);background:#050506;position:sticky;top:0;z-index:5}.brand{font:800 15px/1 var(--mono);letter-spacing:4px}.brand i{color:var(--acc);font-style:normal;margin-right:6px}.tag{color:var(--dim);font-size:12px}#hdr .right{margin-left:auto;color:var(--mute);font:500 10.5px var(--mono)}
.hl{display:flex;gap:4px;margin-left:10px}.hl a{font:600 10px var(--mono);letter-spacing:1px;padding:3px 9px;border:1px solid var(--edge2);border-radius:4px;color:var(--dim)}.hl a:hover,.hl a.on{color:var(--fg);border-color:var(--acc)}
.wrap{max-width:1500px;margin:0 auto;padding:16px 24px 40px}h1{font:800 24px/1.15 var(--sans);letter-spacing:-.3px;margin:4px 0 2px}h1 small{display:block;font:400 12.5px/1.5 var(--sans);color:var(--dim);margin-top:5px;max-width:980px}
h2{font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin:22px 0 10px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}h2 span{font:400 11.5px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}h2 .sp{flex:1}
.pintro{display:flex;flex-direction:column;gap:5px;padding:10px 12px;margin:12px 0;background:var(--panel);border:1px solid var(--edge);border-left:3px solid var(--acc);border-radius:8px}.pintro .pw{font-size:12.5px;line-height:1.45}.pintro .pw b{color:var(--acc)}.pintro .ph{display:flex;flex-wrap:wrap;gap:4px 6px}.pintro .ph span{font:500 10.5px/1.5 var(--mono);color:var(--dim);background:var(--s2);border:1px solid var(--edge);border-radius:4px;padding:0 7px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}.card{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:12px 14px}.card h3{margin:0 0 8px;font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);display:flex;justify-content:space-between;gap:8px;align-items:baseline}.card h3 span{font:400 11px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}.kpi{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:10px 12px}.kpi b{display:block;font:700 20px/1.1 var(--mono)}.kpi span{display:block;font:600 9.5px var(--mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--mute);margin-bottom:4px}.kpi small{color:var(--dim);font-size:11px}.g{color:var(--green)}.r{color:var(--red)}.a{color:var(--acc)}
.prof{display:flex;align-items:center;gap:12px}.av{width:44px;height:44px;border-radius:50%;background:var(--s3);border:2px solid var(--acc);display:flex;align-items:center;justify-content:center;font:800 18px var(--mono);color:var(--acc)}.prof input{background:var(--s2);border:1px solid var(--edge2);color:var(--fg);border-radius:5px;padding:5px 8px;font:600 13px var(--sans);width:180px}
.srcs{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.src{display:inline-flex;align-items:center;gap:6px;font:600 10.5px var(--mono);padding:3px 8px;border-radius:5px;border:1px solid var(--edge2);background:var(--s2);color:var(--dim)}.src i{width:7px;height:7px;border-radius:50%;background:var(--mute);display:inline-block}.src.ok i{background:var(--green)}.src.soon i{background:var(--acc)}
form.add{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:6px;align-items:end}form.add label{display:flex;flex-direction:column;gap:3px;font:600 9.5px var(--mono);letter-spacing:1px;text-transform:uppercase;color:var(--mute)}form.add input,form.add select{background:var(--s2);border:1px solid var(--edge2);color:var(--fg);border-radius:5px;padding:6px 8px;font:500 12px var(--sans);min-width:0}form.add button,.btn{background:var(--acc);color:#000;border:0;border-radius:5px;padding:7px 12px;font:700 11px var(--mono);letter-spacing:1px;cursor:pointer}.btn.ghost{background:transparent;color:var(--dim);border:1px solid var(--edge2)}.btn.ghost:hover{color:var(--fg);border-color:var(--fg)}
.drafts{display:flex;flex-direction:column;gap:6px}.draft{display:grid;grid-template-columns:1fr auto auto auto;gap:8px;align-items:center;padding:6px 8px;border:1px dashed var(--edge2);border-radius:7px;font-size:12px}.draft b{font-family:var(--mono)}.draft input{width:70px;background:var(--s2);border:1px solid var(--edge2);color:var(--fg);border-radius:4px;padding:4px 6px;font:600 11px var(--mono)}
table{border-collapse:collapse;width:100%;font-size:12px}th{font:600 9.5px var(--mono);letter-spacing:1px;text-transform:uppercase;color:var(--mute);text-align:left;padding:6px 8px;border-bottom:1px solid var(--edge2);cursor:pointer;white-space:nowrap}th.srt-asc::after{content:' ▲'}th.srt-desc::after{content:' ▼'}td{padding:6px 8px;border-bottom:1px solid var(--edge);white-space:nowrap;vertical-align:middle}tr:hover td{background:var(--s2)}.mono{font-family:var(--mono)}.dim{color:var(--dim)}.tm{display:inline-flex;align-items:center;gap:5px}.tm img{width:16px;height:16px;object-fit:contain}
.st{font:700 9.5px var(--mono);letter-spacing:1px;padding:2px 6px;border-radius:4px}.st.open{background:var(--s3);color:var(--dim)}.st.won{background:rgba(63,185,80,.18);color:var(--green)}.st.lost{background:rgba(240,86,74,.18);color:var(--red)}.st.push{background:rgba(88,166,255,.18);color:var(--blue)}
.gr{display:inline-flex;gap:3px}.gr button{font:700 9.5px var(--mono);padding:2px 6px;border-radius:4px;border:1px solid var(--edge2);background:var(--panel);color:var(--dim);cursor:pointer}.gr button:hover{color:var(--fg);border-color:var(--fg)}
.wk{display:flex;align-items:flex-end;gap:6px;height:110px;padding:6px 0 0}.wk .b{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;gap:3px}.wk .b i{display:block;width:100%;max-width:46px;border-radius:3px 3px 0 0;background:var(--green)}.wk .b i.n{background:var(--red)}.wk .b small{font:500 9.5px var(--mono);color:var(--mute)}.wk .b b{font:600 10px var(--mono)}
.lb{display:flex;flex-direction:column;gap:5px}.lbr{display:grid;grid-template-columns:26px 1fr 1.2fr auto;gap:8px;align-items:center;padding:5px 8px;border:1px solid var(--edge);border-radius:7px;background:var(--panel)}.lbr.me{border-color:var(--acc)}.lbr .i{font:700 12px var(--mono);color:var(--mute)}.lbr .who{display:flex;align-items:center;gap:8px}.lbr .who .av{width:26px;height:26px;font-size:11px;border-width:1px}.lbr .bar{height:8px;background:var(--s3);border-radius:2px;position:relative}.lbr .bar i{position:absolute;top:0;bottom:0;background:var(--green);border-radius:2px}.lbr .bar i.n{background:var(--red)}.lbr .n{font:700 12px var(--mono);text-align:right}.lbr .n small{display:block;font-weight:500;color:var(--dim);font-size:10px}
.feed{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px}.post{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:10px 12px;display:flex;flex-direction:column;gap:5px}.post .ph2{display:flex;align-items:center;gap:8px;font-size:12px}.post .ph2 .av{width:24px;height:24px;font-size:10px;border-width:1px}.post .ph2 small{color:var(--mute);margin-left:auto;font:500 10px var(--mono)}.post .pk{font:600 13px var(--sans)}.post .pk b{font-family:var(--mono);color:var(--acc)}.post .pm{display:flex;gap:8px;align-items:center;font:500 10.5px var(--mono);color:var(--dim)}.post .note{color:var(--dim);font-size:12px;font-style:italic}
.empty{color:var(--mute);padding:12px;border:1px dashed var(--edge2);border-radius:8px;text-align:center}.toast{position:fixed;right:18px;bottom:18px;background:#15140f;border:1px solid var(--acc);color:var(--fg);padding:8px 12px;border-radius:8px;font:600 11px var(--mono);display:none;z-index:9}
.foot{margin-top:26px;padding-top:12px;border-top:1px solid var(--edge);color:var(--mute);font:400 11px/1.6 var(--sans)}
"""
JS = r"""
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TZ='America/Chicago';const CT=d=>new Date(d).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:TZ}).replace(':00','');
const GAMES=J.games;const GBY={};GAMES.forEach(g=>GBY[g.id]=g);const RES=J.results;
const logo=l=>l?`<img src="https://a.espncdn.com/i/teamlogos/${l}" alt="" onerror="this.style.visibility='hidden'">`:'';
const am=d=>d>=2?'+'+Math.round((d-1)*100):String(Math.round(-100/(d-1)));const dec=a=>{a=+a;return a>0?1+a/100:1+100/-a};
const LS=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}};const SV=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let PROF=LS('rainman.profile',{name:''}),BETS=LS('rainman.bets',[]),FR=LS('rainman.friends',[]);const plays=()=>LS('rainman.plays',[]);
const wkOf=d=>{const x=new Date(d);const t=new Date(Date.UTC(x.getFullYear(),x.getMonth(),x.getDate()));const day=t.getUTCDay()||7;t.setUTCDate(t.getUTCDate()+4-day);const y0=new Date(Date.UTC(t.getUTCFullYear(),0,1));return t.getUTCFullYear()+'-W'+String(Math.ceil(((t-y0)/864e5+1)/7)).padStart(2,'0')};
const toast=m=>{const t=$('#toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(()=>t.style.display='none',1800)};
// ---- grading: NFL finals (others graded by hand)
function grade(b){const g=b.gid&&GBY[b.gid];const key=g?`${g.lg}|${g.away}|${g.home}|${g.date.slice(0,10)}`:'';const r=RES[key];if(!r)return null;const [as,hs]=r;const pt=+b.point||0;
  if(b.market==='moneyline'){if(as===hs)return 'push';return (b.selection===g.away?as>hs:hs>as)?'won':'lost'}
  if(b.market==='spread'){const m=(b.selection===g.away?as-hs:hs-as)+pt;return m>0?'won':m<0?'lost':'push'}
  if(b.market==='total'){const t=as+hs;if(t===pt)return 'push';return (b.selection==='Over'?t>pt:t<pt)?'won':'lost'}
  if(b.market==='prop'&&b.player&&b.stat){const idx={pass_yds:0,pass_td:1,completions:2,pass_att:3,rush_yds:4,rush_att:5,receptions:6,rec_yds:7,anytime_td:8}[b.stat];if(idx==null)return null;const nn=b.player.toLowerCase().replace(/\b(jr|sr|ii|iii|iv)\b/g,'').replace(/[^a-z]/g,'');const d0=new Date(g.date);
    for(const off of [-1,0,1]){const d=new Date(d0.getTime()+off*864e5).toISOString().slice(0,10);const row=((J.props[g.lg]||{})[d]||{})[nn];if(row){const v=row[idx];if(b.stat==='anytime_td')return (b.side==='Yes'||b.selection.endsWith('Yes'))?(v?'won':'lost'):(v?'lost':'won');if(v===pt)return 'push';const over=b.side==='Over'||/\bOver\b/.test(b.selection);return (over?v>pt:v<pt)?'won':'lost'}}
    return null}
  return null}
const pnl=b=>b.status==='won'?+(b.stake*(b.dec-1)).toFixed(2):b.status==='lost'?-b.stake:0;
function autograde(){let n=0;BETS.forEach(b=>{if(b.status==='open'){const s=grade(b);if(s){b.status=s;b.auto=true;n++}}});if(n){SV('rainman.bets',BETS)}}
// ---- profile
function profile(){const el=$('#prof');el.innerHTML=`<div class="prof"><div class="av">${esc((PROF.name||'?')[0].toUpperCase())}</div><div><input id="pname" placeholder="your handle" value="${esc(PROF.name)}"><div class="dim" style="font-size:11px;margin-top:3px">shown on the leaderboard and on plays you share</div></div></div>
  <div class="srcs"><span class="src ok"><i></i>manual entry</span><span class="src ok"><i></i>Arb Engine saves</span><span class="src soon"><i></i>Kalshi import · coming</span><span class="src soon"><i></i>Polymarket wallet · coming</span><span class="src"><i></i>DraftKings / FanDuel · no account API, log by hand</span></div>`;
  $('#pname').onchange=e=>{PROF.name=e.target.value.trim();SV('rainman.profile',PROF);render()}}
// ---- add a play
function addForm(){const el=$('#add');const lgs=[...new Set(GAMES.map(g=>g.lg))];
  el.innerHTML=`<form class="add" id="f"><label>league<select name="lg">${lgs.map(l=>`<option>${l}</option>`).join('')}</select></label><label>game<select name="gid"></select></label><label>market<select name="market"><option>moneyline</option><option>spread</option><option>total</option><option>prop</option><option>parlay</option></select></label><label>pick<input name="selection" placeholder="team / Over / player" required></label><label>line<input name="point" placeholder="-3.5 / 45.5 / 249.5"></label><label>odds (american)<input name="odds" placeholder="-110" required></label><label>stake<input name="stake" type="number" step="1" placeholder="units or $" required></label><label>book<select name="source"><option>DK</option><option>FD</option><option>KAL</option><option>POLY</option><option>other</option></select></label><label>note<input name="note" placeholder="why (optional)"></label><button type="submit">log play</button></form>`;
  const f=$('#f');const fill=()=>{const lg=f.lg.value;f.gid.innerHTML=GAMES.filter(g=>g.lg===lg).map(g=>`<option value="${g.id}">${g.away} @ ${g.home} · ${CT(g.date)}</option>`).join('')};fill();f.lg.onchange=fill;
  f.onsubmit=e=>{e.preventDefault();const g=GBY[f.gid.value];const d=dec(f.odds.value);if(!(d>1)){toast('odds?');return}BETS.push({id:'b'+Date.now(),lg:f.lg.value,gid:g.id,game:g.away+' @ '+g.home,kickoff:g.date,market:f.market.value,selection:f.selection.value.trim(),point:f.point.value.trim(),dec:+d.toFixed(4),american:am(d),stake:+f.stake.value,source:f.source.value,note:f.note.value.trim(),status:'open',placed:new Date().toISOString(),shared:true});SV('rainman.bets',BETS);f.reset();fill();toast('logged');render()}}
// ---- drafts saved from the Arb Engine
function drafts(){const P=plays().filter(p=>p.status==='open');const el=$('#drafts');if(!P.length){el.innerHTML='<div class="empty">nothing saved yet — click any price on the Arb Engine to park it here, then set a stake to log it</div>';return}
  el.innerHTML=P.map(p=>`<div class="draft" data-id="${esc(p.id)}"><span>${esc(p.game)} · <b>${esc(p.selection)}${p.market==='spread'?' '+(+p.point>0?'+':'')+p.point:p.market==='total'?' '+p.point:''}</b> <span class="dim">${p.market} · ${esc(p.source)} ${esc(p.american)} · ${CT(p.kickoff)}</span></span><input type="number" placeholder="stake" step="1"><button class="btn">log</button><button class="btn ghost">drop</button></div>`).join('');
  el.querySelectorAll('.draft').forEach(d=>{const id=d.dataset.id;const p=P.find(x=>x.id===id);d.querySelector('.btn:not(.ghost)').onclick=()=>{const st=+d.querySelector('input').value;if(!st){toast('stake?');return}const gid=(GAMES.find(g=>g.lg===p.league&&g.away+' @ '+g.home===p.game&&g.date===p.kickoff)||{}).id;BETS.push({id:'b'+Date.now(),lg:p.league,gid,game:p.game,kickoff:p.kickoff,market:p.market,selection:p.selection,point:p.point,player:p.player||'',stat:p.stat||'',side:p.side||'',dec:+p.dec,american:p.american,stake:st,source:p.source,note:p.fair?`fair ${(100*p.fair).toFixed(1)}% on the Arb Engine`:'from the Arb Engine',status:'open',placed:new Date().toISOString(),shared:true});const all=plays();const i=all.findIndex(x=>x.id===id);if(i>=0)all[i].status='logged';SV('rainman.plays',all);SV('rainman.bets',BETS);toast('logged');render()};
    d.querySelector('.ghost').onclick=()=>{SV('rainman.plays',plays().filter(x=>x.id!==id));render()}})}
// ---- stats + ledger
function stats(){const g=BETS.filter(b=>b.status!=='open');const w=g.filter(b=>b.status==='won').length,l=g.filter(b=>b.status==='lost').length,p=g.filter(b=>b.status==='push').length;const units=g.reduce((s,b)=>s+pnl(b),0),risk=g.reduce((s,b)=>s+b.stake,0);
  const wk=wkOf(new Date());const tw=BETS.filter(b=>b.status!=='open'&&wkOf(b.kickoff)===wk).reduce((s,b)=>s+pnl(b),0);
  $('#kpis').innerHTML=`<div class="kpi"><span>record</span><b>${w}-${l}${p?'-'+p:''}</b><small>${BETS.filter(b=>b.status==='open').length} open</small></div><div class="kpi ${units>=0?'g':'r'}"><span>units</span><b>${units>=0?'+':''}${units.toFixed(2)}</b><small>roi ${risk?((100*units/risk).toFixed(1)+'%'):'—'}</small></div><div class="kpi ${tw>=0?'g':'r'}"><span>this week</span><b>${tw>=0?'+':''}${tw.toFixed(2)}</b><small>${wk} · the leaderboard week</small></div><div class="kpi"><span>win rate</span><b>${w+l?(100*w/(w+l)).toFixed(0)+'%':'—'}</b><small>break-even at −110 is 52.4%</small></div><div class="kpi a"><span>avg odds</span><b>${g.length?am(g.reduce((s,b)=>s+b.dec,0)/g.length):'—'}</b><small>graded plays</small></div>`;
  // weekly bars
  const byW={};BETS.filter(b=>b.status!=='open').forEach(b=>{const k=wkOf(b.kickoff);byW[k]=(byW[k]||0)+pnl(b)});const ks=Object.keys(byW).sort().slice(-10);const mx=Math.max(1,...ks.map(k=>Math.abs(byW[k])));
  $('#weekly').innerHTML=ks.length?`<div class="wk">${ks.map(k=>`<div class="b"><b class="${byW[k]>=0?'g':'r'}">${byW[k]>=0?'+':''}${byW[k].toFixed(1)}</b><i class="${byW[k]<0?'n':''}" style="height:${Math.max(3,80*Math.abs(byW[k])/mx).toFixed(0)}px"></i><small>${k.slice(5)}</small></div>`).join('')}</div>`:'<div class="empty">weekly units appear once plays are graded</div>'}
let SK='kickoff',SA=false;
function ledger(){const V={kickoff:b=>b.kickoff,game:b=>b.game,market:b=>b.market,pick:b=>b.selection,odds:b=>b.dec,stake:b=>b.stake,src:b=>b.source,status:b=>b.status,pnl:b=>pnl(b)};const rows=BETS.slice().sort((a,b)=>{const x=V[SK](a),y=V[SK](b);return (x<y?-1:x>y?1:0)*(SA?1:-1)});
  const th=(k,l)=>`<th data-k="${k}" class="${SK===k?(SA?'srt-asc':'srt-desc'):''}">${l}</th>`;
  $('#ledger').innerHTML=rows.length?`<table><thead><tr>${th('kickoff','kick (CT)')}${th('game','game')}${th('market','market')}${th('pick','pick')}${th('odds','odds')}${th('stake','stake')}${th('src','book')}${th('status','result')}${th('pnl','+/−')}<th>grade</th><th></th></tr></thead><tbody>${rows.map(b=>{const g=GBY[b.gid]||{};return `<tr><td class="mono dim">${CT(b.kickoff)}</td><td><span class="tm">${logo(g.al)}${esc(b.game)}${logo(g.hl)}</span></td><td class="dim">${esc(b.market)}</td><td><b>${esc(b.selection)}${b.point?' '+(b.market==='spread'&&+b.point>0?'+':'')+esc(b.point):''}</b>${b.note?` <span class="dim" title="${esc(b.note)}">ⓘ</span>`:''}</td><td class="mono">${esc(b.american)}</td><td class="mono">${b.stake}</td><td class="dim">${esc(b.source)}</td><td><span class="st ${b.status}">${b.status.toUpperCase()}</span>${b.auto?' <span class="dim" title="graded from the final score">auto</span>':''}</td><td class="mono ${pnl(b)>0?'g':pnl(b)<0?'r':'dim'}">${b.status==='open'?'':(pnl(b)>=0?'+':'')+pnl(b).toFixed(2)}</td><td><span class="gr">${['won','lost','push','open'].map(s=>`<button data-id="${b.id}" data-s="${s}">${s[0].toUpperCase()}</button>`).join('')}</span></td><td><button class="btn ghost" data-del="${b.id}">×</button></td></tr>`}).join('')}</tbody></table>`:'<div class="empty">no plays logged yet</div>';
  $('#ledger').querySelectorAll('th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(SK===k)SA=!SA;else{SK=k;SA=false}ledger()});
  $('#ledger').querySelectorAll('.gr button').forEach(x=>x.onclick=()=>{const b=BETS.find(y=>y.id===x.dataset.id);b.status=x.dataset.s;b.auto=false;SV('rainman.bets',BETS);render()});
  $('#ledger').querySelectorAll('[data-del]').forEach(x=>x.onclick=()=>{BETS=BETS.filter(y=>y.id!==x.dataset.del);SV('rainman.bets',BETS);render()})}
// ---- leaderboard (weekly units) — you + everyone you imported
function entries(){const wk=wkOf(new Date());const me={name:PROF.name||'you',bets:BETS,me:true};return [me,...FR].map(e=>{const g=e.bets.filter(b=>b.status!=='open');const week=g.filter(b=>wkOf(b.kickoff)===wk);const u=x=>x.reduce((s,b)=>s+pnl(b),0);return {name:e.name,me:!!e.me,week:u(week),all:u(g),w:g.filter(b=>b.status==='won').length,l:g.filter(b=>b.status==='lost').length,n:week.length}}).sort((a,b)=>b.week-a.week||b.all-a.all)}
function leaderboard(){const E=entries();const mx=Math.max(1,...E.map(e=>Math.abs(e.week)));$('#lb').innerHTML=E.map((e,i)=>`<div class="lbr ${e.me?'me':''}"><span class="i">${i+1}</span><span class="who"><span class="av">${esc((e.name||'?')[0].toUpperCase())}</span><b>${esc(e.name)}</b><span class="dim" style="font:500 10px var(--mono)">${e.w}-${e.l} all-time</span></span><span class="bar"><i class="${e.week<0?'n':''}" style="left:${e.week<0?50-50*Math.abs(e.week)/mx:50}%;width:${50*Math.abs(e.week)/mx}%"></i></span><span class="n ${e.week>=0?'g':'r'}">${e.week>=0?'+':''}${e.week.toFixed(2)}<small>${e.n} graded this week</small></span></div>`).join('')}
// ---- feed: shared plays (yours + imported), tail = copy to your drafts
function feed(){const posts=[];const wk=wkOf(new Date());BETS.filter(b=>b.shared).forEach(b=>posts.push({who:PROF.name||'you',me:true,b}));FR.forEach(f=>f.bets.forEach(b=>posts.push({who:f.name,b})));posts.sort((a,b)=>b.b.placed<a.b.placed?-1:1);
  $('#feed').innerHTML=posts.length?posts.slice(0,40).map(({who,me,b})=>`<div class="post"><div class="ph2"><span class="av">${esc(who[0].toUpperCase())}</span><b>${esc(who)}</b><small>${CT(b.placed)}</small></div><div class="pk">${esc(b.game)} — <b>${esc(b.selection)}${b.point?' '+(b.market==='spread'&&+b.point>0?'+':'')+esc(b.point):''}</b> ${esc(b.american)}</div><div class="pm"><span>${esc(b.market)}</span><span>${esc(b.source)}</span><span>${b.stake}u</span><span class="st ${b.status}">${b.status.toUpperCase()}</span>${me?'':`<button class="btn ghost" data-tail="${esc(b.id)}" data-who="${esc(who)}" style="margin-left:auto">tail</button>`}</div>${b.note?`<div class="note">${esc(b.note)}</div>`:''}</div>`).join(''):'<div class="empty">plays you log show up here; import a friend\'s link to see theirs</div>';
  $('#feed').querySelectorAll('[data-tail]').forEach(x=>x.onclick=()=>{const f=FR.find(f=>f.name===x.dataset.who);const b=f&&f.bets.find(y=>y.id===x.dataset.tail);if(!b)return;const all=plays();all.push({id:'t'+Date.now(),league:b.lg,game:b.game,kickoff:b.kickoff,market:b.market,selection:b.selection,point:b.point,source:b.source,dec:b.dec,american:b.american,fair:null,from:'tail:'+f.name,status:'open'});SV('rainman.plays',all);toast('tailed into your drafts');render()})}
// ---- share / import: the link carries your name + plays (compressed JSON in the hash)
function shareLink(){const data={name:PROF.name||'anon',bets:BETS.filter(b=>b.shared).map(b=>({id:b.id,lg:b.lg,game:b.game,kickoff:b.kickoff,market:b.market,selection:b.selection,point:b.point,dec:b.dec,american:b.american,stake:b.stake,source:b.source,status:b.status,placed:b.placed,note:b.note}))};
  const s=btoa(unescape(encodeURIComponent(JSON.stringify(data))));const url=location.origin+location.pathname+'#import='+s;(navigator.clipboard?navigator.clipboard.writeText(url):Promise.reject()).then(()=>toast('share link copied · '+Math.round(url.length/1024)+' KB'),()=>{prompt('copy this link',url)})}
function importHash(){const m=location.hash.match(/import=([^&]+)/);if(!m)return;try{const d=JSON.parse(decodeURIComponent(escape(atob(m[1]))));if(!d.name||!Array.isArray(d.bets))throw 0;FR=FR.filter(f=>f.name!==d.name);FR.push({name:d.name,bets:d.bets,imported:new Date().toISOString()});SV('rainman.friends',FR);history.replaceState(null,'',location.pathname);toast('imported '+d.name+' · '+d.bets.length+' plays')}catch(e){toast('could not read that link')}}
function render(){autograde();profile();drafts();stats();ledger();leaderboard();feed();$('#nfr').textContent=FR.length?FR.length+' imported':''}
importHash();addForm();render();$('#share').onclick=shareLink;$('#exp').onclick=()=>{const blob=new Blob([JSON.stringify({profile:PROF,bets:BETS,friends:FR},null,1)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='rainman-plays.json';a.click()};
$('#imp').onchange=e=>{const f=e.target.files[0];if(!f)return;f.text().then(t=>{const d=JSON.parse(t);if(d.bets){BETS=d.bets;PROF=d.profile||PROF;FR=d.friends||FR;SV('rainman.bets',BETS);SV('rainman.profile',PROF);SV('rainman.friends',FR);render();toast('restored')}})};
$('#wipe').onclick=()=>{if(confirm('clear every play, friend and the profile from this browser?')){['rainman.bets','rainman.plays','rainman.friends','rainman.profile'].forEach(k=>localStorage.removeItem(k));BETS=[];FR=[];PROF={name:''};render()}};
"""

def page(games, results, pulled):
    J = dict(games=games, results={k: list(v) for k, v in results.items()}, props=prop_results(), pulled=pulled)
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · Social</title>{HEAD}<style>{CSS}</style></head><body>
<div id="hdr"><a class="brand" href="index.html"><i>◍</i> RAINMAN</a><span class="tag">Social · plays, records, leaderboard</span><span class="hl"><a href="index.html">all sports</a><a href="arb.html">Arb Engine</a><a class="on" href="social.html">Social</a></span><span class="right"><span id="nfr"></span> · slate {pulled} · built {built}</span></div>
<div class="wrap">
<h1>Your plays. Your record. The board.<small>Log every bet you place — by hand, or straight from the Arb Engine — and the site grades it, tracks your units week by week and ranks you against everyone whose plays you've imported. Share a link and friends can see and tail your plays. Everything here lives in this browser: no account yet, nothing leaves your machine unless you share a link.</small></h1>
<div class="pintro"><div class="pw"><b>How it works</b> — log a play (or set a stake on one saved from the Arb Engine) · NFL game lines grade themselves from the final score, everything else gets the W / L / P buttons · the leaderboard ranks weekly units · <b>share</b> copies a link that carries your plays; open a friend's link to import theirs.</div><div class="ph"><span>units = stake × (odds − 1) on a win, −stake on a loss</span><span>week = Monday to Sunday</span><span>DraftKings and FanDuel have no account feed — log those by hand</span><span>Kalshi / Polymarket imports are next</span><span>backup / restore keeps a JSON copy</span></div></div>
<div class="grid" style="grid-template-columns:1.2fr 2fr"><div class="card"><h3>profile <span>local</span></h3><div id="prof"></div></div><div class="card"><h3>log a play <span>any league on the slate</span></h3><div id="add"></div></div></div>
<h2>saved from the Arb Engine <span>set a stake to move a saved price into the ledger</span></h2><div id="drafts" class="drafts"></div>
<h2>your record <span>graded plays only</span><span class="sp"></span><button id="share" class="btn">share my plays</button> <button id="exp" class="btn ghost">backup</button> <label class="btn ghost" style="cursor:pointer">restore<input id="imp" type="file" accept="application/json" hidden></label> <button id="wipe" class="btn ghost">clear</button></h2>
<div id="kpis" class="kpis"></div>
<div class="grid" style="margin-top:10px;grid-template-columns:1.4fr 1fr"><div class="card"><h3>units by week <span>last ten weeks with graded plays</span></h3><div id="weekly"></div></div><div class="card"><h3>leaderboard <span>this week's units · you + imported friends</span></h3><div id="lb" class="lb"></div></div></div>
<h2>ledger <span>every play · click a header to sort · W / L / P sets the result by hand, × removes</span></h2><div id="ledger"></div>
<h2>feed <span>plays shared by you and the people you've imported · tail copies a play into your drafts</span></h2><div id="feed" class="feed"></div>
<div class="foot">RAINMAN · Social (local prototype) · plays are stored in this browser only; a share link carries a copy of your plays to whoever opens it. Automatic grading uses the finals the site already tracks (NFL now; other leagues as their results feeds land). Bet responsibly.</div></div>
<div id="toast" class="toast"></div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script><script>{JS}</script></body></html>"""

def main():
    games, pulled = slate(); R = results()
    open('dashboard/social.html', 'w', encoding='utf-8').write(page(games, R, pulled))
    print(f'social: {len(games)} games on the picker · {len(R)} finals keyed for grading · dashboard/social.html {os.path.getsize("dashboard/social.html")//1024} KB')

if __name__ == '__main__':
    main()
