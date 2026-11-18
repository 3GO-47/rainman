"""v62 — META / META v2: the every-position table carries every market column (not one 'best market' cell); METAPROP is its own
visible sub-tab under Matchups instead of a pill hidden behind META. metaProp() itself is untouched. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v62 */' in s:
    print('v62 already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:100])
    s = s.replace(old, new)

# 1. METAPROP out from behind META: no pair → both render as sub-tabs (META · METAPROP · META v2 order below)
rep("const PAIRS={meta:['metaprop','META','METAPROP','META'],tdboard:", "/* v62 */const PAIRS={tdboard:")
# order: META, METAPROP, META v2
i_meta = s.index("   {id:'meta',label:'META',"); i_v2 = s.index("   {id:'metav2',nfl:true,label:'META v2',"); i_mp = s.index("   {id:'metaprop',nfl:true,label:'METAPROP',")
assert i_meta < i_v2 < i_mp
e_mp = s.index('\n', i_mp) + 1
mp_line = s[i_mp:e_mp]
s = s[:i_mp] + s[e_mp:]
s = s[:i_v2] + mp_line + s[i_v2:]
s = s.replace("'test',sub:'metaprop'}]},\n", "'test',sub:'metaprop'},\n").replace("',c:'test',sub:'metav2'},\n", "',c:'test',sub:'metav2'}]},\n")   # the section closer stays on the last item

# 2. the ALL table: every market column (QB → RB → receiving), '·' where the market is not his
rep("const mkTH=(th,p)=>{const MS=p==='ALL'?['best']:(MK_POS[p]||[]);",
    "const MK_ALL=['pass_yds','pass_td','completions','rush_yds','rush_att','receptions','rec_yds'];\nconst mkTH=(th,p)=>{const MS=p==='ALL'?MK_ALL:(MK_POS[p]||[]);")
rep("const MS=p==='ALL'?[]:(MK_POS[p]||[]);return meta+(p==='ALL'?mkBestCell(x):MS.map(m=>mkCell(x.mk&&x.mk[m],m)).join(''))+mkTdCell(x)};",
    "const MS=p==='ALL'?MK_ALL:(MK_POS[p]||[]);return meta+MS.map(m=>mkCell(x.mk&&x.mk[m],m)).join('')+mkTdCell(x)};")
rep("MS=p==='ALL'?['best']:(MK_POS[p]||[]),wname=p==='ALL'?20:24,wpos=p==='ALL'?4:0,wopp=9,wmeta=9,wtd=11,",
    "MS=p==='ALL'?MK_ALL:(MK_POS[p]||[]),wname=p==='ALL'?16:24,wpos=p==='ALL'?4:0,wopp=8,wmeta=7,wtd=9,", 2)
rep("p==='ALL'?mkBestCell(x):MS.map(m=>mkCell(x.mk&&x.mk[m],m)).join('')}", "MS.map(m=>mkCell(x.mk&&x.mk[m],m)).join('')}")
# reading key
rep("one column — META; every position together, then QB, RB, WR and TE;", "one column — META, then every market the books post for him (bold = model median · line · O/U lean, green over / red under) and the TD model; every position together, then QB, RB, WR and TE;")
rep("Object.assign(NOTES,{metaprop:['v23',", "Object.assign(NOTES,{meta62:['v62','META and META v2: the every-position table now shows every market column (pass yds · pass TD · cmp · rush yds · carries · rec · rec yds) instead of one best-market cell · METAPROP is its own sub-tab under Matchups (META · METAPROP · META v2), no longer hidden behind a pill'],metaprop:['v23',")
open(P, 'w', encoding='utf-8').write(s)
print('v62 applied')
