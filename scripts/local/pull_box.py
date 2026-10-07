"""Local box-score pull (replaces the Chrome PFR recipe). Appends P| / D| lines for every FINISHED 2026 game that is not yet in
data/raw/box_lines_2026.txt, in exactly the format build_game_logs.py expects:
  P|bid|pid|name|TEAM|cmp|att|payds|patd|int|ratt|ryds|rtd|tgt|rec|recyds|rectd|fl      D|bid|team|return_tds
Source 1: pro-football-reference.com boxscore pages (same ids / numbers as before), fetched one every 4 s with a browser UA.
Source 2 (fallback when PFR refuses or a page is missing): nflverse stats_player_week parquet (identical numbers, ids mapped to
PFR ids through roster_2026.parquet). Finished games come from nflverse nfldata games.csv (scripts/fetch_games.py).
Also refreshes data/raw/positions_2026.csv from the nflverse roster and notes/scrape_state.json (boxscores_done / weeks_done).
Usage: python scripts/local/pull_box.py [--season 2026]"""
import json, os, re, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import get, log, run, ROOT

SEASON = int(sys.argv[sys.argv.index('--season') + 1]) if '--season' in sys.argv else 2026
BOX = f'data/raw/box_lines_{SEASON}.txt'
STATS_URL = 'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{y}.parquet'
LA = {'LA': 'LAR'}

def pfr_box(bid):
    """Parse one PFR boxscore page into P|/D| lines (None if PFR refuses)."""
    from bs4 import BeautifulSoup, Comment
    html = get(f'https://www.pro-football-reference.com/boxscores/{bid}.htm', pace=4.0, retries=2)
    soup = BeautifulSoup(html, 'html.parser')
    def table(tid):
        t = soup.find('table', id=tid)
        if t: return t
        for c in soup.find_all(string=lambda s: isinstance(s, Comment) and f'id="{tid}"' in s):
            t = BeautifulSoup(str(c), 'html.parser').find('table', id=tid)
            if t: return t
        return None
    off = table('player_offense')
    if off is None: return None
    out = []
    for tr in off.select('tbody tr'):
        th = tr.find('th', attrs={'data-stat': 'player'})
        if not th or not th.find('a'): continue
        href = th.find('a').get('href', '')
        m = re.search(r'players/\w+/([\w.]+)\.htm', href)
        pid = m.group(1) if m else re.sub(r'\W', '', href)[-10:]
        def g(s):
            c = tr.find(attrs={'data-stat': s}); v = (c.get_text(strip=True) if c else '') or '0'
            return v
        out.append('|'.join(['P', bid, pid, th.get_text(strip=True), g('team'), g('pass_cmp'), g('pass_att'), g('pass_yds'), g('pass_td'), g('pass_int'),
                             g('rush_att'), g('rush_yds'), g('rush_td'), g('targets'), g('rec'), g('rec_yds'), g('rec_td'), g('fumbles_lost')]))
    sc = table('scoring')
    if sc is not None:
        cnt = {}
        for tr in sc.select('tbody tr'):
            team = tr.find(attrs={'data-stat': 'team'}); desc = tr.find(attrs={'data-stat': 'description'})
            team = team.get_text(strip=True) if team else ''; desc = desc.get_text(' ', strip=True) if desc else ''
            if re.search(r'return', desc, re.I) and not re.search(r'field goal', desc, re.I): cnt[team] = cnt.get(team, 0) + 1
        for t, c in cnt.items(): out.append(f'D|{bid}|{t}|{c}')
    return out

def nflverse_box(missing, games):
    """P|/D| lines for the games in `missing` (list of nfldata rows) from the nflverse weekly stats parquet."""
    f = f'data/raw/nflverse/stats_player_week_{SEASON}.parquet'
    os.makedirs('data/raw/nflverse', exist_ok=True)
    try: open(f, 'wb').write(get(STATS_URL.format(y=SEASON), binary=True, timeout=120))
    except Exception as e:
        log(f'  nflverse stats download failed: {e}')
        if not os.path.exists(f): return [], set()
    s = pd.read_parquet(f)
    ros = pd.read_parquet(f'data/raw/nflverse/roster_{SEASON}.parquet', columns=['gsis_id', 'pfr_id'])
    pfr = dict(ros.dropna().drop_duplicates('gsis_id').values)
    # also learn ids from names already in the box file (keeps a player on one id across sources)
    byname = {}
    if os.path.exists(BOX):
        for l in open(BOX, encoding='utf-8'):
            if l.startswith('P|'):
                p = l.split('|'); byname[(p[3], norm(p[4]))] = p[2]
    want = {g.game_id: g.pfr for g in missing}
    s = s[(s.season_type != 'PRE') & s.game_id.isin(want)]
    out, done = [], set()
    for r in s.itertuples():
        bid = want[r.game_id]; team = LA.get(r.team, r.team)
        if not any([r.attempts, r.carries, r.targets, r.receptions]): continue
        pid = pfr.get(r.player_id) or byname.get((r.player_display_name, team)) or r.player_id
        fl = int((r.sack_fumbles_lost or 0) + (r.rushing_fumbles_lost or 0) + (r.receiving_fumbles_lost or 0))
        out.append('|'.join(str(x) for x in ['P', bid, pid, r.player_display_name, team, int(r.completions or 0), int(r.attempts or 0), int(r.passing_yards or 0), int(r.passing_tds or 0),
                                             int(r.passing_interceptions or 0), int(r.carries or 0), int(r.rushing_yards or 0), int(r.rushing_tds or 0), int(r.targets or 0),
                                             int(r.receptions or 0), int(r.receiving_yards or 0), int(r.receiving_tds or 0), fl]))
        done.add(r.game_id)
    d = s.assign(team=s.team.map(lambda t: LA.get(t, t)), rt=s.def_tds.fillna(0) + s.special_teams_tds.fillna(0) + s.fumble_recovery_tds.fillna(0)).groupby(['game_id', 'team']).rt.sum()
    for (gid, team), c in d.items():
        if c > 0 and gid in done: out.append(f'D|{want[gid]}|{team}|{int(c)}')
    return out, done

