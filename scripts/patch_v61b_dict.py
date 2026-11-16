"""v61b — dictionary-encode repeated strings inside the columnized payloads (lossless; the template rehydrates). Keeps rainman.html under the 10 MB upload cap. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
T = 'scripts/dashboard_template.html'; B = 'scripts/build_dashboard.py'
t = open(T, encoding='utf-8').read(); b = open(B, encoding='utf-8').read()
old_t = "if(v&&v.__cols){const C=v.__cols;box[key]=v.rows.map(r=>{const o={};for(let i=0;i<C.length;i++)o[C[i]]=r[i];return o})}"
new_t = "if(v&&v.__cols){const C=v.__cols,D=v.__dict||{};box[key]=v.rows.map(r=>{const o={};for(let i=0;i<C.length;i++){const x=r[i];o[C[i]]=D[i]&&typeof x==='number'?D[i][x]:x}return o})}"
if old_t in t:
    t = t.replace(old_t, new_t); open(T, 'w', encoding='utf-8').write(t); print('template: rehydrate reads __dict')
else:
    assert new_t in t, 'rehydrate line not found'; print('template already v61b')
old_b = "                container[key] = {'__cols': cols, 'rows': [[r.get(c) for c in cols] for r in v]}\n"
new_b = """                rows = [[r.get(c) for c in cols] for r in v]
                # v61b: columns of repeated strings become indexes into a per-column dictionary (lossless; rehydrated on load)
                dct = {}
                for j in range(len(cols)):
                    vals = [row[j] for row in rows]
                    strs = [x for x in vals if isinstance(x, str)]
                    if len(strs) < 50 or any(not isinstance(x, (str, type(None))) for x in vals): continue
                    uniq = list(dict.fromkeys(strs))
                    if sum(len(x) + 2 for x in strs) <= len(strs) * 3 + sum(len(x) + 3 for x in uniq): continue
                    idx = {x: i for i, x in enumerate(uniq)}
                    for row in rows: row[j] = idx[row[j]] if row[j] is not None else None
                    dct[str(j)] = uniq
                container[key] = {'__cols': cols, 'rows': rows} | ({'__dict': dct} if dct else {})
"""
if old_b in b:
    b = b.replace(old_b, new_b); open(B, 'w', encoding='utf-8').write(b); print('build_dashboard: dictionary columns')
else:
    assert '__dict' in b; print('build_dashboard already v61b')
# Live Categories: members arrive compact (player table + slot table) — expand on read
t = open(T, encoding='utf-8').read()
old_w = "function wkView(c,wk){if(wk===C.week)return {n:c.cur.n,played:c.cur.played,hits:c.cur.hits,hr:c.cur.hr,members:c.cur.members,live:true};const w=c.weeks[C.seasons[C.seasons.length-1]+'-'+wk];if(!w)return null;return {n:w.n,played:w.n,hits:w.hits,hr:w.hr,members:(w.members||[]).map(m=>({player:m[0],team:m[1],slot:m[2],ppr:m[3],hit:m[4],opp:null,pos:null,base:null})),live:false,base:w.base}}"
new_w = "const PL=C.players||[],SLs=C.slots||[];const ex=m=>Array.isArray(m)?(m.length>4?{player:PL[m[0]][0],team:PL[m[0]][1],slot:SLs[m[1]],opp:m[2],pos:m[3],base:m[4],ppr:m[5],hit:m[6],td:m[7],inj:m[8]}:{player:PL[m[0]][0],team:PL[m[0]][1],slot:SLs[m[1]],ppr:m[2],hit:m[3],opp:null,pos:null,base:null}):m;\n  function wkView(c,wk){if(wk===C.week)return {n:c.cur.n,played:c.cur.played,hits:c.cur.hits,hr:c.cur.hr,members:c.cur.members.map(ex),live:true};const w=c.weeks[C.seasons[C.seasons.length-1]+'-'+wk];if(!w)return null;return {n:w.n,played:w.n,hits:w.hits,hr:w.hr,members:(w.members||[]).map(ex),live:false,base:w.base}}"
if old_w in t:
    t = t.replace(old_w, new_w); open(T, 'w', encoding='utf-8').write(t); print('template: compact category members')
else:
    assert new_w in t; print('template already expands members')
# v61c: layout fixes seen in proof — auto column widths on the new tables, visible live bars, wider rank cell
t = open(T, encoding='utf-8').read()
if '/* v61c */' not in t:
    t = t.replace('</style>', "/* v61c */table.fx.qtt,table.fx.g2t{table-layout:auto}.clrow .bar{display:block;width:100%}.clrow{grid-template-columns:48px minmax(180px,1.4fr) 100px repeat(6,minmax(64px,.6fr)) 60px}.clrow>span:nth-child(3){white-space:nowrap}\n</style>", 1)
    open(T, 'w', encoding='utf-8').write(t); print('template: v61c css')
else: print('template already v61c')
