"""Closing-line value for every frozen position in picks_all.csv (NFL + CFB game lines, NFL props).

Why: W/L over a few hundred props takes a season to separate skill from noise; whether the market moved TOWARD the
model's side between freeze and kickoff shows up in weeks. Source = the consensus snapshots fetch_odds_api.py appends on
every pull (data/raw/odds_api/lines_history.csv: p = home win / home cover / Over probability, point = home handicap or
total; props_history.csv: line = median book line, p = P(Over)). Closing = the last snapshot before kickoff.

Per position:
  close_line / close_p  the consensus at the close
  clv_pts   points of line in the pick's favor (spread: our number minus the closing number for our team; total: Over =
            close - ours, Under = ours - close; prop: Over = close - ours, Under = ours - close)
  clv_p     probability points in the pick's favor (moneyline / anytime TD: closing P(our side) - frozen market P;
            props only when the closing line equals the frozen line, else blank)
  beat      1 = the close moved our way, 0 = against, blank = no movement or no data
  snaps     number of consensus snapshots that led to the close (1 = opener only, so the "close" is the opener)
Output: data/processed/picks_clv.csv — one row per picks_all position (key: type|ref|market|side|line).
"""
import os, re, csv, sys
import pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'data/processed/'
HL, HP = 'data/raw/odds_api/lines_history.csv', 'data/raw/odds_api/props_history.csv'
OUT = P + 'picks_clv.csv'
COLS = ['type', 'ref', 'market', 'side', 'line', 'week', 'close_ts', 'close_line', 'close_p', 'clv_pts', 'clv_p', 'beat', 'snaps']

