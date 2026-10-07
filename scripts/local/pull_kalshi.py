"""Local Kalshi pull (public trade API, no key) — Python port of the Chrome recipe. Writes data/raw/kalshi_<today>.txt:
  K|series|event|subject|rungs(strike:yes_bid/yes_ask/volume;...)|close_date   then scripts/build_kalshi.py consumes it."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get_json, log, write_lines, TODAY_S

API = 'https://api.elections.kalshi.com/trade-api/v2/markets'
SERIES = ['GAME', 'SPREAD', 'TOTAL', 'PASSYDS', 'PASSATT', 'PASSTDS', 'PASSCOMP', 'PASSINT', 'RSHYDS', 'RSHATT', 'REC', 'RECYDS', 'TD', 'FIRSTTD',
          'LADDERREC', 'LADDERRECYDS', 'LADDERRSHYDS']

def main(prefix='KXNFL'):
    G = {}
    for s in SERIES:
        cur = ''
        for _ in range(10):
            try: j = get_json(f'{API}?limit=200&status=open&series_ticker={prefix}{s}' + (f'&cursor={cur}' if cur else ''), pace=0.5)
            except Exception as e:
                log(f'  kalshi {s}: {str(e)[:60]}'); break
            for m in j.get('markets', []):
                ev = m.get('event_ticker', ''); evs = ev.split('-')[1] if '-' in ev else ev
                title = (m.get('title') or '').replace('|', '/'); sub = (m.get('yes_sub_title') or '').replace('|', '/')
                subj = sub or title
                subj = re.sub(r':.*$', '', subj); subj = re.sub(r' wins.*$', '', subj); subj = re.sub(r'^Over .*$', 'TOTAL', subj); subj = re.sub(r' wins by over.*$', '', subj).strip()
                if s == 'TOTAL': subj = 'TOTAL'
                if s in ('TD', 'FIRSTTD'): subj = re.sub(r' to score.*$', '', re.sub(r' scores.*$', '', re.sub(r':.*$', '', title))).strip()
                strike = m.get('floor_strike', m.get('cap_strike', ''))
                strike = '' if strike is None else strike
                k = f'{s}|{evs}|{subj}'
                g = G.setdefault(k, {'close': (m.get('close_time') or '')[:10], 'r': []})
                bid = float(m.get('yes_bid_dollars') or 0); ask = float(m.get('yes_ask_dollars') or 0); vol = float(m.get('volume_fp') or m.get('volume') or 0)
                g['r'].append(f'{strike}:{bid:.2f}/{ask:.2f}/{round(vol)}')
            cur = j.get('cursor') or ''
            if not cur: break
    lines = [f'K|{k}|{";".join(g["r"])}|{g["close"]}' for k, g in G.items()]
    out = f'data/raw/kalshi_{TODAY_S}.txt'
    write_lines(out, lines, f'# Kalshi NFL markets · pulled {TODAY_S} locally (api.elections.kalshi.com/trade-api/v2/markets, status=open)\n'
                '# K|series|event|subject|rungs(strike:yes_bid/yes_ask/volume;...)|close_date   — GAME rungs have an empty strike (team wins)')
    log(f'kalshi: {len(lines)} subjects -> {out}')
    return out if lines else None

if __name__ == '__main__':
    main()
