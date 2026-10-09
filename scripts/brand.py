"""RAINMAN brand: the three themes, the mascot and its states — the single source of truth every page builder imports.

Source: notes/brand/RAINMAN_Brand.pdf (Josh, 2026-10-08). DARK is exactly what was live before themes existed and must not change.
Docs: notes/brand.md. Standalone mascot files: dashboard/assets/mascot/*.svg (written by scripts/build_brand_assets.py).

Usage in a page builder:
    from brand import THEME_CSS, THEME_JS, theme_switch_html, alias_css, mascot
    ...<style>{THEME_CSS}{alias_css('arb')}{YOUR_CSS}</style>...
    ...<header>{theme_switch_html()}</header>...
    ...<script>{THEME_JS}</script>
"""

# ------------------------------------------------------------------ tokens
# Every page uses these names. Page-local vocabularies are aliased onto them by alias_css().
THEMES = {
    'dark': {  # the live site. Only the retired gold family moved: the secondary is now rain blue
        'bg': '#000', 'panel': '#0b0b0c', 's2': '#131315', 's3': '#1a1a1d',
        'edge': '#1d1e21', 'edge2': '#2a2b30',
        'txt': '#e6e6e8', 'dim': '#9a9ca4', 'dim2': '#60626a',
        'accent': '#2b6bff', 'accent-text': '#5c93ff', 'on-accent': '#ffffff',
        'amber': '#2b6bff', 'green': '#3fb950', 'red': '#f0564a',
        'cyan': '#8ab4d8', 'violet': '#a99bd6', 'blue': '#6c8cff', 'pink': '#e86fa8',
        'mark': '#e6e6e8', 'mark-shade': '#1a1a1d',
    },
    'light': {  # paper. bg / txt / accent are the brand sheet's; the rest are tuned for contrast on paper
        'bg': '#f3efe6', 'panel': '#fdfbf6', 's2': '#f6f2e9', 's3': '#e9e3d4',
        'edge': '#d5cbb5', 'edge2': '#b9ad92',
        'txt': '#14213d', 'dim': '#434c63', 'dim2': '#596072',
        'accent': '#b8460b', 'accent-text': '#a8400a', 'on-accent': '#ffffff',
        'amber': '#8f6410', 'green': '#157348', 'red': '#b32424',
        'cyan': '#16627e', 'violet': '#53439b', 'blue': '#2743a8', 'pink': '#a8336c',
        'mark': '#14213d', 'mark-shade': '#f3efe6',
    },
    'rain': {  # midnight. bg / accent are the brand sheet's; surfaces stepped so panels lift off the page
        'bg': '#0b1220', 'panel': '#111c30', 's2': '#17243c', 's3': '#1f3050',
        'edge': '#2a3d5c', 'edge2': '#3b5680',
        'txt': '#e6f1ff', 'dim': '#a8bcd6', 'dim2': '#8196b2',
        'accent': '#19e3b1', 'accent-text': '#19e3b1', 'on-accent': '#0b1220',
        'amber': '#f2c75c', 'green': '#4fe08a', 'red': '#ff7a7a',
        'cyan': '#6cb6ff', 'violet': '#b3a6ff', 'blue': '#7f9cff', 'pink': '#ff86c0',
        'mark': '#e6f1ff', 'mark-shade': '#1f3050',
    },
}
ORDER = ['dark', 'light', 'rain']
LABEL = {'dark': 'Dark', 'light': 'Light', 'rain': 'Rain'}

# one tag colour per league, darker on paper
LEAGUE_TAG = {
    'dark':  {'nfl': '#6c8cff', 'cfb': '#f0564a', 'nba': '#a99bd6', 'wnba': '#e86fa8', 'nhl': '#8ab4d8'},
    'light': {'nfl': '#2743a8', 'cfb': '#b32a1f', 'nba': '#5b4b9a', 'wnba': '#a8336c', 'nhl': '#1d6e8c'},
    'rain':  {'nfl': '#6cb6ff', 'cfb': '#ff6b6b', 'nba': '#a99bff', 'wnba': '#ff86c0', 'nhl': '#7fd4ff'},
}

