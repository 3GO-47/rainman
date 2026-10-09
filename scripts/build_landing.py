"""Layer 0 — the multi-sport landing page -> dashboard/index.html, plus Layer-1 shells for the sports that have no data
pipeline yet (nba.html, ncaab.html, wnba.html, mlb.html, nhl.html, soccer.html) from the same slate file.

Usage: python3 scripts/build_landing.py
Input : data/raw/slate_all_YYYY-MM-DD.txt (latest; ESPN scoreboard pulls, see notes/scrape_recipe.md "multi-sport slate")
Every number on the page comes from that file; nothing is typed in by hand. NFL -> rainman.html, CFB -> ncaa.html.
"""
import os, glob, json, re
from datetime import datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
CDN = 'https://a.espncdn.com/i/'
NCAA_LOGO = 'https://upload.wikimedia.org/wikipedia/commons/d/dd/NCAA_logo.svg'
LEAGUES = [  # key, label, sport group, page, status, logo (real league marks: ESPN CDN dark variants; NCAA mark for the college sports)
    ('nfl', 'NFL', 'football', 'rainman.html', 'live', CDN + 'teamlogos/leagues/500-dark/nfl.png'),
    ('cfb', 'College Football', 'football', 'ncaa.html', 'live', NCAA_LOGO),
    ('nba', 'NBA', 'basketball', 'nba.html', 'live', CDN + 'teamlogos/leagues/500-dark/nba.png'),
    ('ncaab', 'College Basketball', 'basketball', 'ncaab.html', 'shell', NCAA_LOGO),
    ('wnba', 'WNBA', 'basketball', 'wnba.html', 'live', CDN + 'teamlogos/leagues/500-dark/wnba.png'),
    ('mlb', 'MLB', 'baseball', 'mlb.html', 'shell', CDN + 'teamlogos/leagues/500-dark/mlb.png'),
    ('nhl', 'NHL', 'hockey', 'nhl.html', 'live', CDN + 'teamlogos/leagues/500-dark/nhl.png'),
    ('soccer', 'Soccer', 'soccer', 'soccer.html', 'shell', CDN + 'leaguelogos/soccer/500-dark/2.png'),
    ('tennis', 'Tennis', 'tennis', 'tennis.html', 'live', CDN + 'espn/misc_logos/500-dark/tennis.png')]
SOCCER = {'epl': 'Premier League', 'mls': 'MLS', 'ucl': 'Champions League', 'laliga': 'La Liga', 'bund': 'Bundesliga', 'seriea': 'Serie A', 'ligue1': 'Ligue 1'}
SOCCER_LOGO = {'epl': 23, 'mls': 19, 'ucl': 2, 'laliga': 15, 'bund': 10, 'seriea': 12, 'ligue1': 9}
SOCCER_LOGO = {k: CDN + f'leaguelogos/soccer/500-dark/{v}.png' for k, v in SOCCER_LOGO.items()}
COMING = [('f1', 'Formula 1', CDN + 'teamlogos/leagues/500-dark/f1.png'), ('ufc', 'UFC', CDN + 'teamlogos/leagues/500/ufc.png')]
import brand

MK_LABEL = {'pass_yds': 'Pass yds', 'pass_td': 'Pass TD', 'rush_yds': 'Rush yds', 'rush_att': 'Rush att', 'receptions': 'Receptions', 'rec_yds': 'Rec yds'}
def nfl_teaser():
    """Softest NFL matchups per market this week: the opponent's opponent-adjusted DvP rank for the player's slot and stat
    (rank 1 of 32 = allows the most), among the 40 highest-volume players in the market (prop_projections.csv + dvp_adjusted.csv)."""
    f = 'data/processed/prop_projections.csv'; d = 'data/processed/dvp_adjusted.csv'
    if not (os.path.exists(f) and os.path.exists(d)): return None
    import csv
    rows = list(csv.DictReader(open(f, encoding='utf-8')))
    if not rows: return None
    DVP = {r['defense']: r for r in csv.DictReader(open(d, encoding='utf-8'))}
    def col(mk, slot):
        sl = 'QB' if slot.startswith('QB') else slot
        if mk == 'pass_yds': return 'QB PY rank'
        if mk == 'pass_td': return 'P TD rank'
        if mk in ('rush_yds', 'rush_att'): return {'QB': 'QB RY rank', 'RB1': 'RB1 RY rank', 'RB2': 'RB2+ RY rank'}.get(sl, 'WR RY rank' if sl.startswith('WR') else None)
        if mk == 'receptions': return f'{sl} Recep rank'
        if mk == 'rec_yds': return f'{sl} RecY rank'
    def rank(r):
        c = col(r['market'], r['slot']); x = DVP.get(r['opp'].replace('@', ''))
        try: return float(x[c]) if x and c else None
        except (KeyError, ValueError): return None
    wk = max(int(r['week']) for r in rows); rows = [r for r in rows if int(r['week']) == wk and r['market'] in MK_LABEL]
    out = {}
    for mk in MK_LABEL:
        R = [r for r in rows if r['market'] == mk and float(r['base'] or 0) > 0]
        R.sort(key=lambda r: -float(r['base'])); R = R[:40]
        R = [(rank(r), r) for r in R]; R = [(k, r) for k, r in R if k is not None]
        R.sort(key=lambda kr: (kr[0], -float(kr[1]['matchup_x']), -float(kr[1]['base'])))
        out[mk] = [dict(player=r['player'], team=r['team'], opp=r['opp'].replace('@', ''), slot=r['slot'], proj=round(float(r['proj']), 1), base=round(float(r['base']), 1), mx=round(float(r['matchup_x']), 2), rank=int(k)) for k, r in R[:3]]
    return dict(week=wk, n=32, markets=out)

def sport_teaser(lg, labels):
    """Softest matchups per market for the sportsdataverse leagues (scripts/sports/build.py projections.csv)."""
    f = f'data/sports/{lg}/processed/projections.csv'
    if not os.path.exists(f): return None
    import csv
    rows = [r for r in csv.DictReader(open(f, encoding='utf-8')) if r['market'] in labels and r['opp_rank']]
    if not rows: return None
    out = {}
    for mk in labels:
        R = [r for r in rows if r['market'] == mk and float(r['base'] or 0) > 0]
        R.sort(key=lambda r: -float(r['base'])); R = R[:40]; R.sort(key=lambda r: (float(r['opp_rank']), -float(r['ratio']), -float(r['base'])))
        out[mk] = [dict(player=r['player'], team=r['team'], opp=r['opp'], proj=round(float(r['proj']), 1), base=round(float(r['base']), 1), mx=round(float(r['ratio']), 2), rank=int(float(r['opp_rank']))) for r in R[:3]]
    n = len({r['opp'].replace('@', '') for r in rows} | {r['team'] for r in rows})
    return dict(week='', n=n, markets={k: v for k, v in out.items() if v})

def load_slate():
    files = sorted(glob.glob('data/raw/slate_all_*.txt'))
    if not files: raise SystemExit('no data/raw/slate_all_*.txt — pull the multi-sport slate first (notes/scrape_recipe.md)')
    f = files[-1]; pulled = re.search(r'(\d{4}-\d{2}-\d{2})', f).group(1)
    games = []
    for line in open(f, encoding='utf-8'):
        if not line.startswith('G|'): continue
        p = line.rstrip('\n').split('|')
        if len(p) < 26: continue
        if p[22] == '1': continue            # preseason is ignored everywhere (Josh, 2026-10-07)
        lg = p[1]
        games.append(dict(lg=lg, sport='soccer' if lg in SOCCER else lg, sub=SOCCER.get(lg, ''), id=p[2], date=p[3], status=p[4],
                          away=dict(id=p[5], abbr=p[6], name=p[7], rec=p[8], logo=p[9], rank=p[10] if p[10] not in ('', '99') else ''),
                          home=dict(id=p[11], abbr=p[12], name=p[13], rec=p[14], logo=p[15], rank=p[16] if p[16] not in ('', '99') else ''),
                          venue=p[17], tv=p[18], odds=p[19], ou=p[20], week=p[21], neutral=p[23] == '1', book=p[24], note=p[25]))
    tf = 'data/processed/tennis_matches.csv'                                  # scripts/tennis/build.py: the week's ATP / WTA singles
    if os.path.exists(tf):
        import csv
        for r in csv.DictReader(open(tf, encoding='utf-8')):
            if r['status'] not in ('STATUS_SCHEDULED', 'STATUS_IN_PROGRESS'): continue
            side = lambda n, rk: dict(id='', abbr=n.split()[-1][:10], name=n, rec=f'#{rk}' if rk else '', logo='', rank='')
            mp = r.get('model_p1'); kp = r.get('market_p1')
            games.append(dict(lg='tennis', sport='tennis', sub=r['tour'].upper(), id='t' + r['id'], date=r['date'], status=r['status'],
                              away=side(r['p1'], r['p1_rank']), home=side(r['p2'], r['p2_rank']), venue=r['tourney'], tv=r['round'], odds='', ou='', week='', neutral=True, book='',
                              note=' · '.join(x for x in [f"{r['tourney']} {r['round']}", f'model {round(100*float(mp))}% {r["p1"].split()[-1]}' if mp else '', f'market {round(100*float(kp))}%' if kp else ''] if x)))
    return games, pulled

