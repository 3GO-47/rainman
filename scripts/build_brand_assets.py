"""Brand assets from scripts/brand.py — run after any change to the themes or the mascot.

Writes  dashboard/assets/mascot/<state>.svg     theme-aware (fills are var(--mark) etc; drop into any RAINMAN page)
        dashboard/assets/mascot/icon-<theme>.svg  app icon, flat colours, safe outside the site
        dashboard/assets/favicon.svg              the dark app icon, linked from every page
        dashboard/brand.html                      the living brand sheet: three themes, every mascot state, tokens, league tags
Usage:  python3 scripts/build_brand_assets.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
STATES = ['counting', 'edge', 'noplay', 'loading1', 'loading2', 'loading3', 'loading4', 'error', 'live']
THORP = ['idle', 'edge', 'noplay']
KELLY = ['counting', 'edge', 'noplay']
BLURB = {
    'counting': 'the default — RAINMAN is counting. Use it as the header mark on every page.',
    'edge': 'an edge cleared the threshold. Use beside a tier-A play or a filled arbitrage, never as decoration.',
    'noplay': 'nothing qualifies. Empty states, a filtered board with no rows, a league with no slate.',
    'loading1': 'one drip filled — the first of four load steps. Each drip is a tally.',
    'loading2': 'two drips filled.',
    'loading3': 'three drips filled.',
    'loading4': 'all four filled and the tally struck — the data is in.',
    'error': 'a pull failed or a number could not be trusted. Say what broke next to it.',
    'live': 'prices or scores are moving right now. The dot pulses; nothing else animates.',
}

def main():
    d = 'dashboard/assets/mascot'; os.makedirs(d, exist_ok=True)
    for s in STATES:
        open(f'{d}/{s}.svg', 'w', encoding='utf-8').write(brand.mascot(s, 128))
    for s in THORP:
        open(f'{d}/thorp-{s}.svg', 'w', encoding='utf-8').write(brand.thorp(s, 128))
    for s in KELLY:
        open(f'{d}/kelly-{s}.svg', 'w', encoding='utf-8').write(brand.kelly(s, 128))
    for t in brand.ORDER:
        open(f'{d}/icon-{t}.svg', 'w', encoding='utf-8').write(brand.app_icon(256, t))
        for w in brand.CREW:
            open(f'{d}/badge-{w}-{t}.svg', 'w', encoding='utf-8').write(brand.crew_badge(w, 128, t))
    open('dashboard/assets/favicon.svg', 'w', encoding='utf-8').write(brand.app_icon(64, 'dark'))

    swatch = lambda k, v: (f'<div class="sw"><span class="chip" style="background:{v};border-color:var(--edge2)"></span>'
                           f'<b>--{k}</b><i>{v}</i></div>')
    panes = ''
    for t in brand.ORDER:
        T = brand.THEMES[t]
        cells = ''.join(f'<figure>{brand.mascot(s, 64)}<figcaption>{s}</figcaption></figure>' for s in STATES)
        crew = (''.join(f'<figure>{brand.thorp(s, 64)}<figcaption>thorp {s}</figcaption></figure>' for s in THORP)
                + ''.join(f'<figure>{brand.kelly(s, 64)}<figcaption>kelly {s}</figcaption></figure>' for s in KELLY)
                + ''.join(f'<figure>{brand.crew_badge(w, 56, t)}<figcaption>{brand.CREW[w][0]}</figcaption></figure>'
                          for w in brand.CREW))
        tags = ''.join(f'<span class="tag" style="color:var(--lg-{k});border-color:var(--lg-{k})">{k.upper()}</span>'
                       for k in brand.LEAGUE_TAG[t])
        panes += (f'<section class="pane" data-theme="{t}"><h2>{brand.LABEL[t]}'
                  f'{" · current site, unchanged" if t == "dark" else ""}</h2>'
                  f'<div class="lock">{brand.lockup(40)}<span class="tl">{brand.TAGLINE}</span></div>'
                  f'<div class="row mas">{cells}</div>'
                  f'<div class="row mas">{crew}</div>'
                  f'<div class="row"><div class="icon">{brand.app_icon(72, t)}<span>app icon</span></div>'
                  f'<div class="stack">{brand.lockup(34, True)}<span>stacked</span></div>'
                  f'<div class="tags">{tags}<span>league tags</span></div></div>'
                  f'<div class="sws">{"".join(swatch(k, v) for k, v in T.items())}</div>'
                  f'<p class="voice">{brand.VOICE}</p></section>')

    css = """
