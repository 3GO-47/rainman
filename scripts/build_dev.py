"""The dev dashboard — dashboard/dev.html: what the machinery did, not what the model thinks.
Panels: Odds API spend (notes/odds_usage.log) and the three-pull policy board (notes/odds_state.json + the slate + the DraftKings
sensors), schedule health (every Task Scheduler slot of the last 8 days: ran / pushed / died / missed), loop runs with step timing
(notes/local_runs.log), the error trail, the planted close sleeper, data freshness and row counts, deploy state (git), build
inventory, and site traffic (a privacy-light hit counter the pages call client-side; dashboard/traffic.json still fills the tile
when a server-side count exists). Self-contained, black. Python 3.10-safe."""
import os, re, csv, glob, json, html, datetime, subprocess, sys
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, 'scripts')
NOW = datetime.datetime.now()
UTC = datetime.timezone.utc
NOWU = datetime.datetime.now(UTC)
def esc(s): return html.escape(str(s if s is not None else ''))
GREY = '#8b98a5'
RC = dict(open='#00c853', probe='#8fa3b8', move='#e8b339', close='#61dcff', lines='#c39bff', force='#ff9f43', free='#55606a', legacy='#55606a')
# the Task Scheduler slots on Josh's PC (local time): the daily pass and the markets pass
SCHED = [('06:50', 'daily'), ('00:20', 'markets'), ('06:20', 'markets'), ('12:20', 'markets'), ('18:20', 'markets')]
TASK_LIMIT_MIN = 30
HIT_NS = 'rainman-3go47'

# ------------------------------------------------------------------ sources
def api():
    log = []
    if os.path.exists('notes/odds_usage.log'):
        for line in open('notes/odds_usage.log', encoding='utf-8'):
            p = line.rstrip('\n').split('\t')
            if len(p) < 5: continue
            kv = {x.split('=', 1)[0]: x.split('=', 1)[1] for x in p[2:] if '=' in x}
            try: cost = int(kv.get('cost', '0') or 0)
            except ValueError: cost = 0
            reason = kv.get('reason') or ('free' if 'events' in p[1] else 'lines' if p[1].endswith('lines') else 'legacy')
            rk = reason.split()[0].rstrip(':').split('#')[0]
            log.append(dict(ts=p[0], what=p[1], cost=cost, used=kv.get('used', ''), left=kv.get('left', ''), reason=reason, rk=rk))
    return log

def loop_runs():
    runs = []; cur = None
    if not os.path.exists('notes/local_runs.log'): return runs
    for line in open('notes/local_runs.log', encoding='utf-8', errors='replace'):
        m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)', line.rstrip('\n'))
        if not m: continue
        ts, msg = m.groups()
        if msg.startswith('=== local loop') or msg.startswith('sleeper: waiting'):
            cur = dict(start=ts, kind='markets' if 'markets' in msg or 'sleeper' in msg else 'daily', sleeper=msg.startswith('sleeper'), steps=0, fails=[], pushed=False, end='', done='', slow=[], killed='', last=ts)
            runs.append(cur)
        if cur is None: continue
        cur['last'] = ts
        if msg.startswith('run: ') or msg.startswith('  ') and ':' in msg: cur['steps'] += 1
        if msg.startswith('!! run interrupted'): cur['killed'] = msg[3:160]
        elif msg.startswith('!!') or 'failed' in msg.lower() or 'Traceback' in msg: cur['fails'].append(msg.lstrip('! ')[:140])
        if re.search(r'took \d+(\.\d+)? min', msg): cur['slow'].append(msg.strip()[:120])
        if msg.startswith('pushed'): cur['pushed'] = True
        if msg.startswith('=== done') or msg.startswith('=== markets run done'):
            cur['end'] = ts; cur['done'] = msg.split(':', 1)[1].strip() if ':' in msg else ''
            if 'markets' in msg: cur['kind'] = 'markets'
    for r in runs:
        t0 = datetime.datetime.strptime(r['start'], '%Y-%m-%d %H:%M:%S')
        if not r['end'] and not r['sleeper']: r['kind'] = 'markets' if t0.hour % 6 == 0 and 15 <= t0.minute <= 45 else 'daily'
        tl = datetime.datetime.strptime(r['last'], '%Y-%m-%d %H:%M:%S')
        r['mins'] = (datetime.datetime.strptime(r['end'], '%Y-%m-%d %H:%M:%S') - t0).total_seconds() / 60 if r['end'] else (tl - t0).total_seconds() / 60
        r['state'] = 'done' if r['end'] else 'killed' if r['killed'] else 'running' if (NOW - tl).total_seconds() < 40 * 60 and r is runs[-1] else 'died'
    return runs

def errors():
    out = []
    for f in ('notes/local_runs.log', 'notes/local_loop.out'):
        if not os.path.exists(f): continue
        for line in open(f, encoding='utf-8', errors='replace'):
            s = line.rstrip('\n')
            if re.search(r'!!|failed|Traceback|Error|error:|\^C|interrupted|skipped \(', s) and not s.startswith('  nflverse injuries skipped'):
                m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ?(.*)', s)
                out.append(dict(ts=m.group(1) if m else '', msg=(m.group(2) if m else s).strip()[:200], src=os.path.basename(f)))
    seen = set(); uniq = []
    for e in reversed(out):
        k = (e['ts'], e['msg'][:60])
        if k in seen: continue
        seen.add(k); uniq.append(e)
    return uniq[:60]