def model_records():
    """Per league, the frozen positions and how they scored (NFL picks_all.csv; sports/<lg>/processed/picks.csv).
    One unit risked per position: a win at -110 returns 0.909, a win on a priced moneyline / anytime TD returns its own price."""
    import csv
    out = {}
    def units(r):
        res = (r.get('result') or '').upper()
        if res == 'W':
            t = (r.get('type') or '').upper()
            try: mp = float(r.get('market_ref') or 0)
            except ValueError: mp = 0
            return (1 / mp - 1) if t in ('ML', 'TD') and 0 < mp < 1 else 0.909
        return -1.0 if res == 'L' else 0.0
    def tally(rows, lg):
        by = {}; seq = []; u = 0.0; w = l = p_ = pend = 0
        rows = sorted(rows, key=lambda r: (r.get('frozen_on') or '', r.get('date') or '', str(r.get('week') or '').zfill(2)))
        for r in rows:
            t = (r.get('type') or '').upper() or 'ALL'
            if t == 'DFS': continue
            b = by.setdefault(t, dict(W=0, L=0, P=0, pending=0, u=0.0))
            res = (r.get('result') or '').upper()
            if res in ('W', 'L', 'P'):
                b[res] += 1; seq.append(res); b['u'] += units(r); u += units(r)
                w += res == 'W'; l += res == 'L'; p_ += res == 'P'
            else: b['pending'] += 1; pend += 1
        for b in by.values(): b['u'] = round(b['u'], 2)
        if by: out[lg] = dict(by=by, seq=seq[-80:], W=w, L=l, P=p_, pending=pend, u=round(u, 2),
                              hit=round(w / (w + l), 4) if w + l else None, roi=round(u / (w + l + p_), 4) if w + l + p_ else None)
    f = 'data/processed/picks_all.csv'
    if os.path.exists(f): tally(list(csv.DictReader(open(f, encoding='utf-8'))), 'nfl')
    for lg in ('nba', 'nhl', 'wnba'):
        f = f'data/sports/{lg}/processed/picks.csv'
        if os.path.exists(f): tally(list(csv.DictReader(open(f, encoding='utf-8'))), lg)
    return out

def game_model_backtest():
    """The NFL game model's held-out 2024-25 record, for one honest line on the landing page."""
    import csv
    f = 'data/processed/game_model.csv'
    if not os.path.exists(f): return None
    R = [r for r in csv.DictReader(open(f, encoding='utf-8')) if r['season'] in ('2024', '2025') and r['res_ats']]
    if not R: return None
    w = sum(r['res_ats'] == 'W' for r in R); l = sum(r['res_ats'] == 'L' for r in R)
    tw = sum(r['res_total'] == 'W' for r in R); tl = sum(r['res_total'] == 'L' for r in R)
    return dict(n=len(R), ats=[w, l], total=[tw, tl])

SHEAD = """<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">"""