def _vars(t):
    return ''.join(f'--{k}:{v};' for k, v in THEMES[t].items())

THEME_CSS = (
    f':root,[data-theme="dark"]{{{_vars("dark")}}}\n'
    f'[data-theme="light"]{{{_vars("light")}}}\n'
    f'[data-theme="rain"]{{{_vars("rain")}}}\n'
    + ''.join(
        f'[data-theme="{t}"]{{' + ''.join(f'--lg-{k}:{v};' for k, v in LEAGUE_TAG[t].items()) + '}\n'
        for t in ORDER)
    + ':root{' + ''.join(f'--lg-{k}:{v};' for k, v in LEAGUE_TAG['dark'].items()) + '}\n'
    + 'html{color-scheme:dark}[data-theme="light"]{color-scheme:light}\n'
)

# page-local vocabularies mapped onto the canonical names, so one token set drives every page
ALIAS = {
    # arb.html / social.html / tennis.html / index.html
    'app': {'p': 'panel', 'p2': 's2', 'p3': 's3', 'e': 'edge', 'e2': 'edge2',
            'fg': 'txt', 'mute': 'dim2', 'acc': 'accent', 'g': 'green', 'r': 'red', 'b': 'cyan'},
    # sport pages / shells / social: canonical plus a few short names
    'alt': {'fg': 'txt', 'mute': 'dim2', 'acc': 'accent', 'blue': 'cyan'},
    # the NFL / NCAA dashboards already speak the canonical names
    'dash': {},
}

def alias_css(kind='app'):
    m = ALIAS.get(kind, {})
    return (':root{' + ''.join(f'--{a}:var(--{b});' for a, b in m.items()) + '}\n') if m else ''

# ------------------------------------------------------------------ the switch
THEME_JS = r"""
(function(){var K='rm-theme',O=['dark','light','rain'];
 function set(t){if(O.indexOf(t)<0)t='dark';document.documentElement.dataset.theme=t;try{localStorage.setItem(K,t)}catch(e){}
   document.querySelectorAll('[data-rmtheme]').forEach(function(b){b.classList.toggle('on',b.dataset.rmtheme===t)});}
 var cur='dark';try{cur=localStorage.getItem(K)||'dark'}catch(e){}
 set(cur);
 addEventListener('DOMContentLoaded',function(){set(document.documentElement.dataset.theme||'dark');
   document.querySelectorAll('[data-rmtheme]').forEach(function(b){b.onclick=function(){set(b.dataset.rmtheme)}});});
})();
"""
# inline, runs before paint so there is no flash of the wrong theme; carries the app icon too
_BOOT = ("<script>(function(){try{var t=localStorage.getItem('rm-theme')||'dark';"
         "document.documentElement.dataset.theme=['dark','light','rain'].indexOf(t)<0?'dark':t}"
         "catch(e){document.documentElement.dataset.theme='dark'}})();</script>")

def favicon_tag(theme='dark'):
    return f'<link rel="icon" href="{favicon_href(theme)}">'

SWITCH_CSS = """
.rmsw{display:inline-flex;border:1px solid var(--edge2);border-radius:5px;overflow:hidden;flex:none}
.rmsw button{background:transparent;border:0;border-right:1px solid var(--edge2);padding:3px 8px;cursor:pointer;
 font:600 9.5px/1.6 var(--mono,monospace);letter-spacing:1px;text-transform:uppercase;color:var(--dim2)}
.rmsw button:last-child{border-right:0}
.rmsw button:hover{color:var(--txt)}
.rmsw button.on{background:var(--accent);color:var(--on-accent)}
"""

