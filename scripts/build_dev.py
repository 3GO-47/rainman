"""The dev dashboard — dashboard/dev.html: what the machinery did, not what the model thinks.
Panels: Odds API spend (notes/odds_usage.log), loop runs and failures (notes/local_runs.log), data freshness (newest raw pulls,
latest depth chart, injuries, markets), build inventory (every dashboard page: size, built), site traffic (dashboard/traffic.json
when a counter is wired up — GitHub Pages serves no analytics of its own). Self-contained, black, no network."""
import os, re, csv, glob, json, html, datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
NOW = datetime.datetime.now()
def esc(s): return html.escape(str(s if s is not None else ''))

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
            log.append(dict(ts=p[0], what=p[1], cost=cost, used=kv.get('used', ''), left=kv.get('left', ''), reason=reason))
    return log

def loop_runs():
    runs = []; cur = None
    if not os.path.exists('notes/local_runs.log'): return runs
    for line in open('notes/local_runs.log', encoding='utf-8', errors='replace'):
        m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)', line.rstrip('\n'))
        if not m: continue
        ts, msg = m.groups()
        if msg.startswith('=== local loop') or msg.startswith('sleeper: waiting'):
            cur = dict(start=ts, kind='markets' if 'markets' in msg or 'sleeper' in msg else 'daily', steps=0, fails=[], pushed=False, end='', done='')
            runs.append(cur)
        if cur is None: continue
        if msg.startswith('run: ') or msg.startswith('  ') and ':' in msg: cur['steps'] += 1
        if msg.startswith('!!'): cur['fails'].append(msg[3:120])
        if msg.startswith('pushed'): cur['pushed'] = True
        if msg.startswith('=== done') or msg.startswith('=== markets run done'):
            cur['end'] = ts; cur['done'] = msg.split(':', 1)[1].strip() if ':' in msg else ''
            if 'markets' in msg: cur['kind'] = 'markets'
    return runs

def freshness():
    def newest(pat):
        f = sorted(glob.glob(pat)); return (f[-1], datetime.datetime.fromtimestamp(os.path.getmtime(f[-1]))) if f else ('', None)
    items = [('slate (ESPN)', 'data/raw/slate_all_*.txt'), ('depth chart', 'data/processed/depth_charts_*.csv'), ('injuries (ESPN)', 'data/raw/espn_injuries_*.txt'),
             ('DraftKings lines (ESPN)', 'data/raw/markets/draftkings_*.txt'), ('Kalshi', 'data/raw/markets/kalshi_*.txt'), ('Polymarket', 'data/raw/markets/polymarket_2*.txt'),
             ('Polymarket anytime TD', 'data/raw/markets/polymarket_td_*.txt'), ('Odds API lines', 'data/raw/markets/oddsapi_current.csv'), ('Odds API props', 'data/raw/odds_api/props_current.csv'),
             ('nflverse injuries', 'data/raw/nflverse/injuries_2026.parquet'), ('game logs 2026', 'data/game_logs/*2026*.csv'), ('bet_td', 'data/processed/bet_td.csv'), ('picks_all', 'data/processed/picks_all.csv')]
    out = []
    for name, pat in items:
        f, t = newest(pat); age = (NOW - t).total_seconds() / 3600 if t else None
        out.append(dict(name=name, file=os.path.basename(f) if f else '—', when=t.strftime('%Y-%m-%d %H:%M') if t else '—', age=age, size=os.path.getsize(f) if f else 0))
    return out

def builds():
    out = []
    for f in sorted(glob.glob('dashboard/*.html')):
        t = datetime.datetime.fromtimestamp(os.path.getmtime(f))
        out.append(dict(page=os.path.basename(f), kb=round(os.path.getsize(f) / 1024), when=t.strftime('%Y-%m-%d %H:%M'), age=(NOW - t).total_seconds() / 3600))
    return out

def traffic():
    try: return json.load(open('dashboard/traffic.json'))
    except Exception: return None

