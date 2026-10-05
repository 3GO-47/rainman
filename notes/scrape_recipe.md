# RAINMAN scrape recipe (Chrome workflow)

PFR blocks the sandbox network and web_fetch chokes on box score pages, so all PFR scraping
runs through Chrome: same-origin `fetch()` in a pro-football-reference.com tab, parsed in-page,
dumped to the DOM, read out with get_page_text, appended to disk via bash. ESPN depth charts
use the same pattern. Pace ~2s/page, ≤4 pages per JS call, never parallel (PFR jails IPs at
~20 req/min).

## Weekly in-season refresh (Tuesdays) — what to ask Claude
1. "Scrape 2026 week N box scores into RAINMAN" — box ids are PRECOMPUTED in
   data/processed/games_2026.csv. Append parsed lines to data/raw/box_lines_2026.txt,
   checkpoint the week in notes/scrape_state.json (seasons.2026.weeks_done).
2. "Re-pull ESPN depth charts" — write data/raw/espn_depth_YYYY-MM-DD.txt, then
   python3 scripts/build_depth_chart.py <raw> <date>.
3. Once per season (or when rosters churn): pull
   https://www.pro-football-reference.com/years/2026/fantasy.htm -> data/raw/positions_2026.csv
   (pid,pos lines). Until it exists, build_game_logs falls back to prior seasons + inference.
4. python3 scripts/refresh.py    (auto-detects the current week; rebuilds everything)

## The in-page box score parser (define once per tab on any PFR page)
window._acc = window._acc || [];
window.parseBox = async function(bid){
  const r = await fetch('https://www.pro-football-reference.com/boxscores/'+bid+'.htm');
  if(r.status!==200) return ['ERR|'+bid+'|'+r.status];
  const doc = new DOMParser().parseFromString(await r.text(),'text/html');
  const out=[];
  const tbl = doc.querySelector('#player_offense');
  if(!tbl) return ['ERR|'+bid+'|no_table'];
  for(const tr of tbl.querySelectorAll('tbody tr')){
    const th = tr.querySelector('th[data-stat="player"]');
    if(!th || !th.querySelector('a')) continue;
    const href = th.querySelector('a').getAttribute('href')||'';
    const m = href.match(/players\/\w+\/([\w.]+)\.htm/);
    const pid = m ? m[1] : href.replace(/\W/g,'').slice(-10);
    const name = th.textContent.trim();
    const g = s => {const c=tr.querySelector(`[data-stat="${s}"]`); return c?(c.textContent.trim()||'0'):'0';};
    out.push(['P',bid,pid,name,g('team'),g('pass_cmp'),g('pass_att'),g('pass_yds'),g('pass_td'),g('pass_int'),g('rush_att'),g('rush_yds'),g('rush_td'),g('targets'),g('rec'),g('rec_yds'),g('rec_td'),g('fumbles_lost')].join('|'));
  }
  const sc = doc.querySelector('#scoring');
  if(sc){
    const cnt={};
    for(const tr of sc.querySelectorAll('tbody tr')){
      const team=(tr.querySelector('[data-stat="team"]')||{textContent:''}).textContent.trim();
      const desc=(tr.querySelector('[data-stat="description"]')||{textContent:''}).textContent;
      if(/return/i.test(desc) && !/field goal/i.test(desc)) cnt[team]=(cnt[team]||0)+1;
    }
    for(const [t,c] of Object.entries(cnt)) out.push(['D',bid,t,c].join('|'));
  }
  return out;
};

Loop games (≤4 per JS call, 2000ms delay), push into window._acc, then per week:
document.body.innerHTML='<pre>BOX_BEGIN\n'+window._acc.join('\n')+'\nBOX_END</pre>'
-> get_page_text -> append lines between markers to data/raw/box_lines_<season>.txt via
quoted heredoc -> update scrape_state.json -> window._acc=[].
Never return data lines from javascript_tool directly (results truncate ~1.5KB).

## ESPN depth chart parser (per team slug; offense section = the one whose rows include QB)
See scripts/build_depth_chart.py header for the output format: TEAM|POSROW|DEPTH|NAME|TAG.
Team slugs: buf mia ne nyj bal cin cle pit hou ind jax ten den kc lv lac dal nyg phi wsh
chi det gb min atl car no tb ari lar sf sea (note wsh -> normalized to WAS downstream).

