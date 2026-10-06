"""Assemble dashboard/rainman.html from scripts/dashboard_template.html + embedded JSON.
Usage: python3 build_dashboard.py
Every number traces to data/game_logs/ via the derived CSVs. Rerun after any data refresh.
"""
import re, csv, glob, json, os, sys, datetime
import pandas as pd
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LEAGUE = sys.argv[sys.argv.index('--league') + 1] if '--league' in sys.argv else 'nfl'

STAT_COLS = ['QB PY','P TD','QB RY','RB1 RY','RB2+ RY','WR RY','RB1 Recep','RB1 RecY',
 'RB2 Recep','RB2 RecY','WR1 Recep','WR1 RecY','WR2 Recep','WR2 RecY','WR3 Recep','WR3 RecY',
 'WR4+ Recep','WR4+ RecY','TE1 Recep','TE1 RecY','TE2 Recep','TE2 RecY','QB TD','RB1 TD',
 'RB2 TD','WR1 TD','WR2 TD','WR3 TD','WR4+ TD','TE1 TD','TE2 TD','D/ST TD','QB P+R','RB R+R']
SLOTS = ['QB','RB1','RB2','WR1','WR2','WR3','WR4+','TE1','TE2','D/ST']
GROUP_STATS = {'QB':['QB PY','QB RY','QB P+R','P TD','QB TD'],
 'RB1':['RB1 RY','RB1 Recep','RB1 RecY','RB R+R','RB1 TD'],
 'RB2':['RB2+ RY','RB2 Recep','RB2 RecY','RB R+R','RB2 TD'],
 'WR1':['WR1 Recep','WR1 RecY','WR1 TD'],'WR2':['WR2 Recep','WR2 RecY','WR2 TD'],
 'WR3':['WR3 Recep','WR3 RecY','WR3 TD'],'WR4+':['WR4+ Recep','WR4+ RecY','WR4+ TD'],
 'TE1':['TE1 Recep','TE1 RecY','TE1 TD'],'TE2':['TE2 Recep','TE2 RecY','TE2 TD'],
 'D/ST':['D/ST TD']}
PRIMARY = {'QB':'QB PY','RB1':'RB1 RY','RB2':'RB2+ RY','WR1':'WR1 RecY','WR2':'WR2 RecY',
 'WR3':'WR3 RecY','WR4+':'WR4+ RecY','TE1':'TE1 RecY','TE2':'TE2 RecY','D/ST':'D/ST TD'}

def dvp_table(path):
    df = pd.read_csv(path)
    out = {}
    for _, r in df.iterrows():
        d = r['defense']
        out[d] = {'stats': {c: {'avg': round(float(r[c+' avg']), 2), 'rank': float(r[c+' rank'])}
                            for c in STAT_COLS},
                  'comps': {s: float(r[s+' *']) for s in SLOTS if (s+' *') in df.columns}}
    return out

COV_COLS = ['man_rate','zone_rate','cover0','cover1','cover2','cover3','cover4','cover6','two_man','cover_other','single_high','two_high',
            'base_rate','nickel_rate','dime_rate','four_down_rate','pressure_rate']
