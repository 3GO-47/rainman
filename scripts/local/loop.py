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
import os as _os0; _os0.environ.setdefault('PYTHONIOENCODING', 'utf-8'); _os0.environ.setdefault('PYTHONUTF8', '1')
import datetime, glob, json, os, subprocess, sys, traceback
sys.path.insert(0, os.path.dirname(__file__))
from common import log, state, save_state, run, TODAY, TODAY_S
import gate, pull_box, pull_espn, pull_kalshi, pull_markets, pull_tennis

FORCE = '--force' in sys.argv
WD = TODAY.weekday()            # Mon=0 … Sun=6
DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][WD]

GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')   # never hang on a credential prompt in a scheduled run

def git(*args, check=False):
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True, env=GIT_ENV)
    if check and r.returncode: raise RuntimeError(r.stderr.strip()[:200])
    return r

CUR = {'step': '', 'since': None}
def step(name, fn, *a):
    CUR['step'] = name; CUR['since'] = datetime.datetime.now()
    try:
        out = fn(*a); return out
    except KeyboardInterrupt:
        raise
    except Exception as e:
        log(f'!! {name} failed: {e}'); log(traceback.format_exc().strip().splitlines()[-1]); return None
    finally:
        dt = (datetime.datetime.now() - CUR['since']).total_seconds()
        if dt > 120: log(f'  ({name} took {dt/60:.1f} min)')

SLEEPER = 'notes/close_sleeper.json'
def plant_sleeper():
    """The close pull has to land ~75 minutes before kickoff and the markets task only runs every six hours, so each run
    plants one detached sleeper: a copy of this script that waits for the next close window inside the coming six hours,
    then runs the markets pass (odds, exchanges, arb, commit, push). Nothing recurring, nothing in Claude — a process on
    this PC that exits after one pass. A lock file keeps it to one sleeper at a time."""
    try:
        r = subprocess.run([sys.executable, 'scripts/fetch_odds_api.py', '--next-close'], capture_output=True, text=True, timeout=120)
        when = (r.stdout or '').strip()
    except Exception as e: log(f'  sleeper: could not read the next close window ({e})'); return
    if not when: log('  sleeper: no close window in the next six hours'); return
    try:
        cur = json.load(open(SLEEPER))
        if cur.get('until') == when and cur.get('pid') and _alive(cur['pid']): log(f'  sleeper: already planted for {when}'); return
    except Exception: pass
    flags = 0x00000008 | 0x00000200 | 0x01000000 if os.name == 'nt' else 0     # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB
    try:
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), '--markets', '--wait', when], creationflags=flags, close_fds=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.getcwd())
        json.dump(dict(until=when, pid=p.pid, planted=datetime.datetime.now().isoformat(timespec='minutes')), open(SLEEPER, 'w'))
        log(f'  sleeper: planted for {when} (pid {p.pid})')
    except Exception as e: log(f'  sleeper: could not start ({e})')

def _alive(pid):
    try:
        if os.name == 'nt':
            out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], capture_output=True, text=True).stdout
            return str(pid) in out
        os.kill(pid, 0); return True
    except Exception: return False