def theme_switch_html(title='theme'):
    btns = ''.join(f'<button data-rmtheme="{t}" title="{LABEL[t]} theme">{t[0].upper()}</button>' for t in ORDER)
    return f'<span class="rmsw" role="group" aria-label="{title}">{btns}</span>'

# ------------------------------------------------------------------ team colours
# Real club colours are kept (that is the rule), but a colour picked to glow on black
# is often invisible on paper. Each team ships as --tc-<ABBR>, re-leveled per theme, so
# the page markup never has to know which theme is on.

def _srgb(c):
    c = c / 255
    return c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4

def _wl(rgb):
    return .2126 * _srgb(rgb[0]) + .7152 * _srgb(rgb[1]) + .0722 * _srgb(rgb[2])

def contrast(a, b):
    la, lb = _wl(_hex2rgb(a)[:3] if isinstance(a, str) else a), _wl(_hex2rgb(b)[:3] if isinstance(b, str) else b)
    return (max(la, lb) + .05) / (min(la, lb) + .05)

def level(hexv, theme, target=4.5, on=None):
    """Keep a colour's hue, move its lightness until it is legible on `on` (default: the theme's panel)."""
    try: rgb = _hex2rgb(hexv)[:3]
    except Exception: return hexv
    bg = _hex2rgb(on or THEMES[theme]['panel'])[:3]
    toward = (0, 0, 0) if _wl(bg) > .5 else (255, 255, 255)
    best = rgb
    for i in range(0, 41):                       # walk toward ink (on paper) or light (on a dark page)
        c = _mix(rgb, toward, i / 50)
        best = c
        if contrast(tuple(c), bg) >= target: break
    return _fmt(*best, 1.0)

def team_color_css(teams, var='tc'):
    """teams: {ABBR: '#rrggbb'} -> :root plus one override block per theme."""
    teams = {k: v for k, v in teams.items() if isinstance(v, str) and v.startswith('#') and len(v) in (4, 7)}
    if not teams: return ''
    out = ':root{' + ''.join(f'--{var}-{k}:{v};' for k, v in teams.items()) + '}\n'
    for t in ('light', 'rain'):
        out += f'[data-theme="{t}"]{{' + ''.join(f'--{var}-{k}:{level(v, t)};' for k, v in teams.items()) + '}\n'
    return out

# ------------------------------------------------------------------ the mascot
# A rain cloud wearing a visor, five drips hanging underneath, and a tally stroke counted across them.
# Colours come from the theme: cloud = --mark, visor = --mark-shade, eyes + tally = --accent.
_CLOUD = ('<circle cx="17" cy="20.5" r="10.5"/><circle cx="32" cy="16" r="13.5"/><circle cx="47" cy="20.5" r="10.5"/>'
          '<rect x="6.5" y="20" width="51" height="14" rx="5"/>')
_DRIPS = [(12.2, 11), (21.1, 16), (30.0, 12.5), (38.9, 16.5), (47.8, 10.5)]
_VISOR = '<rect x="10.5" y="18.4" width="43" height="11.6" rx="5.8"/>'
_BOLT = '<path d="M55.5 1.5 L46.8 13.4 h5.1 l-3.4 9.6 L58.6 9.8 h-5.3 z"/>'

