"""v36 — (a) F6 TEST Dev/API sub-tab removed: everything it showed is on dashboard/dev.html (the ⚙ dev link), incl. the
by-reason / by-league credit splits added to build_dev.py; (b) position glyphs replaced by letters (Q R W T D) and, wherever a
player row knows his depth slot, the slot itself (QB1, RB2, WR3 …) is shown instead. Rerunnable."""
import io, re, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'class="posL' in s:
    print('already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

# ---------- (a) Dev / API out of TEST ----------
a = s.index('const SECTIONS=['); b = s.index('const ITEMS={};', a); sec = s[a:b]
for id_ in ['dev', 'api']:
    m = re.search(r"\n[ \t]*\{id:'%s',[^\n]*?c:'test',sub:'[^']*'\}(,?)" % id_, sec); assert m, id_
    sec = sec[:m.start()] + sec[m.end():]
sec = re.sub(r",(\s*)\]\}", r"\1]}", sec); s = s[:a] + sec + s[b:]
rep(",dev:['api','Dev','API','Dev']};", "};")

# ---------- (b) letters, and the depth slot where the row knows it ----------
i = s.index("function posIcon(p,px=12){"); j = s.index("const slotchip=", i)
s = s[:i] + ("const POSL={QB:'Q',RB:'R',FB:'R',WR:'W',TE:'T','D/ST':'D',K:'K'};\n"
             "/* v36: a letter, not a glyph — and the depth slot itself (QB1, RB2, WR3) when the row knows it */\n"
             "function posIcon(p,px=12,slot){const c=POSC[p]||'#8b98a5';const t=slot?String(slot).replace('WR4+','WR4+'):(POSL[p]||'?');return `<b class=\"posL${slot?' sl':''}\" style=\"color:${c};font-size:${slot?Math.max(9,px-2):px}px\" title=\"${slot?esc(String(slot)):p}\">${t}</b>`}\n") + s[j:]
rep("  return `<span class=\"pos\" style=\"color:${c};border-color:${c}55\">${posIcon(p,11)}${x}</span>`};",
    "  return `<span class=\"pos\" style=\"color:${c};border-color:${c}55\">${x}</span>`};")
rep("/* v34 paired views */", "/* v36 position letters */.posL{font:700 11px var(--mono);display:inline-block;min-width:11px;text-align:center;vertical-align:baseline;letter-spacing:.02em}.posL.sl{min-width:0;letter-spacing:.04em}\n/* v34 paired views */")
# rows that know the slot
rep("<span style=\"color:${POSC[x.pos]}\">${posIcon(x.pos,10)}</span>", "${posIcon(x.pos,10,x.u?(x.u.dslot||x.u.slot):x.slot)} ", 4)
rep("<td style=\"color:${POSC[x.pos]}\">${posIcon(x.pos,10)}</td>", "<td>${posIcon(x.pos,10,x.u?(x.u.dslot||x.u.slot):x.slot)}</td>", 4)
rep("${posIcon(u.pos,10)}", "${posIcon(u.pos,10,u.dslot||u.slot)}", 4)
s = s.replace("Object.assign(NOTES,{promote35:", "Object.assign(NOTES,{pos36:['v36','positions are letters now (Q R W T D), and a player row shows his depth slot (QB1, RB2, WR3\\u2026) wherever it knows it \\u00b7 the F6 Dev / API tab is gone: everything it showed is on the \\u2699 dev page']});\nObject.assign(NOTES,{promote35:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v36 applied', len(s))