def main():
    if not os.path.exists(P + 'picks_all.csv'):
        print('build_clv: no picks_all.csv'); return
    picks = pd.read_csv(P + 'picks_all.csv', dtype=str).fillna('')
    L = pd.read_csv(HL, dtype=str).fillna('') if os.path.exists(HL) else pd.DataFrame(columns=['ts'])
    H = pd.read_csv(HP, dtype=str).fillna('') if os.path.exists(HP) else pd.DataFrame(columns=['ts'])
    # game-line series: (away, home, market) -> sorted [(ts, commence, point, p)]
    LS = {}
    for r in L.itertuples(index=False):
        LS.setdefault((r.away, r.home, r.market), []).append((r.ts, r.commence, r.point, r.p))
    for v in LS.values(): v.sort()
    # prop series: (player, stat) -> [(ts, commence, line, p)]
    PS = {}
    for r in H.itertuples(index=False):
        PS.setdefault((r.player, r.stat), []).append((r.ts, r.commence, r.line, r.p))
    for v in PS.values(): v.sort()
    # week -> kickoff date range (so a prop's history rows can be tied to the right game)
    wk_range = {}
    if os.path.exists(P + 'kickoffs_2026.csv'):
        k = pd.read_csv(P + 'kickoffs_2026.csv', dtype=str)
        for w, g in k.groupby('week'): wk_range[str(int(w))] = (g.date.min(), g.date.max())
    def closing(series, commence=None):
        """last snapshot strictly before kickoff (commence from the row itself); returns (ts, commence, x, p, n)"""
        if not series: return None
        c = commence or series[-1][1]
        pre = [s for s in series if s[0] < c.replace(':00Z', 'Z')[:16] + 'Z' or s[0] < c]
        if not pre: return None
        return pre[-1] + (len(pre),)
    def f(x):
        try: return float(x)
        except (TypeError, ValueError): return None
    rows = []
    for p in picks.itertuples(index=False):
        t = p.type.upper(); row = dict(type=p.type, ref=p.ref, market=p.market, side=p.side, line=p.line, week=p.week,
                                       close_ts='', close_line='', close_p='', clv_pts='', clv_p='', beat='', snaps='')
        line = f(p.line); mref = f(p.market_ref)
        try:
            if t in ('ATS', 'TOTAL', 'ML'):
                parts = p.ref.split('_')                         # 2026_05_BAL_ATL = away BAL, home ATL
                if len(parts) < 4: rows.append(row); continue
                away, home = parts[2], parts[3]
                mk = {'ATS': 'spread', 'TOTAL': 'total', 'ML': 'moneyline'}[t]
                # the ref uses RAINMAN codes; history uses Odds API codes — both share the LAR/LA style differences only
                ser = LS.get((away, home, mk)) or LS.get((away.replace('LAR', 'LA'), home.replace('LAR', 'LA'), mk)) or []
                c = closing(ser)
                if not c: rows.append(row); continue
                ts, comm, pt, pp, n = c; pt = f(pt); pp = f(pp)
                row.update(close_ts=ts, snaps=n)
                side = p.side.strip()
                if t == 'ATS' and pt is not None:
                    team = side.split()[0]
                    m = re.search(r'([+-]?\d+(?:\.\d+)?)', side[len(team):])   # "MIA +7" -> +7 (picks_all.line is the AWAY handicap)
                    if not m: rows.append(row); continue
                    our_num = float(m.group(1))                   # the number we took on our team
                    close_num = pt if team == home or team == home.replace('LA', 'LAR') else -pt
                    row.update(close_line=round(close_num, 1), clv_pts=round(our_num - close_num, 1))
                    row['beat'] = '' if abs(our_num - close_num) < 1e-9 else int(our_num > close_num)
                elif t == 'TOTAL' and pt is not None and line is not None:
                    over = side.upper().startswith('OVER')
                    clv = (pt - line) if over else (line - pt)
                    row.update(close_line=round(pt, 1), clv_pts=round(clv, 1)); row['beat'] = '' if abs(clv) < 1e-9 else int(clv > 0)
                elif t == 'ML' and pp is not None and mref is not None:
                    team = side.split()[0]
                    ours = pp if team in (home, home.replace('LA', 'LAR')) else 1 - pp
                    row.update(close_p=round(ours, 4), clv_p=round(ours - mref, 4)); row['beat'] = '' if abs(ours - mref) < 0.002 else int(ours > mref)
            elif t in ('PROP', 'TD'):
                stat = 'anytime_td' if t == 'TD' else p.market
                ser = PS.get((p.player, stat)) or []
                lo, hi = wk_range.get(str(p.week).lstrip('0') or p.week, ('', ''))
                ser = [s for s in ser if (not lo) or (lo <= s[1][:10] <= hi + 'T')]
                c = closing(ser)
                if not c: rows.append(row); continue
                ts, comm, cl, cp, n = c; cl = f(cl); cp = f(cp)
                row.update(close_ts=ts, snaps=n, close_line='' if cl is None else cl, close_p='' if cp is None else round(cp, 4))
                if t == 'TD' and cp is not None and mref is not None:
                    yes = p.side.upper() == 'YES'
                    ours, theirs = (cp, mref) if yes else (1 - cp, 1 - mref)
                    row.update(clv_p=round(ours - theirs, 4)); row['beat'] = '' if abs(ours - theirs) < 0.002 else int(ours > theirs)
                elif t == 'PROP' and cl is not None and line is not None:
                    over = p.side.lower().startswith('over')
                    clv = (cl - line) if over else (line - cl)
                    row.update(clv_pts=round(clv, 2))
                    if abs(cl - line) < 1e-9 and cp is not None:
                        ours = cp if over else 1 - cp
                        row.update(clv_p=round(ours - 0.5, 4)); row['beat'] = '' if abs(ours - 0.5) < 0.002 else int(ours > 0.5)
                    else:
                        row['beat'] = int(clv > 0)
        except Exception as e:
            print(f'  clv: {p.type} {p.ref}: {e}')
        rows.append(row)
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    have = [r for r in rows if r['close_ts']]; beat = [r for r in have if r['beat'] != '']
    print(f'build_clv: {len(rows)} positions · {len(have)} with a closing consensus · '
          f'{sum(1 for r in beat if r["beat"] == 1)}/{len(beat)} beat the close -> {OUT}')

if __name__ == '__main__':
    main()