def mascot(state='counting', size=28, cls='rmask', title=None, anim=False):
    """state: counting · edge · noplay · loading1-4 · error · live.
    Returns an inline SVG that themes itself — no fills are hard-coded."""
    if anim:          # the drips grow and let go, left to right -- used on the landing page only
        drips = ''.join('<rect x="%s" y="32" width="6.2" height="%s" rx="3.1">'
                        '<animate attributeName="height" values="%s;%s;%s" dur="2.6s" begin="%ss" '
                        'repeatCount="indefinite" calcMode="spline" keyTimes="0;0.55;1" '
                        'keySplines="0.4 0 0.2 1;0.4 0 0.2 1"/></rect>'
                        % (x, h, round(h * .45, 1), round(h * 1.45, 1), round(h * .45, 1), round(i * .21, 2))
                        for i, (x, h) in enumerate(_DRIPS))
    else:
        drips = ''.join(f'<rect x="{x}" y="32" width="6.2" height="{h}" rx="3.1"/>' for x, h in _DRIPS)
    mark = 'var(--mark)'; shade = 'var(--mark-shade)'; acc = 'var(--accent)'
    eyes = f'<circle cx="25.4" cy="24.2" r="2.2" fill="{acc}"/><circle cx="38.6" cy="24.2" r="2.2" fill="{acc}"/>'
    tally = f'<path d="M7 50.5 L57 37.5" stroke="{acc}" stroke-width="4.2" stroke-linecap="round" fill="none"/>'
    extra = ''
    if state == 'noplay':
        mark = 'var(--dim2)'; eyes = f'<rect x="23.2" y="23.1" width="6" height="2.3" rx="1.15" fill="{shade}" opacity=".55"/>' \
                                     f'<rect x="36.4" y="23.1" width="6" height="2.3" rx="1.15" fill="{shade}" opacity=".55"/>'
        drips = ''.join(f'<rect x="{x}" y="32" width="6.2" height="{min(h, 7)}" rx="3.1"/>' for x, h in _DRIPS)
        tally = ''
    elif state == 'edge':
        extra = f'<g fill="{acc}">{_BOLT}</g>'
    elif state == 'error':
        x = lambda cx: (f'<path d="M{cx - 2.3} 21.9 L{cx + 2.3} 26.5 M{cx + 2.3} 21.9 L{cx - 2.3} 26.5" '
                        f'stroke="var(--red)" stroke-width="1.9" stroke-linecap="round"/>')
        eyes = x(25.4) + x(38.6)
        tally = '<path d="M7 50.5 L57 37.5" stroke="var(--red)" stroke-width="4.2" stroke-linecap="round" fill="none"/>'
    elif state == 'live':
        extra = f'<circle cx="54" cy="8" r="5" fill="{acc}"><animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></circle>'
    elif state.startswith('loading'):
        n = int(state[-1]) if state[-1].isdigit() else 1          # each drip is a tally; loading fills them left to right
        FADE = ' opacity="0.4"'
        drips = ''.join('<rect x="%s" y="32" width="6.2" height="%s" rx="3.1"%s/>'
                        % (x, h if i < n else 6, '' if i < n else FADE) for i, (x, h) in enumerate(_DRIPS))
        tally = tally if n >= 4 else ''
    t = f'<title>{title}</title>' if title else ''
    return (f'<svg class="{cls}" width="{size}" height="{size * 56 // 64}" viewBox="0 0 64 56" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="RAINMAN {state}">{t}'
            f'<g fill="{mark}">{_CLOUD}{drips}</g><g fill="{shade}">{_VISOR}</g>{eyes}{tally}{extra}</svg>')


# ------------------------------------------------------------------ the rest of the crew
# RAINMAN is the cloud. THORP is the umbrella — he covers the slate. KELLY is the raindrop,
# and she carries the +1 card. Same colour logic as the cloud: body = --mark, visor = --mark-shade,
# accent parts = --accent, so all three re-skin with the theme and none of them hard-codes a fill.