def main():
    L = api(); R = loop_runs(); F = freshness(); B = builds(); T = traffic()
    today = NOW.strftime('%Y-%m-%d'); mo = today[:7]
    by_day = {}
    for r in L: by_day.setdefault(r['ts'][:10], {'cost': 0, 'calls': 0, 'by': {}}); d = by_day[r['ts'][:10]]; d['cost'] += r['cost']; d['calls'] += 1; d['by'][r['reason']] = d['by'].get(r['reason'], 0) + r['cost']
    days = sorted(by_day)[-30:]; mx = max([by_day[d]['cost'] for d in days] + [1])
    last = L[-1] if L else {}
    mo_cost = sum(by_day[d]['cost'] for d in by_day if d.startswith(mo)); dom = int(today[8:10]); dim = (datetime.date(NOW.year + (NOW.month == 12), NOW.month % 12 + 1, 1) - datetime.timedelta(days=1)).day
    pace = mo_cost / max(1, dom) * dim
    GREY = '#8b98a5'
    RC = dict(open='#00c853', probe='#8fa3b8', move='#e8b339', close='#61dcff', lines='#c39bff', force='#ff9f43', free='#55606a', legacy='#55606a')
    by_reason = {}
    for r in L: by_reason.setdefault(r['reason'], [0, 0]); by_reason[r['reason']][0] += 1; by_reason[r['reason']][1] += r['cost']
    runs7 = [r for r in R if r['start'][:10] >= (NOW - datetime.timedelta(days=7)).strftime('%Y-%m-%d')]
    fails7 = sum(len(r['fails']) for r in runs7)
    agefmt = lambda h: '—' if h is None else (f'{h:.0f} h' if h < 72 else f'{h/24:.1f} d')
    age_cls = lambda h: 'g' if h is not None and h < 26 else 'a' if h is not None and h < 80 else 'r'
    tone = lambda x: 'g' if x else 'r'
    H = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · dev</title>
