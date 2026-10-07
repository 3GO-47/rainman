"""Download the sportsdataverse release parquets for every configured league -> data/sports/<league>/raw/
Usage: python3 scripts/sports/fetch_sdv.py [nba nhl wnba]   (default: all)
Idempotent: a file is re-downloaded only when the remote size differs (or it is the current season). Needs only GitHub."""
import os, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from config import LEAGUES, REL
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))

def get(url, dest, force):
    try:
        req = urllib.request.Request(url, method='HEAD'); req.add_header('User-Agent', 'rainman')
        with urllib.request.urlopen(req, timeout=60) as r: size = int(r.headers.get('Content-Length') or 0)
    except Exception as e:
        return f'skip ({e})'
    if not force and os.path.exists(dest) and size and os.path.getsize(dest) == size: return 'cached'
    req = urllib.request.Request(url); req.add_header('User-Agent', 'rainman')
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, 'wb') as f: f.write(r.read())
    return f'{os.path.getsize(dest) // 1024} KB'

def main(leagues):
    for lg in leagues:
        C = LEAGUES[lg]; d = f'data/sports/{lg}/raw'; os.makedirs(d, exist_ok=True)
        for y in C['seasons']:
            for kind, pat in C['files'].items():
                name = pat.format(y=y); dest = os.path.join(d, name.split('/')[-1])
                print(f'{lg} {kind} {y}: {get(REL + "/" + name, dest, force=(y == C["current"]))}')

if __name__ == '__main__':
    main(sys.argv[1:] or list(LEAGUES))