def thorp(state='idle', size=28, cls='rmask', title=None):
    """state: idle · edge · noplay (soaked)."""
    mark, shade, acc = 'var(--mark)', 'var(--mark-shade)', 'var(--accent)'
    dim = 'var(--dim2)'
    body, tilt, extra = mark, '', ''
    mouth = f'<path d="M26.4 42.6 q5.6 5.2 11.2 0" stroke="{shade}" stroke-width="2.4" stroke-linecap="round" fill="none"/>'
    eyes = f'<circle cx="28.3" cy="35.1" r="2.1" fill="{acc}"/><circle cx="35.7" cy="35.1" r="2.1" fill="{acc}"/>'
    feet = (f'<ellipse cx="26.2" cy="57.2" rx="4.6" ry="2.8" fill="{acc}"/>'
            f'<ellipse cx="37.8" cy="57.2" rx="4.6" ry="2.8" fill="{acc}"/>')
    nub = f'<rect x="29.6" y="4" width="4.8" height="11" rx="2.4" fill="{acc}"/>'
    if state == 'noplay':                                  # soaked: canopy droops, the rain won
        body, feet = dim, feet.replace(acc, dim)
        nub = nub.replace(acc, dim)
        eyes = (f'<rect x="25.6" y="34" width="5.4" height="2.2" rx="1.1" fill="{mark}" opacity=".5"/>'
                f'<rect x="33" y="34" width="5.4" height="2.2" rx="1.1" fill="{mark}" opacity=".5"/>')
        tilt = ' transform="rotate(-9 32 21)"'
        mouth = f'<path d="M26.4 45 q5.6 -5 11.2 0" stroke="{shade}" stroke-width="2.4" stroke-linecap="round" fill="none"/>'
        extra = ''.join(f'<rect x="{x}" y="{y}" width="3" height="7" rx="1.5" fill="{dim}" opacity=".55"/>'
                        for x, y in ((16, 2), (31, 0), (46, 3)))
    elif state == 'edge':                                  # the spark: he found one
        extra = ''.join(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{acc}" stroke-width="2.4" stroke-linecap="round"/>'
                        for x1, y1, x2, y2 in ((44, 10, 51, 5), (46, 16, 54, 14), (41, 6, 45, 0)))
    t = f'<title>{title}</title>' if title else ''
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Thorp {state}">{t}'
            f'<g{tilt}>{nub}<rect x="8" y="14.5" width="48" height="15" rx="7.5" fill="{body}"/></g>'
            f'<rect x="24.2" y="27" width="15.6" height="29" rx="6" fill="{body}"/>'
            f'<rect x="24.2" y="30.4" width="15.6" height="9.4" rx="4.7" fill="{shade}"/>'
            f'{eyes}{mouth}{feet}{extra}</svg>')

_DROP = 'M32 4 C32 4 14.5 26.5 14.5 39 a17.5 17.5 0 1 0 35 0 C49.5 26.5 32 4 32 4 Z'

def kelly(state='counting', size=28, cls='rmask', title=None, card=True):
    """state: counting · edge · noplay. The +1 card is hers; drop it with card=False for a plain drop."""
    body, face = 'var(--accent)', 'var(--on-accent)'
    if state == 'noplay': body, face = 'var(--dim2)', 'var(--bg)'
    mouth = f'<path d="M25.6 48.6 q6.4 5.6 12.8 0" stroke="{face}" stroke-width="2.6" stroke-linecap="round" fill="none"/>'
    if state == 'noplay':
        mouth = f'<path d="M25.6 51.4 q6.4 -5.2 12.8 0" stroke="{face}" stroke-width="2.6" stroke-linecap="round" fill="none"/>'
    spark = ''
    if state == 'edge':
        spark = ''.join(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{body}" stroke-width="2.4" stroke-linecap="round"/>'
                        for x1, y1, x2, y2 in ((47, 14, 54, 8), (50, 21, 58, 18)))
    plus = ('<g transform="rotate(14 50 50)">'
            f'<rect x="40.5" y="40.5" width="19" height="19" rx="3.4" fill="var(--txt)"/>'
            f'<text x="50" y="53.4" text-anchor="middle" fill="var(--bg)" '
            f'font-family="var(--mono,ui-monospace,monospace)" font-size="11" font-weight="700">+1</text></g>') if card else ''
    t = f'<title>{title}</title>' if title else ''
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Kelly {state}">{t}'
            f'<path d="{_DROP}" fill="{body}"/>'
            f'<rect x="20.4" y="36.2" width="23.2" height="8.8" rx="4.4" fill="{face}"/>'
            f'{mouth}{spark}{plus}</svg>')