def norm(t):
    from importlib import import_module
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    return import_module('build_game_logs').norm_team(t)

def positions():
    """positions_{season}.csv (pid,pos) from the nflverse roster — existing PFR-page entries are kept."""
    ros = pd.read_parquet(f'data/raw/nflverse/roster_{SEASON}.parquet', columns=['pfr_id', 'position'])
    ros = ros[ros.pfr_id.notna() & ros.position.isin(['QB', 'RB', 'WR', 'TE', 'FB'])].drop_duplicates('pfr_id')
    f = f'data/raw/positions_{SEASON}.csv'
    have = dict(l.rstrip('\n').split(',')[:2] for l in open(f, encoding='utf-8') if ',' in l) if os.path.exists(f) else {}
    new = {r.pfr_id: r.position for r in ros.itertuples() if r.pfr_id not in have}
    if new:
        with open(f, 'a', encoding='utf-8') as fh:
            for k, v in new.items(): fh.write(f'{k},{v}\n')
    log(f'  positions_{SEASON}.csv: +{len(new)} from roster ({len(have) + len(new)} total)')

def main():
    run(['scripts/fetch_games.py'])                       # nfldata games.csv: scores + pfr boxscore ids
    g = pd.read_csv('data/raw/nflverse/games.csv')
    g = g[(g.season == SEASON) & (g.game_type != 'PRE') & g.result.notna() & g.pfr.notna()]
    have = set()
    if os.path.exists(BOX):
        have = {l.split('|')[1] for l in open(BOX, encoding='utf-8') if l.startswith('P|')}
    missing = [r for r in g.itertuples() if r.pfr not in have]
    log(f'box {SEASON}: {len(g)} finished games · {len(have)} already pulled · {len(missing)} to pull')
    if not missing:
        positions(); return 0
    lines, done, pfr_ok = [], set(), True
    for r in missing:
        if not pfr_ok: break
        try:
            out = pfr_box(r.pfr)
            if out is None: log(f'  {r.pfr}: no offense table'); continue
            lines += out; done.add(r.game_id); log(f'  {r.pfr}: {len(out)} lines (PFR)')
        except Exception as e:
            log(f'  {r.pfr}: PFR failed ({str(e)[:80]}) — switching to nflverse for the rest'); pfr_ok = False
    rest = [r for r in missing if r.game_id not in done]
    if rest:
        nl, nd = nflverse_box(rest, g)
        if nd: log(f'  nflverse: {len(nd)}/{len(rest)} games ({len(nl)} lines)')
        lines += nl; done |= nd
    if lines:
        with open(BOX, 'a', encoding='utf-8') as fh: fh.write('\n'.join(lines) + '\n')
    # scrape_state: boxscores_done + weeks_done (a week is done when every game of it is in the file)
    st = json.load(open('notes/scrape_state.json'))
    ss = st['seasons'].setdefault(str(SEASON), {'status': 'in_progress', 'weeks_done': [], 'boxscores_done': []})
    pulled = have | {r.pfr for r in g.itertuples() if r.game_id in done}
    ss['boxscores_done'] = sorted(pulled)
    allg = pd.read_csv('data/raw/nflverse/games.csv'); allg = allg[(allg.season == SEASON) & (allg.game_type == 'REG')]
    ss['weeks_done'] = sorted(int(w) for w, grp in allg.groupby('week') if grp.pfr.notna().all() and set(grp.pfr) <= pulled)
    json.dump(st, open('notes/scrape_state.json', 'w'), indent=1)
    positions()
    log(f'box {SEASON}: +{len(done)} games · weeks complete {ss["weeks_done"][-1] if ss["weeks_done"] else 0} · still missing {len(missing) - len(done)}')
    return len(done)

if __name__ == '__main__':
    main()