*{box-sizing:border-box}html,body{margin:0;font:14px/1.5 Inter,system-ui,sans-serif;background:#0a0a0b;color:#e6e6e8;
 --mono:'JetBrains Mono',ui-monospace,Menlo,monospace}
header{padding:26px 24px 10px;max-width:1240px;margin:0 auto}
h1{font:800 28px/1.1 Inter,sans-serif;letter-spacing:-.4px;margin:0 0 6px}
header p{color:#9a9ca4;margin:0 0 4px;max-width:70ch}
header code{font:500 12px var(--mono);color:#e8b339}
main{max-width:1240px;margin:0 auto;padding:12px 24px 60px;display:grid;gap:16px}
.pane{background:var(--bg);color:var(--txt);border:1px solid var(--edge);border-radius:12px;padding:18px 20px}
.pane h2{font:600 10.5px var(--mono);letter-spacing:2.2px;text-transform:uppercase;color:var(--dim);margin:0 0 14px}
.lock{display:flex;align-items:center;gap:14px;margin-bottom:16px}
.lock .tl{font:500 12.5px var(--mono);letter-spacing:1px;color:var(--accent-text)}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px}
.mas figure{margin:0;text-align:center;background:var(--s2);border:1px solid var(--edge);border-radius:8px;padding:10px 12px}
figcaption{font:500 9px var(--mono);letter-spacing:1px;text-transform:uppercase;color:var(--dim2);margin-top:6px}
.icon,.stack,.tags{display:flex;flex-direction:column;align-items:flex-start;gap:6px;background:var(--s2);
 border:1px solid var(--edge);border-radius:8px;padding:10px 12px}
.icon span,.stack span,.tags span.l,.tags>span:last-child{font:500 9px var(--mono);letter-spacing:1px;text-transform:uppercase;color:var(--dim2)}
.tags{flex-direction:row;align-items:center;flex-wrap:wrap}
.tag{font:700 9.5px var(--mono);letter-spacing:1px;padding:2px 7px;border:1px solid;border-radius:4px}
.sws{display:grid;grid-template-columns:repeat(auto-fill,minmax(176px,1fr));gap:6px;margin-bottom:12px}
.sw{display:flex;align-items:center;gap:8px;font:500 10.5px var(--mono);color:var(--dim)}
.sw .chip{width:18px;height:18px;border-radius:4px;border:1px solid;flex:none}
.sw b{color:var(--txt);font-weight:600}.sw i{font-style:normal;color:var(--dim2);margin-left:auto}
.voice{font:500 12px var(--mono);color:var(--dim2);margin:0}
"""
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>RAINMAN · brand</title>'
            f'<link rel="icon" href="assets/favicon.svg">'
            f'<link rel="preconnect" href="https://fonts.googleapis.com">'
            f'<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
            f'<style>{brand.THEME_CSS}{css}</style></head><body>'
            f'<header><h1>RAINMAN brand</h1>'
            f'<p>Three themes, one set of variables. Every page reads them off <code>html[data-theme]</code> and remembers the choice in '
            f'<code>localStorage["rm-theme"]</code>. <b>Dark is the site as it was before themes existed and does not change</b> — '
            f'light and rain are built by remapping, never by editing dark.</p>'
            f'<p>Source of truth: <code>scripts/brand.py</code> · written up in <code>notes/brand.md</code> · '
            f'original sheet in <code>notes/brand/RAINMAN_Brand.pdf</code>.</p></header>'
            f'<main>{panes}</main></body></html>')
    open('dashboard/brand.html', 'w', encoding='utf-8').write(html)
    print(f'brand assets: {len(STATES) + len(THORP) + len(KELLY)} crew SVGs + {len(brand.ORDER)} app icons + favicon · dashboard/brand.html '
          f'{os.path.getsize("dashboard/brand.html") // 1024} KB')

if __name__ == '__main__':
    main()