SCSS = """
:root{--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;--sans:'Inter',system-ui,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:13px;line-height:1.45}a{color:inherit;text-decoration:none}img{-webkit-user-drag:none}
#hdr{display:flex;align-items:center;gap:16px;padding:10px 24px;border-bottom:1px solid var(--edge);background:#050506;position:sticky;top:0;z-index:5}
.brand{font:800 15px/1 var(--mono);letter-spacing:4px}.brand i{color:var(--acc);font-style:normal;margin-right:6px}.tag{color:var(--dim);font-size:12px}#hdr .right{margin-left:auto;color:var(--mute);font:500 10.5px var(--mono)}
.hl{display:flex;gap:4px;margin-left:10px}.hl a{font:600 10px var(--mono);letter-spacing:1px;padding:3px 9px;border:1px solid var(--edge2);border-radius:4px;color:var(--dim)}.hl a:hover{color:var(--fg);border-color:var(--acc)}
.wrap{max-width:1500px;margin:0 auto;padding:16px 24px 40px}
h1{font:800 24px/1.15 var(--sans);letter-spacing:-.3px;margin:4px 0 2px}h1 small{display:block;font:400 12.5px/1.5 var(--sans);color:var(--dim);margin-top:5px;max-width:900px}
h2{font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin:22px 0 10px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}h2 span{font:400 11.5px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}h2 a.go{margin-left:auto;font:600 10px var(--mono);letter-spacing:1px;padding:3px 9px;border:1px solid var(--edge2);border-radius:4px;color:var(--acc)}h2 a.go:hover{border-color:var(--acc)}
/* bubbles */
.bubs{display:flex;justify-content:space-between;align-items:flex-end;gap:8px;padding:6px 10px 2px;flex-wrap:wrap}
.bub{display:flex;flex-direction:column;align-items:center;gap:6px;cursor:pointer;min-width:120px;flex:1}
.bub .o{border-radius:50%;background:var(--panel);border:1px solid var(--edge2);display:flex;align-items:center;justify-content:center;position:relative}.bub.on .o{border:2px solid var(--acc);box-shadow:0 0 0 4px rgba(232,179,57,.12)}.bub:hover .o{border-color:var(--dim)}.bub.on:hover .o{border-color:var(--acc)}
.bub .o img{width:56%;height:56%;object-fit:contain}.bub .o .n{position:absolute;right:-2px;bottom:-2px;font:700 10.5px var(--mono);background:var(--s3);border:1px solid var(--edge2);border-radius:10px;padding:1px 7px;color:var(--fg)}.bub.on .o .n{background:var(--acc);color:#000;border-color:var(--acc)}
.bub b{font-size:12.5px}.bub small{color:var(--dim);font-size:10.5px;text-align:center}.bub .live{font:600 8.5px var(--mono);letter-spacing:1px;color:var(--acc)}.bub .shell{font:600 8.5px var(--mono);letter-spacing:1px;color:var(--mute)}
.seq{display:flex;gap:2px;height:7px}.seq i{display:block;width:5px;border-radius:1px;background:var(--s3)}.seq i.W{background:var(--green)}.seq i.L{background:var(--red)}.seq i.P{background:var(--dim)}
/* timeline */
.tlwrap{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:10px 12px 8px;overflow:hidden}
.tlhead{display:grid;grid-template-columns:150px 1fr;margin-bottom:4px}.tlaxis{position:relative;height:16px;border-bottom:1px solid var(--edge2)}.tlaxis span{position:absolute;top:0;font:500 9.5px var(--mono);color:var(--mute);transform:translateX(-50%)}
.lane{display:grid;grid-template-columns:150px 1fr;border-top:1px solid var(--edge);min-height:52px}.lane:first-of-type{border-top:0}
.lane .ll{display:flex;align-items:center;gap:8px;padding:6px 6px 6px 0;font-size:12px}.lane .ll img{width:22px;height:22px;object-fit:contain}.lane .ll b{font-weight:600}.lane .ll small{color:var(--mute);font:500 10px var(--mono)}.lane.on .ll b{color:var(--acc)}
.lane .lf{position:relative}.lane .lf .grid{position:absolute;top:0;bottom:0;border-left:1px dashed var(--edge)}.lane .lf .now{position:absolute;top:0;bottom:0;border-left:2px solid var(--acc);opacity:.7}
.chip{position:absolute;display:flex;align-items:center;gap:5px;height:44px;padding:0 8px 0 6px;border:1px solid var(--edge2);border-radius:7px;background:var(--s2);font:600 11px var(--mono);white-space:nowrap}.chip:hover{border-color:var(--acc);z-index:3}.chip img{width:22px;height:22px;object-fit:contain}.chip .v{display:flex;flex-direction:column;line-height:1.15;font-size:10.5px}.chip .v small{color:var(--dim);font-weight:500;font-size:9.5px}.chip.sel{background:#15140f;border-color:#4a3d16}
/* game wall */
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px;align-items:center}.chips button{font:600 10.5px var(--mono);letter-spacing:.5px;padding:4px 10px;border-radius:5px;border:1px solid var(--edge2);background:var(--panel);color:var(--dim);cursor:pointer;display:inline-flex;align-items:center;gap:6px}.chips button.on{border-color:var(--acc);color:var(--fg);background:rgba(232,179,57,.1)}.chips button img{width:14px;height:14px;object-fit:contain}.chips .sp{flex:1}
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(236px,1fr));gap:8px}
.gc{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:10px 10px 9px;display:flex;flex-direction:column;gap:7px;position:relative}.gc.lk{cursor:pointer}.gc.lk:hover{border-color:var(--edge2)}.gc.top{border-color:#4a3d16}
.gc .teams{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:4px}.gc .t{display:flex;flex-direction:column;align-items:center;gap:2px;text-align:center}.gc .t img{width:44px;height:44px;object-fit:contain}.gc .t b{font-size:12.5px;line-height:1.1}.gc .t small{color:var(--dim);font:500 10px var(--mono)}.gc .t .rk{color:var(--acc);font:700 9.5px var(--mono)}
.gc .mid{display:flex;flex-direction:column;align-items:center;gap:1px;font:500 10px var(--mono);color:var(--dim);min-width:68px;text-align:center}.gc .mid b{color:var(--fg);font-size:11px}.gc .mid .at{color:var(--mute)}
.gc .tilt{height:7px;border-radius:2px;background:var(--s3);overflow:hidden;display:flex}.gc .tilt i{display:block;height:100%}.gc .tilt .a{background:var(--s3)}.gc .tilt .f{background:var(--acc)}.gc .tilt .u{background:#3a3b40}
.gc .nums{display:flex;justify-content:space-between;font:600 10.5px var(--mono);color:var(--dim)}.gc .nums b{color:var(--fg)}.gc .nums .c{color:var(--mute);font-weight:500}
.gc .tagl{position:absolute;top:7px;left:10px;font:600 8.5px var(--mono);letter-spacing:1px;color:var(--mute)}.gc .tagr{position:absolute;top:7px;right:10px;font:600 8.5px var(--mono);letter-spacing:1px;color:var(--acc)}
/* bar panels */
.panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}
.card{border:1px solid var(--edge);border-radius:10px;background:var(--panel);padding:12px 14px}.card h3{margin:0 0 8px;font:600 10.5px var(--mono);letter-spacing:2px;text-transform:uppercase;color:var(--dim);display:flex;justify-content:space-between;align-items:baseline;gap:8px}.card h3 span{font:400 11px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}
.brow{display:grid;grid-template-columns:minmax(165px,1.2fr) 1fr auto;gap:8px;align-items:center;padding:4px 0;font-size:12px}.brow .who{display:flex;align-items:center;gap:6px;min-width:0}.brow .who img{width:18px;height:18px;object-fit:contain;flex:none}.brow .who b{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.brow .who small{color:var(--dim);font:500 10px var(--mono);white-space:nowrap}
.brow .bar{position:relative;height:10px;background:var(--s3);border-radius:2px}.brow .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:2px;background:var(--acc)}.brow .bar i.g{background:var(--green)}.brow .bar i.b{background:var(--blue)}.brow .bar em{position:absolute;top:-3px;bottom:-3px;border-left:1px solid var(--fg);opacity:.5}
.brow .n{font:600 11.5px var(--mono);text-align:right;white-space:nowrap}.brow .n small{color:var(--dim);font-weight:500;margin-left:5px}
.mkgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}
.recrow{display:grid;grid-template-columns:86px 1fr auto;gap:8px;align-items:center;padding:4px 0;font-size:12px}.recrow .ty{font:600 9.5px var(--mono);letter-spacing:1px;color:var(--mute)}.recrow .bar{height:9px;background:var(--s3);border-radius:2px;overflow:hidden;display:flex}.recrow .bar i{display:block;height:100%}.recrow .bar .w{background:var(--green)}.recrow .bar .l{background:var(--red)}.recrow .n{font:600 12px var(--mono);white-space:nowrap}.recrow .n small{color:var(--dim);font-weight:400;margin-left:6px}
.note{color:var(--mute);font-size:10.5px;margin:8px 0 0}
/* standings */
.stand{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}
.srow{display:grid;grid-template-columns:22px minmax(150px,1.4fr) 1fr 58px;gap:6px;align-items:center;padding:3px 0;font-size:12px}.srow .i{color:var(--mute);font:500 10px var(--mono)}.srow .who{display:flex;align-items:center;gap:6px;min-width:0}.srow .who img{width:18px;height:18px;object-fit:contain}.srow .who b{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.srow .who .rk{color:var(--acc);font:700 9.5px var(--mono)}.srow .bar{height:8px;background:var(--s3);border-radius:2px;overflow:hidden}.srow .bar i{display:block;height:100%;background:var(--blue)}.srow .n{font:600 11px var(--mono);text-align:right}
/* list view */
table{border-collapse:collapse;width:100%;font-size:12px}th{font:600 9.5px var(--mono);letter-spacing:1px;text-transform:uppercase;color:var(--mute);text-align:left;padding:6px 8px;border-bottom:1px solid var(--edge2);cursor:pointer;white-space:nowrap}th.srt-asc::after{content:' ▲'}th.srt-desc::after{content:' ▼'}td{padding:6px 8px;border-bottom:1px solid var(--edge);vertical-align:middle;white-space:nowrap}tr:hover td{background:var(--s2)}
.tm{display:inline-flex;align-items:center;gap:6px}.tm img{width:18px;height:18px;object-fit:contain}.tm small{color:var(--dim)}.tm .rk{font:600 9.5px var(--mono);color:var(--acc)}.mono{font-family:var(--mono)}.dim{color:var(--dim)}
.empty{color:var(--mute);padding:12px;border:1px dashed var(--edge2);border-radius:8px;text-align:center}
.foot{margin-top:26px;padding-top:12px;border-top:1px solid var(--edge);color:var(--mute);font:400 11px/1.6 var(--sans)}
@media (max-width:760px){.wrap{padding:12px}h1{font-size:20px}#hdr .tag,#hdr .hl{display:none}.tlhead,.lane{grid-template-columns:90px 1fr}.bub{min-width:88px}}
"""
SCSS, SCSS_VARS = brand.themed_css(SCSS, 'scss')