<style>
:root{{--bg:#000;--panel:#0a0b0d;--edge:#1c1f24;--edge2:#2a2e35;--txt:#e6e8ec;--dim:#8b98a5;--dim2:#55606a;--green:#00c853;--red:#ff5252;--amber:#e8b339;--cyan:#61dcff;--mono:ui-monospace,"JetBrains Mono",Menlo,Consolas,monospace;--ui:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:12.5px/1.45 var(--ui)}}a{{color:var(--cyan);text-decoration:none}}
header{{display:flex;align-items:center;gap:14px;padding:10px 18px;border-bottom:1px solid var(--edge)}}header b{{font:700 15px var(--mono);letter-spacing:2px}}header .mini{{color:var(--dim)}}header nav a{{margin-left:12px;font:600 11px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--dim)}}
main{{padding:12px 18px;max-width:1500px;margin:0 auto}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-bottom:12px}}.kpi{{background:var(--panel);border:1px solid var(--edge);border-radius:4px;padding:8px 10px}}.kpi .k{{display:block;font:600 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2)}}.kpi .v{{display:block;font:600 16px var(--mono);margin:4px 0 2px}}.kpi .s{{display:block;font:10.5px var(--ui);color:var(--dim)}}.kpi.g .v{{color:var(--green)}}.kpi.r .v{{color:var(--red)}}.kpi.a .v{{color:var(--amber)}}
.panel{{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:10px 12px;margin-bottom:12px}}.panel h3{{margin:0 0 6px;font:600 12px var(--ui);letter-spacing:.06em;text-transform:uppercase}}.panel h3 .f{{font:400 11px var(--ui);text-transform:none;letter-spacing:0;color:var(--dim);margin-left:8px}}
table{{width:100%;border-collapse:collapse;font-size:11.5px}}th{{text-align:left;font:600 9px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--dim2);padding:3px 6px;border-bottom:1px solid var(--edge2)}}td{{padding:3px 6px;border-bottom:1px solid var(--edge);font-family:var(--mono);white-space:nowrap}}td.r,th.r{{text-align:right}}.g{{color:var(--green)}}.r{{color:var(--red)}}.a{{color:var(--amber)}}.dim{{color:var(--dim2)}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}@media(max-width:900px){{.grid2{{grid-template-columns:1fr}}}}
.bars{{display:flex;align-items:flex-end;gap:3px;height:120px;padding:4px 0 18px}}.b{{flex:1 1 0;max-width:34px;height:100%;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;position:relative}}.bar{{width:100%;height:100%;display:flex;flex-direction:column-reverse}}.bar i{{display:block;width:100%}}.b b{{font:600 9px var(--mono);color:var(--dim);margin-top:2px}}.b span{{position:absolute;bottom:-14px;font:8.5px var(--mono);color:var(--dim2)}}
.tag{{display:inline-block;font:600 8.5px var(--mono);letter-spacing:.5px;padding:0 4px;border:1px solid;border-radius:2px;line-height:14px}}
.scroll{{max-height:44vh;overflow:auto}}
</style></head><body>
<header><b>RAINMAN · DEV</b><span class="mini">built {NOW.strftime('%Y-%m-%d %H:%M')} · the machinery, not the model</span><nav><a href="rainman.html">dashboard</a><a href="arb.html">arb</a><a href="index.html">landing</a></nav></header><main>
<div class="kpis">
 <div class="kpi"><span class="k">Odds API · plan</span><span class="v">100,000</span><span class="s">credits a month</span></div>
 <div class="kpi {'r' if last and str(last.get('left','')).isdigit() and int(last['left'])<5000 else ''}"><span class="k">used · plan period</span><span class="v">{esc(last.get('used','—'))}</span><span class="s">{esc(last.get('left','—'))} left · last header {esc(last.get('ts','—'))}</span></div>
 <div class="kpi {'r' if pace>100000 else 'a' if pace>50000 else 'g'}"><span class="k">logged this month</span><span class="v">{mo_cost:,}</span><span class="s">pace {int(pace):,} / month</span></div>
 <div class="kpi"><span class="k">loop runs · 7 days</span><span class="v">{len(runs7)}</span><span class="s">{sum(1 for r in runs7 if r['kind']=='daily')} daily · {sum(1 for r in runs7 if r['kind']=='markets')} markets · {sum(1 for r in runs7 if r['pushed'])} pushed</span></div>
 <div class="kpi {'r' if fails7 else 'g'}"><span class="k">step failures · 7 days</span><span class="v">{fails7}</span><span class="s">from notes/local_runs.log</span></div>
 <div class="kpi"><span class="k">site traffic</span><span class="v">{esc(T.get('visits_7d','—')) if T else '—'}</span><span class="s">{'visits, last 7 days' if T else 'no counter wired yet — GitHub Pages has none'}</span></div>