## ESPN depth chart parser (verified 2026-09-17, in-page JS on any espn.com tab)
const SL={buf:'BUF',mia:'MIA',ne:'NE',nyj:'NYJ',bal:'BAL',cin:'CIN',cle:'CLE',pit:'PIT',hou:'HOU',ind:'IND',jax:'JAX',ten:'TEN',den:'DEN',kc:'KC',lv:'LV',lac:'LAC',dal:'DAL',nyg:'NYG',phi:'PHI',wsh:'WSH',chi:'CHI',det:'DET',gb:'GB',min:'MIN',atl:'ATL',car:'CAR',no:'NO',tb:'TB',ari:'ARI',lar:'LAR',sf:'SF',sea:'SEA'};
window.parseDepth=function(doc,team){const rt=[...doc.querySelectorAll('.ResponsiveTable')].find(r=>[...r.querySelectorAll('table')[0].querySelectorAll('tbody tr')].some(tr=>tr.textContent.trim()==='QB'));if(!rt)return['ERR|'+team+'|no_offense'];const T=rt.querySelectorAll('table');const pos=[...T[0].querySelectorAll('tbody tr')].map(tr=>tr.textContent.trim());const rows=[...T[1].querySelectorAll('tbody tr')];const out=[];let wr=0;pos.forEach((p,i)=>{let pr=p;if(p==='WR'){wr++;pr='WR'+wr;}const tr=rows[i];if(!tr)return;[...tr.querySelectorAll('td')].forEach((td,d)=>{const a=td.querySelector('a');if(!a)return;out.push([team,pr,d+1,a.textContent.trim(),(td.querySelector('.nfl-injuries-status')||{textContent:''}).textContent.trim()].join('|'));});});return out;};
// loop: fetch('https://www.espn.com/nfl/team/depth/_/name/'+slug) -> DOMParser -> parseDepth(doc,team), 1500ms apart,
// fire-and-forget (evaluate times out at 45s) then poll window._dc; keep only /^[A-Z]+\|(QB|RB|WR\d|TE|FB)\|/ rows.
// Box-score loop: same pattern — start runBatch(ids) without await, poll window._acc / window._done.
// Verify transcription with {lines, chars, sum of charCodes} computed in-page vs python on disk.

## Final-score lines (added 2026-09-29)
parseBox now also emits `S|bid|Away Team Name|pts|Home Team Name|pts` from the .scorebox (build_game_logs ignores S lines;
they cross-check nflverse results). Background tabs throttle timers — keep the PFR tab in the foreground or expect ~1 game/min.

## Game lines / results (no browser needed — cloud)
python3 scripts/fetch_games.py  -> data/raw/nflverse/games.csv (nflverse nfldata; scores, closing spread/total/moneylines,
rest, roof, QBs for every game) -> data/processed/game_lines.csv. Then scripts/build_games.py (run by refresh.py).

## Player prop lines — DraftKings via ESPN's public odds API (in-page JS on any espn.com tab, no key)
1. scoreboard: https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week=W&dates=2026 -> event ids,
   abbreviations, DK spread/total.
2. per event: https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{id}/competitions/{id}/odds/100/propBets?limit=500&page=N
   (provider 100 = DraftKings; pageCount ~3; ALWAYS https — the $ref links are http and get blocked as mixed content).
   Items: type.name (market), athlete.$ref (…/athletes/{espnId}), current.target.value (line), open.target.value. No prices.
3. keep full-game 'Total … (incl. overtime)' markets, dedupe (over/under appear as two identical records), drop kicker markets ->
   lines `GM|eventId|away|home|kickUTC|spread text|total` and `PB|eventId|espnId|typeId|market|line|open|updated`
   -> data/raw/props_2026_wk{W}_{date}.txt (verify lines/chars/charCode-sum) -> python3 scripts/build_props.py
   (espn_id -> pfr_id via data/raw/nflverse/roster_2026.parquet).
Timing: DK posts main props progressively — Tuesday only the early/TNF games have them (6/16 in wk 4); re-pull Fri/Sat for the
full slate. The ledger freezes a lean the first time it is seen and grades it from game logs after the refresh.

## ESPN birthplaces + college venues (Chrome, on demand)
- From an espn.com tab: `fetch('https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes/{espn_id}')`
  -> `.birthPlace {city,state,country}`; ids = nflverse roster espn_id for players with 2025-26 logs or on the depth chart.
- College venue: `.../college-football/teams/{id}` -> `venue.$ref` (switch to https) -> `address {city,state}`.
- javascript_tool output truncates near 1 KB: write results with document.write('<pre>...') and read with get_page_text.
- Save as data/raw/espn_birthplaces_YYYY-MM-DD.txt (`id|city|state|country`) and data/raw/colleges_venues.txt; then
  `python3 scripts/build_connections.py` (needs `pip install geonamescache`).