def schedule_health(R):
    """Every scheduler slot of the last 8 days against the runs that actually started (within 25 min of the slot)."""
    days = [(NOW.date() - datetime.timedelta(days=i)) for i in range(7, -1, -1)]
    first = {}
    for r in R:
        if not r['sleeper']: first.setdefault(r['kind'], r['start'])
    grid = []
    for d in days:
        row = []
        for hm, kind in SCHED:
            t = datetime.datetime.combine(d, datetime.time(int(hm[:2]), int(hm[3:])))
            if t > NOW: row.append(dict(slot=hm, kind=kind, state='future', run=None)); continue
            if kind not in first or t < datetime.datetime.strptime(first[kind], '%Y-%m-%d %H:%M:%S') - datetime.timedelta(minutes=30): row.append(dict(slot=hm, kind=kind, state='before', run=None)); continue
            best = None; late = False
            lo, hi = (-25 * 60, 25 * 60) if kind == 'markets' else (-25 * 60, 4 * 3600)     # the daily task catches up after the PC wakes
            for r in R:
                if r['sleeper'] or r.get('_used'): continue
                t0 = datetime.datetime.strptime(r['start'], '%Y-%m-%d %H:%M:%S'); dt = (t0 - t).total_seconds()
                if lo <= dt <= hi and (kind == 'markets' or r['kind'] != 'markets') and (best is None or abs(dt) < abs((datetime.datetime.strptime(best['start'], '%Y-%m-%d %H:%M:%S') - t).total_seconds())): best = r
            if best is not None:
                best['_used'] = True; late = (datetime.datetime.strptime(best['start'], '%Y-%m-%d %H:%M:%S') - t).total_seconds() > 30 * 60
            if best is None: state = 'missed' if (NOW - t).total_seconds() > (40 * 60 if kind == 'markets' else 4.2 * 3600) else 'due'
            elif best['state'] == 'done': state = 'pushed' if best['pushed'] else 'done'
            elif best['state'] == 'running': state = 'running'
            else: state = 'died'
            if late and state in ('pushed', 'done'): state = 'late'
            row.append(dict(slot=hm, kind=kind, state=state, run=best))
        grid.append((d, row))
    return grid

def freshness():
    def newest(pat):
        f = sorted(glob.glob(pat)); return (f[-1], datetime.datetime.fromtimestamp(os.path.getmtime(f[-1]))) if f else ('', None)
    items = [('slate (ESPN)', 'data/raw/slate_all_*.txt'), ('depth chart', 'data/processed/depth_charts_*.csv'), ('injuries (ESPN)', 'data/raw/espn_injuries_*.txt'), ('injuries_current', 'data/processed/injuries_current.csv'),
             ('DraftKings lines (ESPN)', 'data/raw/markets/draftkings_*.txt'), ('Kalshi', 'data/raw/markets/kalshi_*.txt'), ('Polymarket', 'data/raw/markets/polymarket_2*.txt'),
             ('Polymarket anytime TD', 'data/raw/markets/polymarket_td_*.txt'), ('Odds API lines', 'data/raw/markets/oddsapi_current.csv'), ('Odds API props', 'data/raw/odds_api/props_current.csv'),
             ('nflverse injuries', 'data/raw/nflverse/injuries_2026.parquet'), ('game logs 2026', 'data/game_logs/*2026*.csv'), ('dvp_season', 'data/processed/dvp_season.csv'), ('bet_td', 'data/processed/bet_td.csv'), ('picks_all', 'data/processed/picks_all.csv'), ('bets', 'data/processed/bets*.csv')]
    out = []
    for name, pat in items:
        f, t = newest(pat); age = (NOW - t).total_seconds() / 3600 if t else None
        rows = ''
        if f and f.endswith('.csv'):
            try: rows = sum(1 for _ in open(f, encoding='utf-8', errors='replace')) - 1
            except Exception: rows = ''
        elif f and f.endswith('.txt'):
            try: rows = sum(1 for l in open(f, encoding='utf-8', errors='replace') if l[:1] not in '#\n')
            except Exception: rows = ''
        out.append(dict(name=name, file=os.path.basename(f) if f else '—', when=t.strftime('%Y-%m-%d %H:%M') if t else '—', age=age, size=os.path.getsize(f) if f else 0, rows=rows))
    return out