CREW = {'rainman': ('Rainman', 'the cloud', mascot), 'thorp': ('Thorp', 'the umbrella', thorp),
        'kelly': ('Kelly', 'the raindrop', kelly)}


def _flat(svg, theme, knockout=True):
    """Resolve a crew SVG's variables to literals. knockout=True draws it onto an accent field:
    the body takes the on-accent colour and the detail takes the accent back, so it reads at 16px."""
    T = THEMES[theme]
    pal = {'mark': 'on-accent', 'mark-shade': 'accent', 'accent': 'on-accent', 'on-accent': 'accent',
           'txt': 'on-accent', 'bg': 'accent', 'dim2': 'on-accent', 'red': 'on-accent'} if knockout else \
          {k: k for k in T}
    return _re.sub(r'var\(--([a-z-]+)(?:,[^)]*)?\)', lambda m: T.get(pal.get(m.group(1), m.group(1)), T['txt']), svg)

def app_icon(size=64, theme='dark', who='kelly'):
    """Rounded-square app icon: accent field, one of the crew knocked out of it. Kelly is the default."""
    T = THEMES[theme]
    inner = CREW[who][2]('counting' if who != 'thorp' else 'idle', 64, cls='')
    inner = _flat(inner, theme).replace('<svg ', '<svg x="7" y="7" ', 1)
    inner = _re.sub(r'(<svg x="7" y="7" class="" )width="64" height="\d+"', r'\1width="50" height="50"', inner)
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="RAINMAN">'
            f'<rect width="64" height="64" rx="14" fill="{T["accent"]}"/>{inner}</svg>')

def crew_badge(who='rainman', size=48, theme='dark'):
    """The round badge from the brand sheet: accent disc, crew member knocked out."""
    T = THEMES[theme]
    inner = _flat(CREW[who][2]('counting' if who != 'thorp' else 'idle', 64, cls=''), theme)
    inner = _re.sub(r'(<svg class="" )width="64" height="\d+"', r'\1x="10" y="10" width="44" height="44"', inner)
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{CREW[who][0]}">'
            f'<circle cx="32" cy="32" r="32" fill="{T["accent"]}"/>{inner}</svg>')

def favicon_href(theme='dark'):
    import base64
    return 'data:image/svg+xml;base64,' + base64.b64encode(app_icon(64, theme).encode()).decode()

def lockup(size=34, stacked=False, cls='rmlock'):
    """Rainman + Kelly + wordmark. The wordmark is live text so it inherits the page font."""
    m = (f'<span style="display:inline-flex;align-items:flex-end;gap:0;margin-right:{size//10}px">'
         f'{mascot("counting", size)}'
         f'<span style="margin-left:-{int(size*.26)}px;margin-bottom:-{int(size*.06)}px">{kelly("counting", int(size * .78))}</span></span>')
    if stacked:
        return (f'<span class="{cls} st" style="display:inline-flex;flex-direction:column;align-items:center;gap:4px">'
                f'{m}<b style="font:800 {max(13, size // 2)}px/1 var(--mono,monospace);letter-spacing:4px;color:var(--mark)">RAINMAN</b></span>')
    return (f'<span class="{cls}" style="display:inline-flex;align-items:center;gap:9px">{m}'
            f'<b style="font:800 {max(13, int(size * .46))}px/1 var(--mono,monospace);letter-spacing:5px;color:var(--mark)">RAINMAN</b></span>')

TAGLINE = 'Count the edge.'
VOICE = 'Number first. Work second. No locks, no promises.'


# ------------------------------------------------------------------ automatic theming of legacy CSS
# The dashboards carry hundreds of hard-coded colours from before themes existed. Rewriting them by hand would
# risk changing DARK, which must stay byte-identical. Instead every literal becomes var(--kN, ORIGINAL): dark
# defines none of those vars, so it resolves to the original literal and cannot drift; light and rain define
# them, mapped by role. Greys ride the theme's background-to-text ramp, saturated colours snap to the nearest
# semantic token of that theme, and alpha is preserved.
import re as _re

