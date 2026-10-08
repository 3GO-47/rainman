"""RAINMAN local loop — the whole autoloop on Josh's PC, no Claude session, no browser, no credentials in the repo.
Run it once a day (Windows Task Scheduler, see scripts/local/install.ps1). It decides what to do from the calendar and the gate:

  every run      multi-sport slate (ESPN) -> gate: which leagues have regular-season / playoff games (preseason never counts)
  NFL in season  box scores of every finished game not yet pulled (PFR, nflverse fallback) · depth charts (ESPN) ·
                 Thu/Sat/Sun: DraftKings props + Kalshi · Tue: nflverse cache · then scripts/refresh.py (full rebuild)
  NCAA in season Tue/Sat: ESPN lines -> scripts/ncaa/refresh.py
  NBA/NHL/WNBA   only on days a league has a game today/yesterday/this week: sportsdataverse parquets -> scripts/sports/build.py
  always         scripts/build_landing.py, git commit, git push if a credential helper is configured (else the commit stays local)

Usage: python scripts/local/loop.py [--force] [--no-push] [--dry]      (--force ignores the weekday cadence, --dry = gate only)
Log: notes/local_runs.log · state: notes/local_state.json"""
import datetime, glob, json, os, subprocess, sys, traceback
sys.path.insert(0, os.path.dirname(__file__))
from common import log, state, save_state, run, TODAY, TODAY_S
import gate, pull_box, pull_espn, pull_kalshi, pull_markets

FORCE = '--force' in sys.argv
WD = TODAY.weekday()            # Mon=0 … Sun=6
DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][WD]

GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')   # never hang on a credential prompt in a scheduled run

def git(*args, check=False):
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True, env=GIT_ENV)
    if check and r.returncode: raise RuntimeError(r.stderr.strip()[:200])
    return r

def step(name, fn, *a):
    try:
        out = fn(*a); return out
    except Exception as e:
        log(f'!! {name} failed: {e}'); log(traceback.format_exc().strip().splitlines()[-1]); return None

def main():
    st = state(); did = []
    log(f'=== local loop {TODAY_S} ({DOW}){" FORCE" if FORCE else ""}')
    step('slate', pull_espn.slate)
    G = gate.all_leagues()
    log('gate: ' + json.dumps(G, default=str))
    if '--dry' in sys.argv: return
    nfl_changed = False
    # ---------------- NFL
    if G['nfl']['active']:
        n = step('box', pull_box.main) or 0
        nfl_changed |= n > 0
        if n == 0 and G['nfl']['unpulled']: log(f'  {G["nfl"]["unpulled"]} finished games still missing — retry tomorrow')
        snaps = sorted(glob.glob('data/processed/depth_charts_*.csv'))
        age = (TODAY - datetime.date.fromisoformat(snaps[-1][-14:-4])).days if snaps else 99
        if FORCE or DOW in ('Tue', 'Wed', 'Thu', 'Sat', 'Sun') or age > 5:
            raw = step('depth', pull_espn.depth)
            if raw:
                step('build_depth_chart', run, ['scripts/build_depth_chart.py', raw, TODAY_S]); nfl_changed = True
        if G['nfl']['games_next7'] and (FORCE or DOW in ('Thu', 'Sat', 'Sun')):
            if step('props', pull_espn.props): nfl_changed = True
            if step('kalshi', pull_kalshi.main): nfl_changed = True
        if FORCE or DOW == 'Tue':
            step('nflverse', run, ['scripts/fetch_nflverse.py'], False)
        if nfl_changed or FORCE or DOW in ('Tue', 'Thu', 'Sat', 'Sun'):
            if step('refresh', run, ['scripts/refresh.py']) is not None: did.append('nfl')
    else:
        log('NFL: no regular-season / playoff games within 7 days — skipped')
    # ---------------- NCAA
    if G['ncaa']['active'] and (FORCE or DOW in ('Tue', 'Sat')):
        if step('ncaa lines', pull_espn.ncaa):
            if step('ncaa refresh', run, ['scripts/ncaa/refresh.py']) is not None: did.append('ncaa')
    # ---------------- NBA / NHL / WNBA (refresh.py already ran them when the NFL branch rebuilt)
    live = [lg for lg in ('nba', 'nhl', 'wnba') if G[lg]['active']]
    if live and 'nfl' not in did:
        step('fetch_sdv', run, ['scripts/sports/fetch_sdv.py'], False)
        if step('sports build', run, ['scripts/sports/build.py']) is not None: did += live
    elif live: did += live
    else: log('NBA/NHL/WNBA: no games around today — skipped')
    if 'nfl' not in did and glob.glob('data/raw/slate_all_*.txt'):
        step('landing', run, ['scripts/build_landing.py'])
    # ---------------- Arb Engine: DK (ESPN) + Kalshi + Polymarket for every league with games in the window, then the board
    if any(G[lg]['active'] for lg in G):
        if step('markets', pull_markets.main):
            if step('arb', run, ['scripts/build_arb.py']) is not None: did.append('arb')
        step('social', run, ['scripts/build_social.py'])
    # ---------------- commit / push
    git('add', '-A')
    chg = git('status', '--porcelain').stdout.strip()
    if chg:
        msg = f'local loop {TODAY_S} ({DOW}): ' + (', '.join(did) or 'slate') + f' · {len(chg.splitlines())} files'
        git('commit', '-q', '-m', msg)
        pushed = False
        if '--no-push' not in sys.argv:
            r = git('push', '-q', 'origin', 'HEAD:main')
            pushed = r.returncode == 0
            log('pushed to origin/main' if pushed else f'push skipped ({(r.stderr or "").strip().splitlines()[-1][:120] if r.stderr else "no credential helper"}); commit kept locally')
        st[TODAY_S] = dict(did=did, files=len(chg.splitlines()), pushed=pushed)
    else:
        log('nothing changed'); st[TODAY_S] = dict(did=did, files=0, pushed=False)
    save_state(st)
    log(f'=== done: {", ".join(did) or "no builds"}')

if __name__ == '__main__':
    main()