def gamelog_counts():
    out = []
    for f in sorted(glob.glob('data/game_logs/*.csv')):
        try:
            n = sum(1 for _ in open(f, encoding='utf-8', errors='replace')) - 1
            wk = set(); pl = set()
            for r in csv.DictReader(open(f, encoding='utf-8', errors='replace')):
                wk.add(r.get('week', '')); pl.add(r.get('player', ''))
            out.append(dict(file=os.path.basename(f), rows=n, weeks=len(wk), players=len(pl), when=datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M')))
        except Exception: pass
    return out

def builds():
    out = []
    for f in sorted(glob.glob('dashboard/*.html')):
        t = datetime.datetime.fromtimestamp(os.path.getmtime(f))
        out.append(dict(page=os.path.basename(f), kb=round(os.path.getsize(f) / 1024), when=t.strftime('%Y-%m-%d %H:%M'), age=(NOW - t).total_seconds() / 3600, big=os.path.getsize(f) > 10 * 1024 * 1024))
    return out

def git_state():
    def g(*a):
        try: return subprocess.run(['git'] + list(a), capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception: return ''
    head = g('log', '-1', '--format=%h|%ci|%s')
    ahead = g('rev-list', '--count', 'origin/main..HEAD'); behind = g('rev-list', '--count', 'HEAD..origin/main')
    dirty = g('status', '--porcelain'); origin = g('log', '-1', '--format=%h %ci', 'origin/main')
    st = {}
    try: st = json.load(open('notes/local_state.json'))
    except Exception: pass
    pushed = [d for d, v in st.items() if isinstance(v, dict) and v.get('pushed')]
    recent = g('log', '-12', '--format=%h|%ci|%s')
    return dict(head=head.split('|') if head else [], ahead=ahead, behind=behind, dirty=len(dirty.splitlines()), origin=origin, last_push_day=max(pushed) if pushed else '—', recent=[r.split('|', 2) for r in recent.splitlines() if r])

def policy_board():
    """Where every game stands under the three-pull policy: window, probes, open, moves, close — and what is due next."""
    try:
        import fetch_odds_api as F
    except Exception as e:
        return dict(err=str(e), rows=[], sleeper=None)
    try: names, games = F.slate()
    except Exception as e: return dict(err=str(e), rows=[], sleeper=None)
    st = F.load_state() if hasattr(F, 'load_state') else {}
    try: SENS = F.sensors()
    except Exception: SENS = {}
    P = F.POLICY; cmin, cmax = P['CLOSE_MIN']
    rows = []
    for g in games:
        if g['lg'] not in F.PLAN: continue
        try: ko = F.parse_ts(g['date'])
        except Exception: continue
        hrs = (ko - NOWU).total_seconds() / 3600
        if hrs < -4 or hrs > P['OPEN_FROM_H'][g['lg']] + 48: continue
        k = f"{g['lg']}|{g['away']}@{g['home']}|{g['date'][:10]}"
        S = st.get('props', {}).get(k) or {}
        LG = (st.get('lines_games', {}).get(g['lg']) or {}).get(k) or {}
        mk = S.get('mkts') or (S.get('n') and 'legacy') or 0
        probes = S.get('probes', []); moves = S.get('moves', [])
        opened = isinstance(mk, int) and mk >= P['OPEN_MIN_MKTS'] or mk == 'legacy'
        if hrs < -0.1: stage = 'kicked off'
        elif S.get('closed'): stage = 'closed'
        elif hrs > P['OPEN_FROM_H'][g['lg']]: stage = 'outside window'
        elif opened: stage = 'open'
        elif probes: stage = 'probing (not posted)'
        else: stage = 'in window · not probed'
        nxt = ''
        if stage in ('in window · not probed',): nxt = 'probe on the next pass (free if nothing posted)'
        elif stage == 'probing (not posted)':
            t = F.parse_ts(S['at']) + datetime.timedelta(hours=P['PROBE_GAP_H']) if S.get('at') else NOWU
            nxt = 'probe again ' + ('now' if t <= NOWU else t.astimezone().strftime('%a %H:%M'))
        elif stage == 'open':
            cw = ko - datetime.timedelta(minutes=cmax); nxt = 'close pull ' + cw.astimezone().strftime('%a %H:%M') + '–' + (ko - datetime.timedelta(minutes=cmin)).astimezone().strftime('%H:%M')
            if len(moves) < P['MOVE_MAX']: nxt += f' · move pull if spread ≥{P["MOVE"]["spread"]} / total ≥{P["MOVE"]["total"]} / ml ≥{int(P["MOVE"]["ml"]*100)}% off our last ({P["MOVE_MAX"]-len(moves)} left)'
        elif stage == 'outside window': nxt = 'window opens ' + (ko - datetime.timedelta(hours=P['OPEN_FROM_H'][g['lg']])).astimezone().strftime('%a %H:%M')
        sens = SENS.get(g['id']) or {}
        rows.append(dict(lg=g['lg'], game=f"{g['away']} @ {g['home']}", ko=ko.astimezone().strftime('%a %m/%d %H:%M'), hrs=hrs, stage=stage, mkts=mk if mk != 'legacy' else S.get('n', ''), probes=len(probes), moves=len(moves),
                         last=(S.get('at') or LG.get('at') or '')[:16].replace('T', ' '), lines_at=(LG.get('at') or '')[:16].replace('T', ' '), lines_closed=bool(LG.get('closed')), sens=sens, nxt=nxt))
    rows.sort(key=lambda r: r['hrs'])
    sl = None
    try: sl = json.load(open('notes/close_sleeper.json'))
    except Exception: pass
    return dict(err='', rows=rows, sleeper=sl, policy=P, reserve=getattr(F, 'RESERVE', ''))

def section_ids():
    try:
        s = open('scripts/dashboard_template.html', encoding='utf-8').read()
        i = s.index('const SECTIONS='); j = s.index('];', i)
        return re.findall(r"\bid:'([a-z0-9]+)'", s[i:j])
    except Exception: return []

def traffic():
    try: return json.load(open('dashboard/traffic.json'))
    except Exception: return None

# ------------------------------------------------------------------ render helpers
def kpi(k, v, s, cls=''): return f'<div class="kpi {cls}"><span class="k">{k}</span><span class="v">{v}</span><span class="s">{s}</span></div>'
def tag(txt, color): return f'<span class="tag" style="color:{color};border-color:{color}66">{esc(txt)}</span>'
agefmt = lambda h: '—' if h is None else (f'{h:.0f} h' if h < 72 else f'{h/24:.1f} d')
age_cls = lambda h: 'g' if h is not None and h < 26 else 'a' if h is not None and h < 80 else 'r'
STATE_C = dict(pushed='#00c853', late='#9ccc65', done='#e8b339', running='#61dcff', died='#ff5252', killed='#ff5252', missed='#ff5252', due='#8b98a5', future='#2a2e35', before='#2a2e35')
STAGE_C = {'closed': '#61dcff', 'open': '#00c853', 'probing (not posted)': '#8fa3b8', 'in window · not probed': '#e8b339', 'outside window': '#55606a', 'kicked off': '#55606a'}

def main():
    L = api(); R = loop_runs(); E = errors(); F = freshness(); GL = gamelog_counts(); B = builds(); G = git_state(); PB = policy_board(); T = traffic(); SH = schedule_health(R); IDS = section_ids()
    today = NOW.strftime('%Y-%m-%d'); mo = today[:7]
    by_day = {}
    for r in L:
        d = by_day.setdefault(r['ts'][:10], {'cost': 0, 'calls': 0, 'by': {}}); d['cost'] += r['cost']; d['calls'] += 1; d['by'][r['rk']] = d['by'].get(r['rk'], 0) + r['cost']
    days = sorted(by_day)[-30:]; mx = max([by_day[d]['cost'] for d in days] + [1])
    last = L[-1] if L else {}
    mo_cost = sum(by_day[d]['cost'] for d in by_day if d.startswith(mo)); dom = int(today[8:10])
    dim = (datetime.date(NOW.year + (NOW.month == 12), NOW.month % 12 + 1, 1) - datetime.timedelta(days=1)).day
    pace = mo_cost / max(1, dom) * dim
    by_reason = {}
    for r in L: by_reason.setdefault(r['rk'], [0, 0]); by_reason[r['rk']][0] += 1; by_reason[r['rk']][1] += r['cost']
    runs7 = [r for r in R if r['start'][:10] >= (NOW - datetime.timedelta(days=7)).strftime('%Y-%m-%d')]
    fails7 = sum(len(r['fails']) for r in runs7); dead7 = sum(1 for r in runs7 if r['state'] in ('died', 'killed'))
    slots = [c for d, row in SH for c in row if c['state'] not in ('future', 'due', 'before')]
    missed = sum(1 for c in slots if c['state'] == 'missed'); okslots = sum(1 for c in slots if c['state'] in ('pushed', 'done', 'late'))
    left = int(last['left']) if last and str(last.get('left', '')).isdigit() else None
    plan = 100000 if (left is not None and left > 600) or (last and str(last.get('used', '')).isdigit() and int(last['used']) > 600) else '?'
    key_note = 'new 100k key confirmed by the last header' if plan == 100000 else 'last header still shows the old 500-credit key — the new key has not answered a call yet' if last else 'no call logged yet'

    # ---- KPIs
    K = ''.join([
        kpi('Odds API · plan', '100,000', 'credits a month'),
        kpi('used · plan period', esc(last.get('used', '—')), f"{esc(last.get('left','—'))} left · {esc(last.get('ts','—'))}", 'r' if left is not None and left < 5000 else 'g' if left is not None and left > 50000 else ''),
        kpi('logged this month', f'{mo_cost:,}', f'pace {int(pace):,} / month', 'r' if pace > 100000 else 'a' if pace > 50000 else 'g'),
        kpi('scheduler · 8 days', f'{okslots}/{len(slots)}', f'{missed} missed · {sum(1 for c in slots if c["state"]=="died")} died', 'g' if missed == 0 and okslots == len(slots) else 'a' if okslots >= len(slots) * .7 else 'r'),
        kpi('loop runs · 7 days', str(len(runs7)), f"{sum(1 for r in runs7 if r['kind']=='daily')} daily · {sum(1 for r in runs7 if r['kind']=='markets')} markets · {sum(1 for r in runs7 if r['pushed'])} pushed"),
        kpi('step failures · 7 days', str(fails7), f'{dead7} runs died', 'r' if fails7 or dead7 else 'g'),
        kpi('deploy', f"+{esc(G['ahead'] or '0')}", f"commits not on origin · last push {esc(G['last_push_day'])}", 'g' if (G['ahead'] or '0') == '0' else 'a' if int(G['ahead'] or 0) < 10 else 'r'),
        kpi('site traffic · 7 days', '<span id="tr7">…</span>', '<span id="trs">views · counter</span>'),
    ])
    # ---- schedule grid
    SHT = '<table class="sched"><thead><tr><th>day</th>' + ''.join(f'<th>{hm}<br><span class="dim">{k}</span></th>' for hm, k in SCHED) + '</tr></thead><tbody>'
    for d, row in SH:
        SHT += f'<tr><td>{d.strftime("%a %m/%d")}</td>'
        for c in row:
            r = c['run']; t = ''
            if r: t = f"{r['start'][11:16]} → {r['end'][11:16] if r['end'] else '…'} · {r['mins']:.0f} min · {r['steps']} steps" + (' · ' + r['killed'] if r['killed'] else '') + (' · ' + r['fails'][0] if r['fails'] else '')
            lbl = dict(pushed='✓ pushed', late='✓ late', done='✓ no push', running='running', died='✗ died', missed='missed', due='due', future='', before='·')[c['state']]
            SHT += f'<td class="sc" style="color:{STATE_C[c["state"]]}" title="{esc(t)}"><span class="dot" style="background:{STATE_C[c["state"]]}"></span>{lbl}</td>'
        SHT += '</tr>'
    SHT += '</tbody></table>'
    # ---- policy board
    PBT = ''
    if PB.get('err'): PBT = f'<p class="r">policy board unavailable: {esc(PB["err"])}</p>'
    else:
        PBT = '<table><thead><tr><th>lg</th><th>game</th><th>kickoff</th><th class="n">in</th><th>stage</th><th class="n">mkts</th><th class="n">probes</th><th class="n">moves</th><th>last props pull</th><th>lines pull</th><th>sensor (DK)</th><th>next</th></tr></thead><tbody>'
        for r in PB['rows']:
            s = r['sens'] or {}
            fm = lambda v, pct=False: '—' if v is None else (f'{100*v:.0f}%' if pct else f'{v:+.1f}')
            sens = f"{fm(s.get('spread'))} / {s.get('total') if s.get('total') is not None else '—'} / {fm(s.get('ml'), True)}" if s else '—'
            hrs = f"{r['hrs']:.0f} h" if abs(r['hrs']) < 72 else f"{r['hrs']/24:.1f} d"
            PBT += f'<tr><td class="dim">{esc(r["lg"].upper())}</td><td>{esc(r["game"])}</td><td>{esc(r["ko"])}</td><td class="n {"a" if 0<=r["hrs"]<=3 else ""}">{hrs}</td><td>{tag(r["stage"], STAGE_C.get(r["stage"], GREY))}</td><td class="n">{esc(r["mkts"] or "—")}</td><td class="n {"dim" if not r["probes"] else ""}">{r["probes"]}</td><td class="n {"dim" if not r["moves"] else "a"}">{r["moves"]}</td><td class="dim">{esc(r["last"] or "—")}</td><td class="dim">{esc(r["lines_at"] or "—")}{" ✓closed" if r["lines_closed"] else ""}</td><td class="dim">{esc(sens)}</td><td class="dim" style="white-space:normal;min-width:220px">{esc(r["nxt"])}</td></tr>'
        PBT += '</tbody></table>'
        if not PB['rows']: PBT = '<p class="dim">no games inside the policy window on the slate</p>'
    sl = PB.get('sleeper'); SLP = ''
    if sl: SLP = f'<p class="mini">close sleeper: planted {esc(str(sl.get("planted","?"))[:16])} · waits until <b class="g">{esc(str(sl.get("until","?"))[:16])}</b> · pid {esc(sl.get("pid","?"))} — a detached loop.py --markets that wakes for the close window and dies with the lock</p>'
    else: SLP = '<p class="mini dim">no close sleeper planted right now — the markets pass plants one when a kickoff enters the next 6.5 h</p>'
    pol = PB.get('policy') or {}
    POL = f'<p class="mini dim">policy: props probed from {pol.get("OPEN_FROM_H",{}).get("nfl","?")} h (NFL) / {pol.get("OPEN_FROM_H",{}).get("cfb","?")} h (CFB) before kickoff, empty answers free · partial (&lt;{pol.get("OPEN_MIN_MKTS","?")} markets) re-probed every {pol.get("PROBE_GAP_H","?")} h · a move pull when the DraftKings sensor moves spread ≥{pol.get("MOVE",{}).get("spread","?")} / total ≥{pol.get("MOVE",{}).get("total","?")} / ML ≥{int(pol.get("MOVE",{}).get("ml",0)*100)}% off our last pull, max {pol.get("MOVE_MAX","?")} per game {pol.get("MOVE_GAP_H","?")} h apart · the close pull {pol.get("CLOSE_MIN",("?","?"))[0]}–{pol.get("CLOSE_MIN",("?","?"))[1]} min before kickoff · reserve {PB.get("reserve","?")} credits</p>' if pol else ''
    # ---- runs
    RT = ''.join(f'<tr><td>{esc(r["start"])}</td><td>{esc(r["kind"])}{" <span class=dim>(sleeper)</span>" if r["sleeper"] else ""}</td><td style="color:{STATE_C.get("pushed" if r["state"]=="done" and r["pushed"] else "done" if r["state"]=="done" else r["state"], GREY)}">{esc(r["state"])}</td><td class="n {"a" if r["mins"]>20 else ""}">{r["mins"]:.0f}</td><td class="n">{r["steps"]}</td><td class="{"r" if r["fails"] or r["killed"] else "dim"}" style="white-space:normal;max-width:360px">{esc(r["killed"] or "; ".join(r["fails"])[:160]) if r["fails"] or r["killed"] else "—"}{("<br><span class=a>" + esc("; ".join(r["slow"])[:160]) + "</span>") if r["slow"] else ""}</td><td class="{"g" if r["pushed"] else "dim"}">{"pushed" if r["pushed"] else "—"}</td><td class="dim">{esc(r["done"][:60])}</td></tr>' for r in reversed(R[-80:])) or '<tr><td colspan="8" class="dim">no runs logged</td></tr>'
    ET = ''.join(f'<tr><td class="dim">{esc(e["ts"])}</td><td class="dim">{esc(e["src"])}</td><td class="{"r" if "!!" in e["msg"] or "Traceback" in e["msg"] or "^C" in e["msg"] else "a"}" style="white-space:normal">{esc(e["msg"])}</td></tr>' for e in E) or '<tr><td colspan="3" class="g">clean — nothing failed in the logs</td></tr>'
    # ---- freshness, game logs, builds, git
    FT = ''.join(f'<tr><td>{esc(f["name"])}</td><td class="dim">{esc(f["file"])}</td><td>{esc(f["when"])}</td><td class="n {age_cls(f["age"])}">{agefmt(f["age"])}</td><td class="n dim">{(str(f["rows"])+" rows") if f["rows"]!="" else "—"}</td><td class="n dim">{f["size"]//1024 if f["size"] else "—"} KB</td></tr>' for f in F)
    GLT = ''.join(f'<tr><td>{esc(g["file"])}</td><td class="n">{g["rows"]:,}</td><td class="n">{g["weeks"]}</td><td class="n">{g["players"]:,}</td><td class="dim">{esc(g["when"])}</td></tr>' for g in GL) or '<tr><td colspan="5" class="dim">no game logs</td></tr>'
    BT = ''.join(f'<tr><td><a href="{esc(b["page"])}">{esc(b["page"])}</a></td><td class="n {"r" if b["big"] else ""}">{b["kb"]:,} KB{" ⚠ over the 10 MB web-upload limit" if b["big"] else ""}</td><td>{esc(b["when"])}</td><td class="n {age_cls(b["age"])}">{agefmt(b["age"])}</td><td class="n dim" id="pv-{esc(b["page"].replace(".html",""))}">…</td></tr>' for b in B)
    GT = ''.join(f'<tr><td class="dim">{esc(c[0])}</td><td class="dim">{esc(c[1][:16])}</td><td style="white-space:normal">{esc(c[2])}</td></tr>' for c in G['recent'])
    head = G['head'] or ['—', '', '']
    GK = f'HEAD <b>{esc(head[0])}</b> · {esc(head[1][:16])} · {esc(head[2][:80])}<br>origin/main {esc(G["origin"][:24] or "—")} · <span class="{"g" if (G["ahead"] or "0")=="0" else "a"}">{esc(G["ahead"] or "0")} ahead</span> · {esc(G["behind"] or "0")} behind · <span class="{"a" if G["dirty"] else "g"}">{G["dirty"]} files changed in the tree</span> · last loop push day {esc(G["last_push_day"])}'
    # ---- api
    def bar_day(d):
        parts = sorted(by_day[d]['by'].items(), key=lambda kv: -kv[1])
        segs = ''.join('<i style="height:%dpx;background:%s"></i>' % (max(1, round(100 * v / mx)), RC.get(k, GREY)) for k, v in parts if v)
        title = '%s: %d credits · %d calls · %s' % (d, by_day[d]['cost'], by_day[d]['calls'], ', '.join(k + ' ' + str(v) for k, v in parts if v))
        return '<div class="b" title="%s"><div class="bar">%s</div><b>%s</b><span>%s</span></div>' % (esc(title), segs, by_day[d]['cost'] or '', d[5:])
    BARS = ''.join(bar_day(d) for d in days) or '<span class="dim">no calls logged</span>'
    LEG = ' '.join(tag(k.upper(), c) for k, c in RC.items()) + ' · by reason: ' + ' · '.join(f'{k} {v[1]:,} credits / {v[0]} calls' for k, v in sorted(by_reason.items(), key=lambda kv: -kv[1][1]))
    PLT = ''.join(f'<tr><td class="dim">{esc(r["ts"])}</td><td>{esc(r["what"])}</td><td>{tag(r["reason"].upper(), RC.get(r["rk"], GREY))}</td><td class="n {"" if r["cost"] else "dim"}">{r["cost"]}</td><td class="n dim">{esc(r["used"])}</td><td class="n dim">{esc(r["left"])}</td></tr>' for r in reversed(L[-300:])) or '<tr><td colspan="6" class="dim">nothing yet</td></tr>'
    TJ = ('<pre class="dim">' + esc(json.dumps(T, indent=1)[:2000]) + '</pre>') if T else ''
    pages = [b['page'].replace('.html', '') for b in B]
    ids_js = json.dumps(IDS); pages_js = json.dumps(pages)
    traffic_js = """
(async()=>{const ns='%s',base='https://abacus.jasoncameron.dev/get/'+ns+'/';const get=async k=>{try{const r=await fetch(base+k);if(!r.ok)return 0;const j=await r.json();return +j.value||0}catch(e){return 0}};
const days=[];for(let i=13;i>=0;i--){const d=new Date(Date.now()-i*864e5).toISOString().slice(0,10);days.push(d)}
const daily=await Promise.all(days.map(d=>get('all.'+d)));const t7=daily.slice(-7).reduce((a,b)=>a+b,0),t14=daily.reduce((a,b)=>a+b,0);
document.getElementById('tr7').textContent=t7.toLocaleString();document.getElementById('trs').textContent=t14.toLocaleString()+' in 14 days · today '+daily[daily.length-1];
const mx=Math.max(1,...daily);document.getElementById('trBars').innerHTML=days.map((d,i)=>`<div class="b" title="${d}: ${daily[i]} views"><div class="bar"><i style="height:${daily[i]?Math.max(1,Math.round(100*daily[i]/mx)):0}px;background:#61dcff"></i></div><b>${daily[i]||''}</b><span>${d.slice(5)}</span></div>`).join('');
const pages=%s;const pv=await Promise.all(pages.map(p=>get('page.'+p)));pages.forEach((p,i)=>{const e=document.getElementById('pv-'+p);if(e)e.textContent=pv[i]?pv[i].toLocaleString()+' views':'—'});
const ids=%s;const tv=await Promise.all(ids.map(t=>get('tab.rainman.'+t)));const rows=ids.map((t,i)=>[t,tv[i]]).filter(x=>x[1]).sort((a,b)=>b[1]-a[1]);const tm=Math.max(1,...rows.map(x=>x[1]));
document.getElementById('tabViews').innerHTML=rows.length?rows.map(([t,n])=>`<tr><td>${t}</td><td class="n">${n.toLocaleString()}</td><td style="width:40%%"><i class="hb" style="width:${100*n/tm}%%"></i></td></tr>`).join(''):'<tr><td colspan="3" class="dim">no tab views counted yet</td></tr>';
})();""" % (HIT_NS, pages_js, ids_js)
    sort_js = r'''(function(){function val(td){var t=td.textContent.trim().replace(/[,%$u+]/g,'');var n=parseFloat(t);return isNaN(n)||!/^[-+]?[\d.]/.test(t)?t.toLowerCase():n}
document.addEventListener('click',function(e){var th=e.target.closest('table th');if(!th)return;var tb=th.closest('table'),body=tb.tBodies[0];if(!body)return;var i=[...th.parentNode.children].indexOf(th),asc=th.classList.contains('sa');
tb.querySelectorAll('th').forEach(function(h){h.classList.remove('sa','sd')});th.classList.add(asc?'sd':'sa');var rows=[...body.rows];rows.sort(function(a,b){var x=val(a.cells[i]||{textContent:''}),y=val(b.cells[i]||{textContent:''});if(typeof x==='number'&&typeof y==='number')return asc?y-x:x-y;if(typeof x==='number')return -1;if(typeof y==='number')return 1;return asc?(y>x?1:-1):(x>y?1:-1)});rows.forEach(function(r){body.appendChild(r)})})})();'''
    hit_js = "(function(){try{if(location.protocol==='file:'||window.top!==window||localStorage.getItem('rm-nocount'))return;var ns='%s',d=new Date().toISOString().slice(0,10),h=function(k){fetch('https://abacus.jasoncameron.dev/hit/'+ns+'/'+k,{keepalive:true}).catch(function(){})};h('page.dev');h('all.'+d)}catch(e){}})();" % HIT_NS

    H = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · dev</title>
<style>
:root{{--bg:#000;--panel:#0a0b0d;--edge:#1c1f24;--edge2:#2a2e35;--txt:#e6e8ec;--dim:#8b98a5;--dim2:#55606a;--green:#00c853;--red:#ff5252;--amber:#e8b339;--cyan:#61dcff;--mono:ui-monospace,"JetBrains Mono",Menlo,Consolas,monospace;--ui:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:12.5px/1.45 var(--ui)}}a{{color:var(--cyan);text-decoration:none}}
header{{display:flex;align-items:center;gap:14px;padding:10px 18px;border-bottom:1px solid var(--edge);position:sticky;top:0;background:#000;z-index:5}}header b{{font:700 15px var(--mono);letter-spacing:2px}}header .mini{{color:var(--dim)}}header nav{{margin-left:auto}}header nav a{{margin-left:12px;font:600 11px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--dim)}}header nav a:hover{{color:var(--txt)}}
main{{padding:12px 18px;max-width:1560px;margin:0 auto}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-bottom:12px}}.kpi{{background:var(--panel);border:1px solid var(--edge);border-radius:4px;padding:8px 10px}}.kpi .k{{display:block;font:600 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2)}}.kpi .v{{display:block;font:600 16px var(--mono);margin:4px 0 2px}}.kpi .s{{display:block;font:10.5px var(--ui);color:var(--dim)}}.kpi.g .v{{color:var(--green)}}.kpi.r .v{{color:var(--red)}}.kpi.a .v{{color:var(--amber)}}
.panel{{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:10px 12px;margin-bottom:12px}}.panel h3{{margin:0 0 6px;font:600 12px var(--ui);letter-spacing:.06em;text-transform:uppercase}}.panel h3 .f{{font:400 11px var(--ui);text-transform:none;letter-spacing:0;color:var(--dim);margin-left:8px}}.mini{{font-size:11px;color:var(--dim);margin:4px 0}}
table{{width:100%;border-collapse:collapse;font-size:11.5px}}th{{cursor:pointer;user-select:none;text-align:left;font:600 9.5px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--dim2);padding:3px 6px;border-bottom:1px solid var(--edge2);position:sticky;top:0;background:var(--panel)}}td{{padding:3px 6px;border-bottom:1px solid var(--edge);font-family:var(--mono);white-space:nowrap;vertical-align:top}}td.n,th.n{{text-align:right}}.g{{color:var(--green)}}.r{{color:var(--red)}}.a{{color:var(--amber)}}.dim{{color:var(--dim2)}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}@media(max-width:1000px){{.grid2{{grid-template-columns:1fr}}}}
.bars{{display:flex;align-items:flex-end;gap:3px;height:140px;padding:4px 0 18px}}.b{{flex:1 1 0;max-width:34px;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;position:relative}}.bar{{width:100%;height:100px;display:flex;flex-direction:column-reverse;justify-content:flex-start}}.bar i{{display:block;width:100%}}.b b{{font:600 9.5px var(--mono);color:var(--dim);margin-top:2px}}.b span{{position:absolute;bottom:-14px;font:9.5px var(--mono);color:var(--dim2)}}
.tag{{display:inline-block;font:600 9.5px var(--mono);letter-spacing:.5px;padding:0 4px;border:1px solid;border-radius:2px;line-height:14px;white-space:nowrap}}
.scroll{{max-height:46vh;overflow:auto}}
.sched td.sc{{font:600 10.5px var(--mono)}}.dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;vertical-align:middle}}
.hb{{display:block;height:8px;background:var(--cyan);border-radius:2px;opacity:.75}}
th.sa:after{{content:' \\25B4';opacity:.7}}th.sd:after{{content:' \\25BE';opacity:.7}}

@media (max-width:760px){{
 html,body{{overflow-x:hidden;max-width:100vw}}
 body{{font-size:12px}}
 #hdr{{flex-wrap:wrap;height:auto!important;min-height:0;padding:6px 10px!important;gap:6px 10px!important;row-gap:4px}}
 #hdr .brand{{font-size:13px}}#hdr .brand small{{display:none}}
 #hdr .tag,#hdr .mini{{display:none}}
 #hdr .hl,#hdr .tabs,#hdr nav{{flex-wrap:wrap;gap:3px;margin-left:0}}
 #hdr .hl a,#hdr .tabs a,#hdr .tabs button,#hdr nav a{{padding:5px 8px;min-height:30px;display:inline-flex;align-items:center;font-size:11.5px}}
 main{{padding:8px!important}}
 .panel{{padding:8px!important;border-radius:5px}}
 h1{{font-size:15px}}h2{{font-size:13px}}h3{{font-size:12px}}
 .mscroll{{overflow-x:auto;width:0;min-width:100%;max-width:100%;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain;position:relative}}
 .mgrid1>*,.panel,main>*{{min-width:0}}
 header{{flex-wrap:wrap;height:auto;padding:6px 10px;gap:6px 10px}}header nav{{flex-wrap:wrap}}
 .mscroll>table{{font-size:11px;width:max-content;min-width:100%}}
 .mscroll>table th,.mscroll>table td{{white-space:nowrap;max-width:220px;overflow:hidden;text-overflow:ellipsis}}
 .mscroll>table th:first-child,.mscroll>table td:first-child{{position:sticky;left:0;z-index:2;background:#000;box-shadow:1px 0 0 var(--edge2,#222)}}
 .mscroll>table thead th{{position:sticky;top:0;z-index:3}}
 .mscroll>table thead th:first-child{{z-index:4}}
 .mscroll.one>table th:first-child,.mscroll.one>table td:first-child{{position:static;box-shadow:none}}
 .mgrid1{{grid-template-columns:1fr!important}}
 select,input[type=text],input[type=search],input[type=number]{{min-height:32px;font-size:13px}}
 .chips button,button.sw,.chip{{min-height:30px;padding:5px 9px}}
 .modal{{padding:0!important;align-items:stretch!important}}
 .modal .modalbox,.modal .modalbox.wide,.modalbox{{max-width:100%!important;width:100%;min-height:100%;padding:10px 10px 40px!important;border-left:0;border-right:0}}
 .mclose{{position:sticky!important;top:0;float:right;z-index:5;min-height:32px;padding:4px 12px}}
 .sfoot{{flex-wrap:wrap;gap:8px}}
 .trk{{min-width:26px;line-height:22px}}
}}
</style></head><body>
<header><b>RAINMAN · DEV</b><span class="mini">built {NOW.strftime('%Y-%m-%d %H:%M')} local · the machinery, not the model</span><nav><a href="rainman.html">dashboard</a><a href="ncaa.html">ncaa</a><a href="arb.html">arb</a><a href="index.html">landing</a><a href="rainman.html#v=api">api tab</a></nav></header><main>
<div class="kpis">{K}</div>
<div class="grid2">
<div class="panel"><h3>scheduler health <span class="f">every Task Scheduler slot, last 8 days · local time · hover a cell for the run</span></h3>{SHT}
<p class="mini dim">daily 06:50 = game logs, depth charts, injuries, DvP, model, every page · markets :20 every 6 h = slate, odds policy, exchanges, arb, bets, dashboard, dev, push · the task has a {TASK_LIMIT_MIN}-min limit, so a run that never logs an end line was killed by it</p></div>
<div class="panel"><h3>deploy <span class="f">git on the PC vs origin/main (GitHub Pages serves origin/main/dashboard)</span></h3><p class="mini">{GK}</p><div class="scroll" style="max-height:190px"><table><thead><tr><th>commit</th><th>when</th><th>subject</th></tr></thead><tbody>{GT}</tbody></table></div></div>
</div>
<div class="panel"><h3>Odds API · three-pull policy board <span class="f">where every game inside the window stands · sensor = DraftKings spread / total / home ML from the free ESPN feed · {esc(key_note)}</span></h3>{SLP}<div class="scroll">{PBT}</div>{POL}</div>
<div class="panel"><h3>Odds API · credits per day <span class="f">last {len(days)} days with calls · split by reason · hover for the calls</span></h3>
<div class="bars">{BARS}</div><p class="dim" style="margin:4px 0 0">{LEG}</p></div>
<div class="grid2">
<div class="panel"><h3>loop runs <span class="f">newest first · a run = one Task Scheduler pass or one planted sleeper · amber = over 20 min</span></h3><div class="scroll"><table><thead><tr><th>start</th><th>kind</th><th>state</th><th class="n">min</th><th class="n">steps</th><th>failures / slow steps</th><th>push</th><th>did</th></tr></thead><tbody>{RT}</tbody></table></div></div>
<div class="panel"><h3>error trail <span class="f">every failure, traceback, kill and skip in the logs · newest first</span></h3><div class="scroll"><table><thead><tr><th>when</th><th>log</th><th>line</th></tr></thead><tbody>{ET}</tbody></table></div></div>
</div>
<div class="grid2">
<div class="panel"><h3>data freshness <span class="f">newest file per source · green under 26 h, amber under 80 h</span></h3><table><thead><tr><th>source</th><th>file</th><th>updated</th><th class="n">age</th><th class="n">rows</th><th class="n">size</th></tr></thead><tbody>{FT}</tbody></table>
<h3 style="margin-top:10px">game logs <span class="f">the source of truth — every derived table is rebuilt from these</span></h3><table><thead><tr><th>file</th><th class="n">rows</th><th class="n">weeks</th><th class="n">players</th><th>updated</th></tr></thead><tbody>{GLT}</tbody></table></div>
<div class="panel"><h3>builds <span class="f">every page the loop writes · views from the counter</span></h3><table><thead><tr><th>page</th><th class="n">size</th><th>built</th><th class="n">age</th><th class="n">views</th></tr></thead><tbody>{BT}</tbody></table>
<h3 style="margin-top:10px">Odds API · pull log <span class="f">newest first · cost from the x-requests-last header</span></h3><div class="scroll" style="max-height:30vh"><table><thead><tr><th>when (UTC)</th><th>call</th><th>reason</th><th class="n">cost</th><th class="n">used</th><th class="n">left</th></tr></thead><tbody>{PLT}</tbody></table></div></div>
</div>
<div class="grid2">
<div class="panel"><h3>site traffic · views per day <span class="f">client-side counter (abacus) keyed by page and tab · my own file:// checks never count · last 14 days, UTC</span></h3><div class="bars" id="trBars"><span class="dim">loading the counter…</span></div>{TJ}</div>
<div class="panel"><h3>tab views <span class="f">rainman.html · which tabs get opened · all time</span></h3><div class="scroll" style="max-height:300px"><table><thead><tr><th>tab</th><th class="n">views</th><th></th></tr></thead><tbody id="tabViews"><tr><td colspan="3" class="dim">loading…</td></tr></tbody></table></div></div>
</div>
</main><script>{hit_js}{traffic_js}{sort_js}</script><script>(function(){{const mq=matchMedia('(max-width:760px)');let mo,tm;
function wrap(){{document.querySelectorAll('table').forEach(t=>{{if(t.closest('.mscroll,.tw,.tscroll,#mnav'))return;if(t.parentElement&&t.parentElement.closest('table'))return;const w=document.createElement('div');w.className='mscroll';t.parentNode.insertBefore(w,t);w.appendChild(t);const f=t.querySelector('tr');if(f&&f.children.length<=2)w.classList.add('one')}})}}
function grids(){{document.querySelectorAll('main *,body>div *').forEach(e=>{{if(e.classList.contains('mgrid1')||e.dataset.mg)return;const cs=getComputedStyle(e);if(cs.display!=='grid')return;const tr=cs.gridTemplateColumns.split(' ').filter(Boolean);e.dataset.mg='1';if(tr.length<2)return;const row=tr.some(x=>/^\d+(\.\d+)?px$/.test(x)&&parseFloat(x)<90);if(row)return;if(e.scrollWidth>e.clientWidth+2||tr.length>=3)e.classList.add('mgrid1')}})}}
function pass(){{wrap();grids()}}
function on(){{document.documentElement.classList.add('mob');pass();mo=new MutationObserver(()=>{{clearTimeout(tm);tm=setTimeout(pass,150)}});mo.observe(document.body,{{childList:true,subtree:true}})}}
function off(){{document.documentElement.classList.remove('mob');if(mo)mo.disconnect()}}
if(mq.matches)on();mq.addEventListener('change',e=>e.matches?on():off());window.rmMobile=mq}})();</script></body></html>'''
    os.makedirs('dashboard', exist_ok=True)
    open('dashboard/dev.html', 'w', encoding='utf-8').write(H)
    print(f'dashboard/dev.html: {len(H)//1024} KB · {len(L)} api calls · {len(R)} loop runs · {missed} missed slots · {len(E)} error lines · {len(PB.get("rows",[]))} games on the policy board · {len(B)} pages')

if __name__ == '__main__':
    main()
