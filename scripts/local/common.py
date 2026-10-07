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
    import subprocess
    log('run: ' + ' '.join(cmd))
    r = subprocess.run([sys.executable] + cmd)
    if check and r.returncode: raise RuntimeError(f'FAILED: {cmd}')
    return r.returncode

# ESPN NFL team ids (site + core API) and the abbreviations the rest of RAINMAN uses
ESPN_NFL = {'ARI': 22, 'ATL': 1, 'BAL': 33, 'BUF': 2, 'CAR': 29, 'CHI': 3, 'CIN': 4, 'CLE': 5, 'DAL': 6, 'DEN': 7, 'DET': 8, 'GB': 9, 'HOU': 34, 'IND': 11,
            'JAX': 30, 'KC': 12, 'LV': 13, 'LAC': 24, 'LAR': 14, 'MIA': 15, 'MIN': 16, 'NE': 17, 'NO': 18, 'NYG': 19, 'NYJ': 20, 'PHI': 21, 'PIT': 23,
            'SF': 25, 'SEA': 26, 'TB': 27, 'TEN': 10, 'WSH': 28}
