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
    'dark': {  # current site, unchanged
        'bg': '#000', 'panel': '#0b0b0c', 's2': '#131315', 's3': '#1a1a1d',
        'edge': '#1d1e21', 'edge2': '#2a2b30',
        'txt': '#e6e6e8', 'dim': '#9a9ca4', 'dim2': '#60626a',
        'accent': '#e8b339', 'accent-text': '#e8b339', 'on-accent': '#000',
        'amber': '#e8b339', 'green': '#3fb950', 'red': '#f0564a',
        'cyan': '#8ab4d8', 'violet': '#a99bd6',
        'mark': '#e6e6e8', 'mark-shade': '#1a1a1d',
    },
    'light': {
        'bg': '#f3efe6', 'panel': '#ede8db', 's2': '#e8e2d3', 's3': '#ddd5c2',
        'edge': '#cfc7b3', 'edge2': '#b9af97',
        'txt': '#14213d', 'dim': '#5b6478', 'dim2': '#7a8296',
        'accent': '#e8590c', 'accent-text': '#b8430a', 'on-accent': '#14213d',
        'amber': '#b7791f', 'green': '#1e7f4f', 'red': '#c92a2a',
        'cyan': '#1d6e8c', 'violet': '#5b4b9a',
        'mark': '#14213d', 'mark-shade': '#f3efe6',
    },
    'rain': {
        'bg': '#0b1220', 'panel': '#0f182b', 's2': '#131d33', 's3': '#1b2a44',
        'edge': '#24344f', 'edge2': '#33466a',
        'txt': '#e6f1ff', 'dim': '#8fa3bf', 'dim2': '#5f7391',
        'accent': '#19e3b1', 'accent-text': '#19e3b1', 'on-accent': '#0b1220',
        'amber': '#f0c04a', 'green': '#5be38f', 'red': '#ff6b6b',
        'cyan': '#6cb6ff', 'violet': '#a99bff',
        'mark': '#e6f1ff', 'mark-shade': '#1b2a44',
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

# ------------------------------------------------------------------ the mascot
# A rain cloud wearing a visor, five drips hanging underneath, and a tally stroke counted across them.
# Colours come from the theme: cloud = --mark, visor = --mark-shade, eyes + tally = --accent.
_CLOUD = ('<circle cx="17" cy="20.5" r="10.5"/><circle cx="32" cy="16" r="13.5"/><circle cx="47" cy="20.5" r="10.5"/>'
          '<rect x="6.5" y="20" width="51" height="14" rx="5"/>')
_DRIPS = [(12.2, 11), (21.1, 16), (30.0, 12.5), (38.9, 16.5), (47.8, 10.5)]
_VISOR = '<rect x="10.5" y="18.4" width="43" height="11.6" rx="5.8"/>'
_BOLT = '<path d="M55.5 1.5 L46.8 13.4 h5.1 l-3.4 9.6 L58.6 9.8 h-5.3 z"/>'

def mascot(state='counting', size=28, cls='rmask', title=None):
    """state: counting · edge · noplay · loading1-4 · error · live.
    Returns an inline SVG that themes itself — no fills are hard-coded."""
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

def app_icon(size=64, theme='dark'):
    """Rounded-square app icon: accent field, mark knocked out in on-accent."""
    T = THEMES[theme]
    drips = ''.join(f'<rect x="{x}" y="32" width="6.2" height="{h}" rx="3.1"/>' for x, h in _DRIPS)
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="RAINMAN">'
            f'<rect width="64" height="64" rx="14" fill="{T["accent"]}"/>'
            f'<g transform="translate(5,5) scale(.84)" fill="{T["on-accent"]}">{_CLOUD}{drips}</g>'
            f'<g transform="translate(5,5) scale(.84)" fill="{T["accent"]}">{_VISOR}</g></svg>')

def favicon_href(theme='dark'):
    import base64
    return 'data:image/svg+xml;base64,' + base64.b64encode(app_icon(64, theme).encode()).decode()

def lockup(size=34, stacked=False, cls='rmlock'):
    """Mascot + wordmark. The wordmark is live text so it inherits the page font."""
    m = mascot('counting', size)
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

def map_color(lit, theme):
    """One dark literal -> its counterpart in `theme`."""
    r, g, b, a = _parse(lit)
    T = THEMES[theme]
    bg = _hex2rgb(T['bg'])[:3]; txt = _hex2rgb(T['txt'])[:3]
    L, S = _lum(r, g, b), _sat(r, g, b)
    # near-black and near-white are structure, not brand colour, however tinted they look
    if S < 0.22 or (L < 0.22 and S < 0.62) or L > 0.86:
        t = L ** 0.85                              # dark's black sits on the theme's bg, dark's white on its text
        if theme == 'light': t = min(1.0, t * 1.08)
        return _fmt(*_mix(bg, txt, t), a)
    H = _hue(r, g, b)                              # saturated: snap to the nearest semantic token of this theme
    NAMED = [('red', 10), ('amber', 45), ('green', 140), ('cyan', 205), ('accent', 48), ('violet', 262)]
    best = min(NAMED, key=lambda kv: min(abs(H - kv[1]), 360 - abs(H - kv[1])))[0]
    nr, ng, nb, _ = _hex2rgb(T[best])
    if L < 0.14:                                   # a very dark tint of that colour (a filled chip back) stays a tint
        return _fmt(*_mix(bg, (nr, ng, nb), 0.22), a)
    return _fmt(nr, ng, nb, a)

def themed_css(css, prefix='k'):
    """Returns (css_with_vars, override_blocks). Dark is untouched: it defines none of the vars."""
    seen = {}
    def sub(m):
        lit = m.group(0)
        key = seen.setdefault(lit.lower(), f'--{prefix}{len(seen)}')
        return f'var({key},{lit})'
    out = _RGBA.sub(sub, _HEX.sub(sub, css))
    blocks = ''
    for t in ('light', 'rain'):
        decls = ''.join(f'{v}:{map_color(k, t)};' for k, v in seen.items())
        blocks += f'[data-theme="{t}"]{{{decls}}}\n'
    return out, blocks


THEME_BOOT = _BOOT + favicon_tag("dark")
