"""sport template v4b: memoised day keys, one GAMESD per slate pass, schedule grid on ET days. Rerunnable (guarded)."""
import os, sys
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sport_template.html')
s = open(P, encoding='utf-8').read()
if 'const _DK={}' in s:
    print('already applied'); sys.exit()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
rep("const dayKey=d=>{const x=PD(d);return isNaN(x)?String(d).slice(0,10):x.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:TZD})};",
    "const _DK={};const dayKey=d=>_DK[d]!==undefined?_DK[d]:(_DK[d]=(()=>{const x=PD(d);return isNaN(x)?String(d).slice(0,10):x.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:TZD})})());")
rep("const slatePlayers=()=>J.players.filter(p=>inT(p.team)&&inS(p.slot)&&(p.gp||p.gp_prior)&&nextGame(p.team)&&GAMESD().some(g=>g.away===p.team||g.home===p.team));",
    "const slatePlayers=()=>{const T=new Set(GAMESD().flatMap(g=>[g.away,g.home]));return J.players.filter(p=>inT(p.team)&&inS(p.slot)&&(p.gp||p.gp_prior)&&T.has(p.team))};")
rep("function schedule(){const el=$('#intel');const days=DAYS();",
    "function schedule(){const el=$('#intel');const days=[...new Set(J.games.map(g=>g.day))].sort();")
rep("const gs=J.games.filter(g=>g.away===t||g.home===t);const dd=gs.map(g=>dayKey(g.date));const b2b=",
    "const gs=J.games.filter(g=>g.away===t||g.home===t).sort((a,b)=>a.day<b.day?-1:1);const dd=gs.map(g=>g.day);const b2b=")
rep("const g=gs.find(x=>dayKey(x.date)===d);if(!g)return '<td></td>';",
    "const g=gs.find(x=>x.day===d);if(!g)return '<td></td>';")
open(P, 'w', encoding='utf-8').write(s)
print('applied')
