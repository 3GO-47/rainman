"""Shared helpers for the local (no-Claude) loop: HTTP with pacing + retries, paths, state, logging.
Runs on Josh's Windows PC (full internet) — see notes/local_loop.md. Nothing here needs credentials."""
import datetime, json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
os.chdir(ROOT)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
TODAY = datetime.date.today()
TODAY_S = TODAY.isoformat()
STATE = 'notes/local_state.json'
LOG = 'notes/local_runs.log'

def log(msg):
    line = f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}'
    print(line, flush=True)
    os.makedirs('notes', exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f: f.write(line + '\n')

def state():
    try: return json.load(open(STATE))
    except Exception: return {}

def save_state(st):
    json.dump(st, open(STATE, 'w'), indent=1)

_last = {}
def get(url, pace=0.0, retries=3, timeout=40, headers=None, binary=False):
    """GET with a browser UA, per-host pacing (seconds between calls) and backoff on 429/5xx. Returns text (or bytes)."""
    host = url.split('/')[2]
    if pace:
        dt = time.time() - _last.get(host, 0)
        if dt < pace: time.sleep(pace - dt)
    h = {'User-Agent': UA, 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9'}
    if headers: h.update(headers)
    err = None
    for i in range(retries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)
            _last[host] = time.time()
            b = r.read()
            return b if binary else b.decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            _last[host] = time.time(); err = e
            if e.code in (403, 404): raise
            time.sleep(60 if e.code == 429 else 5 * (i + 1))
        except Exception as e:
            err = e; time.sleep(5 * (i + 1))
    raise err

def get_json(url, **kw):
    return json.loads(get(url, **kw))

def write_lines(path, lines, header=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        if header: f.write(header.rstrip('\n') + '\n')
        f.write('\n'.join(lines) + ('\n' if lines else ''))

def run(cmd, check=True):
    # Children print the site's own glyphs (·, ≥, Ψ); under Task Scheduler there is no console and Windows falls
    # back to cp1252, where ≥ raises UnicodeEncodeError and the whole script reports FAILED with no reason in the
    # log — build_arb.py did exactly that on every markets run from 2026-10-08. Force UTF-8 for the child and keep
    # the tail of its stderr, so a failure says why.
    import subprocess
    log('run: ' + ' '.join(cmd))
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    r = subprocess.run([sys.executable] + cmd, env=env, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
    if r.returncode:
        tail = [l for l in (r.stderr or '').strip().splitlines() if l.strip()][-4:]
        for l in tail: log('    ' + l[:200])
        if check: raise RuntimeError(f'FAILED: {cmd}')
    return r.returncode

# ESPN NFL team ids (site + core API) and the abbreviations the rest of RAINMAN uses
ESPN_NFL = {'ARI': 22, 'ATL': 1, 'BAL': 33, 'BUF': 2, 'CAR': 29, 'CHI': 3, 'CIN': 4, 'CLE': 5, 'DAL': 6, 'DEN': 7, 'DET': 8, 'GB': 9, 'HOU': 34, 'IND': 11,
            'JAX': 30, 'KC': 12, 'LV': 13, 'LAC': 24, 'LAR': 14, 'MIA': 15, 'MIN': 16, 'NE': 17, 'NO': 18, 'NYG': 19, 'NYJ': 20, 'PHI': 21, 'PIT': 23,
            'SF': 25, 'SEA': 26, 'TB': 27, 'TEN': 10, 'WSH': 28}


def kicked_off(g, hours=5):
    """Boolean mask over an nfldata games frame: the game is finished — nfldata has a `result`, OR kickoff (ET) was at least
    `hours` ago. nfldata posts results with a lag (MNF WAS@SF 2026-10-19 still had result=NaN through the next afternoon), and
    gate.py / pull_box.py keyed on `result` alone, so the gate said unpulled=0 and the box pull skipped a finished game."""
    import pandas as pd
    try:
        from zoneinfo import ZoneInfo
        now = datetime.datetime.now(ZoneInfo('America/New_York')).replace(tzinfo=None)
    except Exception:
        now = datetime.datetime.now()
    ko = pd.to_datetime(g.gameday.astype(str) + ' ' + g.gametime.fillna('13:00').astype(str), errors='coerce')
    return g.result.notna() | (ko + pd.Timedelta(hours=hours) <= now)