def intel_payload():
    """Scheme / tendency / turnover / coaching layer from build_advanced.py outputs (nflverse + FTN charting)."""
    P = 'data/processed/'
    if not os.path.exists(P + 'scheme_tags.csv'): return None
    def num(v, d=3):
        if v is None or v == '' or v == 'nan': return None
        if v in ('True', 'False'): return v == 'True'
        try: return round(float(v), d)
        except ValueError: return v
    def by_season_team(path, keys=('season', 'team'), side=None):
        out = {}
        for r in csv.DictReader(open(path, encoding='utf-8')):
            d = out.setdefault(r['season'], {}).setdefault(r['team'], {})
            row = {k: (v if k in ('coverage_source','evidence','descriptors','primary_tag','coach','coach_from','departed','new_starters','cur_starter_names',
                                 'hc','oc','dc','hc_prev','oc_prev','dc_prev','hc_from','oc_from','dc_from','side','team','season') else num(v))
                   for k, v in r.items() if k not in keys}
            if side and 'side' in r: d[r['side']] = row
            else: d.update(row)
        return out
    intel = {'off': by_season_team(P + 'team_off_tendencies.csv'),
             'def': by_season_team(P + 'team_def_tendencies.csv'),
             'tags': by_season_team(P + 'scheme_tags.csv', side=True),
             'turnover': by_season_team(P + 'starter_turnover.csv', side=True) if os.path.exists(P + 'starter_turnover.csv') else {},
             'coaching': by_season_team(P + 'coaching.csv') if os.path.exists(P + 'coaching.csv') else {},
             'schemeSlot': [{k: num(v, 2) if k not in ('family', 'grp') else v for k, v in r.items()}
                            for r in csv.DictReader(open(P + 'scheme_slot_effects.csv', encoding='utf-8'))] if os.path.exists(P + 'scheme_slot_effects.csv') else []}
    # coverage for uncharted seasons: mirror the same fallback tag_defense used (new DC's prior unit, else same team prior season)
    for s in sorted(intel['def']):
        for t, row in intel['def'][s].items():
            if row.get('coverage_charted') is True and row.get('two_high') is not None: continue
            src = (intel['tags'].get(s, {}).get(t, {}).get('DEF') or {}).get('coverage_source', '')
            m = re.search(r'^(\d{4}) charting.*prior unit \((\w+)\)', src) or re.search(r'^(\d{4}) charting', src)
            if not m: continue
            ss, st = m.group(1), (m.group(2) if m.lastindex == 2 else t)
            base = intel['def'].get(ss, {}).get(st)
            if not base: continue
            for c in COV_COLS: row[c] = base.get(c)
            row['cov_est'] = f'{ss} {st}'
    return intel

def bets_payload():
    """Game model + frozen picks ledger + player-prop lines (build_games.py / build_props.py)."""
    P = 'data/processed/'
    if not os.path.exists(P + 'game_model.csv'): return None
    def rows(path, keep=None):
        out = []
        for r in csv.DictReader(open(path, encoding='utf-8')):
            if keep and not keep(r): continue
            o = {}
            for k, v in r.items():
                if v in ('', 'nan'): o[k] = None
                else:
                    try: o[k] = round(float(v), 3) if ('.' in v or v.lstrip('-').isdigit()) and k not in ('game_id','pfr','pick_ats','pick_total','pick_ml','res_ats','res_total','res_ml','frozen_on','result','lean','market','stat_cols','updated','kick','event','pfr_id') else v
                    except ValueError: o[k] = v
            out.append(o)
        return out
    gm = rows(P + 'game_model.csv', lambda r: r['season'] == '2026')
    bt = [r for r in csv.DictReader(open(P + 'game_model.csv', encoding='utf-8')) if r['season'] in ('2024', '2025') and r['result'] not in ('', 'nan') and r['model_spread'] not in ('', 'nan')]
    def rec(rs, col): return {'W': sum(r[col] == 'W' for r in rs), 'L': sum(r[col] == 'L' for r in rs), 'P': sum(r[col] == 'PUSH' for r in rs)}
    mae = lambda rs, col: round(sum(abs(float(r[col]) - float(r['result'])) for r in rs) / max(1, len(rs)), 2)
    backtest = {'n': len(bt), 'ats': rec(bt, 'res_ats'), 'total': rec(bt, 'res_total'), 'mae_model': mae(bt, 'model_spread'), 'mae_market': mae(bt, 'spread_line'),
                'mae_total_model': round(sum(abs(float(r['model_total']) - float(r['total'])) for r in bt) / max(1, len(bt)), 2),
                'mae_total_market': round(sum(abs(float(r['total_line']) - float(r['total'])) for r in bt if r['total_line'] not in ('', 'nan')) / max(1, len(bt)), 2)}
    ledger = rows(P + 'picks_ledger.csv') if os.path.exists(P + 'picks_ledger.csv') else []
    retro = rows(P + 'picks_retro.csv') if os.path.exists(P + 'picks_retro.csv') else []
    rt = rows(P + 'team_ratings.csv', lambda r: r['season'] == '2026') if os.path.exists(P + 'team_ratings.csv') else []
    props = rows(P + 'props_current.csv') if os.path.exists(P + 'props_current.csv') else []
    pledger = rows(P + 'props_ledger.csv') if os.path.exists(P + 'props_ledger.csv') else []
    return {'games': gm, 'backtest': backtest, 'ledger': ledger, 'retro': retro, 'ratings': rt, 'props': props, 'propsLedger': pledger,
            'propsWeek': int(props[0]['week']) if props else None}

