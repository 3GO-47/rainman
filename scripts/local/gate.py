"""Season / slate gate: which leagues have REGULAR-SEASON or PLAYOFF games around today (preseason never counts).
Reads only files on disk (nflverse games.csv, sportsdataverse schedules, the latest slate). Used by loop.py to decide what
to pull and build; `python scripts/local/gate.py` prints the verdict."""
import datetime, glob, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import TODAY

def nfl():
    f = 'data/raw/nflverse/games.csv'
    if not os.path.exists(f): return dict(active=False, reason='no games.csv')
    g = pd.read_csv(f); g = g[(g.season == TODAY.year if TODAY.month >= 3 else g.season == TODAY.year - 1) & (g.game_type != 'PRE')]
    g['d'] = pd.to_datetime(g.gameday).dt.date
    win = g[(g.d >= TODAY - datetime.timedelta(days=7)) & (g.d <= TODAY + datetime.timedelta(days=7))]
    box = 'data/raw/box_lines_2026.txt'
    have = {l.split('|')[1] for l in open(box, encoding='utf-8') if l.startswith('P|')} if os.path.exists(box) else set()
    fin = g[g.result.notna() & g.pfr.notna()]
    return dict(active=len(win) > 0, games_today=int((g.d == TODAY).sum()), games_next7=int(((g.d >= TODAY) & (g.d <= TODAY + datetime.timedelta(days=7))).sum()),
                unpulled=int((~fin.pfr.isin(have)).sum()), week=int(win.week.min()) if len(win) else None)

def slate_counts():
    files = sorted(glob.glob('data/raw/slate_all_*.txt'))
    out = {}
    if not files: return out
    for l in open(files[-1], encoding='utf-8'):
        if not l.startswith('G|'): continue
        p = l.rstrip('\n').split('|')
        if len(p) < 26 or p[22] == '1': continue
        d = p[3][:10]
        k = p[1]
        o = out.setdefault(k, dict(today=0, next7=0))
        if d == str(TODAY): o['today'] += 1
        if str(TODAY) <= d <= str(TODAY + datetime.timedelta(days=7)): o['next7'] += 1
    return out

def sport(lg):
    sys.path.insert(0, 'scripts/sports')
    from config import LEAGUES
    C = LEAGUES[lg]; rows = []
    for y in C['seasons']:
        f = f'data/sports/{lg}/raw/' + C['files']['sched'].format(y=y).split('/')[-1]
        if not os.path.exists(f): continue
        s = pd.read_parquet(f)
        if C['sport'] == 'basketball': s = s[s.season_type.isin([2, 3])]; dcol = 'game_date'
        else: s = s[s.game_type.isin(['R', 'P'])]; dcol = 'game_date'
        rows.append(pd.to_datetime(s[dcol]).dt.date)
    d = pd.concat(rows) if rows else pd.Series([], dtype=object)
    sc = slate_counts().get(lg, {})
    yday = int((d == TODAY - datetime.timedelta(days=1)).sum()); today = int((d == TODAY).sum()) or sc.get('today', 0)
    nxt = int(((d >= TODAY) & (d <= TODAY + datetime.timedelta(days=7))).sum()) or sc.get('next7', 0)
    return dict(active=(yday + today + nxt) > 0, yesterday=yday, games_today=today, games_next7=nxt)

def all_leagues():
    sc = slate_counts()
    out = {'nfl': nfl(), 'ncaa': dict(active=sc.get('cfb', {}).get('next7', 0) > 0 or (TODAY.month in (8, 9, 10, 11, 12) or (TODAY.month == 1 and TODAY.day < 25)),
                                      games_next7=sc.get('cfb', {}).get('next7', 0))}
    for lg in ('nba', 'nhl', 'wnba'):
        try: out[lg] = sport(lg)
        except Exception as e: out[lg] = dict(active=False, reason=str(e)[:80])
    return out

if __name__ == '__main__':
    print(json.dumps(all_leagues(), indent=1, default=str))