SJS = r"""
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LG=J.leagues,LGBY={};LG.forEach(l=>LGBY[l.key]=l);const SHELL=!!J.shell;
let SEL=SHELL?LG[0].key:(new URLSearchParams(location.hash.replace('#','')).get('lg')||'nfl');if(!LGBY[SEL])SEL=LG[0].key;
const TZ='America/Chicago';
const CT=d=>new Date(d).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:TZ}).replace(':00','');
const DAY=d=>new Date(d).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:TZ});
const DAYS=d=>new Date(d).toLocaleDateString('en-US',{weekday:'short',timeZone:TZ});
const DKEY=d=>new Date(d).toLocaleDateString('en-CA',{timeZone:TZ});
const HOUR=d=>{const p=new Intl.DateTimeFormat('en-US',{hour:'numeric',minute:'numeric',hour12:false,timeZone:TZ}).formatToParts(new Date(d));const h=+p.find(x=>x.type==='hour').value%24,m=+p.find(x=>x.type==='minute').value;return h+m/60};
const TODAY=DKEY(new Date());
const L=t=>t&&t.logo?`<img src="https://a.espncdn.com/i/teamlogos/${t.logo}" alt="" onerror="this.style.visibility='hidden'">`:'';
const tm=(t,nm)=>`<span class="tm">${L(t)}${t.rank?`<span class="rk">${t.rank}</span>`:''}<b>${esc(nm?t.name:t.abbr)}</b>${t.rec?`<small>${esc(t.rec)}</small>`:''}</span>`;
const fav=g=>{const m=(g.odds||'').match(/^([A-Z0-9&.' -]+?)\s*(-?\d+(\.\d+)?)$/);return m?{team:m[1].trim(),line:+m[2]}:null};
const isML=f=>!!f&&Math.abs(f.line)>=100;const prob=l=>l<0?(-l)/(-l+100):100/(l+100);
const implied=g=>{const f=fav(g),ou=+g.ou;if(!f)return null;const h=f.team===g.home.abbr;if(isML(f)){const p=100*prob(f.line);return h?{home:p,away:100-p,pct:true}:{away:p,home:100-p,pct:true}}if(!ou)return null;const favTot=(ou-f.line)/2;return h?{home:favTot,away:ou-favTot}:{away:favTot,home:ou-favTot}};
const fmtI=(im,k)=>im?(im.pct?im[k].toFixed(0)+'%':im[k].toFixed(1)):'';
const games=J.games.slice().sort((a,b)=>a.date<b.date?-1:1);const byLg={};games.forEach(g=>(byLg[g.sport]=byLg[g.sport]||[]).push(g));
const TL={};games.forEach(g=>{TL[g.sport+'|'+g.away.abbr]=g.away;TL[g.sport+'|'+g.home.abbr]=g.home});const teamOf=(sp,ab)=>TL[sp+'|'+String(ab||'').replace('@','')]||{abbr:String(ab||'').replace('@','')};
const lgName=g=>g.sport==='soccer'?(J.soccer[g.lg]||g.lg):(LGBY[g.sport]||{label:g.sport}).label;
const open=(l)=>{if(!SHELL&&l&&l.page&&l.page!=='#')location.href=l.page};
const seqStrip=(seq,n)=>seq&&seq.length?`<span class="seq" title="last ${Math.min(n,seq.length)} graded positions, oldest → newest">${seq.slice(-n).map(r=>`<i class="${r}"></i>`).join('')}</span>`:'';
// ---- 1. sports as bubbles — size = games this week
function rail(){const el=$('#sports');if(!el||SHELL){if(el)el.hidden=true;return}
  const mx=Math.max(1,...LG.map(l=>(byLg[l.key]||[]).length));
  el.innerHTML=LG.map(l=>{const G=byLg[l.key]||[];const n=G.length,td=G.filter(g=>DKEY(g.date)===TODAY).length;const R=J.records&&J.records[l.key];let rec='';
    if(R){let w=0,x=0;Object.values(R.by||{}).forEach(b=>{w+=b.W;x+=b.L});if(w+x)rec=`<small>model <b>${w}-${x}</b></small>${seqStrip(R.seq,20)}`}
    const d=Math.round(60+56*Math.sqrt(n/mx));
    return `<div class="bub${l.key===SEL?' on':''}" data-k="${l.key}" title="${esc(l.label)} · ${n} games this week"><span class="o" style="width:${d}px;height:${d}px"><img src="${l.logo}" alt="" onerror="this.style.visibility='hidden'"><span class="n">${n}</span></span><b>${l.label}</b><small>${td?td+' today · ':''}${n} this week</small><span class="${l.status==='live'?'live':'shell'}">${l.status==='live'?'PLAYER MODEL':'SCHEDULE + LINES'}</span>${rec}</div>`}).join('');
  el.querySelectorAll('.bub').forEach(d=>d.onclick=()=>{SEL=d.dataset.k;history.replaceState(null,'','#lg='+SEL);render()})}
// ---- 2. today on a clock — one lane per league, every game at its kickoff
function timeline(){const el=$('#tl');let day=TODAY;let T=games.filter(g=>DKEY(g.date)===day);
  if(!T.length){const nxt=games.find(g=>DKEY(g.date)>TODAY);if(nxt){day=DKEY(nxt.date);T=games.filter(g=>DKEY(g.date)===day)}}
  $('#tlH').innerHTML=`${day===TODAY?'today':'next up'} · ${T.length?DAY(T[0].date):''} <span>${T.length} games across ${new Set(T.map(lgName)).size} leagues on one clock (Central) · each chip sits at its kickoff · the line under the logos is the favorite · click a game to open its league</span>`;
  if(!T.length){el.innerHTML='<div class="empty">nothing scheduled in the slate window</div>';return}
  const hs=T.map(g=>HOUR(g.date));const h0=Math.floor(Math.min(...hs)),h1=Math.min(24,Math.ceil(Math.max(...hs))+1.25);const span=h1-h0;const X=h=>100*(h-h0)/span;
  const laneKey=g=>SHELL&&g.sport==='soccer'?g.lg:g.sport;const lanes=[...new Set(T.map(laneKey))];lanes.sort((a,b)=>(a===SEL?-1:b===SEL?1:0)||(LG.findIndex(l=>l.key===a)-LG.findIndex(l=>l.key===b)));
  const W=Math.max(600,(el.clientWidth||1200)-150-24);const chipW=118;const minGap=span*chipW/W;
  const ticks=[];for(let h=Math.ceil(h0);h<=h1;h++)ticks.push(h);
  const axis=`<div class="tlhead"><span></span><div class="tlaxis">${ticks.map(h=>`<span style="left:${X(h)}%">${h%12||12}${h<12||h===24?'a':'p'}</span>`).join('')}</div></div>`;
  const nowH=day===TODAY?HOUR(new Date()):null;
  el.innerHTML=axis+lanes.map(k=>{const G=T.filter(g=>laneKey(g)===k).sort((a,b)=>HOUR(a.date)-HOUR(b.date));const rows=[];const placed=G.map(g=>{const h=HOUR(g.date);let r=rows.findIndex(end=>h-end>=minGap);if(r<0){r=rows.length;rows.push(h)}else rows[r]=h;return {g,h,r}});
    const l=LGBY[k]||{label:J.soccer[k]||k,logo:J.soccerLogo&&J.soccerLogo[k]};
    return `<div class="lane${k===SEL?' on':''}"><div class="ll"><img src="${l.logo||''}" alt="" onerror="this.style.visibility='hidden'"><div><b>${esc(l.label)}</b><br><small>${G.length} game${G.length===1?'':'s'}</small></div></div><div class="lf" style="height:${rows.length*50+6}px">${ticks.map(h=>`<i class="grid" style="left:${X(h)}%"></i>`).join('')}${nowH!=null&&nowH>=h0&&nowH<=h1?`<i class="now" style="left:${X(nowH)}%" title="now"></i>`:''}
      ${placed.map(({g,h,r})=>{const f=fav(g);const lg=LGBY[g.sport];return `<a class="chip${g.sport===SEL?' sel':''}" ${!SHELL&&lg&&lg.page?`href="${lg.page}"`:''} style="left:${X(h)}%;top:${4+r*50}px" title="${esc(g.away.name)} ${g.neutral?'vs':'@'} ${esc(g.home.name)} · ${CT(g.date)} CT${g.tv?' · '+esc(g.tv.split(',')[0]):''}${f?' · '+esc(f.team)+' '+f.line:''}${g.ou?' · O/U '+g.ou:''}${g.note?' · '+esc(g.note):''}">${L(g.away)}${L(g.home)}<span class="v">${esc(g.away.abbr)}<small>${g.neutral?'vs':'@'}</small>${esc(g.home.abbr)}</span><span class="v" style="margin-left:2px"><small>${CT(g.date)}</small>${f?`${esc(f.team)} ${f.line}`:'<small>no line</small>'}${g.ou?`<small>o/u ${g.ou}</small>`:''}</span></a>`}).join('')}</div></div>`}).join('')}
// ---- 3. the week as a wall of games for the selected league
let DAYF='auto',SUBF='all',LIST=false,sortK='date',sortA=true,DAYSEL='';
function week(){const l=LGBY[SEL];const All=(byLg[SEL]||[]);const days=[...new Set(All.map(g=>DKEY(g.date)))].sort();if(DAYSEL!==SEL){DAYSEL=SEL;SUBF='all';DAYF=All.length>20?(days.find(d=>d>=TODAY)||days[0]||'all'):'all'}const subs=[...new Set(All.map(g=>g.lg))];
  $('#weekH').innerHTML=`${esc(l.label)} · the week <span>${All.length} games · ${All.filter(g=>g.odds).length} with DraftKings lines · gold bar = the favorite's share — of the expected points when the line is a spread (implied team totals), of the win odds when it is a moneyline</span>${!SHELL&&l.page&&l.page!=='#'?`<a class="go" href="${l.page}">${l.status==='live'?'open the '+esc(l.label)+' dashboard →':esc(l.label)+' →'}</a>`:''}`;
  const subChip=s=>`<button data-s="${s}" class="${SUBF===s?'on':''}">${J.soccerLogo&&J.soccerLogo[s]?`<img src="${J.soccerLogo[s]}" alt="">`:''}${esc(J.soccer[s]||s)} <span class="dim">${All.filter(g=>g.lg===s).length}</span></button>`;
  $('#filt').innerHTML=`<button data-d="all" class="${DAYF==='all'?'on':''}">all days</button>${days.map(d=>`<button data-d="${d}" class="${DAYF===d?'on':''}">${DAY(All.find(g=>DKEY(g.date)===d).date)} <span class="dim">${All.filter(g=>DKEY(g.date)===d).length}</span></button>`).join('')}${subs.length>1?`<span style="width:10px"></span><button data-s="all" class="${SUBF==='all'?'on':''}">all leagues</button>${subs.map(subChip).join('')}`:''}<span class="sp"></span><button data-v="wall" class="${!LIST?'on':''}">wall</button><button data-v="list" class="${LIST?'on':''}">sortable list</button>`;
  $('#filt').querySelectorAll('button').forEach(b=>b.onclick=()=>{if(b.dataset.d)DAYF=b.dataset.d;if(b.dataset.s)SUBF=b.dataset.s;if(b.dataset.v)LIST=b.dataset.v==='list';week()});
  const G=All.filter(g=>(DAYF==='all'||DKEY(g.date)===DAYF)&&(SUBF==='all'||g.lg===SUBF));
  const score=g=>{const f=fav(g);const rk=(g.away.rank?1:0)+(g.home.rank?1:0);const sp=f?(isML(f)?60*(prob(f.line)-.5):Math.abs(f.line)):15;return (g.ou?+g.ou:0)/2-sp+rk*12+(g.tv?3:0)};const top=G.length?G.slice().sort((a,b)=>score(b)-score(a))[0]:null;
  if(!G.length){$('#week').innerHTML='<div class="empty">no games for this filter</div>';return}
  if(LIST){const rows=G.map(g=>{const f=fav(g),im=implied(g);return {g,f,im,date:g.date,match:g.away.abbr+'@'+g.home.abbr,line:f?Math.abs(f.line):99,tot:+g.ou||0,tv:g.tv||'',sub:g.sub||'',venue:g.venue||''}});
    const V={date:r=>r.date,match:r=>r.match,line:r=>r.line,tot:r=>r.tot,tv:r=>r.tv,sub:r=>r.sub,venue:r=>r.venue,imp:r=>r.im?Math.max(r.im.away,r.im.home):0};rows.sort((a,b)=>{const x=V[sortK](a),y=V[sortK](b);return (x<y?-1:x>y?1:0)*(sortA?1:-1)});
    const th=(k,lab)=>`<th data-k="${k}" class="${sortK===k?(sortA?'srt-asc':'srt-desc'):''}">${lab}</th>`;
    $('#week').innerHTML=`<table><thead><tr>${th('date','kick (CT)')}${subs.length>1?th('sub','league'):''}${th('match','matchup')}${th('line','favorite · line')}${th('tot','total')}${th('imp','implied')}${th('tv','tv')}${th('venue','venue')}</tr></thead><tbody>${rows.map(r=>`<tr><td class="mono">${DAY(r.date)} ${CT(r.date)}</td>${subs.length>1?`<td class="dim">${esc(r.sub)}</td>`:''}<td>${tm(r.g.away)} <span class="dim">${r.g.neutral?'vs':'@'}</span> ${tm(r.g.home)}</td><td>${r.f?`<b>${esc(r.f.team)} ${r.f.line>0?'+':''}${r.f.line}</b>`:'<span class="dim">—</span>'}</td><td class="mono">${r.g.ou||'<span class="dim">—</span>'}</td><td class="mono dim">${r.im?`${fmtI(r.im,'away')} · ${fmtI(r.im,'home')}`:''}</td><td class="dim">${esc(r.tv.split(',')[0])}</td><td class="dim">${esc(r.venue)}</td></tr>`).join('')}</tbody></table>`;
    $('#week').querySelectorAll('th[data-k]').forEach(t=>t.onclick=()=>{const k=t.dataset.k;if(sortK===k)sortA=!sortA;else{sortK=k;sortA=!(k==='tot'||k==='imp')}week()});return}
  const card=g=>{const f=fav(g),im=implied(g);const hf=f&&f.team===g.home.abbr,af=f&&f.team===g.away.abbr;const aw=im?100*im.away/(im.away+im.home):50;
    const T=(t,isF)=>`<div class="t">${L(t)}<b>${esc(t.abbr)}</b><small>${t.rank?`<span class="rk">#${t.rank}</span> `:''}${esc(t.rec||'')}</small></div>`;
    return `<div class="gc${!SHELL&&l.page&&l.page!=='#'?' lk':''}${g===top?' top':''}" data-p="${l.page||''}">${g.sub?`<span class="tagl">${esc(g.sub).toUpperCase()}</span>`:g.note?`<span class="tagl">${esc(g.note).toUpperCase()}</span>`:''}${g===top?'<span class="tagr">MARQUEE</span>':''}
      <div class="teams" style="margin-top:8px">${T(g.away,af)}<div class="mid"><span>${DAYS(g.date)}</span><b>${CT(g.date)}</b><span class="at">${g.neutral?'vs':'@'}</span>${g.tv?`<span>${esc(g.tv.split(',')[0])}</span>`:''}</div>${T(g.home,hf)}</div>
      <div class="tilt" title="${im?(im.pct?`win odds from the moneyline: ${esc(g.away.abbr)} ${fmtI(im,'away')} · ${esc(g.home.abbr)} ${fmtI(im,'home')}`:`implied ${esc(g.away.abbr)} ${im.away.toFixed(1)} · ${esc(g.home.abbr)} ${im.home.toFixed(1)}`):'no line yet'}">${im?`<i class="${af?'f':'u'}" style="width:${aw.toFixed(1)}%"></i><i class="${hf?'f':'u'}" style="width:${(100-aw).toFixed(1)}%"></i>`:'<i class="a" style="width:100%"></i>'}</div>
      <div class="nums"><span>${im?`<b>${fmtI(im,'away')}</b>`:''}</span><span class="c">${f?`<b>${esc(f.team)} ${f.line>0?'+':''}${f.line}</b>${g.ou?` · o/u <b>${g.ou}</b>`:''}`:'no line yet'}</span><span>${im?`<b>${fmtI(im,'home')}</b>`:''}</span></div></div>`};
  $('#week').innerHTML=`<div class="wall">${G.map(card).join('')}</div>`;
  $('#week').querySelectorAll('.gc.lk').forEach(d=>d.onclick=()=>open(l))}
// ---- 4. who's soft (player model) + where the money sits (lines) + model record — all bars
function edges(){const l=LGBY[SEL];const T=J.teasers&&J.teasers[SEL];const el=$('#edges');const G=(byLg[SEL]||[]).filter(g=>DKEY(g.date)>=TODAY);
  const tick=`<em style="left:50%"></em>`;
  const short=n=>{const p=String(n).split(' ');return p.length>1?p[0][0]+'. '+p.slice(1).join(' '):n};
  const edgeCard=(mk,rows)=>`<div class="card"><h3>${esc(T.labels&&T.labels[mk]||mk)} <span>softest opponents</span></h3>${rows.map(r=>{const N=T.n||32;const w=Math.max(6,100*(N+1-r.rank)/N);const o=teamOf(SEL,r.opp);return `<div class="brow"><span class="who">${L(teamOf(SEL,r.team))}<b title="${esc(r.player)}">${esc(short(r.player))}</b><small>vs</small>${L(o)}<small>${esc(o.abbr)}</small></span><span class="bar" title="${esc(o.abbr)} ranks ${r.rank} of ${N} in this stat allowed (1 = allows the most)"><i class="g" style="width:${w}%"></i>${tick}</span><span class="n">${r.proj}<small>#${r.rank}</small></span></div>`}).join('')}</div>`;
  const favs=G.map(g=>({g,f:fav(g)})).filter(x=>x.f).sort((a,b)=>Math.abs(b.f.line)-Math.abs(a.f.line)).slice(0,6);const mxl=favs.length?Math.abs(favs[0].f.line):1;
  const tots=G.filter(g=>+g.ou).sort((a,b)=>+b.ou-+a.ou).slice(0,6);const mxt=tots.length?+tots[0].ou:1,mnt=tots.length?Math.min(...G.filter(g=>+g.ou).map(g=>+g.ou)):0;
  const favCard=`<div class="card"><h3>biggest favorites <span>${esc(l.label)} · this week</span></h3>${favs.map(({g,f})=>{const t=teamOf(SEL,f.team),o=f.team===g.home.abbr?g.away:g.home;return `<div class="brow"><span class="who">${L(t)}<b>${esc(t.abbr)}</b><small>vs ${esc(o.abbr)}</small></span><span class="bar"><i style="width:${(100*Math.abs(f.line)/mxl).toFixed(0)}%"></i></span><span class="n">${f.line>0?'+':''}${f.line}<small>${DAYS(g.date)}</small></span></div>`}).join('')||'<div class="empty">no lines posted yet</div>'}</div>`;
  const totCard=`<div class="card"><h3>highest totals <span>most scoring expected</span></h3>${tots.map(g=>`<div class="brow"><span class="who">${L(g.away)}${L(g.home)}<b>${esc(g.away.abbr)} ${g.neutral?'vs':'@'} ${esc(g.home.abbr)}</b></span><span class="bar"><i class="b" style="width:${(100*(+g.ou-mnt*.9)/(mxt-mnt*.9)).toFixed(0)}%"></i></span><span class="n">${g.ou}<small>${DAYS(g.date)}</small></span></div>`).join('')||'<div class="empty">no totals posted yet</div>'}</div>`;
  const R=J.records&&J.records[SEL];const LBL={ML:'moneyline',ATS:'spread',TOTAL:'total',PROP:'props',TD:'anytime TD',DFS:'DFS',ALL:'all'};let recCard='';
  if(R){const rows=Object.entries(R.by).filter(([t,b])=>b.W+b.L+b.P);let w=0,x=0,pend=0;rows.forEach(([,b])=>{w+=b.W;x+=b.L});Object.values(R.by).forEach(b=>pend+=b.pending);
    recCard=w+x===0?`<div class="card"><h3>model record <span>frozen before kickoff, graded after</span></h3><div class="empty">${pend} positions frozen, none graded yet — the first results land after tonight's games</div></div>`:`<div class="card"><h3>model record <span>frozen before kickoff, graded after</span></h3><div class="recrow"><span class="ty">ALL</span><span class="bar"><i class="w" style="width:${w+x?100*w/(w+x):0}%"></i><i class="l" style="width:${w+x?100*x/(w+x):0}%"></i></span><span class="n">${w}-${x}<small>${w+x?(100*w/(w+x)).toFixed(0)+'%':''}</small></span></div>${rows.map(([t,b])=>`<div class="recrow"><span class="ty">${LBL[t]||t}</span><span class="bar"><i class="w" style="width:${b.W+b.L?100*b.W/(b.W+b.L):0}%"></i><i class="l" style="width:${b.W+b.L?100*b.L/(b.W+b.L):0}%"></i></span><span class="n">${b.W}-${b.L}${b.P?'-'+b.P:''}<small>${b.pending} open</small></span></div>`).join('')}<div style="margin-top:8px">${seqStrip(R.seq,60)}</div><p class="note">green = win, red = loss, oldest → newest · break-even at −110 is 52.4% · every graded position is on the dashboard</p></div>`}
  else if(l.status==='live')recCard=`<div class="card"><h3>model record</h3><div class="empty">nothing graded yet for ${esc(l.label)}</div></div>`;
  const mk=T&&Object.entries(T.markets).filter(([,r])=>r.length);
  $('#edgesH').innerHTML=`${esc(l.label)} · the edges <span>${mk&&mk.length?`green bar = how soft the opponent is in that exact stat (#1 of ${T.n||32} allows the most; tick = league middle) · number = the model's projection · from the ${esc(l.label)} player model${T.week?', week '+T.week:''}`:l.status==='live'?'the player model has no games on this slate yet':'player matchups for '+esc(l.label)+' arrive with a box-score source — lines are live now'}</span>`;
  el.innerHTML=(mk&&mk.length?`<div class="mkgrid">${mk.map(([k,r])=>edgeCard(k,r)).join('')}</div><div style="height:10px"></div>`:'')+`<div class="panels">${favCard}${totCard}${recCard}</div>`}
// ---- 5. standings from the records on the slate, as bars
function standings(){const el=$('#stand');if(!el)return;const G=byLg[SEL]||[];const T={};
  G.forEach(g=>[g.away,g.home].forEach(t=>{if(!t.rec||T[t.abbr])return;const m=t.rec.match(/^(\d+)-(\d+)(?:-(\d+))?/);if(!m)return;T[t.abbr]={t,w:+m[1],l:+m[2],d:m[3]!=null?+m[3]:null,rec:t.rec,sub:g.sub}}));
  const pct=r=>r.w/((r.w+r.l+(r.d||0))||1);const rows=Object.values(T).sort((a,b)=>pct(b)-pct(a)||b.w-a.w);
  if(!rows.length){el.innerHTML='';$('#standH').innerHTML='';return}
  const groups={};rows.forEach(r=>(groups[r.sub||'']=groups[r.sub||'']||[]).push(r));
  if(Object.keys(groups).length===1&&rows.length>12){const k=Object.keys(groups)[0];const per=Math.ceil(rows.length/Math.min(3,Math.ceil(rows.length/11)));delete groups[k];for(let i=0;i<rows.length;i+=per)groups[(k?k+' · ':'')+`${i+1}–${Math.min(rows.length,i+per)}`]=rows.slice(i,i+per)}
  $('#standH').innerHTML=`${esc(LGBY[SEL].label)} · records <span>every team on this week's slate, bar = win percentage · from the records ESPN carries on the schedule</span>`;
  el.innerHTML=`<div class="stand">${Object.entries(groups).map(([k,R])=>`<div class="card">${k?`<h3>${esc(k)}</h3>`:''}${R.map(r=>`<div class="srow"><span class="i">${rows.indexOf(r)+1}</span><span class="who">${L(r.t)}${r.t.rank?`<span class="rk">#${r.t.rank}</span>`:''}<b>${esc(r.t.name)}</b></span><span class="bar"><i style="width:${(100*pct(r)).toFixed(0)}%"></i></span><span class="n">${esc(r.rec)}</span></div>`).join('')}</div>`).join('')}</div>`}
function render(){rail();timeline();week();edges();standings()}
render();window.addEventListener('resize',()=>timeline());
"""

HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">"""
CSS = r"""
:root{--mono:'JetBrains Mono',ui-monospace,Menlo,monospace;--sans:Inter,system-ui,-apple-system,Segoe UI,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 var(--sans)}a{color:inherit;text-decoration:none}img{-webkit-user-drag:none;user-select:none}
#hdr{display:flex;align-items:center;gap:14px;padding:0 20px;height:48px;border-bottom:1px solid var(--e);background:#050506;position:sticky;top:0;z-index:5}
.brand{font:800 15px/1 var(--mono);letter-spacing:5px}.brand i{color:var(--acc);font-style:normal;margin-right:7px}
.hl{display:flex;gap:5px;margin-left:auto}.hl a{border:1px solid var(--e2);border-radius:4px;padding:4px 11px;font:600 10.5px var(--mono);letter-spacing:1px;color:var(--dim)}
.hl a:hover{color:var(--fg);border-color:var(--acc)}.hl a.acc{color:var(--acc);border-color:#3a3322}
main{max-width:1180px;margin:0 auto;padding:34px 20px 70px}
h1{font:800 30px/1.15 var(--sans);letter-spacing:-.5px;margin:0 0 6px}
.sub{color:var(--dim);font-size:13.5px;margin:0}
.hero{display:flex;align-items:center;gap:16px;margin:0 0 26px}
.hero>.rmask{flex:none;width:82px;height:72px}
.hero .kel{flex:none;margin:14px 2px 0 -26px;display:block;animation:rmbob 3.6s ease-in-out infinite}
.hero .kel .rmask{width:50px;height:50px;display:block}
@keyframes rmbob{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-6px) rotate(2deg)}}
#rainfx{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
#hdr,main{position:relative;z-index:1}
@media(prefers-reduced-motion:reduce){.hero .kel{animation:none}#rainfx{display:none}}
@media(max-width:640px){.hero{gap:10px}.hero>.rmask{width:56px;height:50px}.hero .kel{margin-left:-18px}.hero .kel .rmask{width:34px;height:34px}}
h2{font:600 10.5px var(--mono);letter-spacing:2.2px;text-transform:uppercase;color:var(--mute);margin:34px 0 12px;display:flex;align-items:baseline;gap:10px}
h2 span{font:400 11.5px var(--sans);letter-spacing:0;text-transform:none;color:var(--mute)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:10px}
.sp{display:flex;flex-direction:column;gap:9px;border:1px solid var(--e);border-radius:10px;background:var(--p);padding:14px 15px;transition:none;min-height:116px}
.sp:hover{border-color:var(--acc);background:var(--p2)}
.sp .t{display:flex;align-items:center;gap:10px;min-width:0}
.sp .t img{width:30px;height:30px;object-fit:contain;flex:none}
.sp .t b{font:700 16px/1.2 var(--sans);letter-spacing:-.2px}
.sp .k{font:600 9.5px var(--mono);letter-spacing:1.3px;text-transform:uppercase;color:var(--mute)}
.sp .k i{font-style:normal;color:var(--acc)}
.sp .m{margin-top:auto;display:flex;align-items:baseline;gap:8px;font:500 11.5px var(--mono);color:var(--dim)}
.sp .m b{font-weight:700;color:var(--fg)}.sp .m .g{color:var(--g)}.sp .m .r{color:var(--r)}
.sp.soon{opacity:.45}.sp.soon:hover{border-color:var(--e)}
.perf{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:9px;margin-bottom:12px}
.perf>div{border:1px solid var(--e);border-radius:8px;background:var(--p);padding:11px 13px}
.perf span{display:block;font:600 9px var(--mono);letter-spacing:1.4px;text-transform:uppercase;color:var(--mute)}
.perf b{display:block;font:700 21px/1.25 var(--mono);margin-top:3px}
.perf small{display:block;font:500 10.5px var(--mono);color:var(--dim)}
.perf b.g{color:var(--g)}.perf b.r{color:var(--r)}
table{border-collapse:collapse;width:100%;font-size:12.5px;border:1px solid var(--e);border-radius:8px;overflow:hidden}
th{font:600 9.5px var(--mono);letter-spacing:1.2px;text-transform:uppercase;color:var(--mute);text-align:left;padding:8px 11px;background:var(--p);border-bottom:1px solid var(--e2);white-space:nowrap}
td{padding:8px 11px;border-bottom:1px solid var(--e);white-space:nowrap}tbody tr:last-child td{border-bottom:0}
tr.lg{cursor:pointer}tr.lg:hover td{background:var(--p)}
.r{text-align:right}.mono{font-family:var(--mono)}.dim{color:var(--dim)}.mute{color:var(--mute)}.g{color:var(--g)}.rd{color:var(--r)}
.lgn{display:inline-flex;align-items:center;gap:8px;font-weight:600}.lgn img{width:17px;height:17px;object-fit:contain}
.bar{display:inline-flex;align-items:center;gap:7px;font:600 11px var(--mono)}
.bar .t{position:relative;width:84px;height:6px;background:var(--p3);border-radius:2px;overflow:hidden}
.bar .t i{display:block;height:100%}.bar .t em{position:absolute;top:0;bottom:0;width:2px;background:var(--amber)}
.seq{display:inline-flex;gap:2px}.seq i{width:5px;height:11px;border-radius:1px;display:block}
.note{color:var(--mute);font:500 11px/1.65 var(--mono);margin:10px 0 0}
.foot{margin-top:40px;padding-top:14px;border-top:1px solid var(--e);color:var(--mute);font:500 10.5px/1.75 var(--mono)}
.foot b{color:var(--dim);font-weight:500}
@media(max-width:640px){main{padding:24px 14px 50px}h1{font-size:24px}.grid{grid-template-columns:1fr}}
"""
CSS, CSS_VARS = brand.themed_css(CSS, 'css')