def betting_payload():
    """Bet board: priced prop lines, anytime-TD fair prices, SGP correlations, model validation, graded ledger."""
    P = 'data/processed/'
    if not os.path.exists(P + 'bet_lines.csv'):
        if not os.path.exists(P + 'game_lines.csv'): return None
        GL = pd.read_csv(P + 'game_lines.csv')
        glh = [[int(r.season), int(r.week), r.away_team, r.home_team, int(r.away_score) if r.away_score == r.away_score else None,
                int(r.home_score) if r.home_score == r.home_score else None, r.spread_line if r.spread_line == r.spread_line else None,
                r.total_line if r.total_line == r.total_line else None] for r in GL.itertuples()]
        return {'lines': [], 'td': [], 'proj': [], 'glh': glh, 'corr': {}, 'model': {}, 'dists': {}, 'ledger': [], 'dvpMeta': {}, 'week': None}
    def rows(f):
        if not os.path.exists(P + f): return []
        df = pd.read_csv(P + f)
        return json.loads(df.to_json(orient='records'))
    M = json.load(open(P + 'prop_model.json'))
    meta = json.load(open(P + 'dvp_adjusted_meta.json')) if os.path.exists(P + 'dvp_adjusted_meta.json') else {}
    td = rows('bet_td.csv')[:260]
    # every projected player x market (not just posted DK lines) so F11 can research any prop at any line
    proj = []
    if os.path.exists(P + 'prop_projections.csv'):
        PJ = pd.read_csv(P + 'prop_projections.csv')
        PJ = PJ[(PJ.market != 'anytime_td') & (PJ.games > 0) & ~PJ.slot.isin(['QB3', 'QB4', 'RB4'])]
        proj = [[r.player, r.team, r.opp, r.slot, r.market, round(float(r.proj), 1), r.q10, r.q50, r.q90, round(float(r.n_eff), 1),
                 round(float(r.matchup_x), 3), round(float(r.game_x), 3)]
                for r in PJ.itertuples()]
    # three seasons of closing lines + scores for team trend charts (ATS margin, team / game totals vs today's numbers)
    glh = []
    if os.path.exists(P + 'game_lines.csv'):
        GL = pd.read_csv(P + 'game_lines.csv')
        for r in GL.itertuples():
            sc = r.away_score == r.away_score
            glh.append([int(r.season), int(r.week), r.away_team, r.home_team, int(r.away_score) if sc else None,
                        int(r.home_score) if sc else None, r.spread_line, r.total_line])
    return {'lines': rows('bet_lines.csv'), 'td': td, 'proj': proj, 'glh': glh, 'corr': json.load(open(P + 'bet_corr.json')),
            'model': {k: {kk: vv for kk, vv in v.items()} for k, v in M['markets'].items()}, 'dists': M['dists'],
            'ledger': rows('bet_ledger.csv'), 'dvpMeta': meta,
            'week': int(pd.read_csv(P + 'prop_projections.csv').week.iloc[0]) if os.path.exists(P + 'prop_projections.csv') else None}