</div>
<div class="panel"><h3>Odds API · credits per day <span class="f">last {len(days)} days with calls · split by reason · hover for the calls</span></h3>
<div class="bars">{''.join(f'<div class="b" title="{d}: {by_day[d]["cost"]} credits · {by_day[d]["calls"]} calls · {", ".join(k+" "+str(v) for k,v in sorted(by_day[d]["by"].items(),key=lambda kv:-kv[1]) if v)}"><div class="bar">{"".join(f"<i style=&quot;height:{100*v/mx:.1f}%;background:{RC.get(k,GREY)}&quot;></i>" for k,v in sorted(by_day[d]["by"].items(),key=lambda kv:-kv[1]) if v)}</div><b>{by_day[d]["cost"] or ""}</b><span>{d[5:]}</span></div>' for d in days) or '<span class="dim">no calls logged</span>'}</div>
<p class="dim" style="margin:4px 0 0">{' '.join(f'<span class="tag" style="color:{c};border-color:{c}66">{k.upper()}</span>' for k,c in RC.items())} · by reason: {' · '.join(f'{k} {v[1]:,} credits / {v[0]} calls' for k,v in sorted(by_reason.items(),key=lambda kv:-kv[1][1]))}</p></div>
<div class="grid2">
<div class="panel"><h3>loop runs <span class="f">newest first · from notes/local_runs.log · a run = one Task Scheduler pass or one planted sleeper</span></h3><div class="scroll"><table><thead><tr><th>start</th><th>kind</th><th>end</th><th class="r">steps</th><th>failures</th><th>push</th><th>did</th></tr></thead><tbody>
{''.join(f'<tr><td>{esc(r["start"])}</td><td>{esc(r["kind"])}</td><td class="dim">{esc(r["end"][11:] if r["end"] else "…")}</td><td class="r">{r["steps"]}</td><td class="{"r" if r["fails"] else "dim"}">{esc("; ".join(r["fails"])[:90]) if r["fails"] else "—"}</td><td class="{tone(r["pushed"])}">{"pushed" if r["pushed"] else "—"}</td><td class="dim">{esc(r["done"][:60])}</td></tr>' for r in reversed(R[-60:])) or '<tr><td colspan="7" class="dim">no runs logged</td></tr>'}</tbody></table></div></div>
<div class="panel"><h3>data freshness <span class="f">newest file per source · green under 26 h, amber under 80 h</span></h3><table><thead><tr><th>source</th><th>file</th><th>updated</th><th class="r">age</th><th class="r">size</th></tr></thead><tbody>
{''.join(f'<tr><td>{esc(f["name"])}</td><td class="dim">{esc(f["file"])}</td><td>{esc(f["when"])}</td><td class="r {age_cls(f["age"])}">{agefmt(f["age"])}</td><td class="r dim">{f["size"]//1024 if f["size"] else "—"} KB</td></tr>' for f in F)}</tbody></table></div>
</div>
<div class="grid2">
<div class="panel"><h3>builds <span class="f">every page the loop writes</span></h3><table><thead><tr><th>page</th><th class="r">size</th><th>built</th><th class="r">age</th></tr></thead><tbody>
{''.join(f'<tr><td><a href="{esc(b["page"])}">{esc(b["page"])}</a></td><td class="r">{b["kb"]:,} KB</td><td>{esc(b["when"])}</td><td class="r {age_cls(b["age"])}">{b["age"]:.0f} h</td></tr>' for b in B)}</tbody></table></div>
<div class="panel"><h3>Odds API · pull log <span class="f">newest first · cost from the x-requests-last header</span></h3><div class="scroll"><table><thead><tr><th>when (UTC)</th><th>call</th><th>reason</th><th class="r">cost</th><th class="r">used</th><th class="r">left</th></tr></thead><tbody>
{''.join(f'<tr><td class="dim">{esc(r["ts"])}</td><td>{esc(r["what"])}</td><td><span class="tag" style="color:{RC.get(r["reason"],GREY)};border-color:{RC.get(r["reason"],GREY)}66">{esc(r["reason"].upper())}</span></td><td class="r {"" if r["cost"] else "dim"}">{r["cost"]}</td><td class="r dim">{esc(r["used"])}</td><td class="r dim">{esc(r["left"])}</td></tr>' for r in reversed(L[-300:])) or '<tr><td colspan="6" class="dim">nothing yet</td></tr>'}</tbody></table></div></div>
</div>
<div class="panel"><h3>site traffic <span class="f">GitHub Pages serves no analytics; wire a privacy-light counter (GoatCounter / Plausible) and drop its JSON at dashboard/traffic.json to fill the tile</span></h3>
{('<pre class="dim">'+esc(json.dumps(T, indent=1)[:2000])+'</pre>') if T else '<p class="dim">not wired yet — the tile above reads dashboard/traffic.json ({"visits_7d": n, "visits_30d": n, "pages": {...}}) when it exists</p>'}</div>
</main></body></html>'''
    os.makedirs('dashboard', exist_ok=True)
    open('dashboard/dev.html', 'w', encoding='utf-8').write(H)
    print(f'dashboard/dev.html: {len(H)//1024} KB · {len(L)} api calls · {len(R)} loop runs · {len(F)} sources · {len(B)} pages')

if __name__ == '__main__':
    main()