def page(games, pulled):
    """Layer 0: the sports, each linked to its dashboard, and how the models have actually scored. Nothing else."""
    cnt = {}
    for g in games: cnt[g['sport']] = cnt.get(g['sport'], 0) + 1
    REC = model_records(); BT = game_model_backtest()
    KIND = {'nfl': 'defense-vs-position · player model · picks', 'cfb': 'defense-vs-position · 138 FBS teams',
            'nba': 'player model · matchups · picks', 'wnba': 'player model · matchups · picks', 'nhl': 'player model · matchups · picks',
            'tennis': 'elo model · atp + wta · match prices', 'ncaab': 'schedule &amp; lines', 'mlb': 'schedule &amp; lines', 'soccer': 'schedule &amp; lines · 7 leagues'}
    LGLBL = {'nfl': 'NFL', 'cfb': 'CFB', 'nba': 'NBA', 'nhl': 'NHL', 'wnba': 'WNBA'}
    def rec_line(k):
        r = REC.get(k)
        if not r: return '<span class="mute">no graded positions yet</span>'
        if not (r['W'] + r['L']): return '<span class="mute">%d live, none graded</span>' % r['pending']
        tone = 'g' if r['u'] > 0 else 'r' if r['u'] < 0 else ''
        wl = '%d-%d%s' % (r['W'], r['L'], '-%d' % r['P'] if r['P'] else '')
        return '<b>%s</b> <span class="%s">%s%.2fu</span>' % (wl, tone, '+' if r['u'] >= 0 else '', r['u'])
    def tile(k, label, pg, status, logo):
        n = cnt.get(k, 0)
        soon = status == 'shell' and not n
        img = '<img src="%s" alt="" onerror="this.style.display=\'none\'">' % logo if logo else ''
        gm = '<b>%d</b> this week' % n if n else '<span class="mute">no games in the window</span>'
        rec = (' &middot; ' + rec_line(k)) if REC.get(k) else ''
        return ('<a class="sp%s" href="%s"><span class="t">%s<b>%s</b></span><span class="k">%s</span><span class="m">%s%s</span></a>'
                % (' soon' if soon else '', pg, img, label, KIND.get(k, ''), gm, rec))
    tiles = ''.join(tile(k, l, p, s, i) for k, l, g, p, s, i in LEAGUES)
    # ---- model performance, per league, from the frozen ledgers
    BE = 0.5238
    def bar(hit):
        if hit is None: return '<span class="mute">—</span>'
        x = max(0, min(100, (hit - 0.3) / 0.4 * 100))
        return ('<span class="bar"><span class="t"><i style="width:%.0f%%;background:%s"></i><em style="left:%.0f%%"></em></span><b class="%s">%.1f%%</b></span>'
                % (x, 'var(--g)' if hit >= BE else 'var(--r)', (BE - 0.3) / 0.4 * 100, 'g' if hit >= BE else 'rd', 100 * hit))
    def seq(s):
        if not s: return ''
        col = lambda x: 'var(--g)' if x == 'W' else 'var(--r)' if x == 'L' else 'var(--mute)'
        return '<span class="seq">' + ''.join('<i style="background:%s"></i>' % col(x) for x in s[-24:]) + '</span>'
    LOGO = {k: i for k, l, g, p, s, i in LEAGUES}
    PG = {k: p for k, l, g, p, s, i in LEAGUES}
    rows = ''
    for k in ('nfl', 'nba', 'nhl', 'wnba'):
        r = REC.get(k)
        if not r: continue
        tone = 'g' if r['u'] > 0 else 'rd' if r['u'] < 0 else 'dim'
        wl = '%d-%d%s' % (r['W'], r['L'], '-%d' % r['P'] if r['P'] else '')
        roi = '' if r['roi'] is None else '%s%.1f%%' % ('+' if r['roi'] >= 0 else '', 100 * r['roi'])
        rows += ('<tr class="lg" data-go="%s"><td><span class="lgn"><img src="%s" alt="" onerror="this.style.display=\'none\'">%s</span></td>'
                 '<td class="r mono dim">%d</td><td class="r mono dim">%d</td><td class="mono">%s</td><td>%s</td>'
                 '<td class="r mono %s">%s%.2f</td><td class="r mono %s">%s</td><td>%s</td></tr>'
                 % (PG.get(k, ''), LOGO.get(k, ''), LGLBL.get(k, k.upper()), r['W'] + r['L'] + r['P'], r['pending'], wl, bar(r['hit']),
                    tone, '+' if r['u'] >= 0 else '', r['u'], tone, roi, seq(r['seq'])))
    tot = dict(W=sum(r['W'] for r in REC.values()), L=sum(r['L'] for r in REC.values()), P=sum(r['P'] for r in REC.values()),
               u=round(sum(r['u'] for r in REC.values()), 2), pend=sum(r['pending'] for r in REC.values()))
    dec = tot['W'] + tot['L']; hit = tot['W'] / dec if dec else None
    graded = tot['W'] + tot['L'] + tot['P']
    twl = '%d-%d%s' % (tot['W'], tot['L'], '-%d' % tot['P'] if tot['P'] else '')
    utone = 'g' if tot['u'] > 0 else 'r' if tot['u'] < 0 else ''
    per = '' if not graded else '%+.1f%% per position' % (100 * tot['u'] / graded)
    htxt = '&mdash;' if hit is None else '%.1f%%' % (100 * hit)
    htone = 'g' if hit and hit >= BE else 'r' if hit else ''
    bts = '%d-%d' % (BT['ats'][0], BT['ats'][1]) if BT else '&mdash;'
    btsub = 'ATS over %d held-out 2024-25 games' % BT['n'] if BT else 'no backtest on file'
    kp = ('<div><span>record</span><b>%s</b><small>%d graded &middot; %d live</small></div>'
          '<div><span>units</span><b class="%s">%s%.2f</b><small>%s</small></div>'
          '<div><span>hit rate</span><b class="%s">%s</b><small>break-even 52.4%% at &minus;110</small></div>'
          '<div><span>game model &middot; backtest</span><b>%s</b><small>%s</small></div>'
          '<div><span>slate</span><b>%d</b><small>games in the window &middot; pulled %s</small></div>'
          % (twl, graded, tot['pend'], utone, '+' if tot['u'] >= 0 else '', tot['u'], per, htone, htxt, bts, btsub, len(games), pulled))
    table_html = ('<table><thead><tr><th>league</th><th class="r">graded</th><th class="r">live</th><th>record</th>'
                  '<th>hit rate vs break-even</th><th class="r">units</th><th class="r">per play</th><th>last 24</th></tr></thead><tbody>'
                  + rows + '</tbody></table>') if rows else '<p class="note">No graded positions on file yet.</p>'
    nsport = len([1 for k, l, g, p, s_, i in LEAGUES if cnt.get(k)])
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN</title>
{HEAD}<style>{brand.THEME_CSS}{brand.alias_css("app")}{brand.SWITCH_CSS}{CSS_VARS}{CSS}</style>{brand.THEME_BOOT}</head><body>
<div id="hdr"><span class="brand">{brand.mascot("counting", 22, "rmask hdr")}RAINMAN</span><span class="hl"><a class="acc" href="arb.html">Arb Engine</a><a class="acc" href="social.html">Social</a>{brand.theme_switch_html()}</span></div>
<main>
<canvas id="rainfx" aria-hidden="true"></canvas>
<div class="hero">{brand.mascot("counting", 82, "rmask", anim=True)}<span class="kel">{brand.kelly("counting", 50, "rmask")}</span><div><h1>RAINMAN</h1>
<p class="sub">Matchup intelligence, one dashboard per sport.</p></div></div>
<h2>sports <span>{nsport} with games in the window</span></h2>
<div class="grid">{tiles}</div>
<h2>model performance <span>every position the models froze, graded against the line it was frozen at · one unit risked per position</span></h2>
<div class="perf">{kp}</div>
{table_html}
<p class="note">A win at −110 returns 0.909 and a loss costs 1, so 52.4% is break-even; the tick on each bar is that line. Records separate skill from variance somewhere past 300 positions — read these as a running tally, not a verdict. The NFL model's full breakdown, calibration and changelog live on <a href="rainman.html#v=pkhome" style="color:var(--acc)">its Model tab</a>.</p>
<div class="foot"><a href="brand.html" style="color:var(--accent-text)">brand</a> · RAINMAN · schedules, records and lines from ESPN's public scoreboard (pulled {pulled}) · player models from game logs (Pro Football Reference, ESPN, sportsdataverse, the Sackmann tennis archive) · built {built} · information, not advice</div>
</main>
<script>{brand.THEME_JS}</script>
<script>
(function(){{
 var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
 if (reduce) {{ document.querySelectorAll('#rainfx,animate').forEach(function(n){{n.remove()}}); return; }}
 var c = document.getElementById('rainfx'); if (!c) return; var g = c.getContext('2d');
 var W, H, drops = [], dpr = Math.min(devicePixelRatio || 1, 2);
 function mk(y){{ return {{x: Math.random()*W, y: y, l: (9 + Math.random()*30)*dpr,
                         v: (2.2 + Math.random()*4.4)*dpr, a: .06 + Math.random()*.26}}; }}
 function size(){{ W = c.width = innerWidth*dpr; H = c.height = innerHeight*dpr;
   c.style.width = innerWidth+'px'; c.style.height = innerHeight+'px';
   var n = Math.max(40, Math.min(190, Math.round(innerWidth*innerHeight/11000)));
   drops = []; for (var i=0;i<n;i++) drops.push(mk(Math.random()*H)); }}
 var col = '#2b6bff', fade = 1;
 function theme(){{ var cs = getComputedStyle(document.documentElement), t = document.documentElement.dataset.theme;
   col = (t === 'light' ? cs.getPropertyValue('--dim2') : cs.getPropertyValue('--accent')).trim() || col;
   fade = t === 'light' ? .5 : 1; }}                         // paper takes a lighter shower
 function tick(){{
   theme(); g.clearRect(0,0,W,H); g.lineWidth = 1.15*dpr; g.lineCap = 'round'; g.strokeStyle = col;
   for (var i=0;i<drops.length;i++){{ var d = drops[i];
     g.globalAlpha = d.a*fade; g.beginPath(); g.moveTo(d.x, d.y); g.lineTo(d.x + 1.3*dpr, d.y + d.l); g.stroke();
     d.y += d.v*2.1; if (d.y > H) drops[i] = mk(-d.l); }}
   g.globalAlpha = 1; requestAnimationFrame(tick); }}
 addEventListener('resize', size); size(); tick();
}})();
</script>