def college_payload(logs):
    """College for every player in the logs / depth chart: nflverse rosters (college, draft) x ESPN college-football
    team ids/colors/conference (data/raw/colleges_espn.txt, pulled via Chrome). First school listed = final school."""
    src = 'data/raw/colleges_espn.txt'
    if not os.path.exists(src): return {'s': {}, 'p': {}}
    S = {}
    for line in open(src, encoding='utf-8'):
        if line.startswith('#') or not line.strip(): continue
        f = line.rstrip('\n').split('|')
        S[re.sub(r'\s+', ' ', f[0]).strip()] = f[1:7]
    cols = ['pfr_id', 'full_name', 'team', 'college', 'entry_year', 'draft_number', 'draft_club', 'birth_date']
    R = pd.concat([pd.read_parquet(f'data/raw/nflverse/roster_{y}.parquet', columns=cols) for y in (2026, 2025, 2024)
                   if os.path.exists(f'data/raw/nflverse/roster_{y}.parquet')])
    R = R[R.college.notna() | R.birth_date.notna()]
    by_id = R.dropna(subset=['pfr_id']).drop_duplicates('pfr_id').set_index('pfr_id')
    by_name = R.drop_duplicates('full_name').set_index('full_name')
    P, miss, BD = {}, set(), {}
    def add(name, r):
        if pd.notna(r.birth_date) and name not in BD: BD[name] = str(r.birth_date)[:10]
        if name in P or not isinstance(r.college, str): return
        allc = [re.sub(r'\s+', ' ', c).strip() for c in str(r.college).split(';')]
        key = allc[0]
        if key not in S: miss.add(key); return
        num = lambda v: int(v) if pd.notna(v) else None
        P[name] = [key, num(r.entry_year), num(r.draft_number), r.draft_club if isinstance(r.draft_club, str) else '',
                   ' / '.join(allc[1:])]
    for l in logs:
        if l[1] in by_id.index: add(l[0], by_id.loc[l[1]])
    dcp = sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1]
    norm = lambda n: re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', '', str(n).lower()))
    by_norm = {norm(n): r for n, r in by_name.iterrows()}
    R2 = R.assign(last=R.full_name.str.split().str[-1].str.lower())
    for r in csv.DictReader(open(dcp, encoding='utf-8')):
        n = r['player']; alias = {'Hollywood Brown': 'Marquise Brown'}.get(n)
        if alias in by_name.index: add(n, by_name.loc[alias]); continue
        if n in by_name.index: add(n, by_name.loc[n]); continue
        if norm(n) in by_norm: add(n, by_norm[norm(n)]); continue
        last = [w for w in n.lower().replace('.', '').split() if w not in ('jr', 'sr', 'ii', 'iii', 'iv')][-1]
        c = R2[(R2['last'] == last) & (R2.team.replace({'LA': 'LAR'}) == r['team'])].drop_duplicates('full_name')
        if len(c) == 1: add(n, c.iloc[0])
    used = {v[0] for v in P.values()}
    if miss: print('  colleges missing from colleges_espn.txt:', sorted(miss))
    return {'s': {k: v for k, v in S.items() if k in used}, 'p': P, 'bd': BD}

def headshots(logs, depth):
    """{display name: espn athlete id} for every player in the logs or on the depth chart -> ESPN headshot CDN URLs in the UI."""
    import re, unicodedata
    f = 'data/raw/nflverse/roster_2026.parquet'
    if not os.path.exists(f): return {}
    R = pd.read_parquet(f, columns=['full_name', 'team', 'espn_id', 'pfr_id', 'week']).dropna(subset=['espn_id'])
    R = R.sort_values('week').drop_duplicates('espn_id', keep='last')
    nk = lambda n: re.sub(r'\s+(jr|sr|ii|iii|iv|v)$', '', re.sub(r"[^a-z ]", '', unicodedata.normalize('NFKD', str(n)).encode('ascii', 'ignore').decode().lower()).strip())
    by_pfr = {r.pfr_id: str(int(float(r.espn_id))) for r in R.itertuples() if isinstance(r.pfr_id, str)}
    by_nt, by_n = {}, {}
    for r in R.itertuples():
        e = str(int(float(r.espn_id))); by_nt[(nk(r.full_name), r.team)] = e; by_n.setdefault(nk(r.full_name), set()).add(e)
    out = {}
    for l in logs:
        if l[0] not in out and l[1] in by_pfr: out[l[0]] = by_pfr[l[1]]
    for d in depth:
        if d['player'] in out: continue
        k = nk(d['player']); e = by_nt.get((k, d['team'].replace('WSH', 'WAS'))) or (next(iter(by_n[k])) if len(by_n.get(k, ())) == 1 else None)
        if e: out[d['player']] = e
    return out

