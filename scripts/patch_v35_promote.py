"""v35 — Josh's promotions (2026-10-21): META -> F2 Matchups; TD Picks, Backtest, Card v2 -> F5 Picks; Weeklies v2 + Category
Grid v2 -> F1 Home (v1 stays behind their switch); API folded under Dev; the six TEST duplicates removed from the registry
(Lab Grid, TD Grid, Head to Head, Game View, Splits, Depth Delta — their promoted copies in F2/F3 are untouched). Rerunnable."""
import io, re, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if "weeklies2:['weeklies','v2','v1','Weeklies']" in s:
    print('already applied'); sys.exit(0)
a = s.index('const SECTIONS=['); b = s.index('const ITEMS={};', a)
sec = s[a:b]

def take(id_):
    """cut one item object out of the TEST section (its whole line) and return its text"""
    global sec
    m = re.search(r"\n[ \t]*\{id:'%s',[^\n]*?c:'test',sub:'[^']*'\}(,?)" % id_, sec)
    assert m, id_
    item = m.group(0).strip().rstrip(',')
    sec = sec[:m.start()] + ('' if m.group(1) else '') + sec[m.end():]
    return item

def put(section_id, items):
    """append items at the end of a section's item list"""
    global sec
    i = sec.index("{id:'%s'," % section_id)
    j = sec.index("]}", i)
    sec = sec[:j] + ',\n   ' + ',\n   '.join(items) + sec[j:]

meta = take('meta'); tdp = take('tdpicks'); w2 = take('weeklies2'); g2 = take('wkgrid2'); bt = take('backtest'); c2 = take('card2')
for d in ['labgrid', 'tdgrid', 'h2h', 'gameview', 'splits', 'ddelta']:
    take(d)
w1 = take('weeklies'); g1 = take('wkgrid')
put('match', [meta]); put('picksec', [tdp, bt, c2]); put('home', [w2, g2, w1, g1])   # v1s ride along, hidden behind the switch
# the TEST section may now end with a dangling comma before "]}"
sec = re.sub(r",(\s*)\]\}", r"\1]}", sec)
s = s[:a] + sec + s[b:]

# pairs: v2 is the primary on Home, v1 lives behind the switch; API behind Dev
old = "const PAIRS={tdboard:['tdbx','Grid','Board','TD'],labgridp:['lab','Grid','Board','Players'],h2hgridp:['h2hp','Grid','Board','H2H'],weeklies:['weeklies2','v1','v2','Weeklies'],wkgrid:['wkgrid2','v1','v2','Category Grid']};"
assert s.count(old) == 1
s = s.replace(old, "const PAIRS={tdboard:['tdbx','Grid','Board','TD'],labgridp:['lab','Grid','Board','Players'],h2hgridp:['h2hp','Grid','Board','H2H'],weeklies2:['weeklies','v2','v1','Weeklies'],wkgrid2:['wkgrid','v2','v1','Category Grid'],dev:['api','Dev','API','Dev']};")
# the Dev panel has no controls row of its own; pairBar creates one. Keep the dev frame lazy-load working for both.
old = "if(it.id==='dev'){const f=$('#devFrame');if(f&&!f.src)f.src=f.dataset.src}"
assert s.count(old) == 1
s = s.replace(old, "if(it.id==='dev'||it.id==='api'){const f=$('#devFrame');if(f&&!f.src&&it.id==='dev')f.src=f.dataset.src}")
s = s.replace("Object.assign(NOTES,{pairs34:", "Object.assign(NOTES,{promote35:['v35','META now lives on F2 Matchups \\u00b7 TD Picks, Backtest and Card v2 on F5 Picks \\u00b7 Weeklies and Category Grid (v2 first, v1 behind the switch) on F1 Home \\u00b7 API behind Dev \\u00b7 Lab Grid, TD Grid, Head to Head, Game View, Splits and Depth Delta left TEST (their F2 / F3 versions stay)']});\nObject.assign(NOTES,{pairs34:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v35 applied', len(s))