<script>document.querySelectorAll('tr.lg[data-go]').forEach(t=>{{if(t.dataset.go)t.onclick=()=>location.href=t.dataset.go}});</script>
</body></html>"""

LEAGUES_BY = {k: dict(key=k, label=l, page=p, status=s, logo=i) for k, l, g, p, s, i in LEAGUES}

def shell(key, label, games, pulled, logo=''):
    """Schedule-and-lines page for a league without a player data source yet (same page, one league)."""
    J = dict(games=games, leagues=[dict(key=key, label=label, page='#', status='shell', logo=logo)], soccer=SOCCER, soccerLogo=SOCCER_LOGO, pulled=pulled, shell=True, teasers={}, records={})
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    links = ''.join(f'<a href="{p}">{l}</a>' for k, l, g, p, s, i in LEAGUES)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · {label}</title>
{SHEAD}<style>{brand.THEME_CSS}{brand.alias_css("alt")}{brand.SWITCH_CSS}.brand .rmask{{vertical-align:-5px;margin-right:4px}}{SCSS_VARS}{SCSS}</style>{brand.THEME_BOOT}</head><body>
<div id="hdr"><a class="brand" href="index.html">{brand.mascot("counting", 20, "rmask hdr")}RAINMAN</a><span class="tag">{label} · schedule &amp; lines</span><span class="hl">{links}</span><span class="right">slate {pulled} · built {built}{brand.theme_switch_html()}</span></div>
<div class="wrap">
<h1><img src="{logo}" alt="" style="height:34px;vertical-align:middle;margin-right:10px" onerror="this.style.display='none'">{label}<small>Every game in the slate window on one clock, then as a wall of matchups with the DraftKings line, total and implied scores, plus the records ESPN carries on the schedule. Player matchups and the pick model arrive for {label} when a box-score source is wired in.</small></h1>
<div id="sports" class="bubs" hidden></div>
<h2 id="tlH"></h2><div id="tl" class="tlwrap"></div>
<h2 id="weekH"></h2><div id="filt" class="chips"></div><div id="week"></div>
<h2 id="edgesH"></h2><div id="edges"></div>
<h2 id="standH"></h2><div id="stand"></div>
<div class="foot">RAINMAN · {label} · schedules, records and lines from ESPN's public scoreboard (pulled {pulled}). <a href="index.html">← all sports</a></div>
</div>
<script>const J={json.dumps(J, separators=(',', ':'))};</script>
<script>{brand.THEME_JS}</script><script>{SJS}</script></body></html>"""

def main():
    games, pulled = load_slate()
    os.makedirs('dashboard', exist_ok=True)
    open('dashboard/index.html', 'w', encoding='utf-8').write(page(games, pulled))
    n = {}
    for k, l, g, p, s, i in LEAGUES:
        if s != 'shell': continue
        gs = [x for x in games if x['sport'] == k]
        open('dashboard/' + p, 'w', encoding='utf-8').write(shell(k, l, gs, pulled, i)); n[p] = len(gs)
    print(f"dashboard/index.html: {len(games)} games across {len(set(g['lg'] for g in games))} leagues (pulled {pulled}) · shells {n}")

if __name__ == '__main__':
    main()