_HEX = _re.compile(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
_RGBA = _re.compile(r'rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)')

def _hex2rgb(h):
    h = h.lstrip('#')
    if len(h) == 3: h = ''.join(c * 2 for c in h)
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a

def _parse(lit):
    if lit.startswith('#'): return _hex2rgb(lit)
    n = [float(x) for x in _re.findall(r'[\d.]+', lit)]
    return int(n[0]), int(n[1]), int(n[2]), (n[3] if len(n) > 3 else 1.0)

def _fmt(r, g, b, a):
    r, g, b = (max(0, min(255, round(v))) for v in (r, g, b))
    return f'#{r:02x}{g:02x}{b:02x}' if a >= 0.999 else f'rgba({r},{g},{b},{round(a, 3)})'

def _lum(r, g, b): return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255

def _sat(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    return 0 if mx == 0 else (mx - mn) / mx

def _hue(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn: return 0.0
    d = mx - mn
    h = (60 * ((g - b) / d) + 360) if mx == r else (60 * ((b - r) / d) + 120) if mx == g else (60 * ((r - g) / d) + 240)
    return h % 360

def _mix(c1, c2, t):
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))

# ---- dark -> theme colour mapping -------------------------------------------------
# Three rules, in order, so the result is designed rather than merely computed:
#   1. a literal that IS one of dark's tokens becomes that token in the target theme (exact, by name)
#   2. a grey rides an ANCHORED ramp: dark's own surface/text steps are the knots, so #0b0b0c lands on
#      the theme's panel and #9a9ca4 on its dim -- surfaces keep their separation instead of collapsing
#   3. anything saturated snaps to the nearest semantic token by hue, then keeps its EMPHASIS: a literal
#      dimmer than dark's token fades toward the theme's bg by the same ratio, a brighter one pushes past it

_EXACT = {}
for _k, _v in THEMES['dark'].items():
    _EXACT.setdefault(_v.lower(), _k)
_EXACT['#e8b339'] = 'accent-text'   # the brand gold reads as TEXT more often than as a fill
for _k, _v in LEAGUE_TAG['dark'].items():
    _EXACT.setdefault(_v.lower(), 'lg-' + _k)

def _tok(theme, name):
    return _hex2rgb(LEAGUE_TAG[theme][name[3:]] if name.startswith('lg-') else THEMES[theme][name])[:3]

# knots for the grey ramp: dark's structural greys, darkest first
_RAMP = ['bg', 'panel', 's2', 's3', 'edge', 'edge2', 'dim2', 'dim', 'txt']
_KNOTS = sorted(((_lum(*_tok('dark', n)), n) for n in _RAMP), key=lambda x: x[0])

def _grey(L, theme):
    ks = _KNOTS
    if L <= ks[0][0]: return _tok(theme, ks[0][1])
    if L >= ks[-1][0]:                                  # brighter than dark's text -> push to pure ink/paper
        hi = _tok(theme, ks[-1][1])
        return _mix(hi, (255, 255, 255) if _lum(*_tok(theme, 'bg')) < .5 else (0, 0, 0),
                    min((L - ks[-1][0]) / max(1e-6, 1 - ks[-1][0]), 1) * .6)
    for i in range(len(ks) - 1):
        a, b = ks[i], ks[i + 1]
        if a[0] <= L <= b[0]:
            t = 0 if b[0] == a[0] else (L - a[0]) / (b[0] - a[0])
            return _mix(_tok(theme, a[1]), _tok(theme, b[1]), t)
    return _tok(theme, 'txt')

# Hue anchors for the semantic buckets. Fixed, not read off the live palette: dark's --amber is rain
# blue now, so deriving them would send every gold literal to the nearest surviving hue (red).
_BUCKETS = [(4, 'red'), (43, 'amber'), (128, 'green'), (206, 'cyan'), (228, 'blue'), (253, 'violet'), (331, 'pink')]

_GOLD = (20, 66)        # hue window of the retired amber/gold family

def map_color(lit, theme):
    """One dark literal -> its counterpart in `theme`."""
    r, g, b, a = _parse(lit)
    if theme == 'dark':
        # dark is the live site and stays byte-identical, with ONE deliberate exception:
        # the old gold secondary is now rain blue. Every other literal is returned untouched.
        if lit.lower() in ('#e8b339', '#e8b33a'): return _fmt(*_hex2rgb(THEMES['dark']['accent-text'])[:3], a)
        H, S, L = _hue(r, g, b), _sat(r, g, b), _lum(r, g, b)
        if S < .25 or not (_GOLD[0] <= H <= _GOLD[1]): return lit
        th = _hex2rgb(THEMES['dark']['accent'])[:3]
        e = L / max(_lum(*_hex2rgb('#e8b339')[:3]), 1e-6)
        if e < 1: return _fmt(*_mix((0, 0, 0), th, max(e, .06) ** .85), a)
        return _fmt(*_mix(th, (255, 255, 255), min((e - 1) * .55, .40)), a)
    T = THEMES[theme]
    key = lit.lower()
    if key.startswith('#'):                              # 1. a named token keeps its name
        if len(key) == 4: key = '#' + ''.join(c * 2 for c in key[1:])
        hit = _EXACT.get(key) or _EXACT.get(lit.lower())
        if hit: return _fmt(*_tok(theme, hit), a)
    L, S = _lum(r, g, b), _sat(r, g, b)
    if S < 0.22 or (L < 0.22 and S < 0.50) or L > 0.90:  # 2. structure: near-black / near-white / unsaturated
        return _fmt(*_grey(L, theme), a)
    H = _hue(r, g, b)                                    # 3. brand colour: nearest token, same emphasis
    name = min(_BUCKETS, key=lambda kv: min(abs(H - kv[0]), 360 - abs(H - kv[0])))[1]
    if name == 'amber' and S < .55: name = 'dim'         # a desaturated gold is a muted label, not the brand gold
    if name == 'dim': return _fmt(*_grey(L, theme), a)
    dk, th = _hex2rgb(THEMES['dark'][name])[:3], _tok(theme, name)
    bg = _tok(theme, 'bg')
    e = L / max(_lum(*dk), 1e-6)                         # how bright this literal is next to dark's own token
    if e < 1:                                            # dimmer -> a tint of the theme colour over its bg
        gamma = .85 if _lum(*bg) < .5 else 1.45          # paper takes a far lighter wash than a dark page
        return _fmt(*_mix(bg, th, max(e, .06) ** gamma), a)
    far = (255, 255, 255) if _lum(*bg) < .5 else (0, 0, 0)
    return _fmt(*_mix(th, far, min((e - 1) * .55, .40)), a)

def themed_css(css, prefix='k'):
    """Returns (css_with_vars, override_blocks). Dark is untouched: it defines none of the vars."""
    seen = {}
    def sub(m):
        lit = m.group(0)
        key = seen.setdefault(lit.lower(), f'--{prefix}{len(seen)}')
        return f'var({key},{lit})'
    out = _RGBA.sub(sub, _HEX.sub(sub, css))
    blocks = ''
    for t in ORDER:
        decls = ''.join(f'{v}:{map_color(k, t)};' for k, v in seen.items()
                        if not (t == 'dark' and map_color(k, t) == k))   # dark declares only what actually moved
        if decls: blocks += (f':root,[data-theme="dark"]{{{decls}}}\n' if t == 'dark'
                             else f'[data-theme="{t}"]{{{decls}}}\n')
    return out, blocks


THEME_BOOT = _BOOT + favicon_tag("dark")