def league_config():
    """Per-league UI config embedded as J.league. NFL keeps the template's built-in team map / slates; NCAA injects its own."""
    if LEAGUE == 'nfl':
        return {'code': 'nfl', 'title': 'NFL DEFENSE-VS-POSITION', 'other': {'code': 'ncaa', 'label': 'NCAA', 'href': 'ncaa.html'}}
    def hx(h):
        h = str(h or '').lstrip('#')
        return h if re.fullmatch(r'[0-9a-fA-F]{6}', h) else None
    def lum(h):
        h = hx(h)
        if not h: return 0
        v = int(h, 16)
        r, g, b_ = v >> 16, (v >> 8) & 255, v & 255
        return (0.2126 * r + 0.7152 * g + 0.0722 * b_) / 255
    def readable(c1, c2):
        """ESPN primary colors are often near-black on a black terminal: prefer the brighter of the two, then lighten toward white."""
        c1, c2 = (('#' + hx(c1)) if hx(c1) else '#58a6ff'), (('#' + hx(c2)) if hx(c2) else '#444444')
        if lum(c1) >= 0.22: return c1                                   # bright enough as is (Texas orange, Georgia red)
        v2 = int(c2.lstrip('#'), 16); sat2 = max(v2 >> 16, (v2 >> 8) & 255, v2 & 255) - min(v2 >> 16, (v2 >> 8) & 255, v2 & 255)
        if 0.12 <= lum(c2) <= 0.8 and sat2 > 40: return c2             # a real secondary color (Michigan maize, Navy gold, Ole Miss red)
        c = c1; l = lum(c)                                              # otherwise lighten the dark primary toward white
        v = int(c.lstrip('#'), 16); t = (0.30 - l) / (1 - l) * 1.1
        mix = lambda x: int(x + (255 - x) * min(1, t))
        return '#%02x%02x%02x' % (mix(v >> 16), mix((v >> 8) & 255), mix(v & 255))
    teams = {}
    for r in csv.DictReader(open('data/processed/teams.csv', encoding='utf-8')):
        teams[r['code']] = {'n': r['school'], 's': r['team_id'], 'c1': readable(r['color'], r['alt_color']), 'c2': r['alt_color'], 'conf': r['conference'], 'fbs': r['classification'] == 'fbs'}
    return {'code': 'ncaa', 'title': 'NCAA FBS DEFENSE-VS-POSITION', 'other': {'code': 'nfl', 'label': 'NFL', 'href': 'rainman.html'},
            'teams': teams, 'weeks': 20, 'nTeams': sum(1 for t in teams.values() if t['fbs']),
            'slateLbl': {'MIDWK': 'MIDWEEK', 'THU': 'THU', 'FRI': 'FRI', 'SAT_AM': 'SAT NOON', 'SAT_PM': 'SAT AFT', 'SAT_NT': 'SAT NIGHT', 'SAT_LT': 'LATE NIGHT', 'SUNMON': 'SUN/MON', 'TBD': 'TBD'},
            'slateTip': {'MIDWK': 'Tuesday / Wednesday games (MACtion)', 'THU': 'Thursday', 'FRI': 'Friday', 'SAT_AM': 'Saturday kickoffs before 2 PM ET', 'SAT_PM': 'Saturday 2:00-6:59 PM ET',
                         'SAT_NT': 'Saturday 7:00-9:59 PM ET', 'SAT_LT': 'Saturday 10 PM ET and later', 'SUNMON': 'Sunday / Monday games', 'TBD': 'kickoff time not set yet (TV windows are announced 6-12 days out)'},
            'slateOrder': ['MIDWK', 'THU', 'FRI', 'SAT_AM', 'SAT_PM', 'SAT_NT', 'SAT_LT', 'SUNMON', 'TBD'],
            'hideTabs': ['intel', 'games', 'locker'], 'depthNote': 'usage-derived (carries + receptions / attempts over the last 3 games) — no public college depth-chart feed'}