def wait_until(iso):
    import time
    t = datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))
    while True:
        s = (t - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        if s <= 0: return
        time.sleep(min(s, 300))

def markets_only(G, st):
    did = []
    if any(G[lg]['active'] for lg in G):
        if G['nfl']['active'] and step('injuries', pull_espn.injuries): step('build_injuries', run, ['scripts/build_injuries.py'], False); did.append('injuries')
        if os.path.exists('.env') and 'ODDS_API_KEY=' in open('.env').read():
            if step('odds api', run, ['scripts/fetch_odds_api.py'], False): did.append('odds')
        if step('markets', pull_markets.main): did.append('exchanges')
        if step('tennis markets', pull_tennis.markets) and step('tennis', run, ['scripts/tennis/build.py']) is not None: did.append('tennis')
        if did and step('arb', run, ['scripts/build_arb.py']) is not None: did.append('arb'); step('tracking', run, ['scripts/build_tracking.py'])
        if 'odds' in did:                                                                           # fresh book prices: re-price the bet board and the dashboard that shows it
            step('bets', run, ['scripts/build_bets.py'], False); step('clv', run, ['scripts/build_clv.py'], False)
        if 'odds' in did or 'injuries' in did: step('td picks', run, ['scripts/build_td_picks.py'], False); step('dashboard', run, ['scripts/build_dashboard.py'], False); step('dev', run, ['scripts/build_dev.py'], False)
        if did: step('social', run, ['scripts/build_social.py']); step('landing', run, ['scripts/build_landing.py'])
    git('add', '-A'); chg = git('status', '--porcelain').stdout.strip()
    if chg:
        git('commit', '-q', '-m', f'markets {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}: ' + (', '.join(did) or 'state') + f' · {len(chg.splitlines())} files')
        if '--no-push' not in sys.argv:
            r = git('push', '-q', 'origin', 'HEAD:main'); log('pushed' if r.returncode == 0 else 'push skipped (no credential helper); commit kept locally')
    log(f'=== markets run done: {", ".join(did) or "nothing due"}')
    if '--wait' not in sys.argv and os.path.exists('.env') and 'ODDS_API_KEY=' in open('.env').read(): plant_sleeper()

def main():
    st = state(); did = []
    log(f'=== local loop {TODAY_S} ({DOW}){" FORCE" if FORCE else ""}')
    step('slate', pull_espn.slate)
    G = gate.all_leagues()
    log('gate: ' + json.dumps(G, default=str))
    if '--dry' in sys.argv: return
    if '--markets' in sys.argv:                                                                     # the 6-hourly task: lines + exchanges + arb board only
        if '--wait' in sys.argv:                                                                    # the planted sleeper: wait for the close window, then one pass
            when = sys.argv[sys.argv.index('--wait') + 1]; log(f'sleeper: waiting for the close window at {when}'); wait_until(when)
            step('slate', pull_espn.slate); G = gate.all_leagues()
        markets_only(G, st); return
    if '--tennis' in sys.argv:                                                                      # one-off: tennis history + week + prices -> tennis.html + landing, then commit
        step('tennis pull', pull_tennis.main); step('tennis', run, ['scripts/tennis/build.py']); step('landing', run, ['scripts/build_landing.py'])
        git('add', '-A')
        if git('status', '--porcelain').stdout.strip():
            git('commit', '-q', '-m', f'tennis {TODAY_S}')
            if '--no-push' not in sys.argv: git('push', '-q', 'origin', 'HEAD:main')
        return
    nfl_changed = False
    # ---------------- NFL
    if G['nfl']['active']:
        n = step('box', pull_box.main) or 0
        nfl_changed |= n > 0
        if n == 0 and G['nfl']['unpulled']: log(f'  {G["nfl"]["unpulled"]} finished games still missing — retry tomorrow')
        snaps = sorted(glob.glob('data/processed/depth_charts_*.csv'))
        age = (TODAY - datetime.date.fromisoformat(snaps[-1][-14:-4])).days if snaps else 99
        step('injuries', pull_espn.injuries)
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
    # ---------------- Tennis (year-round): Sackmann history + ESPN week + exchange prices -> tennis.html
    if step('tennis pull', pull_tennis.main) is not None and step('tennis', run, ['scripts/tennis/build.py']) is not None: did.append('tennis')
    if 'nfl' not in did and glob.glob('data/raw/slate_all_*.txt'):
        step('landing', run, ['scripts/build_landing.py'])
    # ---------------- Arb Engine: DK (ESPN) + Kalshi + Polymarket for every league with games in the window, then the board
    if any(G[lg]['active'] for lg in G):
        if os.path.exists('.env') and 'ODDS_API_KEY=' in open('.env').read():                     # every US book; the script's own cadence decides what is due
            step('odds api', run, ['scripts/fetch_odds_api.py'], False)
        if step('markets', pull_markets.main):
            if step('arb', run, ['scripts/build_arb.py']) is not None: did.append('arb'); step('tracking', run, ['scripts/build_tracking.py'])
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
    try: main()
    except KeyboardInterrupt:
        # Task Scheduler's time limit (or a user Ctrl-C) lands here: say where the run was when it died, so the next session can see it
        log(f'!! run interrupted (time limit or Ctrl-C) during step "{CUR["step"]}" after {((datetime.datetime.now()-CUR["since"]).total_seconds()/60 if CUR["since"] else 0):.1f} min'); raise
