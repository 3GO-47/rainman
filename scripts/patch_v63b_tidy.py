"""v63b — Def Trends tidy: lead cards skip defenses on bye this week (nobody draws the hole), the pop-up's value columns are
plain (the rank badge carries the colour), the control row drops the hint the intro already gives. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v63b */' in s:
    print('v63b already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:100])
    s = s.replace(old, new)
rep("const cw=win>=7?3:win,od=r=>r.w[cw]-r.se;\n    const holes=R.slice().sort((a,b)=>b.ex-a.ex).slice(0,6);\n    const open=R.filter(r=>r.n>cw&&r.w[cw]>r.lg[cw])",
    "const cw=win>=7?3:win,od=r=>r.w[cw]-r.se;/* v63b */const live=R.filter(r=>!draw(r.d,r.s,wk).bye);\n    const holes=live.slice().sort((a,b)=>b.ex-a.ex).slice(0,6);\n    const open=live.filter(r=>r.n>cw&&r.w[cw]>r.lg[cw])")
rep("const shut=R.filter(r=>r.n>cw&&r.se>r.lg.se)", "const shut=live.filter(r=>r.n>cw&&r.se>r.lg.se)")
rep("[{l:ST[k].l,t:'allowed per game to the '+s+", "[{l:ST[k].l,g:false,t:'allowed per game to the '+s+")
rep("return [{v,h:fmt(v,k)},{v:r.rk[n],h:badge(r.rk[n])},{v:r.lg[n],h:fmt(r.lg[n],k)}]", "return [{v,h:'<b>'+fmt(v,k)+'</b>'},{v:r.rk[n],h:badge(r.rk[n])},{v:r.lg[n],h:fmt(r.lg[n],k)}]")
rep("<span class=\"mini dim\">${SE} games through week ${wk-1} · allowed per game · green = allows the most · click anything for every window and the game log</span>", "<span class=\"mini dim\">${SE} games through week ${wk-1}</span>")
rep("${ST[stat].l} per game over the league average for the slot · who draws it this week`", "${ST[stat].l} per game over the league average for the slot · who draws it this week · byes left out`")
open(P, 'w', encoding='utf-8').write(s); print('v63b applied')