def ncaa_headshots():
    """{display name: ESPN college athlete id} from players.csv (CFBD roster headshot urls carry the ESPN id)."""
    out = {}
    for r in csv.DictReader(open('data/processed/players.csv', encoding='utf-8')):
        m = re.search(r'/(\d+)\.png', r['headshot'] or '')
        if m and r['player'] not in out: out[r['player']] = m.group(1)
    return out

def main():
    if LEAGUE != 'nfl': os.chdir(os.path.join(REPO, LEAGUE))
    data = {'built': str(datetime.date.today()), 'statCols': STAT_COLS, 'slots': SLOTS,
            'groupStats': GROUP_STATS, 'primary': PRIMARY}
    data['dvp'] = {}
    for f in sorted(glob.glob('data/processed/dvp_season_[0-9]*.csv')):
        data['dvp'][f.split('_')[-1].split('.')[0]] = dvp_table(f)
    data['dvp']['combined'] = dvp_table('data/processed/dvp_combined.csv')
    if os.path.exists('data/processed/dvp_adjusted.csv'):
        data['dvp']['adjusted'] = dvp_table('data/processed/dvp_adjusted.csv')
    data['blend'] = pd.read_csv('data/processed/dvp_combined.csv')['seasons_blended'].iloc[0]

    wk = pd.read_csv('data/processed/dvp_weekly.csv')
    data['weekly'] = [[r['defense'], int(r['season']), int(r['week']), r['opponent']] +
                      [round(float(r[c]), 1) for c in STAT_COLS] for _, r in wk.iterrows()]

    # usage layer (build_advanced.py: game_logs x nflverse snap counts / pbp) -> appended to each log row
    usage = {}
    if os.path.exists('data/processed/player_usage.csv'):
        for r in csv.DictReader(open('data/processed/player_usage.csv', encoding='utf-8')):
            f4 = lambda k, d=3: (round(float(r[k]), d) if r[k] not in ('', 'nan') else None)
            usage[(int(r['season']), int(r['week']), r['player_id'])] = [f4('snaps', 0), f4('snap_pct'), f4('target_share'), f4('adot', 1), f4('rush_share'), f4('wopr')]
    logs = []
    for f in sorted(glob.glob('data/game_logs/game_logs_*.csv')):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            logs.append([r['player'], r['player_id'], int(r['season']), int(r['week']), r['team'],
                r['opponent'], r['home_away'], r['slot'], r['pos'], int(r['pass_yds']), int(r['pass_td']),
                int(r['pass_att']), int(r['int']), int(r['rush_att']), int(r['rush_yds']), int(r['rush_td']),
                int(r['targets']), int(r['rec']), int(r['rec_yds']), int(r['rec_td']),
                float(r['fantasy_pts_std']), float(r['fantasy_pts_ppr'])]
                + usage.get((int(r['season']), int(r['week']), r['player_id']), [None] * 6) + [int(r['cmp'] or 0)])
    data['logs'] = logs
    data['intel'] = intel_payload()
    data['bets'] = bets_payload()
    data['college'] = college_payload(logs)
    data['betting'] = betting_payload()
    # v4: exchange prices, unified picks ledger, DFS entries, signal efficacy
    def rows_of(path, flt=None):
        if not os.path.exists(path): return []
        R = list(csv.DictReader(open(path, encoding='utf-8')))
        return [r for r in R if flt is None or flt(r)]
    _m = list(csv.DictReader(open('data/processed/matchups_current.csv', encoding='utf-8'))) if os.path.exists('data/processed/matchups_current.csv') else []
    cur_week = int(_m[0]['week']) if _m else 1
    data['kalshi'] = rows_of('data/processed/kalshi_implied.csv', lambda r: r['week'] != '' and int(r['week']) >= cur_week)
    data['picksAll'] = rows_of('data/processed/picks_all.csv')
    data['dfs'] = {'entries': rows_of('data/processed/dfs_entries.csv'), 'summary': rows_of('data/processed/dfs_summary.csv')}
    data['signals'] = json.load(open('data/processed/signals.json')) if os.path.exists('data/processed/signals.json') else None
    # player <-> game connections (build_connections.py): homecoming / college town / home state / revenge / birthday
    data['conn'] = {'rows': [], 'born': {}}
    if os.path.exists('data/processed/connections_2026.csv'):
        for r in csv.DictReader(open('data/processed/connections_2026.csv', encoding='utf-8')):
            data['conn']['rows'].append([int(r['week']), r['game'], r['player'], r['team'], r['opp'], r['type'], r['detail'], int(r['miles']) if r['miles'] else None])
        for r in csv.DictReader(open('data/processed/player_geo.csv', encoding='utf-8')):
            if r['birthplace']: data['conn']['born'][r['player']] = r['birthplace']

    data['matchups'] = list(csv.DictReader(open('data/processed/matchups_current.csv', encoding='utf-8')))
    sched = {}
    for r in csv.DictReader(open('data/processed/schedule_2026.csv')):
        nwk = sum(1 for k in r if k.startswith('week_'))
        sched[r['team']] = [r[f'week_{i}'] for i in range(1, nwk + 1)]
    data['sched26'] = sched
    # games26 row: [week, vis, home, date, day, time_et, slate] — kickoff cols from kickoffs_2026.csv
    kick = {}
    if os.path.exists('data/processed/kickoffs_2026.csv'):
        for r in csv.DictReader(open('data/processed/kickoffs_2026.csv')):
            kick[(int(r['week']), r['vis'], r['home'])] = (r['day'], r['time_et'], r['slate'])
    data['games26'] = [[int(r['week']), r['vis'], r['home'], r['date']] +
                       list(kick.get((int(r['week']), r['vis'], r['home']), ('', '', 'TBD')))
                       for r in csv.DictReader(open('data/processed/games_2026.csv'))]
    # current 2026/27 matchup week (set by refresh.py via build_matchups.py)
    data['week'] = int(data['matchups'][0]['week']) if data['matchups'] else 1
    dcp = sorted(glob.glob('data/processed/depth_charts_*.csv'))[-1]
    data['depth'] = list(csv.DictReader(open(dcp, encoding='utf-8')))
    data['depthDate'] = dcp.split('_')[-1][:10]
    data['ph'] = headshots(logs, data['depth']) if LEAGUE == 'nfl' else ncaa_headshots()
    data['league'] = league_config()

    def np_default(o):
        import numpy as np
        if isinstance(o, np.integer): return int(o)
        if isinstance(o, np.floating): return float(o)
        raise TypeError(type(o))
    payload = json.dumps(data, separators=(',', ':'), default=np_default)
    template = open(os.path.join(REPO, 'scripts/dashboard_template.html'), encoding='utf-8').read()
    html = template.replace('__DATA__', payload).replace('__LEAGUE_NAME__', data['league']['title'])
    out = os.path.join(REPO, 'dashboard', 'rainman.html' if LEAGUE == 'nfl' else f'{LEAGUE}.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(html)
    print(f'{os.path.relpath(out, REPO)} written: {len(html)//1024} KB, logs={len(logs)}, '
          f'weekly={len(data["weekly"])}, matchups={len(data["matchups"])}')

if __name__ == '__main__':
    main()
